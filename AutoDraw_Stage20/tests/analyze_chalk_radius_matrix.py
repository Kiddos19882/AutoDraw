#!/usr/bin/env python3
"""Summarize saved CHALK radius matrix experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PREPARATION_DIR = Path(__file__).resolve().parents[1] / "source" / "preparation"
if str(PREPARATION_DIR) not in sys.path:
    sys.path.insert(0, str(PREPARATION_DIR))

from chalk_radius_matrix import summarize_chalk_radius_matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results_dir",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "results" / "brush_behavior_tests",
    )
    parser.add_argument("--output", type=Path, help="Write summary JSON to this path.")
    args = parser.parse_args()

    documents = []
    for path in args.results_dir.rglob("experiment.json"):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(document, dict) and document.get("chalk_radius_matrix"):
            document["experiment_dir"] = str(path.parent)
            documents.append(document)

    summary = summarize_chalk_radius_matrix(documents)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
