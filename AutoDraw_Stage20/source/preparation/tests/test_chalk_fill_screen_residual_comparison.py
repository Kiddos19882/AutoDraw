from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from chalk_fill_screen_residual_comparison import (
    CAPTURE_BASE,
    EXPECTED_AFTER_SHA256,
    TASK_ID,
    analyze_committed_screen_residual,
    save_screen_residual_report,
)


def _results_root() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "data" / "results" / "brush_behavior_tests"
    )


def test_pinned_actual_png_residual_and_counterfactual_guards():
    report, overlays = analyze_committed_screen_residual(_results_root())
    actual = report["observed_actual_png"]
    assert actual["uncovered_target_screen_pixels"] == 1116
    assert actual["leakage_screen_pixels"] == 11
    assert actual["png_audit_status"] == "failed"
    assert actual["uncovered_zones"] == {
        "top_y_lt_75": 244,
        "bottom_y_gt_165": 239,
        "left_middle_x_le_94": 134,
        "right_middle_x_ge_366": 499,
        "interior_or_other": 0,
    }
    assert len(actual["leakage_xy"]) == 11
    assert report["input_evidence_sha256"]["after_png"] == EXPECTED_AFTER_SHA256
    assert list(overlays) == [
        "actual_residual",
        "baseline_model_disagreement",
        "model_contour_inset_5",
        "model_contour_inset_6",
        "model_contour_inset_7",
        "model_contour_inset_8",
    ]
    assert all(img.shape == (304, 581, 3) for img in overlays.values())
    assert all(img.dtype == np.uint8 for img in overlays.values())

    assert [x["inset_logical_px"] for x in report["counterfactual_contours"]] == [
        5, 6, 7, 8
    ]
    for case in report["counterfactual_contours"]:
        nominal = case["nominal_projection"]
        eroded = case["one_screen_px_erosion_sensitivity"]
        dilated = case["one_screen_px_dilation_sensitivity"]
        assert nominal["hypothetical_union_leakage_pixels"] >= 11
        assert nominal["can_additive_union_pass_original_quality_gates"] is False
        assert (
            nominal["actually_missing_screen_pixels_covered_by_model"]
            + nominal["remaining_actual_uncovered_under_union"] == 1116
        )
        assert (
            sum(nominal["recovered_by_zone"].values())
            == nominal["actually_missing_screen_pixels_covered_by_model"]
        )
        assert (
            eroded["actually_missing_screen_pixels_covered_by_model"]
            <= nominal["actually_missing_screen_pixels_covered_by_model"]
            <= dilated["actually_missing_screen_pixels_covered_by_model"]
        )
        assert (
            eroded["hypothetical_new_leakage_pixels"]
            <= nominal["hypothetical_new_leakage_pixels"]
            <= dilated["hypothetical_new_leakage_pixels"]
        )
    assert report["measured_chalk_for_new_contour"] is None
    assert report["new_runtime_capture"] is False
    assert report["executor_ready"] is False


def test_residual_analysis_is_repeatable_and_never_modifies_evidence():
    original = _results_root() / (CAPTURE_BASE + "-after.png")
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    first, masks_first = analyze_committed_screen_residual(_results_root())
    second, masks_second = analyze_committed_screen_residual(_results_root())
    assert first == second
    assert all(
        np.array_equal(masks_first[name], masks_second[name])
        for name in masks_first
    )
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before


def test_report_artifacts_and_no_overwrite(tmp_path):
    out = tmp_path / "FILL001-RS-SCREEN-RESIDUAL-CF-V1"
    file = save_screen_residual_report(_results_root(), out)
    report = json.loads(file.read_text(encoding="utf-8"))
    assert report["experiment_id"] == "FILL-001-RS-SCREEN-RESIDUAL-CF-V1"
    assert len(list(out.glob("*.png"))) == 6
    edge = json.loads((out / "FILL001_RIGHT_EDGE_SPATIAL_V1.json").read_text(encoding="utf-8"))
    assert edge["status"] == "DIAGNOSTIC_NOT_CAUSAL_NO_NEW_LIVE"
    assert edge["middle"]["screen_rows"] == 114
    assert edge["middle"]["rows_with_right_gap"] == 114
    assert [edge["middle"][k] for k in (
        "right_gap_min_px", "right_gap_median_px", "right_gap_max_px",
        "left_gap_median_px",
    )] == [3, 4.0, 7, 1.0]
    assert edge["uncovered_by_zone"]["right_middle_x_ge_366"] == 499
    assert len(edge["raw_monitor_endpoint_summary"]) == 27
    with pytest.raises(FileExistsError, match="overwrite"):
        save_screen_residual_report(_results_root(), out)


@pytest.mark.parametrize("insets", [(), (0,), (True,), (5, 5), (-1,)])
def test_fail_closed_on_bad_sensitivity_parameters(insets):
    with pytest.raises(ValueError, match="Insets"):
        analyze_committed_screen_residual(_results_root(), insets=insets)


def test_json_sha_is_canonical_across_checkout_line_endings_but_png_is_exact(tmp_path):
    from chalk_fill_screen_residual_comparison import _read_pinned

    source = b'{\n  "message": "immutable"\n}\n'
    expected = hashlib.sha256(source).hexdigest()
    path = tmp_path / "evidence.json"
    path.write_bytes(source)
    assert _read_pinned(path, expected, git_json=True) == source

    crlf = source.replace(b"\n", b"\r\n")
    path.write_bytes(crlf)
    assert _read_pinned(path, expected, git_json=True) == crlf
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        _read_pinned(path, expected)

    mixed = crlf.replace(b"immutable\"\r\n", b"immutable\"\n")
    path.write_bytes(mixed)
    with pytest.raises(ValueError, match="Mixed JSON"):
        _read_pinned(path, expected, git_json=True)


def test_reject_modified_png_and_identity(tmp_path):
    original = _results_root()
    target = tmp_path / "source"
    for relative in (
        "fill001/attempts/" + TASK_ID + ".json",
        "fill001/plans/" + TASK_ID + ".json",
        CAPTURE_BASE + "-before.png",
        CAPTURE_BASE + "-after.png",
    ):
        source = original / relative
        copied = target / relative
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, copied)
    after = target / (CAPTURE_BASE + "-after.png")
    after.write_bytes(after.read_bytes() + b"unauthorized-change")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        analyze_committed_screen_residual(target)


def test_edge_diagnostic_rejects_modified_endpoint_source(tmp_path):
    from chalk_fill_screen_residual_comparison import _edge_profile_from_pinned_overlay

    root = _results_root()
    _, overlays = analyze_committed_screen_residual(root)
    original = root / "fill001" / "endpoint-analysis-6a17a297.json"
    new = tmp_path / "fill001" / original.name
    new.parent.mkdir(parents=True)
    new.write_bytes(original.read_bytes() + b"\n ")
    with pytest.raises(ValueError, match="Endpoint Git blob SHA mismatch"):
        _edge_profile_from_pinned_overlay(tmp_path, overlays["actual_residual"])


def test_edge_diagnostic_rejects_changed_pixel_label():
    from chalk_fill_screen_residual_comparison import _edge_profile_from_pinned_overlay

    root = _results_root()
    _, overlays = analyze_committed_screen_residual(root)
    modified = overlays["actual_residual"].copy()
    modified[0, 0] = (220, 40, 45)
    with pytest.raises(ValueError, match="residual masks disagree"):
        _edge_profile_from_pinned_overlay(root, modified)
