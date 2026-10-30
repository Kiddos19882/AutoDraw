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
    """Enumerate every grid cell touched by a segment using grid traversal."""
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    x, y = math.floor(x0 + 0.5), math.floor(y0 + 0.5)
    end_x, end_y = math.floor(x1 + 0.5), math.floor(y1 + 0.5)
    cells: set[tuple[int, int]] = {(x, y)}

    step_x = 1 if dx > 0 else -1 if dx < 0 else 0
    step_y = 1 if dy > 0 else -1 if dy < 0 else 0
    t_delta_x = abs(1.0 / dx) if dx else math.inf
    t_delta_y = abs(1.0 / dy) if dy else math.inf
    boundary_x = x + 0.5 if step_x > 0 else x - 0.5
    boundary_y = y + 0.5 if step_y > 0 else y - 0.5
    t_max_x = (boundary_x - x0) / dx if dx else math.inf
    t_max_y = (boundary_y - y0) / dy if dy else math.inf

    # Each iteration crosses at least one grid boundary. At a corner crossing,
    # include both side cells as well as the diagonal cell (fail-closed policy).
    max_iterations = 4 + 2 * (abs(end_x - x) + abs(end_y - y))
    for _ in range(max_iterations):
        if (x, y) == (end_x, end_y):
            break
        if abs(t_max_x - t_max_y) <= 1e-12:
            cells.add((x + step_x, y))
            cells.add((x, y + step_y))
            x += step_x
            y += step_y
            cells.add((x, y))
            t_max_x += t_delta_x
            t_max_y += t_delta_y
        elif t_max_x < t_max_y:
            x += step_x
            cells.add((x, y))
            t_max_x += t_delta_x
        else:
            y += step_y
            cells.add((x, y))
            t_max_y += t_delta_y
    else:
        raise ValueError("Could not rasterize segment within the expected grid traversal bound.")

    def cells_touching_point(px: float, py: float) -> set[tuple[int, int]]:
        cx, cy = math.floor(px + 0.5), math.floor(py + 0.5)
        xs = {cx}
        ys = {cy}
        if math.isclose(px - 0.5, round(px - 0.5), rel_tol=0.0, abs_tol=1e-10):
            xs.add(cx - 1)
        if math.isclose(py - 0.5, round(py - 0.5), rel_tol=0.0, abs_tol=1e-10):
            ys.add(cy - 1)
        return {(cell_x, cell_y) for cell_x in xs for cell_y in ys}

    # Include cells touched exactly at segment endpoints. A segment aligned
    # with a grid boundary touches both sides along its entire length, not just
    # at the endpoints, so expand every traversed cell in that axis as well.
    cells.update(cells_touching_point(x0, y0))
    cells.update(cells_touching_point(x1, y1))
    if dx == 0 and math.isclose(x0 - 0.5, round(x0 - 0.5), rel_tol=0.0, abs_tol=1e-10):
        cells.update((cell_x - 1, cell_y) for cell_x, cell_y in tuple(cells))
    if dy == 0 and math.isclose(y0 - 0.5, round(y0 - 0.5), rel_tol=0.0, abs_tol=1e-10):
        cells.update((cell_x, cell_y - 1) for cell_x, cell_y in tuple(cells))
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
        if not (0 <= x < width and 0 <= y < height):
            return {
                "safe_for_color_map": False,
                "reason": "centerline_outside_canvas",
                "offending_pixel": [x, y],
                "checked_footprint_cells": checked_cells,
                "safe_to_execute": False,
            }
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
