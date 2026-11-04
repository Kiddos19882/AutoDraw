from __future__ import annotations

import pytest

from chalk_fill_experiment import FILL001_RADII, FILL001_SHAPES, build_fill_target_mask
from chalk_fill_fixed_radius_planner import (
    FillPlannerError,
    build_fixed_radius_fill_plan,
    rasterize_fill_strokes,
)


@pytest.mark.parametrize("shape_id", FILL001_SHAPES)
@pytest.mark.parametrize("radius", FILL001_RADII)
def test_all_frozen_shape_radius_cells_pass_coverage_and_leakage_gate(shape_id, radius):
    plan = build_fixed_radius_fill_plan(shape_id, radius)

    assert plan["summary"]["coverage_fraction"] >= 0.99
    assert plan["summary"]["leakage_pixels"] == 0
    assert plan["summary"]["quality_gate_passed"] is True
    assert plan["summary"]["unsupported"] is False
    assert plan["summary"]["stroke_count"] > 0


@pytest.mark.parametrize("shape_id", FILL001_SHAPES)
@pytest.mark.parametrize("radius", FILL001_RADII)
def test_every_stroke_uses_one_fixed_radius_and_is_not_executor_ready(shape_id, radius):
    plan = build_fixed_radius_fill_plan(shape_id, radius)

    assert plan["radius"] == radius
    assert plan["brush_configuration"]["brush_value"] == radius
    assert all(stroke["brush_value"] == radius for stroke in plan["strokes"])
    assert all(stroke["safe_to_execute"] is False for stroke in plan["strokes"])
    assert plan["summary"]["ready_for_automatic_execution"] is False


@pytest.mark.parametrize("shape_id", FILL001_SHAPES)
@pytest.mark.parametrize("radius", FILL001_RADII)
def test_plan_signature_and_raster_metrics_are_deterministic(shape_id, radius):
    first = build_fixed_radius_fill_plan(shape_id, radius)
    second = build_fixed_radius_fill_plan(shape_id, radius)

    assert first["plan_signature"] == second["plan_signature"]
    assert first["target_mask_sha256"] == second["target_mask_sha256"]
    assert first["summary"] == second["summary"]


def test_sampling_estimate_is_not_reported_as_exact_chalk():
    plan = build_fixed_radius_fill_plan("rectangle", 10, sampling_step=4)

    assert plan["summary"]["estimated_sampling_points"] > 0
    assert plan["summary"]["estimated_sampling_points_are_exact_chalk"] is False


def test_rasterizer_rejects_a_stroke_with_a_different_radius():
    mask = build_fill_target_mask("rectangle")
    with pytest.raises(FillPlannerError):
        rasterize_fill_strokes(
            mask,
            [{
                "brush_value": 5,
                "points": [{"x": 100, "y": 100}, {"x": 200, "y": 100}],
            }],
            10,
        )


def test_unknown_shape_radius_and_invalid_sampling_step_are_rejected():
    with pytest.raises(FillPlannerError):
        build_fixed_radius_fill_plan("unknown", 10)
    with pytest.raises(FillPlannerError):
        build_fixed_radius_fill_plan("rectangle", 2)
    with pytest.raises(FillPlannerError):
        build_fixed_radius_fill_plan("rectangle", True)
    with pytest.raises(FillPlannerError):
        build_fixed_radius_fill_plan("rectangle", 10, sampling_step=0)


def test_rasterizer_rejects_out_of_canvas_and_non_integer_coordinates():
    mask = build_fill_target_mask("rectangle")
    with pytest.raises(FillPlannerError):
        rasterize_fill_strokes(
            mask,
            [{"brush_value": 10, "points": [{"x": -1, "y": 100}, {"x": 200, "y": 100}]}],
            10,
        )
    with pytest.raises(FillPlannerError):
        rasterize_fill_strokes(
            mask,
            [{"brush_value": 10, "points": [{"x": 10.5, "y": 100}, {"x": 200, "y": 100}]}],
            10,
        )


def test_default_scanline_spacing_keeps_legacy_planner_version_and_baseline_geometry():
    plan = build_fixed_radius_fill_plan("rectangle", 10)

    assert plan["planner_version"] == 1
    assert plan["brush_configuration"]["scanline_row_step"] == 1
    assert plan["brush_configuration"]["scanline_offset"] == 0
    assert plan["summary"]["stroke_count"] == 131
    assert plan["summary"]["path_length_logical_pixels"] == 40218.0
    assert plan["summary"]["estimated_sampling_points"] == 10237
    assert plan["summary"]["coverage_fraction"] == 1.0
    assert plan["summary"]["leakage_pixels"] == 0


def test_rs_scanline_spacing_is_versioned_and_reduces_rectangle_r10_passes():
    plan = build_fixed_radius_fill_plan(
        "rectangle", 10, scanline_row_step=5, scanline_offset=0
    )

    assert plan["planner_version"] == 2
    assert plan["plan_type"] == "autodraw_fill001_rs_fixed_radius_experimental"
    assert plan["brush_configuration"]["scanline_row_step"] == 5
    assert plan["brush_configuration"]["scanline_offset"] == 0
    assert plan["summary"]["stroke_count"] == 27
    assert plan["summary"]["coverage_fraction"] == pytest.approx(0.993192, abs=1e-6)
    assert plan["summary"]["uncovered_target_pixels"] == 304
    assert plan["summary"]["leakage_pixels"] == 0
    assert plan["summary"]["estimated_sampling_points_are_exact_chalk"] is False


def test_rs_scanline_offset_changes_plan_signature_and_geometry():
    first = build_fixed_radius_fill_plan(
        "narrow_irregular", 5, scanline_row_step=3, scanline_offset=0
    )
    second = build_fixed_radius_fill_plan(
        "narrow_irregular", 5, scanline_row_step=3, scanline_offset=1
    )

    assert first["plan_signature"] != second["plan_signature"]
    assert first["summary"]["coverage_fraction"] < 0.99
    assert second["summary"]["coverage_fraction"] >= 0.99
    assert second["summary"]["leakage_pixels"] == 0


def test_rs_scanline_parameters_reject_invalid_values():
    with pytest.raises(FillPlannerError):
        build_fixed_radius_fill_plan("rectangle", 10, scanline_row_step=0)
    with pytest.raises(FillPlannerError):
        build_fixed_radius_fill_plan("rectangle", 10, scanline_row_step=True)
    with pytest.raises(FillPlannerError):
        build_fixed_radius_fill_plan("rectangle", 10, scanline_row_step=5, scanline_offset=5)
    with pytest.raises(FillPlannerError):
        build_fixed_radius_fill_plan("rectangle", 10, scanline_row_step=5, scanline_offset=-1)
