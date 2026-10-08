# Judge Q&A

> Short, honest answers for the regional proposal. Anything not built or measured remains labelled. **[Design]**

## 1. What problem does Substrata solve?

It addresses false diversification: several direct suppliers can appear independent while sharing one deeper supplier, site, material, owner, region or route. **[Design]** It is proposed to surface that evidence, calculate decision runway and prepare a governed response. **[Design]**

## 2. How is this different from Resilinc, Prewave, Everstream, Sphera or SAP's orchestration?

We are not claiming they lack a feature or that Substrata is broader. **[Design]** The hackathon thesis is deliberately narrow: traceable candidate-link inference, a supplier/analyst confirmation loop, deterministic stock-cover-versus-requalification runway and a visible human approval gate. **[Design]** [SAP itself has announced multi-tier insight, impact analysis and prioritized action](https://news.sap.com/2025/10/sap-connect-innovative-updates-supply-chain-management/); Substrata is positioned as a complementary experiment. **[Sourced]**

## 3. Where does Tier-N data come from?

In the prototype: synthetic ERP-shaped records, declared synthetic relationships, replayed public events/ownership context and simulated supplier confirmations. **[Design]** In a real deployment, usable sources, permissions, refresh rates and supplier participation would have to be negotiated and validated. **[TBD]**

## 4. What if an inferred link is wrong?

The design never equates `inferred` with `confirmed`. **[Design]** The edge retains evidence, confidence and score components; conflicting/low-confidence cases go to review; negative confirmation is stored; cascade outputs identify inferred exposure. **[Design]** A wrong link can still cause wasted attention, which is why precision and reviewer burden are evaluation criteria. **[Design]**

## 5. Why agents instead of a dashboard?

The proposed work crosses evidence extraction, event sensing, deterministic simulation, option drafting and governance, each with different tools and escalation rules. **[Design]** Agent boundaries make those responsibilities inspectable. **[Design]** If LangGraph/A2A does not improve pause/resume, tool control or auditability over a plain state machine, we should remove it. **[Design]**

## 6. What is real today and what is simulated?

Real today: the proposal, sources, specifications and editable diagrams. **[Design]** Planned/simulated: the full application, every supplier/stock/BOM record, confirmations, impacts, action payloads and SAP-shaped adapters. **[Design]** There is no live SAP integration, customer validation or measured result. **[Design]**

## 7. Did you train a model?

No. This is deliberate: the core hypothesis can be tested with pretrained LLMs/embeddings for retrieval and structured extraction, while graph math and policy remain deterministic. **[Design]** Training a bespoke model before establishing a legitimate dataset and baseline would add risk without proving user value. **[Design]** A GNN is optional, trained on synthetic data only and reported as a separate baseline. **[Design]**

## 8. Is the accuracy proven on real data?

No. There is no measured accuracy yet, and the planned first evaluation is synthetic. **[Design]** Targets are not results. **[Design]** Synthetic evaluation can test implementation and method behavior on a constructed scenario; it cannot establish real-world performance. **[Design]**

## 9. How does confidence work?

The first proposal is a versioned combination of documented deterministic and pretrained-model signals, with caps against double-counting correlated evidence. **[Design]** It is a review score until calibration is demonstrated; weights and thresholds are **[TBD]**. Path confidence is deterministic multiplication of edge scores, with noisy-OR for multiple candidate paths as a starting design. **[Design]**

## 10. Why use the Nexperia crisis?

The public October 2025 chronology gives judges a dated, understandable disruption sequence and illustrates the reported time mismatch between [limited stocks and alternative homologation](https://www.european-rubber-journal.com/article/2098231/acea-calls-for-immediate-resolution-to-critical-chip-supply-shortage). **[Sourced]** It does not reveal a real confidential graph. **[Design]** Substrata overlays that chronology on a synthetic network and states that limitation on-screen. **[Design]**

## 11. Can the system act automatically?

Only low-risk, reversible analysis tasks are proposed as automatic. **[Design]** Supplier contact, inventory transfer, expedite and sourcing proposals require a configured human gate; purchase-order changes, onboarding and real shipment moves are prohibited in the prototype. **[Design]** The spend limit is a configuration placeholder, not a validated business rule. **[Assumption]**

## 12. Why SAP and what happens without SAP access?

The workflow naturally touches procurement, BOM, inventory, planning and supplier-network data, and SAP publishes relevant [supply-chain](https://news.sap.com/2025/10/sap-connect-innovative-updates-supply-chain-management/) and [agent architecture](https://architecture.learning.sap.com/docs/golden-path/ai-golden-path/build-and-deliver/build-ai-agents) direction. **[Sourced]** The core demo runs on local interfaces and synthetic fixtures; HANA, generative AI hub, BTP and Joule/A2A are entitlement-dependent stretches. **[Design]** **[TBD]**

## Follow-up evidence to keep ready

- [Research register](RESEARCH.md) for every sourced fact.
- [Architecture](ARCHITECTURE.md) for boundaries and failure behavior.
- [Data model](DATA_MODEL.md) for status/provenance fields.
- [Evaluation](EVALUATION.md) for targets, leakage controls and the synthetic limitation.
- [Diagram manifest](diagrams/README.md) for editable sources and visual questions.
