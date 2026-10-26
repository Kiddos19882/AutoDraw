from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from palette_quantization import PaletteQuantizationError, normalize_palette
from paint_cost_model import (
    DEFAULT_PAINT_BUDGET_PX_EQUIVALENT, DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
    estimate_color_plan_paint_cost,
)

COLOR_SCANLINE_SCHEMA_VERSION = 1
COLOR_SCANLINE_PLAN_TYPE = "autodraw_color_scanline_plan"
MAX_IMAGE_PIXELS = 40_000_000
MAX_COLOR_STROKES = 250_000


class ColorScanlinePlanError(ValueError):
    """Raised when a color scanline plan cannot be built, loaded, or saved safely."""


def _normalize_palette_document(palette: Any) -> list[dict[str, Any]]:
    if isinstance(palette, dict):
        raw_colors = palette.get("colors")
    else:
        raw_colors = palette
    try:
        normalized = normalize_palette(raw_colors or [])
    except (PaletteQuantizationError, TypeError, ValueError) as exc:
        raise ColorScanlinePlanError(f"Некорректная палитра: {exc}") from exc
    return normalized


def _validate_index_map(index_map: Any, palette_size: int) -> np.ndarray:
    try:
        indexes = np.asarray(index_map)
    except (TypeError, ValueError) as exc:
        raise ColorScanlinePlanError("Не удалось прочитать карту индексов цветов.") from exc
    if indexes.ndim != 2:
        raise ColorScanlinePlanError("Карта цветов должна быть двумерной матрицей.")
    height, width = indexes.shape
    if height <= 0 or width <= 0:
        raise ColorScanlinePlanError("Размер карты цветов должен быть положительным.")
    if width * height > MAX_IMAGE_PIXELS:
        raise ColorScanlinePlanError(f"Изображение слишком большое: максимум {MAX_IMAGE_PIXELS:,} пикселей.")
    if indexes.dtype.kind not in "iu":
        raise ColorScanlinePlanError("Индексы цветов должны быть целыми числами.")
    if indexes.size:
        minimum = int(indexes.min())
        maximum = int(indexes.max())
        if minimum < -1 or maximum >= palette_size:
            raise ColorScanlinePlanError(
                f"Карта цветов содержит индекс за пределами палитры: диапазон {minimum}…{maximum}, "
                f"допустимо -1…{palette_size - 1}."
            )
    return indexes.astype(np.int32, copy=False)


def build_color_scanline_plan(
    index_map: Any,
    palette: Any,
    *,
    source_report: dict[str, Any] | None = None,
    source_name: str | None = None,
    plan_name: str = "Цветной scanline-план",
    row_step_px: int = 1,
    row_offset_px: int = 0,
    max_strokes: int = MAX_COLOR_STROKES,
    paint_stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
    paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
) -> dict[str, Any]:
    """Build color runs in strict top-to-bottom, left-to-right order.

    index -1 means a transparent pixel and splits a run. Consecutive pixels are
    merged only when they carry the exact same palette index. Single-pixel runs
    intentionally remain zero-length point strokes; widening them belongs to the
    executor stage because widening here could paint over an adjacent color.
    """
    normalized_palette = _normalize_palette_document(palette)
    if isinstance(max_strokes, bool) or not isinstance(max_strokes, int) or max_strokes < 1:
        raise ColorScanlinePlanError("Лимит штрихов должен быть положительным целым числом.")
    if isinstance(row_step_px, bool) or not isinstance(row_step_px, int) or row_step_px < 1:
        raise ColorScanlinePlanError("Шаг строк должен быть положительным целым числом.")
    if isinstance(row_offset_px, bool) or not isinstance(row_offset_px, int):
        raise ColorScanlinePlanError("Смещение строк должно быть целым числом.")
    if not 0 <= row_offset_px < row_step_px:
        raise ColorScanlinePlanError("Смещение строк должно быть от 0 до шага строк минус 1.")
    indexes = _validate_index_map(index_map, len(normalized_palette))
    height, width = indexes.shape
    source_visible_pixels = int(np.count_nonzero(indexes >= 0))
    transparent_pixels = int(indexes.size - source_visible_pixels)
    if source_visible_pixels == 0:
        raise ColorScanlinePlanError("В изображении нет непрозрачных пикселей для рисования.")
    # The color plan may intentionally sample every Nth row. Pixels on skipped
    # rows are reported separately from truly transparent pixels.
    sampled_rows = range(row_offset_px, height, row_step_px)
    drawn_visible_pixels = sum(int(np.count_nonzero(indexes[y] >= 0)) for y in sampled_rows)
    omitted_by_row_step_pixels = source_visible_pixels - drawn_visible_pixels
    if drawn_visible_pixels == 0:
        raise ColorScanlinePlanError(
            f"При шаге строк {row_step_px} px не осталось видимых пикселей для рисования. "
            "Уменьшите шаг строк."
        )
    visible_pixels = drawn_visible_pixels

    strokes: list[dict[str, Any]] = []
    color_pixel_counts = np.zeros(len(normalized_palette), dtype=np.int64)
    color_stroke_counts = np.zeros(len(normalized_palette), dtype=np.int64)
    drawing_length = 0.0
    pen_up_distance = 0.0
    single_pixel_runs = 0
    color_switch_count = 0
    previous_end: tuple[int, int] | None = None
    previous_color_index: int | None = None

    for y in range(row_offset_px, height, row_step_px):
        row = indexes[y]
        valid = row >= 0
        if not bool(np.any(valid)):
            continue
        # A run starts whenever a non-transparent pixel differs from the pixel on its left.
        starts = np.flatnonzero(valid & np.r_[True, row[1:] != row[:-1]])
        # A run ends whenever a non-transparent pixel differs from the pixel on its right.
        ends = np.flatnonzero(valid & np.r_[row[:-1] != row[1:], True])
        if len(starts) != len(ends):  # defensive invariant; should be impossible for validated indexes
            raise ColorScanlinePlanError(f"Не удалось разделить строку {y} на цветовые участки.")

        for start_raw, end_raw in zip(starts, ends):
            start, end = int(start_raw), int(end_raw)
            palette_index = int(row[start])
            if palette_index != int(row[end]):
                raise ColorScanlinePlanError(f"Внутри участка строки {y} обнаружена неожиданная смена цвета.")
            pixel_count = end - start + 1
            color = normalized_palette[palette_index]
            if len(strokes) >= max_strokes:
                raise ColorScanlinePlanError(
                    f"План превысил лимит {max_strokes:,} штрихов. Уменьшите изображение или упростите цветовую детализацию."
                )

            start_point = {"x": float(start), "y": float(y)}
            end_point = {"x": float(end), "y": float(y)}
            is_single_pixel = start == end
            stroke = {
                "name": f"color_scanline_y{y}_x{start}-{end}_{color['id']}",
                "closed": False,
                "points": [start_point, end_point],
                "color": {
                    "palette_index": palette_index,
                    "id": color["id"],
                    "name": color["name"],
                    "rgb": list(color["rgb"]),
                    "hex": color["hex"],
                },
                "metadata": {
                    "row_y": y,
                    "x_start": start,
                    "x_end": end,
                    "pixel_count": pixel_count,
                    "single_pixel": is_single_pixel,
                },
            }
            strokes.append(stroke)
            color_pixel_counts[palette_index] += pixel_count
            color_stroke_counts[palette_index] += 1
            drawing_length += float(end - start)
            if is_single_pixel:
                single_pixel_runs += 1
            if previous_end is not None:
                pen_up_distance += math.hypot(start - previous_end[0], y - previous_end[1])
            if previous_color_index is not None and previous_color_index != palette_index:
                color_switch_count += 1
            previous_end = (end, y)
            previous_color_index = palette_index

    if not strokes:
        raise ColorScanlinePlanError("Не удалось сформировать штрихи из цветного изображения.")

    used_colors: list[dict[str, Any]] = []
    for color in normalized_palette:
        idx = int(color["index"])
        pixels = int(color_pixel_counts[idx])
        color_strokes = int(color_stroke_counts[idx])
        if pixels:
            used_colors.append({
                "palette_index": idx,
                "id": color["id"],
                "name": color["name"],
                "rgb": list(color["rgb"]),
                "hex": color["hex"],
                "pixel_count": pixels,
                "stroke_count": color_strokes,
                "percentage_visible": round(100.0 * pixels / visible_pixels, 4),
            })

    paint_model_config = {
        "model_id": "empirical-ink-cost-v1",
        "stroke_overhead_px_equivalent": float(paint_stroke_overhead_px_equivalent),
        "budget_px_equivalent": float(paint_budget_px_equivalent),
        "single_pixel_execution_length_px": 1.0,
    }
    source_info: dict[str, Any] = {
        "name": str(source_name or "Изображение в цветах палитры"),
        "quantization_algorithm": "CIELAB + CIEDE2000",
    }
    if isinstance(source_report, dict):
        source_size = source_report.get("source_size")
        if isinstance(source_size, dict):
            source_info["quantized_size"] = {
                "width": source_size.get("width"),
                "height": source_size.get("height"),
            }
        profile_info = source_report.get("palette_profile")
        if isinstance(profile_info, dict):
            source_info["palette_profile"] = {
                "name": profile_info.get("name"),
                "file": profile_info.get("file"),
            }
        for key in ("changed_pixel_count", "mean_delta_e_2000", "p95_delta_e_2000", "max_delta_e_2000"):
            if key in source_report:
                source_info[key] = source_report[key]
        budget_report = source_report.get("paint_budget_optimization")
        if isinstance(budget_report, dict):
            source_info["paint_budget_optimization"] = {
                key: budget_report[key]
                for key in (
                    "enabled", "target_usage_percent", "budget_px_equivalent",
                    "target_cost_px_equivalent", "block_size_px", "row_step_px", "row_offset_px",
                    "stroke_count_before", "stroke_count_after", "estimated_ink_before_px_equivalent",
                    "estimated_ink_after_px_equivalent", "used_color_count_before",
                    "used_color_count_after", "changed_pixel_count", "changed_pixel_percentage",
                    "fallback_used",
                )
                if key in budget_report
            }
        merge_report = source_report.get("rare_color_merge")
        if isinstance(merge_report, dict):
            # Keep a concise provenance record on the executable color plan.
            source_info["rare_color_merge"] = {
                key: merge_report[key]
                for key in (
                    "enabled", "min_pixel_count", "min_percentage", "max_delta_e_2000",
                    "rare_color_count_merged", "remapped_pixel_count",
                    "estimated_scanline_strokes_before", "estimated_scanline_strokes_after",
                    "estimated_scanline_strokes_reduced", "estimated_scanline_stroke_reduction_percentage",
                    "mean_delta_e_2000_for_merged_colors", "max_delta_e_2000_for_merged_colors",
                )
                if key in merge_report
            }

    plan = {
        "schema_version": COLOR_SCANLINE_SCHEMA_VERSION,
        "plan_type": COLOR_SCANLINE_PLAN_TYPE,
        "name": str(plan_name).strip() or "Цветной scanline-план",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "coordinate_system": "local_canvas_pixels",
        "canvas": {"width": int(width), "height": int(height)},
        "source": source_info,
        "palette": normalized_palette,
        "generation": {
            "method": "color_scanline",
            "row_step_px": row_step_px,
            "row_offset_px": row_offset_px,
            "row_order": "top_to_bottom",
            "stroke_order": "left_to_right_within_row",
            "run_rule": "merge_adjacent_pixels_with_same_palette_index_only",
            "transparent_pixels": "skipped_and_split_runs",
            "single_pixel_rule": "kept_as_zero_length_point_stroke",
            "note": (
                "Цветные штрихи сохраняют порядок строк сверху вниз и участков слева направо. "
                "Перестановка по цветам запрещена. При шаге больше 1 пропущенные строки не рисуются."
            ),
            "paint_cost_model": paint_model_config,
        },
        "summary": {
            "stroke_count": len(strokes),
            "point_count": len(strokes) * 2,
            "drawing_length_px": round(drawing_length, 3),
            "pen_up_distance_px": round(pen_up_distance, 3),
            "visible_pixel_count": visible_pixels,
            "source_visible_pixel_count": source_visible_pixels,
            "omitted_by_row_step_pixel_count": omitted_by_row_step_pixels,
            "transparent_pixel_count": transparent_pixels,
            "single_pixel_stroke_count": single_pixel_runs,
            "color_switch_count": color_switch_count,
            "color_selection_count_estimate": 1 + color_switch_count,
            "used_palette_color_count": len(used_colors),
            "unused_palette_color_count": len(normalized_palette) - len(used_colors),
            "used_colors": used_colors,
        },
        "strokes": strokes,
    }
    # Include both the estimate for a shared pool and per-color estimates. The
    # real game was calibrated with a single color, so either resource model may apply.
    plan["summary"]["paint_cost_estimate"] = estimate_color_plan_paint_cost(
        plan,
        stroke_overhead_px_equivalent=paint_model_config["stroke_overhead_px_equivalent"],
        paint_budget_px_equivalent=paint_model_config["budget_px_equivalent"],
    )
    validate_color_scanline_plan(plan)
    return plan


def validate_color_scanline_plan(plan: Any) -> dict[str, Any]:
    """Validate a serialized color plan, including geometry and stable order."""
    if not isinstance(plan, dict):
        raise ColorScanlinePlanError("Корень цветного плана должен быть JSON-объектом.")
    if plan.get("plan_type") != COLOR_SCANLINE_PLAN_TYPE:
        raise ColorScanlinePlanError("Это не цветной scanline-план AutoDraw.")
    if plan.get("schema_version") != COLOR_SCANLINE_SCHEMA_VERSION:
        raise ColorScanlinePlanError(f"Неподдерживаемая версия цветного плана: {plan.get('schema_version')!r}.")
    canvas = plan.get("canvas")
    if not isinstance(canvas, dict):
        raise ColorScanlinePlanError("В плане отсутствует объект canvas.")
    try:
        raw_width, raw_height = canvas["width"], canvas["height"]
        width, height = int(raw_width), int(raw_height)
    except (KeyError, TypeError, ValueError) as exc:
        raise ColorScanlinePlanError("Размеры холста должны быть целыми числами.") from exc
    if isinstance(raw_width, bool) or isinstance(raw_height, bool) or width != raw_width or height != raw_height:
        raise ColorScanlinePlanError("Размеры холста должны быть целыми числами без округления.")
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise ColorScanlinePlanError("Размер холста недопустим.")

    palette = _normalize_palette_document(plan.get("palette"))
    generation = plan.get("generation", {})
    if not isinstance(generation, dict):
        raise ColorScanlinePlanError("generation должен быть объектом.")
    raw_row_step = generation.get("row_step_px", 1)
    if isinstance(raw_row_step, bool) or not isinstance(raw_row_step, int) or raw_row_step < 1:
        raise ColorScanlinePlanError("Шаг строк в плане должен быть положительным целым числом.")
    row_step_px = raw_row_step
    raw_row_offset = generation.get("row_offset_px", 0)
    if isinstance(raw_row_offset, bool) or not isinstance(raw_row_offset, int):
        raise ColorScanlinePlanError("Смещение строк в плане должно быть целым числом.")
    row_offset_px = raw_row_offset
    if not 0 <= row_offset_px < row_step_px or row_offset_px >= height:
        raise ColorScanlinePlanError("Смещение строк выходит за допустимый диапазон.")
    raw_strokes = plan.get("strokes")
    if not isinstance(raw_strokes, list) or not raw_strokes:
        raise ColorScanlinePlanError("В плане отсутствуют цветные штрихи.")
    if len(raw_strokes) > MAX_COLOR_STROKES:
        raise ColorScanlinePlanError(f"План превышает лимит {MAX_COLOR_STROKES:,} штрихов.")

    last_y = -1
    last_x_end = -1
    last_row: int | None = None
    visible_pixels_sum = 0
    single_pixel_count = 0
    per_color_pixels = [0] * len(palette)
    per_color_strokes = [0] * len(palette)
    drawing_length = 0.0
    pen_up = 0.0
    previous_end: tuple[float, float] | None = None
    previous_color: int | None = None
    switches = 0

    for stroke_number, stroke in enumerate(raw_strokes, start=1):
        if not isinstance(stroke, dict):
            raise ColorScanlinePlanError(f"Штрих №{stroke_number} должен быть объектом.")
        points = stroke.get("points")
        if not isinstance(points, list) or len(points) != 2:
            raise ColorScanlinePlanError(f"Штрих №{stroke_number} должен содержать ровно две точки.")
        try:
            x1, y1 = float(points[0]["x"]), float(points[0]["y"])
            x2, y2 = float(points[1]["x"]), float(points[1]["y"])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ColorScanlinePlanError(f"Координаты штриха №{stroke_number} повреждены.") from exc
        if not all(math.isfinite(value) for value in (x1, y1, x2, y2)):
            raise ColorScanlinePlanError(f"Координаты штриха №{stroke_number} должны быть конечными числами.")
        if not (0 <= x1 <= x2 < width and y1 == y2 and 0 <= y1 < height):
            raise ColorScanlinePlanError(f"Штрих №{stroke_number} выходит за границы или не является горизонтальным.")
        if x1 != int(x1) or x2 != int(x2) or y1 != int(y1):
            raise ColorScanlinePlanError(f"Штрих №{stroke_number} должен располагаться на целочисленных координатах пикселей.")

        row_y = int(y1)
        start_x, end_x = int(x1), int(x2)
        if row_y < row_offset_px or (row_y - row_offset_px) % row_step_px != 0:
            raise ColorScanlinePlanError(
                f"Штрих №{stroke_number} находится в строке {row_y}, пропущенной схемой "
                f"шага {row_step_px} и смещения {row_offset_px}."
            )
        if row_y < last_y or (row_y == last_y and start_x <= last_x_end):
            raise ColorScanlinePlanError("Порядок штрихов нарушен: требуется сверху вниз и слева направо без перекрытий.")
        if last_row == row_y and start_x <= last_x_end:
            raise ColorScanlinePlanError("Штрихи одной строки перекрываются.")

        color = stroke.get("color")
        if not isinstance(color, dict):
            raise ColorScanlinePlanError(f"У штриха №{stroke_number} отсутствует цвет.")
        try:
            palette_index = int(color["palette_index"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ColorScanlinePlanError(f"У штриха №{stroke_number} некорректный индекс палитры.") from exc
        if not 0 <= palette_index < len(palette):
            raise ColorScanlinePlanError(f"Индекс палитры штриха №{stroke_number} выходит за границы палитры.")
        expected_color = palette[palette_index]
        if color.get("hex", "").upper() != expected_color["hex"] or color.get("rgb") != expected_color["rgb"]:
            raise ColorScanlinePlanError(f"Цвет штриха №{stroke_number} не совпадает с указанным цветом палитры.")

        metadata = stroke.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ColorScanlinePlanError(f"Метаданные штриха №{stroke_number} должны быть объектом.")
        expected_count = end_x - start_x + 1
        if metadata.get("pixel_count") != expected_count:
            raise ColorScanlinePlanError(f"Число пикселей штриха №{stroke_number} не соответствует его координатам.")
        if metadata.get("row_y") != row_y or metadata.get("x_start") != start_x or metadata.get("x_end") != end_x:
            raise ColorScanlinePlanError(f"Координаты в метаданных штриха №{stroke_number} не совпадают с геометрией.")
        is_single = start_x == end_x
        if bool(metadata.get("single_pixel")) != is_single:
            raise ColorScanlinePlanError(f"Флаг одиночного пикселя штриха №{stroke_number} некорректен.")

        visible_pixels_sum += expected_count
        per_color_pixels[palette_index] += expected_count
        per_color_strokes[palette_index] += 1
        drawing_length += end_x - start_x
        if is_single:
            single_pixel_count += 1
        if previous_end is not None:
            pen_up += math.hypot(x1 - previous_end[0], y1 - previous_end[1])
        if previous_color is not None and previous_color != palette_index:
            switches += 1
        previous_end = (x2, y2)
        previous_color = palette_index
        last_y, last_x_end, last_row = row_y, end_x, row_y

    summary = plan.get("summary")
    if not isinstance(summary, dict):
        raise ColorScanlinePlanError("В плане отсутствует summary.")
    actual_summary = {
        "stroke_count": len(raw_strokes),
        "point_count": len(raw_strokes) * 2,
        "drawing_length_px": round(drawing_length, 3),
        "pen_up_distance_px": round(pen_up, 3),
        "visible_pixel_count": visible_pixels_sum,
        "single_pixel_stroke_count": single_pixel_count,
        "color_switch_count": switches,
    }
    for key, actual in actual_summary.items():
        if summary.get(key) != actual:
            raise ColorScanlinePlanError(f"Сводка плана не совпадает с геометрией: поле {key}.")

    # Legacy row_step=1 plans only stored visible_pixel_count. For those files,
    # omitted_by_row_step defaults to zero and behavior remains backward compatible.
    omitted_count_raw = summary.get("omitted_by_row_step_pixel_count", 0)
    source_visible_raw = summary.get("source_visible_pixel_count", visible_pixels_sum + omitted_count_raw)
    transparent_count = int(summary.get("transparent_pixel_count", -1))
    try:
        omitted_count = int(omitted_count_raw)
        source_visible_count = int(source_visible_raw)
    except (TypeError, ValueError) as exc:
        raise ColorScanlinePlanError("Число пропущенных пикселей должно быть целым.") from exc
    if omitted_count < 0 or source_visible_count < visible_pixels_sum:
        raise ColorScanlinePlanError("Сводка содержит недопустимое число пропущенных пикселей.")
    if source_visible_count != visible_pixels_sum + omitted_count:
        raise ColorScanlinePlanError("Видимые и пропущенные по шагу строки пиксели не совпадают с исходной маской.")
    if transparent_count != width * height - source_visible_count:
        raise ColorScanlinePlanError("Количество прозрачных пикселей в сводке не соответствует исходному изображению.")
    if row_step_px == 1 and row_offset_px != 0:
        raise ColorScanlinePlanError("При шаге строк 1 px смещение должно быть равно 0.")
    if omitted_count and row_step_px == 1:
        raise ColorScanlinePlanError("При шаге строк 1 px не должно быть пропущенных строк.")
    if summary.get("color_selection_count_estimate") != (1 + switches):
        raise ColorScanlinePlanError("Оценка количества выборов цвета не соответствует порядку штрихов.")
    actual_used_colors = summary.get("used_colors")
    if not isinstance(actual_used_colors, list):
        raise ColorScanlinePlanError("В сводке отсутствует список использованных цветов.")
    expected_used_colors = []
    for color in palette:
        idx = int(color["index"])
        pixels = per_color_pixels[idx]
        if pixels:
            expected_used_colors.append({
                "palette_index": idx,
                "id": color["id"],
                "name": color["name"],
                "rgb": list(color["rgb"]),
                "hex": color["hex"],
                "pixel_count": pixels,
                "stroke_count": per_color_strokes[idx],
                "percentage_visible": round(100.0 * pixels / visible_pixels_sum, 4),
            })
    if actual_used_colors != expected_used_colors:
        raise ColorScanlinePlanError("Список использованных цветов не соответствует штрихам плана.")
    if summary.get("used_palette_color_count") != len(expected_used_colors):
        raise ColorScanlinePlanError("Число использованных цветов не соответствует штрихам плана.")
    if summary.get("unused_palette_color_count") != len(palette) - len(expected_used_colors):
        raise ColorScanlinePlanError("Число неиспользованных цветов не соответствует палитре.")

    # Newer plans include a reproducible estimate. Older saved plans remain valid;
    # the UI/executor can calculate an estimate on load without rewriting them.
    stored_estimate = summary.get("paint_cost_estimate")
    stored_model = generation.get("paint_cost_model")
    if stored_estimate is not None:
        if not isinstance(stored_estimate, dict) or not isinstance(stored_model, dict):
            raise ColorScanlinePlanError("Сводка оценки краски или параметры модели повреждены.")
        if stored_model.get("model_id") != "empirical-ink-cost-v1":
            raise ColorScanlinePlanError("Неизвестная модель расхода краски в цветном плане.")
        try:
            expected_estimate = estimate_color_plan_paint_cost(
                plan,
                stroke_overhead_px_equivalent=stored_model["stroke_overhead_px_equivalent"],
                paint_budget_px_equivalent=stored_model["budget_px_equivalent"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ColorScanlinePlanError(f"Некорректные параметры модели расхода краски: {exc}") from exc
        for key in (
            "model_id", "stroke_count", "risk_level", "estimated_total_ink_px_equivalent",
            "estimated_budget_px_equivalent", "estimated_usage_percent", "effective_path_length_px",
            "per_color_estimates", "max_per_color_usage_percent", "highest_use_color",
        ):
            if stored_estimate.get(key) != expected_estimate.get(key):
                raise ColorScanlinePlanError(f"Оценка расхода краски не соответствует геометрии плана: поле {key}.")
    return plan


def save_color_scanline_plan(path: str | Path, plan: dict[str, Any]) -> Path:
    """Validate and atomically save a color scanline plan."""
    validate_color_scanline_plan(plan)
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", prefix=f".{target.stem}.", suffix=".tmp",
            dir=target.parent, delete=False,
        ) as file:
            temporary = Path(file.name)
            json.dump(plan, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary.replace(target)
        return target
    except (OSError, TypeError, ValueError) as exc:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        raise ColorScanlinePlanError(f"Не удалось сохранить цветной план: {exc}") from exc


def load_color_scanline_plan(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        plan = json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ColorScanlinePlanError(f"Не удалось прочитать цветной план: {exc}") from exc
    return validate_color_scanline_plan(plan)


def render_color_scanline_preview(
    plan: dict[str, Any], *, max_dimension: int = 1200, expand_single_pixel_strokes: bool = False
) -> Image.Image:
    """Render plan strokes at canvas resolution; optionally preview executor single-pixel expansion.

    Stage 19 defaults to the exact one-pixel map. Stage 20 can enable expansion to
    show the short one-pixel drag that the executor will make instead of a click.
    """
    validate_color_scanline_plan(plan)
    width, height = int(plan["canvas"]["width"]), int(plan["canvas"]["height"])
    scale = min(1.0, max_dimension / max(width, height))
    output_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    image = Image.new("RGBA", output_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for stroke in plan["strokes"]:
        start, end = stroke["points"]
        rgb = tuple(int(value) for value in stroke["color"]["rgb"])
        x1, y1 = round(float(start["x"]) * scale), round(float(start["y"]) * scale)
        x2, y2 = round(float(end["x"]) * scale), round(float(end["y"]) * scale)
        is_single_pixel = x1 == x2 and y1 == y2
        if expand_single_pixel_strokes and is_single_pixel and float(start["x"]) < width:
            x2 = round((float(start["x"]) + 1.0) * scale)
        # Downscaling can map adjacent narrow runs onto the same display column.
        # This preview is informative only; the stored plan remains full-resolution.
        if x1 == x2 and y1 == y2:
            draw.point((x1, y1), fill=(*rgb, 255))
        else:
            draw.line((x1, y1, x2, y2), fill=(*rgb, 255), width=1)
    return image
