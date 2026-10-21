# Substrata: SAP Hackfest Regional Idea Pitch Handoff

This handoff maps Substrata to every slide in the official 11-slide regional-round template. It is written for a 10-minute pitch and separates short on-slide copy from the explanation the presenter should give aloud.

## 1. Use this handoff correctly

- Keep the project name **Substrata**.
- Replace every square-bracket placeholder for team details or completed SAP learning before submission.
- Keep the words **synthetic**, **simulated**, **proposed**, and **target** wherever they appear. They prevent the pitch from claiming evidence that the team does not have.
- Do not say that Substrata is connected to a live SAP system. The current product uses synthetic SAP-shaped data and read-only adapter patterns. SAP BTP, SAP HANA graph/vector, SAP Business Network, SAP S/4HANA, SAP AI Core, and Joule/A2A are integration targets subject to access and entitlement.
- Do not say that an LLM calculates supply-chain impact. LLMs only assist with evidence extraction, event classification, and drafting. Deterministic Python code performs graph traversal, stock-cover arithmetic, policy checks, and audit verification.
- Do not claim real-world accuracy, ROI, cost savings, customers, or deployed procurement actions. The current measurements come from a constructed synthetic fixture.
- The **18, 90, and 72 days** are business-scenario assumptions, not a hackathon schedule.
- The core system does not fine-tune an LLM or train a GNN. The broader platform contains an optional, separately governed gradient-boosted link scorer trained from reviewed labels. Keep this out of the main pitch unless a judge asks.

## 2. Ten-minute narrative

| Time | Slides | Narrative job |
|---:|---|---|
| 0:00-0:35 | 1-2 | Introduce Substrata, the team, and the one-line purpose. |
| 0:35-2:05 | 3-4 | Explain false diversification, the user, and the current decision gap. |
| 2:05-4:15 | 5 | Explain how evidence becomes a verified link, deterministic runway, and a governed response. |
| 4:15-5:35 | 6 | Show the implemented stack, the SAP fit, and what the team learned rather than claiming a live SAP integration. |
| 5:35-7:10 | 7 | Define impact, success measures, assumptions, and risks. |
| 7:10-8:35 | 8 | Show a feasible finale plan built around the smallest credible proof. |
| 8:35-9:35 | 9 | Close with why the idea should advance and show the evidence sources. |
| 9:35-10:00 | 10 | Invite questions. |
| Internal | 11 | Complete the submission checklist; do not present this as content. |

## 3. Slide-by-slide content

### Slide 1: Event cover

**Template heading:** Hackfest 2026, Regional College Round, Idea Pitch

**Action:** Keep the official event cover unchanged. Do not place product content over sponsor or partner marks.

**Optional addition, only if the template allows it:** Add a small line below “Idea Pitch” without moving the official logos:

> **Theme: Resilient Supply Chains**<br>
> **Idea: Hidden Tier-N Supplier Dependency AI**

This slide should remain visually light. The audience only needs the event, theme, and project context before the project title appears on slide 2.

**Presenter opening:**

> Good morning. We are presenting Substrata under the Resilient Supply Chains theme. Substrata helps a manufacturer see when apparently independent suppliers share the same hidden upstream dependency, calculate how long remains before production is exposed, and prepare a governed response.

### Slide 2: Project and team

**Project / Idea Name**

> **Substrata**<br>
> *See what your suppliers secretly share.*

**Team Name**

> [TEAM NAME]

**Team Members**

> 1. [NAME - role in this project]<br>
> 2. [NAME - role in this project]<br>
> 3. [NAME - role in this project]<br>
> 4. [NAME - role in this project]<br>
> 5. [NAME - role in this project, only if applicable]

**Department / Semester**

> [DEPARTMENT] | [SEMESTER]

**Small footer line, if space permits**

> Agentic early warning for hidden Tier-N supply dependencies.

**Expanded project description for the slide or speaker notes**

> Substrata helps manufacturers discover when apparently independent suppliers share the same hidden upstream dependency. It combines cited relationship evidence with a versioned supply graph, calculates how long production remains protected after a disruption, and prepares simulated mitigation options under human approval.

**Suggested team capability line**

> Supply-chain research | Knowledge graphs | Agentic AI | Deterministic simulation | Governed decision workflow

Replace the capability line with four or five real responsibilities if the template has enough space. It should show why the team can take the idea from business research to a working prototype.

**Presenter note:** Do not spend time listing technologies here. Give each person a responsibility such as research and business design, data and graph, backend and AI, frontend and experience, or testing and presentation.

### Slide 3: Problem and theme

**Template heading:** What problem are you solving?

**Selected theme**

> **Resilient Supply Chains**

**Problem statement, 2-3 sentences**

> Manufacturers can see their direct Tier-1 suppliers, yet several of those suppliers may rely on the same deeper supplier, site, material, owner, region, or route. A disruption at that hidden Tier-N node can disable multiple supposedly independent supply paths at once. Evidence is fragmented, so planners may discover the concentration only after stock is already running out.

**Expanded problem statement, use this while building the slide and shorten later if required**

> Enterprise procurement data gives manufacturers a strong view of the suppliers with whom they contract directly. It does not always reveal the deeper facilities, component makers, parent organisations, raw materials, regions, or transport routes shared by those suppliers. As a result, several Tier-1 suppliers can look diversified while their upstream paths converge on one Tier-N source.
>
> When that shared source is disrupted, multiple direct suppliers can fail together. The supply-risk analyst must then verify whether the relationship is credible, identify which components and plants are affected, calculate how long current inventory will last, compare recovery options, and escalate the decision to the correct approver. Those inputs often sit across different systems, documents, and teams.

**Who experiences the problem?**

> Supply-risk analysts, procurement teams, plant planners, and the managers who approve mitigation decisions.

**When and where does it occur?**

> During supplier onboarding, periodic risk reviews, and fast-moving disruptions, especially when Tier-N relationships are split across ERP records, documents, news, and supplier responses.

**Concrete example**

> In our synthetic automotive scenario, three Tier-1 supplier groups appear independent but share one deeper semiconductor source. A replayed disruption exposes the common point of failure.

**Why the problem occurs**

- Direct contracts reveal the Tier-1 relationship but may not reveal the complete sub-tier path.
- Supplier names, subsidiaries, facilities, and parent organisations can appear differently across sources.
- Relationship evidence, BOM data, inventory, lead time, and disruption signals live in separate records.
- Supplier networks change, so an old relationship map can create false confidence.
- A generic risk score does not show which plant is affected first or how much decision time remains.

**Failure modes to mention during the pitch**

| Failure | Consequence |
|---|---|
| Shared Tier-N source remains hidden | Several supplier paths fail at the same time. |
| Weak evidence is treated as fact | The team investigates or mitigates the wrong dependency. |
| Event is detected without a where-used path | The affected component, product, or plant remains unclear. |
| Stock cover is not compared with recovery time | The team knows there is risk but cannot judge urgency. |
| Recommendation lacks an approval boundary | A draft may exceed authority, budget, or policy. |

**Visual placement**

Use the hidden-dependency diagram on the right half or across the lower 40% of the slide. Crop the outer whitespace, but do not remove the words “Mapper agent confidence” or “Supplier confirms or rejects link.”

![Hidden shared Tier-N dependency](diagrams/01-visibility-gap.png)

**What to say**

> The failure is not simply that data is missing. The dangerous failure is false diversification. Three contracts look like three independent options, but the graph beneath them may contain only one real source. Substrata treats that relationship as a claim with evidence and confidence, then asks for verification rather than silently declaring it true.

**Truth note:** The suppliers and network shown are invented. The problem framing is inspired by public supply disruption reporting, but Substrata does not claim access to any company's private supplier graph.

### Slide 4: Users and current gap

**Template heading:** Who needs this solution, and why?

#### Target users

> **Primary:** supply-risk analyst or supply planner<br>
> Needs traceable evidence, affected plants/components, and clear decision time.<br>
> **Secondary:** procurement approver<br>
> Needs exact options, assumptions, cost/risk context, and an accountable approval record.<br>
> **Participant:** supplier contact<br>
> Confirms or rejects an uncertain relationship through a bounded request.

**Expanded user needs**

| User | Main decision | Information required | Current pain hypothesis |
|---|---|---|---|
| Supply-risk analyst | Is this hidden dependency credible and material? | Evidence passage, relationship status, path, confidence, affected scope | Reconciles fragmented records and must explain uncertain links |
| Supply planner | When will production become exposed? | Inventory, incoming supply, consumption, qualification time, affected plant | Risk alerts do not always translate into a decision deadline |
| Procurement approver | Which response is justified and within authority? | Options, cost and timing assumptions, policy reason, requested action | Context is split across analysis, meetings, and approval tools |
| Supplier contact | Is the proposed relationship correct? | Narrow claim, source context, response deadline, permitted use | Broad questionnaires create effort and confidentiality concerns |

#### Current approach

> Teams often reconcile direct-supplier records, spreadsheets, documents, alerts, and calls manually. A conventional Tier-1 view can show who has a contract without revealing the upstream dependency shared by multiple contracts. Analysis and approval are separated, so the reason for a decision may be difficult to reconstruct later.

**Expanded current workflow hypothesis**

1. An analyst receives an alert, report, news item, or supplier message.
2. The analyst searches vendor records and spreadsheets for matching names.
3. Procurement asks internal owners or suppliers to validate the relationship.
4. Planning gathers inventory and consumption information.
5. Engineering or sourcing estimates the time required for an alternative.
6. The team compares options in meetings or separate files.
7. A manager approves an action through an existing process.
8. The evidence, assumptions, and approval reason may remain distributed across systems.

This workflow must be validated through stakeholder interviews. Present it as the team’s current understanding, not as a universal description of every manufacturer.

#### Opportunity

> Join evidence and supply relationships in a versioned knowledge graph, keep uncertain links visibly inferred, ask humans or suppliers to confirm them, and calculate decision runway before recommending a response. The result is earlier attention with less false certainty.

**Expanded opportunity statement**

> Substrata can create one traceable decision chain. A relationship starts as a cited proposal, moves through confirmation or rejection, enters a versioned impact calculation, produces a clear runway, and results in a governed action draft. The analyst spends less time assembling context and more time judging the evidence and response.

**Concrete scenario to place under the three boxes**

> **Synthetic example:** 1,800 units available at 100 units/day gives 18 days of cover. A replacement takes an assumed 90 days to qualify, leaving a 72-day exposure window.

**Business model sentence for this slide**

> Proposed buyer: a manufacturer or supply-risk function. Proposed value: evidence-backed hidden-dependency discovery, decision runway, and governed response. Subscription and implementation pricing remain unvalidated assumptions.

**Expanded business model hypothesis**

- **Primary user:** supply-risk analyst or supply planner.
- **Economic buyer:** procurement, supply-chain, or enterprise-risk leadership. This must be validated.
- **Value proposition:** reveal shared upstream concentration, quantify the decision window, and preserve accountability.
- **Delivery model:** enterprise web application integrated with approved planning and supplier data.
- **Potential revenue:** subscription plus implementation and support. No price or willingness-to-pay claim has been validated.
- **Key adoption risk:** analysts may distrust inferred relationships or receive too many low-quality review requests.
- **Validation priority:** confirm whether the runway view changes a real sourcing, inventory, or escalation decision.

**Optional Q&A visual:** The full empathy map is a draft, not interview evidence. Use it only as a backup slide or when the judges ask about design thinking.

![Draft supply-risk analyst empathy map](diagrams/15-empathy-map.png)

**What to say**

> Our primary persona is not asking for another red risk score. The analyst asks three practical questions: Is this relationship credible? Which plant is affected first? Who is authorized to act? The current empathy map is explicitly a hypothesis that we must correct through stakeholder interviews.

### Slide 5: Proposed solution

**Template heading:** How will your idea work?

#### Solution summary

> Substrata combines supplier records and cited evidence to propose missing Tier-N relationships, then keeps them marked as inferred until a supplier or analyst confirms or rejects them. When a disruption is sensed, deterministic graph code traces the impact to components and plants, calculates remaining runway, compares simulated mitigations, and pauses high-stakes decisions for a named human approver.

#### Key differentiator

> Substrata connects **evidence to confirmation, confirmation to runway, and runway to governed action**. It does not let uncertain AI output become supply-chain truth or allow an LLM to perform the impact arithmetic.

#### User journey / solution flow

Use the four template boxes exactly as follows:

| Template box | Paste this content |
|---|---|
| **Input** | ERP-shaped supplier, BOM, inventory and lead-time records; documents; declared links; disruption event |
| **Analyse / Decide** | Mapper proposes cited links; supplier/analyst verifies; Sensor matches the event; the deterministic impact engine traces exposure and runway |
| **Action** | Compare buffer, expedite, transfer, or alternate-qualification drafts; policy chooses allow, review, or block |
| **Outcome** | Earlier warning, explicit uncertainty, named approval, simulated SAP-shaped payload, verifiable audit trail |

**Expanded five-stage operating model**

1. **Map:** Load supplier, purchasing, BOM, plant, inventory, lead-time, declared-relationship, and evidence records. Keep legal entities, supplier sites, components, products, and plants distinct.
2. **Infer and verify:** The Mapper extracts relationship claims into a strict schema and attaches exact evidence. The graph stores the result as `inferred`. A supplier or analyst can confirm, reject, or allow the claim to expire.
3. **Sense:** The Sensor receives a sourced disruption event, classifies it, and proposes affected graph entities. Ambiguous matches wait for analyst review.
4. **Simulate:** Deterministic Python services traverse a pinned graph, find affected paths, calculate stock cover, compare it with qualification time, and return complete, incomplete, or truncated results.
5. **Act safely:** The Action role prepares dry-run mitigation options. Policy checks the action, actor, threshold, graph version, and expiry. High-impact options pause for a named human, and the final decision enters the audit chain.

**Detailed flow for building the slide**

| Stage | Data or request | System output | Human responsibility |
|---|---|---|---|
| Discover | Supplier records and documents | Cited inferred relationship | Review ambiguity and unsupported claims |
| Confirm | Inferred relationship | Confirmed, rejected, or expired status | Supplier or analyst responds |
| Detect | Sourced event | Matched entity or review candidates | Resolve unclear matches |
| Calculate | Pinned graph, BOM, stock, consumption, lead time | Affected paths, cover, exposure, uncertainty | Inspect assumptions and missing data |
| Compare | Impact report and sourced option inputs | Ranked simulated mitigation drafts | Judge business feasibility |
| Govern | Draft, actor, policy, versions | Allow, review, block, approve, or reject | Named approver records a reason |
| Audit | Frozen decision context | Verifiable history and report | Reviewer verifies integrity |

**Architecture sentence beneath the flow**

> Data and evidence feed a versioned graph; bounded agents call deterministic tools; policy and a human gate control all high-impact actions.

**Preferred visual for presenter notes or backup:**

![Agent collaboration and human approval gate](diagrams/05-agent-collaboration.png)

**Optional visual if the slide can replace the four-box flow without becoming crowded:**

![Substrata system context](diagrams/03-system-context.png)

**Worked calculation to explain aloud**

```text
cover_days = (on_hand + in_transit) / daily_use
           = (1,200 + 600) / 100
           = 18 days

exposure_window = qualification_days - cover_days
                = 90 - 18
                = 72 days
```

> A positive exposure window means stock cover ends before an alternative is ready. It is not a prediction that the project takes 72 days.

**What is agentic here?**

- **Mapper:** proposes evidence-backed hidden links.
- **Sensor:** classifies a disruption and resolves affected entities.
- **Deterministic impact engine:** performs graph traversal, exposure, runway, and policy calculations without improvising numbers.
- **Action:** prepares and compares mitigation drafts.
- **Compliance/Audit:** applies policy and records provenance.
- **Human gate:** approves or rejects high-impact actions with a reason.

**Why this approach is different**

- An AI-generated relationship remains a proposal with evidence and status.
- Supplier or analyst confirmation becomes part of the graph rather than a separate email outcome.
- Urgency is expressed through stock cover versus recovery time rather than only a risk category.
- Graph paths and arithmetic remain reproducible because deterministic services own them.
- The system prepares actions but does not remove human authority for consequential decisions.
- Every approval keeps the exact graph, data, formula, policy, actor, and reason used at that time.

**Longer solution summary if the template allows more text**

> Substrata builds a versioned supplier knowledge graph from enterprise records, declared relationships, and cited evidence. Pretrained AI helps extract possible hidden links, but the system stores them as inferred until a supplier or analyst verifies them. When a disruption is matched, deterministic services trace the affected components and plants, calculate decision runway, and prepare mitigation drafts. Policy blocks unsafe actions and routes high-impact decisions to a named human approver, while a hash-chained audit record preserves the decision context.

### Slide 6: SAP technology and learning

**Template heading:** Where do SAP technologies fit?

This slide must distinguish the **working local prototype** from the **SAP-aligned finale path**.

#### Left box: Technology / concept

> **Current prototype**<br>
> Next.js + TypeScript + Cytoscape.js interface<br>
> FastAPI + Pydantic service layer<br>
> NetworkX deterministic graph analysis<br>
> SQLAlchemy + Alembic with SQLite/PostgreSQL<br>
> Provider-neutral pretrained AI gateway; Google Gen AI SDK for the cited assistant, with Groq fallback and an offline mock<br>
> SSE updates, human approval, and SHA-256 audit chain

> **SAP-aligned integration path, subject to access**<br>
> Read-only SAP S/4HANA procurement, BOM, inventory, and lead-time data<br>
> SAP Business Network / Ariba supplier relationships<br>
> SAP BTP deployment and integration<br>
> SAP HANA Cloud graph/vector services<br>
> SAP AI Core generative AI hub and Joule/A2A as optional adapters

#### Right box: Learning Hub connection

> **Concepts applied**<br>
> End-to-end supply-chain process thinking<br>
> Master data, procurement, BOM, inventory, and planning context<br>
> Clean-core extension and API-first integration<br>
> Responsible AI, human oversight, traceability, and governed automation

> **Before submission**<br>
> Replace this line with the exact SAP Learning Hub course or learning journey completed by each team member: [COURSE / JOURNEY NAME]. Do not claim course completion until it is visible in the learner account.

#### Answer the template prompts

- **Information and process SAP would support:** supplier master, purchasing data, BOM where-used, plant stock, lead times, planning context, approval workflow, and supplier collaboration.
- **Where AI adds value:** extracting relationship claims from text, suggesting entity matches, classifying events, and drafting explanations.
- **Where deterministic logic remains:** graph paths, impact ranges, stock cover, policy checks, approval validity, and audit hashing.

**Expanded SAP process mapping**

| Substrata requirement | Relevant SAP process or concept | Proposed role in the solution | Current status |
|---|---|---|---|
| Supplier and purchasing context | SAP S/4HANA procurement | Read approved vendor, purchasing, material, and plant fields | Synthetic local records and read-only adapter contracts |
| Component where-used analysis | BOM and production-planning concepts | Trace disrupted material to products and consuming plants | Implemented on the synthetic graph |
| Stock and recovery planning | Inventory and SAP IBP concepts | Compare stock cover, eligible arrivals, and recovery time | Deterministic local calculation |
| Multi-tier supplier context | SAP Business Network / Ariba concepts | Add declared supplier relationships and support confirmation | Local stand-in and explicit adapter stub |
| Extension and integration | SAP BTP | Host or integrate Substrata without replacing the system of record | Future deployment target |
| Graph and semantic retrieval | SAP HANA Cloud graph/vector concepts | Replace local adapters if the service is available and suitable | Entitlement-dependent stretch |
| Governed pretrained AI | SAP AI Core generative AI hub | Supply a managed model-access adapter for structured extraction | Current demo uses Gemini, Groq, or mock |
| Enterprise assistant interoperability | Joule and A2A concepts | Invoke a bounded assessment or retrieve a result | Local A2A-style endpoint; Joule not verified |

**Current implementation versus future SAP integration**

| Concern | Current prototype | SAP-aligned future path |
|---|---|---|
| Data | Synthetic fixtures, file imports, local connector mock | Customer-authorized read-only SAP interfaces |
| Graph | Versioned relational records and NetworkX | SAP HANA graph adapter if available |
| AI | Provider-neutral extraction `LLMClient`; Google Gen AI SDK/Groq assistant adapters and offline mocks | SAP generative AI hub adapter if entitled |
| Deployment | Local Python and Next.js; Docker/PostgreSQL platform path | SAP BTP after account and service verification |
| Action | Simulated SAP-shaped draft | Controlled external adapter after approval and production safeguards |

**Learning Hub content to complete before submission**

| Team member | Exact completed resource | Concept applied in Substrata |
|---|---|---|
| [NAME] | [EXACT COURSE OR JOURNEY] | [EXAMPLE: procurement data or planning process] |
| [NAME] | [EXACT COURSE OR JOURNEY] | [EXAMPLE: BTP extension or integration] |
| [NAME] | [EXACT COURSE OR JOURNEY] | [EXAMPLE: responsible AI or agents] |
| [NAME] | [EXACT COURSE OR JOURNEY] | [EXAMPLE: graph, analytics, or business process] |
| [NAME, IF APPLICABLE] | [EXACT COURSE OR JOURNEY] | [CONCEPT APPLIED] |

**Expanded Learning Hub explanation**

> The team should connect learning to a design decision. Supply-chain process learning explains which records and approvals matter. BTP and clean-core concepts support a read-only extension boundary. Responsible-AI learning supports evidence citations, uncertainty labels, human oversight, and auditability. The slide should name only the courses or learning journeys the team actually completed.

**Visual placement:** If space permits, place the technology map as a narrow lower band. Add a caption: “Current local stack plus entitlement-dependent SAP adapters.” The existing image says “proposed”; keep that word visible.

![Substrata technology map](diagrams/12-tech-stack.png)

**Important correction to the diagram:** typed Python workflows remain the core platform path. LangGraph and LangChain are implemented for the read-only cited domain assistant, Google Gen AI SDK is its optional Gemini adapter, and Tavily is optional public-web retrieval. MapLibre, SAP HANA graph, and SAP generative AI hub remain planned or entitlement-dependent; none should be presented as implemented.

**What to say**

> We are not using SAP's name as decoration. The workflow naturally consumes procurement, BOM, inventory, planning, and supplier-network information. Our current prototype proves the decision flow locally. If the finale provides the required services, the same interfaces can be connected to SAP data and AI services without moving graph mathematics into a language model.

### Slide 7: Impact and validation

**Template heading:** How will you know it works?

#### Expected impact

> Surface common upstream dependencies before a Tier-1-only view would.<br>
> Express urgency as decision runway rather than a vague risk score.<br>
> Reduce false certainty by separating inferred, confirmed, rejected, and expired links.<br>
> Make every proposed action reviewable through evidence, versions, approver, reason, and audit history.

**Expanded expected-benefit chain**

| Capability | Immediate result | Expected benefit | Important limitation |
|---|---|---|---|
| Hidden-link discovery | Cited relationship proposal | Earlier investigation of shared concentration | Proposal may be wrong until verified |
| Confirmation workflow | Confirmed or rejected link state | Less false certainty in the graph | Requires supplier or analyst participation |
| Deterministic impact analysis | Affected paths, components, products, and plants | Faster impact scoping | Depends on graph completeness and correct units |
| Runway calculation | Cover, qualification time, and exposure | Clearer urgency and escalation timing | Inputs may be assumptions or ranges |
| Mitigation comparison | Dry-run options with time, cost, and risk context | Faster preparation for a decision | Does not prove an option can be executed |
| Policy and approval | Allow, review, block, approve, or reject | Reduced risk of unauthorized action | Policy must match the organisation’s authority model |
| Audit chain | Frozen decision context | Better traceability and post-event review | Integrity does not prove the original source was true |

#### Success measures

> **Link quality:** held-out synthetic precision and recall, with false positives and review volume.<br>
> **Warning:** days of warning gained over an identical Tier-1-only snapshot.<br>
> **Calculation safety:** exact results on hand-calculated cascade fixtures.<br>
> **Governance:** prohibited actions blocked and stale approvals rejected.<br>
> **Human factors:** analyst completion time, errors, and confidence in the explanation.

**Expanded measurement plan**

- Hide selected true relationships from a complete synthetic graph.
- Prevent their direct declarations from entering the observable graph.
- Run the discovery and confirmation workflow on the remaining evidence.
- Measure true positives, false positives, false negatives, precision, recall, and review volume.
- Compare warning time under the Tier-1-only graph and the hidden-dependency graph using the same event and inventory snapshot.
- Compare every cascade result against a hand-calculated fixture.
- Test missing units, missing stock, conflicting evidence, ambiguous entities, stale approvals, policy violations, and audit tampering.
- Run short usability tasks that ask a new user to find the evidence, explain the runway, and identify the required approver.

**Targets, not current claims**

| Measure | Proposed target |
|---|---:|
| Hidden-link precision at review threshold | at least 0.80 |
| Hidden-link recall at review threshold | at least 0.70 |
| Curated cascade calculations | 100% exact |
| Prohibited test actions blocked | 100% |
| Seeded offline replay consistency | 10 out of 10 identical runs |

**Current narrow synthetic baseline, speaker note only**

> The frozen mock fixture produced precision 1.00, recall 0.50, three reviewed claims, and 18 days of warning over the Tier-1-only view. This demonstrates the fixture pipeline, not generalisation or real-world accuracy.

**Required limitation statement**

> Synthetic evaluation can show that the workflow behaves correctly on a constructed, versioned scenario. It cannot show that Substrata will achieve the same link quality, warning time, analyst utility, or financial value on a real manufacturer’s network. Real validation requires authorized enterprise data, domain review, security controls, and prospective workflow testing.

#### Assumptions and risks

| Risk | Mitigation |
|---|---|
| Incomplete or conflicting Tier-N data | Preserve provenance, show uncertainty, and request confirmation. |
| LLM hallucination or malformed output | Require structured JSON, exact evidence spans, schema validation, and review. |
| Confidentiality and source licensing | Use tenant isolation, minimum excerpts, access control, and approved sources. |
| False urgency from assumptions | Show units, source, observation time, range, and incomplete status instead of guessing. |
| Unsafe automation | Keep real procurement changes prohibited; use named approval and dry-run execution. |
| SAP service unavailable at the finale | Keep the offline synthetic replay as the core path; connect only verified entitlements. |

**Additional adoption and delivery risks**

| Risk | Why it matters | Response |
|---|---|---|
| Excessive review volume | Analysts may ignore the queue | Measure review load and raise the proposal threshold |
| Supplier reluctance | A supplier may not disclose upstream relationships | Ask narrow questions, define purpose, and retain uncertainty when unanswered |
| Entity-resolution error | Similar names can merge unrelated organisations | Show candidates separately and require an explicit reason before merging |
| Stale graph or inventory | A correct calculation on old inputs can still mislead | Pin observation times and expire decisions after input changes |
| Overreliance on explanation quality | A fluent rationale can hide weak evidence | Show sources, formulas, missing data, and rule outcomes before narrative |
| User distrust | Analysts may reject black-box recommendations | Make evidence and deterministic calculation provenance available from the result |

**Optional backup visual:**

![Evaluation gates and roadmap](diagrams/14-evaluation-roadmap.png)

### Slide 8: Feasibility and roadmap

**Template heading:** What would it take to build the prototype?

The repository already contains a working local synthetic vertical slice. Frame this slide as the plan to turn it into a finale-ready, SAP-aligned proof, not as starting from zero.

#### 1. Plan

> Interview 2-3 supply-risk or procurement practitioners. Confirm the user decision, required inputs, acceptable uncertainty, and SAP services available to finalists.

**Plan deliverables**

- corrected empathy map and ranked user pain points;
- one validated decision scenario and primary persona;
- minimum required data, units, and evidence list;
- SAP account, service, quota, and practice-system checklist;
- updated Business Model Canvas with assumptions clearly marked.

**Plan exit condition:** At least one practitioner confirms that the selected workflow and runway view address a real decision problem.

#### 2. Design

> Freeze the minimum data contract and user journey. Keep the system boundary clear: cited inference, deterministic impact, policy, human approval, and audit.

**Design deliverables**

- final user journey and agent-human interaction;
- entity, relationship, evidence, event, scenario, action, and approval contracts;
- clear model-versus-deterministic responsibility table;
- failure behavior for ambiguous, incomplete, stale, and prohibited cases;
- frozen synthetic scenario and evaluation manifest.

**Design exit condition:** The team can explain every input, output, assumption, authority boundary, and failure state used by the demonstration.

#### 3. Build

> Harden agent orchestration, evidence mapping, the cited domain assistant, deterministic impact services, approval, and audit on synthetic data. Add one read-only SAP adapter only if entitlement and test data are available. Preserve an offline replay fallback.

**Build deliverables**

- reproducible local setup and deterministic seed;
- evidence discovery and verification workflow;
- event replay, graph impact, and runway result;
- mitigation comparison, named approval, and audit verification;
- one verified read-only SAP integration if available;
- offline mock and recovery path for the presentation machine.

**Build exit condition:** A fresh environment can run the core scenario without editing code or repairing data during the demo.

#### 4. Test

> Run hidden-edge evaluation, cited-answer checks, exact impact fixtures, failure cases, stale approval tests, usability sessions, and repeated judge rehearsals. Report targets and measured results separately.

**Test deliverables**

- versioned evaluation report with raw counts and failure examples;
- exact impact and unit-validation results;
- policy, stale-input, and audit-mutation test results;
- provider-failure and offline-fallback rehearsal;
- timed team presentation and recovery checklist;
- final claim table separating measured, expected, and future items.

**Test exit condition:** The team can repeat the demo, explain every number, recover from common failures, and defend every statement in the pitch.

#### Feasibility check

- **Smallest finale proof:** discover one hidden dependency, verify it, replay one event, calculate runway, compare simulated actions, approve one, and verify the audit chain.
- **Already available:** interactive graph, evidence-backed discovery, simulated confirmations, event replay, deterministic 18/90/72 runway, mitigation drafts, approval, audit, a tenant workspace, imports, jobs, and report exports on synthetic data.
- **Needed skills:** Python service development, TypeScript/React UI, graph modelling, testing, SAP process learning, and stakeholder interviewing.
- **Needed support:** a confirmed SAP practice environment, a supply-chain mentor, legally usable test data, and feedback from real target users.
- **Deliberate exclusions:** autonomous purchasing, production SAP writes, unbounded web crawling, customer-accuracy claims, and a custom GNN.

**Resources and support required**

| Area | Requirement |
|---|---|
| Domain knowledge | Supply-chain practitioner interviews and mentor feedback |
| SAP learning | Individual Learning Hub registration and completed relevant learning items |
| SAP environment | Confirmed finale entitlements, sample data, documentation, and access dates |
| Engineering | Python, TypeScript, graph modelling, API integration, testing, and deployment skills |
| Data | Versioned synthetic fixture plus any legally usable sample data |
| Presentation | Stable laptop, offline fallback, recorded backup, and repeated rehearsal |

**Why the plan is feasible**

> The minimum proof is intentionally narrow. It requires one hidden dependency, one confirmation, one event, one deterministic calculation, one governed mitigation draft, and one verifiable decision record. The current repository already demonstrates this synthetic vertical slice, so finale work can focus on validation, reliability, and one honest SAP integration rather than building every possible feature.

**Do not paste a 30-day schedule here.** Use capability gates. The supply-chain values 18, 90, and 72 days are unrelated to project delivery.

**Optional visual:**

![Six-stage synthetic demo replay](diagrams/10-demo-replay.png)

### Slide 9: Team and closing

**Template heading:** Why should this idea move forward?

**One-sentence pitch**

> Substrata turns hidden Tier-N uncertainty into evidence-backed links, quantified decision runway, and human-approved response drafts, giving supply teams time to act before a shared dependency stops production.

**Short closing paragraph for the presenter**

> The idea is focused enough to test, relevant to SAP's supply-chain domain, and safe by design. It combines agentic assistance where interpretation is useful with deterministic services where correctness and accountability matter. The regional round can validate the user and business assumptions; the finale can demonstrate one end-to-end, SAP-aligned scenario without pretending to be a production procurement system.

**Expanded closing argument**

> Substrata addresses a specific supply-chain weakness: apparent diversification can hide real upstream concentration. The proposal goes beyond drawing a network. It asks whether the hidden relationship is supported, gives a supplier or analyst a way to verify it, traces the disruption through a versioned graph, converts operational inputs into decision runway, and keeps consequential action under named human authority.
>
> The project is feasible because the smallest useful prototype has a clear boundary. It needs one scenario, one hidden dependency, one disruption, one deterministic calculation, one approval, and one audit trail. The working synthetic prototype already establishes this flow. The next stage should validate the user, harden the evaluation, and connect one SAP boundary that the team can access and explain.

**Alternative one-sentence pitches**

| Tone | One-sentence pitch |
|---|---|
| Recommended | Substrata reveals hidden shared supplier dependencies, calculates how long production remains protected, and places every high-impact response under evidence-backed human approval. |
| Business-focused | Substrata helps manufacturers detect false supplier diversification early enough to protect production through a traceable and governed response. |
| Technical | Substrata combines cited relationship inference, a versioned supply graph, deterministic cascade analysis, and policy-controlled approval for Tier-N disruption response. |

**Final request to the judges**

> [Advance Substrata so the team can validate the workflow with practitioners, connect one verified SAP boundary, and demonstrate the complete evidence-to-decision flow at the finale.](https://news.sap.com/2025/10/sap-connect-innovative-updates-supply-chain-management/)

**References / sources for the slide**

Use shortened titles on the slide and keep full URLs in speaker notes:

1. [SAP Hackfest Bengaluru 2026](https://events.sap.com/in-hackfest-bangalore-2026/en_us/home.html)
2. [SAP Learning Hub, student edition](https://learning.sap.com/students)
3. [SAP guidance for building AI agents](https://architecture.learning.sap.com/docs/golden-path/ai-golden-path/build-and-deliver/build-ai-agents)
4. [SAP Supply Chain Orchestration announcement](https://news.sap.com/2025/10/sap-connect-innovative-updates-supply-chain-management/)
5. [Cambridge Supply Chain AI Lab: link prediction](https://www.ifm.eng.cam.ac.uk/research/supply-chain-ai-lab/current-themes/supply-chain-link-prediction/)
6. [ACEA: critical Nexperia chip supply shortage](https://www.acea.auto/press-release/acea-calls-for-quick-resolution-to-critical-chip-supply-shortage/)
7. [UNCTAD Review of Maritime Transport 2022](https://unctad.org/system/files/official-document/rmt2022_en.pdf)
8. [SAP Business Network: Multitier Order Collaboration](https://help.sap.com/docs/business-network-for-supply-chain/business-network-for-supply-chain-integration-and-configuration/multitier-order-collaboration-0d01b6d20b9042f4ac46c2ad2839d0ad)
9. [SAP HANA Cloud Property Graph Engine](https://help.sap.com/docs/hana-cloud-database/sap-hana-cloud-sap-hana-database-property-graph-engine-reference/sap-hana-graph-data-model-030-000-000-sap_hana_graph_data_model)
10. [SAP Clean Core Extensibility](https://help.sap.com/docs/erp-transformation-with-itc/buildable-map/clean-core-extensibility-for-sap-cloud-erp)
11. [NIST Generative AI Risk Management Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)

**Source disclosure to place in speaker notes**

> Public reporting supplies disruption context only. All supplier relationships, inventory quantities, lead times, costs, actions, and financial assumptions in the demonstration are synthetic.

**Draft business model, for Q&A rather than the crowded closing slide**

![Draft Substrata Business Model Canvas](diagrams/16-business-model-canvas.png)

> The customer, buyer, pricing, willingness to share data, and sales cycle are unvalidated. Present the canvas as a hypothesis and state that stakeholder interviews are the next validation step.

### Slide 10: Questions and answers

Keep the template text:

> **THANK YOU | Questions & Answers**

Optionally add one small footer:

> Substrata | Evidence -> Runway -> Governed Action

**Best opening for Q&A**

> We can show the hidden-link evidence, the deterministic 18/90/72 calculation, or the human approval and audit boundary in more detail.

**Prepare these four Q&A routes**

1. **Problem and user:** visibility-gap diagram, empathy map, current workflow, and Business Model Canvas.
2. **Architecture and AI:** system context, graph schema, link-inference pipeline, deterministic boundary, and technology stack.
3. **Safety and governance:** autonomy matrix, approval rules, stale-input handling, simulated execution, and audit limitation.
4. **Evidence and validation:** runway calculation, synthetic results, targets, failure examples, and real-world validation plan.

Assign a team member to lead each route. The first response should answer the question directly in one or two sentences. Open the relevant backup visual only when the judge asks for deeper detail.

### Slide 11: Presenter checklist

This is an internal submission-control slide. Complete it honestly and hide it during the live pitch if the organiser permits hidden slides.

| Checklist item | Required action |
|---|---|
| Team has 4-5 eligible students | Confirm names and eligibility. |
| Every member registered for SAP Learning Hub student edition | Verify individually; do not assume team registration covers everyone. |
| Every member has a Universal ID and Hackfest registration | Confirm with the college coordinator. |
| One theme and one idea | Use Resilient Supply Chains and Substrata only. |
| Software-based idea | Substrata is a software platform; no hardware claim. |
| 10-minute pitch plus 5-minute Q&A | Rehearse to 9:30 so there is recovery time. |
| Problem, users, solution, SAP relevance, impact, feasibility | Covered by slides 3-8. |
| Team details shared with coordinator | Complete before submission. |

**Additional final checks**

- The title and team details match the official registration.
- Each Learning Hub resource listed on slide 6 has actually been completed or used.
- Every number has a unit, source, and synthetic or target label.
- No SAP product appears on the slide unless the presenter can explain its role and current status.
- The deck does not describe Gemini, Groq, NetworkX, or the scorer as the source of deterministic business arithmetic.
- The team can distinguish a supplier, supplier site, component, product, and plant.
- The presenter can explain why `inferred` and `confirmed` are separate states.
- The laptop can run the full offline path without provider access.
- A PDF and recorded demo are available as presentation backups.
- The team has rehearsed within 10 minutes and assigned Q&A ownership.

## 4. Architecture and technology summary for the main deck

If a judge asks for the architecture, answer in six layers:

1. **Inputs:** synthetic ERP-shaped supplier, purchasing, BOM, inventory, lead-time, document, event, and supplier-response data.
2. **Persistence:** SQLAlchemy and Alembic with SQLite for the offline demo and PostgreSQL/pgvector for the tenant platform.
3. **Knowledge graph:** versioned entities and relationships projected into NetworkX for transparent traversal.
4. **Agent workflow:** Mapper and Sensor interpret evidence; LangGraph coordinates the read-only assistant; deterministic services perform graph and runway calculations; the assistant returns cited path answers; Action prepares options; Compliance/Audit enforces controls.
5. **Application:** FastAPI/Pydantic owns domain logic; Next.js/TypeScript/Cytoscape.js renders the workspace and receives updates through SSE.
6. **Governance and execution:** named approval, separation of duties, dry-run SAP-shaped payloads, and a hash-chained audit record. No real procurement mutation is enabled.

## 5. Diagram placement map

| Asset | Best use in the official deck | Backup/Q&A use | Important caption |
|---|---|---|---|
| `01-visibility-gap.png` | Slide 3 | Problem explanation | Three visible Tier-1 suppliers can share one hidden Tier-N source. |
| `02-runway-timeline.png` | Slide 4 or 5 if space permits | Explain 18/90/72 | Synthetic business runway, not the hackathon schedule. |
| `03-system-context.png` | Slide 5 | Architecture Q&A | SAP systems are integration targets, not current live connections. |
| `04-layered-architecture.png` | Do not crowd the main deck | Technical Q&A | Current implementation plus explicitly proposed adapters. |
| `05-agent-collaboration.png` | Slide 5 presenter notes | Agent/human Q&A | Deterministic policy and a named human gate control action. |
| `06-autonomy-matrix.png` | Slide 7 if replacing text | Safety Q&A | Separate automatic analysis, review-required action, and prohibited action. |
| `07-graph-schema.png` | Not needed in main deck | Data-model Q&A | Every relationship carries status, confidence, evidence, and version. |
| `08-link-inference-pipeline.png` | Slide 5 alternative | AI Q&A | Pretrained extraction proposes a cited edge; verification changes status. |
| `09-cascade-simulation.png` | Slide 5 alternative | Math Q&A | Graph paths identify impact; deterministic code performs arithmetic. |
| `10-demo-replay.png` | Slide 8 | Demo Q&A | A repeatable synthetic replay proves the workflow, not real-world accuracy. |
| `11-persistence-model.png` | Not needed in main deck | Audit/versioning Q&A | Results pin immutable inputs and versions. |
| `12-tech-stack.png` | Slide 6, small lower strip | Tech Q&A | Some products in the diagram are proposed or entitlement-dependent. |
| `13-deployment-topology.png` | Not needed in main deck | SAP/deployment Q&A | Local path works offline; SAP BTP path is a verified-access stretch. |
| `14-evaluation-roadmap.png` | Slide 7 or 8 | Evaluation Q&A | Targets become claims only after versioned measurement. |
| `15-empathy-map.png` | Slide 4 only if replacing boxes | Design-thinking Q&A | Draft assumptions, not interview evidence. |
| `16-business-model-canvas.png` | Avoid shrinking onto slide 9 | Business Q&A | Buyer, pricing, and data-sharing behavior remain unvalidated. |

## 6. Likely judge questions and short answers

### How is this different from existing supplier-risk or SAP products?

Substrata is not claiming that established products lack multi-tier risk functions. The hackathon thesis is narrower: cited link proposals, a confirmation loop, deterministic runway, and an explicit human approval gate in one traceable workflow.

### Where does Tier-N data come from?

The current prototype uses synthetic ERP-shaped records, synthetic declared relationships, documents, replayed public event context, and simulated supplier responses. A real deployment would require customer-authorized data, licensed sources, and supplier participation.

### What if an inferred link is wrong?

It remains `inferred`, carries evidence and confidence, and enters review. Confirmation, rejection, and expiry are stored as separate states. Inferred exposure is shown as uncertainty rather than silently treated as fact.

### Why use agents instead of one dashboard?

Evidence extraction, event matching, graph analysis, option drafting, policy, and approval have different permissions and failure modes. Named agent roles make those boundaries inspectable. The critical calculations still run in deterministic services.

### Did you train a model?

The core flow does not fine-tune an LLM or train a GNN. It uses pretrained models for structured extraction and deterministic graph code for analysis. The broader platform has an optional gradient-boosted link scorer trained from reviewed supplier labels, with explicit activation gates; it is not the core pitch and has no claimed customer accuracy.

### Is accuracy proven?

No. The current measurements are from a narrow synthetic fixture. They verify pipeline behavior and reproducibility only. Real accuracy requires legally usable enterprise data, held-out evaluation, calibration, and prospective user testing.

### Can the system buy stock or switch suppliers?

No. The prototype creates simulated drafts only. Supplier changes, spend, or real external execution require a named human and a separately configured production adapter that does not exist in the current demo.

### What is SAP doing in this solution today?

Today the data is SAP-shaped, and the interfaces are designed for procurement, BOM, inventory, supplier-network, and approval processes. Live SAP access is not claimed. SAP BTP, HANA graph/vector, Business Network, AI Core, and Joule/A2A are possible finale adapters after entitlement and data access are confirmed.

### Why should the idea advance?

It tackles a specific failure mode, has a working and safe synthetic proof, defines measurable validation gates, and fits SAP's supply-chain domain without pretending to be production-ready.

## 7. Final pitch quality check

- Every slide answers one question and uses no more than one main visual.
- No slide presents a target as a result.
- All synthetic numbers are labelled.
- SAP services are split into “current concept/shape” and “future verified integration.”
- The presenter can explain why 90 minus 18 equals a 72-day exposure window.
- The presenter can explain exactly where the LLM stops and deterministic code begins.
- The presenter can explain who approves a high-impact action and what is recorded.
- The presenter can name the primary user, buyer hypothesis, and unvalidated assumptions.
- The final deck contains team names, exact completed Learning Hub resources, and the required registration details.
