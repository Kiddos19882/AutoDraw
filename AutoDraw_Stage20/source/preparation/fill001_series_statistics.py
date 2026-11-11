"""FILL001-SERIES-001 post-run statistics from immutable per-task evidence.

No gameplay, screenshots, or measured CHALK values are synthesized.
Exact CHALK is accepted only from run-bound point-count delta.
Invalid, absent and quality-FAIL captures remain visible and cannot become winners.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

from fill001_series_runner import validate_manifest, SeriesBlocked

SCHEMA = "FILL001_SERIES_ANALYTICS_V1"
METRICS = (
    "coverage_fraction", "leakage_pixels",
    "leakage_pixels_beyond_allowed_halo", "max_perimeter_overshoot_logical_px",
    "stroke_count", "completed_strokes", "duration_seconds",
    "event_count", "dropped_events", "monitor_errors", "bridge_failures",
    "sequence_gaps", "path_length_logical_pixels",
    "color_switches", "brush_switches",
    "mean_fps", "min_fps",
)


def _numeric(x: Any) -> bool:
    return type(x) in (int, float) and x == x and abs(x) != float("inf")


def _scalar_metrics(runtime: dict) -> dict:
    """Only whitelist numeric, run-tagged fields with preserved provenance."""
    out = {}
    sources = [
        runtime.get("quality_metrics"),
        runtime.get("stage6_summary"),
        runtime.get("monitor_summary"),
        runtime.get("statistics"),
    ]
    for src in sources:
        if not isinstance(src, dict):
            continue
        for name in METRICS:
            value = src.get(name)
            if name not in out and _numeric(value):
                out[name] = value
    return out


def _summary(values: list[int | float]) -> dict:
    if not values:
        return {"status": "NOT_EVALUATED", "count": 0}
    return {
        "status": "MEASURED", "count": len(values),
        "min": min(values), "max": max(values),
        "mean": mean(values), "median": median(values),
        "population_stdev": pstdev(values) if len(values) > 1 else 0,
    }


def analyze_series(manifest: dict, results_dir: Path) -> dict:
    validate_manifest(manifest)
    folder = Path(results_dir)
    rows, missing, rejected = [], [], []
    for task in manifest["tasks"]:
        filename = folder / (task["task_id"] + ".json")
        if not filename.is_file():
            missing.append(task["task_id"])
            continue
        raw = filename.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        try:
            item = json.loads(raw)
            if (item.get("task_id") != task["task_id"]
                    or item.get("series_id") != manifest["series_id"]
                    or item.get("manifest_sha256") != manifest["manifest_sha256"]
                    or item.get("schema") != "FILL001_SERIES_RUN_V1"):
                raise SeriesBlocked("Run manifest identity differs")
            state = item.get("status")
            if state not in ("PASS", "QUALITY_FAIL", "BLOCKED"):
                raise SeriesBlocked("Unsupported run status")
            runtime = item.get("runtime")
            exact = None
            if state in ("PASS", "QUALITY_FAIL"):
                if (not isinstance(runtime, dict)
                        or runtime.get("monitor_binding") != "EXACT_RUN_BOUND"
                        or runtime.get("task_id") != task["task_id"]
                        or runtime.get("quality_gate") != ("PASS" if state == "PASS" else "FAIL")
                        or type(runtime.get("pre_pointCount")) is not int
                        or type(runtime.get("post_pointCount")) is not int
                        or runtime["post_pointCount"] < runtime["pre_pointCount"]
                        or type(item.get("actual_chalk")) is not int
                        or item["actual_chalk"] != runtime["post_pointCount"] - runtime["pre_pointCount"]):
                    raise SeriesBlocked("Exact CHALK cannot be re-established")
                exact = item["actual_chalk"]
            rows.append({
                "task_id": task["task_id"], "order": task["order"],
                "shape_id": task["shape_id"], "fill_method": task["fill_method"],
                "brush_radius": task["brush_radius"],
                "status": state, "quality_gate": item.get("quality_gate"),
                "exact_chalk": exact,
                "run_id": runtime.get("run_id") if isinstance(runtime, dict) else None,
                "session_id": runtime.get("session_id") if isinstance(runtime, dict) else None,
                "metrics": _scalar_metrics(runtime) if isinstance(runtime, dict) else {},
                "source_sha256": digest,
            })
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append({"task_id": task["task_id"], "reason": str(exc),
                             "source_sha256": digest})
    grouped = {}
    for axes in (("shape_id",), ("fill_method",), ("brush_radius",),
                 ("shape_id", "fill_method", "brush_radius")):
        label = "+".join(axes)
        cells = defaultdict(list)
        for row in rows:
            cells["|".join(str(row[a]) for a in axes)].append(row)
        view = {}
        for cell, members in sorted(cells.items()):
            good = [m for m in members if m["status"] == "PASS"]
            fail = [m for m in members if m["status"] == "QUALITY_FAIL"]
            metric_values = {
                name: [m["metrics"][name] for m in good if name in m["metrics"]]
                for name in METRICS
            }
            view[cell] = {
                "observations": len(members),
                "quality_pass": len(good), "quality_fail": len(fail),
                "blocked": sum(m["status"] == "BLOCKED" for m in members),
                "chalk_quality_pass": _summary([m["exact_chalk"] for m in good]),
                "chalk_quality_fail": _summary([m["exact_chalk"] for m in fail]),
                "metrics_quality_pass": {
                    name: _summary(values) for name, values in metric_values.items()
                },
            }
        grouped[label] = view
    candidates = [
        x for x in rows if x["status"] == "PASS" and x["exact_chalk"] is not None
    ]
    # Ranking is descriptive for observed runs, not a production decision.
    candidates.sort(key=lambda r: (r["exact_chalk"], r["order"]))
    return {
        "schema": SCHEMA,
        "series_id": manifest["series_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "status": "PARTIAL" if missing or rejected else "COMPLETE",
        "scheduled": len(manifest["tasks"]),
        "observed": len(rows),
        "missing": missing, "rejected": rejected,
        "quality_pass": sum(x["status"] == "PASS" for x in rows),
        "quality_fail": sum(x["status"] == "QUALITY_FAIL" for x in rows),
        "blocked": sum(x["status"] == "BLOCKED" for x in rows),
        "ranking_basis": "observed quality PASS only; no repeatability or E5 implied",
        "lowest_observed_quality_pass_chalk": (
            {"task_id": candidates[0]["task_id"],
             "exact_chalk": candidates[0]["exact_chalk"]} if candidates else None
        ),
        "grouped_statistics": grouped,
        "runs": rows,
        "independent_game_E5": "NOT_RUN",
        "production_eligible": False,
    }


def write_analysis(manifest: dict, results_dir: Path, output: Path) -> Path:
    report = analyze_series(manifest, results_dir)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write("\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only statistics from immutable FILL001 series JSON")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    m = json.loads(args.manifest.read_text(encoding="utf-8"))
    p = write_analysis(m, args.results, args.output)
    report = json.loads(p.read_text(encoding="utf-8"))
    print(f"Series analytics: {p}; {report['observed']}/{report['scheduled']} run records")
    return 0 if report["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
