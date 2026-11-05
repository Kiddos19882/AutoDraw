from __future__ import annotations

"""Aggregate per-run renderer acceptance reports into the multi-axis series gate."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "preparation"))
from renderer_acceptance import summarize_multi_axis_series


def collect_reports(inputs: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    reports: list[dict[str, Any]] = []
    sources: list[str] = []
    seen_paths: set[Path] = set()
    for item in inputs:
        candidates = sorted(item.rglob("comparison-report-independent-transform.json")) if item.is_dir() else [item]
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            if not candidate.is_file():
                raise FileNotFoundError(candidate)
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"Report must be a JSON object: {candidate}")
            reports.append(data)
            sources.append(str(candidate))
    return reports, sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path,
                        help="Per-run reports or directories containing them.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--required-repeats", type=int, default=3)
    args = parser.parse_args()

    reports, sources = collect_reports(args.reports)
    result = summarize_multi_axis_series(reports, required_repeats=args.required_repeats)
    result["source_reports"] = sources
    result["report_count"] = len(reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "report_count": len(reports),
        "output": str(args.output),
        "orientations": {
            name: {
                "status": item["status"],
                "accepted": len(item["accepted_runs"]),
                "rejected": len(item["rejected_runs"]),
                "missing": item["missing_valid_repeats"],
                "duplicates": item["duplicate_run_ids"],
            }
            for name, item in result["orientations"].items()
        },
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
