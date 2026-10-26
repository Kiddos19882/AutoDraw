from __future__ import annotations

import json
import math
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
from PIL import Image, ImageDraw

from palette_quantization import MAX_IMAGE_PIXELS, normalize_palette
from layer_segmentation import filter_small_components as _connected_components
from skeletonization import thin_binary_mask as _zhang_suen_thinning
from skeletonization import trace_skeleton_paths as _skeleton_paths
from stroke_simplification import simplify_path as _simplify_path


GEOMETRY_PLAN_SCHEMA_VERSION = 1
GEOMETRY_PLAN_TYPE = "autodraw_geometry_color_plan"
MAX_GEOMETRY_STROKES = 250_000
_EPSILON = 1e-7


class GeometryColorPlanError(ValueError):
    """Raised when a geometric color plan cannot be created or validated."""


def _estimate_geometry_paint_cost(
    plan: dict[str, Any],
    *,
    stroke_overhead_px_equivalent: float = 6.67,
    paint_budget_px_equivalent: float = 25_650.0,
) -> dict[str, Any]:
    """Estimate cost for arbitrary polylines; the legacy model only accepts two-point runs."""
    budget = float(paint_budget_px_equivalent)
    overhead = float(stroke_overhead_px_equivalent)
    if not math.isfinite(budget) or budget <= 0 or not math.isfinite(overhead) or overhead < 0:
        raise GeometryColorPlanError("Параметры модели расхода краски недопустимы.")
    by_color: dict[int, dict[str, Any]] = {}
    total_length = 0.0
    total_single_pixel_count = 0
    for stroke in plan.get("strokes", []):
        points = [(float(p["x"]), float(p["y"])) for p in stroke["points"]]
        length = _path_length(points, bool(stroke.get("closed")))
        is_single_pixel = len(points) == 2 and _point_distance(points[0], points[1]) <= _EPSILON
        total_length += length
        total_single_pixel_count += int(is_single_pixel)
        color_index = int(stroke["color"]["palette_index"])
        entry = by_color.setdefault(color_index, {
            "palette_index": color_index, "hex": stroke["color"]["hex"],
            "name": stroke["color"]["name"], "stroke_count": 0,
            "drawing_length_px": 0.0, "single_pixel_stroke_count": 0,
        })
        entry["stroke_count"] += 1
        entry["drawing_length_px"] += length
        entry["single_pixel_stroke_count"] += int(is_single_pixel)
    stroke_count = len(plan.get("strokes", []))
    single_pixel_extra_path = float(total_single_pixel_count)
    total_cost = total_length + single_pixel_extra_path + stroke_count * overhead
    per_color = []
    for entry in by_color.values():
        extra_path = float(entry["single_pixel_stroke_count"])
        cost = entry["drawing_length_px"] + extra_path + entry["stroke_count"] * overhead
        per_color.append({
            **entry,
            "drawing_length_px": round(entry["drawing_length_px"], 3),
            "single_pixel_extra_path_px": round(extra_path, 3),
            "estimated_total_ink_px_equivalent": round(cost, 3),
            "estimated_usage_percent": round(cost / budget * 100, 3),
            "risk_level": "over_budget" if cost >= budget else "high" if cost >= budget * 0.9 else "normal",
        })
    highest = max(per_color, key=lambda entry: entry["estimated_usage_percent"], default=None)
    usage = total_cost / budget * 100.0
    return {
        "model_id": "empirical-ink-cost-v1-polyline",
        "stroke_count": stroke_count,
        "drawing_length_px": round(total_length, 3),
        "single_pixel_stroke_count": total_single_pixel_count,
        "single_pixel_extra_path_px": round(single_pixel_extra_path, 3),
        "effective_drawing_length_px": round(total_length + single_pixel_extra_path, 3),
        "stroke_overhead_px_equivalent": overhead,
        "paint_budget_px_equivalent": budget,
        "estimated_total_ink_px_equivalent": round(total_cost, 3),
        "estimated_usage_percent": round(usage, 3),
        "risk_level": "over_budget" if usage >= 100 else "very_high" if usage >= 90 else "high" if usage >= 80 else "normal",
        "risk_label": "Превышение бюджета" if usage >= 100 else "Высокий прогноз расхода" if usage >= 80 else "Оценка в пределах бюджета",
        "per_color_estimates": per_color,
        "highest_use_color": highest,
        "resource_scope_note": "Экспериментальная оценка: длина полилиний + число штрихов × накладные расходы. Не является счётчиком игры.",
    }


def _validate_index_map(index_map: Any, palette_size: int) -> np.ndarray:
    try:
        indexes = np.asarray(index_map)
    except (TypeError, ValueError) as exc:
        raise GeometryColorPlanError("Не удалось прочитать карту цветов.") from exc
    if indexes.ndim != 2 or not indexes.size:
        raise GeometryColorPlanError("Карта цветов должна быть непустой двумерной матрицей.")
    if indexes.dtype.kind not in "iu":
        raise GeometryColorPlanError("Индексы карты цветов должны быть целыми числами.")
    if indexes.size > MAX_IMAGE_PIXELS:
        raise GeometryColorPlanError(f"Изображение превышает лимит {MAX_IMAGE_PIXELS:,} пикселей.")
    if int(indexes.min()) < -1 or int(indexes.max()) >= palette_size:
        raise GeometryColorPlanError("Карта содержит индекс за пределами палитры.")
    if not np.any(indexes >= 0):
        raise GeometryColorPlanError("В изображении нет видимых пикселей.")
    return indexes.astype(np.int32, copy=False)


def _point_distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.hypot(second[0] - first[0], second[1] - first[1])


def _path_length(points: list[tuple[float, float]], closed: bool = False) -> float:
    total = sum(_point_distance(a, b) for a, b in zip(points, points[1:]))
    if closed and len(points) >= 3 and _point_distance(points[0], points[-1]) > _EPSILON:
        total += _point_distance(points[-1], points[0])
    return total


def _stroke_endpoints(stroke: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float]]:
    points = stroke["points"]
    first = (float(points[0]["x"]), float(points[0]["y"]))
    last = (float(points[-1]["x"]), float(points[-1]["y"]))
    if stroke.get("closed") and len(points) >= 3:
        return first, first
    return first, last


def _stroke_record(
    points: list[tuple[float, float]],
    palette_color: dict[str, Any],
    *,
    closed: bool,
    index: int,
    path_type: str,
    source_component_area: int | None = None,
) -> dict[str, Any]:
    if len(points) == 1:
        points = [points[0], points[0]]
    return {
        "name": f"{path_type}-{palette_color['index']}-{index}",
        "points": [{"x": float(x), "y": float(y)} for x, y in points],
        "closed": bool(closed),
        "color": {
            "palette_index": int(palette_color["index"]),
            "id": str(palette_color["id"]),
            "name": str(palette_color["name"]),
            "hex": str(palette_color["hex"]),
            "rgb": list(palette_color["rgb"]),
        },
        "metadata": {
            "path_type": path_type,
            "source_component_area": source_component_area,
        },
    }


def _orient_and_order_strokes(
    strokes: list[dict[str, Any]],
    color_grouping: bool,
) -> list[dict[str, Any]]:
    """Group by color, then use nearest-neighbor routing within each color."""
    if len(strokes) < 2:
        return strokes
    remaining_by_color: dict[int, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for original_index, stroke in enumerate(strokes):
        remaining_by_color[int(stroke["color"]["palette_index"])].append((original_index, stroke))
    first_color = int(strokes[0]["color"]["palette_index"])
    color_order: list[int] = [first_color]
    remaining_colors = set(remaining_by_color) - {first_color}
    current = _stroke_endpoints(strokes[0])[1]

    def prepare(stroke: dict[str, Any], position: tuple[float, float]) -> tuple[float, int, dict[str, Any]]:
        candidate = dict(stroke)
        candidate["points"] = [dict(p) for p in stroke["points"]]
        raw_points = [(float(p["x"]), float(p["y"])) for p in candidate["points"]]
        if candidate.get("closed") and len(raw_points) >= 3:
            start_idx = min(range(len(raw_points)), key=lambda i: (_point_distance(position, raw_points[i]), i))
            raw_points = raw_points[start_idx:] + raw_points[:start_idx]
            candidate["points"] = [{"x": x, "y": y} for x, y in raw_points]
        elif _point_distance(position, raw_points[-1]) < _point_distance(position, raw_points[0]):
            raw_points.reverse()
            candidate["points"] = [{"x": x, "y": y} for x, y in raw_points]
        return _point_distance(position, raw_points[0]), 0, candidate

    # Keep the initial color group as an anchor, then choose the nearest reachable
    # color group. Each color appears in exactly one consecutive batch.
    ordered: list[dict[str, Any]] = []
    for color_index in color_order:
        color_strokes = remaining_by_color.pop(color_index, [])
        if not color_strokes:
            continue
        if not ordered:
            anchor_original, anchor = color_strokes.pop(0)
            ordered.append(anchor)
            current = _stroke_endpoints(anchor)[1]
        else:
            first_candidates = [prepare(stroke, current) for _idx, stroke in color_strokes]
            if first_candidates:
                choice = min(range(len(first_candidates)), key=lambda i: (first_candidates[i][0], color_strokes[i][0]))
                _distance, _unused, chosen = first_candidates[choice]
                color_strokes.pop(choice)
                ordered.append(chosen)
                current = _stroke_endpoints(chosen)[1]

        while color_strokes:
            candidates = []
            for position, (original_index, stroke) in enumerate(color_strokes):
                distance, _unused, candidate = prepare(stroke, current)
                candidates.append((distance, original_index, position, candidate))
            _distance, _original, position, selected = min(candidates, key=lambda item: (item[0], item[1]))
            color_strokes.pop(position)
            ordered.append(selected)
            current = _stroke_endpoints(selected)[1]

        if not color_grouping:
            # Non-grouped routing is handled by restoring original order in the caller.
            pass

        if remaining_by_color:
            color_candidates = []
            for next_color, records in remaining_by_color.items():
                distances = []
                for original_index, stroke in records:
                    entry, _unused, _candidate = prepare(stroke, current)
                    distances.append((entry, original_index))
                color_candidates.append((min(distances), next_color))
            if color_candidates:
                (_distance, _original), next_color = min(color_candidates, key=lambda item: (item[0], item[1]))
                color_order.append(next_color)
    if not color_grouping:
        return strokes
    # The nearest-color selection above adds each color to color_order while iterating.
    # The loop's appended batches are the final ordering; every color switch is minimized.
    return ordered


def _summarize_plan(
    strokes: list[dict[str, Any]],
    palette: list[dict[str, Any]],
    width: int,
    height: int,
    *,
    visible_pixel_count: int,
    transparent_pixel_count: int,
    generation: dict[str, Any],
    source_visible_pixel_count: int | None = None,
    pixel_counts_by_color: dict[int, int] | None = None,
    name: str,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not strokes:
        raise GeometryColorPlanError("После геометрической обработки не осталось штрихов.")
    if len(strokes) > MAX_GEOMETRY_STROKES:
        raise GeometryColorPlanError(f"План превышает лимит {MAX_GEOMETRY_STROKES:,} штрихов.")

    lengths: list[float] = []
    single_pixel_count = 0
    per_color: dict[int, dict[str, Any]] = {}
    used_indexes: set[int] = set()
    pen_up = 0.0
    switches = 0
    previous_end: tuple[float, float] | None = None
    previous_color: int | None = None
    for stroke in strokes:
        points = [(float(p["x"]), float(p["y"])) for p in stroke["points"]]
        length = _path_length(points, bool(stroke.get("closed")))
        lengths.append(length)
        if len(points) == 2 and _point_distance(points[0], points[1]) <= _EPSILON:
            single_pixel_count += 1
        color_index = int(stroke["color"]["palette_index"])
        used_indexes.add(color_index)
        color = per_color.setdefault(color_index, {
            "palette_index": color_index,
            "id": str(stroke["color"]["id"]),
            "name": str(stroke["color"]["name"]),
            "hex": str(stroke["color"]["hex"]),
            "pixel_count": int((pixel_counts_by_color or {}).get(color_index, 0)),
            "stroke_count": 0,
            "percentage_visible": 0.0,
        })
        color["stroke_count"] += 1
        if previous_end is not None:
            pen_up += _point_distance(previous_end, points[0])
        if previous_color is not None and previous_color != color_index:
            switches += 1
        previous_color = color_index
        previous_end = _stroke_endpoints(stroke)[1]

    visible = max(0, int(visible_pixel_count))
    for item in per_color.values():
        item["percentage_visible"] = round(100.0 * item["pixel_count"] / visible, 4) if visible else 0.0
    plan = {
        "schema_version": GEOMETRY_PLAN_SCHEMA_VERSION,
        "plan_type": GEOMETRY_PLAN_TYPE,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "canvas": {"width": int(width), "height": int(height)},
        "source": source or {},
        "palette": palette,
        "generation": generation,
        "strokes": strokes,
        "summary": {
            "stroke_count": len(strokes),
            "point_count": sum(len(stroke["points"]) for stroke in strokes),
            "drawing_length_px": round(sum(lengths), 3),
            "pen_up_distance_px": round(pen_up, 3),
            "visible_pixel_count": visible,
            "retained_visible_pixel_count": visible,
            "source_visible_pixel_count": max(
                0, int(visible if source_visible_pixel_count is None else source_visible_pixel_count)
            ),
            "geometry_coverage_metrics_available": generation.get("coverage_metrics_available", True),
            "geometry_coverage_note": (
                "Метрики покрытия пикселями исходной карты недоступны для плана, собранного "
                "из обрезанных векторных траекторий."
                if generation.get("coverage_metrics_available") is False
                else
                "Счётчик относится к пикселям исходных цветовых слоёв, сохранённым после фильтрации "
                "компонентов; это не оценка площади, фактически закрашенной векторными штрихами."
            ),
            "transparent_pixel_count": max(0, int(transparent_pixel_count)),
            "single_pixel_stroke_count": single_pixel_count,
            "color_switch_count": switches,
            "color_selection_count_estimate": (1 + switches) if strokes else 0,
            "used_palette_color_count": len(used_indexes),
            "unused_palette_color_count": len(palette) - len(used_indexes),
            "used_colors": [per_color[index] for index in sorted(per_color)],
        },
    }
    plan["summary"]["paint_cost_estimate"] = _estimate_geometry_paint_cost(plan)
    return plan


def build_geometry_color_plan(
    index_map: Any,
    palette: Any,
    *,
    mode: str = "skeleton",
    simplify_tolerance_px: float = 0.8,
    min_component_area: int = 1,
    color_grouping: bool = True,
    max_strokes: int = MAX_GEOMETRY_STROKES,
    canvas_size: tuple[int, int] | None = None,
    source_tile: dict[str, int] | None = None,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Create colored vector paths from per-color binary layers.

    Modes:
      scanline: preserve colored raster coverage as horizontal runs.
      contour: trace the boundaries of each binary color layer.
      skeleton: thin each color layer to a one-pixel centerline and trace paths.
    """
    normalized_palette = normalize_palette(palette.get("colors", []) if isinstance(palette, dict) else palette)
    indexes = _validate_index_map(index_map, len(normalized_palette))
    if mode not in {"scanline", "contour", "skeleton"}:
        raise GeometryColorPlanError("Режим должен быть scanline, contour или skeleton.")
    if isinstance(simplify_tolerance_px, bool) or not isinstance(simplify_tolerance_px, (int, float)):
        raise GeometryColorPlanError("Допуск RDP должен быть числом.")
    tolerance = float(simplify_tolerance_px)
    if not math.isfinite(tolerance) or tolerance < 0:
        raise GeometryColorPlanError("Допуск RDP должен быть конечным неотрицательным числом.")
    if isinstance(min_component_area, bool) or not isinstance(min_component_area, int) or min_component_area < 1:
        raise GeometryColorPlanError("Минимальная площадь компонента должна быть целым числом от 1.")
    if isinstance(max_strokes, bool) or not isinstance(max_strokes, int) or max_strokes < 1:
        raise GeometryColorPlanError("Лимит штрихов должен быть положительным целым числом.")

    source_height, source_width = indexes.shape
    if canvas_size is None:
        width, height = source_width, source_height
    else:
        try:
            width, height = int(canvas_size[0]), int(canvas_size[1])
        except (TypeError, ValueError, IndexError) as exc:
            raise GeometryColorPlanError("Размер целевого холста задан неверно.") from exc
        if width < source_width or height < source_height:
            raise GeometryColorPlanError("Целевой холст меньше исходной карты цветов.")

    visible_count = int(np.count_nonzero(indexes >= 0))
    pixel_counts_by_color = {
        int(color["index"]): int(np.count_nonzero(indexes == int(color["index"])))
        for color in normalized_palette
    }
    retained_visible_count = visible_count
    strokes: list[dict[str, Any]] = []
    removed_component_pixels = 0
    if mode == "scanline":
        for y in range(source_height):
            row = indexes[y]
            x = 0
            while x < source_width:
                color_index = int(row[x])
                if color_index < 0:
                    x += 1
                    continue
                end = x + 1
                while end < source_width and int(row[end]) == color_index:
                    end += 1
                color = normalized_palette[color_index]
                strokes.append(_stroke_record(
                    [(float(x), float(y)), (float(end - 1), float(y))],
                    color, closed=False, index=len(strokes) + 1, path_type="scanline",
                ))
                x = end
                if len(strokes) > min(max_strokes, MAX_GEOMETRY_STROKES):
                    raise GeometryColorPlanError("Превышен лимит штрихов.")
    else:
        for color in normalized_palette:
            color_index = int(color["index"])
            raw_mask = (indexes == color_index).astype(np.uint8)
            if not bool(np.any(raw_mask)):
                continue
            mask, removed = _connected_components(raw_mask, min_component_area)
            removed_component_pixels += removed
            pixel_counts_by_color[color_index] = int(np.count_nonzero(mask))
            if not bool(np.any(mask)):
                continue

            if mode == "contour":
                contours, _hierarchy = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
                contours.sort(key=lambda c: (-abs(float(cv2.contourArea(c))), int(c[0][0][1]), int(c[0][0][0])))
                for contour_index, contour in enumerate(contours, start=1):
                    raw_points = [(float(point[0][0]), float(point[0][1])) for point in contour]
                    if not raw_points:
                        continue
                    if len(raw_points) == 1:
                        strokes.append(_stroke_record(
                            raw_points, color, closed=False, index=contour_index,
                            path_type="contour-point", source_component_area=1,
                        ))
                        continue
                    simplified = _simplify_path(
                        raw_points, closed=True, tolerance_px=tolerance, safe_mask=mask
                    )
                    if len(simplified) < 3:
                        simplified = raw_points
                    strokes.append(_stroke_record(
                        simplified, color, closed=True, index=contour_index,
                        path_type="contour", source_component_area=int(len(contour)),
                    ))
            else:
                skeleton = _zhang_suen_thinning(mask)
                paths = _skeleton_paths(skeleton)
                paths.sort(key=lambda item: (-_path_length(item[0], item[1]), item[0][0][1], item[0][0][0]))
                for path_index, (raw_points, closed) in enumerate(paths, start=1):
                    if not raw_points:
                        continue
                    simplified = _simplify_path(
                        raw_points, closed=closed, tolerance_px=tolerance, safe_mask=mask
                    )
                    if len(simplified) < (3 if closed else 2):
                        simplified = raw_points
                    strokes.append(_stroke_record(
                        simplified, color, closed=closed, index=path_index,
                        path_type="skeleton",
                    ))
            if len(strokes) > min(max_strokes, MAX_GEOMETRY_STROKES):
                raise GeometryColorPlanError("Превышен лимит штрихов.")

    if color_grouping:
        strokes = _orient_and_order_strokes(strokes, True)
    generation = {
        "method": "geometry_color_layers",
        "mode": mode,
        "binarization": "one_binary_mask_per_palette_index; -1 is transparent",
        "skeletonization": "zhang_suen" if mode == "skeleton" else "not_applied",
        "simplification": "Ramer-Douglas-Peucker via cv2.approxPolyDP",
        "simplify_tolerance_px": tolerance,
        "min_component_area": min_component_area,
        "color_grouping": bool(color_grouping),
        "row_order": "not_preserved_after_geometric_routing" if color_grouping else "source_layer_order",
        "source_size": {"width": source_width, "height": source_height},
        "removed_component_pixel_count": removed_component_pixels,
        "tile": dict(source_tile) if source_tile else None,
    }
    source = {
        "source_name": source_name or "Карта цветов",
        "source_size": {"width": source_width, "height": source_height},
        "source_tile": dict(source_tile) if source_tile else None,
    }
    retained_visible_count = sum(pixel_counts_by_color.values())
    plan = _summarize_plan(
        strokes, normalized_palette, width, height,
        visible_pixel_count=retained_visible_count,
        transparent_pixel_count=int(indexes.size - visible_count),
        generation=generation, name=f"Геометрический цветной план ({mode})", source=source,
        source_visible_pixel_count=visible_count,
        pixel_counts_by_color=pixel_counts_by_color,
    )
    return validate_geometry_color_plan(plan)


def validate_geometry_color_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("plan_type") != GEOMETRY_PLAN_TYPE:
        raise GeometryColorPlanError("Это не геометрический цветной план AutoDraw.")
    if plan.get("schema_version") != GEOMETRY_PLAN_SCHEMA_VERSION:
        raise GeometryColorPlanError("Неподдерживаемая версия геометрического цветного плана.")
    canvas = plan.get("canvas")
    if not isinstance(canvas, dict):
        raise GeometryColorPlanError("В плане отсутствует объект canvas.")
    try:
        raw_width, raw_height = canvas["width"], canvas["height"]
        width, height = int(raw_width), int(raw_height)
    except (KeyError, TypeError, ValueError) as exc:
        raise GeometryColorPlanError("Размеры холста должны быть целыми числами.") from exc
    if isinstance(raw_width, bool) or isinstance(raw_height, bool) or width != raw_width or height != raw_height:
        raise GeometryColorPlanError("Размеры холста должны быть целыми числами без округления.")
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise GeometryColorPlanError("Размер холста недопустим.")
    palette_raw = plan.get("palette")
    palette = normalize_palette(palette_raw or [])
    strokes = plan.get("strokes")
    if not isinstance(strokes, list) or not strokes:
        raise GeometryColorPlanError("В плане отсутствуют цветные штрихи.")
    if len(strokes) > MAX_GEOMETRY_STROKES:
        raise GeometryColorPlanError("План превышает допустимое число штрихов.")

    for index, stroke in enumerate(strokes, start=1):
        if not isinstance(stroke, dict):
            raise GeometryColorPlanError(f"Штрих №{index} должен быть объектом.")
        points = stroke.get("points")
        if not isinstance(points, list) or len(points) < 2:
            raise GeometryColorPlanError(f"Штрих №{index} должен содержать минимум две точки.")
        parsed: list[tuple[float, float]] = []
        for point in points:
            try:
                x, y = float(point["x"]), float(point["y"])
            except (KeyError, TypeError, ValueError) as exc:
                raise GeometryColorPlanError(f"Координаты штриха №{index} повреждены.") from exc
            if not math.isfinite(x) or not math.isfinite(y) or not (0 <= x < width and 0 <= y < height):
                raise GeometryColorPlanError(f"Штрих №{index} выходит за границы холста.")
            parsed.append((x, y))
        if not isinstance(stroke.get("closed", False), bool):
            raise GeometryColorPlanError(f"Признак замкнутости штриха №{index} должен быть логическим.")
        color = stroke.get("color")
        if not isinstance(color, dict):
            raise GeometryColorPlanError(f"У штриха №{index} отсутствует цвет.")
        try:
            color_index = int(color["palette_index"])
        except (KeyError, TypeError, ValueError) as exc:
            raise GeometryColorPlanError(f"У штриха №{index} неверный индекс палитры.") from exc
        if not 0 <= color_index < len(palette):
            raise GeometryColorPlanError(f"Индекс палитры штриха №{index} выходит за границы.")
        if str(color.get("hex", "")).upper() != palette[color_index]["hex"]:
            raise GeometryColorPlanError(f"Цвет штриха №{index} не соответствует палитре.")
        if color.get("rgb") != palette[color_index]["rgb"]:
            raise GeometryColorPlanError(f"RGB штриха №{index} не соответствует палитре.")
        metadata = stroke.get("metadata", {})
        if not isinstance(metadata, dict):
            raise GeometryColorPlanError(f"Метаданные штриха №{index} должны быть объектом.")

    summary = plan.get("summary")
    if not isinstance(summary, dict):
        raise GeometryColorPlanError("В плане отсутствует summary.")
    if summary.get("stroke_count") != len(strokes):
        raise GeometryColorPlanError("Счётчик штрихов не совпадает с содержимым плана.")
    return plan


def render_geometry_color_preview(plan: Any, max_dimension: int = 1600) -> Image.Image:
    data = validate_geometry_color_plan(plan)
    width, height = int(data["canvas"]["width"]), int(data["canvas"]["height"])
    scale = min(1.0, max_dimension / max(width, height))
    out_width, out_height = max(1, round(width * scale)), max(1, round(height * scale))
    image = Image.new("RGBA", (out_width, out_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    for stroke in data["strokes"]:
        points = [
            (round(float(point["x"]) * scale), round(float(point["y"]) * scale))
            for point in stroke["points"]
        ]
        color = tuple(int(channel) for channel in stroke["color"]["rgb"]) + (255,)
        if len(points) == 2 and points[0] == points[1]:
            x, y = points[0]
            draw.point((x, y), fill=color)
            continue
        if len(points) >= 2:
            if stroke.get("closed") and points[0] != points[-1]:
                points.append(points[0])
            draw.line(points, fill=color, width=max(1, round(scale)), joint="curve")
    return image


def save_geometry_color_plan(path: str | Path, plan: Any) -> Path:
    validated = validate_geometry_color_plan(plan)
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(validated, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return output


def load_geometry_color_plan(path: str | Path) -> dict[str, Any]:
    plan_path = Path(path).expanduser().resolve()
    try:
        with plan_path.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GeometryColorPlanError(f"Не удалось прочитать план: {exc}") from exc
    return validate_geometry_color_plan(document)


def _rescale_map_centered(indexes: np.ndarray, scale: float) -> np.ndarray:
    if scale >= 1.0:
        return indexes.copy()
    height, width = indexes.shape
    new_width = max(1, round(width * scale))
    new_height = max(1, round(height * scale))
    resized = cv2.resize(indexes, (new_width, new_height), interpolation=cv2.INTER_NEAREST)
    output = np.full(indexes.shape, -1, dtype=np.int32)
    x0, y0 = (width - new_width) // 2, (height - new_height) // 2
    output[y0:y0 + new_height, x0:x0 + new_width] = resized
    return output


def optimize_geometry_plan_to_budget(
    index_map: Any,
    palette: Any,
    *,
    mode: str,
    paint_budget_px_equivalent: float,
    target_usage_percent: float = 75.0,
    stroke_overhead_px_equivalent: float = 6.67,
    simplify_tolerance_px: float = 0.8,
    source_name: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Search quality-preserving candidates until the estimated ink budget fits.

    The optimizer prefers the largest image scale, then the least component loss and
    the smallest RDP tolerance. If no single-board candidate fits, the best low-cost
    candidate is returned so the caller can offer a multi-board split.
    """
    normalized = normalize_palette(palette.get("colors", []) if isinstance(palette, dict) else palette)
    original = _validate_index_map(index_map, len(normalized))
    try:
        budget = float(paint_budget_px_equivalent)
        target = float(target_usage_percent)
        overhead = float(stroke_overhead_px_equivalent)
    except (TypeError, ValueError) as exc:
        raise GeometryColorPlanError("Параметры бюджета должны быть числами.") from exc
    if not math.isfinite(budget) or budget <= 0:
        raise GeometryColorPlanError("Бюджет краски должен быть больше нуля.")
    if not math.isfinite(target) or not 10 <= target <= 95:
        raise GeometryColorPlanError("Целевой расход должен быть от 10 до 95%.")
    if not math.isfinite(overhead) or overhead < 0:
        raise GeometryColorPlanError("Расход на один штрих должен быть неотрицательным.")
    target_cost = budget * target / 100.0
    before = build_geometry_color_plan(
        original, normalized, mode=mode, simplify_tolerance_px=0.0,
        min_component_area=1, source_name=source_name,
    )
    before_estimate = _estimate_geometry_paint_cost(
        before,
        stroke_overhead_px_equivalent=overhead,
        paint_budget_px_equivalent=budget,
    )
    scales = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3)
    tolerances = tuple(sorted(set((0.0, float(simplify_tolerance_px), 1.0, 2.0, 3.5, 5.0)))
                        )
    component_thresholds = (1, 2, 4, 8, 16)
    best: dict[str, Any] | None = None
    best_report: dict[str, Any] | None = None
    target_fits_at_scale = False
    source_visible = int(np.count_nonzero(original >= 0))

    for scale in scales:
        scaled_map = _rescale_map_centered(original, scale)
        candidates: list[tuple[tuple[float, float, int], dict[str, Any], dict[str, Any]]] = []
        for min_area in component_thresholds:
            for tolerance in tolerances:
                try:
                    candidate = build_geometry_color_plan(
                        scaled_map, normalized, mode=mode,
                        simplify_tolerance_px=tolerance,
                        min_component_area=min_area,
                        source_name=source_name,
                    )
                    estimate = _estimate_geometry_paint_cost(
                        candidate,
                        stroke_overhead_px_equivalent=overhead,
                        paint_budget_px_equivalent=budget,
                    )
                except (GeometryColorPlanError, ValueError, TypeError, MemoryError):
                    continue
                cost = float(estimate["estimated_total_ink_px_equivalent"])
                visible = int(candidate["summary"]["visible_pixel_count"])
                quality = (float(source_visible - visible), float(tolerance), min_area)
                report = {
                    "enabled": True,
                    "mode": mode,
                    "scale": scale,
                    "min_component_area": min_area,
                    "simplify_tolerance_px": tolerance,
                    "source_visible_pixel_count": source_visible,
                    "retained_visible_pixel_count": visible,
                    "estimated_ink_before_px_equivalent": before_estimate["estimated_total_ink_px_equivalent"],
                    "estimated_ink_after_px_equivalent": cost,
                    "target_cost_px_equivalent": round(target_cost, 3),
                    "paint_budget_px_equivalent": budget,
                    "target_usage_percent": target,
                    "fits_budget": cost <= target_cost,
                    "needs_multi_board_split": cost > target_cost,
                }
                if best is None or cost < float(best_report["estimated_ink_after_px_equivalent"]):
                    best, best_report = candidate, report
                if cost <= target_cost:
                    candidates.append((quality, candidate, report))
        if candidates:
            _quality, best_at_scale, report_at_scale = min(candidates, key=lambda item: item[0])
            best, best_report = best_at_scale, report_at_scale
            target_fits_at_scale = True
            break

    if best is None or best_report is None:
        raise GeometryColorPlanError("Не удалось построить ни одного допустимого геометрического плана.")
    best["generation"]["budget_optimization"] = dict(best_report)
    best["summary"]["paint_cost_estimate"] = _estimate_geometry_paint_cost(
        best,
        stroke_overhead_px_equivalent=overhead,
        paint_budget_px_equivalent=budget,
    )
    best_report["fits_budget"] = bool(
        best_report["estimated_ink_after_px_equivalent"] <= target_cost
    )
    best_report["needs_multi_board_split"] = not best_report["fits_budget"]
    best_report["target_fits_at_scale"] = target_fits_at_scale
    return validate_geometry_color_plan(best), best_report


def _clip_segment(
    first: tuple[float, float],
    last: tuple[float, float],
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Liang-Barsky segment clipping."""
    x0, y0 = first
    x1, y1 = last
    dx, dy = x1 - x0, y1 - y0
    p = (-dx, dx, -dy, dy)
    q = (x0 - xmin, xmax - x0, y0 - ymin, ymax - y0)
    u0, u1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if abs(pi) < _EPSILON:
            if qi < 0:
                return None
            continue
        t = qi / pi
        if pi < 0:
            u0 = max(u0, t)
        else:
            u1 = min(u1, t)
        if u0 > u1:
            return None
    return (x0 + u0 * dx, y0 + u0 * dy), (x0 + u1 * dx, y0 + u1 * dy)


def _clip_stroke_to_tile(
    stroke: dict[str, Any],
    tile: tuple[int, int, int, int],
) -> list[dict[str, Any]]:
    x0, y0, x1, y1 = tile
    xmin, ymin, xmax, ymax = float(x0), float(y0), float(x1 - 1), float(y1 - 1)
    points = [(float(p["x"]), float(p["y"])) for p in stroke["points"]]
    closed = bool(stroke.get("closed"))
    segments = list(zip(points, points[1:]))
    if closed and len(points) >= 3 and _point_distance(points[-1], points[0]) > _EPSILON:
        segments.append((points[-1], points[0]))
    if not segments:
        return []

    pieces: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for first, last in segments:
        clipped = _clip_segment(first, last, xmin, ymin, xmax, ymax)
        if clipped is None:
            if len(current) >= 2:
                pieces.append(current)
            current = []
            continue
        start, end = clipped
        continues = bool(current) and _point_distance(current[-1], start) <= 1e-5
        if not continues:
            if len(current) >= 2:
                pieces.append(current)
            current = [start, end]
        else:
            if _point_distance(current[-1], end) > _EPSILON:
                current.append(end)
        # If a segment was clipped at either end, the path is broken at this tile edge.
        reached_end = _point_distance(end, last) <= 1e-5
        reached_start = _point_distance(start, first) <= 1e-5
        if not (reached_end and reached_start):
            if len(current) >= 2:
                pieces.append(current)
            current = []
    if len(current) >= 2:
        pieces.append(current)

    output: list[dict[str, Any]] = []
    for piece in pieces:
        local = [(max(0.0, x - x0), max(0.0, y - y0)) for x, y in piece]
        clean: list[tuple[float, float]] = []
        for point in local:
            if not clean or _point_distance(clean[-1], point) > _EPSILON:
                clean.append(point)
        if len(clean) == 1:
            clean.append(clean[0])
        if len(clean) < 2:
            continue
        copied = {
            "name": str(stroke.get("name", "stroke")) + f"_tile_{x0}_{y0}_{len(output) + 1}",
            "points": [{"x": x, "y": y} for x, y in clean],
            "closed": False,
            "color": dict(stroke["color"]),
            "metadata": {**dict(stroke.get("metadata", {})), "clipped_from": stroke.get("name", "")},
        }
        output.append(copied)
    return output


def split_geometry_plan_to_boards(
    plan: Any,
    *,
    paint_budget_px_equivalent: float,
    target_usage_percent: float = 75.0,
    stroke_overhead_px_equivalent: float = 6.67,
    min_tile_size: int = 24,
    max_boards: int = 64,
    board_width: int = 660,
    board_height: int = 340,
) -> dict[str, Any]:
    """Partition an already-optimized vector plan into spatial tile plans.

    Paths are clipped to tile rectangles, not re-contoured from each crop. Therefore
    artificial color borders are not introduced along tile edges. Tile plans preserve
    the original full canvas size expected by the executor; their path coordinates are
    local to each tile. The manifest records source rectangles for later stitching.
    """
    data = validate_geometry_color_plan(plan)
    budget = float(paint_budget_px_equivalent)
    target = float(target_usage_percent)
    overhead = float(stroke_overhead_px_equivalent)
    if not math.isfinite(budget) or budget <= 0:
        raise GeometryColorPlanError("Бюджет краски должен быть больше нуля.")
    if not 10 <= target <= 95 or not math.isfinite(target):
        raise GeometryColorPlanError("Целевой расход должен быть от 10 до 95%.")
    if min_tile_size < 2 or max_boards < 1:
        raise GeometryColorPlanError("Недопустимые параметры разбиения на доски.")
    if isinstance(board_width, bool) or isinstance(board_height, bool) or board_width < 2 or board_height < 2:
        raise GeometryColorPlanError("Размеры физической доски должны быть целыми числами от 2.")
    width, height = int(data["canvas"]["width"]), int(data["canvas"]["height"])
    target_cost = budget * target / 100.0
    pending = [(0, 0, width, height)]
    accepted: list[tuple[tuple[int, int, int, int], list[dict[str, Any]], dict[str, Any]]] = []

    def tile_strokes(tile: tuple[int, int, int, int]) -> list[dict[str, Any]]:
        clipped: list[dict[str, Any]] = []
        for stroke in data["strokes"]:
            clipped.extend(_clip_stroke_to_tile(stroke, tile))
        # The local tile plan uses the same physical board dimensions, so coordinates
        # stay near the origin and are accepted by the current stage-20 area validator.
        return _orient_and_order_strokes(clipped, True)

    while pending:
        if len(pending) + len(accepted) > max_boards:
            raise GeometryColorPlanError(
                f"Разбиение потребовало бы больше {max_boards} досок. Увеличьте допустимый бюджет или упростите изображение."
            )
        tile = pending.pop(0)
        x0, y0, x1, y1 = tile
        strokes = tile_strokes(tile)
        if not strokes:
            continue
        draft = _summarize_plan(
            strokes, data["palette"], board_width, board_height,
            visible_pixel_count=0, transparent_pixel_count=board_width * board_height,
            generation={
                **data["generation"],
                "tile": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0},
                "coverage_metrics_available": False,
            },
            name=f"{data.get('name', 'Геометрический план')} — фрагмент",
            source={**data.get("source", {}), "source_tile": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}},
        )
        estimate = _estimate_geometry_paint_cost(
            draft, stroke_overhead_px_equivalent=overhead, paint_budget_px_equivalent=budget
        )
        cost = float(estimate["estimated_total_ink_px_equivalent"])
        tile_width, tile_height = x1 - x0, y1 - y0
        if tile_width > board_width or tile_height > board_height:
            if tile_width / max(1, board_width) >= tile_height / max(1, board_height) and tile_width > board_width:
                middle = x0 + tile_width // 2
                pending[0:0] = [(x0, y0, middle, y1), (middle, y0, x1, y1)]
            else:
                middle = y0 + tile_height // 2
                pending[0:0] = [(x0, y0, x1, middle), (x0, middle, x1, y1)]
            continue
        if cost <= target_cost or (tile_width <= min_tile_size and tile_height <= min_tile_size):
            draft["summary"]["paint_cost_estimate"] = estimate
            accepted.append((tile, strokes, draft))
            continue

        if tile_width >= tile_height and tile_width > min_tile_size:
            middle = x0 + tile_width // 2
            pending[0:0] = [(x0, y0, middle, y1), (middle, y0, x1, y1)]
        elif tile_height > min_tile_size:
            middle = y0 + tile_height // 2
            pending[0:0] = [(x0, y0, x1, middle), (x0, middle, x1, y1)]
        else:
            draft["summary"]["paint_cost_estimate"] = estimate
            accepted.append((tile, strokes, draft))

    boards: list[dict[str, Any]] = []
    for index, (tile, _strokes, board_plan) in enumerate(accepted, start=1):
        x0, y0, x1, y1 = tile
        bounds = {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}
        board_plan["name"] = f"{data.get('name', 'План')} — доска {index}"
        board_plan["source"]["source_tile"] = bounds
        board_plan["generation"]["tile"] = bounds
        board_plan["generation"]["board_index"] = index
        board_plan["generation"]["board_count"] = len(accepted)
        board_plan["generation"]["paint_budget_optimization"] = {
            "target_cost_px_equivalent": round(target_cost, 3),
            "estimated_ink_after_px_equivalent": board_plan["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"],
            "fits_budget": board_plan["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"] <= target_cost,
        }
        boards.append(validate_geometry_color_plan(board_plan))
    return {
        "schema_version": 1,
        "plan_type": "autodraw_multi_board_manifest",
        "source_plan_type": GEOMETRY_PLAN_TYPE,
        "source_plan_name": str(data.get("name", "Геометрический план")),
        "canvas": {"width": width, "height": height},
        "board_size": {"width": board_width, "height": board_height},
        "target_budget_px_equivalent": budget,
        "target_usage_percent": target,
        "board_count": len(boards),
        "boards": [
            {
                "board_index": index,
                "tile": dict(board["source"]["source_tile"]),
                "stroke_count": board["summary"]["stroke_count"],
                "estimated_ink_px_equivalent": board["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"],
                "fits_budget": board["generation"]["paint_budget_optimization"]["fits_budget"],
                "plan": board,
            }
            for index, board in enumerate(boards, start=1)
        ],
        "notes": [
            "Это разбиение по пространственным областям, а не произвольное распределение штрихов между досками.",
            "Каждый дочерний план рисуется на холсте полного размера; траектории локализованы у начала холста.",
            "Для сборки общей картинки используйте метаданные tile и обрезайте соответствующие прямоугольники с готовых досок.",
            "Расход оценивается экспериментальной моделью; результат нужно сверять с реальным счётчиком игры.",
        ],
    }


def save_multi_board_manifest(path: str | Path, manifest: Any) -> Path:
    if not isinstance(manifest, dict) or manifest.get("plan_type") != "autodraw_multi_board_manifest":
        raise GeometryColorPlanError("Это не манифест многодосочного плана.")
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    output.write_text(payload, encoding="utf-8")
    return output
