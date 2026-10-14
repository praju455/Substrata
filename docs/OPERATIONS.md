# Local operations and production gates

## Docker Compose development

Compose is a local development scaffold, not a production deployment. Its
PostgreSQL credentials are deliberately marked local-only and must never be reused
outside a developer machine. The database and API ports bind to loopback. The app
database role is `NOSUPERUSER` and `NOBYPASSRLS`; migrations use the separate
PostgreSQL admin account. The worker is opt-in because its tenant must already be
provisioned.

Create a development signing key on the host, then start PostgreSQL, migrations
and the API. On PowerShell:

```powershell
New-Item -ItemType Directory -Force data/dev-auth
$env:SUBSTRATA_ENV = "development"
$env:SUBSTRATA_AUTH_KEY_FILE = "data/dev-auth/auth.secret"
python -m substrata.platform.cli dev-key
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

## Health, logs and metrics

`/health` is liveness only. `/ready` checks each configured SQLAlchemy database
connection with `SELECT 1` and returns 503 on a database failure. `/metrics`
exports process-local request and 5xx counters in Prometheus text format. These
counters reset on restart and are not tenant-labelled. Each HTTP request logs one
JSON record with request ID, method, path, status and elapsed milliseconds. The
server accepts a bounded safe `X-Request-ID` or generates one. Tokens, request
bodies and query strings are not logged. Forward these records to the deployment's
log collector and retain request IDs across API gateways.

## Database backup and restore

Production deployments must use PostgreSQL with TLS and managed encrypted storage;
SQLite is for local development and offline tests. Define customer-specific RPO
and RTO before a pilot. Schedule encrypted, access-controlled `pg_dump` backups or
managed point-in-time recovery, keep encryption keys outside the database account,
and retain copies in a separate failure domain. Protect audit exports and their
chain heads separately.

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
distributed tracing plus durable metrics/log shipping. The included Compose file
uses local credentials and does not claim to satisfy those controls.
