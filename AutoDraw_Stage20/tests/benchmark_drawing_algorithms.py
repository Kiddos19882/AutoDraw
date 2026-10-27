from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
PREPARATION_ROOT = REPO_ROOT / "AutoDraw_Stage20" / "source" / "preparation"
if str(PREPARATION_ROOT) not in sys.path:
    sys.path.insert(0, str(PREPARATION_ROOT))

from board_resource_model import DEFAULT_POINT_SAFETY_FACTOR, get_board_point_limit  # noqa: E402
from color_scanline import build_color_scanline_plan  # noqa: E402
from drawing_algorithm_benchmark import render_index_map_png, summarize_plan  # noqa: E402
from geometry_color_plan import build_geometry_color_plan  # noqa: E402
from image_processing.pipeline import fit_to_canvas  # noqa: E402
from paint_budget_optimizer import fit_result_to_paint_budget  # noqa: E402
from palette_quantization import (  # noqa: E402
    PaletteQuantizationResult,
    normalize_palette,
    quantize_image_to_palette,
    remove_edge_connected_background,
)
from drawing_algorithm_benchmark import load_palette_document  # noqa: E402


def load_git_image(ref: str, repo_path: str) -> Image.Image:
    """Load a source image from a Git ref without relying on the working-tree copy."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{repo_path}"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return Image.open(BytesIO(result.stdout)).copy()


def make_index_map(
    source_image: Image.Image,
    *,
    width: int,
    height: int,
    fit_mode: str,
    quantize_colors: int,
    background_mode: str,
    palette: list[dict[str, Any]] | None = None,
    palette_info: dict[str, Any] | None = None,
) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any], Image.Image]:
    """Create one deterministic map shared by every path planner.

    The normal path uses the saved browser palette and CIEDE2000 mapping.
    MEDIANCUT remains available only with --synthetic-palette for comparison tests.
    """
    fitted = fit_to_canvas(source_image, width, height, fit_mode)
    if background_mode == "edge-connected":
        background_result = remove_edge_connected_background(fitted, tolerance=24)
        working = background_result.image
        background_report = background_result.report
    else:
        working = fitted.convert("RGBA")
        background_report = {
            "method": "preserve",
            "removed_pixel_count": 0,
            "note": "Фон сохранён; это влияет на число видимых пикселей и работу геометрических методов.",
        }

    if palette is not None:
        quantized = quantize_image_to_palette(working, palette)
        index_map = np.asarray(quantized.index_map, dtype=np.int32)
        report = {
            "original_size": {"width": source_image.width, "height": source_image.height},
            "target_size": {"width": width, "height": height},
            "fit_mode": fit_mode,
            "background_mode": background_mode,
            "background_report": background_report,
            "quantization_algorithm": "saved browser palette + CIELAB/CIEDE2000 nearest color; no dithering",
            "requested_palette_colors": len(palette),
            "used_palette_colors": int(np.unique(index_map[index_map >= 0]).size),
            "browser_palette_used": True,
            "palette_source": palette_info or {},
            "palette_quantization_report": quantized.report,
            "source_visible_pixel_count": int(np.count_nonzero(index_map >= 0)),
            "palette_note": (
                "Все планировщики используют один и тот же снимок карты цветов, построенный "
                "по сохранённым образцам игровой палитры. Геометрические планы не выполняют "
                "дополнительную квантовку."
            ),
        }
        return index_map, palette, report, quantized.image

    # Explicit optional baseline: synthetic colors derived from the source image.
    rgb_image = working.convert("RGB")
    quantized_image = rgb_image.quantize(
        colors=quantize_colors,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    source_indexes = np.asarray(quantized_image, dtype=np.int32).copy()
    alpha = np.asarray(working.getchannel("A"), dtype=np.uint8)
    source_indexes[alpha == 0] = -1

    raw_palette = quantized_image.getpalette()
    if not raw_palette:
        raise ValueError("Pillow не вернул палитру для benchmark-изображения.")

    old_indexes = sorted(int(value) for value in np.unique(source_indexes[source_indexes >= 0]))
    if not old_indexes:
        raise ValueError("После обработки фона не осталось видимых пикселей.")

    compact_indexes = np.full(source_indexes.shape, -1, dtype=np.int32)
    palette_entries: list[dict[str, Any]] = []
    for new_index, old_index in enumerate(old_indexes):
        offset = old_index * 3
        rgb = [int(channel) for channel in raw_palette[offset:offset + 3]]
        if len(rgb) != 3:
            raise ValueError(f"Не удалось прочитать RGB цвета палитры с индексом {old_index}.")
        compact_indexes[source_indexes == old_index] = new_index
        palette_entries.append({
            "id": f"benchmark-{new_index + 1}",
            "name": f"Benchmark color {new_index + 1}",
            "rgb": rgb,
            "hex": "#{:02X}{:02X}{:02X}".format(*rgb),
        })

    palette = normalize_palette(palette_entries)
    report = {
        "original_size": {"width": source_image.width, "height": source_image.height},
        "target_size": {"width": width, "height": height},
        "fit_mode": fit_mode,
        "background_mode": background_mode,
        "background_report": background_report,
        "quantization_algorithm": "Pillow MEDIANCUT, no dithering (synthetic baseline)",
        "requested_palette_colors": quantize_colors,
        "used_palette_colors": len(palette),
        "browser_palette_used": False,
        "palette_source": None,
        "palette_note": (
            "Синтетическая палитра создана из эталонного изображения; она не является палитрой браузерной игры."
        ),
        "source_visible_pixel_count": int(np.count_nonzero(compact_indexes >= 0)),
    }
    return compact_indexes, palette, report, working


def _resolved_path(raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else REPO_ROOT / path


def _print_summary(report: dict[str, Any]) -> None:
    print("")
    print("Stage 5 drawing-strategy baseline")
    print("Metric percentages and resource values are estimates, not browser measurements.")
    print(
        f"{'Algorithm':<25} {'Strokes':>9} {'Coverage %':>12} "
        f"{'Exact %':>10} {'Colors':>8} {'Ink %':>9} {'Points %':>11}"
    )
    for item in report["algorithm_results"]:
        print(
            f"{item['name']:<25} "
            f"{item['stroke_count']:>9} "
            f"{item['covered_source_visible_percent']:>12.2f} "
            f"{item['exact_color_match_percent_of_source']:>10.2f} "
            f"{item['actually_drawn_color_count']:>8} "
            f"{item['paint_cost_estimate']['estimated_usage_percent']:>9.2f} "
            f"{item['point_quota_estimate']['estimated_usage_percent']:>11.2f}"
        )
    fit = report["scanline_optimization"]
    print("")
    print(
        "Scanline optimization: block/row step={step}, changed pixels={changed} ({changed_percent:.2f}%), "
        "omitted source pixels={omitted}, colors {before}->{after}, strokes {strokes_before}->{strokes_after}."
        .format(
            step=fit["row_step_px"],
            changed=fit["changed_pixel_count"],
            changed_percent=fit["changed_pixel_percentage"],
            omitted=fit["sampled_row_omitted_pixel_count"],
            before=fit["used_color_count_before"],
            after=fit["used_color_count_after"],
            strokes_before=fit["stroke_count_before"],
            strokes_after=fit["stroke_count_after"],
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Сравнить contour, skeleton, цветной scanline и scanline после подгонки "
            "на одной и той же индексированной карте цветов."
        )
    )
    parser.add_argument("--git-ref", default="origin/master")
    parser.add_argument("--git-path", default="AutoDraw_Stage20/testImages/images.png")
    parser.add_argument("--target-width", type=int, default=646)
    parser.add_argument("--target-height", type=int, default=323)
    parser.add_argument("--fit-mode", choices=("contain", "cover", "stretch"), default="contain")
    parser.add_argument("--quantize-colors", type=int, default=8, help="Color count only for --synthetic-palette.")
    parser.add_argument(
        "--palette-json",
        default="AutoDraw_Stage20/data/palettes/profiles/Browser_palette.autodraw-palette.json",
        help="Saved browser palette/profile JSON; uses CIEDE2000 to map the source image to these exact colors.",
    )
    parser.add_argument(
        "--synthetic-palette",
        action="store_true",
        help="Use an optional MEDIANCUT palette generated from the image instead of the saved game palette.",
    )
    parser.add_argument(
        "--background-mode",
        choices=("preserve", "edge-connected"),
        default="edge-connected",
        help="preserve retains the whole canvas; edge-connected removes only near-white pixels connected to an edge.",
    )
    parser.add_argument("--board-item-type", default="BoardItem2")
    parser.add_argument("--target-usage-percent", type=float, default=75.0)
    parser.add_argument("--point-step-px", type=float, default=2.0)
    parser.add_argument("--point-delay-ms", type=float, default=10.0)
    parser.add_argument("--frame-rate-fps", type=float, default=48.0)
    parser.add_argument("--safety-factor", type=float, default=DEFAULT_POINT_SAFETY_FACTOR)
    parser.add_argument(
        "--output",
        default="AutoDraw_Stage20/benchmark-results/stage5-report.json",
        help="JSON report path, relative to the repository root unless absolute.",
    )
    parser.add_argument(
        "--preview-dir",
        default="AutoDraw_Stage20/benchmark-results/previews",
        help="Directory for transparent PNG previews, relative to the repository root unless absolute.",
    )
    args = parser.parse_args()

    if args.target_width < 1 or args.target_height < 1:
        parser.error("Canvas dimensions must be positive.")
    if not 2 <= args.quantize_colors <= 256:
        parser.error("quantize-colors must be between 2 and 256.")
    if not 10.0 <= args.target_usage_percent <= 95.0:
        parser.error("target-usage-percent must be between 10 and 95.")
    if not 0.0 < args.safety_factor <= 1.0:
        parser.error("safety-factor must be greater than 0 and at most 1.")

    source_image = load_git_image(args.git_ref, args.git_path)
    benchmark_palette = None
    palette_info = None
    if not args.synthetic_palette:
        palette_path = _resolved_path(args.palette_json)
        benchmark_palette, palette_info = load_palette_document(palette_path)
        print(
            f"Using saved browser palette: {palette_info['palette_name']} "
            f"({palette_info['palette_color_count']} colors) from {palette_path}"
        )
        if palette_info.get("missing_required_colors"):
            print(
                "Palette warning: expected base colors missing: "
                + ", ".join(palette_info["missing_required_colors"])
            )
    index_map, palette, image_report, fitted_image = make_index_map(
        source_image,
        width=args.target_width,
        height=args.target_height,
        fit_mode=args.fit_mode,
        quantize_colors=args.quantize_colors,
        background_mode=args.background_mode,
        palette=benchmark_palette,
        palette_info=palette_info,
    )
    point_limit = get_board_point_limit(args.board_item_type)
    source_name = f"{args.git_ref}:{args.git_path}"

    plans: list[tuple[str, dict[str, Any]]] = []
    plans.append((
        "contour",
        build_geometry_color_plan(
            index_map, palette, mode="contour", simplify_tolerance_px=0.8,
            min_component_area=1, source_name=source_name,
        ),
    ))
    plans.append((
        "skeleton",
        build_geometry_color_plan(
            index_map, palette, mode="skeleton", simplify_tolerance_px=0.8,
            min_component_area=1, source_name=source_name,
        ),
    ))
    raw_scanline = build_color_scanline_plan(
        index_map,
        palette,
        source_name=source_name,
        plan_name="Stage 5 baseline color scanline",
        row_step_px=1,
        row_offset_px=0,
        board_item_type=args.board_item_type,
        board_point_limit=point_limit,
        point_step_px=args.point_step_px,
        point_delay_ms=int(round(args.point_delay_ms)),
        frame_rate_fps=args.frame_rate_fps,
        point_quota_safety_factor=args.safety_factor,
    )
    plans.append(("scanline", raw_scanline))

    palette_result = PaletteQuantizationResult(
        image=render_index_map_png(index_map, palette),
        index_map=index_map,
        report={"source_name": source_name, "benchmark_input": image_report},
    )
    optimized_result, chosen_step, chosen_offset, optimization_report = fit_result_to_paint_budget(
        palette_result,
        palette,
        target_usage_percent=args.target_usage_percent,
        board_item_type=args.board_item_type,
        board_point_limit=point_limit,
        point_step_px=args.point_step_px,
        point_delay_ms=int(round(args.point_delay_ms)),
        frame_rate_fps=args.frame_rate_fps,
        point_quota_safety_factor=args.safety_factor,
    )
    optimized_scanline = build_color_scanline_plan(
        optimized_result.index_map,
        palette,
        source_name=source_name,
        plan_name="Stage 5 scanline fitted to resource target",
        row_step_px=chosen_step,
        row_offset_px=chosen_offset,
        board_item_type=args.board_item_type,
        board_point_limit=point_limit,
        point_step_px=args.point_step_px,
        point_delay_ms=int(round(args.point_delay_ms)),
        frame_rate_fps=args.frame_rate_fps,
        point_quota_safety_factor=args.safety_factor,
    )
    plans.append(("scanline_optimized", optimized_scanline))

    algorithm_results = [
        summarize_plan(
            name,
            plan,
            index_map,
            board_item_type=args.board_item_type,
            point_step_px=args.point_step_px,
            point_delay_ms=args.point_delay_ms,
            frame_rate_fps=args.frame_rate_fps,
            safety_factor=args.safety_factor,
        )
        for name, plan in plans
    ]
    optimized_index_map = np.asarray(optimized_result.index_map, dtype=np.int32)
    changed_pixels = int(np.count_nonzero(optimized_index_map != index_map))
    visible_mask = index_map >= 0
    color_changed_visible = int(np.count_nonzero(
        visible_mask & (optimized_index_map >= 0) & (optimized_index_map != index_map)
    ))
    omitted_by_sampling = int(optimization_report["sampled_row_omitted_pixel_count"])

    report = {
        "schema_version": 1,
        "stage": 5,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "git_ref": args.git_ref,
            "git_path": args.git_path,
            **image_report,
        },
        "resource_configuration": {
            "board_item_type": args.board_item_type,
            "board_point_limit": point_limit,
            "target_usage_percent": args.target_usage_percent,
            "point_step_px": args.point_step_px,
            "point_delay_ms": args.point_delay_ms,
            "frame_rate_fps": args.frame_rate_fps,
            "frame_rate_is_measured": False,
            "safety_factor": args.safety_factor,
            "interpretation": (
                "Both resource metrics are estimates. The 48 FPS value is the engine's nominal setting, "
                "not a measured browser frame rate for this benchmark."
            ),
        },
        "algorithm_results": algorithm_results,
        "scanline_optimization": {
            **optimization_report,
            "changed_pixels_from_input_index_map": changed_pixels,
            "visible_pixels_changed_to_another_palette_color": color_changed_visible,
            "changed_pixels_from_input_map_percent": round(100.0 * changed_pixels / index_map.size, 4),
            "visible_source_pixels_omitted_by_row_sampling": omitted_by_sampling,
        },
        "interpretation_limits": [
            "This run uses one shared index map, so differences reflect planning strategies rather than different input colors.",
            "By default the map is quantized to the saved browser palette with CIELAB/CIEDE2000; use --synthetic-palette only for a synthetic comparison.",
            "Coverage is rasterized with a 1 px line and does not simulate the game's actual brush width.",
            "Point and ink values are estimates and must be checked against a controlled browser run.",
        ],
    }

    preview_dir = _resolved_path(args.preview_dir)
    preview_dir.mkdir(parents=True, exist_ok=True)
    render_index_map_png(index_map, palette).save(preview_dir / "source-index-map.png")
    for name, plan in plans:
        from drawing_algorithm_benchmark import render_plan_index_map

        rendered = render_plan_index_map(plan)
        render_index_map_png(rendered, palette).save(preview_dir / f"{name}.png")

    output_path = _resolved_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _print_summary(report)
    print(f"\nJSON report: {output_path}")
    print(f"Preview directory: {preview_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
