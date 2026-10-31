from __future__ import annotations

import pytest

from brush_coordinate_transform import transform_logical_brush_plan_to_screen


def make_plan():
    return {
        "coordinate_system": "logical_board_pixels",
        "canvas": {"width": 420, "height": 240},
        "strokes": [{
            "name": "edge",
            "points": [{"x": 0, "y": 0}, {"x": 210, "y": 120}, {"x": 420, "y": 240}],
            "closed": False,
            "metadata": {},
        }],
        "generation": {},
    }


def test_logical_bounds_map_to_screen_pixel_centers():
    result, info = transform_logical_brush_plan_to_screen(
        make_plan(), {"x": 100, "y": 80, "width": 646, "height": 323}
    )
    points = result["strokes"][0]["points"]
    assert points[0] == {"x": 0.0, "y": 0.0}
    assert points[-1] == {"x": 645.0, "y": 322.0}
    assert points[1]["x"] == pytest.approx(322.5)
    assert points[1]["y"] == pytest.approx(161.0)
    assert result["canvas"] == {"width": 646, "height": 323}
    assert result["coordinate_system"] == "local_canvas_pixels"
    assert info["scale_x"] == pytest.approx(645 / 420)
    assert info["scale_y"] == pytest.approx(322 / 240)


def test_source_plan_is_not_mutated_and_transform_is_recorded():
    plan = make_plan()
    before = plan["strokes"][0]["points"][1].copy()
    result, info = transform_logical_brush_plan_to_screen(
        plan, {"x": 0, "y": 0, "width": 421, "height": 241}
    )
    assert plan["strokes"][0]["points"][1] == before
    assert result["generation"]["screen_transform"] == info
    assert result["generation"]["source_canvas"] == {"width": 420, "height": 240}


def test_transform_rejects_wrong_coordinate_system():
    plan = make_plan()
    plan["coordinate_system"] = "local_canvas_pixels"
    with pytest.raises(ValueError, match="только для logical_board_pixels"):
        transform_logical_brush_plan_to_screen(
            plan, {"x": 0, "y": 0, "width": 646, "height": 323}
        )


def test_transform_rejects_invalid_roi_and_points():
    plan = make_plan()
    with pytest.raises(ValueError, match="не меньше 2×2"):
        transform_logical_brush_plan_to_screen(
            plan, {"x": 0, "y": 0, "width": 1, "height": 323}
        )
    plan["strokes"][0]["points"][0]["x"] = 421
    with pytest.raises(ValueError, match="выходит за границы"):
        transform_logical_brush_plan_to_screen(
            plan, {"x": 0, "y": 0, "width": 646, "height": 323}
        )
