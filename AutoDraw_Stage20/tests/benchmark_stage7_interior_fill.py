from __future__ import annotations

import argparse
import json
import math
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
        half_x = brush * float(plan["brush_configuration"]["scale_x_source_px_per_game_unit"]) / 2.0
        half_y = brush * float(plan["brush_configuration"]["scale_y_source_px_per_game_unit"]) / 2.0
        left = max(0, math.ceil(min(x1, x2) - half_x - 1e-9))
        right = min(width - 1, math.floor(max(x1, x2) + half_x + 1e-9))
        top = max(0, math.ceil(y - half_y - 1e-9))
        bottom = min(height - 1, math.floor(y + half_y + 1e-9))
        if left > right or top > bottom:
            raise ValueError("План содержит footprint за пределами холста.")
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
        results.append(measure_rendering(
            name, index_map, rendered, len(plan.get("strokes", [])),
            _centerline_length(plan), footprint_model="1px centerline rasterization",
        ))
    previews["interior_fill"] = interior_rendered
    results.append(measure_rendering(
        "interior_fill", index_map, interior_rendered,
        len(interior_plan["strokes"]), _centerline_length(interior_plan),
        footprint_model="conservative axis-aligned rectangle; not a measured game brush",
    ))

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
            "This report compares geometry quality and stroke count; it does not certify paint quota or enable automatic execution.",
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
    print(f"{'Algorithm':<18} {'Strokes':>9} {'Coverage %':>12} {'Exact %':>10} {'Wrong':>8} {'Transparent':>13}")
    for item in results:
        print(
            f"{item['name']:<18} {item['stroke_count']:>9} {item['coverage_percent']:>12.2f} "
            f"{item['exact_color_percent']:>10.2f} {item['wrong_color_pixel_count']:>8} "
            f"{item['painted_transparent_pixel_count']:>13}"
        )
    print(f"\nJSON report: {output_path}")
    print(f"Preview directory: {preview_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
