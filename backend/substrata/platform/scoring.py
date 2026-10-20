"""Small calibrated gradient-boosted scorer trained only on supplier response labels."""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import joblib
import numpy as np
import sklearn
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score, brier_score_loss, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit

from substrata.platform.database import tenant_transaction
from substrata.platform.records import add, encode, list_records, require_record
from substrata.seed import canonical

FEATURE_VERSION = "supplier-link-features-v1"
FEATURES = ("evidence_count", "supplier_source", "explicit_endpoints", "rule_score")


def features(link):
    return {
        "evidence_count": len(link.evidence),
        "supplier_source": int(link.provenance.kind == "supplier"),
        "explicit_endpoints": 1,
        "rule_score": link.confidence,
    }


def feature_vector(values):
    vector = [float(values[name]) for name in FEATURES]
    if not all(np.isfinite(value) and value >= 0 for value in vector):
        raise ValueError("Features must be finite and nonnegative.")
    if not all(vector[index] <= 1 for index in (1, 2, 3)):
        raise ValueError("Binary and rule-confidence features must be bounded by one.")
    return vector


def train(labels, output_dir: Path):
    if len(labels) < 50 or len({row["group_id"] for row in labels}) < 10:
        raise ValueError("Training requires at least 50 labels and 10 independent supplier groups.")
    if any(row.get("provenance", {}).get("kind") != "supplier" for row in labels):
        raise ValueError("Training labels must come from supplier confirm/reject responses.")
    groups = np.array([row["group_id"] for row in labels])
    x = np.array([feature_vector(row["features"]) for row in labels])
    y = np.array([row["label"] for row in labels])
    if any(value not in {0, 1} for value in y):
        raise ValueError("Supplier training labels must be binary.")
    remaining, test = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(x, y, groups)
    )
    train_rel, calibrate_rel = next(
        GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=43).split(
            x[remaining], y[remaining], groups[remaining]
        )
    )
    training, calibration = remaining[train_rel], remaining[calibrate_rel]
    splits = {"train": training, "calibration": calibration, "test": test}
    if any(len(set(y[index])) != 2 for index in splits.values()):
        raise ValueError("Each independent split needs confirmed and rejected supplier labels.")
    raw = GradientBoostingClassifier(
        n_estimators=40, max_depth=2, learning_rate=0.05, random_state=42
    )
    raw.fit(x[training], y[training])
    calibrated = CalibratedClassifierCV(FrozenEstimator(raw), method="sigmoid")
    calibrated.fit(x[calibration], y[calibration])
    probabilities = calibrated.predict_proba(x[test])[:, 1]
    predicted = probabilities >= 0.5
    observed, expected = calibration_curve(y[test], probabilities, n_bins=5, strategy="quantile")
    report = {
        "precision": float(precision_score(y[test], predicted, zero_division=0)),
        "recall": float(recall_score(y[test], predicted, zero_division=0)),
        "average_precision": float(average_precision_score(y[test], probabilities)),
        "brier_score": float(brier_score_loss(y[test], probabilities)),
        "threshold": 0.5,
        "test_positive": int(sum(y[test])),
        "test_negative": int(sum(1 - y[test])),
        "calibration": {"observed": observed.tolist(), "predicted": expected.tolist()},
        "splits": {
            name: {"rows": len(index), "groups": sorted(set(groups[index]))}
            for name, index in splits.items()
        },
        "errors": [
            {"link_id": labels[index]["link_id"], "expected": int(y[index]), "score": float(score)}
            for index, score in zip(test, probabilities, strict=True)
            if int(score >= 0.5) != y[index]
        ],
        "synthetic": any(row.get("synthetic", True) for row in labels),
        "scope": "Supplier-labelled holdout split by source supplier; no LLM fine-tuning.",
        "limitation": (
            "Calibration and scores apply to this labelled distribution, not arbitrary industries."
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    model_path = output_dir / "model.joblib"
    joblib.dump(calibrated, model_path)
    manifest = {
        "feature_version": FEATURE_VERSION,
        "features": list(FEATURES),
        "model_type": "GradientBoostingClassifier+sigmoid",
        "sklearn_version": sklearn.__version__,
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "labels_sha256": hashlib.sha256(canonical(labels).encode()).hexdigest(),
        "created_at": datetime.now(UTC).isoformat(),
        "report": report,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def registry_root():
    return Path(os.environ.get("SUBSTRATA_MODEL_REGISTRY", "data/models")).resolve()


def train_tenant(store, actor):
    actor.require("admin")
    labels = [
        record["payload"]
        for record in list_records(store, actor.tenant_id, kind="training_label", limit=500)
    ]
    id = str(uuid4())
    artifact = registry_root() / actor.tenant_id / id
    manifest = train(labels, artifact)
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        record = add(session, actor.tenant_id, "model_registry", "candidate", manifest, id)
        store.append(
            session,
            org,
            "scorer.trained",
            actor.subject,
            {
                "id": id,
                "model_sha256": manifest["model_sha256"],
                "synthetic": manifest["report"]["synthetic"],
            },
        )
        return encode(record)


def activate(store, actor, id):
    actor.require("admin")
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        record = require_record(session, actor.tenant_id, id, "model_registry")
        report = record.payload["report"]
        if report["synthetic"] and os.environ.get("SUBSTRATA_ENV", "development") != "development":
            raise ValueError("A synthetic-trained scorer cannot be activated for production.")
        if report["precision"] < 0.8 or report["recall"] < 0.7:
            raise ValueError("Scorer holdout precision/recall did not meet activation gates.")
        for previous in session.query(type(record)).filter_by(
            tenant_id=actor.tenant_id, kind="model_registry", status="active"
        ):
            previous.status = "retired"
        record.status = "active"
        store.append(session, org, "scorer.activated", actor.subject, {"id": id, "report": report})
        return encode(record)


def score(store, tenant_id, values):
    models = list_records(store, tenant_id, kind="model_registry", status="active")
    if not models:
        return {
            "score": 0.65,
            "model_version": "uncalibrated-rule-v1",
            "calibrated": False,
            "feature_version": FEATURE_VERSION,
            "evaluation_scope": None,
            "evaluation_metrics": {},
            "synthetic_evaluation": None,
        }
    record = models[0]
    path = registry_root() / tenant_id / record["id"] / "model.joblib"
    if hashlib.sha256(path.read_bytes()).hexdigest() != record["payload"]["model_sha256"]:
        raise ValueError("Model artifact integrity check failed.")
    # Artifacts are server-generated, never uploaded or caller-selected pickle paths.
    model = joblib.load(path)
    return {
        "score": float(model.predict_proba([feature_vector(values)])[0, 1]),
        "model_version": record["id"],
        "calibrated": True,
        "feature_version": record["payload"]["feature_version"],
        "calibration_scope": record["payload"]["report"]["scope"],
        "evaluation_scope": record["payload"]["report"]["scope"],
        "evaluation_metrics": {
            name: float(record["payload"]["report"][name])
            for name in ("precision", "recall", "average_precision", "brier_score")
        },
        "synthetic_evaluation": bool(record["payload"]["report"]["synthetic"]),
    }
