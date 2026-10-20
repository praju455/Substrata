# Local platform completion audit

This audit follows the original ten-area brief and the instruction to finish the
local platform without deploying it. The previously identified implementation
gaps are now closed and covered by local regression evidence. This does **not**
establish production readiness, customer accuracy, or permission to contact real
suppliers.

## Completed local work

| Area | Implemented evidence |
|---|---|
| PostgreSQL graph traversal | Tenant-scoped, revision-pinned recursive CTE traversal now applies link status, validity, cycle, depth, path and work bounds. Assessment parity is tested against the deterministic offline NetworkX implementation. |
| Database graph load | `scripts/platform_graph_load.py` can exercise PostgreSQL directly. `scripts/verify_postgres.py` runs this database path after PostgreSQL regressions and reports synthetic latency/throughput without claiming a production target. |
| Extraction evaluation | A versioned, labelled, recorded-response fixture covers multiple synthetic industries. `scripts/evaluate_platform_extraction.py` reports exact TP/FP/FN, precision, recall and citation errors with prompt/fixture/provider versions and an input hash. These are regression measurements, not real-world accuracy claims. |
| Import mappings | The workspace exposes entity identifiers, country/unit/requalification/revenue fields, inventory, links, purchase orders and BOM mappings, including independent unit inputs. Backend mapping regressions cover identifiers, revenue and units. |
| History at scale | Tenant- and kind-scoped keyset pagination is available through `/platform/records/page`. The workspace loads relevant queues independently and can load older records without unrelated activity hiding them. |
| Inventory completeness | The API derives expected material-to-plant inventory coverage from the graph and distinguishes entirely missing rows, incomplete rows and complete rows. |
| Confidence provenance | Inferred links store structured method, scorer, calibration, feature/prompt, evaluation-scope and synthetic-data provenance. The inspector no longer labels calibrated and rule-supported scores identically. |
| Execution governance | Tenant policy now includes a durable hourly background-job allowance and a whole-job deadline. Claims serialize the tenant counter across workers; deadline context also bounds provider calls. Expiry, recovery and overlapping PostgreSQL workers are covered. |
| Accessibility and translation | Shared graph controls accept translated text and accessible labels; the workspace includes responsive mapping/history layouts and English/Hindi copy for the added controls. |

## Reproducible verification

```bash
python -m scripts.evaluate_platform_extraction
python scripts/verify_postgres.py --full-suite
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run build
```

The extraction fixture and graph-load inputs are synthetic. The generated
evaluation report is stored at `data/platform_extraction_evaluation.json`.

## Deliberately outside this local scope

- Production deployment, monitoring ownership, TLS/secrets and recovery objectives.
- Customer credentials, licensed feeds, live SAP validation and real supplier delivery.
- Customer-shaped performance baselines and a representative labelled evaluation set.
- Any learned accuracy claim. No LLM or embedding model is trained by this project;
  providers are pretrained models used through prompts and structured output. The
  optional small link scorer remains separately governed and synthetic results must
  stay labelled.

The Ariba requirement remains an explicit adapter stub, as requested. The local
prototype stays dry-run and makes no real purchase or supplier contact.
