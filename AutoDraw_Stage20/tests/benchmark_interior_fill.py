from __future__ import annotations

"""Compare conservative interior fill with existing geometry strategies.

Run from the repository root. Resource numbers for interior fill are deliberately
reported as counts/lengths only: the planner is not executor-ready and its brush
footprint is an estimate, not a browser measurement.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PREPARATION = ROOT / "AutoDraw_Stage20" / "source" / "preparation"
TESTS = ROOT / "AutoDraw_Stage20" / "tests"
for entry in (str(PREPARATION), str(TESTS)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from benchmark_drawing_algorithms import make_index_map, load_git_image, _resolved_path  # noqa: E402
from drawing_algorithm_benchmark import render_plan_index_map, summarize_plan, load_palette_document  # noqa: E402
from geometry_color_plan import build_geometry_color_plan  # noqa: E402
from interior_fill_planner import build_interior_fill_plan  # noqa: E402


def _footprint(
    indexes: np.ndarray,
    stroke: dict[str, Any],
    *,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
) -> tuple[int, int, int, int]:
    """Return the modeled brush bounds using independent X/Y scale factors."""
    brush = float(stroke["brush_value"])
    first, last = stroke["points"]
    x1, x2, y = float(first["x"]), float(last["x"]), float(first["y"])
    half_x = brush * scale_x / 2.0
    half_y = brush * scale_y / 2.0
    height, width = indexes.shape
    left = max(0, int(np.ceil(min(x1, x2) - half_x - 1e-9)))
    right = min(width - 1, int(np.floor(max(x1, x2) + half_x + 1e-9)))
    top = max(0, int(np.ceil(y - half_y - 1e-9)))
    bottom = min(height - 1, int(np.floor(y + half_y + 1e-9)))
    return left, top, right, bottom


def summarize_interior_fill(indexes: np.ndarray, plan: dict[str, Any]) -> dict[str, Any]:
    height, width = indexes.shape
    rendered = np.full((height, width), -1, dtype=np.int32)
    invalid_footprints = 0
    modeled_length = 0.0
    brush_configuration = plan.get("brush_configuration", {})
    scale_x = float(brush_configuration.get("scale_x_source_px_per_game_unit", 1.0))
    scale_y = float(brush_configuration.get("scale_y_source_px_per_game_unit", 1.0))
    for stroke in plan["strokes"]:
        left, top, right, bottom = _footprint(
            indexes, stroke, scale_x=scale_x, scale_y=scale_y
        )
        region = indexes[top:bottom + 1, left:right + 1]
        if not region.size or not np.all(region == int(stroke["color_index"])):
            invalid_footprints += 1
            continue
        rendered[top:bottom + 1, left:right + 1] = int(stroke["color_index"])
        first, last = stroke["points"]
        modeled_length += float(np.hypot(
            float(last["x"]) - float(first["x"]),
            float(last["y"]) - float(first["y"]),
        ))
    visible = indexes >= 0
    covered = visible & (rendered >= 0)
    exact = covered & (rendered == indexes)
    visible_count = int(np.count_nonzero(visible))
    covered_count = int(np.count_nonzero(covered))
    return {
        "name": "interior_fill",
        "stroke_count": len(plan["strokes"]),
        "interior_fill_stroke_count": plan["summary"]["interior_fill_stroke_count"],
        "boundary_fallback_stroke_count": plan["summary"]["boundary_fallback_stroke_count"],
        "source_visible_pixel_count": visible_count,
        "covered_source_visible_percent": round(100 * covered_count / visible_count, 4) if visible_count else 100.0,
        "exact_color_match_percent_of_source": round(100 * int(np.count_nonzero(exact)) / visible_count, 4) if visible_count else 100.0,
        "wrong_color_pixel_count": int(np.count_nonzero(covered & (rendered != indexes))),
        "painted_transparent_pixel_count": int(np.count_nonzero((indexes < 0) & (rendered >= 0))),
        "invalid_footprint_count": invalid_footprints,
        "modeled_centerline_length_px": round(modeled_length, 3),
        "ready_for_automatic_execution": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark interior fill against contour, skeleton and scanline.")
    parser.add_argument("--git-ref", default="origin/master")
    parser.add_argument("--git-path", default="AutoDraw_Stage20/testImages/images.png")
    parser.add_argument("--target-width", type=int, default=646)
    parser.add_argument("--target-height", type=int, default=323)
    parser.add_argument("--fit-mode", choices=("contain", "cover", "stretch"), default="contain")
    parser.add_argument("--palette-json", default="AutoDraw_Stage20/data/palettes/profiles/Browser_palette.autodraw-palette.json")
    parser.add_argument("--background-mode", choices=("preserve", "edge-connected"), default="edge-connected")
    parser.add_argument("--max-brush-value", type=int, default=20)
    parser.add_argument("--min-brush-value", type=int, default=2)
    parser.add_argument("--brush-scale-x", type=float, default=1.0)
    parser.add_argument("--brush-scale-y", type=float, default=1.0)
    parser.add_argument("--output", default="AutoDraw_Stage20/benchmark-results/stage7-interior-fill-report.json")
    args = parser.parse_args()

    if args.target_width < 1 or args.target_height < 1:
        parser.error("Canvas dimensions must be positive.")
    source = load_git_image(args.git_ref, args.git_path)
    palette_path = _resolved_path(args.palette_json)
    palette, palette_info = load_palette_document(palette_path)
    index_map, palette, image_report, _ = make_index_map(
        source, width=args.target_width, height=args.target_height, fit_mode=args.fit_mode,
        quantize_colors=8, background_mode=args.background_mode,
        palette=palette, palette_info=palette_info,
    )

    strategies: list[dict[str, Any]] = []
    for mode in ("contour", "skeleton", "scanline"):
        started = time.perf_counter()
        plan = build_geometry_color_plan(index_map, palette, mode=mode, simplify_tolerance_px=0.8, min_component_area=1)
        elapsed = time.perf_counter() - started
        metrics = summarize_plan(mode, plan, index_map)
        strategies.append({
            "name": mode,
            "planning_time_seconds": round(elapsed, 4),
            "stroke_count": metrics["stroke_count"],
            "covered_source_visible_percent": metrics["covered_source_visible_percent"],
            "exact_color_match_percent_of_source": metrics["exact_color_match_percent_of_source"],
            "wrong_color_pixel_count": metrics["wrong_color_pixel_count"],
            "painted_transparent_pixel_count": metrics["painted_transparent_pixel_count"],
            "estimated_ink_usage_percent": metrics["paint_cost_estimate"]["estimated_usage_percent"],
            "estimated_point_usage_percent": metrics["point_quota_estimate"]["estimated_usage_percent"],
            "resource_values_are_estimates": True,
        })

    started = time.perf_counter()
    fill_plan = build_interior_fill_plan(
        index_map,
        max_brush_value=args.max_brush_value,
        min_brush_value=args.min_brush_value,
        brush_scale_x=args.brush_scale_x,
        brush_scale_y=args.brush_scale_y,
    )
    fill_elapsed = time.perf_counter() - started
    fill_metrics = summarize_interior_fill(index_map, fill_plan)
    fill_metrics["planning_time_seconds"] = round(fill_elapsed, 4)
    fill_metrics["footprint_model"] = fill_plan["brush_configuration"]["footprint_model"]
    fill_metrics["resource_values_are_estimates"] = True
    strategies.append(fill_metrics)

    report = {
        "schema_version": 1,
        "stage": 7,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "git_ref": args.git_ref,
            "git_path": args.git_path,
            **image_report,
        },
        "interior_fill_configuration": {
            "max_brush_value": args.max_brush_value,
            "min_brush_value": args.min_brush_value,
            "brush_scale_x": args.brush_scale_x,
            "brush_scale_y": args.brush_scale_y,
            "automatic_execution_allowed": False,
        },
        "results": strategies,
        "interpretation_limits": [
            "Every strategy receives the same quantized index map.",
            "Contour, skeleton and scanline coverage uses a one-pixel rasterized path; it does not model the game's brush width.",
            "Interior fill coverage uses a conservative axis-aligned rectangular footprint model and must not be interpreted as a measured in-game footprint.",
            "Paint and point costs are available only for existing executor-compatible geometry plans; interior fill cost is not estimated until its brush semantics are validated.",
            "Planning time depends on machine and Python/OpenCV/NumPy versions.",
        ],
    }
    output = _resolved_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{'Strategy':<18} {'Strokes':>9} {'Coverage %':>12} {'Exact %':>10} {'Time s':>9}")
    for item in strategies:
        print(
            f"{item['name']:<18} {item['stroke_count']:>9} "
            f"{item['covered_source_visible_percent']:>12.2f} "
            f"{item['exact_color_match_percent_of_source']:>10.2f} "
            f"{item['planning_time_seconds']:>9.3f}"
        )
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
