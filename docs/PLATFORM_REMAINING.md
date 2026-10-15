# Remaining local platform work

This audit follows the original ten-area brief and the user's later instruction
to finish local integration without deployment. Passing the current regression
suite does not establish completion of the full brief. Customer credentials,
licensed data, live supplier delivery and production operation remain separate
configuration/validation gates.

## Verified corrections in this pass

The 15 October pass fixed fact loss during identity matching, omitted same-upload
identity reviews, overlapping mapping errors, delegation authority/expiry,
downstream cascade uncertainty, public credential request budgets, intraday feed
polling and expired-worker state overwrites. All 296 Python tests passed through
the disposable PostgreSQL runner without skips. Ruff lint and formatting passed.
The frontend source did not change in this pass; its previous twelve tests,
type/lint checks and production build remain the latest frontend evidence.

## Requirements still needing local implementation or stronger evidence

| Brief area | Current evidence and gap | Completion evidence needed |
|---|---|---|
| 9: database graph queries; 10: graph-query load | `platform/store.py` stores immutable JSON snapshots and exposes snapshot reads; `platform/cascade.py` projects them into NetworkX. `scripts/platform_graph_load.py` times in-memory traversal. The requested PostgreSQL recursive-query/AGE path and a database/API load harness are absent. | Tenant-scoped, revision/as-of-aware database traversal with the same status/validity, cycle, depth/path/work limits; PostgreSQL parity regressions and a load command exercising the actual database/API query path. |
| 3 and 10: extraction evaluation and recorded agent fixtures | `scripts/evaluate.py` calls the retained prototype evaluation. Platform provider/citation regressions exist, but there is no labelled multi-industry platform extraction corpus and replay report. Scorer holdout evaluation is implemented separately. | Offline recorded provider responses through the platform extraction/citation pipeline, explicit TP/FP/FN, precision/recall and citation-error counts, fixture/prompt versions and reproducible CLI/test output. Synthetic measurements must remain labelled. |
| 2: complete import mapping UI | The backend accepts bounded dotted mappings and per-field units. `frontend/app/platform/workspace.tsx` exposes a fixed subset, omitting identifiers, daily revenue, other measurements and some link fields. | Accessible field/unit controls that can populate the implemented domain inputs through staging/review/apply, with regression evidence for sourced revenue, lead times and identifiers. |
| 2 and 8: history and review queues at scale | `platform/records.py:list_records` defaults to the latest 200 mixed records. Several workspace panels filter that shared list; imports, approvals, events and notifications can be hidden by unrelated newer work. Dedicated jobs/model lists are also bounded. | Scoped, deterministic pagination and product navigation/filtering that retain access to older imports, pending reviews and linked source records, with tenant/privacy and concurrent-insert regressions. |
| 8: inventory completeness dashboard | The workspace counts missing fields on existing inventory rows. Absent material/plant inventory can therefore display zero missing inputs although the cascade correctly flags missing stock. | A graph-aware completeness measure distinguishing missing rows from missing values and tests for an empty inventory list and partially covered material/plant usage. |
| 3 and 8: score provenance and presentation | `platform/evidence.py` places active-model details in a free-text note; the graph inspector always labels confidence uncalibrated. | Structured scorer/model/calibration provenance and display that accurately distinguishes rule support from a calibrated scorer's limited evaluation scope. |
| 6: tenant execution budgets and deadlines | Durable cost reservations, request limits, queue capacity, retries and claim fencing exist. Queue capacity is not a tenant execution-rate budget, and fencing does not cancel an in-flight tool call. | Durable tenant-wide execution limits across callers/workers, bounded whole-job behavior and tests for overlapping workers, expiry and safe recovery of side effects. |

Some network toolbar/accessibility strings remain English in the shared graph
component. The English/Hindi workspace catalog is implemented, but full local
copy/accessibility/responsive verification still needs to include those controls.

The original Ariba requirement is an adapter **stub**, which exists; validating a
real customer adapter is not a missing stub implementation. Likewise, the local
encrypted backup/recovery drill exists; production scheduling, secret/TLS setup
and recovery objectives belong to the excluded deployment work.
