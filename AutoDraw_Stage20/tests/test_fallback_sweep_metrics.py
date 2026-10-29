from __future__ import annotations

from benchmark_stage7_fallback_merge_sweep import (
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
