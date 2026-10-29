from __future__ import annotations

"""Conservative swept-footprint checks for straight segments and polylines."""

import math
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

from brush_footprint_geometry import footprint_pixel_bounds

Point = tuple[float, float]


def _normalize_point(point: Any) -> Point:
    if isinstance(point, dict):
        raw_x, raw_y = point.get("x"), point.get("y")
    elif isinstance(point, Sequence) and not isinstance(point, (str, bytes)) and len(point) == 2:
        raw_x, raw_y = point
    else:
        raise ValueError("Each path point must be an (x, y) pair or an x/y mapping.")
    if isinstance(raw_x, bool) or isinstance(raw_y, bool):
        raise ValueError("Boolean path coordinates are not supported.")
    try:
        x, y = float(raw_x), float(raw_y)
    except (TypeError, ValueError) as exc:
        raise ValueError("Path coordinates must be numeric.") from exc
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("Path coordinates must be finite.")
    return x, y


def _supercover_segment(start: Point, end: Point) -> list[tuple[int, int]]:
    """Sample all cells conservatively along a segment, including grid corners."""
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    steps = max(1, math.ceil(max(abs(dx), abs(dy)) * 2))
    cells: set[tuple[int, int]] = set()
    for index in range(steps + 1):
        t = index / steps
        x, y = x0 + dx * t, y0 + dy * t
        cells.add((math.floor(x + 0.5), math.floor(y + 0.5)))

    # Exact corner crossings conservatively include all four neighboring cells.
    if dx != 0 and dy != 0:
        min_x, max_x = sorted((x0, x1))
        min_y, max_y = sorted((y0, y1))
        for gx in range(math.floor(min_x + 0.5), math.ceil(max_x + 0.5)):
            for gy in range(math.floor(min_y + 0.5), math.ceil(max_y + 0.5)):
                tx = (gx + 0.5 - x0) / dx
                ty = (gy + 0.5 - y0) / dy
                if 0.0 <= tx <= 1.0 and abs(tx - ty) <= 1e-9:
                    cells.update(((gx, gy), (gx + 1, gy), (gx, gy + 1), (gx + 1, gy + 1)))
    return sorted(cells, key=lambda p: (p[1], p[0]))


def _path_centerline_cells(points: list[Point]) -> list[tuple[int, int]]:
    if len(points) == 1:
        return [(math.floor(points[0][0] + 0.5), math.floor(points[0][1] + 0.5))]
    cells: set[tuple[int, int]] = set()
    for start, end in zip(points, points[1:]):
        cells.update(_supercover_segment(start, end))
    return sorted(cells, key=lambda p: (p[1], p[0]))


def check_swept_footprint(
    index_map: Any,
    points: Iterable[Any],
    *,
    color_index: int,
    brush_value: int = 1,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
) -> dict[str, Any]:
    """Validate the modeled brush footprint along every segment of a polyline.

    This conservative offline check is not a measurement of the real brush and
    never authorizes automatic execution.
    """
    indexes = np.asarray(index_map)
    if indexes.ndim != 2 or not indexes.size or indexes.dtype.kind not in "iu":
        raise ValueError("Color map must be a non-empty 2D integer array.")
    if int(indexes.min()) < -1:
        raise ValueError("Transparent pixels must use -1; lower indexes are invalid.")
    if isinstance(color_index, bool) or not isinstance(color_index, int) or color_index < 0:
        raise ValueError("color_index must be a non-negative integer.")
    if isinstance(brush_value, bool) or not isinstance(brush_value, int) or brush_value <= 0:
        raise ValueError("brush_value must be a positive integer.")
    try:
        sx, sy = float(scale_x), float(scale_y)
    except (TypeError, ValueError) as exc:
        raise ValueError("Axis scales must be finite positive numbers.") from exc
    if not math.isfinite(sx) or not math.isfinite(sy) or sx <= 0 or sy <= 0:
        raise ValueError("Axis scales must be finite positive numbers.")

    normalized = [_normalize_point(point) for point in points]
    if not normalized:
        raise ValueError("Path must contain at least one point.")

    height, width = indexes.shape
    centerline_cells = _path_centerline_cells(normalized)
    checked_cells = 0
    for x, y in centerline_cells:
        bounds = footprint_pixel_bounds(x, x, y, brush_value, sx, sy, width, height)
        if bounds is None:
            return {
                "safe_for_color_map": False,
                "reason": "empty_or_out_of_canvas_footprint",
                "offending_pixel": [x, y],
                "checked_footprint_cells": checked_cells,
                "safe_to_execute": False,
            }
        left, right, top, bottom = bounds
        region = indexes[top:bottom + 1, left:right + 1]
        checked_cells += int(region.size)
        mismatch = np.argwhere(region != color_index)
        if mismatch.size:
            local_y, local_x = (int(v) for v in mismatch[0])
            return {
                "safe_for_color_map": False,
                "reason": "footprint_crosses_other_color_or_transparency",
                "offending_pixel": [left + local_x, top + local_y],
                "centerline_cell": [x, y],
                "checked_footprint_cells": checked_cells,
                "safe_to_execute": False,
            }

    return {
        "safe_for_color_map": True,
        "reason": None,
        "offending_pixel": None,
        "checked_footprint_cells": checked_cells,
        "centerline_cell_count": len(centerline_cells),
        "safe_to_execute": False,
    }
