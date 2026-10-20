"""Reproducible evaluation of recorded platform extraction responses."""

import hashlib
from pathlib import Path

from substrata.platform.providers import PROMPT_VERSION, Extraction
from substrata.seed import canonical


def evaluate_recorded_fixture(fixture: dict) -> dict:
    if fixture.get("fixture_version") is None or not isinstance(fixture.get("cases"), list):
        raise ValueError("Extraction fixture requires a version and cases.")
    true_positive = false_positive = false_negative = citation_errors = 0
    cases = []
    for case in fixture["cases"]:
        documents = {row["id"]: row["text"] for row in case["documents"]}
        entities = {row["id"]: row for row in case["entities"]}
        extraction = Extraction.model_validate(case["recorded_response"])
        expected = {
            (row["source"], row["target"], row["type"]) for row in case["expected_relations"]
        }
        predicted = set()
        case_citation_errors = 0
        for relation in extraction.relations:
            citation = relation.citation
            document = documents.get(citation.document_id)
            valid = (
                document is not None
                and document[citation.start : citation.end] == citation.passage
                and relation.source in entities
                and relation.target in entities
                and relation.source != relation.target
                and entities[relation.source]["name"] in citation.passage
                and entities[relation.target]["name"] in citation.passage
            )
            if not valid:
                case_citation_errors += 1
                continue
            predicted.add((relation.source, relation.target, relation.type))
        tp = len(expected & predicted)
        fp = len(predicted - expected)
        fn = len(expected - predicted)
        true_positive += tp
        false_positive += fp
        false_negative += fn
        citation_errors += case_citation_errors
        cases.append(
            {
                "id": case["id"],
                "industry": case["industry"],
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "citation_errors": case_citation_errors,
            }
        )
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
    )
    return {
        "evaluation_scope": (
            "Recorded synthetic provider responses; no live-provider or real-world accuracy claim."
        ),
        "fixture_version": fixture["fixture_version"],
        "fixture_sha256": hashlib.sha256(canonical(fixture).encode()).hexdigest(),
        "prompt_version": PROMPT_VERSION,
        "provider_recording_versions": sorted(
            {
                case["recording"]["provider"]
                + "/"
                + case["recording"]["model"]
                + "/"
                + case["recording"]["version"]
                for case in fixture["cases"]
            }
        ),
        "metrics": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": precision,
            "recall": recall,
            "citation_errors": citation_errors,
        },
        "cases": cases,
    }


def load_and_evaluate(path: Path) -> dict:
    import json

    return evaluate_recorded_fixture(json.loads(path.read_text(encoding="utf-8")))
