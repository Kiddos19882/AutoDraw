from __future__ import annotations

import numpy as np
import pytest
import geometry_color_plan as geometry_module
import geometry_budget_optimizer as budget_module

from geometry_color_plan import (
    GeometryColorPlanError,
    _zhang_suen_thinning,
    build_geometry_color_plan,
    load_geometry_color_plan,
    save_geometry_color_plan,
    optimize_geometry_plan_to_budget,
    render_geometry_color_preview,
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


import stroke_order_optimizer as routing_module
from stroke_order_optimizer import orient_and_order_strokes
from geometry_budget_optimizer import _rescale_map_centered
from geometry_budget_optimizer import (
    measure_geometry_plan_quality,
    optimize_geometry_plan_across_modes,
)


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
    # Fill the first physical board to its 660 px width, then use a 40 px remainder.
    assert [board["tile"]["x"] for board in manifest["boards"]] == [0, 660]
    assert [board["tile"]["width"] for board in manifest["boards"]] == [660, 40]
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


def test_exact_scanline_render_has_full_pixel_accuracy():
    index_map = _map()
    plan = build_geometry_color_plan(index_map, PALETTE, mode="scanline")

    quality = measure_geometry_plan_quality(index_map, plan)

    assert quality["quality_mismatch_pixel_count"] == 0
    assert quality["quality_pixel_accuracy_percent"] == 100.0
    assert quality["quality_visible_pixel_accuracy_percent"] == 100.0
    assert quality["quality_is_preview_estimate"] is True
    assert quality["quality_measure_scope"] == "programmatic_preview"
    assert "браузерной игре" in quality["quality_measure_note"]


def test_automatic_optimizer_compares_all_modes_and_prefers_exact_render():
    index_map = _map()

    plan, report = optimize_geometry_plan_across_modes(
        index_map,
        PALETTE,
        paint_budget_px_equivalent=100_000,
        target_usage_percent=90,
        stroke_overhead_px_equivalent=6.67,
        simplify_tolerance_px=0.8,
    )

    assert validate_geometry_color_plan(plan) is plan
    assert report["requested_mode"] == "automatic"
    assert report["mode"] == "scanline"
    assert report["fits_budget"] is True
    assert report["quality_pixel_accuracy_percent"] == 100.0
    assert {item["mode"] for item in report["mode_candidates"]} == {
        "scanline", "contour", "skeleton"
    }


def test_pixel_fidelity_accounts_for_executor_single_pixel_drag():
    index_map = np.full((9, 9), -1, dtype=np.int32)
    index_map[4, 4] = 0
    plan = build_geometry_color_plan(index_map, PALETTE, mode="scanline")

    quality = measure_geometry_plan_quality(index_map, plan)

    # The executor converts a click into a short horizontal drag, painting one
    # extra board pixel when that pixel is inside the canvas.
    assert quality["quality_mismatch_pixel_count"] == 1
    assert quality["quality_exact_visible_pixel_count"] == 1


def test_optimizer_can_recover_when_unoptimized_source_exceeds_stroke_cap(monkeypatch):
    index_map = np.array([[0, 1, 0, 1]], dtype=np.int32)
    monkeypatch.setattr(geometry_module, "MAX_GEOMETRY_STROKES", 1)

    plan, report = optimize_geometry_plan_to_budget(
        index_map,
        PALETTE,
        mode="scanline",
        paint_budget_px_equivalent=1_000,
        target_usage_percent=90,
        stroke_overhead_px_equivalent=1,
    )

    assert validate_geometry_color_plan(plan) is plan
    assert report["baseline_plan_available"] is False
    assert report["scale"] < 1.0
    assert report["fits_budget"] is True


def test_geometry_plan_json_round_trip(tmp_path):
    plan = build_geometry_color_plan(_map(), PALETTE, mode="contour")
    path = tmp_path / "geometry-plan.json"

    saved_path = save_geometry_color_plan(path, plan)
    loaded = load_geometry_color_plan(saved_path)

    assert loaded["plan_type"] == "autodraw_geometry_color_plan"
    assert loaded["summary"]["stroke_count"] == plan["summary"]["stroke_count"]
    assert loaded["strokes"] == plan["strokes"]


def test_scanline_component_filtering_respects_minimum_component_area():
    indexes = np.full((8, 8), -1, dtype=np.int32)
    indexes[1:4, 1:4] = 0
    indexes[6, 6] = 1

    plan = build_geometry_color_plan(
        indexes, PALETTE, mode="scanline", min_component_area=2
    )

    assert plan["summary"]["source_visible_pixel_count"] == 10
    assert plan["summary"]["retained_visible_pixel_count"] == 9
    assert plan["generation"]["removed_component_pixel_count"] == 1
    assert {stroke["color"]["palette_index"] for stroke in plan["strokes"]} == {0}


def test_optimizer_never_uses_component_threshold_below_user_setting():
    indexes = np.full((16, 16), -1, dtype=np.int32)
    indexes[2:14, 2:14] = 0
    indexes[0, 0] = 1

    plan, report = optimize_geometry_plan_to_budget(
        indexes,
        PALETTE,
        mode="scanline",
        paint_budget_px_equivalent=10_000,
        target_usage_percent=90,
        min_component_area=4,
    )

    assert validate_geometry_color_plan(plan) is plan
    assert report["min_component_area"] >= 4
    assert plan["generation"]["min_component_area"] >= 4
    assert plan["summary"]["retained_visible_pixel_count"] <= (
        plan["summary"]["source_visible_pixel_count"]
    )


def test_skeleton_tracing_visits_a_closed_loop_once():
    skeleton = np.zeros((7, 7), dtype=np.uint8)
    skeleton[1, 1:6] = 1
    skeleton[5, 1:6] = 1
    skeleton[1:6, 1] = 1
    skeleton[1:6, 5] = 1

    paths = trace_skeleton_paths(skeleton)

    assert len(paths) == 1
    points, closed = paths[0]
    assert closed is True
    assert len(points) == 16
    assert len(set(points)) == 16


def test_skeleton_tracing_splits_a_junction_without_losing_edges():
    skeleton = np.zeros((7, 7), dtype=np.uint8)
    skeleton[3, 1:6] = 1
    skeleton[1:6, 3] = 1

    paths = trace_skeleton_paths(skeleton)

    assert len(paths) == 4
    assert all(closed is False for _points, closed in paths)
    assert sum(len(points) - 1 for points, _closed in paths) == 8
    assert all(points[0] == (3.0, 3.0) or points[-1] == (3.0, 3.0) for points, _closed in paths)


def test_multiboard_split_reconstructs_scanline_pixels_across_board_seam():
    index_map = np.full((20, 700), -1, dtype=np.int32)
    index_map[5, :] = 0
    plan = build_geometry_color_plan(index_map, PALETTE, mode="scanline")

    manifest = split_geometry_plan_to_boards(
        plan,
        paint_budget_px_equivalent=25_650,
        target_usage_percent=75,
        min_tile_size=8,
        max_boards=4,
        board_width=660,
        board_height=340,
    )

    assembled = np.zeros((20, 700, 4), dtype=np.uint8)
    for board in manifest["boards"]:
        tile = board["tile"]
        preview = np.asarray(
            render_geometry_color_preview(board["plan"], max_dimension=660).crop(
                (0, 0, tile["width"], tile["height"])
            )
        )
        destination = assembled[
            tile["y"]:tile["y"] + tile["height"],
            tile["x"]:tile["x"] + tile["width"],
        ]
        visible = preview[:, :, 3] > 0
        destination[visible] = preview[visible]

    expected = np.asarray(render_geometry_color_preview(plan, max_dimension=700))
    assert manifest["board_count"] == 2
    # Transparent pixels may carry different, irrelevant RGB values; compare
    # the alpha mask everywhere and exact RGB values on every painted pixel.
    assert np.array_equal(assembled[:, :, 3], expected[:, :, 3])
    visible_pixels = expected[:, :, 3] > 0
    assert np.array_equal(assembled[visible_pixels, :3], expected[visible_pixels, :3])


def test_large_color_batch_uses_bounded_work_in_stroke_router(monkeypatch):
    distance_calls = 0
    original_distance = routing_module._point_distance

    def counted_distance(first, second):
        nonlocal distance_calls
        distance_calls += 1
        return original_distance(first, second)

    monkeypatch.setattr(routing_module, "_point_distance", counted_distance)
    strokes = [
        _route_stroke(0, float(index * 3), float(index * 3 + 1))
        for index in range(1_000)
    ]

    ordered = orient_and_order_strokes(strokes, color_grouping=True)

    assert len(ordered) == len(strokes)
    assert distance_calls < 10_000


def test_disabled_color_grouping_returns_without_routing_work(monkeypatch):
    strokes = [
        _route_stroke(0, 0.0, 1.0),
        _route_stroke(1, 10.0, 11.0),
        _route_stroke(0, 2.0, 3.0),
    ]

    def unexpected_distance_call(_first, _second):
        raise AssertionError("Роутер не должен вычислять расстояния при отключённой группировке.")

    monkeypatch.setattr(routing_module, "_point_distance", unexpected_distance_call)

    assert orient_and_order_strokes(strokes, color_grouping=False) is strokes


def test_multiboard_split_reconstructs_closed_contour_crossing_board_seam():
    index_map = np.full((24, 700), -1, dtype=np.int32)
    index_map[3:20, 630:681] = 0
    plan = build_geometry_color_plan(
        index_map, PALETTE, mode="contour", simplify_tolerance_px=0
    )

    manifest = split_geometry_plan_to_boards(
        plan,
        paint_budget_px_equivalent=25_650,
        target_usage_percent=75,
        min_tile_size=8,
        max_boards=4,
        board_width=660,
        board_height=340,
    )

    assembled = np.zeros((24, 700, 4), dtype=np.uint8)
    for board in manifest["boards"]:
        tile = board["tile"]
        preview = np.asarray(
            render_geometry_color_preview(board["plan"], max_dimension=660).crop(
                (0, 0, tile["width"], tile["height"])
            )
        )
        destination = assembled[
            tile["y"]:tile["y"] + tile["height"],
            tile["x"]:tile["x"] + tile["width"],
        ]
        visible = preview[:, :, 3] > 0
        destination[visible] = preview[visible]

    expected = np.asarray(render_geometry_color_preview(plan, max_dimension=700))
    assert manifest["board_count"] == 2
    assert np.array_equal(assembled[:, :, 3], expected[:, :, 3])
    visible_pixels = expected[:, :, 3] > 0
    assert np.array_equal(assembled[visible_pixels, :3], expected[visible_pixels, :3])


@pytest.mark.parametrize("canvas_size", [(32.5, 32), (True, 32), ("32", 32)])
def test_builder_rejects_non_integer_canvas_dimensions(canvas_size):
    with pytest.raises(GeometryColorPlanError):
        build_geometry_color_plan(
            _map(), PALETTE, mode="scanline", canvas_size=canvas_size
        )


@pytest.mark.parametrize("palette_index", [0.5, "0", True])
def test_validator_rejects_non_integer_palette_indexes(palette_index):
    plan = build_geometry_color_plan(_map(), PALETTE, mode="scanline")
    plan["strokes"][0]["color"]["palette_index"] = palette_index

    with pytest.raises(GeometryColorPlanError):
        validate_geometry_color_plan(plan)


def test_multiboard_split_reconstructs_diagonal_strokes_crossing_board_seam():
    index_map = np.full((40, 700), -1, dtype=np.int32)
    for x in range(642, 679):
        y = 1 + (x - 642)
        index_map[y, x] = 0
    plan = build_geometry_color_plan(
        index_map, PALETTE, mode="contour", simplify_tolerance_px=0
    )

    manifest = split_geometry_plan_to_boards(
        plan,
        paint_budget_px_equivalent=25_650,
        target_usage_percent=75,
        min_tile_size=8,
        max_boards=4,
        board_width=660,
        board_height=340,
    )

    assembled = np.zeros((40, 700, 4), dtype=np.uint8)
    for board in manifest["boards"]:
        tile = board["tile"]
        preview = np.asarray(
            render_geometry_color_preview(board["plan"], max_dimension=660).crop(
                (0, 0, tile["width"], tile["height"])
            )
        )
        destination = assembled[
            tile["y"]:tile["y"] + tile["height"],
            tile["x"]:tile["x"] + tile["width"],
        ]
        visible = preview[:, :, 3] > 0
        destination[visible] = preview[visible]

    expected = np.asarray(render_geometry_color_preview(plan, max_dimension=700))
    assert manifest["board_count"] == 2
    assert np.array_equal(assembled[:, :, 3], expected[:, :, 3])
    visible_pixels = expected[:, :, 3] > 0
    assert np.array_equal(assembled[visible_pixels, :3], expected[visible_pixels, :3])


@pytest.mark.parametrize(
    ("axis", "value"),
    [
        ("x", True),
        ("y", False),
        ("x", "1"),
        ("y", "2.5"),
        ("x", float("nan")),
        ("y", float("inf")),
    ],
)
def test_validator_rejects_non_numeric_or_non_finite_coordinates(axis, value):
    plan = build_geometry_color_plan(_map(), PALETTE, mode="scanline")
    plan["strokes"][0]["points"][0][axis] = value

    with pytest.raises(GeometryColorPlanError):
        validate_geometry_color_plan(plan)



def test_multiboard_split_preserves_a_real_single_pixel_stroke():
    index_map = np.full((20, 700), -1, dtype=np.int32)
    index_map[5, 660] = 0
    plan = build_geometry_color_plan(index_map, PALETTE, mode="scanline")

    manifest = split_geometry_plan_to_boards(
        plan,
        paint_budget_px_equivalent=25_650,
        target_usage_percent=75,
        min_tile_size=8,
        max_boards=4,
        board_width=660,
        board_height=340,
    )

    # The empty left tile is intentionally omitted from the manifest.
    assert manifest["board_count"] == 1
    right_board = manifest["boards"][0]
    assert right_board["tile"]["x"] == 660
    singleton_strokes = [
        stroke for stroke in right_board["plan"]["strokes"]
        if stroke["points"][0] == stroke["points"][1]
    ]
    assert len(singleton_strokes) == 1
    assert singleton_strokes[0]["points"][0] == {"x": 0.0, "y": 5.0}



def test_quality_measure_rejects_fractional_palette_index_map():
    plan = build_geometry_color_plan(_map(), PALETTE, mode="scanline")
    invalid_map = _map().astype(np.float32)
    invalid_map[0, 0] = 0.5

    with pytest.raises(GeometryColorPlanError):
        measure_geometry_plan_quality(invalid_map, plan)


def test_quality_measure_rejects_out_of_range_palette_indexes():
    plan = build_geometry_color_plan(_map(), PALETTE, mode="scanline")
    invalid_map = _map().copy()
    invalid_map[0, 0] = len(PALETTE)

    with pytest.raises(GeometryColorPlanError):
        measure_geometry_plan_quality(invalid_map, plan)


def test_automatic_optimizer_uses_precise_cost_when_no_mode_fits(monkeypatch):
    costs = {
        "scanline": (100.9, 0),
        "contour": (100.1, 99),
        "skeleton": (100.5, 3),
    }

    def fake_optimize(
        index_map,
        palette,
        *,
        mode,
        paint_budget_px_equivalent,
        target_usage_percent=75.0,
        stroke_overhead_px_equivalent=6.67,
        simplify_tolerance_px=0.8,
        min_component_area=1,
        source_name=None,
    ):
        plan = build_geometry_color_plan(index_map, palette, mode=mode)
        cost, mismatches = costs[mode]
        return plan, {
            "mode": mode,
            "fits_budget": False,
            "needs_multi_board_split": True,
            "scale": 1.0,
            "estimated_ink_after_px_equivalent": cost,
            "quality_mismatch_pixel_count": mismatches,
            "quality_pixel_accuracy_percent": 0.0,
        }

    monkeypatch.setattr(budget_module, "optimize_geometry_plan_to_budget", fake_optimize)

    plan, report = optimize_geometry_plan_across_modes(
        _map(),
        PALETTE,
        paint_budget_px_equivalent=1,
        target_usage_percent=75,
    )

    assert report["mode"] == "contour"
    assert report["estimated_ink_after_px_equivalent"] == pytest.approx(100.1)
    assert report["fits_budget"] is False
    assert report["needs_multi_board_split"] is True
    assert plan["generation"]["mode"] == "contour"
