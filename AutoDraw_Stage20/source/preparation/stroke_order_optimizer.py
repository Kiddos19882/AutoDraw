"""Marker-change reduction and geometric stroke routing."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

_EPSILON = 1e-7


def _point_distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.hypot(second[0] - first[0], second[1] - first[1])


def _stroke_endpoints(stroke: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float]]:
    points = stroke["points"]
    first = (float(points[0]["x"]), float(points[0]["y"]))
    last = (float(points[-1]["x"]), float(points[-1]["y"]))
    if stroke.get("closed") and len(points) >= 3:
        return first, first
    return first, last


MAX_EXACT_NEAREST_NEIGHBOR_STROKES = 256


def _prepare_stroke(
    stroke: dict[str, Any],
    position: tuple[float, float],
) -> tuple[float, dict[str, Any]]:
    """Copy a path and orient its closest endpoint (or closed vertex) toward position."""
    candidate = dict(stroke)
    candidate["points"] = [dict(point) for point in stroke["points"]]
    raw_points = [
        (float(point["x"]), float(point["y"]))
        for point in candidate["points"]
    ]

    if candidate.get("closed") and len(raw_points) >= 3:
        start_index = min(
            range(len(raw_points)),
            key=lambda index: (_point_distance(position, raw_points[index]), index),
        )
        raw_points = raw_points[start_index:] + raw_points[:start_index]
    elif len(raw_points) >= 2:
        if _point_distance(position, raw_points[-1]) < _point_distance(position, raw_points[0]):
            raw_points.reverse()

    candidate["points"] = [{"x": x, "y": y} for x, y in raw_points]
    distance = _point_distance(position, raw_points[0])
    return distance, candidate


def _distance_to_stroke_access_point(
    position: tuple[float, float],
    stroke: dict[str, Any],
) -> float:
    """Cheap one-pass estimate used to choose the first stroke of a large batch."""
    points = stroke["points"]
    first = (float(points[0]["x"]), float(points[0]["y"]))
    if stroke.get("closed"):
        return min(
            _point_distance(position, (float(point["x"]), float(point["y"])))
            for point in points
        )
    last = (float(points[-1]["x"]), float(points[-1]["y"]))
    return min(_point_distance(position, first), _point_distance(position, last))


def _stroke_group_bounds(
    records: list[tuple[int, dict[str, Any]]],
) -> tuple[float, float, float, float]:
    min_x = min_y = math.inf
    max_x = max_y = -math.inf
    for _original_index, stroke in records:
        for point in stroke["points"]:
            x, y = float(point["x"]), float(point["y"])
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    return min_x, min_y, max_x, max_y


def _distance_to_bounds(
    position: tuple[float, float],
    bounds: tuple[float, float, float, float],
) -> float:
    x, y = position
    min_x, min_y, max_x, max_y = bounds
    dx = max(min_x - x, 0.0, x - max_x)
    dy = max(min_y - y, 0.0, y - max_y)
    return math.hypot(dx, dy)


def _route_color_group(
    records: list[tuple[int, dict[str, Any]]],
    position: tuple[float, float],
    *,
    preserve_first_stroke: bool,
) -> tuple[list[dict[str, Any]], tuple[float, float]]:
    """Route one marker's paths with exact greedy routing only for small batches."""
    if not records:
        return [], position

    available = list(records)
    ordered: list[dict[str, Any]] = []
    current = position

    if preserve_first_stroke:
        _original_index, first = available.pop(0)
        ordered.append(first)
        current = _stroke_endpoints(first)[1]
    else:
        first_position = min(
            range(len(available)),
            key=lambda index: (
                _distance_to_stroke_access_point(current, available[index][1]),
                available[index][0],
            ),
        )
        _original_index, first = available.pop(first_position)
        _distance, selected = _prepare_stroke(first, current)
        ordered.append(selected)
        current = _stroke_endpoints(selected)[1]

    # Nearest-neighbor routing is useful on small batches, but its quadratic
    # cost becomes prohibitive when the optimizer evaluates many candidate plans.
    if len(available) <= MAX_EXACT_NEAREST_NEIGHBOR_STROKES:
        while available:
            candidates: list[tuple[float, int, int, dict[str, Any]]] = []
            for list_position, (original_index, stroke) in enumerate(available):
                distance, candidate = _prepare_stroke(stroke, current)
                candidates.append((distance, original_index, list_position, candidate))
            _distance, _original_index, selected_position, selected = min(
                candidates, key=lambda item: (item[0], item[1])
            )
            available.pop(selected_position)
            ordered.append(selected)
            current = _stroke_endpoints(selected)[1]
        return ordered, current

    # For large groups, use a deterministic spatial route. It is O(N log N)
    # rather than O(N^2), while still reversing open paths and rotating closed
    # paths to reduce pen-up distance locally.
    available.sort(
        key=lambda item: (
            float(item[1]["points"][0]["y"]),
            float(item[1]["points"][0]["x"]),
            item[0],
        )
    )
    for _original_index, stroke in available:
        _distance, selected = _prepare_stroke(stroke, current)
        ordered.append(selected)
        current = _stroke_endpoints(selected)[1]

    return ordered, current


def orient_and_order_strokes(
    strokes: list[dict[str, Any]],
    color_grouping: bool,
) -> list[dict[str, Any]]:
    """Group strokes by color and route them without quadratic work on large plans.

    Grouping into a single consecutive batch per marker is the main guarantee:
    it minimizes marker changes to the number of used colors minus one. Small
    batches use greedy nearest-neighbor ordering; large batches use a spatial
    approximation to keep image optimization responsive.
    """
    if len(strokes) < 2 or not color_grouping:
        return strokes

    remaining_by_color: dict[int, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for original_index, stroke in enumerate(strokes):
        remaining_by_color[int(stroke["color"]["palette_index"])].append(
            (original_index, stroke)
        )

    # Compute spatial bounds once. Selecting the next marker by its closest
    # bounding box avoids scanning every stroke for every marker transition.
    bounds_by_color = {
        color_index: _stroke_group_bounds(records)
        for color_index, records in remaining_by_color.items()
    }

    first_color = int(strokes[0]["color"]["palette_index"])
    first_group = remaining_by_color.pop(first_color)
    ordered, current = _route_color_group(
        first_group, _stroke_endpoints(strokes[0])[1], preserve_first_stroke=True
    )

    while remaining_by_color:
        next_color = min(
            remaining_by_color,
            key=lambda color_index: (
                _distance_to_bounds(current, bounds_by_color[color_index]),
                remaining_by_color[color_index][0][0],
            ),
        )
        group = remaining_by_color.pop(next_color)
        batch, current = _route_color_group(
            group, current, preserve_first_stroke=False
        )
        ordered.extend(batch)

    return ordered
