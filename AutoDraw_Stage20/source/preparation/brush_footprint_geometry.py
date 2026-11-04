from __future__ import annotations

"""Conservative mapping from a continuous brush footprint to raster pixel cells.

The color map stores pixels as cells, not mathematical points. A safety check
must include every pixel cell with positive-area intersection with the modeled
brush footprint; testing only pixel centers can miss edge bleed.
"""

import math


def footprint_pixel_bounds(
    x_start: float,
    x_end: float,
    y: float,
    brush_value: int,
    scale_x: float,
    scale_y: float,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    """Return inclusive raster bounds intersected by a horizontal brush stroke.

    Coordinates refer to pixel centers. Cells that only touch the brush exactly
    at an edge are excluded; any positive-area intersection is included. Bounds
    are clipped to the canvas because painting cannot affect pixels outside it.
    Return None when the clipped footprint is empty.
    """
    if width <= 0 or height <= 0:
        return None
    if brush_value <= 0 or scale_x <= 0 or scale_y <= 0:
        raise ValueError("Brush value and axis scales must be positive.")
    if not all(math.isfinite(value) for value in (x_start, x_end, y, scale_x, scale_y)):
        raise ValueError("Brush geometry values must be finite.")
    if x_start > x_end:
        raise ValueError("x_start must not exceed x_end.")

    half_x = brush_value * scale_x / 2.0
    half_y = brush_value * scale_y / 2.0
    # A pixel centered at p occupies [p - 0.5, p + 0.5]. The strict
    # inequalities exclude cells that touch only along a zero-area edge.
    epsilon = 1e-9
    left = math.floor(x_start - half_x - 0.5 + epsilon) + 1
    right = math.ceil(x_end + half_x + 0.5 - epsilon) - 1
    top = math.floor(y - half_y - 0.5 + epsilon) + 1
    bottom = math.ceil(y + half_y + 0.5 - epsilon) - 1

    left = max(0, left)
    right = min(width - 1, right)
    top = max(0, top)
    bottom = min(height - 1, bottom)
    if left > right or top > bottom:
        return None
    return left, right, top, bottom



def _point_segment_distance_squared(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return (px - ax) ** 2 + (py - ay) ** 2
    projection = ((px - ax) * dx + (py - ay) * dy) / length_squared
    t = min(1.0, max(0.0, projection))
    nearest_x, nearest_y = ax + t * dx, ay + t * dy
    return (px - nearest_x) ** 2 + (py - nearest_y) ** 2


def _segment_intersects_rectangle(
    start: tuple[float, float],
    end: tuple[float, float],
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> bool:
    """Liang-Barsky segment/rectangle intersection, including boundary contact."""
    x1, y1 = start
    x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    lower, upper = 0.0, 1.0
    for p, q in (
        (-dx, x1 - left),
        (dx, right - x1),
        (-dy, y1 - top),
        (dy, bottom - y1),
    ):
        if p == 0:
            if q < 0:
                return False
            continue
        ratio = q / p
        if p < 0:
            lower = max(lower, ratio)
        else:
            upper = min(upper, ratio)
        if lower > upper:
            return False
    return True


def _point_rectangle_distance_squared(
    point: tuple[float, float],
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> float:
    px, py = point
    dx = max(left - px, 0.0, px - right)
    dy = max(top - py, 0.0, py - bottom)
    return dx * dx + dy * dy


def _segment_rectangle_distance_squared(
    start: tuple[float, float],
    end: tuple[float, float],
    left: float,
    top: float,
    right: float,
    bottom: float,
) -> float:
    """Minimum Euclidean distance between a segment and an axis-aligned rectangle."""
    if (
        left <= start[0] <= right and top <= start[1] <= bottom
    ) or (
        left <= end[0] <= right and top <= end[1] <= bottom
    ) or _segment_intersects_rectangle(start, end, left, top, right, bottom):
        return 0.0

    corners = (
        (left, top),
        (right, top),
        (left, bottom),
        (right, bottom),
    )
    distances = [
        _point_segment_distance_squared(corner, start, end)
        for corner in corners
    ]
    distances.extend((
        _point_rectangle_distance_squared(start, left, top, right, bottom),
        _point_rectangle_distance_squared(end, left, top, right, bottom),
    ))
    return min(distances)


def swept_capsule_pixel_masks(
    points: object,
    brush_value: int,
    scale_x: float,
    scale_y: float,
    width: int,
    height: int,
) -> dict[str, object]:
    """Return conservative pixel-cell masks for an ideal round-capped polyline.

    potential_cells contains cells with positive-area intersection with the
    continuous capsule sweep and is suitable as a safety/leakage envelope.
    guaranteed_cells contains only cells wholly contained in at least one
    segment capsule; it is a conservative coverage under-approximation.

    Pixel cells are mapped back into logical coordinates before distance tests,
    so non-uniform axis scales are handled as an ellipse in screen space. The
    polyline model is the union of round-capped segment capsules (round joins).
    This is an offline geometric candidate, not proof of a particular game's
    renderer, antialiasing, or deployed Egret runtime.
    """
    if isinstance(brush_value, bool) or not isinstance(brush_value, int) or brush_value <= 0:
        raise ValueError("brush_value must be a positive integer.")
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise ValueError("width must be a positive integer.")
    if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
        raise ValueError("height must be a positive integer.")
    try:
        sx, sy = float(scale_x), float(scale_y)
    except (TypeError, ValueError) as exc:
        raise ValueError("Axis scales must be finite positive numbers.") from exc
    if not math.isfinite(sx) or not math.isfinite(sy) or sx <= 0 or sy <= 0:
        raise ValueError("Axis scales must be finite positive numbers.")

    try:
        raw_points = list(points)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError("points must be a non-empty iterable.") from exc
    if not raw_points:
        raise ValueError("points must be a non-empty iterable.")

    normalized: list[tuple[float, float]] = []
    for item in raw_points:
        if isinstance(item, dict):
            raw_x, raw_y = item.get("x"), item.get("y")
        else:
            if isinstance(item, (str, bytes)):
                raise ValueError("Each point must contain finite x/y coordinates.")
            try:
                if len(item) != 2:  # type: ignore[arg-type]
                    raise ValueError("Each point must contain exactly two coordinates.")
                raw_x, raw_y = item[0], item[1]  # type: ignore[index]
            except (TypeError, IndexError) as exc:
                raise ValueError("Each point must contain finite x/y coordinates.") from exc
        if isinstance(raw_x, bool) or isinstance(raw_y, bool):
            raise ValueError("Point coordinates must be finite numbers.")
        try:
            x, y = float(raw_x), float(raw_y)
        except (TypeError, ValueError) as exc:
            raise ValueError("Point coordinates must be finite numbers.") from exc
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("Point coordinates must be finite numbers.")
        normalized.append((x, y))

    radius = brush_value / 2.0
    min_x = min(point[0] for point in normalized)
    max_x = max(point[0] for point in normalized)
    min_y = min(point[1] for point in normalized)
    max_y = max(point[1] for point in normalized)
    epsilon = 1e-9
    left = max(0, math.floor((min_x - radius) * sx - 0.5 + epsilon) + 1)
    right = min(width - 1, math.ceil((max_x + radius) * sx + 0.5 - epsilon) - 1)
    top = max(0, math.floor((min_y - radius) * sy - 0.5 + epsilon) + 1)
    bottom = min(height - 1, math.ceil((max_y + radius) * sy + 0.5 - epsilon) - 1)

    potential: set[tuple[int, int]] = set()
    guaranteed: set[tuple[int, int]] = set()
    if left > right or top > bottom:
        return {
            "bounds": None,
            "potential_cells": potential,
            "guaranteed_cells": guaranteed,
            "model": "ideal_round_capsule_polyline",
        }

    segments = list(zip(normalized, normalized[1:]))
    if not segments:
        segments = [(normalized[0], normalized[0])]
    radius_squared = radius * radius
    tolerance = 1e-12 * max(1.0, radius_squared)

    for py in range(top, bottom + 1):
        cell_top = (py - 0.5) / sy
        cell_bottom = (py + 0.5) / sy
        for px in range(left, right + 1):
            cell_left = (px - 0.5) / sx
            cell_right = (px + 0.5) / sx
            corners = (
                (cell_left, cell_top),
                (cell_right, cell_top),
                (cell_left, cell_bottom),
                (cell_right, cell_bottom),
            )
            may_be_painted = False
            fully_inside_one_capsule = False
            for start, end in segments:
                minimum_distance = _segment_rectangle_distance_squared(
                    start, end, cell_left, cell_top, cell_right, cell_bottom
                )
                if minimum_distance < radius_squared - tolerance:
                    may_be_painted = True
                if all(
                    _point_segment_distance_squared(corner, start, end)
                    <= radius_squared + tolerance
                    for corner in corners
                ):
                    fully_inside_one_capsule = True
                if may_be_painted and fully_inside_one_capsule:
                    break
            if may_be_painted:
                potential.add((px, py))
            if fully_inside_one_capsule:
                guaranteed.add((px, py))

    return {
        "bounds": (left, right, top, bottom),
        "potential_cells": potential,
        "guaranteed_cells": guaranteed,
        "model": "ideal_round_capsule_polyline",
    }
