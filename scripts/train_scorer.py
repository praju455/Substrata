"""Train a small scorer on exported supplier labels; never fine-tune an LLM."""

import argparse
import json
from pathlib import Path

from substrata.platform.scoring import train


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    manifest = train(labels, args.output)
    print(json.dumps(manifest["report"], indent=2))


if __name__ == "__main__":
    main()
