from __future__ import annotations

"""Compare current interior-fill with the experimental boundary-first strategy."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

APP_ROOT = Path(__file__).resolve().parents[1]
for import_root in (APP_ROOT / "source" / "preparation", APP_ROOT / "tests"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from benchmark_stage7_fallback_merge_sweep import (  # noqa: E402
    _coverage_path_metrics,
    _path_length,
    _zero_length_stroke_count,
    make_cases,
)
from interior_fill_planner import build_interior_fill_plan  # noqa: E402
from outline_first_fill_planner import build_outline_first_fill_plan  # noqa: E402


def _summarize(strokes: list[dict[str, Any]], index_map) -> dict[str, Any]:
    metrics = _coverage_path_metrics(strokes, index_map)
    return {
        "stroke_count": len(strokes),
        "zero_length_stroke_count": _zero_length_stroke_count(strokes),
        "centerline_path_length_px": round(_path_length(strokes), 3),
        **metrics,
        "all_strokes_safe_for_color_map": all(
            stroke.get("safe_for_color_map") is True for stroke in strokes
        ),
        "automatic_execution_allowed": False,
    }


def run_comparison() -> dict[str, Any]:
    cases = []
    for name, index_map in make_cases().items():
        interior = build_interior_fill_plan(index_map)
        outline = build_outline_first_fill_plan(index_map)
        cases.append({
            "case": name,
            "canvas": {
                "width": int(index_map.shape[1]),
                "height": int(index_map.shape[0]),
            },
            "visible_pixel_count": int((index_map >= 0).sum()),
            "strategies": {
                "interior_fill": _summarize(interior["strokes"], index_map),
                "outline_first_fill": {
                    **_summarize(outline["strokes"], index_map),
                    "outline_stroke_count": outline["summary"]["outline_stroke_count"],
                    "residual_visible_pixel_count": outline["summary"]["residual_visible_pixel_count"],
                },
            },
        })
    return {
        "schema_version": 1,
        "benchmark": "outline_first_fill_vs_interior_fill",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_scope": (
            "offline synthetic maps; horizontal strokes; conservative rectangular "
            "footprint proxy; not browser measurements or paint consumption"
        ),
        "cases": cases,
        "interpretation_limits": [
            "The strategies receive identical deterministic input maps.",
            "Outline-first currently uses horizontal boundary runs, not a connected contour route.",
            "Coverage and footprint spill are offline geometric estimates only.",
            "Path length, stroke count, fresh/revisit visits, and footprint visits do not estimate paint consumption.",
            "Automatic execution remains disabled.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=APP_ROOT / "benchmark-results" / "outline-first-comparison.json",
    )
    args = parser.parse_args()
    report = run_comparison()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Outline-first vs interior-fill (offline comparison)")
    for case in report["cases"]:
        left = case["strategies"]["interior_fill"]
        right = case["strategies"]["outline_first_fill"]
        print(
            f"{case['case']}: strokes {left['stroke_count']} -> {right['stroke_count']}; "
            f"path {left['centerline_path_length_px']} -> {right['centerline_path_length_px']} px; "
            f"uncovered {left['uncovered_visible_pixel_count']} -> "
            f"{right['uncovered_visible_pixel_count']}"
        )
    print(f"JSON report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
