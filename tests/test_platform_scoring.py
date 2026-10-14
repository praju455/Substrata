"""Calibration, supplier-group holdouts and insufficient-label safety gates."""

from random import Random

import joblib
import pytest

from substrata.platform.scoring import FEATURES, feature_vector, train


def labels():
    rng = Random(17)
    return [
        {
            "link_id": f"link-{index}",
            "group_id": f"supplier-{index // 3}",
            "synthetic": True,
            "label": index % 2,
            "provenance": {"kind": "supplier", "note": "Invented labelled fixture"},
            "features": {
                "evidence_count": 1 + index % 2,
                "supplier_source": index % 2,
                "explicit_endpoints": 1,
                "rule_score": 0.2 + 0.6 * (index % 2) + rng.random() * 0.05,
            },
        }
        for index in range(180)
    ]


def test_training_uses_independent_calibration_and_test_groups(tmp_path):
    output = tmp_path / "model"
    manifest = train(labels(), output)
    splits = manifest["report"]["splits"]
    train_groups, calibration, test = (
        set(splits[name]["groups"]) for name in ("train", "calibration", "test")
    )
    assert not train_groups & calibration and not train_groups & test and not calibration & test
    assert manifest["report"]["synthetic"]
    assert 0 <= manifest["report"]["brier_score"] <= 1
    assert (output / "manifest.json").exists()
    loaded = joblib.load(output / "model.joblib")
    probabilities = loaded.predict_proba([feature_vector(row["features"]) for row in labels()])[
        :, 1
    ]
    assert all(0 <= value <= 1 for value in probabilities)


def test_unlabelled_and_insufficient_datasets_cannot_train(tmp_path):
    with pytest.raises(ValueError, match="50 labels"):
        train(labels()[:10], tmp_path / "few")
    invalid = labels()
    invalid[0]["provenance"]["kind"] = "model_prediction"
    with pytest.raises(ValueError, match="supplier"):
        train(invalid, tmp_path / "invalid")
    with pytest.raises(ValueError, match="finite"):
        feature_vector({name: float("nan") for name in FEATURES})
