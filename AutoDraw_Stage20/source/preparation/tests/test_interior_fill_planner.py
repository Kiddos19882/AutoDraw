from __future__ import annotations

import numpy as np
import pytest

from interior_fill_planner import (
    InteriorFillError,
    _iter_fallback_runs,
    build_interior_fill_plan,
)


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
        footprint = _independent_footprint_pixels(
            indexes.shape, x1, x2, y, brush,
            plan["brush_configuration"]["scale_x_source_px_per_game_unit"],
            plan["brush_configuration"]["scale_y_source_px_per_game_unit"],
        )
        for py, px in footprint:
            assert indexes[py, px] == color


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
        footprint = _independent_footprint_pixels(
            indexes.shape, x1, x2, y, brush,
            plan["brush_configuration"]["scale_x_source_px_per_game_unit"],
            plan["brush_configuration"]["scale_y_source_px_per_game_unit"],
        )
        for py, px in footprint:
            assert indexes[py, px] == color

    # The hole is transparent in the input and cannot be covered by a planned
    # footprint; disconnected regions are represented without connecting paths.
    assert np.all(indexes[8:18, 8:18] == -1)
    assert all(len(stroke["points"]) == 2 for stroke in plan["strokes"])

def _independent_footprint_pixels(
    shape: tuple[int, int],
    x1: int,
    x2: int,
    y: int,
    brush: int,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
) -> set[tuple[int, int]]:
    """Enumerate pixel centers covered by a modeled rectangular brush footprint.

    Deliberately uses coordinate inequalities rather than the planner's ceil/floor
    slice calculation, so a shared off-by-one error is less likely to pass unnoticed.
    """
    height, width = shape
    half_x = brush * scale_x / 2.0
    half_y = brush * scale_y / 2.0
    return {
        (py, px)
        for py in range(height)
        for px in range(width)
        if py + 0.5 > y - half_y and py - 0.5 < y + half_y
        and px + 0.5 > x1 - half_x and px - 0.5 < x2 + half_x
    }


@pytest.mark.parametrize("seed", range(12))
def test_randomized_maps_match_independent_footprint_oracle(seed: int):
    rng = np.random.default_rng(seed)
    indexes = rng.integers(-1, 4, size=(7, 11), dtype=np.int32)

    plan = build_interior_fill_plan(indexes, max_brush_value=5)
    independently_covered: set[tuple[int, int]] = set()

    for stroke in plan["strokes"]:
        color = stroke["color_index"]
        brush = stroke["brush_value"]
        first, last = stroke["points"]
        x1, x2, y = int(first["x"]), int(last["x"]), int(first["y"])
        footprint = _independent_footprint_pixels(
            indexes.shape, x1, x2, y, brush,
            plan["brush_configuration"]["scale_x_source_px_per_game_unit"],
            plan["brush_configuration"]["scale_y_source_px_per_game_unit"],
        )

        for py, px in footprint:
            assert indexes[py, px] == color, (
                f"seed={seed}, stroke={stroke}, foreign pixel at ({px}, {py}) "
                f"has palette index {indexes[py, px]}"
            )
        independently_covered.update(footprint)

    expected_visible = {
        (int(py), int(px))
        for py, px in zip(*np.where(indexes >= 0))
    }
    assert expected_visible <= independently_covered
    assert plan["summary"]["coverage_percent"] == 100.0
    assert plan["summary"]["all_strokes_safe_for_color_map"]
    assert not plan["summary"]["ready_for_automatic_execution"]

@pytest.mark.parametrize(
    ("scale_x", "scale_y"),
    [(0.75, 1.0), (1.0, 0.75), (1.0, 1.0)],
)
def test_anisotropic_scale_preserves_diagonal_components_and_holes(scale_x: float, scale_y: float):
    indexes = np.full((24, 30), -1, dtype=np.int32)
    # A broad region with a transparent hole.
    indexes[2:22, 2:20] = 0
    indexes[8:15, 8:14] = -1
    # A disconnected diagonal component and a different-color neighbor.
    for offset in range(5):
        indexes[4 + offset, 23 + offset] = 1
    indexes[:, 29] = 2

    plan = build_interior_fill_plan(
        indexes,
        max_brush_value=8,
        brush_scale_x=scale_x,
        brush_scale_y=scale_y,
    )
    independently_covered: set[tuple[int, int]] = set()

    for stroke in plan["strokes"]:
        color = stroke["color_index"]
        brush = stroke["brush_value"]
        first, last = stroke["points"]
        footprint = _independent_footprint_pixels(
            indexes.shape,
            int(first["x"]),
            int(last["x"]),
            int(first["y"]),
            brush,
            scale_x,
            scale_y,
        )
        for py, px in footprint:
            assert indexes[py, px] == color, (
                f"scale=({scale_x}, {scale_y}), stroke={stroke}, "
                f"foreign pixel at ({px}, {py}) has index {indexes[py, px]}"
            )
        independently_covered.update(footprint)

    expected_visible = {
        (int(py), int(px))
        for py, px in zip(*np.where(indexes >= 0))
    }
    assert expected_visible <= independently_covered
    assert plan["summary"]["coverage_percent"] == 100.0



def test_checkerboard_stress_case_keeps_isolated_multicolor_pixels_separate():
    # Every visible pixel is isolated from its neighbours; no wide brush may
    # bridge colors, and transparent cells must remain untouched.
    height, width = 13, 17
    yy, xx = np.indices((height, width))
    indexes = ((xx + yy) % 4).astype(np.int32)
    indexes[(xx * 3 + yy * 5) % 7 == 0] = -1

    plan = build_interior_fill_plan(indexes, max_brush_value=8)
    independently_covered: set[tuple[int, int]] = set()

    for stroke in plan["strokes"]:
        assert stroke["role"] == "boundary_fallback"
        assert stroke["brush_value"] == 1
        color = stroke["color_index"]
        first, last = stroke["points"]
        footprint = _independent_footprint_pixels(
            indexes.shape,
            int(first["x"]),
            int(last["x"]),
            int(first["y"]),
            int(stroke["brush_value"]),
        )
        for py, px in footprint:
            assert indexes[py, px] == color
        independently_covered.update(footprint)

    expected_visible = {
        (int(py), int(px))
        for py, px in zip(*np.where(indexes >= 0))
    }
    expected_transparent = {
        (int(py), int(px))
        for py, px in zip(*np.where(indexes < 0))
    }
    assert expected_visible == independently_covered
    assert expected_transparent.isdisjoint(independently_covered)
    assert plan["summary"]["coverage_percent"] == 100.0


def test_fallback_runs_merge_across_short_same_color_covered_gaps_only():
    indexes = np.zeros((1, 9), dtype=np.int32)
    covered = np.array([[False, True, True, False, True, True, True, False, False]])

    runs = list(_iter_fallback_runs(indexes, covered, 0, max_merge_gap=2))

    # The first two uncovered runs are joined across two same-color pixels;
    # a three-pixel covered gap is too wide, so the final run stays separate.
    assert runs == [(0, 0, 4), (0, 7, 9)]


def test_fallback_merge_never_bridges_different_color_or_transparency():
    indexes = np.array([[0, 0, 1, 0, 0, -1, 0, 0]], dtype=np.int32)
    covered = np.array([[False, True, True, False, False, True, False, False]])

    runs = list(_iter_fallback_runs(indexes, covered, 0, max_merge_gap=3))

    # The first run must stop before the foreign-color pixel at x=2,
    # even though the preceding covered pixel at x=1 has the same color.
    assert runs == [(0, 0, 1), (0, 3, 5), (0, 6, 8)]
