# Diagram manifest

All diagrams are design artifacts for the Substrata proposal. Each is stored as editable Excalidraw JSON plus SVG and PNG. **[Design]** The repository exports were created locally with `mcp-excalidraw-server`; no share upload was used. Its optional `share` command uploads diagram data to a third-party Excalidraw service, so it must not be used for confidential content without approval. **[Design]**

## Visual language

| Color | Meaning |
|---|---|
| Gray | Data sources, context, stores or neutral controls |
| Purple | Knowledge graph, relationships or deterministic graph math |
| Teal | Agents, application services or pretrained AI boundary |
| Amber | Human approval, review or business assumption |
| Red | Risk, disruption, prohibition, gate or unresolved availability |

Every diagram uses a light background, title inside the scene and short labels intended to remain readable near 900 px width. **[Design]** PNGs are the README default; SVGs support scalable viewing; `.excalidraw` files are the editable source.

## Manifest

| # | Title | This diagram answers | README section | Files | Share URL | Status |
|---:|---|---|---|---|---|---|
| 01 | Visibility gap / hidden shared dependency | Why can three Tier-1 suppliers still be one risk? | 1 | [`excalidraw`](01-visibility-gap.excalidraw) · [`svg`](01-visibility-gap.svg) · [`png`](01-visibility-gap.png) | Not used | Reviewed |
| 02 | Supply-chain runway example | When does stock cover end relative to requalification, and how is that different from the hackathon schedule? | Worked example | [`excalidraw`](02-runway-timeline.excalidraw) · [`svg`](02-runway-timeline.svg) · [`png`](02-runway-timeline.png) | Not used | Reviewed after schedule clarification |
| 03 | System context | Who and what exchanges data with Substrata? | 6 | [`excalidraw`](03-system-context.excalidraw) · [`svg`](03-system-context.svg) · [`png`](03-system-context.png) | Not used | Reviewed |
| 04 | Layered architecture | Where do data, storage, graph, agents, UI and simulation belong? | 6 | [`excalidraw`](04-layered-architecture.excalidraw) · [`svg`](04-layered-architecture.svg) · [`png`](04-layered-architecture.png) | Not used | Reviewed |
| 05 | Agent collaboration + human gate | How do bounded agents reach an approved simulated action? | 7 | [`excalidraw`](05-agent-collaboration.excalidraw) · [`svg`](05-agent-collaboration.svg) · [`png`](05-agent-collaboration.png) | Not used | Reviewed |
| 06 | Autonomy matrix | What is automatic, review-required or prohibited? | 7 | [`excalidraw`](06-autonomy-matrix.excalidraw) · [`svg`](06-autonomy-matrix.svg) · [`png`](06-autonomy-matrix.png) | Not used | Reviewed |
| 07 | Supply graph schema | Which entities and governed relationship fields drive analysis? | 8 | [`excalidraw`](07-graph-schema.excalidraw) · [`svg`](07-graph-schema.svg) · [`png`](07-graph-schema.png) | Not used | Reviewed |
| 08 | Link-inference pipeline | How does evidence become an inferred or reviewed edge without training? | 9–10 | [`excalidraw`](08-link-inference-pipeline.excalidraw) · [`svg`](08-link-inference-pipeline.svg) · [`png`](08-link-inference-pipeline.png) | Not used | Reviewed |
| 09 | Cascade simulation | How does one event become deterministic plant impact without confusing business time with project time? | Worked example | [`excalidraw`](09-cascade-simulation.excalidraw) · [`svg`](09-cascade-simulation.svg) · [`png`](09-cascade-simulation.png) | Not used | Reviewed after schedule clarification |
| 10 | Six-minute demo replay | What will judges see, and in what order? | 13 | [`excalidraw`](10-demo-replay.excalidraw) · [`svg`](10-demo-replay.svg) · [`png`](10-demo-replay.png) | Not used | Reviewed |
| 11 | Persistence + provenance | What is authoritative, versioned and auditable? | 8 / architecture | [`excalidraw`](11-persistence-model.excalidraw) · [`svg`](11-persistence-model.svg) · [`png`](11-persistence-model.png) | Not used | Reviewed |
| 12 | Technology map | Which proposed technologies sit behind each boundary? | 14 | [`excalidraw`](12-tech-stack.excalidraw) · [`svg`](12-tech-stack.svg) · [`png`](12-tech-stack.png) | Not used | Reviewed |
| 13 | Deployment topology | What runs locally and what is an entitlement-dependent SAP stretch? | 14 | [`excalidraw`](13-deployment-topology.excalidraw) · [`svg`](13-deployment-topology.svg) · [`png`](13-deployment-topology.png) | Not used | Reviewed |
| 14 | Evaluation gates + roadmap | What must be measured before each phase can support a claim? | 15–16 | [`excalidraw`](14-evaluation-roadmap.excalidraw) · [`svg`](14-evaluation-roadmap.svg) · [`png`](14-evaluation-roadmap.png) | Not used | Reviewed |
| 15 | Empathy map | What does the unvalidated analyst persona say, think, do and feel? | 5 | [`excalidraw`](15-empathy-map.excalidraw) · [`svg`](15-empathy-map.svg) · [`png`](15-empathy-map.png) | Not used | Reviewed after overlap fix |
| 16 | Business Model Canvas | Which business hypotheses must the team validate? | 5 | [`excalidraw`](16-business-model-canvas.excalidraw) · [`svg`](16-business-model-canvas.svg) · [`png`](16-business-model-canvas.png) | Not used | Reviewed |

## Why no additional diagrams

The HQNN style reference contains domain-specific quantum-circuit, training-pipeline and deployment-detail visuals. Substrata has no credible use for a quantum/training diagram because core scope does not train a model; adding one would imply work that is not planned. **[Design]** API endpoint and risk lists remain tables because their relationships are clearer in text. **[Design]** Evaluation and roadmap are intentionally merged in Figure 14 because phase progression depends on passing the measurement gate. **[Design]** Visibility gap and shared dependency are intentionally merged in Figure 1 because they are the same reader question. **[Design]**

## Editing and export

Open the `.excalidraw` file in a compatible editor. For a local repeatable export with the CLI, import the file and render PNG/SVG; review both for clipping and bound-text changes. **[Design]** If the local renderer is unavailable, a manual Excalidraw export should use background on and embedded scene on. A manual/share upload is still a third-party disclosure and must be treated accordingly. **[Design]**
