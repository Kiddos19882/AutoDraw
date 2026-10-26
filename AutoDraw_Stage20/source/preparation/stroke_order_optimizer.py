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


def orient_and_order_strokes(
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


