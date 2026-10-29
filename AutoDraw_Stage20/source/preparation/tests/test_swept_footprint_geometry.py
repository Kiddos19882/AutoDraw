from __future__ import annotations

import numpy as np
import pytest

from swept_footprint_geometry import check_swept_footprint


def test_horizontal_segment_is_safe_inside_one_color():
    indexes = np.full((12, 16), -1, dtype=np.int32)
    indexes[2:10, 2:14] = 3
    result = check_swept_footprint(indexes, [(4, 5), (10, 5)], color_index=3, brush_value=2)
    assert result["safe_for_color_map"] is True
    assert result["safe_to_execute"] is False
    assert result["checked_footprint_cells"] > 0


def test_diagonal_segment_rejects_neighbor_color():
    indexes = np.zeros((12, 12), dtype=np.int32)
    indexes[5, 5] = 1
    result = check_swept_footprint(indexes, [(2, 2), (8, 8)], color_index=0, brush_value=1)
    assert result["safe_for_color_map"] is False
    assert result["reason"] == "footprint_crosses_other_color_or_transparency"
    assert result["offending_pixel"] == [5, 5]


def test_polyline_checks_turns_not_only_endpoints():
    indexes = np.full((12, 12), 4, dtype=np.int32)
    indexes[5, 8] = -1
    result = check_swept_footprint(indexes, [(2, 2), (8, 2), (8, 8)], color_index=4)
    assert result["safe_for_color_map"] is False
    assert result["offending_pixel"] == [8, 5]


def test_wide_brush_rejects_narrow_color_region():
    indexes = np.zeros((10, 10), dtype=np.int32)
    indexes[2:8, 2:8] = 1
    result = check_swept_footprint(indexes, [(3, 3), (6, 3)], color_index=1, brush_value=4)
    assert result["safe_for_color_map"] is False


def test_isolated_pixel_can_be_checked_as_single_point():
    indexes = np.full((5, 5), -1, dtype=np.int32)
    indexes[2, 2] = 7
    result = check_swept_footprint(indexes, [(2, 2)], color_index=7)
    assert result["safe_for_color_map"] is True
    assert result["centerline_cell_count"] == 1


@pytest.mark.parametrize("points", [[], [(0, float("nan"))], [(0, 0), (float("inf"), 2)], [(0,)], ["xy"]])
def test_malformed_paths_are_rejected(points):
    with pytest.raises(ValueError):
        check_swept_footprint(np.zeros((5, 5), dtype=np.int32), points, color_index=0)


def test_invalid_map_and_brush_arguments_are_rejected():
    with pytest.raises(ValueError):
        check_swept_footprint(np.array([0, 1]), [(0, 0)], color_index=0)
    with pytest.raises(ValueError):
        check_swept_footprint(np.zeros((3, 3), dtype=np.int32), [(1, 1)], color_index=0, brush_value=0)


def test_path_outside_canvas_is_rejected_even_if_footprint_clips_to_canvas():
    indexes = np.zeros((5, 5), dtype=np.int32)
    result = check_swept_footprint(indexes, [(-1, 2), (2, 2)], color_index=0)
    assert result["safe_for_color_map"] is False
    assert result["reason"] == "centerline_outside_canvas"


def test_supercover_includes_both_side_cells_at_exact_corner_crossings():
    from swept_footprint_geometry import _supercover_segment

    cells = set(_supercover_segment((0, 0), (2, 2)))
    assert {(1, 0), (0, 1), (1, 1), (2, 1), (1, 2), (2, 2)} <= cells


def test_supercover_is_direction_symmetric():
    from swept_footprint_geometry import _supercover_segment

    forward = set(_supercover_segment((1.25, 7.75), (10.5, 2.125)))
    backward = set(_supercover_segment((10.5, 2.125), (1.25, 7.75)))
    assert forward == backward


def test_supercover_handles_vertical_and_negative_direction_segments():
    from swept_footprint_geometry import _supercover_segment

    vertical = set(_supercover_segment((4, 9), (4, 1)))
    assert {(4, y) for y in range(1, 10)} <= vertical
    reverse_diagonal = set(_supercover_segment((8, 2), (2, 8)))
    assert (5, 5) in reverse_diagonal
    assert (5, 4) in reverse_diagonal
    assert (4, 5) in reverse_diagonal
