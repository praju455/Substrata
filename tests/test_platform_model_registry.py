"""Model activation, synthetic production gate and artifact integrity."""

import pytest
from test_platform_evidence import actor
from test_platform_scoring import labels

from substrata.platform.database import tenant_transaction
from substrata.platform.records import add
from substrata.platform.scoring import activate, score, train_tenant


def test_registry_train_activate_and_hash_tampering(platform, tmp_path, monkeypatch):
    monkeypatch.setenv("SUBSTRATA_MODEL_REGISTRY", str(tmp_path / "registry"))
    with tenant_transaction(platform.engine, "alpha") as session:
        for label in labels():
            add(session, "alpha", "training_label", "labelled", label)
    trained = train_tenant(platform, actor())
    monkeypatch.setenv("SUBSTRATA_ENV", "production")
    with pytest.raises(ValueError, match="synthetic"):
        activate(platform, actor(), trained["id"])
    monkeypatch.setenv("SUBSTRATA_ENV", "development")
    active = activate(platform, actor(), trained["id"])
    assert active["status"] == "active"
    result = score(platform, "alpha", labels()[0]["features"])
    assert result["calibrated"] and 0 <= result["score"] <= 1
    model = tmp_path / "registry" / "alpha" / trained["id"] / "model.joblib"
    model.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        score(platform, "alpha", labels()[0]["features"])
    assert not score(platform, "beta", labels()[0]["features"])["calibrated"]
