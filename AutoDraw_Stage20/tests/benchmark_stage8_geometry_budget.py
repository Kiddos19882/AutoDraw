from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
PREPARATION_ROOT = REPO_ROOT / "AutoDraw_Stage20" / "source" / "preparation"
if str(PREPARATION_ROOT) not in sys.path:
    sys.path.insert(0, str(PREPARATION_ROOT))

from benchmark_drawing_algorithms import load_git_image, make_index_map, _resolved_path
from drawing_algorithm_benchmark import load_palette_document
from geometry_budget_optimizer import measure_geometry_plan_quality, optimize_geometry_plan_across_modes, optimize_geometry_plan_to_budget
from geometry_color_plan import build_geometry_color_plan, render_geometry_color_preview, _estimate_geometry_paint_cost
from engine_point_calibration import estimate_point_quota_usage
from board_resource_model import get_board_point_limit


SYNTHETIC_PALETTE = [
    {"id": "red", "name": "Red", "rgb": [220, 35, 45], "hex": "#DC232D"},
    {"id": "blue", "name": "Blue", "rgb": [35, 75, 220], "hex": "#234BDC"},
    {"id": "yellow", "name": "Yellow", "rgb": [245, 205, 40], "hex": "#F5CD28"},
    {"id": "green", "name": "Green", "rgb": [35, 170, 85], "hex": "#23AA55"},
]


def synthetic_cases() -> dict[str, np.ndarray]:
    h, w = 64, 96
    y, x = np.indices((h, w))
    checkerboard = ((x + y) % 2).astype(np.int32)
    stripes = ((y // 8) % 2).astype(np.int32)
    details = np.zeros((h, w), dtype=np.int32)
    details[8:56, 12:84] = 1
    details[20:44, 28:68] = 2
    details[30:34, 44:52] = 3
    blocks = ((x // 16 + y // 16) % 4).astype(np.int32)
    transparent = blocks.copy()
    transparent[:8, :] = -1
    transparent[:, :4] = -1
    return {
        "checkerboard": checkerboard,
        "horizontal_stripes": stripes,
        "nested_details": details,
        "four_color_blocks_with_transparency": transparent,
    }


def save_index_map(index_map: np.ndarray, palette: list[dict[str, Any]], path: Path) -> None:
    rgb = np.zeros((*index_map.shape, 4), dtype=np.uint8)
    rgb[:, :, 3] = 0
    for i, color in enumerate(palette):
        mask = index_map == i
        rgb[mask, :3] = np.asarray(color["rgb"], dtype=np.uint8)
        rgb[mask, 3] = 255
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, mode="RGBA").save(path)


def benchmark_case(
    name: str,
    index_map: np.ndarray,
    palette: list[dict[str, Any]],
    output_dir: Path,
    *,
    budget: float,
    target_usage_percent: float,
    point_limit: int,
    safety_factor: float,
    scenario: str,
) -> dict[str, Any]:
    baseline: dict[str, Any] = {"available": False, "note": None}
    try:
        baseline_plan = build_geometry_color_plan(
            index_map, palette, mode="scanline", simplify_tolerance_px=0.0,
            min_component_area=1, source_name=f"stage8-baseline:{name}:{scenario}",
        )
        baseline_quality = measure_geometry_plan_quality(index_map, baseline_plan)
        baseline_paint = _estimate_geometry_paint_cost(
            baseline_plan, stroke_overhead_px_equivalent=6.67,
            paint_budget_px_equivalent=budget,
        )
        baseline_points = estimate_point_quota_usage(
            drawing_length_px=float(baseline_paint["drawing_length_px"]),
            stroke_count=int(baseline_paint["stroke_count"]),
            single_pixel_stroke_count=int(baseline_paint["single_pixel_stroke_count"]),
            board_point_limit=point_limit,
            safety_factor=safety_factor,
        )
        baseline = {
            "available": True,
            "stroke_count": int(baseline_paint["stroke_count"]),
            "path_length_px": baseline_paint["drawing_length_px"],
            "paint_cost_px_equivalent": baseline_paint["estimated_total_ink_px_equivalent"],
            "estimated_game_points": baseline_points["estimated_point_count"],
            "fits_paint_budget": float(baseline_paint["estimated_total_ink_px_equivalent"]) <= budget * target_usage_percent / 100.0,
            "fits_point_budget": int(baseline_points["estimated_point_count"]) <= int(baseline_points["planning_budget_points"]),
            "quality_mismatch_pixel_count": baseline_quality["quality_mismatch_pixel_count"],
            "quality_mismatch_percent": baseline_quality["quality_mismatch_percent"],
            "quality_pixel_accuracy_percent": baseline_quality["quality_pixel_accuracy_percent"],
            "quality_visible_pixel_accuracy_percent": baseline_quality["quality_visible_pixel_accuracy_percent"],
            "quality_measure_scope": baseline_quality["quality_measure_scope"],
        }
    except (ValueError, TypeError, MemoryError) as exc:
        baseline = {"available": False, "note": f"{type(exc).__name__}: {exc}"}

    optimizer_kwargs = {
        "paint_budget_px_equivalent": budget,
        "target_usage_percent": target_usage_percent,
        "stroke_overhead_px_equivalent": 6.67,
        "board_point_limit": point_limit,
        "point_safety_factor": safety_factor,
        "source_name": f"stage8:{name}:{scenario}",
    }
    if name == "reference-image":
        plan, report = optimize_geometry_plan_across_modes(index_map, palette, **optimizer_kwargs)
    else:
        plan, report = optimize_geometry_plan_to_budget(index_map, palette, mode="scanline", **optimizer_kwargs)
    case_dir = output_dir / name / scenario
    case_dir.mkdir(parents=True, exist_ok=True)
    save_index_map(index_map, palette, case_dir / "input.png")
    if baseline.get("available"):
        render_geometry_color_preview(baseline_plan, max_dimension=max(index_map.shape)).save(case_dir / "baseline-preview.png")
        (case_dir / "baseline-plan.json").write_text(json.dumps(baseline_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    render_geometry_color_preview(plan, max_dimension=max(index_map.shape)).save(case_dir / "optimized-preview.png")
    (case_dir / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (case_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "case": name,
        "scenario": scenario,
        "input_width": int(index_map.shape[1]),
        "input_height": int(index_map.shape[0]),
        "input_visible_pixels": int(np.count_nonzero(index_map >= 0)),
        "mode": report.get("mode"),
        "scale": report.get("scale"),
        "min_component_area": report.get("min_component_area"),
        "simplify_tolerance_px": report.get("simplify_tolerance_px"),
        "stroke_count": int(plan.get("summary", {}).get("stroke_count", len(plan.get("strokes", [])))) ,
        "path_length_px": plan.get("summary", {}).get("drawing_length_px"),
        "paint_cost_px_equivalent": report.get("estimated_ink_after_px_equivalent"),
        "paint_target_px_equivalent": report.get("target_cost_px_equivalent"),
        "estimated_game_points": report.get("estimated_game_points_after"),
        "target_game_points": report.get("target_point_count"),
        "fits_paint_budget": report.get("fits_paint_budget"),
        "fits_point_budget": report.get("fits_point_budget"),
        "fits_both_budgets": report.get("fits_budget"),
        "needs_multi_board_split": report.get("needs_multi_board_split"),
        "quality_measure": report.get("quality_measure"),
        "quality_mismatch_pixel_count": report.get("quality_mismatch_pixel_count"),
        "quality_mismatch_percent": report.get("quality_mismatch_percent"),
        "quality_pixel_accuracy_percent": report.get("quality_pixel_accuracy_percent"),
        "quality_visible_pixel_accuracy_percent": report.get("quality_visible_pixel_accuracy_percent"),
        "quality_measure_scope": report.get("quality_measure_scope"),
        "mode_candidates": report.get("mode_candidates", []),
        "baseline": baseline,
        "coarsening_quality_loss_percentage_points": (
            round(float(baseline["quality_pixel_accuracy_percent"]) - float(report["quality_pixel_accuracy_percent"]), 4)
            if baseline.get("available") else None
        ),
        "artifacts": {
            "input": str((case_dir / "input.png").relative_to(REPO_ROOT)),
            "baseline_preview": str((case_dir / "baseline-preview.png").relative_to(REPO_ROOT)) if baseline.get("available") else None,
            "baseline_plan": str((case_dir / "baseline-plan.json").relative_to(REPO_ROOT)) if baseline.get("available") else None,
            "plan": str((case_dir / "plan.json").relative_to(REPO_ROOT)),
            "preview": str((case_dir / "optimized-preview.png").relative_to(REPO_ROOT)),
            "report": str((case_dir / "report.json").relative_to(REPO_ROOT)),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 8 reproducible geometry budget/quality benchmark.")
    parser.add_argument("--git-ref", default="origin/master")
    parser.add_argument("--git-path", default="AutoDraw_Stage20/testImages/images.png")
    parser.add_argument("--target-width", type=int, default=646)
    parser.add_argument("--target-height", type=int, default=323)
    parser.add_argument("--palette-json", default="AutoDraw_Stage20/data/palettes/profiles/Browser_palette.autodraw-palette.json")
    parser.add_argument("--board-item-type", default="BoardItem2")
    parser.add_argument("--target-usage-percent", type=float, default=75.0)
    parser.add_argument("--safety-factor", type=float, default=0.85)
    parser.add_argument("--output", default="AutoDraw_Stage20/benchmark-results/stage8/report.json")
    parser.add_argument("--artifact-dir", default="AutoDraw_Stage20/benchmark-results/stage8/cases")
    args = parser.parse_args()

    output = _resolved_path(args.output)
    artifact_dir = _resolved_path(args.artifact_dir)
    palette, palette_info = load_palette_document(_resolved_path(args.palette_json))
    point_limit = get_board_point_limit(args.board_item_type)
    results: list[dict[str, Any]] = []

    source = load_git_image(args.git_ref, args.git_path)
    source_map, source_palette, source_report, _ = make_index_map(
        source,
        width=args.target_width,
        height=args.target_height,
        fit_mode="contain",
        quantize_colors=8,
        background_mode="edge-connected",
        palette=palette,
        palette_info=palette_info,
    )
    results.append(benchmark_case(
        "reference-image", source_map, source_palette, artifact_dir,
        budget=25650.0, target_usage_percent=args.target_usage_percent,
        point_limit=point_limit, safety_factor=args.safety_factor, scenario="combined-budget",
    ))

    synthetic = synthetic_cases()
    for name, index_map in synthetic.items():
        results.append(benchmark_case(
            name, index_map, SYNTHETIC_PALETTE, artifact_dir,
            budget=25650.0, target_usage_percent=args.target_usage_percent,
            point_limit=point_limit, safety_factor=args.safety_factor, scenario="combined-budget",
        ))

    # Separate constraint experiments use a small deterministic input so the reports
    # isolate the configuration change and remain inexpensive enough for every CI run.
    small_checkerboard = synthetic["checkerboard"]
    results.append(benchmark_case(
        "constraint-isolation", small_checkerboard, SYNTHETIC_PALETTE, artifact_dir,
        budget=1_000_000_000.0, target_usage_percent=args.target_usage_percent,
        point_limit=6_000, safety_factor=args.safety_factor, scenario="point-budget-priority",
    ))
    results.append(benchmark_case(
        "constraint-isolation", small_checkerboard, SYNTHETIC_PALETTE, artifact_dir,
        budget=14_000.0, target_usage_percent=args.target_usage_percent,
        point_limit=12_000, safety_factor=args.safety_factor, scenario="paint-budget-priority",
    ))
    results.append(benchmark_case(
        "constraint-isolation", small_checkerboard, SYNTHETIC_PALETTE, artifact_dir,
        budget=14_000.0, target_usage_percent=args.target_usage_percent,
        point_limit=3_000, safety_factor=args.safety_factor, scenario="combined-budget",
    ))

    report = {
        "schema_version": 1,
        "benchmark": "stage8_geometry_budget_quality",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_reference": f"{args.git_ref}:{args.git_path}",
        "target_size": {"width": args.target_width, "height": args.target_height},
        "browser_palette": palette_info,
        "resource_model": {
            "paint_budget_px_equivalent": 25650.0,
            "target_usage_percent": args.target_usage_percent,
            "board_item_type": args.board_item_type,
            "board_point_limit": point_limit,
            "point_safety_factor": args.safety_factor,
            "note": "Paint and point values are model estimates, not direct browser telemetry.",
        },
        "case_count": len(results),
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Stage 8 benchmark wrote {len(results)} case results to {output}")
    for item in results:
        print(
            f"{item['case']}/{item['scenario']}: strokes={item['stroke_count']}, "
            f"quality={item['quality_pixel_accuracy_percent']}%, "
            f"paint_fit={item['fits_paint_budget']}, points_fit={item['fits_point_budget']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
