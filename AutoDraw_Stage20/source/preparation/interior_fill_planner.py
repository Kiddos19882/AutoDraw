from __future__ import annotations

"""Conservative raster-mask planner for interior brush fill.

This module produces recommendations only. It does not integrate with the executor:
the in-game brush footprint and coordinate mapping still require manual validation.
"""

import math
from typing import Any

import numpy as np

from brush_footprint_geometry import footprint_pixel_bounds


class InteriorFillError(ValueError):
    """Raised when an interior-fill request cannot be planned safely."""


def _positive_scale(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise InteriorFillError(f"{field} должен быть положительным числом.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise InteriorFillError(f"{field} должен быть положительным числом.") from exc
    if not math.isfinite(result) or result <= 0:
        raise InteriorFillError(f"{field} должен быть конечным числом больше нуля.")
    return result


def _footprint_is_color(
    indexes: np.ndarray, color: int, x1: int, x2: int, y: int,
    brush: int, scale_x: float, scale_y: float,
) -> bool:
    height, width = indexes.shape
    bounds = footprint_pixel_bounds(x1, x2, y, brush, scale_x, scale_y, width, height)
    if bounds is None:
        return False
    left, right, top, bottom = bounds
    region = indexes[top:bottom + 1, left:right + 1]
    return bool(region.size and np.all(region == color))


def _mark_footprint(
    covered: np.ndarray, x1: int, x2: int, y: int, brush: int,
    scale_x: float, scale_y: float,
) -> None:
    height, width = covered.shape
    bounds = footprint_pixel_bounds(x1, x2, y, brush, scale_x, scale_y, width, height)
    if bounds is None:
        return
    left, right, top, bottom = bounds
    covered[top:bottom + 1, left:right + 1] = True



def _iter_fallback_runs(
    indexes: np.ndarray,
    covered: np.ndarray,
    y: int,
    max_merge_gap: int,
):
    """Yield same-color fallback runs, bridging only short covered gaps.

    Covered pixels are eligible as a bridge only when they belong to the same
    color. The caller still validates the complete brush footprint before use.
    """
    width = indexes.shape[1]
    x = 0
    while x < width:
        color = int(indexes[y, x])
        if color < 0 or covered[y, x]:
            x += 1
            continue

        start = x
        last_uncovered = x
        cursor = x + 1
        while cursor < width and int(indexes[y, cursor]) == color:
            if not covered[y, cursor]:
                last_uncovered = cursor
                cursor += 1
                continue

            gap_start = cursor
            while (
                cursor < width
                and int(indexes[y, cursor]) == color
                and covered[y, cursor]
            ):
                cursor += 1
            gap_length = cursor - gap_start
            if (
                cursor < width
                and int(indexes[y, cursor]) == color
                and not covered[y, cursor]
                and gap_length <= max_merge_gap
            ):
                continue
            break

        yield color, start, last_uncovered + 1
        x = last_uncovered + 1


def build_interior_fill_plan(
    index_map: Any,
    *,
    max_brush_value: int = 20,
    min_brush_value: int = 2,
    brush_scale_x: float = 1.0,
    brush_scale_y: float = 1.0,
    fallback_merge_gap_px: int = 3,
) -> dict[str, Any]:
    """Cover a color-index map with safe wide strokes and thin fallback runs.

    A stroke is accepted only when its conservative rectangular footprint lies
    entirely inside one palette index. Transparent pixels (-1) are never painted.
    Wide strokes are greedy recommendations; remaining visible pixels are covered
    with one-unit scanline runs. This is not a contour tracer and not executor-ready.
    """
    try:
        indexes = np.asarray(index_map)
    except (TypeError, ValueError) as exc:
        raise InteriorFillError("Не удалось прочитать карту цветов.") from exc
    if indexes.ndim != 2 or not indexes.size or indexes.dtype.kind not in "iu":
        raise InteriorFillError("Карта цветов должна быть непустым двумерным массивом целых индексов.")
    if int(indexes.min()) < -1:
        raise InteriorFillError("Индекс прозрачности не может быть меньше -1.")
    if isinstance(max_brush_value, bool) or not isinstance(max_brush_value, int):
        raise InteriorFillError("Максимальный размер кисти должен быть целым числом.")
    if isinstance(min_brush_value, bool) or not isinstance(min_brush_value, int):
        raise InteriorFillError("Минимальный размер кисти должен быть целым числом.")
    if not 2 <= min_brush_value <= max_brush_value <= 20:
        raise InteriorFillError("Диапазон широких кистей должен находиться внутри 2…20.")
    if isinstance(fallback_merge_gap_px, bool) or not isinstance(fallback_merge_gap_px, int):
        raise InteriorFillError("Допуск объединения fallback должен быть целым числом.")
    if not 0 <= fallback_merge_gap_px <= 20:
        raise InteriorFillError("Допуск объединения fallback должен находиться внутри 0…20 px.")
    scale_x = _positive_scale(brush_scale_x, "Масштаб кисти по X")
    scale_y = _positive_scale(brush_scale_y, "Масштаб кисти по Y")
    indexes = indexes.astype(np.int32, copy=False)
    height, width = indexes.shape
    covered = np.zeros((height, width), dtype=bool)
    strokes: list[dict[str, Any]] = []

    # Large brush values first; center rows are spaced by the estimated brush
    # height. Footprint validation, rather than the spacing heuristic, is the
    # actual safety gate.
    for color in sorted(int(v) for v in np.unique(indexes) if int(v) >= 0):
        color_mask = indexes == color
        for brush in range(max_brush_value, min_brush_value - 1, -1):
            row_step = max(1, int(math.floor(brush * scale_y)))
            for y in range(0, height, row_step):
                safe_centers = np.zeros(width, dtype=bool)
                # Only test pixels belonging to this color. This avoids scanning
                # every x coordinate for every palette index and brush size.
                for x in np.flatnonzero(color_mask[y]):
                    if _footprint_is_color(
                        indexes, color, int(x), int(x), y, brush, scale_x, scale_y
                    ):
                        safe_centers[x] = True
                x = 0
                while x < width:
                    if not safe_centers[x]:
                        x += 1
                        continue
                    end = x + 1
                    while end < width and safe_centers[end]:
                        end += 1
                    # A wider stroke is useful only if its entire footprint is
                    # safe and contributes at least one not-yet-covered pixel.
                    if _footprint_is_color(indexes, color, x, end - 1, y, brush, scale_x, scale_y):
                        bounds = footprint_pixel_bounds(
                            x, end - 1, y, brush, scale_x, scale_y, width, height
                        )
                        if bounds is None:
                            x = end
                            continue
                        left, right, top, bottom = bounds
                        if not bool(np.all(covered[top:bottom + 1, left:right + 1])):
                            strokes.append({
                                "color_index": color,
                                "points": [{"x": float(x), "y": float(y)}, {"x": float(end - 1), "y": float(y)}],
                                "brush_value": brush,
                                "role": "interior_fill",
                                "safe_for_color_map": True,
                                "safe_to_execute": False,
                            })
                            _mark_footprint(covered, x, end - 1, y, brush, scale_x, scale_y)
                    x = end

    # Fine pass closes all gaps and preserves thin features. Short runs may be
    # joined across a small span already covered by interior-fill, but only when
    # every bridged pixel has the same palette index. The full footprint is still
    # checked, so the merge cannot cross a different color or transparency.
    for y in range(height):
        for color, x, end in _iter_fallback_runs(
            indexes, covered, y, fallback_merge_gap_px
        ):
            if not _footprint_is_color(indexes, color, x, end - 1, y, 1, scale_x, scale_y):
                # At a sharp edge even the assumed thin footprint may be unsafe
                # under this scale model. Fail closed instead of inventing safety.
                raise InteriorFillError(
                    f"Тонкий fallback для цвета {color} в строке {y} не проходит проверку footprint."
                )
            strokes.append({
                "color_index": color,
                "points": [{"x": float(x), "y": float(y)}, {"x": float(end - 1), "y": float(y)}],
                "brush_value": 1,
                "role": "boundary_fallback",
                "safe_for_color_map": True,
                "safe_to_execute": False,
            })
            _mark_footprint(covered, x, end - 1, y, 1, scale_x, scale_y)

    visible = indexes >= 0
    # Coverage means pixels included in the conservative modeled footprints.
    covered_visible = int(np.count_nonzero(covered & visible))
    visible_count = int(np.count_nonzero(visible))
    return {
        "schema_version": 1,
        "plan_type": "autodraw_interior_fill_plan",
        "canvas": {"width": width, "height": height},
        "brush_configuration": {
            "min_brush_value": min_brush_value,
            "max_brush_value": max_brush_value,
            "fallback_merge_gap_px": fallback_merge_gap_px,
            "scale_x_source_px_per_game_unit": scale_x,
            "scale_y_source_px_per_game_unit": scale_y,
            "footprint_model": "conservative_axis_aligned_rectangle",
            "automatic_execution_allowed": False,
        },
        "summary": {
            "visible_pixel_count": visible_count,
            "covered_visible_pixel_count": covered_visible,
            "coverage_percent": round(100.0 * covered_visible / visible_count, 4) if visible_count else 100.0,
            "stroke_count": len(strokes),
            "interior_fill_stroke_count": sum(s["role"] == "interior_fill" for s in strokes),
            "boundary_fallback_stroke_count": sum(s["role"] == "boundary_fallback" for s in strokes),
            "all_strokes_safe_for_color_map": all(s["safe_for_color_map"] for s in strokes),
            "ready_for_automatic_execution": False,
        },
        "strokes": strokes,
    }
