from __future__ import annotations

from benchmark_stage7_fallback_merge_sweep import (
    _coverage_path_metrics,
    _path_length,
    _stroke_path_length,
    _zero_length_stroke_count,
)


def test_path_length_supports_points_and_counts_single_pixel_strokes():
    strokes = [
        {"points": [{"x": 0, "y": 0}, {"x": 3, "y": 4}]},
        {"points": [{"x": 7, "y": 2}, {"x": 7, "y": 2}]},
    ]

    assert _path_length(strokes) == 5.0
    assert _zero_length_stroke_count(strokes) == 1


def test_path_length_supports_start_end_representation():
    stroke = {"start": {"x": 1, "y": 1}, "end": {"x": 4, "y": 5}}

    assert _stroke_path_length(stroke) == 5.0


def test_path_length_includes_closing_segment_for_closed_contour():
    stroke = {
        "points": [
            {"x": 0, "y": 0},
            {"x": 3, "y": 0},
            {"x": 3, "y": 4},
        ],
        "closed": True,
    }

    # 3 + 4 + 5 px, including the last-to-first closing segment.
    assert _stroke_path_length(stroke) == 12.0


def test_isolated_pixel_strokes_are_counted_even_when_path_length_is_zero():
    strokes = [
        {"role": "boundary_fallback", "points": [{"x": 2, "y": 5}, {"x": 2, "y": 5}]}
        for _ in range(381)
    ]

    assert len(strokes) == 381
    assert _path_length(strokes) == 0.0
    assert _zero_length_stroke_count(strokes) == 381



def test_coverage_metrics_separate_fresh_and_revisited_centerline_pixels():
    import numpy as np

    indexes = np.zeros((5, 8), dtype=np.int32)
    strokes = [
        {
            "color_index": 0,
            "points": [{"x": 1, "y": 2}, {"x": 3, "y": 2}],
            "brush_value": 3,
            "role": "interior_fill",
        },
        {
            "color_index": 0,
            "points": [{"x": 2, "y": 2}, {"x": 4, "y": 2}],
            "brush_value": 1,
            "role": "boundary_fallback",
        },
    ]

    metrics = _coverage_path_metrics(strokes, indexes)

    assert metrics["revisit_centerline_pixel_visits"] == 3
    assert metrics["fresh_centerline_pixel_visits"] == 3
    assert metrics["invalid_centerline_pixel_visits"] == 0


def test_coverage_metrics_report_foreign_color_centerline_visits():
    import numpy as np

    indexes = np.zeros((3, 6), dtype=np.int32)
    indexes[1, 4] = 1
    stroke = {
        "color_index": 0,
        "points": [{"x": 2, "y": 1}, {"x": 5, "y": 1}],
        "brush_value": 1,
    }

    metrics = _coverage_path_metrics([stroke], indexes)

    assert metrics["invalid_centerline_pixel_visits"] == 1

def test_coverage_metrics_report_uncovered_visible_pixels():
    import numpy as np

    indexes = np.zeros((3, 5), dtype=np.int32)
    stroke = {
        "color_index": 0,
        "points": [{"x": 1, "y": 1}, {"x": 2, "y": 1}],
        "brush_value": 1,
    }

    metrics = _coverage_path_metrics([stroke], indexes)

    assert metrics["uncovered_visible_pixel_count"] == 13
    assert metrics["footprint_coverage_percent"] == 13.3333


def test_coverage_metrics_report_footprint_spilling_into_foreign_color():
    import numpy as np

    indexes = np.zeros((5, 6), dtype=np.int32)
    indexes[1, 2] = 1
    stroke = {
        "color_index": 0,
        "points": [{"x": 2, "y": 2}, {"x": 2, "y": 2}],
        "brush_value": 3,
    }

    metrics = _coverage_path_metrics([stroke], indexes)

    assert metrics["invalid_centerline_pixel_visits"] == 0
    assert metrics["invalid_footprint_pixel_visits"] > 0
