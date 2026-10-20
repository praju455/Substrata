# Substrata

> **See what your suppliers secretly share.** <sup>[Design]</sup>

![Stage](https://img.shields.io/badge/stage-working%20prototype-6f42c1)
![Build](https://img.shields.io/badge/build-synthetic%20vertical%20slice%20checked-147d78)
![Data](https://img.shields.io/badge/demo%20data-synthetic-f59e0b)
![Event](https://img.shields.io/badge/SAP%20Hackfest-Bengaluru%202026-0a6ed1)

**Project:** Substrata <sup>[Design]</sup> · **Team:** V-Max

Substrata is a proposed agentic supply-chain resilience layer that discovers hidden dependencies across supplier tiers, estimates how much decision time remains before production is exposed, and recommends governed mitigation options. <sup>[Design]</sup>

> **Current prototype status:** the synthetic vertical slice implements evidence-backed graph discovery, simulated supplier confirmations, event replay, deterministic exposure calculations, mitigation drafts, named approval and hash-chained audit. Pretrained-model access remains behind a provider-neutral `LLMClient`; Gemini is primary, Groq is the fallback and mock mode works offline. LangGraph orchestration, the grounded domain assistant and the Google Gen AI SDK adapter remain selected next steps. Neither path claims validated live SAP access, customer accuracy or real purchase execution.

See the [three-minute demo](docs/DEMO_SCRIPT.md), [build checklist](docs/BUILD_PLAN.md) and [decision register](docs/DECISIONS.md).

## Getting started

Requires Python 3.12+, Node.js 24.x and npm. Verified on Windows with Python 3.13.5, Node.js 24.14.0 and npm 11.9.0. Run from the repository root. Setup needs internet to install dependencies.

```powershell
python scripts/dev.py setup
python scripts/dev.py migrate
python scripts/dev.py seed
python scripts/dev.py demo
```

Before starting the demo, add `GEMINI_API_KEY` and `GROQ_API_KEY` to the root `.env`. See [LLM setup and failover](docs/LLM_SETUP.md). To follow the exact offline demo instead, set `SUBSTRATA_LLM_PROVIDER=mock`.

Open [the local workspace](http://127.0.0.1:3000), [API health](http://127.0.0.1:8000/health), [readiness](http://127.0.0.1:8000/ready), process metrics at `/metrics`, or [API documentation](http://127.0.0.1:8000/docs). `Ctrl+C` stops both servers. The documentation page uses FastAPI's default CDN assets; the workspace, `/health` and `/openapi.json` work offline after installation.

```json
{"status":"ok","service":"substrata-api","data_mode":"synthetic"}
```

`seed` creates or resets the deterministic synthetic scenario and the ignored SQLite database, including demo approvals and audit history. Stop servers before CLI reseeding. Normal schema upgrades use `migrate` and preserve data. Health reports process liveness; `/state` checks seeded workspace readiness. The UI fetches the API directly and receives live events through SSE.

Use **Discover links → Simulate supplier replies → Replay next event**, inspect the 18/90/72-day runway, enter a name and reason, approve a simulated draft, then verify the audit chain. [Exact click path and recovery](docs/DEMO_SCRIPT.md).

Run the current checks:

```powershell
python scripts/dev.py test
python scripts/dev.py lint
python scripts/dev.py build
python scripts/dev.py evaluate
```

`test` runs pytest and frontend type checking. `lint` checks Python lint/formatting and frontend ESLint. `build` exports the frontend to `frontend/out/`. The exported UI still requires the running FastAPI API. `evaluate` regenerates measured fixture results and persists the evaluation run; it does not train a model. Frontend dependency limitations are recorded in the [decision register](docs/DECISIONS.md#d006-static-frontend-scaffold).

## Individual services and local configuration

To run services separately, use these commands in separate terminals:

```powershell
python scripts/dev.py api
```

```powershell
python scripts/dev.py ui
```

Setup creates a root `.env` from `.env.example` when absent and preserves an existing file. Set `SUBSTRATA_API_PORT` / `SUBSTRATA_UI_PORT` there to change the default 8000 / 3000 ports; shell values take precedence. Both development and the static build use the configured API port; `NEXT_PUBLIC_API_URL` explicitly overrides the browser API URL and is embedded at build time. Rebuild after changing it. Stop running servers before rerunning setup. All commands after setup use `.venv` automatically.

The Makefile forwards the same tasks for GNU Make users. GNU Make is unavailable on this workstation, so those wrappers have not been locally executed; use the Python commands above. See the [scripts guide](scripts/README.md) for all tasks.

## Read this first: what do 18, 90 and 72 days mean?

These numbers describe a **synthetic supply-chain incident**, not our hackathon schedule. <sup>[Design]</sup>

| Number | Meaning in the business example |
|---:|---|
| **18 days** | Available stock and in-transit supply can support production for 18 days. <sup>[Design]</sup> |
| **90 days** | A replacement component is assumed to require 90 days to qualify. <sup>[Design]</sup> |
| **72 days** | The uncovered exposure period: `90 − 18 = 72 days`. <sup>[Design]</sup> |
| **30 days** | Time remaining to prepare for the hackathon; unrelated to the calculation above. |

The 90-day value is only a demonstration assumption. It must be replaced by the real qualification lead time for each component and company. <sup>[Assumption]</sup>

![Synthetic supply-chain runway timeline, separate from the hackathon schedule](docs/diagrams/02-runway-timeline.png)

*Figure 1 — A synthetic operational example: stock ends before an alternative is qualified. <sup>[Design]</sup>*

## The problem

Companies may believe that several Tier-1 suppliers give them diversification while those suppliers secretly depend on the same deeper manufacturer, facility, material, owner, region or route. <sup>[Design]</sup>

Available surveys indicate that deep-tier visibility remains difficult: one 2025 survey reported 95% visibility into Tier-1 risk but only 42% into Tier 2 or beyond; an older survey reported 15% visibility beyond Tier 1. These figures differ by year, population and wording and should not be directly compared as one benchmark. <sup>[[Sourced]](https://www.certaintysoftware.com/multi-tier-supply-chain-visibility/) [[Sourced]](https://www.sedex.com/blog/supply-chain-visibility-beyond-tier-1/)</sup>

![Several Tier-1 supplier wells drawing from one hidden Tier-N source](docs/diagrams/01-visibility-gap.png)

*Figure 2 — Three apparently independent suppliers can share one hidden upstream dependency. <sup>[Design]</sup>*

### Design question

> How might we help a supply-risk analyst discover and verify shared Tier-N dependencies early enough to protect production, without allowing uncertain AI inferences to trigger irreversible procurement actions? <sup>[Design]</sup>

## Proposed solution

Substrata follows a five-stage workflow. <sup>[Design]</sup>

| Stage | Proposed behavior |
|---|---|
| **Map** | Combine declared relationships, ERP-shaped records and public evidence to propose missing supplier links with confidence and provenance. |
| **Verify** | Keep links marked `inferred` until a supplier or analyst confirms or rejects them. |
| **Sense** | Match a replayed disruption event to affected graph nodes. |
| **Simulate** | Deterministically calculate affected components, plants, stock cover and exposure windows. |
| **Act safely** | Rank mitigation options, pause high-impact actions for a named approver and audit every decision. |

### What makes the idea different

1. **Inference that asks:** uncertain relationships create confirmation work instead of silently becoming truth. <sup>[Design]</sup>
2. **Runway instead of a generic risk score:** compare stock cover with the time required to qualify recovery. <sup>[Design]</sup>
3. **Governed action:** analysis may run automatically, while supplier switches, spend and real operational changes require human authority. <sup>[Design]</sup>

## Worked example

All values below are synthetic demonstration inputs, not Nexperia or customer data. <sup>[Design]</sup>

```text
on_hand                 = 1,200 units
in_transit              =   600 units
daily_consumption       =   100 units/day
requalification_days    =    90 days

cover_days = (1,200 + 600) / 100 = 18 days
exposure_window = 90 - 18 = 72 days
```

The exposure window means production cover ends 72 days before the alternative is ready. It does **not** predict that the hackathon or project will take 72 days. <sup>[Design]</sup>

![Synthetic cascade from a matched event to a deterministic impact report](docs/diagrams/09-cascade-simulation.png)

*Figure 3 — The graph identifies affected paths; deterministic code performs the calculation. <sup>[Design]</sup>*

## Hero scenario: October 2025 Nexperia disruption

The proposed demo replays public Nexperia events over an invented automotive network. It does not claim access to any manufacturer's private supplier graph, stock or revenue. <sup>[Design]</sup>

| Date | Public event | Demo purpose |
|---|---|---|
| 30 Sep 2025 | The Dutch government took control of Nexperia. <sup>[[Sourced]](https://blog.findchips.com/nexperia-supply-disruption/)</sup> | Initial disruption signal |
| 4 Oct 2025 | China restricted exports of Nexperia's China output. <sup>[[Sourced]](https://blog.findchips.com/nexperia-supply-disruption/)</sup> | Supply-risk escalation |
| 22 Oct 2025 | Reporting described Nexperia chips in Tier-1 components supplied by Bosch and Denso. <sup>[[Sourced]](https://news.dealershipguy.com/p/chipmaker-seizure-could-snarl-u-s-car-production-as-early-as-next-month-2025-10-22)</sup> | Hidden shared-dependency narrative |
| 28 Oct 2025 | ACEA said stocks could last only a few weeks while alternatives could take months to homologate. <sup>[[Sourced]](https://www.european-rubber-journal.com/article/2098231/acea-calls-for-immediate-resolution-to-critical-chip-supply-shortage)</sup> | Runway comparison |
| 29 Oct 2025 | Honda suspended production at a Mexico plant. <sup>[[Sourced]](https://blog.findchips.com/nexperia-supply-disruption/)</sup> | Public downstream consequence |

## Architecture at a glance

![Proposed Substrata system boundary](docs/diagrams/03-system-context.png)

*Figure 4 — Substrata sits between evidence sources and governed, simulated actions. SAP systems are integration targets, not existing connections. <sup>[Design]</sup> <sup>[TBD]</sup>*

| Layer | Proposed implementation |
|---|---|
| Data | Synthetic procurement, BOM, stock and lead-time records; declared links; replayed public events; simulated confirmations. <sup>[Design]</sup> |
| Persistence | SQLAlchemy and Alembic with PostgreSQL for the platform and SQLite WAL for the local demo. <sup>[Design]</sup> |
| Graph and impact | `GraphStore` with NetworkX and PostgreSQL traversal; deterministic services calculate exposure, runway and policy outcomes. SAP HANA Graph remains an entitlement-dependent stretch adapter. <sup>[Design]</sup> <sup>[TBD]</sup> |
| Orchestration | Typed Python workflows today; LangGraph is the selected next-step orchestrator. MCP and A2A expose bounded task/tool contracts. <sup>[Design]</sup> |
| Grounded assistance | A planned LangChain retrieval layer supports path-specific questions, exact citations and explicit known/inferred/unknown labels. <sup>[Design]</sup> |
| Pretrained AI gateway | Provider-neutral `LLMClient`; Google Gen AI SDK is the planned Gemini adapter, with Groq fallback and an offline mock. No custom LLM training or fine-tuning. <sup>[Design]</sup> |
| Experience | Next.js and TypeScript with Cytoscape.js; MapLibre is planned for geographic concentration views. FastAPI/Pydantic and SSE serve the current interface; WebSocket transport is planned. <sup>[Design]</sup> |
| Governed execution | Relationship confirmation, deterministic policy checks, named approval, SHA-256 audit history and SAP-shaped actions marked `simulated_only`. <sup>[Design]</sup> |

Detailed contracts and failure handling: [Architecture](docs/ARCHITECTURE.md).

## Agents and human control

![Agents collaborating through deterministic services and a human gate](docs/diagrams/05-agent-collaboration.png)

*Figure 5 — Language models may extract or explain; graph mathematics, policies and approval validity remain deterministic. <sup>[Design]</sup>*

| Agent or service | Responsibility | Escalation boundary |
|---|---|---|
| **Mapper** | Propose evidence-backed hidden links. | Low confidence, conflicting evidence or confirmation |
| **Sensor** | Classify events and resolve affected entities. | Ambiguous or conflicting event matches |
| **Relationship confirmation** | Keep inferred links as candidates until an analyst or supplier confirms or rejects them. | Missing evidence, conflicting responses or expired requests |
| **Domain assistant** <sup>[Planned]</sup> | Investigate one supply-chain path and return cited, evidence-grounded answers. | Clearly labels known, inferred and unknown information; cannot confirm links |
| **Deterministic impact engine** | Traverse the graph and calculate exposure, runway and policy outcomes. | Reports complete, incomplete or invalid calculations; does not improvise numbers |
| **Action** | Prepare and compare tool-returned mitigation drafts. | Spend, supplier switch, route risk or missing source data |
| **Compliance/Audit** | Apply rules and append provenance, decisions and approvals. | Policy conflict, missing approver or audit-chain failure |
| **Human gate** | Approve or reject high-impact actions with a recorded reason. | Rejection returns the proposal for review; approval creates only a dry-run action |

The prototype will not issue purchase orders, onboard suppliers or move real shipments. <sup>[Design]</sup>

## Models and training

Substrata does not train or fine-tune a generative model. Pretrained models are
accessed through a provider-neutral gateway for evidence extraction, explanation
and, in the planned grounded assistant, cited supply-path investigation. Typed
Python workflows coordinate the current platform; LangGraph is the selected
orchestration upgrade and LangChain is planned for grounded retrieval. Neither
framework performs exposure arithmetic or automatically turns an inferred link
into a confirmed fact.

Separately, administrators can train a small classical gradient-boosted link
scorer from reviewed supplier labels, with grouped holdouts, calibration and
explicit model activation. This scorer is not an LLM. Synthetic evaluation
establishes pipeline behavior, not customer accuracy.

![Substrata proposed technology map](docs/diagrams/12-tech-stack.png)

*Technology map — current components, selected next steps and optional adapters. Bracketed labels prevent planned technology from being presented as implemented. <sup>[Design]</sup>*

| Pretrained AI may assist with | Deterministic code remains responsible for |
|---|---|
| Name similarity and candidate retrieval | Entity identifiers and schema validation |
| Relationship extraction from evidence text | Graph traversal and path confidence |
| Event classification | Inventory, cover and exposure arithmetic |
| Rationale and message drafting | Policy, approval and audit rules |

LLM outputs must be structured JSON, validated against a schema and include evidence references for proposed links. <sup>[Design]</sup> A custom GNN is deliberately excluded from the finale scope. No accuracy figure will be claimed until it is measured; synthetic results will not be presented as real-world accuracy. <sup>[Design]</sup>

## Demo plan

The local prototype implements this synthetic six-stage replay. See the [three-minute click path](docs/DEMO_SCRIPT.md). A production/competition deployment remains a future decision. <sup>[Design]</sup>

1. Show three Tier-1 suppliers that appear independent.
2. Reveal their inferred shared Tier-N source and supporting evidence.
3. Replay the public disruption event.
4. Calculate affected components, 18-day cover and the synthetic 72-day exposure window.
5. Compare mitigation options.
6. Approve one simulated action and inspect its audit history.

![Proposed six-minute demo replay](docs/diagrams/10-demo-replay.png)

*Figure 6 — Seeded fixtures keep the judge demonstration reproducible and independent of internet access. <sup>[Design]</sup>*

## Evaluation plan

The [evaluation report](docs/EVALUATION.md#measured-synthetic-fixture-results) contains script-generated frozen-fixture measurements and raw errors. These do not establish held-out generalisation or real-world accuracy. Broader planned targets include:

| Area | Proposed target |
|---|---:|
| Entity retrieval | Recall@5 ≥ 0.90 <sup>[Design]</sup> |
| Hidden-link inference | Precision ≥ 0.80 and recall ≥ 0.70 on held-out synthetic edges <sup>[Design]</sup> |
| Deterministic impact calculations | 100% exact on hand-calculated fixtures <sup>[Design]</sup> |
| Policy safety | 100% of prohibited test actions blocked <sup>[Design]</sup> |
| Offline replay | 10/10 identical seeded runs <sup>[Design]</sup> |

These are targets, not results. Synthetic evaluation would show only that the method works on a constructed scenario; it would not prove equivalent performance on a real company's supply network. <sup>[Design]</sup>

Full protocol: [Evaluation plan](docs/EVALUATION.md).

## Finale preparation gates

The regional round evaluates structured ideas, and a working prototype is not mandatory. <sup>[[Sourced]](https://events.sap.com/in-hackfest-bangalore-2026/en_us/home.html)</sup>

| Gate | Priority | Intended output |
|---|---|---|
| **Plan** | Validate the decision and user | Two or three practitioner conversations; corrected empathy map, scenario and Business Model Canvas <sup>[Design]</sup> |
| **Design** | Freeze boundaries and contracts | Cited inference, confirmation, deterministic impact, policy, approval, audit and failure behavior <sup>[Design]</sup> |
| **Build** | Harden the smallest proof | Reproducible synthetic workflow, grounded assistant, optional read-only SAP adapter and offline fallback <sup>[Design]</sup> |
| **Test** | Validate quality and safety | Hidden-link evaluation, cited answers, exact calculations, policy controls, failure cases and rehearsals <sup>[Design]</sup> |

### How to use SAP Learning Hub

The [SAP Learning Hub student edition](https://learning.sap.com/students) is for learning SAP concepts and practice systems; using it does not itself mean Substrata is integrated with SAP. <sup>[Design]</sup>

Suggested focus areas are supply-chain planning, SAP Business Network, SAP BTP fundamentals, SAP HANA graph concepts, SAP AI Core/generative AI hub concepts and responsible AI. <sup>[Design]</sup> Course availability, practice-system access and event entitlements must be confirmed after sign-in. <sup>[TBD]</sup>

## Scope and safety

| Included in the proposed prototype | Explicitly excluded |
|---|---|
| Synthetic SAP-shaped business records | Production SAP or customer data |
| Evidence-backed inferred relationships | Claiming every hidden dependency can be discovered |
| Deterministic graph and runway calculations | LLM-generated graph mathematics |
| Replayed public event fixtures | Unbounded live web crawling |
| Ranked mitigation drafts and approval | Autonomous strategic sourcing or procurement |
| SAP-shaped local adapters | Representing stand-ins as real SAP transactions |

Key unresolved items include stakeholder validation, real data availability, source licensing, SAP finale entitlements, security controls, score calibration and the unresearched essential-medicines vertical. <sup>[TBD]</sup>

## Business design artifacts

- [Draft empathy map](docs/diagrams/15-empathy-map.png) — assumptions to replace after interviews. <sup>[Assumption]</sup>
- [Draft Business Model Canvas](docs/diagrams/16-business-model-canvas.png) — buyer, willingness to pay and data-sharing behavior remain unvalidated. <sup>[Assumption]</sup>
- [Autonomy matrix](docs/diagrams/06-autonomy-matrix.png) — proposed automatic, review-required and prohibited actions. <sup>[Design]</sup>
- [Technology map](docs/diagrams/12-tech-stack.png) and [deployment topology](docs/diagrams/13-deployment-topology.png) — all service availability remains subject to verification. <sup>[Design]</sup> <sup>[TBD]</sup>

## Documentation

| Document | Purpose |
|---|---|
| [Research](docs/RESEARCH.md) | Approved evidence, source caveats and open research |
| [Architecture](docs/ARCHITECTURE.md) | Layers, agent contracts, state machine and failure handling |
| [Data model](docs/DATA_MODEL.md) | Graph entities, relationships, provenance and persistence |
| [Tech stack](docs/TECH_STACK.md) | Proposed technologies, alternatives and SAP preflight checklist |
| [Evaluation](docs/EVALUATION.md) | Synthetic dataset, leakage controls, metrics and reporting template |
| [Build checklist](docs/BUILD_PLAN.md) | Small implementation checkpoints and current progress |
| [LLM setup](docs/LLM_SETUP.md) | Gemini/Groq credentials, failover and offline mode |
| [Decisions](docs/DECISIONS.md) | Implementation choices, assumptions and deferred work |
| [Judge Q&A](docs/JUDGE_QA.md) | Twelve candid answers for expected judge questions |
| [A-Z revision guide](output/pdf/substrata-a-to-z-revision-guide.pdf) | Fifteen-page project study guide, case study and judge question bank |
| [Diagram manifest](docs/diagrams/README.md) | Questions answered, editable sources and export notes |

## What is real versus planned?

| Item | Current status |
|---|---|
| Research, proposal and diagrams | Available in this repository <sup>[Design]</sup> |
| Stakeholder validation | Not completed <sup>[TBD]</sup> |
| Project folder scaffold | Created (M0.1) |
| Backend process health and OpenAPI contract | Implemented and tested (M0.2) |
| Interactive graph, replay, runway, approvals and audit UI | Implemented with direct API/SSE and static export; see current verification in the build checklist |
| Development commands and local configuration | Implemented and checked (M0.4); Makefile forwarding supplied, GNU Make execution unverified locally |
| Database connection, transactions and migration history | Implemented and checked (M1.1) |
| Graph entities, relationships and evidence provenance | Implemented with typed/versioned records, evidence citations and GraphStore API |
| Synthetic dataset and workflow | Implemented: fixed seed 42, separate truth/declared graphs, 32 nodes, seven evidence snippets and six events |
| Mapper and supplier replies | Provider-neutral `LLMClient` with Gemini primary, Groq fallback and an explicit offline mock. Google Gen AI SDK and Groq SDK adapters are planned; provider transport/failover is tested with simulated responses and live keys remain pending |
| Grounded domain assistant | Planned LangChain retrieval for path-specific questions with exact source citations and known/inferred/unknown labels |
| Agent orchestration | Typed Python workflows implemented; LangGraph selected but not yet presented as implemented |
| Action, approval and audit | Implemented simulated templates, stale-input checks and hash-chain verification; self-declared local roles |
| Generative-model training | No custom LLM training or fine-tuning; pretrained models remain behind the provider-neutral gateway <sup>[Design]</sup> |
| Classical link scorer | Implemented training/registry path from reviewed labels; reported separately from generative AI |
| SAP access and integration | Not confirmed <sup>[TBD]</sup> |
| Evaluation results | Generated by the evaluation script; frozen synthetic fixture only, not held-out generalisation or real business value |

## Key sources

- [SAP Hackfest Bengaluru 2026](https://events.sap.com/in-hackfest-bangalore-2026/en_us/home.html)
- [SAP Learning Hub, student edition](https://learning.sap.com/students)
- [SAP Supply Chain Orchestration announcement](https://news.sap.com/2025/10/sap-connect-innovative-updates-supply-chain-management/)
- [SAP guidance for building AI agents](https://architecture.learning.sap.com/docs/golden-path/ai-golden-path/build-and-deliver/build-ai-agents)
- [Cambridge Supply Chain AI Lab: link prediction](https://www.ifm.eng.cam.ac.uk/research/supply-chain-ai-lab/current-themes/supply-chain-link-prediction/)
- [ACEA: critical Nexperia chip supply shortage](https://www.acea.auto/press-release/acea-calls-for-quick-resolution-to-critical-chip-supply-shortage/)
- [UNCTAD Review of Maritime Transport 2022](https://unctad.org/system/files/official-document/rmt2022_en.pdf)
- [SAP Business Network: Multitier Order Collaboration](https://help.sap.com/docs/business-network-for-supply-chain/business-network-for-supply-chain-integration-and-configuration/multitier-order-collaboration-0d01b6d20b9042f4ac46c2ad2839d0ad)
- [SAP HANA Cloud Property Graph Engine](https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-database-property-graph-engine-reference/sap-hana-graph-data-model-030-000-000-sap_hana_graph_data_model)
- [SAP Clean Core Extensibility](https://help.sap.com/docs/erp-transformation-with-itc/buildable-map/clean-core-extensibility-for-sap-cloud-erp)
- [NIST Generative AI Risk Management Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)

See the [research register](docs/RESEARCH.md) for the complete approved source list and limitations.

---

**Name:** Substrata <sup>[Design]</sup> · **Tagline:** See what your suppliers secretly share. <sup>[Design]</sup> · **Team:** V-Max
