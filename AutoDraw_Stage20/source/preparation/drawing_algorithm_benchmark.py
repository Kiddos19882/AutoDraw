"""Common rendering and resource metrics for Stage 5 algorithm comparisons."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from palette_quantization import normalize_palette
from PIL import Image, ImageDraw

from board_resource_model import DEFAULT_POINT_SAFETY_FACTOR, get_board_point_limit
from engine_point_calibration import (
    DEFAULT_EXECUTOR_POINT_DELAY_MS,
    DEFAULT_EXECUTOR_POINT_STEP_PX,
    GAME_ENGINE_DEFAULT_FRAME_RATE_FPS,
    HISTORICAL_CALIBRATION_FRAME_RATE_FPS,
    HISTORICAL_CALIBRATION_POINT_DELAY_MS,
    HISTORICAL_CALIBRATION_POINT_LIMIT,
    HISTORICAL_CALIBRATION_POINT_STEP_PX,
    estimate_point_quota_usage,
)
from paint_cost_model import (
    DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
    DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
    estimate_paint_cost,
)


def load_palette_document(path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load a saved browser palette/profile and return normalized confirmed colors."""
    import json

    palette_path = Path(path)
    try:
        document = json.loads(palette_path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise ValueError(f"Не удалось прочитать файл игровой палитры: {palette_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Файл палитры содержит некорректный JSON: {palette_path}: {exc}") from exc

    if not isinstance(document, dict) or not isinstance(document.get("colors"), list):
        raise ValueError("В JSON палитры должен быть объект с массивом colors.")

    raw_colors = document["colors"]
    if not raw_colors:
        raise ValueError("Файл игровой палитры не содержит цветов.")

    statuses = [
        str(item.get("status", "")).strip().lower()
        for item in raw_colors
        if isinstance(item, dict) and item.get("status") is not None
    ]
    unconfirmed = sorted({status for status in statuses if status not in {"confirmed", "corrected"}})
    if unconfirmed:
        raise ValueError(
            "В файле есть неподтверждённые цвета палитры ("
            + ", ".join(unconfirmed)
            + "). Подтверди образцы на вкладке 3 или используй другой файл."
        )

    try:
        normalized = normalize_palette(raw_colors)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Не удалось проверить цвета игровой палитры: {exc}") from exc

    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    reduction = metadata.get("palette_reduction")
    if not isinstance(reduction, dict):
        reduction = {}

    confirmed_count = sum(
        1 for item in raw_colors
        if isinstance(item, dict) and str(item.get("status", "")).lower() in {"confirmed", "corrected"}
    )
    palette_report = {
        "palette_file": str(palette_path),
        "palette_name": str(document.get("profile_name") or document.get("name") or document.get("palette_id") or palette_path.stem),
        "schema_version": document.get("profile_schema_version", document.get("schema_version")),
        "palette_color_count": len(normalized),
        "sample_statuses_present": bool(statuses),
        "confirmed_color_count": confirmed_count if statuses else None,
        "source": str(metadata.get("source") or document.get("source") or "unknown"),
        "capture_method": str(metadata.get("method") or document.get("capture_method") or "unknown"),
        "captured_at": metadata.get("captured_at") or document.get("created_at"),
        "has_exact_black": any(item["hex"].upper() == "#000000" for item in normalized),
        "has_exact_white": any(item["hex"].upper() == "#FFFFFF" for item in normalized),
        "missing_required_colors": list(reduction.get("missing_required_colors", [])),
    }
    return normalized, palette_report


def render_plan_index_map(plan: dict[str, Any]) -> np.ndarray:
    """Rasterize ordered plan strokes into palette indexes; untouched pixels are -1."""
    canvas = plan.get("canvas")
    if not isinstance(canvas, dict):
        raise ValueError("У плана отсутствует описание холста.")
    try:
        width, height = int(canvas["width"]), int(canvas["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Некорректный размер холста в плане.") from exc
    if width < 1 or height < 1:
        raise ValueError("Размер холста должен быть положительным.")

    rendered_image = Image.new("I", (width, height), -1)
    draw = ImageDraw.Draw(rendered_image)
    strokes = plan.get("strokes")
    if not isinstance(strokes, list):
        raise ValueError("У плана отсутствует список штрихов.")

    for stroke in strokes:
        if not isinstance(stroke, dict):
            continue
        color = stroke.get("color")
        points = stroke.get("points")
        if not isinstance(color, dict) or not isinstance(points, list) or not points:
            continue
        try:
            palette_index = int(color["palette_index"])
            coordinates = [
                (int(round(float(point["x"]))), int(round(float(point["y"]))))
                for point in points
            ]
        except (KeyError, TypeError, ValueError, OverflowError):
            continue

        if stroke.get("closed") and len(coordinates) >= 3 and coordinates[-1] != coordinates[0]:
            coordinates.append(coordinates[0])
        if len(coordinates) == 1:
            draw.point(coordinates[0], fill=palette_index)
        else:
            draw.line(coordinates, fill=palette_index, width=1)

    return np.asarray(rendered_image, dtype=np.int32).copy()


def summarize_plan(
    name: str,
    plan: dict[str, Any],
    source_index_map: Any,
    *,
    board_item_type: str = "BoardItem2",
    point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX,
    point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS,
    frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS,
    safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR,
    paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
    stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
) -> dict[str, Any]:
    """Measure drawing coverage and both existing resource estimates for one plan."""
    source = np.asarray(source_index_map, dtype=np.int32)
    if source.ndim != 2 or source.size == 0:
        raise ValueError("Исходная карта цветов должна быть непустой двумерной матрицей.")

    rendered = render_plan_index_map(plan)
    if rendered.shape != source.shape:
        raise ValueError(
            f"Размер плана {rendered.shape[::-1]} не совпадает с исходной картой {source.shape[::-1]}."
        )

    source_visible = source >= 0
    rendered_visible = rendered >= 0
    source_visible_count = int(np.count_nonzero(source_visible))
    if source_visible_count == 0:
        raise ValueError("В исходной карте нет видимых пикселей.")

    covered = source_visible & rendered_visible
    exact = covered & (source == rendered)
    wrong_color = covered & (source != rendered)
    painted_transparent = (~source_visible) & rendered_visible
    painted_count = int(np.count_nonzero(rendered_visible))
    covered_count = int(np.count_nonzero(covered))
    exact_count = int(np.count_nonzero(exact))
    mismatches = rendered != source

    summary = plan.get("summary") if isinstance(plan.get("summary"), dict) else {}
    strokes = plan.get("strokes") if isinstance(plan.get("strokes"), list) else []
    stroke_count = len(strokes)
    drawing_length = float(summary.get("drawing_length_px", 0.0) or 0.0)
    single_pixel_count = summary.get("single_pixel_stroke_count")
    if isinstance(single_pixel_count, bool) or not isinstance(single_pixel_count, int):
        single_pixel_count = 0
        for stroke in strokes:
            points = stroke.get("points", []) if isinstance(stroke, dict) else []
            if len(points) >= 2:
                first, last = points[0], points[-1]
                try:
                    distance = math.hypot(
                        float(last["x"]) - float(first["x"]),
                        float(last["y"]) - float(first["y"]),
                    )
                except (KeyError, TypeError, ValueError):
                    continue
                if distance <= 1e-7 and not stroke.get("closed"):
                    single_pixel_count += 1

    ink = estimate_paint_cost(
        drawing_length,
        stroke_count,
        single_pixel_count,
        stroke_overhead_px_equivalent=stroke_overhead_px_equivalent,
        paint_budget_px_equivalent=paint_budget_px_equivalent,
    )
    point_limit = get_board_point_limit(board_item_type)
    point_report = estimate_point_quota_usage(
        drawing_length,
        stroke_count,
        board_point_limit=point_limit,
        single_pixel_stroke_count=single_pixel_count,
        point_step_px=point_step_px,
        point_delay_ms=point_delay_ms,
        frame_rate_fps=frame_rate_fps,
        calibration_point_limit=HISTORICAL_CALIBRATION_POINT_LIMIT,
        calibration_point_step_px=HISTORICAL_CALIBRATION_POINT_STEP_PX,
        calibration_point_delay_ms=HISTORICAL_CALIBRATION_POINT_DELAY_MS,
        calibration_frame_rate_fps=HISTORICAL_CALIBRATION_FRAME_RATE_FPS,
        safety_factor=safety_factor,
    )

    total_pixels = int(source.size)
    drawn_colors = np.unique(rendered[rendered_visible])
    source_colors = np.unique(source[source_visible])
    return {
        "name": name,
        "plan_type": plan.get("plan_type"),
        "mode": (plan.get("generation") or {}).get("mode")
        if isinstance(plan.get("generation"), dict) else None,
        "canvas": {"width": int(source.shape[1]), "height": int(source.shape[0])},
        "source_visible_pixel_count": source_visible_count,
        "planned_visible_pixel_count": summary.get("visible_pixel_count"),
        "rendered_pixel_count": painted_count,
        "covered_source_pixel_count": covered_count,
        "covered_source_visible_percent": round(100.0 * covered_count / source_visible_count, 4),
        "exact_color_pixel_count": exact_count,
        "exact_color_match_percent_of_source": round(100.0 * exact_count / source_visible_count, 4),
        "correct_color_percent_of_covered_pixels": round(
            100.0 * exact_count / covered_count, 4
        ) if covered_count else 0.0,
        "wrong_color_pixel_count": int(np.count_nonzero(wrong_color)),
        "painted_transparent_pixel_count": int(np.count_nonzero(painted_transparent)),
        "pixel_mismatch_count": int(np.count_nonzero(mismatches)),
        "pixel_mismatch_percent_of_canvas": round(
            100.0 * int(np.count_nonzero(mismatches)) / total_pixels, 4
        ),
        "used_source_color_count": int(source_colors.size),
        "actually_drawn_color_count": int(drawn_colors.size),
        "stroke_count": stroke_count,
        "drawing_length_px": round(drawing_length, 3),
        "single_pixel_stroke_count": int(single_pixel_count),
        "paint_cost_estimate": {
            "model_id": ink["model_id"],
            "is_estimate": True,
            "estimated_total_ink_px_equivalent": ink["estimated_total_ink_px_equivalent"],
            "estimated_usage_percent": ink["estimated_usage_percent"],
            "paint_budget_px_equivalent": ink["estimated_budget_px_equivalent"],
            "stroke_overhead_px_equivalent": ink["stroke_overhead_px_equivalent"],
        },
        "point_quota_estimate": {
            "model_id": point_report["model_id"],
            "is_estimate": True,
            "frame_rate_fps_is_nominal": True,
            "board_point_limit": point_report["board_point_limit"],
            "planning_budget_points": point_report["planning_budget_points"],
            "estimated_point_count": point_report["estimated_point_count"],
            "estimated_usage_percent": point_report["estimated_usage_percent"],
            "estimated_safe_budget_usage_percent": point_report["estimated_safe_budget_usage_percent"],
            "risk_level": point_report["risk_level"],
        },
    }


def render_index_map_png(index_map: Any, palette: list[dict[str, Any]]) -> Image.Image:
    """Render an index map as RGBA PNG for a side-by-side visual check."""
    indexes = np.asarray(index_map, dtype=np.int32)
    if indexes.ndim != 2:
        raise ValueError("Карта цветов должна быть двумерной.")
    result = np.zeros((indexes.shape[0], indexes.shape[1], 4), dtype=np.uint8)
    for item in palette:
        index = int(item["index"])
        rgb = np.asarray(item["rgb"], dtype=np.uint8)
        mask = indexes == index
        result[mask, :3] = rgb
        result[mask, 3] = 255
    return Image.fromarray(result, mode="RGBA")
