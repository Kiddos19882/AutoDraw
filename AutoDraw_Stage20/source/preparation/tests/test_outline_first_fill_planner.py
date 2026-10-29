from __future__ import annotations

import numpy as np

from brush_footprint_geometry import footprint_pixel_bounds
from outline_first_fill_planner import build_outline_first_fill_plan


def _assert_footprints_stay_in_source_color(indexes, plan):
    height, width = indexes.shape
    for stroke in plan["strokes"]:
        (first, last) = stroke["points"]
        bounds = footprint_pixel_bounds(
            first["x"], last["x"], first["y"], stroke["brush_value"],
            1.0, 1.0, width, height,
        )
        assert bounds is not None
        left, right, top, bottom = bounds
        assert np.all(indexes[top:bottom + 1, left:right + 1] == stroke["color_index"])


def test_outline_boundary_runs_are_planned_before_residual_fill():
    indexes = np.full((11, 13), -1, dtype=np.int32)
    indexes[1:10, 1:12] = 0

    plan = build_outline_first_fill_plan(indexes, max_brush_value=3)

    roles = [stroke["role"] for stroke in plan["strokes"]]
    assert roles
    assert roles[:plan["summary"]["outline_stroke_count"]] == [
        "outline_boundary"
    ] * plan["summary"]["outline_stroke_count"]
    assert "interior_fill" in roles[plan["summary"]["outline_stroke_count"]:]
    assert plan["summary"]["boundary_pixel_count"] > 0
    assert plan["summary"]["residual_visible_pixel_count"] > 0
    assert plan["brush_configuration"]["automatic_execution_allowed"] is False
    assert plan["summary"]["ready_for_automatic_execution"] is False
    _assert_footprints_stay_in_source_color(indexes, plan)


def test_outline_first_never_bridges_neighbor_color_or_transparency():
    indexes = np.full((9, 14), -1, dtype=np.int32)
    indexes[1:8, 1:7] = 0
    indexes[1:8, 7:13] = 1

    plan = build_outline_first_fill_plan(indexes, max_brush_value=4)

    _assert_footprints_stay_in_source_color(indexes, plan)
    assert plan["summary"]["all_strokes_safe_for_color_map"]


def test_outline_first_preserves_isolated_pixels_as_separate_actions():
    indexes = np.full((5, 7), -1, dtype=np.int32)
    indexes[1, 1] = 0
    indexes[3, 5] = 1

    plan = build_outline_first_fill_plan(indexes, max_brush_value=4)

    assert plan["summary"]["outline_stroke_count"] == 2
    assert plan["summary"]["interior_and_fallback_stroke_count"] == 0
    assert [stroke["color_index"] for stroke in plan["strokes"]] == [0, 1]
    _assert_footprints_stay_in_source_color(indexes, plan)
