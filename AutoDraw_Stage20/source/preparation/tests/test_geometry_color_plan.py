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
