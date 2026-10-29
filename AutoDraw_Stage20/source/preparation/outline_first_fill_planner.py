from __future__ import annotations

"""Experimental boundary-first raster planner; independent from interior-fill."""

from typing import Any

import numpy as np

from brush_footprint_geometry import footprint_pixel_bounds
from interior_fill_planner import InteriorFillError, build_interior_fill_plan


def _boundary_mask(indexes: np.ndarray) -> np.ndarray:
    """Mark visible pixels adjacent to another palette index or transparency."""
    visible = indexes >= 0
    boundary = np.zeros(indexes.shape, dtype=bool)
    boundary[0, :] |= visible[0, :]
    boundary[-1, :] |= visible[-1, :]
    boundary[:, 0] |= visible[:, 0]
    boundary[:, -1] |= visible[:, -1]
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        shifted = np.full(indexes.shape, -2, dtype=np.int32)
        source_y = slice(max(0, -dy), indexes.shape[0] - max(0, dy))
        source_x = slice(max(0, -dx), indexes.shape[1] - max(0, dx))
        target_y = slice(max(0, dy), indexes.shape[0] - max(0, -dy))
        target_x = slice(max(0, dx), indexes.shape[1] - max(0, -dx))
        shifted[target_y, target_x] = indexes[source_y, source_x]
        boundary |= visible & (shifted != indexes)
    return boundary


def build_outline_first_fill_plan(
    index_map: Any,
    *,
    max_brush_value: int = 20,
    min_brush_value: int = 2,
    brush_scale_x: float = 1.0,
    brush_scale_y: float = 1.0,
    fallback_merge_gap_px: int = 3,
) -> dict[str, Any]:
    """Plan conservative horizontal boundary runs first, then fill residual pixels.

    This is a first experimental approximation, not a connected contour tracer:
    boundary runs are horizontal and are emitted before residual interior-fill.
    """
    indexes = np.asarray(index_map)
    if indexes.ndim != 2 or not indexes.size or indexes.dtype.kind not in "iu":
        raise InteriorFillError("Карта цветов должна быть непустым двумерным массивом целых индексов.")
    if int(indexes.min()) < -1:
        raise InteriorFillError("Индекс прозрачности не может быть меньше -1.")
    indexes = indexes.astype(np.int32, copy=False)
    height, width = indexes.shape
    boundary = _boundary_mask(indexes)
    residual = indexes.copy()
    boundary_strokes: list[dict[str, Any]] = []

    # One-pixel horizontal boundary runs. A complete brush footprint must stay
    # within the source palette index; no contour is allowed to bridge colors.
    for y in range(height):
        x = 0
        while x < width:
            color = int(indexes[y, x])
            if color < 0 or not boundary[y, x]:
                x += 1
                continue
            end = x + 1
            while end < width and int(indexes[y, end]) == color and boundary[y, end]:
                end += 1
            bounds = footprint_pixel_bounds(x, end - 1, y, 1, brush_scale_x, brush_scale_y, width, height)
            if bounds is None:
                raise InteriorFillError("Контурный штрих имеет пустой footprint.")
            left, right, top, bottom = bounds
            if not np.all(indexes[top:bottom + 1, left:right + 1] == color):
                # Fail closed: split to individual pixels rather than bridging
                # a boundary whose combined brush footprint is not safe.
                for px in range(x, end):
                    pixel_bounds = footprint_pixel_bounds(px, px, y, 1, brush_scale_x, brush_scale_y, width, height)
                    if pixel_bounds is None:
                        raise InteriorFillError("Граничный пиксель не проходит footprint-проверку.")
                    pl, pr, pt, pb = pixel_bounds
                    if not np.all(indexes[pt:pb + 1, pl:pr + 1] == color):
                        raise InteriorFillError("Однопиксельный контур пересекает другой цвет или прозрачность.")
                    boundary_strokes.append({
                        "color_index": color,
                        "points": [{"x": float(px), "y": float(y)}, {"x": float(px), "y": float(y)}],
                        "brush_value": 1,
                        "role": "outline_boundary",
                        "safe_for_color_map": True,
                        "safe_to_execute": False,
                    })
                    residual[y, px] = -1
            else:
                boundary_strokes.append({
                    "color_index": color,
                    "points": [{"x": float(x), "y": float(y)}, {"x": float(end - 1), "y": float(y)}],
                    "brush_value": 1,
                    "role": "outline_boundary",
                    "safe_for_color_map": True,
                    "safe_to_execute": False,
                })
                residual[y, x:end] = -1
            x = end

    fill_plan = build_interior_fill_plan(
        residual,
        max_brush_value=max_brush_value,
        min_brush_value=min_brush_value,
        brush_scale_x=brush_scale_x,
        brush_scale_y=brush_scale_y,
        fallback_merge_gap_px=fallback_merge_gap_px,
    )
    strokes = boundary_strokes + fill_plan["strokes"]
    visible_count = int(np.count_nonzero(indexes >= 0))
    residual_count = int(np.count_nonzero(residual >= 0))
    return {
        "schema_version": 1,
        "plan_type": "autodraw_outline_first_fill_experimental",
        "canvas": {"width": width, "height": height},
        "brush_configuration": {
            **fill_plan["brush_configuration"],
            "automatic_execution_allowed": False,
            "strategy": "horizontal_boundary_runs_then_interior_fill",
        },
        "summary": {
            "visible_pixel_count": visible_count,
            "boundary_pixel_count": visible_count - residual_count,
            "residual_visible_pixel_count": residual_count,
            "outline_stroke_count": len(boundary_strokes),
            "interior_and_fallback_stroke_count": len(fill_plan["strokes"]),
            "stroke_count": len(strokes),
            "all_strokes_safe_for_color_map": all(s["safe_for_color_map"] for s in strokes),
            "ready_for_automatic_execution": False,
        },
        "strokes": strokes,
    }
