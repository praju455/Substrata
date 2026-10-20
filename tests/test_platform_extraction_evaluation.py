"""Recorded platform extraction evaluation remains reproducible and honestly labelled."""

from pathlib import Path

from substrata.platform.extraction_evaluation import load_and_evaluate


def test_recorded_platform_extraction_report():
    fixture = Path(__file__).parent / "fixtures/platform_extraction_recorded.json"
    report = load_and_evaluate(fixture)
    assert report["fixture_version"] == "platform-extraction-synthetic-v1"
    assert report["prompt_version"] == "platform-link-extraction-v1"
    assert report["metrics"] == {
        "true_positive": 2,
        "false_positive": 0,
        "false_negative": 2,
        "precision": 1.0,
        "recall": 0.5,
        "citation_errors": 1,
    }
    assert "synthetic" in report["evaluation_scope"].lower()
