from __future__ import annotations

import numpy as np
import pytest

from interior_fill_planner import InteriorFillError, build_interior_fill_plan


def test_uniform_rectangle_uses_wide_fill_and_covers_every_visible_pixel():
    indexes = np.full((30, 50), -1, dtype=np.int32)
    indexes[3:27, 4:46] = 0

    plan = build_interior_fill_plan(indexes, max_brush_value=8)

    assert plan["plan_type"] == "autodraw_interior_fill_plan"
    assert plan["summary"]["interior_fill_stroke_count"] > 0
    assert plan["summary"]["coverage_percent"] == 100.0
    assert plan["summary"]["all_strokes_safe_for_color_map"]
    assert not plan["summary"]["ready_for_automatic_execution"]
    assert all(stroke["safe_to_execute"] is False for stroke in plan["strokes"])


def test_wide_fill_never_crosses_neighbor_color_or_transparency():
    indexes = np.zeros((24, 40), dtype=np.int32)
    indexes[:, 20:] = 1
    indexes[0:5, :] = -1

    plan = build_interior_fill_plan(indexes, max_brush_value=10)

    assert plan["summary"]["coverage_percent"] == 100.0
    for stroke in plan["strokes"]:
        color = stroke["color_index"]
        brush = stroke["brush_value"]
        (first, last) = stroke["points"]
        x1, x2, y = int(first["x"]), int(last["x"]), int(first["y"])
        half_x = brush / 2
        half_y = brush / 2
        left = max(0, int(np.ceil(x1 - half_x - 1e-9)))
        right = min(indexes.shape[1] - 1, int(np.floor(x2 + half_x + 1e-9)))
        top = max(0, int(np.ceil(y - half_y - 1e-9)))
        bottom = min(indexes.shape[0] - 1, int(np.floor(y + half_y + 1e-9)))
        assert np.all(indexes[top:bottom + 1, left:right + 1] == color)


def test_narrow_features_and_isolated_pixels_are_kept_by_fallback():
    indexes = np.full((12, 16), -1, dtype=np.int32)
    indexes[5, 2:14] = 0
    indexes[2, 7] = 1

    plan = build_interior_fill_plan(indexes, max_brush_value=8)

    fallback = [s for s in plan["strokes"] if s["role"] == "boundary_fallback"]
    assert fallback
    assert any(s["color_index"] == 1 for s in fallback)
    assert plan["summary"]["coverage_percent"] == 100.0


def test_rejects_bad_dimensions_indexes_and_brush_range():
    with pytest.raises(InteriorFillError):
        build_interior_fill_plan(np.zeros((3, 3, 1), dtype=np.int32))
    with pytest.raises(InteriorFillError):
        build_interior_fill_plan(np.array([[0.0, 1.0]]))
    with pytest.raises(InteriorFillError):
        build_interior_fill_plan(np.array([[-2]], dtype=np.int32))
    with pytest.raises(InteriorFillError):
        build_interior_fill_plan(np.zeros((3, 3), dtype=np.int32), max_brush_value=21)


def test_scale_that_makes_even_thin_footprint_unsafe_fails_closed():
    indexes = np.array([[0, 1, 1]], dtype=np.int32)
    with pytest.raises(InteriorFillError):
        build_interior_fill_plan(indexes, max_brush_value=2, brush_scale_x=3.0)


def test_hole_and_disconnected_component_remain_unpainted_and_separate():
    indexes = np.full((28, 36), -1, dtype=np.int32)
    indexes[2:24, 2:24] = 0
    indexes[8:18, 8:18] = -1  # transparent hole
    indexes[4:9, 29:34] = 0  # disconnected component

    plan = build_interior_fill_plan(indexes, max_brush_value=10)

    assert plan["summary"]["coverage_percent"] == 100.0
    for stroke in plan["strokes"]:
        color = stroke["color_index"]
        brush = stroke["brush_value"]
        first, last = stroke["points"]
        x1, x2, y = int(first["x"]), int(last["x"]), int(first["y"])
        left = max(0, int(np.ceil(x1 - brush / 2 - 1e-9)))
        right = min(indexes.shape[1] - 1, int(np.floor(x2 + brush / 2 + 1e-9)))
        top = max(0, int(np.ceil(y - brush / 2 - 1e-9)))
        bottom = min(indexes.shape[0] - 1, int(np.floor(y + brush / 2 + 1e-9)))
        assert np.all(indexes[top:bottom + 1, left:right + 1] == color)

    # The hole is transparent in the input and cannot be covered by a planned
    # footprint; disconnected regions are represented without connecting paths.
    assert np.all(indexes[8:18, 8:18] == -1)
    assert all(len(stroke["points"]) == 2 for stroke in plan["strokes"])
