from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
import sys
from typing import Any

PREPARATION_SOURCE = Path(__file__).resolve().parents[1] / "source" / "preparation"
sys.path.insert(0, str(PREPARATION_SOURCE))

import brush_footprint_geometry as geometry


def _bounds(points, brush, sx, sy, width, height):
    import math

    radius = brush / 2.0
    epsilon = 1e-9
    left = max(0, math.floor((min(p[0] for p in points) - radius) * sx - 0.5 + epsilon) + 1)
    right = min(width - 1, math.ceil((max(p[0] for p in points) + radius) * sx + 0.5 - epsilon) - 1)
    top = max(0, math.floor((min(p[1] for p in points) - radius) * sy - 0.5 + epsilon) + 1)
    bottom = min(height - 1, math.ceil((max(p[1] for p in points) + radius) * sy + 0.5 - epsilon) - 1)
    return None if left > right or top > bottom else (left, right, top, bottom)


def _segment_bounds(start, end, brush, sx, sy, width, height):
    import math

    radius = brush / 2.0
    epsilon = 1e-9
    left = max(0, math.floor((min(start[0], end[0]) - radius) * sx - 0.5 + epsilon) + 1)
    right = min(width - 1, math.ceil((max(start[0], end[0]) + radius) * sx + 0.5 - epsilon) - 1)
    top = max(0, math.floor((min(start[1], end[1]) - radius) * sy - 0.5 + epsilon) + 1)
    bottom = min(height - 1, math.ceil((max(start[1], end[1]) + radius) * sy + 0.5 - epsilon) - 1)
    return None if left > right or top > bottom else (left, right, top, bottom)


def _area(bounds):
    if bounds is None:
        return 0
    left, right, top, bottom = bounds
    return (right - left + 1) * (bottom - top + 1)


def _global_aabb_reference(points, brush, sx, sy, width, height):
    """Reproduce the former global-AABB raster loop with production predicates."""
    bounds = _bounds(points, brush, sx, sy, width, height)
    potential: set[tuple[int, int]] = set()
    guaranteed: set[tuple[int, int]] = set()
    counters = {
        "segment_cell_visits": 0,
        "segment_rectangle_distance_calls": 0,
        "point_segment_distance_calls": 0,
    }
    if bounds is None:
        return {"potential_cells": potential, "guaranteed_cells": guaranteed}, counters

    original_rectangle_distance = geometry._segment_rectangle_distance_squared
    original_point_distance = geometry._point_segment_distance_squared

    def count_rectangle_distance(*args):
        counters["segment_rectangle_distance_calls"] += 1
        return original_rectangle_distance(*args)

    def count_point_distance(*args):
        counters["point_segment_distance_calls"] += 1
        return original_point_distance(*args)

    geometry._segment_rectangle_distance_squared = count_rectangle_distance
    geometry._point_segment_distance_squared = count_point_distance
    try:
        left, right, top, bottom = bounds
        radius_squared = (brush / 2.0) ** 2
        tolerance = 1e-12 * max(1.0, radius_squared)
        segments = list(zip(points, points[1:])) or [(points[0], points[0])]

        for py in range(top, bottom + 1):
            cell_top, cell_bottom = (py - 0.5) / sy, (py + 0.5) / sy
            for px in range(left, right + 1):
                cell_left, cell_right = (px - 0.5) / sx, (px + 0.5) / sx
                cell = (px, py)
                corners = (
                    (cell_left, cell_top), (cell_right, cell_top),
                    (cell_left, cell_bottom), (cell_right, cell_bottom),
                )
                for start, end in segments:
                    if cell in potential and cell in guaranteed:
                        break
                    counters["segment_cell_visits"] += 1
                    if cell not in potential:
                        if geometry._segment_rectangle_distance_squared(
                            start, end, cell_left, cell_top, cell_right, cell_bottom
                        ) < radius_squared:
                            potential.add(cell)
                    if cell not in guaranteed:
                        wholly_inside = all(
                            geometry._point_segment_distance_squared(corner, start, end)
                            <= radius_squared - tolerance
                            for corner in corners
                        )
                        if wholly_inside:
                            guaranteed.add(cell)
    finally:
        geometry._segment_rectangle_distance_squared = original_rectangle_distance
        geometry._point_segment_distance_squared = original_point_distance

    return {"potential_cells": potential, "guaranteed_cells": guaranteed}, counters


def _optimized_instrumented(points, brush, sx, sy, width, height):
    original_potential = geometry._segment_rectangle_distance_squared
    original_guaranteed = geometry._point_segment_distance_squared
    counters = {
        "segment_rectangle_distance_calls": 0,
        "point_segment_distance_calls": 0,
    }

    def count_potential(*args):
        counters["segment_rectangle_distance_calls"] += 1
        return original_potential(*args)

    def count_guaranteed(*args):
        counters["point_segment_distance_calls"] += 1
        return original_guaranteed(*args)

    geometry._segment_rectangle_distance_squared = count_potential
    geometry._point_segment_distance_squared = count_guaranteed
    try:
        result = geometry.swept_capsule_pixel_masks(
            points, brush, sx, sy, width, height
        )
    finally:
        geometry._segment_rectangle_distance_squared = original_potential
        geometry._point_segment_distance_squared = original_guaranteed

    segments = list(zip(points, points[1:])) or [(points[0], points[0])]
    segment_bounds = [
        _segment_bounds(a, b, brush, sx, sy, width, height)
        for a, b in segments
    ]
    counters["segment_cell_visits"] = sum(_area(item) for item in segment_bounds)
    counters["unique_candidate_cells"] = len({
        (x, y)
        for item in segment_bounds if item is not None
        for x in range(item[0], item[1] + 1)
        for y in range(item[2], item[3] + 1)
    })
    return result, counters


def _cases():
    return [
        {
            "name": "winding_reference_case",
            "points": [(4, 5), (18, 5), (18, 34), (7, 34), (7, 13), (31, 13), (31, 42), (44, 42)],
            "brush": 6, "sx": 1.25, "sy": 0.8, "width": 64, "height": 52,
        },
        {
            "name": "large_zigzag",
            "points": [(8, 10), (220, 10), (220, 175), (18, 175), (18, 28), (205, 28), (205, 150), (35, 150), (35, 48), (190, 48), (190, 125), (55, 125)],
            "brush": 8, "sx": 1.0, "sy": 1.0, "width": 256, "height": 192,
        },
        {
            "name": "diagonal_turns",
            "points": [(8, 8), (205, 165), (25, 170), (210, 20), (120, 95), (235, 180)],
            "brush": 5, "sx": 1.35, "sy": 0.75, "width": 320, "height": 200,
        },
        {
            "name": "compact_many_segments",
            "points": [(80, 80), (95, 82), (88, 96), (104, 101), (92, 112), (110, 118), (98, 130), (120, 136), (108, 145)],
            "brush": 4, "sx": 1.2, "sy": 0.9, "width": 256, "height": 192,
        },
        {
            "name": "single_long_diagonal",
            "points": [(5, 5), (240, 175)],
            "brush": 7, "sx": 1.0, "sy": 1.0, "width": 256, "height": 192,
        },
    ]


def _benchmark_case(case: dict[str, Any], repeats: int):
    args = (
        case["points"], case["brush"], case["sx"], case["sy"],
        case["width"], case["height"],
    )
    reference, reference_counts = _global_aabb_reference(*args)
    optimized, optimized_counts = _optimized_instrumented(*args)
    if (
        reference["potential_cells"] != optimized["potential_cells"]
        or reference["guaranteed_cells"] != optimized["guaranteed_cells"]
    ):
        raise AssertionError(f"Mask mismatch in {case['name']}")

    # Warm both paths before collecting timing samples.
    for _ in range(2):
        _global_aabb_reference(*args)
        _optimized_instrumented(*args)

    reference_times, optimized_times = [], []
    for index in range(repeats):
        runners = (
            (_global_aabb_reference, reference_times),
            (_optimized_instrumented, optimized_times),
        )
        if index % 2:
            runners = tuple(reversed(runners))
        for runner, samples in runners:
            started = time.perf_counter_ns()
            runner(*args)
            samples.append(time.perf_counter_ns() - started)

    global_bounds = _bounds(*args)
    segments = list(zip(case["points"], case["points"][1:])) or [(case["points"][0], case["points"][0])]
    global_cells = _area(global_bounds)
    global_candidate_slots = global_cells * len(segments)
    segmented_candidate_slots = optimized_counts["segment_cell_visits"]
    return {
        "name": case["name"],
        "parameters": {
            "points": len(case["points"]), "segments": len(segments),
            "brush": case["brush"], "scale_x": case["sx"], "scale_y": case["sy"],
            "canvas": [case["width"], case["height"]],
        },
        "mask_equivalence": True,
        "candidate_cells": {
            "global_aabb_cells": global_cells,
            "global_aabb_segment_slots": global_candidate_slots,
            "per_segment_aabb_slots": segmented_candidate_slots,
            "per_segment_unique_cells": optimized_counts["unique_candidate_cells"],
            "slot_reduction_percent": (
                100.0 * (1.0 - segmented_candidate_slots / global_candidate_slots)
                if global_candidate_slots else 0.0
            ),
        },
        "predicate_evaluations": {
            "global_aabb": reference_counts,
            "per_segment_aabb": optimized_counts,
            "distance_call_reduction_percent": (
                100.0 * (
                    1.0
                    - (
                        optimized_counts["segment_rectangle_distance_calls"]
                        + optimized_counts["point_segment_distance_calls"]
                    )
                    / (
                        reference_counts["segment_rectangle_distance_calls"]
                        + reference_counts["point_segment_distance_calls"]
                    )
                )
                if reference_counts["segment_rectangle_distance_calls"]
                + reference_counts["point_segment_distance_calls"] else 0.0
            ),
        },
        "timing_ms": {
            "repeats": repeats,
            "global_aabb_median": statistics.median(reference_times) / 1_000_000,
            "per_segment_aabb_median": statistics.median(optimized_times) / 1_000_000,
            "global_aabb_samples": [value / 1_000_000 for value in reference_times],
            "per_segment_aabb_samples": [value / 1_000_000 for value in optimized_times],
            "median_speedup": (
                statistics.median(reference_times) / statistics.median(optimized_times)
            ),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark capsule raster broad-phase variants.")
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    parser.add_argument("--repeats", type=int, default=7)
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error("--repeats must be at least 3 for a useful median.")

    report = {
        "benchmark": "capsule_global_vs_per_segment_aabb",
        "method": (
            "Same production distance predicates and mask semantics; former global-AABB "
            "enumeration is reconstructed in the benchmark. Wall-clock values are "
            "environment-specific and are not renderer or CHALK measurements."
        ),
        "repeats": args.repeats,
        "cases": [_benchmark_case(case, args.repeats) for case in _cases()],
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
