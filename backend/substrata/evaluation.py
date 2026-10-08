"""Measured frozen-fixture evaluation, never a claim of real-world accuracy."""

import hashlib
import json
import math
import random
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from substrata.agent_models import EvaluationExample, EvaluationMetric, EvaluationRun
from substrata.cascade import cascade
from substrata.database import build_engine, transaction, upgrade_database
from substrata.graph import NetworkXGraphStore
from substrata.mapper import map_evidence
from substrata.models import GraphEdge
from substrata.seed import AS_OF, DATASET, canonical, seed_database, write_fixtures


def evaluate(target_engine, hide_share: float = 1, threshold: float = 0.75) -> dict:
    if not 0 < hide_share <= 1:
        raise ValueError("Hide share must be greater than zero and at most one.")
    with TemporaryDirectory() as directory:
        directory = Path(directory)
        fixture_hash = write_fixtures(directory)
        truth = json.loads((directory / "true_graph.json").read_text())
        hidden = [e for e in truth["edges"] if e["hidden"]]
        expected = {
            e["id"] for e in random.Random(42).sample(hidden, math.ceil(len(hidden) * hide_share))
        }
        engine = build_engine(directory / "evaluation.sqlite3")
        try:
            upgrade_database(engine)
            seed_database(engine, directory)
            with transaction(engine) as session:
                for item in hidden:
                    if item["id"] not in expected:
                        session.add(
                            GraphEdge(
                                **{k: v for k, v in item.items() if k != "hidden"},
                                graph_version=1,
                                status="declared",
                                valid_from=AS_OF,
                            )
                        )
            outcome = map_evidence(engine, threshold=threshold)
            predicted = set(outcome["inferred"])
            tp, fp, fn = (
                len(predicted & expected),
                len(predicted - expected),
                len(expected - predicted),
            )
            impacts = cascade(
                engine, NetworkXGraphStore(engine).snapshot(), "site_shared_source", 0.9
            ).impacts
            covers = [i.cover_days for i in impacts if i.status == "complete"]
            metrics = {
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "precision": tp / (tp + fp) if tp + fp else 0,
                "recall": tp / (tp + fn) if tp + fn else 0,
                "review_volume": len(outcome["confirmation_requests"]),
                "warning_days_gained_vs_tier1": min(covers) if covers else 0,
            }
            report = {
                "dataset_version": DATASET,
                "generator_version": "1.0",
                "seed": 42,
                "fixture_sha256": fixture_hash,
                "corpus_sha256": hashlib.sha256(
                    (directory / "corpus.json").read_bytes()
                ).hexdigest(),
                "hide_share": hide_share,
                "threshold": threshold,
                "provider": "local-mock",
                "model": "ownership-template-v1",
                "prompt_version": "ownership-extraction-v1",
                "evaluation_scope": "Frozen synthetic fixture; no trained model or "
                "held-out generalisation claim",
                "metrics": metrics,
                "expected": sorted(expected),
                "predicted": sorted(predicted),
                "false_positive_ids": sorted(predicted - expected),
                "false_negative_ids": sorted(expected - predicted),
                "warning_assumption": "Tier-1-only alert occurs at stock exhaustion "
                "(zero warning); deep view alerts at the replay event. "
                "Gain is minimum affected stock cover, not observed enterprise data.",
                "limitation": "Measured only on invented data and template extraction. "
                "Not real-world accuracy or business value.",
            }
        finally:
            engine.dispose()
    run_id = str(uuid4())
    with transaction(target_engine) as session:
        session.add(
            EvaluationRun(
                id=run_id,
                dataset_version=DATASET,
                seed=42,
                config={k: v for k, v in report.items() if k != "metrics"},
                metrics=metrics,
            )
        )
        session.flush()
        for name, value in metrics.items():
            session.add(EvaluationMetric(evaluation_run_id=run_id, name=name, value=value))
        for index, edge_id in enumerate(sorted(expected | predicted)):
            session.add(
                EvaluationExample(
                    id=f"{run_id}_{index}",
                    evaluation_run_id=run_id,
                    edge_id=edge_id,
                    expected=edge_id in expected,
                    predicted=edge_id in predicted,
                )
            )
    return json.loads(canonical(report))
