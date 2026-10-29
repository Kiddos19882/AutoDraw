from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "AutoDraw_Stage20"
PREPARATION_ROOT = APP_ROOT / "source" / "preparation"
# Compatibility wrappers resolve canonical modules from the Stage20 root.
for import_root in (PREPARATION_ROOT, APP_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from benchmark_drawing_algorithms import (  # noqa: E402
    _resolved_path,
    load_git_image,
    make_index_map,
)
from color_scanline import build_color_scanline_plan  # noqa: E402
from drawing_algorithm_benchmark import (  # noqa: E402
    load_palette_document,
    render_index_map_png,
    render_plan_index_map,
)
from geometry_color_plan import build_geometry_color_plan  # noqa: E402
from interior_fill_planner import build_interior_fill_plan  # noqa: E402
from paint_cost_model import (
    DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
    DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
    estimate_paint_cost,
)  # noqa: E402
from engine_point_calibration import estimate_point_quota_usage  # noqa: E402
from brush_footprint_geometry import footprint_pixel_bounds  # noqa: E402


def render_interior_fill_footprints(index_map: Any, plan: dict[str, Any]) -> np.ndarray:
    """Rasterize the planner's declared rectangular footprints, not just centerlines."""
    source = np.asarray(index_map, dtype=np.int32)
    canvas = plan.get("canvas", {})
    if source.ndim != 2 or source.shape != (canvas.get("height"), canvas.get("width")):
        raise ValueError("Размер карты не совпадает с планом внутренней заливки.")
    rendered = np.full(source.shape, -1, dtype=np.int32)
    height, width = source.shape

    for stroke in plan.get("strokes", []):
        color = int(stroke["color_index"])
        brush = int(stroke["brush_value"])
        first, last = stroke["points"]
        x1, x2 = float(first["x"]), float(last["x"])
        y = float(first["y"])
        bounds = footprint_pixel_bounds(
            min(x1, x2), max(x1, x2), y, brush,
            float(plan["brush_configuration"]["scale_x_source_px_per_game_unit"]),
            float(plan["brush_configuration"]["scale_y_source_px_per_game_unit"]),
            width, height,
        )
        if bounds is None:
            raise ValueError("План содержит пустой footprint или выходит за пределы холста.")
        left, right, top, bottom = bounds
        footprint = source[top:bottom + 1, left:right + 1]
        if footprint.size == 0 or not np.all(footprint == color):
            raise ValueError(
                f"Footprint штриха {stroke.get('name', '?')} пересекает другой цвет или прозрачность."
            )
        rendered[top:bottom + 1, left:right + 1] = color
    return rendered


def measure_rendering(name: str, source: np.ndarray, rendered: np.ndarray, stroke_count: int,
                      centerline_length_px: float, *, footprint_model: str) -> dict[str, Any]:
    source_visible = source >= 0
    rendered_visible = rendered >= 0
    covered = source_visible & rendered_visible
    exact = covered & (source == rendered)
    wrong = covered & (source != rendered)
    painted_transparent = (~source_visible) & rendered_visible
    visible_count = int(np.count_nonzero(source_visible))
    covered_count = int(np.count_nonzero(covered))
    exact_count = int(np.count_nonzero(exact))
    total_count = int(source.size)
    return {
        "name": name,
        "footprint_model": footprint_model,
        "stroke_count": stroke_count,
        "centerline_length_px": round(centerline_length_px, 3),
        "source_visible_pixel_count": visible_count,
        "covered_source_pixel_count": covered_count,
        "coverage_percent": round(100.0 * covered_count / visible_count, 4) if visible_count else 100.0,
        "exact_color_pixel_count": exact_count,
        "exact_color_percent": round(100.0 * exact_count / visible_count, 4) if visible_count else 100.0,
        "wrong_color_pixel_count": int(np.count_nonzero(wrong)),
        "painted_transparent_pixel_count": int(np.count_nonzero(painted_transparent)),
        "canvas_mismatch_percent": round(
            100.0 * int(np.count_nonzero(rendered != source)) / total_count, 4
        ) if total_count else 0.0,
    }


def _transparent_stroke_samples(
    plan: dict[str, Any], source: np.ndarray, *, limit: int = 10
) -> list[dict[str, Any]]:
    """Locate the exact strokes responsible for transparent-pixel benchmark failures."""
    transparent = np.asarray(source) < 0
    height, width = transparent.shape
    samples: list[dict[str, Any]] = []
    for stroke in plan.get("strokes", []):
        points = stroke.get("points", [])
        if len(points) < 2:
            continue
        coordinates = [(int(round(float(p["x"]))), int(round(float(p["y"])))) for p in points]
        if stroke.get("closed") and len(coordinates) >= 3 and coordinates[-1] != coordinates[0]:
            coordinates.append(coordinates[0])
        xmin = max(0, min(x for x, _ in coordinates))
        xmax = min(width - 1, max(x for x, _ in coordinates))
        ymin = max(0, min(y for _, y in coordinates))
        ymax = min(height - 1, max(y for _, y in coordinates))
        if xmin > xmax or ymin > ymax:
            continue
        local = [(x - xmin, y - ymin) for x, y in coordinates]
        image = Image.new("I", (xmax - xmin + 1, ymax - ymin + 1), -1)
        draw = ImageDraw.Draw(image)
        if len(local) == 1:
            draw.point(local[0], fill=int(stroke["color"]["palette_index"]))
        else:
            draw.line(local, fill=int(stroke["color"]["palette_index"]), width=1)
        painted = np.asarray(image, dtype=np.int32) >= 0
        hits = np.argwhere(painted & transparent[ymin:ymax + 1, xmin:xmax + 1])
        if hits.size:
            samples.append({
                "name": stroke.get("name", "unknown"),
                "points": coordinates,
                "transparent_pixels": [[int(xmin + x), int(ymin + y)] for y, x in hits[:10]],
            })
            if len(samples) >= limit:
                break
    return samples


def _centerline_length(plan: dict[str, Any]) -> float:
    total = 0.0
    for stroke in plan.get("strokes", []):
        points = stroke.get("points", [])
        for first, last in zip(points, points[1:]):
            total += math.hypot(
                float(last["x"]) - float(first["x"]),
                float(last["y"]) - float(first["y"]),
            )
    return total


def _single_pixel_stroke_count(plan: dict[str, Any]) -> int:
    """Count executor-expanded point strokes using the shared plan cost semantics."""
    count = 0
    for stroke in plan.get("strokes", []):
        points = stroke.get("points", [])
        if len(points) != 2:
            continue
        first, last = points
        distance = math.hypot(
            float(last["x"]) - float(first["x"]),
            float(last["y"]) - float(first["y"]),
        )
        if distance <= 1e-7:
            count += 1
    return count


def _resource_budget_estimates(
    plan: dict[str, Any],
    *,
    board_point_limit: int = 6_000,
    point_safety_factor: float = 0.85,
    paint_target_usage_percent: float = 75.0,
) -> dict[str, Any]:
    """Report separate paint and point budgets for any Stage 7 strategy."""
    stroke_count = len(plan.get("strokes", []))
    path_length = _centerline_length(plan)
    single_pixels = _single_pixel_stroke_count(plan)
    paint = estimate_paint_cost(
        path_length,
        stroke_count,
        single_pixels,
        stroke_overhead_px_equivalent=DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
        paint_budget_px_equivalent=DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
    )
    points = estimate_point_quota_usage(
        path_length,
        stroke_count,
        single_pixel_stroke_count=single_pixels,
        board_point_limit=board_point_limit,
        safety_factor=point_safety_factor,
    )
    paint_target = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT * paint_target_usage_percent / 100.0
    point_target = int(points["planning_budget_points"])
    fits_paint = float(paint["estimated_total_ink_px_equivalent"]) <= paint_target
    fits_points = int(points["estimated_point_count"]) <= point_target
    return {
        "model_scope": "offline_estimate_not_browser_measurement",
        "single_pixel_stroke_count": single_pixels,
        "paint": {
            "model_id": paint["model_id"],
            "estimated_total_ink_px_equivalent": paint["estimated_total_ink_px_equivalent"],
            "paint_budget_px_equivalent": DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
            "target_usage_percent": paint_target_usage_percent,
            "target_cost_px_equivalent": round(paint_target, 3),
            "fits_target": fits_paint,
            "risk_level": paint["risk_level"],
        },
        "game_points": {
            "model_id": points["model_id"],
            "estimated_point_count": points["estimated_point_count"],
            "board_point_limit": board_point_limit,
            "planning_budget_points": point_target,
            "safety_factor": point_safety_factor,
            "fits_target": fits_points,
            "risk_level": points["risk_level"],
            "calibration_point_limit_is_inferred": points["calibration_point_limit_is_inferred"],
        },
        "fits_both_targets": fits_paint and fits_points,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 7 benchmark: compare contour, skeleton, scanline and modeled interior-fill footprints."
    )
    parser.add_argument("--git-ref", default="HEAD")
    parser.add_argument("--image-file", help="Optional local image path; overrides --git-ref/--git-path.")
    parser.add_argument("--git-path", default="AutoDraw_Stage20/testImages/images.png")
    parser.add_argument("--target-width", type=int, default=646)
    parser.add_argument("--target-height", type=int, default=323)
    parser.add_argument("--fit-mode", choices=("contain", "cover", "stretch"), default="contain")
    parser.add_argument(
        "--palette-json",
        default="AutoDraw_Stage20/data/palettes/profiles/Browser_palette.autodraw-palette.json",
    )
    parser.add_argument("--background-mode", choices=("preserve", "edge-connected"), default="edge-connected")
    parser.add_argument("--max-brush-value", type=int, default=20)
    parser.add_argument("--output", default="AutoDraw_Stage20/benchmark-results/stage7-report.json")
    parser.add_argument("--preview-dir", default="AutoDraw_Stage20/benchmark-results/stage7-previews")
    args = parser.parse_args()

    if args.target_width < 1 or args.target_height < 1:
        parser.error("Canvas dimensions must be positive.")
    if not 2 <= args.max_brush_value <= 20:
        parser.error("max-brush-value must be between 2 and 20.")

    if args.image_file:
        image_path = _resolved_path(args.image_file)
        with Image.open(image_path) as opened_image:
            source_image = opened_image.convert("RGBA").copy()
        source_name = str(image_path.relative_to(REPO_ROOT)) if image_path.is_relative_to(REPO_ROOT) else str(image_path)
    else:
        source_image = load_git_image(args.git_ref, args.git_path)
        source_name = f"{args.git_ref}:{args.git_path}"
    palette, palette_info = load_palette_document(_resolved_path(args.palette_json))
    index_map, palette, image_report, _ = make_index_map(
        source_image,
        width=args.target_width,
        height=args.target_height,
        fit_mode=args.fit_mode,
        quantize_colors=8,
        background_mode=args.background_mode,
        palette=palette,
        palette_info=palette_info,
    )
    plans: list[tuple[str, dict[str, Any]]] = [
        ("contour", build_geometry_color_plan(
            index_map, palette, mode="contour", simplify_tolerance_px=0.8,
            min_component_area=1, source_name=source_name,
        )),
        ("skeleton", build_geometry_color_plan(
            index_map, palette, mode="skeleton", simplify_tolerance_px=0.8,
            min_component_area=1, source_name=source_name,
        )),
        ("scanline", build_color_scanline_plan(
            index_map, palette, source_name=source_name,
            plan_name="Stage 7 comparison scanline",
        )),
    ]
    interior_plan = build_interior_fill_plan(index_map, max_brush_value=args.max_brush_value)
    interior_rendered = render_interior_fill_footprints(index_map, interior_plan)

    results = []
    previews: dict[str, np.ndarray] = {"source-index-map": index_map}
    for name, plan in plans:
        rendered = render_plan_index_map(plan)
        previews[name] = rendered
        metrics = measure_rendering(
            name, index_map, rendered, len(plan.get("strokes", [])),
            _centerline_length(plan), footprint_model="1px centerline rasterization",
        )
        metrics["resource_budget_estimates"] = _resource_budget_estimates(plan)
        if metrics["painted_transparent_pixel_count"]:
            metrics["transparent_stroke_samples"] = _transparent_stroke_samples(plan, index_map)
        results.append(metrics)
    previews["interior_fill"] = interior_rendered
    interior_metrics = measure_rendering(
        "interior_fill", index_map, interior_rendered,
        len(interior_plan["strokes"]), _centerline_length(interior_plan),
        footprint_model="conservative axis-aligned rectangle; not a measured game brush",
    )
    interior_metrics["resource_budget_estimates"] = _resource_budget_estimates(interior_plan)
    # Expose why the interior-fill candidate spends its budget: wide-fill strokes
    # and thin fallback strokes have very different planning roles. This is
    # diagnostic only and does not alter the plan or its resource estimates.
    interior_strokes = interior_plan.get("strokes", [])
    role_counts: dict[str, int] = {}
    brush_counts: dict[str, int] = {}
    for stroke in interior_strokes:
        role = str(stroke.get("role", "unknown"))
        brush_value = str(stroke.get("brush_value", "unknown"))
        role_counts[role] = role_counts.get(role, 0) + 1
        brush_counts[brush_value] = brush_counts.get(brush_value, 0) + 1
    interior_metrics["planner_diagnostics"] = {
        "role_stroke_counts": role_counts,
        "brush_value_stroke_counts": brush_counts,
        "interior_fill_stroke_count": int(interior_plan["summary"]["interior_fill_stroke_count"]),
        "boundary_fallback_stroke_count": int(interior_plan["summary"]["boundary_fallback_stroke_count"]),
        "fallback_stroke_percentage": round(
            100.0 * int(interior_plan["summary"]["boundary_fallback_stroke_count"]) / len(interior_strokes),
            4,
        ) if interior_strokes else 0.0,
        "modeled_coverage_percent": interior_plan["summary"]["coverage_percent"],
        "automatic_execution_allowed": interior_plan["brush_configuration"]["automatic_execution_allowed"],
    }
    results.append(interior_metrics)

    report = {
        "schema_version": 1,
        "stage": 7,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "git_ref": None if args.image_file else args.git_ref,
            "git_path": None if args.image_file else args.git_path,
            "image_file": args.image_file,
            **image_report,
        },
        "palette": palette_info,
        "configuration": {
            "target_width": args.target_width,
            "target_height": args.target_height,
            "fit_mode": args.fit_mode,
            "background_mode": args.background_mode,
            "interior_fill_max_brush_value": args.max_brush_value,
            "interior_fill_ready_for_automatic_execution": False,
        },
        "algorithm_results": results,
        "interior_fill_planner_summary": interior_plan["summary"],
        "interpretation_limits": [
            "All strategies use the same quantized palette-index map.",
            "Contour, skeleton and scanline are rasterized as 1px centerlines; their real brush footprint is not modeled here.",
            "Interior fill is rasterized using its conservative rectangular model, not a measured in-game brush shape.",
            "Coverage and exact-color scores are offline estimates and do not prove the game registers every stroke.",
            "Both paint and game-point budgets are reported separately for all four strategies; these are model estimates, not browser measurements.",
            "This report compares geometry quality and stroke count; it does not certify resource depletion or enable automatic execution.",
        ],
    }

    preview_dir = _resolved_path(args.preview_dir)
    preview_dir.mkdir(parents=True, exist_ok=True)
    for name, rendered in previews.items():
        render_index_map_png(rendered, palette).save(preview_dir / f"{name}.png")
    output_path = _resolved_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Stage 7 geometry comparison (offline estimates, not browser measurements)")
    print(f"{'Algorithm':<18} {'Strokes':>9} {'Coverage %':>12} {'Exact %':>10} {'Ink %':>9} {'Points %':>10} {'Both fit':>9} {'Wrong':>8} {'Transparent':>13}")
    for item in results:
        print(
            f"{item['name']:<18} {item['stroke_count']:>9} {item['coverage_percent']:>12.2f} "
            f"{item['exact_color_percent']:>10.2f} "
            f"{item['resource_budget_estimates']['paint']['estimated_total_ink_px_equivalent'] / DEFAULT_PAINT_BUDGET_PX_EQUIVALENT * 100:>8.1f} "
            f"{item['resource_budget_estimates']['game_points']['estimated_point_count'] / item['resource_budget_estimates']['game_points']['board_point_limit'] * 100:>9.1f} "
            f"{'yes' if item['resource_budget_estimates']['fits_both_targets'] else 'no':>9} "
            f"{item['wrong_color_pixel_count']:>8} {item['painted_transparent_pixel_count']:>13}"
        )
    print(f"\nJSON report: {output_path}")
    print(f"Preview directory: {preview_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
