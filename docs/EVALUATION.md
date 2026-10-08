# Evaluation plan

> **Current status:** the executed frozen-fixture results appear in the generated results section below. They measure a narrow synthetic template baseline, not held-out generalisation or real-world accuracy. Other metrics and targets in this design plan remain unmeasured. **[Design]**

## 1. Claims under test

| ID | Falsifiable design hypothesis | Evidence required |
|---|---|---|
| H1 | Layered retrieval/extraction can recover useful hidden synthetic links without flooding review. **[Design]** | Held-out precision, recall, PR curve and review volume |
| H2 | Tier-N analysis provides more warning in the constructed scenario than a Tier-1-only view. **[Design]** | Paired warning-day calculation on identical snapshots |
| H3 | Reviewers can trace an inferred link and runway result to evidence and formulas. **[Design]** | Task completion, errors and qualitative confusion points |
| H4 | Policy prevents every prohibited prototype action and pauses every configured high-impact action. **[Design]** | Adversarial policy test suite |
| H5 | The judge replay is reproducible offline. **[Design]** | Canonical output hashes across repeated seeded runs |

## 2. Planned synthetic dataset

The minimum judge fixture is proposed to contain one focal product, eight components, twelve supplier sites across four regions, three apparent Tier-1 alternatives sharing one hidden Tier-3 source, two plants, five alternative-supplier candidates, six dated public-event records and three confirmation outcomes. **[Design]** Implemented fixture: seed 42, generator 1.0, 32 nodes, seven evidence snippets, four hidden ownership relationships and six synthetic events. Aliases, transliterations and broad semantic retrieval remain future evaluation work; the generator list below is a design target.

The generator should emit:

- full ground-truth edges before masking; **[Design]**
- aliases, transliterations, address variation, missing identifiers and duplicated reports; **[Design]**
- evidence text with supported, unsupported and conflicting relationship claims; **[Design]**
- declared, inferred-target, rejected and expired relationships; **[Design]**
- unit-consistent stock, consumption, in-transit and lead-time records plus deliberately invalid cases; **[Design]**
- a manifest containing seed, generator version and class prevalence. **[Design]**

The October 2025 Nexperia chronology supplies replay context only. **[Design]** It is not used as ground truth for real company relationships, inventory or financial impact. **[Design]**

## 3. Split and leakage protocol

1. Generate the full graph and evidence corpus from a recorded seed. **[Design]**
2. Split by relationship/entity clusters before prompt or weight selection so aliases of one hidden link do not cross train/dev/test. **[Design]**
3. Hide test edges and their direct declarations from the observable graph. **[Design]**
4. Freeze the test manifest and hash before selecting inference thresholds. **[Design]**
5. Tune prompts/rules on development data only; no core model training is performed. **[Design]**
6. Run once on the held-out test set and publish errors, not only aggregate scores. **[Design]**

Exact split proportions are **[TBD]**. If the optional GNN baseline is attempted, it receives only synthetic training data, uses the same held-out test edges and is reported separately. **[Design]**

## 4. Metrics and targets

| Area | Metric | Target, not result |
|---|---|---:|
| Retrieval | Recall@5 | ≥ 0.90 **[Design]** |
| Link inference | Precision at review threshold | ≥ 0.80 **[Design]** |
| Link inference | Recall at review threshold | ≥ 0.70 **[Design]** |
| Structured extraction | First-pass schema-valid JSON | ≥ 0.98 **[Design]** |
| Event classification | Macro-F1 | ≥ 0.80 **[Design]** |
| Cascade | Exact curated calculations | 100% **[Design]** |
| Policy | Prohibited actions blocked | 100% **[Design]** |
| Audit | Injected mutations detected | 100% **[Design]** |
| Replay | Identical canonical output | 10/10 runs **[Design]** |
| Human factors | Scenario comprehension time/error | Baseline and target **[TBD]** |

Precision/recall reports must include raw counts, prevalence, threshold, confidence interval where meaningful and a confusion/error table. **[Design]** “Accuracy” alone is not an acceptable link metric for an imbalanced graph. **[Design]**

## 5. Baselines and ablations

| Comparison | Purpose |
|---|---|
| Exact identifiers only | Lower-bound precision-oriented mapper **[Design]** |
| Normalized names + heuristic rules | Simple non-LLM baseline **[Design]** |
| Pretrained embeddings only | Retrieval contribution **[Design]** |
| Heuristics + LLM extraction | Planned layered method **[Design]** |
| Remove evidence-recency signal | Measure dependence on freshness **[Design]** |
| Remove supplier confirmation | Measure downstream review/false-positive effect **[Design]** |
| Optional synthetic GNN | Research stretch, reported separately **[Design]** |

## 6. Runway and decision evaluation

For each constructed disruption, calculate the alert time under a Tier-1-only observable graph and under the permitted hidden-link inference snapshot. **[Design]** Report paired `warning_days = production_impact_time - actionable_alert_time`, without claiming that the constructed lead times generalize. **[Design]** Also report how many proposed actions were automatic, required review, were blocked or could not be calculated due to missing data. **[Design]**

## 7. Reporting template

```text
Run ID:
Dataset/generator version and hash:
Seed and split manifest:
Observable vs hidden ground truth:
Rule/prompt/model/provider versions:
Threshold-selection rule:
Metrics with raw counts:
Latency and estimated inference cost:
Failure examples:
Known leakage checks:
Limitations:
```

## 8. Required limitation statement

> Because the evaluation data is synthetic, a successful result would show that the method works on a constructed, versioned scenario. It would **not** show that Substrata will achieve the same link quality, warning time, analyst utility or business value on a real company's network. **[Design]** Real validation requires legally usable enterprise data, domain review, security controls and prospective workflow testing. **[TBD]**

<!-- measured-results -->

## Measured synthetic fixture results

Generated by `python scripts/dev.py evaluate`. These are measurements on invented data with the deterministic mock, not real-world accuracy or a held-out benchmark.

| Metric | Measured value |
|---|---:|
| false_negatives | 2 |
| false_positives | 0 |
| precision | 1 |
| recall | 0.5 |
| review_volume | 3 |
| true_positives | 2 |
| warning_days_gained_vs_tier1 | 18 |

Seed: 42; hide share: 1; threshold: 0.75. Fixture SHA-256: `90a5cc9e5249aa17bdcd4dcb76a89479266f6f9d4d5ec52489a961643075b55e`.

Tier-1-only alert occurs at stock exhaustion (zero warning); deep view alerts at the replay event. Gain is minimum affected stock cover, not observed enterprise data.

The mock uses a fixed ownership sentence template and frozen reliability weights. No parameter tuning, split-based model training or independent generalisation test was performed. Raw expected/predicted IDs and errors are in `data/evaluation.json`; the run, examples and metrics are persisted in the evaluation tables.
