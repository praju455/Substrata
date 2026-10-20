# Research notes and approved evidence

> **Scope:** these are the only external sources approved for factual claims in this proposal. Product behavior is labelled **[Design]**, placeholder beliefs are **[Assumption]**, and unresolved facts are **[TBD]**.

## Evidence register

| ID | Evidence and note | Label |
|---|---|---|
| R1 | Secondary report of McKinsey Supply Chain Risk Pulse 2025: 95% Tier-1 visibility and 42% Tier-2+ visibility. Survey framing must accompany the figures. [Certainty](https://www.certaintysoftware.com/multi-tier-supply-chain-visibility/) | [Sourced] |
| R2 | Older Deloitte CPO figure: 15% report visibility beyond Tier 1. It is not directly comparable with R1. [Sedex](https://www.sedex.com/blog/supply-chain-visibility-beyond-tier-1/) | [Sourced] |
| R3 | Vendor estimate: roughly 70% lack accurate Tier 2–4 data; self-reported sub-tier information may be about 18 months stale. Treat as directional secondary evidence. [JAGGAER](https://www.jaggaer.com/blog/why-supply-chain-visibility-breaks-down-beyond-tier-1-in-2026) | [Sourced] |
| R4 | CSDDD, UFLPA and LkSG are presented as drivers for deeper-tier visibility; requirements and dates vary. [Certainty](https://www.certaintysoftware.com/multi-tier-supply-chain-visibility/) | [Sourced] |
| R5 | Nexperia chronology and Honda Mexico suspension. [Findchips](https://blog.findchips.com/nexperia-supply-disruption/) | [Sourced] |
| R6 | Nexperia chips were described as embedded in components supplied by Bosch and Denso; replacement certification can take weeks to months. [DealershipGuy](https://news.dealershipguy.com/p/chipmaker-seizure-could-snarl-u-s-car-production-as-early-as-next-month-2025-10-22) | [Sourced] |
| R7 | ACEA described stocks as lasting a few weeks and alternative homologation/build-up as taking several months. [ACEA](https://www.acea.auto/press-release/acea-calls-for-quick-resolution-to-critical-chip-supply-shortage/) | [Sourced] |
| R8 | SAP announced Supply Chain Orchestration around early detection, multi-tier context, impact analysis and prioritized action using Business Network and Business Data Cloud data. [SAP News](https://news.sap.com/2025/10/sap-connect-innovative-updates-supply-chain-management/) | [Sourced] |
| R9 | SAP documents pro-code agents, SAP Cloud SDK for AI, Generative AI Hub, HANA Cloud Vector and Knowledge Graph engines, MCP tools and A2A/Joule integration. [SAP Architecture Center](https://architecture.learning.sap.com/docs/golden-path/ai-golden-path/build-and-deliver/build-ai-agents) | [Sourced] |
| R10 | Cambridge Supply Chain AI Lab describes supply-network reconstruction, NLP, link prediction, knowledge graphs and GNN research for hidden dependencies. [Cambridge IfM](https://www.ifm.eng.cam.ac.uk/research/supply-chain-ai-lab/current-themes/supply-chain-link-prediction/) | [Sourced] |
| R11 | Exploratory research combines language-model embeddings and knowledge-graph link prediction. It is prior research, not evidence that this proposal will achieve similar performance. [arXiv:2412.03390](https://arxiv.org/abs/2412.03390) | [Sourced] |
| R12 | A 2025 graph-language paper reports supply-relation identification results on a proprietary dataset; its metrics are not transferable to our synthetic evaluation. [arXiv:2510.09735](https://arxiv.org/abs/2510.09735) | [Sourced] |
| R13 | Neutral market overview of Prewave, Resilinc, Everstream and Sphera. Vendor capabilities must not be reduced to claims of absence. [Suplari](https://suplari.com/blog/supplier-risk-management-solutions-compared-standalone-risk-tools-vs-spend-integrated-platforms) | [Sourced] |
| R14 | Meridian is an adjacent open-source supply-chain risk intelligence project. [GitHub](https://github.com/askmy-stack/meridian) | [Sourced] |
| R15 | Regional round evaluates ideas; a prototype is optional; finale requires a working prototype using SAP technologies at NHCE on 4 November 2026. [SAP Hackfest](https://events.sap.com/in-hackfest-bangalore-2026/en_us/home.html) | [Sourced] |
| R16 | More than 80% of world merchandise trade by volume is carried by sea, which supports the route/chokepoint context without making Substrata maritime-only. [UNCTAD Review of Maritime Transport](https://unctad.org/system/files/official-document/rmt2022_en.pdf) | [Sourced] |
| R17 | SAP Business Network documents multitier order collaboration. This supports positioning Substrata as complementary evidence, runway and governance rather than claiming SAP lacks multitier capability. [SAP Help](https://help.sap.com/docs/business-network-for-supply-chain/business-network-for-supply-chain-integration-and-configuration/multitier-order-collaboration-0d01b6d20b9042f4ac46c2ad2839d0ad) | [Sourced] |
| R18 | SAP HANA Cloud provides a property graph engine suitable for graph-shaped dependency data when the required service and entitlement are available. [SAP Help](https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-database-property-graph-engine-reference/sap-hana-graph-data-model-030-000-000-sap_hana_graph_data_model) | [Sourced] |
| R19 | SAP clean-core guidance supports API-first, side-by-side extensibility rather than modifying the ERP core. [SAP Help](https://help.sap.com/docs/erp-transformation-with-itc/buildable-map/clean-core-extensibility-for-sap-cloud-erp) | [Sourced] |
| R20 | NIST's Generative AI risk profile supports explicit evidence, validation, human oversight and monitoring controls for generative AI use. [NIST AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | [Sourced] |

## Research interpretation

1. Survey percentages are evidence of a visibility problem, not a universal baseline. <sup>[Design]</sup>
2. The Nexperia case motivates the demo but does not reveal any company's private supplier graph or inventory. <sup>[Design]</sup>
3. Link prediction is technically plausible enough to evaluate, but no research metric is adopted as a promised product result. <sup>[Design]</sup>
4. Existing SAP and specialist platforms already address multi-tier visibility, risk and orchestration in different ways. Substrata is positioned as a hackathon exploration of confidence-to-confirmation and runway, not as proof of missing capability. <sup>[Design]</sup>
5. No model training is planned for the core system; pretrained models and deterministic code will be evaluated as components. <sup>[Design]</sup>

## Open research items

| Item | Why it remains open | Status |
|---|---|---|
| Interview 2–3 procurement or supply-planning practitioners | Validate workflow, thresholds, explanations and approval boundaries | [TBD] |
| Research essential-medicines raw-material dependency scenario | Second vertical currently has no approved evidence pack | [TBD] |
| Confirm SAP environment and entitlements supplied at the finale | Determines HANA, Generative AI Hub, Joule and BTP deployment scope | [TBD] |
| Confirm Nexperia chronology against primary government/company records | Current approved links are secondary reporting | [TBD] |
| Validate independence assumptions behind noisy-OR | Candidate inference paths may share evidence | [TBD] |
