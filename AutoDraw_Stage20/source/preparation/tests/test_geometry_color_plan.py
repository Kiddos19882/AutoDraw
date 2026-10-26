from __future__ import annotations

import numpy as np
import pytest

from geometry_color_plan import (
    GeometryColorPlanError,
    _zhang_suen_thinning,
    build_geometry_color_plan,
    optimize_geometry_plan_to_budget,
    split_geometry_plan_to_boards,
    validate_geometry_color_plan,
)


PALETTE = [
    {"id": "black", "name": "Black", "rgb": [0, 0, 0], "hex": "#000000"},
    {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
]


def _map() -> np.ndarray:
    image = np.full((32, 32), -1, dtype=np.int32)
    image[5:27, 5:27] = 0
    image[10:22, 10:22] = 1
    return image


def test_scanline_plan_preserves_color_runs_and_has_cost_estimate():
    plan = build_geometry_color_plan(_map(), PALETTE, mode="scanline")
    assert plan["plan_type"] == "autodraw_geometry_color_plan"
    assert plan["summary"]["stroke_count"] > 0
    assert plan["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"] > 0
    assert validate_geometry_color_plan(plan) is plan


def test_contour_plan_uses_rdp_and_keeps_paths_inside_canvas():
    plan = build_geometry_color_plan(_map(), PALETTE, mode="contour", simplify_tolerance_px=1.0)
    assert plan["generation"]["simplification"].startswith("Ramer-Douglas-Peucker")
    assert plan["summary"]["stroke_count"] > 0
    for stroke in plan["strokes"]:
        assert len(stroke["points"]) >= 2
        for point in stroke["points"]:
            assert 0 <= point["x"] < 32
            assert 0 <= point["y"] < 32


def test_skeletonization_reduces_thick_stroke_to_centerline():
    mask = np.zeros((21, 21), dtype=np.uint8)
    mask[8:13, 3:18] = 1
    skeleton = _zhang_suen_thinning(mask)
    assert 0 < int(skeleton.sum()) < int(mask.sum())
    assert np.all(skeleton[0, :] == 0)
    assert np.all(skeleton[-1, :] == 0)


def test_budget_optimizer_returns_a_valid_plan_and_report():
    plan, report = optimize_geometry_plan_to_budget(
        _map(), PALETTE,
        mode="contour",
        paint_budget_px_equivalent=25_650,
        target_usage_percent=75,
    )
    assert validate_geometry_color_plan(plan) is plan
    assert report["estimated_ink_after_px_equivalent"] > 0
    assert report["target_cost_px_equivalent"] == 19_237.5


def test_multiboard_split_has_manifest_and_tile_metadata():
    plan = build_geometry_color_plan(_map(), PALETTE, mode="contour")
    manifest = split_geometry_plan_to_boards(
        plan,
        paint_budget_px_equivalent=25_650,
        target_usage_percent=75,
        min_tile_size=8,
        max_boards=64,
    )
    assert manifest["plan_type"] == "autodraw_multi_board_manifest"
    assert manifest["board_count"] >= 1
    for board in manifest["boards"]:
        assert board["tile"]["width"] > 0
        assert board["tile"]["height"] > 0
        assert board["plan"]["generation"]["tile"] == board["tile"]


def test_invalid_mode_is_rejected():
    with pytest.raises(GeometryColorPlanError):
        build_geometry_color_plan(_map(), PALETTE, mode="magic")


def test_skeletonization_preserves_isolated_single_pixel():
    indexes = np.full((9, 9), -1, dtype=np.int32)
    indexes[4, 4] = 0

    plan = build_geometry_color_plan(
        indexes, PALETTE, mode="skeleton", simplify_tolerance_px=0
    )

    assert plan["summary"]["source_visible_pixel_count"] == 1
    assert plan["summary"]["retained_visible_pixel_count"] == 1
    assert plan["summary"]["stroke_count"] == 1
    assert plan["summary"]["single_pixel_stroke_count"] == 1
    point_a, point_b = plan["strokes"][0]["points"]
    assert point_a == point_b


def test_contour_mode_preserves_isolated_single_pixel():
    indexes = np.full((9, 9), -1, dtype=np.int32)
    indexes[4, 4] = 0

    plan = build_geometry_color_plan(
        indexes, PALETTE, mode="contour", simplify_tolerance_px=0
    )

    assert plan["summary"]["stroke_count"] == 1
    assert plan["summary"]["single_pixel_stroke_count"] == 1
    assert plan["strokes"][0]["metadata"]["path_type"] == "contour-point"


def test_summary_reports_pixels_retained_after_component_filtering():
    indexes = np.full((8, 8), -1, dtype=np.int32)
    indexes[1:4, 1:4] = 0  # Nine connected black pixels.
    indexes[6, 6] = 1      # A single red pixel, removed by min_component_area=2.

    plan = build_geometry_color_plan(
        indexes, PALETTE, mode="contour", min_component_area=2
    )

    summary = plan["summary"]
    assert summary["source_visible_pixel_count"] == 10
    assert summary["visible_pixel_count"] == 9
    assert summary["retained_visible_pixel_count"] == 9
    assert plan["generation"]["removed_component_pixel_count"] == 1
    assert summary["used_colors"][0]["palette_index"] == 0
    assert summary["used_colors"][0]["pixel_count"] == 9
    assert summary["used_colors"][0]["percentage_visible"] == 100.0


def test_geometry_cost_accounts_for_executed_single_pixel_length():
    indexes = np.full((9, 9), -1, dtype=np.int32)
    indexes[4, 4] = 0
    plan = build_geometry_color_plan(
        indexes, PALETTE, mode="skeleton", simplify_tolerance_px=0
    )

    estimate = plan["summary"]["paint_cost_estimate"]
    assert estimate["single_pixel_stroke_count"] == 1
    assert estimate["single_pixel_extra_path_px"] == 1.0
    assert estimate["estimated_total_ink_px_equivalent"] == pytest.approx(7.67, abs=0.01)


def test_optimizer_uses_requested_cost_model_for_before_report():
    indexes = np.full((8, 8), -1, dtype=np.int32)
    indexes[2:6, 1:7] = 0

    baseline = build_geometry_color_plan(
        indexes, PALETTE, mode="scanline", simplify_tolerance_px=0
    )
    estimate = baseline["summary"]["drawing_length_px"] + (
        baseline["summary"]["single_pixel_stroke_count"] * 1.0
    ) + baseline["summary"]["stroke_count"] * 20.0

    _plan, report = optimize_geometry_plan_to_budget(
        indexes,
        PALETTE,
        mode="scanline",
        paint_budget_px_equivalent=10_000,
        stroke_overhead_px_equivalent=20,
        target_usage_percent=90,
    )

    assert report["estimated_ink_before_px_equivalent"] == pytest.approx(estimate)


from layer_segmentation import LayerSegmentationError, filter_small_components
from skeletonization import SkeletonizationError, trace_skeleton_paths
from stroke_simplification import simplify_path


def test_layer_segmentation_removes_only_components_below_threshold():
    mask = np.zeros((10, 10), dtype=np.uint8)
    mask[1:4, 1:4] = 1
    mask[7, 7] = 1

    filtered, removed = filter_small_components(mask, min_component_area=2)

    assert int(filtered.sum()) == 9
    assert removed == 1
    assert filtered[2, 2] == 1
    assert filtered[7, 7] == 0


def test_layer_segmentation_uses_eight_connected_components():
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[1, 1] = 1
    mask[2, 2] = 1

    filtered, removed = filter_small_components(mask, min_component_area=2)

    assert int(filtered.sum()) == 2
    assert removed == 0


def test_layer_segmentation_rejects_invalid_inputs():
    with pytest.raises(LayerSegmentationError):
        filter_small_components(np.zeros((2, 2)), min_component_area=0)
    with pytest.raises(LayerSegmentationError):
        filter_small_components(np.zeros((2, 2, 1)), min_component_area=1)


def test_skeleton_path_tracing_visits_a_straight_line_from_end_to_end():
    skeleton = np.zeros((5, 8), dtype=np.uint8)
    skeleton[2, 1:6] = 1

    paths = trace_skeleton_paths(skeleton)

    assert len(paths) == 1
    points, closed = paths[0]
    assert closed is False
    assert set(points) == {(float(x), 2.0) for x in range(1, 6)}


def test_skeleton_path_tracing_keeps_an_isolated_pixel():
    skeleton = np.zeros((5, 5), dtype=np.uint8)
    skeleton[3, 2] = 1

    paths = trace_skeleton_paths(skeleton)

    assert paths == [([(2.0, 3.0)], False)]


def test_skeleton_path_tracing_rejects_non_2d_input():
    with pytest.raises(SkeletonizationError):
        trace_skeleton_paths(np.zeros((3, 3, 1), dtype=np.uint8))


def test_rdp_does_not_simplify_through_another_color_layer():
    points = [(1.0, 1.0), (1.0, 5.0), (5.0, 5.0), (5.0, 1.0)]
    safe_mask = np.zeros((7, 7), dtype=np.uint8)
    safe_mask[1:6, 1] = 1
    safe_mask[5, 1:6] = 1
    safe_mask[1:6, 5] = 1

    result = simplify_path(
        points,
        closed=False,
        tolerance_px=10.0,
        safe_mask=safe_mask,
    )

    assert result == points


from stroke_order_optimizer import orient_and_order_strokes
from geometry_budget_optimizer import _rescale_map_centered


def _route_stroke(color_index: int, first_x: float, last_x: float) -> dict:
    return {
        "name": f"color-{color_index}-{first_x}-{last_x}",
        "points": [{"x": first_x, "y": 2.0}, {"x": last_x, "y": 2.0}],
        "closed": False,
        "color": {"palette_index": color_index},
    }


def test_stroke_router_groups_each_marker_into_one_batch():
    strokes = [
        _route_stroke(0, 0.0, 1.0),
        _route_stroke(1, 20.0, 21.0),
        _route_stroke(0, 2.0, 3.0),
    ]

    ordered = orient_and_order_strokes(strokes, color_grouping=True)
    colors = [stroke["color"]["palette_index"] for stroke in ordered]
    switches = sum(first != second for first, second in zip(colors, colors[1:]))

    assert colors == [0, 0, 1]
    assert switches == 1


def test_stroke_router_reverses_open_paths_to_reduce_pen_up_distance():
    strokes = [
        _route_stroke(0, 0.0, 10.0),
        _route_stroke(0, 12.0, 11.0),
    ]

    ordered = orient_and_order_strokes(strokes, color_grouping=True)

    assert ordered[1]["points"][0]["x"] == 11.0
    assert ordered[1]["points"][-1]["x"] == 12.0


def test_stroke_router_preserves_input_order_when_grouping_is_disabled():
    strokes = [
        _route_stroke(0, 0.0, 1.0),
        _route_stroke(1, 10.0, 11.0),
        _route_stroke(0, 2.0, 3.0),
    ]

    ordered = orient_and_order_strokes(strokes, color_grouping=False)

    assert ordered == strokes


def test_multiboard_split_clips_a_path_to_physical_board_tiles():
    indexes = np.full((20, 700), -1, dtype=np.int32)
    indexes[5, :] = 0
    plan = build_geometry_color_plan(indexes, PALETTE, mode="scanline")

    manifest = split_geometry_plan_to_boards(
        plan,
        paint_budget_px_equivalent=25_650,
        target_usage_percent=75,
        min_tile_size=8,
        max_boards=4,
        board_width=660,
        board_height=340,
    )

    assert manifest["board_count"] == 2
    assert [board["tile"]["x"] for board in manifest["boards"]] == [0, 350]
    for board in manifest["boards"]:
        tile_plan = board["plan"]
        assert tile_plan["canvas"] == {"width": 660, "height": 340}
        assert board["fits_budget"] is True
        for stroke in tile_plan["strokes"]:
            for point in stroke["points"]:
                assert 0 <= point["x"] < 660
                assert 0 <= point["y"] < 340


def test_multiboard_split_rejects_non_integer_board_size():
    plan = build_geometry_color_plan(_map(), PALETTE, mode="contour")

    with pytest.raises(GeometryColorPlanError):
        split_geometry_plan_to_boards(
            plan,
            paint_budget_px_equivalent=25_650,
            board_width=660.5,
        )


def test_multiboard_split_respects_maximum_board_count():
    indexes = np.full((20, 700), -1, dtype=np.int32)
    indexes[5, :] = 0
    plan = build_geometry_color_plan(indexes, PALETTE, mode="scanline")

    with pytest.raises(GeometryColorPlanError):
        split_geometry_plan_to_boards(
            plan,
            paint_budget_px_equivalent=25_650,
            max_boards=1,
            board_width=660,
            board_height=340,
        )


def test_two_pixel_contour_is_emitted_as_an_open_stroke():
    indexes = np.full((7, 7), -1, dtype=np.int32)
    indexes[3, 2:4] = 0

    plan = build_geometry_color_plan(
        indexes, PALETTE, mode="contour", simplify_tolerance_px=5
    )

    assert plan["summary"]["stroke_count"] == 1
    assert plan["strokes"][0]["closed"] is False
    assert plan["strokes"][0]["metadata"]["path_type"] == "contour-line"
    assert len(plan["strokes"][0]["points"]) >= 2


def test_validator_rejects_closed_path_with_fewer_than_three_distinct_points():
    indexes = np.full((7, 7), -1, dtype=np.int32)
    indexes[3, 2:4] = 0
    plan = build_geometry_color_plan(indexes, PALETTE, mode="contour")
    plan["strokes"][0]["closed"] = True

    with pytest.raises(GeometryColorPlanError):
        validate_geometry_color_plan(plan)


def test_budget_rescaling_preserves_canvas_occupancy():
    indexes = np.full((50, 60), -1, dtype=np.int32)
    indexes[5:45, 8:52] = 0

    resized = _rescale_map_centered(indexes, 0.5)

    assert resized.shape == indexes.shape
    ys, xs = np.where(resized >= 0)
    assert xs.min() <= 10
    assert xs.max() >= 49
    assert ys.min() <= 7
    assert ys.max() >= 42


def test_budget_rescaling_keeps_each_pixel_on_a_valid_palette_index():
    indexes = _map()

    resized = _rescale_map_centered(indexes, 0.4)

    assert resized.dtype.kind in "iu"
    assert int(resized.min()) >= -1
    assert int(resized.max()) < len(PALETTE)
