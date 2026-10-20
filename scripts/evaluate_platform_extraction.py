"""Evaluate versioned recorded responses through platform schema/citation checks."""

import argparse
import json
from pathlib import Path

from scripts.dev import ROOT
from substrata.platform.extraction_evaluation import load_and_evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=ROOT / "tests/fixtures/platform_extraction_recorded.json",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/platform_extraction_evaluation.json"
    )
    args = parser.parse_args()
    report = load_and_evaluate(args.fixture)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
