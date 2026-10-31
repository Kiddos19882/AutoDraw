from __future__ import annotations

import pytest

from brush_coordinate_transform import transform_logical_brush_plan_to_screen


def make_plan():
    return {
        "coordinate_system": "logical_board_pixels",
        "canvas": {"width": 460, "height": 240},
        "strokes": [{
            "name": "edge",
            "points": [{"x": 0, "y": 0}, {"x": 210, "y": 120}, {"x": 460, "y": 240}],
            "closed": False,
            "metadata": {},
        }],
        "generation": {},
    }


def test_logical_bounds_map_to_screen_pixel_centers():
    result, info = transform_logical_brush_plan_to_screen(
        make_plan(), {"x": 100, "y": 80, "width": 646, "height": 338}
    )
    points = result["strokes"][0]["points"]
    assert points[0] == {"x": 0.0, "y": 0.0}
    assert points[-1] == {"x": 645.0, "y": 337.0}
    assert points[1]["x"] == pytest.approx(210 * 645 / 460)
    assert points[1]["y"] == pytest.approx(168.5)
    assert result["canvas"] == {"width": 646, "height": 338}
    assert result["coordinate_system"] == "local_canvas_pixels"
    assert info["scale_x"] == pytest.approx(645 / 460)
    assert info["scale_y"] == pytest.approx(337 / 240)
    assert info["point_step_px_units"] == "screen_pixels"


def test_source_plan_is_not_mutated_and_transform_is_recorded():
    plan = make_plan()
    before = plan["strokes"][0]["points"][1].copy()
    result, info = transform_logical_brush_plan_to_screen(
        plan, {"x": 0, "y": 0, "width": 461, "height": 241}
    )
    assert plan["strokes"][0]["points"][1] == before
    assert result["generation"]["screen_transform"] == info
    assert result["generation"]["source_canvas"] == {"width": 460, "height": 240}


def test_transform_rejects_wrong_coordinate_system():
    plan = make_plan()
    plan["coordinate_system"] = "local_canvas_pixels"
    with pytest.raises(ValueError, match="только для logical_board_pixels"):
        transform_logical_brush_plan_to_screen(
            plan, {"x": 0, "y": 0, "width": 646, "height": 338}
        )


def test_transform_rejects_nonuniform_roi_for_uniform_game_scale():
    with pytest.raises(ValueError, match="не соответствуют равномерному масштабу"):
        transform_logical_brush_plan_to_screen(
            make_plan(), {"x": 0, "y": 0, "width": 646, "height": 338}
        )


def test_transform_rejects_invalid_roi_and_points():
    plan = make_plan()
    with pytest.raises(ValueError, match="не меньше 2×2"):
        transform_logical_brush_plan_to_screen(
            plan, {"x": 0, "y": 0, "width": 1, "height": 323}
        )
    plan["strokes"][0]["points"][0]["x"] = 461
    with pytest.raises(ValueError, match="выходит за границы"):
        transform_logical_brush_plan_to_screen(
            plan, {"x": 0, "y": 0, "width": 646, "height": 323}
        )
