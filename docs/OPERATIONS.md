# Local operations and production gates

## Docker Compose development

Compose is a local development scaffold, not a production deployment. Its
PostgreSQL credentials are deliberately marked local-only and must never be reused
outside a developer machine. The database and API ports bind to loopback. The app
database role is `NOSUPERUSER` and `NOBYPASSRLS`; migrations use the separate
PostgreSQL admin account. The database image includes pgvector to support the
document-vector migration. The worker is opt-in because its tenant must already be
provisioned.

Create a development signing key on the host, then start PostgreSQL, migrations
and the API. On PowerShell:

```powershell
New-Item -ItemType Directory -Force data/dev-auth
$env:SUBSTRATA_ENV = "development"
$env:SUBSTRATA_AUTH_KEY_FILE = "data/dev-auth/auth.secret"
python -m substrata.platform.cli dev-key
$env:SUBSTRATA_AUTH_KEY_FILE = "data/dev-auth/confirmation.secret"
python -m substrata.platform.cli dev-key
$env:SUBSTRATA_AUTH_KEY_FILE = "data/dev-auth/auth.secret"
docker compose up --build db migrate api
```

The command refuses to overwrite an existing key and requests owner-only file
permissions on systems that support POSIX permission bits. Apply restrictive ACLs
to the secret file on Windows hosts.

Use a local development token to onboard the matching tenant:

```powershell
docker compose run --rm --no-deps --entrypoint python api -m substrata.platform.cli dev-token --tenant demo --role admin
```

After provisioning that tenant, run its worker with
`docker compose --profile worker up worker`. Keep development tokens private.
Compose migrations run as the database administrator; API and worker processes
run with the restricted app database role. Starting an existing named volume does
not re-run PostgreSQL initialization SQL. The tenant worker also enforces approval
SLA expiries; without it, API approval decisions still reject expired requests,
but portal expiry notices are delayed until the worker runs.

Start the local UI with `python scripts/dev.py ui` and open
`http://127.0.0.1:3000/platform/`. Its evidence panel connects document storage,
indexing, retrieval and cited discovery; the separate development confirmation key
enables signed local supplier previews without sending email. Background tasks can
be queued, inspected and run one at a time from the workspace when no worker is
running. Risk review uses the existing A2A workflow and pins its graph revision.

The PostgreSQL integration suite uses the migration administrator only for schema
and test-role setup. Workflow checks run as a separate `NOSUPERUSER`, `NOBYPASSRLS`
role. It verifies forced RLS on every tenant table, no tenant-context leakage
through pooled connections, pgvector retrieval and model versions, staged import
history/rollback, atomic concurrent graph/audit writes, and durable risk-review
checkpoints followed by named approval and idempotent dry-run execution. Six
checks passed against the local Docker PostgreSQL 17/pgvector instance on
14 October 2026. These synthetic workflow checks do not establish customer scale.

## Repeatable PostgreSQL verification

Start Docker Desktop (or a local Docker engine) and install `.[dev,platform]` into
the project Python environment. The runner selects `.venv` when it exists. It
can discover both the per-user and system Windows Docker Desktop CLI locations
if Docker is not on PATH; an explicit `--docker PATH` is also supported.

```powershell
python scripts/verify_postgres.py
python scripts/verify_postgres.py --full-suite
```

The first command runs the PostgreSQL integration checks; `--full-suite` runs all
Python tests with PostgreSQL integration enabled. Most fixture tests still use
temporary SQLite databases; the six production-dialect checks use PostgreSQL.
The runner creates its own `--rm` pgvector container with a generated test-only
password and an ephemeral loopback port. It waits for PostgreSQL to accept TCP
connections and passes the admin URL directly to the pytest child environment.
There are no host mounts or named volumes. On success, test failure or interruption,
it stops only the container it created and removes its anonymous database volume;
the existing Compose stack is untouched. Failed tests propagate a nonzero exit.
The latest complete run passed 243 Python tests on 14 October 2026 with no skips.

## Health, logs and metrics

`/health` is liveness only. `/ready` checks each configured SQLAlchemy database
connection with `SELECT 1` and returns 503 on a database failure. `/metrics`
exports process-local request/error counters, an in-flight gauge, response counts
by method/route/status and cumulative latency histograms in Prometheus text format.
Duration covers the complete response body, including streams. Aborted responses
and HTTP 5xx count as errors. Metrics reset on restart, use registered route
templates (or `<unmatched>`), normalize unknown methods to `OTHER` and never label
tenants, tokens or path parameters. Scrape each API process separately and aggregate
in a managed metrics system.

Each request logs one JSON record with a bounded ASCII request ID, trace/span IDs,
method, route template, status, duration and aborted flag. The server accepts a safe
`X-Request-ID` or generates one; validated `traceparent` preserves incoming trace
causality and a server-span traceparent is returned on ordinary responses. Headers,
tokens, raw path parameters, bodies, query strings, vendor tracestate and baggage
are excluded. Unhandled failures record the exception class, not its message or
stack trace. Forward these records to the deployment's log collector.
The supplied Docker and development launchers disable Uvicorn's raw URL access
log; custom launch commands should also use `--no-access-log`. Application JSON
logs are emitted through the `substrata` logger. Configure framework diagnostic
log redaction separately when deploying with a different server/logging setup.

## Optional OTLP tracing

The trace contract follows [W3C Trace Context](https://www.w3.org/TR/trace-context/)
and [OpenTelemetry Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)
and [exporter guidance](https://opentelemetry.io/docs/languages/python/exporters/).
The platform dependencies include the SDK and OTLP/HTTP exporter. Export is
disabled when `SUBSTRATA_OTLP_TRACES_ENDPOINT` is blank; local correlation still
works without a collector. Configure the complete trace endpoint, for example:

```text
SUBSTRATA_OTLP_TRACES_ENDPOINT=https://collector.example/v1/traces
SUBSTRATA_TRACE_SAMPLE_RATIO=0.1
SUBSTRATA_OTLP_HEADERS_FILE=/run/secrets/otlp-headers.json
```

The optional header file contains a JSON object of header names to values. Mount
it with restricted permissions rather than putting credentials in source or a
browser setting. Collector URLs reject credentials, query strings and fragments.
HTTPS is required; development alone permits HTTP on localhost/loopback. Sampling
is trace-ID-based and locally enforced even if the remote client sets sampled=1.
The exporter queue holds at most 1024 spans, batches at most 128, and uses a five
second export timeout. API shutdown flushes and closes its owned provider. No
global provider is replaced when constructing independent test/application instances.
Service names are bounded stable ASCII identifiers; do not encode tenant/customer
information in `OTEL_SERVICE_NAME`. A temporary loopback collector verifies real
protobuf OTLP export and shutdown flushing in the regression suite. Production
collector credentials, certificate trust, retention and log/metric shipping still
require deployment configuration.

Producer spans persist traceparent as durable job metadata. Each worker attempt
creates a linked consumer span even after process restart; retries preserve the
original producer context. Provider and connector requests create child client
spans and propagate traceparent, excluding vendor state/baggage. Trace context is
observability metadata and never grants tenant authority. Worker job logs include
only job type, attempt, status, duration and trace/span IDs, not saved graph inputs,
documents, contacts or mitigation rationales. Assessment jobs reconstruct their
aware datetime from persisted JSON before calling the deterministic calculator.
Tests exercise API-to-worker causality, provider/connector propagation and error
redaction, plus real worker-process OTLP export/flush to a temporary local collector.

Compose passes the optional endpoint, sample ratio and header-file settings to both
API and worker. For local secret-file use, put `otlp-headers.secret` in the ignored
`data/dev-telemetry/` directory and set
`SUBSTRATA_OTLP_HEADERS_FILE=/run/telemetry/otlp-headers.secret`. Both containers
mount that directory read-only; the worker does not receive the API signing key.
Use a collector endpoint reachable from inside each container. Loopback refers
to that container, and HTTPS is required for a collector on another host/service.

## Database backup and restore

Production deployments must use PostgreSQL with TLS and managed encrypted storage;
SQLite is for local development and offline tests. Define customer-specific RPO
and RTO before a pilot. Schedule encrypted, access-controlled `pg_dump` backups or
managed point-in-time recovery, keep encryption keys outside the database account,
and retain copies in a separate failure domain. Protect audit exports and their
chain heads separately.

`substrata.platform.backups` supplies a versioned AES-256-GCM envelope for custom
PostgreSQL archives, using a separate raw 32-byte key. Both the manifest and dump
are encrypted; the version/nonce header is authenticated as additional data. Keys
and output artifacts refuse overwrite. Encryption streams the native dump directly,
and recovery stages only ciphertext in a private temporary file. The entire tag is
verified before any restore callback is exposed; the staged copy also prevents
changes to the original path between verification and restore. Wrong keys,
truncation, nonce/ciphertext/tag modifications and unsupported formats fail closed.
These helpers follow [Cryptography's GCM guidance](https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/#cryptography.hazmat.primitives.ciphers.modes.GCM).
Keep backup keys in the deployment secret manager, separately from artifacts and
database credentials; Windows hosts need restrictive parent-directory/file ACLs.
The ignored `data/backups/` and `data/recovery-drills/` paths are local output areas,
not offsite storage or a production retention policy.

Use the project environment (`pip install -e ".[dev,platform]" -c requirements-dev.lock`)
and native PostgreSQL 17 client tools for the operational CLI. The scripts select
the repository `.venv` automatically when present. For example:

```powershell
python scripts/platform_backup.py key --key-file data/backups/backup.secret
python scripts/platform_backup.py create --key-file data/backups/backup.secret --file data/backups/platform.enc --synthetic
python scripts/platform_backup.py inspect --key-file data/backups/backup.secret --file data/backups/platform.enc
python scripts/platform_backup.py restore --key-file data/backups/backup.secret --file data/backups/platform.enc --new-database recovered_platform
python scripts/verify_recovery.py
```

Create the restricted backup output directory first. Configure
`SUBSTRATA_BACKUP_DATABASE_URL` through the backend secret environment, using a
separate backup role with SELECT rights on every table and BYPASSRLS. Runtime roles
must never receive this privilege. Configure `SUBSTRATA_RESTORE_ADMIN_URL` separately
with CREATE DATABASE permission. Production URLs require `sslmode=verify-full`;
native tool passwords are passed through child environment variables, never argv.
Use `--pg-dump` / `--pg-restore` for trusted executable paths when tools are outside
PATH. Apply `--synthetic` only to known invented data.

The custom dump and encrypted manifest share an exported REPEATABLE READ snapshot.
Restore verifies the complete envelope before database creation, refuses existing
database names and runs `pg_restore` in one transaction. A failed restore leaves its
new database for inspection; it never drops a database. Provision least-privilege
runtime roles and grants afterward: per-database dumps exclude cluster-global roles,
and ownership/ACLs are deliberately omitted. Match the source PostgreSQL/pgvector
versions and confirm encrypted manifest counts, graph hashes and audit heads before
cutover. Only restore archives from trusted database operators: authentication
establishes artifact integrity, while native dumps can contain executable SQL.
See the PostgreSQL [dump](https://www.postgresql.org/docs/17/app-pgdump.html) and
[restore](https://www.postgresql.org/docs/17/app-pgrestore.html) documentation.

The Docker drill uses two fresh containers with generated credentials, loopback
ephemeral ports, no host mounts and synthetic automotive/food fixtures. It removes
only its owned containers/anonymous volumes, never the application's Compose data.
Its ignored JSON report contains validation results and measured backup/restore
seconds; these small-fixture measurements do not establish a customer's RTO/RPO.
Keep authenticated archive/key retention and offsite storage in the deployment's
secret/storage systems, and use managed PITR for production recovery requirements.

For each release, restore a recent backup into an isolated PostgreSQL instance,
run migrations there, validate tenant row-level policies using both allowed and
denied tenant identities, verify exported audit chains, and exercise API readiness
and representative graph/assessment reads. Record elapsed restore time and data
loss window. Do not run destructive restore commands against a production cluster.

## Production work still required

Replace development credentials and role provisioning with a reviewed secret
manager, provision the least-privilege migration/runtime roles separately, enable
TLS on every network hop, configure OIDC and tenant/role claims, and establish
backups, retention, key rotation, restore drills and incident response. Add a
managed durable broker or supervise one worker process per tenant, and add
the production collector plus durable metrics/log shipping. The included Compose file
uses local credentials and does not claim to satisfy those controls.
