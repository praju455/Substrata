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

**Presenter note:** Do not spend time listing technologies here. Give each person a responsibility such as research and business design, data and graph, backend and AI, frontend and experience, or testing and presentation.

### Slide 3: Problem and theme

**Template heading:** What problem are you solving?

**Selected theme**

> **Resilient Supply Chains**

**Problem statement, 2-3 sentences**

> Manufacturers can see their direct Tier-1 suppliers, yet several of those suppliers may rely on the same deeper supplier, site, material, owner, region, or route. A disruption at that hidden Tier-N node can disable multiple supposedly independent supply paths at once. Evidence is fragmented, so planners may discover the concentration only after stock is already running out.

**Who experiences the problem?**

> Supply-risk analysts, procurement teams, plant planners, and the managers who approve mitigation decisions.

**When and where does it occur?**

> During supplier onboarding, periodic risk reviews, and fast-moving disruptions, especially when Tier-N relationships are split across ERP records, documents, news, and supplier responses.

**Concrete example**

> In our synthetic automotive scenario, three Tier-1 supplier groups appear independent but share one deeper semiconductor source. A replayed disruption exposes the common point of failure.

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

#### Current approach

> Teams often reconcile direct-supplier records, spreadsheets, documents, alerts, and calls manually. A conventional Tier-1 view can show who has a contract without revealing the upstream dependency shared by multiple contracts. Analysis and approval are separated, so the reason for a decision may be difficult to reconstruct later.

#### Opportunity

> Join evidence and supply relationships in a versioned knowledge graph, keep uncertain links visibly inferred, ask humans or suppliers to confirm them, and calculate decision runway before recommending a response. The result is earlier attention with less false certainty.

**Concrete scenario to place under the three boxes**

> **Synthetic example:** 1,800 units available at 100 units/day gives 18 days of cover. A replacement takes an assumed 90 days to qualify, leaving a 72-day exposure window.

**Business model sentence for this slide**

> Proposed buyer: a manufacturer or supply-risk function. Proposed value: evidence-backed hidden-dependency discovery, decision runway, and governed response. Subscription and implementation pricing remain unvalidated assumptions.

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
| **Analyse / Decide** | Mapper proposes cited links; supplier/analyst verifies; Sensor matches event; deterministic Cascade traces impact and runway |
| **Action** | Compare buffer, expedite, transfer, or alternate-qualification drafts; policy chooses allow, review, or block |
| **Outcome** | Earlier warning, explicit uncertainty, named approval, simulated SAP-shaped payload, verifiable audit trail |

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
- **Cascade:** calls deterministic graph and runway services; it does not improvise numbers.
- **Action:** prepares and compares mitigation drafts.
- **Compliance/Audit:** applies policy and records provenance.
- **Human gate:** approves or rejects high-impact actions with a reason.

### Slide 6: SAP technology and learning

**Template heading:** Where do SAP technologies fit?

This slide must distinguish the **working local prototype** from the **SAP-aligned finale path**.

#### Left box: Technology / concept

> **Current prototype**<br>
> Next.js + TypeScript + Cytoscape.js interface<br>
> FastAPI + Pydantic service layer<br>
> NetworkX deterministic graph analysis<br>
> SQLAlchemy + Alembic with SQLite/PostgreSQL<br>
> Gemini primary, Groq fallback, and offline mock for structured extraction<br>
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

**Visual placement:** If space permits, place the technology map as a narrow lower band. Add a caption: “Current local stack plus entitlement-dependent SAP adapters.” The existing image says “proposed”; keep that word visible.

![Substrata technology map](diagrams/12-tech-stack.png)

**Important correction to the diagram:** LangGraph, MapLibre, SAP HANA graph, and SAP generative AI hub are proposed or optional. They are not dependencies in the current working build. The implemented orchestration uses typed Python services and state machines, and the current UI manifest includes Cytoscape.js but not MapLibre.

**What to say**

> We are not using SAP's name as decoration. The workflow naturally consumes procurement, BOM, inventory, planning, and supplier-network information. Our current prototype proves the decision flow locally. If the finale provides the required services, the same interfaces can be connected to SAP data and AI services without moving graph mathematics into a language model.

### Slide 7: Impact and validation

**Template heading:** How will you know it works?

#### Expected impact

> Surface common upstream dependencies before a Tier-1-only view would.<br>
> Express urgency as decision runway rather than a vague risk score.<br>
> Reduce false certainty by separating inferred, confirmed, rejected, and expired links.<br>
> Make every proposed action reviewable through evidence, versions, approver, reason, and audit history.

#### Success measures

> **Link quality:** held-out synthetic precision and recall, with false positives and review volume.<br>
> **Warning:** days of warning gained over an identical Tier-1-only snapshot.<br>
> **Calculation safety:** exact results on hand-calculated cascade fixtures.<br>
> **Governance:** prohibited actions blocked and stale approvals rejected.<br>
> **Human factors:** analyst completion time, errors, and confidence in the explanation.

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

#### Assumptions and risks

| Risk | Mitigation |
|---|---|
| Incomplete or conflicting Tier-N data | Preserve provenance, show uncertainty, and request confirmation. |
| LLM hallucination or malformed output | Require structured JSON, exact evidence spans, schema validation, and review. |
| Confidentiality and source licensing | Use tenant isolation, minimum excerpts, access control, and approved sources. |
| False urgency from assumptions | Show units, source, observation time, range, and incomplete status instead of guessing. |
| Unsafe automation | Keep real procurement changes prohibited; use named approval and dry-run execution. |
| SAP service unavailable at the finale | Keep the offline synthetic replay as the core path; connect only verified entitlements. |

**Optional backup visual:**

![Evaluation gates and roadmap](diagrams/14-evaluation-roadmap.png)

### Slide 8: Feasibility and roadmap

**Template heading:** What would it take to build the prototype?

The repository already contains a working local synthetic vertical slice. Frame this slide as the plan to turn it into a finale-ready, SAP-aligned proof, not as starting from zero.

#### 1. Plan

> Interview 2-3 supply-risk or procurement practitioners. Confirm the user decision, required inputs, acceptable uncertainty, and SAP services available to finalists.

#### 2. Design

> Freeze the minimum data contract and user journey. Keep the system boundary clear: cited inference, deterministic impact, policy, human approval, and audit.

#### 3. Build

> Harden Mapper, Cascade, approval, and audit on synthetic data. Add one read-only SAP adapter only if entitlement and test data are available. Preserve an offline replay fallback.

#### 4. Test

> Run hidden-edge evaluation, exact cascade fixtures, failure cases, stale approval tests, usability sessions, and repeated judge rehearsals. Report targets and measured results separately.

#### Feasibility check

- **Smallest finale proof:** discover one hidden dependency, verify it, replay one event, calculate runway, compare simulated actions, approve one, and verify the audit chain.
- **Already available:** interactive graph, evidence-backed discovery, simulated confirmations, event replay, deterministic 18/90/72 runway, mitigation drafts, approval, audit, a tenant workspace, imports, jobs, and report exports on synthetic data.
- **Needed skills:** Python service development, TypeScript/React UI, graph modelling, testing, SAP process learning, and stakeholder interviewing.
- **Needed support:** a confirmed SAP practice environment, a supply-chain mentor, legally usable test data, and feedback from real target users.
- **Deliberate exclusions:** autonomous purchasing, production SAP writes, unbounded web crawling, customer-accuracy claims, and a custom GNN.

**Do not paste a 30-day schedule here.** Use capability gates. The supply-chain values 18, 90, and 72 days are unrelated to project delivery.

**Optional visual:**

![Six-stage synthetic demo replay](diagrams/10-demo-replay.png)

### Slide 9: Team and closing

**Template heading:** Why should this idea move forward?

**One-sentence pitch**

> Substrata turns hidden Tier-N uncertainty into evidence-backed links, quantified decision runway, and human-approved response drafts, giving supply teams time to act before a shared dependency stops production.

**Short closing paragraph for the presenter**

> The idea is focused enough to test, relevant to SAP's supply-chain domain, and safe by design. It combines agentic assistance where interpretation is useful with deterministic services where correctness and accountability matter. The regional round can validate the user and business assumptions; the finale can demonstrate one end-to-end, SAP-aligned scenario without pretending to be a production procurement system.

**References / sources for the slide**

Use shortened titles on the slide and keep full URLs in speaker notes:

1. [SAP Hackfest Bengaluru 2026](https://events.sap.com/in-hackfest-bangalore-2026/en_us/home.html)
2. [SAP Learning Hub, student edition](https://learning.sap.com/students)
3. [SAP guidance for building AI agents](https://architecture.learning.sap.com/docs/golden-path/ai-golden-path/build-and-deliver/build-ai-agents)
4. [SAP Supply Chain Orchestration announcement](https://news.sap.com/2025/10/sap-connect-innovative-updates-supply-chain-management/)
5. [Cambridge Supply Chain AI Lab: link prediction](https://www.ifm.eng.cam.ac.uk/research/supply-chain-ai-lab/current-themes/supply-chain-link-prediction/)
6. [Nexperia disruption timeline used as public replay context](https://blog.findchips.com/nexperia-supply-disruption/)

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

## 4. Architecture and technology summary for the main deck

If a judge asks for the architecture, answer in six layers:

1. **Inputs:** synthetic ERP-shaped supplier, purchasing, BOM, inventory, lead-time, document, event, and supplier-response data.
2. **Persistence:** SQLAlchemy and Alembic with SQLite for the offline demo and PostgreSQL/pgvector for the tenant platform.
3. **Knowledge graph:** versioned entities and relationships projected into NetworkX for transparent traversal.
4. **Agent workflow:** Mapper and Sensor interpret evidence; Cascade calls deterministic calculations; Action prepares options; Compliance/Audit enforces controls.
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

## 8. Expanded content bank for building the PPT

The earlier sections contain the recommended concise copy. This section gives you more material than will fit on the slides. Use it while designing the deck, move explanations into speaker notes, and shorten only after the full story is clear.

### Slide 2 expanded content: project identity and team credibility

#### Longer project description

> Substrata is an agentic supply-chain resilience layer that helps manufacturers discover hidden dependencies beyond their direct suppliers. It connects relationship evidence to a versioned supply graph, verifies uncertain links, calculates the time remaining before production is exposed, and prepares mitigation drafts under human control.

#### Why the name fits

“Substrata” refers to the layers beneath the visible supplier network. Tier-1 contracts form the surface. Deeper suppliers, facilities, ownership links, materials, regions, and routes form the hidden structure underneath. The name supports the message “see beneath the surface” without tying the product to one industry.

#### Team role wording

Use roles that show complete ownership of the idea rather than generic labels such as “member.” Suggested role descriptions are:

- problem research, stakeholder validation, and business model;
- supply-chain data model and graph design;
- backend, deterministic cascade, and governance;
- AI extraction, evidence, and evaluation;
- frontend experience, demo, and presentation.

Only use roles that reflect the team’s real contribution.

#### Longer speaker script

> We chose the name Substrata because the risk we care about sits underneath the visible supplier list. A company may sign with several Tier-1 suppliers and believe it has diversified. If those suppliers depend on the same deeper source, the real network remains concentrated. Our team is combining supply-chain process research, graph modelling, evidence extraction, deterministic simulation, and a human approval workflow to make that concentration visible before production is affected.

#### Cut first when shortening

Remove the longer description and keep only the name, tagline, team details, and one-line purpose.

### Slide 3 expanded content: problem mechanics

#### Full problem explanation

> Enterprise procurement systems usually provide the clearest view of direct suppliers because those are the organisations with contracts, purchase orders, deliveries, and invoices. The picture becomes less complete deeper in the network. A Tier-1 supplier may buy a component from a Tier-2 manufacturer, which may depend on a Tier-3 facility, specialised material, parent company, region, or route that also serves other Tier-1 suppliers.
>
> This creates false diversification. The buyer sees several direct contracts, but the upstream paths converge. When the shared node experiences an export restriction, factory shutdown, financial failure, cyber incident, port closure, or material shortage, multiple direct suppliers can fail together.
>
> The decision problem becomes harder because the company must determine whether the hidden link is credible, which products and plants depend on it, how long existing stock will last, how long a recovery option will take, and which person has authority to act. These questions often span separate tools and teams.

#### Root causes to choose from

Use two or three of these in speaker notes:

- Direct supplier records do not automatically expose sub-tier relationships.
- Names and identifiers differ across documents, subsidiaries, sites, and languages.
- Ownership evidence, supply evidence, inventory, and event signals come from different sources.
- Suppliers may be unable or unwilling to disclose their complete upstream network.
- A relationship can change over time, so an old map can create false confidence.
- A high risk score does not tell the planner when stock ends or when an alternative becomes usable.

#### Failure modes

| Failure mode | Operational consequence |
|---|---|
| Shared source remains hidden | Several supplier paths fail at the same time. |
| Weak evidence becomes accepted as fact | Teams waste time or take the wrong mitigation. |
| Disruption is detected without a where-used view | Analysts cannot identify the affected component, product, or plant. |
| Stock and qualification time are not compared | The team knows there is risk but not how urgently it must decide. |
| Recommendation lacks an approval boundary | The system may suggest an action that exceeds authority or creates new risk. |
| Decision inputs are not frozen | The team cannot reproduce why an action was approved. |

#### Example narrative

> Imagine that Supplier A, Supplier B, and Supplier C each provide different assemblies. Procurement treats them as independent. Evidence suggests that all three depend on the same semiconductor source two or three tiers upstream. A restriction affects that source. The manufacturer now has three contracts but only one real upstream option. The hidden dependency has turned apparent diversification into a single point of failure.

#### Strong problem statement alternatives

**Business-focused version**

> Manufacturers can diversify their direct suppliers and still remain dependent on one hidden upstream source. When that shared source is disrupted, fragmented evidence and disconnected planning data delay the answer to two urgent questions: what production is exposed, and how long remains to act?

**Human-focused version**

> Supply-risk analysts must make urgent decisions using incomplete sub-tier information, scattered evidence, and uncertain assumptions. They need a way to verify hidden relationships, trace their production impact, and escalate the right action without trusting a black box.

**Technical version**

> Direct supplier records show contracts, not the complete dependency graph. Substrata addresses missing Tier-N edges, uncertain evidence, deterministic cascade analysis, and controlled decision handoff.

#### Cut first when shortening

Keep the business-focused problem statement, the target users, and the single synthetic example. Move root causes and failure modes into speaker notes.

### Slide 4 expanded content: users, current workflow, and opportunity

#### Primary persona: supply-risk analyst

**Job to be done**

> When a new relationship or disruption signal appears, determine whether it is credible, identify the affected supply paths, and prepare a recommendation before stock cover ends.

**Information needed**

- exact evidence and source date;
- relationship status and confidence;
- supplier, component, product, and plant path;
- inventory and eligible incoming supply;
- alternate qualification or recovery time;
- assumptions, missing data, and truncation;
- approval rule and responsible decision-maker.

**Pain points to validate**

- repeated manual reconciliation across documents and systems;
- uncertainty about whether two names refer to the same entity;
- difficulty explaining a model-generated relationship to procurement;
- limited time to compare recovery options;
- accountability for escalation without complete evidence.

#### Secondary persona: procurement or planning approver

The approver does not need every model detail. The approver needs the exact affected scope, source evidence, remaining runway, available options, cost and operational assumptions, policy reason, and a clear record of the final decision.

#### Supplier participant

A supplier should receive a narrow confirmation question rather than broad access to the buyer’s network. The request should identify the relationship being checked, explain how the response will be used, expire after a defined period, and prevent reuse after a reply.

#### Current workflow hypothesis

1. A planner or analyst receives an alert, email, report, or news item.
2. The analyst searches supplier records and spreadsheets for matching names.
3. Procurement contacts internal owners or suppliers for clarification.
4. Planning gathers stock and consumption data.
5. Engineering estimates alternate qualification time.
6. The team compares options through meetings and spreadsheets.
7. A manager approves an action through an existing workflow.
8. Evidence for the final decision may remain split across messages and files.

This workflow is a design hypothesis. Stakeholder interviews must confirm which steps occur, who owns them, and where the largest delay actually exists.

#### Opportunity statement

> Substrata can reduce the time spent assembling decision context. It creates one traceable chain from relationship evidence to verification, graph impact, operational runway, mitigation comparison, approval, and audit. The intended benefit is a faster and more explainable decision, not fully autonomous procurement.

#### Expanded business model hypothesis

| Business-model element | Current hypothesis | What must be validated |
|---|---|---|
| User | Supply-risk analyst or supply planner | Frequency and severity of the workflow |
| Buyer | Manufacturer’s procurement, supply-chain, or risk leadership | Budget owner and buying process |
| Value | Earlier hidden-risk visibility and clearer decision runway | Whether it changes a real decision |
| Delivery | Enterprise web application connected to planning and supplier data | Integration effort and data permissions |
| Revenue | Subscription plus implementation/support | Willingness to pay and pricing basis |
| Cost | Data integration, hosting, inference, supplier participation, and validation | Customer-specific cost structure |
| Adoption risk | Users may distrust inferred links or face alert overload | Required explanation and review-volume threshold |

#### Cut first when shortening

Keep one primary user, the current gap, the opportunity, and the 18/90/72 example. Keep supplier participation and the business-model table for questions.

### Slide 5 expanded content: complete solution flow

#### Stage 1: Map the visible network

Substrata begins with supplier, purchasing, BOM, plant, stock, lead-time, and declared-relationship records. Each entity and relationship has an identifier, source, observation time, and version. The system does not assume that a supplier’s legal entity, production site, and parent company are the same thing.

#### Stage 2: Propose hidden relationships

The Mapper searches supplied evidence and returns structured relationship claims with exact citations. Entity resolution connects a claim to known graph entities. The result becomes an `inferred` edge with provenance. The model cannot directly create a `confirmed` edge.

#### Stage 3: Verify uncertain claims

An analyst can review the evidence, or the system can prepare a narrow supplier-confirmation request. A confirmation, rejection, or expiry remains part of history. Rejected claims are not deleted because they help explain later decisions and evaluate the discovery method.

#### Stage 4: Sense and simulate a disruption

The Sensor matches an event to candidate entities. Ambiguous matches pause for review. Once the event is resolved, deterministic code traverses a pinned graph snapshot, finds affected supply paths, checks inventory and incoming supply, and compares cover against recovery time.

#### Stage 5: Prepare and govern a response

The Action role compares simulated options such as a buffer purchase, expedite, plant reallocation, safety-stock adjustment, or alternate-supplier qualification. Policy decides whether the draft may be recorded, requires review, or must be blocked. High-impact options pause for a named approver. The prototype records a dry-run payload and does not change a real purchasing system.

#### Detailed input-to-outcome chain

| Step | Input | Processing | Output | Human role |
|---|---|---|---|---|
| Discover | Supplier records and evidence | Structured extraction and entity resolution | Cited inferred links | Review ambiguous claims |
| Confirm | Inferred link and bounded request | Signed confirmation workflow | Confirmed, rejected, or expired status | Supplier or analyst responds |
| Detect | Sourced disruption event | Classification, deduplication, entity matching | Resolved affected node | Analyst resolves ambiguity |
| Calculate | Pinned graph, stock, consumption, lead time | Deterministic traversal and formulas | Impact report and exposure range | Inspect assumptions and missing inputs |
| Plan | Impact report and sourced options | Rules compare time, cost, and risk | Ranked simulated drafts | Select or reject the proposal |
| Govern | Draft, actor, policy, versions | Role, threshold, staleness, and expiry checks | Allow, review, or block | Named approver records reason |
| Audit | Final decision and frozen context | Hash-chained append | Verifiable decision history | Reviewer verifies the chain |

#### Why the architecture is safe for this problem

- AI assists where language and ambiguity matter.
- Deterministic services own calculations that must be reproducible.
- Status prevents inferred relationships from silently becoming truth.
- Frozen versions make the result reproducible.
- The approval gate keeps authority with a person.
- Dry-run execution prevents a prototype from changing real operations.

#### Longer speaker script

> The workflow begins with records the organisation already understands, plus documents that may contain missing relationship evidence. A pretrained model extracts a claim into a strict schema and cites the exact passage. The graph stores it as inferred. A supplier or analyst can confirm or reject it. When an event arrives, deterministic services trace the affected paths and calculate runway from inventory, consumption, and qualification inputs. The system then prepares options, but policy and a named person control any high-impact choice. Every result retains its graph, data, formula, policy, and actor context.

#### Cut first when shortening

Use the five stage names and the four template flow boxes. Move the detailed table into speaker notes or a technical appendix.

### Slide 6 expanded content: SAP relevance and learning

#### SAP business-process mapping

| Substrata need | Relevant SAP process or concept | Proposed use |
|---|---|---|
| Supplier and purchasing records | SAP S/4HANA procurement data | Read vendor, purchasing, material, and plant context through approved interfaces |
| Product and component use | BOM and where-used processes | Trace a disrupted material to products and plants |
| Inventory and planning | Inventory, supply planning, and SAP IBP concepts | Calculate available cover and compare recovery scenarios |
| Declared supplier relationships | SAP Business Network / Ariba concepts | Add known supplier-network context and support collaboration |
| Extension and integration | SAP BTP concepts | Host or integrate the application without changing the core system of record |
| Graph and retrieval | SAP HANA Cloud graph/vector concepts | Replace local graph or retrieval adapters if services are available and suitable |
| Pretrained AI access | SAP AI Core generative AI hub concepts | Route structured extraction through a governed provider layer |
| Enterprise assistant access | Joule and A2A concepts | Invoke a bounded Substrata assessment as a future integration |

Every row above describes a proposed fit. The team must confirm service access, exact APIs, data fields, and permitted operations before calling any integration implemented.

#### Current implementation versus SAP-aligned target

| Concern | Current implementation | SAP-aligned target |
|---|---|---|
| Source data | Synthetic fixtures, files, and local adapters | Customer-authorized SAP data through verified read-only interfaces |
| Graph | NetworkX plus versioned relational records | HANA graph adapter if entitlement and performance justify it |
| Database | SQLite locally, PostgreSQL/pgvector for platform | PostgreSQL on BTP or HANA after deployment validation |
| AI | Gemini primary, Groq fallback, explicit offline mock | Generative AI hub adapter if available |
| User identity | Development identity and platform OIDC support | Customer identity provider integrated through an approved BTP pattern |
| Action | Simulated SAP-shaped payload | Controlled adapter after human approval and production safeguards |

#### Learning Hub connection worksheet

Complete this before creating the final slide:

| Team member | Exact learning item completed | One concept applied to Substrata | Evidence available |
|---|---|---|---|
| [NAME] | [EXACT TITLE] | [CONCEPT AND WHERE USED] | [ACCOUNT / COMPLETION RECORD] |
| [NAME] | [EXACT TITLE] | [CONCEPT AND WHERE USED] | [ACCOUNT / COMPLETION RECORD] |
| [NAME] | [EXACT TITLE] | [CONCEPT AND WHERE USED] | [ACCOUNT / COMPLETION RECORD] |
| [NAME] | [EXACT TITLE] | [CONCEPT AND WHERE USED] | [ACCOUNT / COMPLETION RECORD] |
| [NAME, IF APPLICABLE] | [EXACT TITLE] | [CONCEPT AND WHERE USED] | [ACCOUNT / COMPLETION RECORD] |

#### Strong learning explanation

> The Learning Hub connection is not a list of SAP product names. We apply process thinking from procurement, planning, supplier collaboration, extension, and responsible AI. Those concepts shaped our data model, read-only integration boundary, approval workflow, and decision to keep uncertain model output separate from deterministic business logic.

#### Cut first when shortening

Keep the current stack, two or three SAP integration targets, and one exact completed Learning Hub item. Move the mapping table into notes.

### Slide 7 expanded content: impact logic and validation plan

#### Impact chain

| Capability | Immediate output | Expected operational benefit | Validation method |
|---|---|---|---|
| Hidden-link discovery | Cited inferred relationship | Analysts can investigate shared concentration earlier | Precision, recall, review volume, and error analysis |
| Confirmation workflow | Confirmed or rejected relationship | Less false certainty in the graph | Confirmation rate, rejection rate, response time, and stale requests |
| Cascade analysis | Affected components, plants, and products | Faster impact scoping | Exact comparison with hand-calculated fixtures |
| Runway calculation | Cover, qualification time, and exposure | Clearer urgency and decision deadline | Unit tests plus user comprehension task |
| Mitigation comparison | Sourced dry-run options | Faster preparation for an approval meeting | Task time, option completeness, and missing-data rate |
| Policy and approval | Allow, review, block, approve, or reject | Fewer unauthorized or stale decisions | Adversarial policy tests |
| Audit chain | Frozen decision record | Better traceability and post-event review | Injected mutation detection and independent verification |

#### What success would look like in the regional stage

- Judges understand the hidden-dependency problem without requiring a technical explanation.
- The team can identify the user, decision, evidence, and business hypothesis clearly.
- The architecture explains where AI is useful and where it has no authority.
- Every claim about SAP, accuracy, or impact has an explicit current or future status.

#### What success would look like in the finale prototype

- One end-to-end scenario runs repeatedly on the presentation machine.
- The graph shows a planted hidden dependency with cited evidence.
- A confirmation changes the relationship state through the governed workflow.
- The deterministic result matches the hand calculation.
- A high-impact draft cannot proceed without a valid named approval.
- A stale approval or modified audit chain fails visibly.
- The SAP-aligned adapter uses only services and access that the team has verified.

#### Evaluation data design

The synthetic generator keeps a complete truth graph, hides selected edges from the observable graph, and creates evidence that includes supported, unsupported, and conflicting claims. Evaluation compares recovered links with the hidden truth. The team should split by relationship or supplier group so aliases of the same hidden link do not appear across training, tuning, and test data.

#### Important limitation paragraph

> Synthetic evaluation can show whether the workflow behaves correctly on a constructed and versioned scenario. It cannot show that Substrata will achieve the same link quality, warning time, analyst utility, or financial value on a real manufacturer’s network. Real validation requires authorized enterprise data, domain review, security controls, and prospective workflow testing.

#### Cut first when shortening

Keep three expected impacts, three success measures, and three principal risks. Keep the limitation in speaker notes and place “targets, not results” on the slide.

### Slide 8 expanded content: feasibility plan and deliverables

#### Plan gate: validate the decision

**Activities**

- Interview supply-risk, procurement, or planning practitioners.
- Confirm the exact decision Substrata should improve.
- Identify minimum data, evidence, units, and update frequency.
- Confirm SAP finale access and mentor support.

**Deliverables**

- corrected empathy map;
- ranked user problems;
- minimum scenario definition;
- approved data and SAP access checklist;
- updated Business Model Canvas.

**Exit condition**

> At least one practitioner confirms that the selected workflow and runway view address a real decision problem.

#### Design gate: freeze the safe architecture

**Activities**

- Define entity, relationship, evidence, scenario, action, and approval contracts.
- Identify what the model may propose and what deterministic services must control.
- Set review, approval, expiry, and incomplete-data behavior.
- Select the one integration that best demonstrates SAP relevance.

**Deliverables**

- final user journey;
- frozen demo data contract;
- architecture and agent-human interaction;
- threat and failure checklist;
- evaluation manifest.

**Exit condition**

> The team can explain every input, output, assumption, authority boundary, and failure state in the demo.

#### Build gate: complete the vertical slice

**Activities**

- Harden evidence discovery and confirmation.
- Confirm deterministic graph and runway services.
- Improve mitigation comparison and approval explanation.
- Add one verified read-only SAP integration if available.
- Keep the offline fixture fully functional.

**Deliverables**

- reproducible local build;
- seeded scenario;
- optional SAP adapter;
- judge-ready UI;
- recovery instructions.

**Exit condition**

> A fresh machine can run the complete flow without manually repairing data or changing code.

#### Test gate: prove the claims made in the demo

**Activities**

- Run hidden-edge, cascade, policy, audit, and replay tests.
- Test provider failure and offline fallback.
- Rehearse with users unfamiliar with the project.
- Record confusion, timing, and failure recovery.

**Deliverables**

- versioned evaluation report;
- failed-case examples;
- demo checklist;
- final claim table;
- timed presentation recording.

**Exit condition**

> The team can repeat the demo, explain every number, recover from common failures, and defend every claim.

#### Resource requirements

| Area | Need |
|---|---|
| Domain | One or more supply-chain practitioners and a faculty/industry mentor |
| SAP | Student Learning Hub accounts, confirmed practice system or finale services, and documentation |
| Engineering | Python, TypeScript, graph/data modelling, API integration, testing, and deployment skills |
| Data | Versioned synthetic fixture plus any legally usable sample data |
| Evaluation | Frozen ground truth, scripted measurements, usability tasks, and failure cases |
| Presentation | One stable laptop, offline fallback, recorded backup, and repeated rehearsal |

#### Cut first when shortening

Use one sentence per Plan, Design, Build, and Test box. Keep exit conditions in speaker notes.

### Slide 9 expanded content: closing argument

#### Full closing case

> Substrata should move forward because it addresses a narrow but serious supply-chain failure: the difference between apparent supplier diversity and real upstream concentration. The project does not stop at drawing a network. It asks whether a hidden relationship is supported, gives people a way to confirm or reject it, traces the disruption through a versioned graph, converts operational data into decision runway, and keeps high-impact action under named human authority.
>
> The idea is feasible because the smallest useful prototype needs one scenario, one hidden dependency, one disruption, one deterministic calculation, one approval, and one audit trail. The team already has a working synthetic vertical slice and a wider tenant-platform foundation. The next step is validation, not uncontrolled feature growth.
>
> The SAP connection is based on real business-process fit. Procurement, BOM, inventory, planning, supplier collaboration, extension, and governed AI are the exact boundaries the solution must address. The team will only claim the integrations it can access and explain.

#### Alternative one-sentence pitches

**Recommended**

> Substrata reveals hidden shared supplier dependencies, calculates how long production remains protected, and places every high-impact response under evidence-backed human approval.

**More business-focused**

> Substrata helps manufacturers detect false supplier diversification early enough to protect production through a traceable and governed response.

**More technical**

> Substrata combines cited relationship inference, a versioned supply graph, deterministic cascade analysis, and policy-controlled approval for Tier-N disruption response.

#### Final ask to the judges

> Advance Substrata so the team can validate the user assumptions with practitioners, connect one verified SAP boundary, and demonstrate the complete evidence-to-decision workflow at the finale.

#### Source-note wording

> Public event reporting provides disruption context only. All supplier relationships, inventory values, lead times, actions, and financial assumptions in the demonstration are synthetic.

#### Cut first when shortening

Keep the recommended one-sentence pitch, one short paragraph, and three to five source titles.

### Slide 10 expanded content: Q&A navigation

Prepare four backup routes rather than answering every question verbally:

1. **Problem route:** visibility-gap diagram, empathy map, and Business Model Canvas.
2. **Technical route:** system context, layered architecture, graph schema, and technology map.
3. **Safety route:** agent collaboration, autonomy matrix, approval rule, and audit limitation.
4. **Proof route:** runway calculation, synthetic evaluation, demo replay, and known limitations.

Assign one team member as the first responder for each route. The first answer should be short. Use the backup visual only if the judge asks for detail.

## 9. Recommended shortening order later

When the team is ready to make the deck shorter, cut in this order:

1. Remove repeated definitions that appear on more than one slide.
2. Move formulas, process tables, and implementation details into speaker notes.
3. Keep only one example on slides 3-5.
4. Keep one primary user on slide 4 and describe secondary users aloud.
5. Keep current technology and two or three SAP targets on slide 6.
6. Keep only the most important targets and risks on slide 7.
7. Keep one deliverable in each roadmap phase on slide 8.
8. Keep the one-sentence pitch and strongest sources on slide 9.

Do not cut the synthetic-data disclosure, the SAP integration caveat, the distinction between inferred and confirmed links, the deterministic-math boundary, or the human approval requirement.
