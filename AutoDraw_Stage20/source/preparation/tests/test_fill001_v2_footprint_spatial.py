from __future__ import annotations

import numpy as np
import json
import tempfile
from pathlib import Path
import pytest

from fill001_v2_footprint_spatial import classify_leakage, _overlay


def test_spatial_regions_are_disjoint_and_count_all_leaks():
    mask = np.zeros((9, 12), dtype=bool)
    mask[2:7, 3:9] = True
    changed = np.zeros_like(mask)
    changed[1, 5] = True   # above
    changed[7, 5] = True   # below
    changed[4, 1] = True   # left, depth 2
    changed[4, 10] = True  # right, depth 2
    changed[4, 5] = True   # covered
    out = classify_leakage(mask, changed)
    assert out["categories"] == {
        "above": 1, "below": 1, "left": 1, "right": 1, "other": 0,
    }
    assert out["leakage_pixels"] == 4
    assert out["max_depth_screen_px"]["left"] == 2
    assert out["max_depth_screen_px"]["right"] == 2
    assert out["mask_screen_bbox_xyxy"] == [3, 2, 8, 6]


def test_rounded_sides_count_as_lateral_leakage():
    mask = np.zeros((8, 8), dtype=bool)
    mask[2, 3:5] = True
    mask[3:6, 2:6] = True
    changed = np.zeros_like(mask)
    changed[2, 2] = True
    changed[2, 5] = True
    result = classify_leakage(mask, changed)
    assert result["categories"]["left"] == 1
    assert result["categories"]["right"] == 1


def test_invalid_mask_rejected_and_overlay_uses_four_unambiguous_classes():
    with pytest.raises(ValueError):
        classify_leakage(np.zeros((2, 2), bool), np.zeros((3, 3), bool))
    mask = np.array([[False, True], [True, True]])
    changed = np.array([[True, True], [False, False]])
    output = np.asarray(_overlay(mask, changed))
    assert output[0, 0].tolist() == [236, 61, 162]
    assert output[0, 1].tolist() == [35, 180, 94]
    assert output[1, 0].tolist() == [246, 174, 44]
    assert output.shape == (2, 2, 3)


def test_accepted_centerline_offsets_uses_real_points_not_cursor_intent():
    from fill001_v2_footprint_spatial import accepted_centerline_offsets
    strokes = [
        {"points": [{"x": 10, "y": 20 + 5 * i}, {"x": 80, "y": 20 + 5 * i}]}
        for i in range(27)
    ]
    points = []
    for i in range(27):
        points.extend([
            {"stroke_id": f"stroke-{i}", "x": 11.2, "y": 21 + 5 * i},
            {"stroke_id": f"stroke-{i}", "x": 79.2, "y": 21 + 5 * i},
        ])
    result = accepted_centerline_offsets({"accepted_points": points}, {"strokes": strokes})
    assert result["max_abs_y_offset"] == 1
    assert result["first"]["observed_first_x"] == 11.2
    assert result["last"]["index"] == 27
    with pytest.raises(ValueError):
        accepted_centerline_offsets({"accepted_points": points[:-1]}, {"strokes": strokes[:-1]})


def test_legacy_roi_board_roundtrip_reproduces_egret_stage_rounding():
    from fill001_v2_footprint_spatial import roundtrip_acceptance
    plan = {"strokes": [{"points": [{"x": 94, "y": 55}, {"x": 366, "y": 55}]}]}
    roi = {"x": 496, "y": 265, "width": 674, "height": 355}
    board = {"left": 497.9604252506065, "right": 1170.1065439720678,
             "top": 267.86, "bottom": 619.06}
    run = {"renderer_geometry_at_start": {"players": [
        {"boardStageCorners": {"topLeft": {"x": 340.7916660308838, "y": 72}}}
    ]}}
    obs = {"rows": [{"index": 1, "observed_first_x": 93.20833396911621,
                     "observed_last_x": 365.2083339691162, "observed_y_median": 53.0}]}
    report = roundtrip_acceptance(plan, run, {"screen_roi": roi, "geometry":
                                              {"board_screen_corners": board}}, obs)
    assert report["first"]["predicted_first"]["y"] == 53
    assert report["first"]["predicted_first"]["x"] == pytest.approx(93.20833396911621)
    assert report["maximum_error_on_observed_first_last_and_y"] == pytest.approx(0)


def test_board_anchored_counterfactual_recovers_planned_y_without_touching_mask():
    from fill001_v2_footprint_spatial import corrected_board_counterfactual
    plan = {"strokes": [{"points": [{"x": 94, "y": 55}, {"x": 366, "y": 55}]}]}
    run = {"renderer_geometry_at_start": {"players": [
        {"boardStageCorners": {"topLeft": {"x": 340.7916660308838, "y": 72}}}
    ]}}
    binding = {
        "screen_roi": {"x": 496, "y": 265, "width": 674, "height": 355},
        "geometry": {"board_screen_corners": {
            "left": 497.9604252506065, "right": 1170.1065439720678,
            "top": 267.86, "bottom": 619.06,
        }},
    }
    corrected = corrected_board_counterfactual(plan, run, binding)
    assert corrected["status"] == "UNEXECUTED_COUNTERFACTUAL"
    assert corrected["first"]["start"]["y"] == 55
    assert corrected["first"]["end"]["y"] == 55
    assert corrected["max_y_deviation_from_planned"] == 0


def test_committed_v3_off_spatial_residual_is_diagnostic_only():
    from fill001_v2_footprint_spatial import analyze_v3_capture
    root = Path(__file__).resolve().parents[3] / "data/results/brush_behavior_tests"
    task = "fill001-20261109-040615-rectangle-r10-s5-o0-v3-smooth-off"
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "v3-off-diagnostic"
        result = analyze_v3_capture(root, target, task)
        assert result["status"] == "DIAGNOSTIC_ONLY"
        assert result["acceptance_override"] is False
        assert result["run_id"] == "3b4243e9-509d-4d5b-9698-04bd657a8888"
        assert result["leakage_pixels"] == 18
        assert result["uncovered_pixels"] == 427
        assert result["coverage_fraction"] == pytest.approx(0.9955219497871091)
        assert sum(result["leakage_regions"]["categories"].values()) == 18
        assert sum(row["count"] for row in result["missing_by_roi_row"]) == 427
        assert sum(col["count"] for col in result["missing_by_roi_column"]) == 427
        assert len(result["leakage_positions_roi_xy"]) == 18
        assert (target / "v3-off-spatial-overlay.png").is_file()
        assert json.loads((target / "report.json").read_text(encoding="utf-8"))["task_id"] == task
        with pytest.raises(FileExistsError):
            analyze_v3_capture(root, target, task)


def test_v3_off_spatial_rejects_non_off_task_and_traversal():
    from fill001_v2_footprint_spatial import analyze_v3_capture
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with pytest.raises(ValueError):
            analyze_v3_capture(root, root / "output", "../v3-smooth-off")
        with pytest.raises(ValueError):
            analyze_v3_capture(root, root / "output", "fill001-any-v3-smooth-on")
