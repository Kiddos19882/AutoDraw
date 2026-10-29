from __future__ import annotations

import json

import pytest

from brush_test_workflow import (
    BrushExperimentState, BrushWorkflowError, PHASES, calculate_slider_target,
    validate_brush_test_preflight,
)


def _state() -> BrushExperimentState:
    return BrushExperimentState(
        requested_brush=14,
        test_case_id="horizontal_lengths",
        experiment_id="experiment-test-001",
    )


def test_workflow_advances_through_exactly_one_complete_experiment() -> None:
    state = _state()
    assert state.phase == "created"
    assert state.status == "running"

    for phase in PHASES[1:]:
        result = {"confirmed": True}
        if state.phase == "before_clear" and phase == "before_capture":
            result["board_clear_status"] = "restored"
        state.advance(phase, result)

    result = state.to_dict()
    assert result["phase"] == "completed"
    assert result["status"] == "completed"
    assert result["terminal"] is True
    assert len(result["phase_results"]) == len(PHASES) - 1
    assert result["phase_results"]["restore_brush_30"] == {"confirmed": True}
    json.dumps(result)


def test_workflow_rejects_skipped_or_repeated_phases() -> None:
    state = _state()
    with pytest.raises(BrushWorkflowError, match="Недопустимый переход"):
        state.advance("set_brush")
    state.advance("preflight")
    with pytest.raises(BrushWorkflowError, match="Недопустимый переход"):
        state.advance("preflight")


@pytest.mark.parametrize("terminal_action, expected_status", [
    (lambda state: state.stop("F12"), "stopped"),
    (lambda state: state.fail("clear failed"), "failed"),
    (lambda state: state.mark_inconclusive("meter ambiguous"), "inconclusive"),
])
def test_terminal_result_is_saved_and_cannot_continue(terminal_action, expected_status) -> None:
    state = _state()
    state.advance("preflight", {"profile_valid": True})
    terminal_action(state)

    result = state.to_dict()
    assert result["status"] == expected_status
    assert result["terminal"] is True
    assert result["phase"] == "preflight"
    with pytest.raises(BrushWorkflowError, match="уже завершён"):
        state.advance("before_clear")


def test_stop_does_not_overwrite_first_terminal_result() -> None:
    state = _state()
    state.stop("F12")
    state.fail("later cleanup error")
    assert state.status == "stopped"
    assert state.stop_reason == "F12"
    assert state.error is None


@pytest.mark.parametrize("brush", [0, 31, -1, True, 14.5])
def test_invalid_brush_is_rejected(brush) -> None:
    with pytest.raises(ValueError, match="целым числом"):
        BrushExperimentState(brush, "horizontal_lengths", "experiment-test-002")


def test_warning_is_preserved_in_manifest_and_empty_warning_is_ignored() -> None:
    state = _state()
    state.add_warning("brush value not visually verified")
    state.add_warning("  ")
    assert state.to_dict()["warnings"] == ["brush value not visually verified"]



@pytest.mark.parametrize(
    "brush, expected",
    [
        (30, (100, 500)),
        (20, (200, 500)),
        (14, (260, 500)),
        (7, (330, 500)),
        (1, (390, 500)),
    ],
)
def test_slider_target_maps_radius_30_left_to_radius_1_right(brush, expected) -> None:
    assert calculate_slider_target((100, 500), (390, 500), brush) == expected


@pytest.mark.parametrize("brush", [0, 31, True, 14.5])
def test_slider_target_rejects_invalid_brush_values(brush) -> None:
    with pytest.raises(ValueError):
        calculate_slider_target((100, 500), (390, 500), brush)


def test_slider_target_supports_diagonal_calibration() -> None:
    assert calculate_slider_target((100, 200), (390, 490), 1) == (390, 490)
    assert calculate_slider_target((100, 200), (390, 490), 30) == (100, 200)



def _valid_calibration_profile():
    return {
        "screen_size": {"width": 1920, "height": 1080},
        "regions": {
            "board_area": {"x": 100, "y": 100, "width": 646, "height": 323},
            "paint_meter_area": {"x": 100, "y": 60, "width": 120, "height": 12},
        },
        "points": {"clear_board": {"x": 80, "y": 50}},
        "status": {
            "regions": {"board_area": "confirmed", "paint_meter_area": "confirmed"},
            "points": {"clear_board": "confirmed"},
        },
    }


def _valid_brush_control():
    return {"mode": "slider", "start": [200, 500], "end": [500, 500]}


def test_preflight_accepts_valid_profile_and_slider():
    result = validate_brush_test_preflight(
        _valid_calibration_profile(), (1920, 1080), brush_control=_valid_brush_control()
    )
    assert result == {"valid": True, "errors": [], "warnings": []}


def test_preflight_rejects_screen_size_mismatch_before_mouse_actions():
    result = validate_brush_test_preflight(
        _valid_calibration_profile(), (1600, 900), brush_control=_valid_brush_control()
    )
    assert result["valid"] is False
    assert any("Разрешение экрана изменилось" in error for error in result["errors"])


def test_preflight_rejects_uncalibrated_or_review_required_clear_point():
    profile = _valid_calibration_profile()
    profile["status"]["points"]["clear_board"] = "needs_review"
    result = validate_brush_test_preflight(
        profile, (1920, 1080), brush_control=_valid_brush_control()
    )
    assert result["valid"] is False
    assert any("Clear помечена" in error for error in result["errors"])


def test_preflight_rejects_missing_meter_roi_and_wrong_brush_mode():
    profile = _valid_calibration_profile()
    profile["regions"].pop("paint_meter_area")
    result = validate_brush_test_preflight(
        profile, (1920, 1080), brush_control={"mode": "presets"}
    )
    assert result["valid"] is False
    assert any("paint_meter_area" in error for error in result["errors"])
    assert any("Расширенный ползунок" in error for error in result["errors"])


def test_preflight_rejects_slider_point_outside_screen():
    result = validate_brush_test_preflight(
        _valid_calibration_profile(), (1920, 1080),
        brush_control={"mode": "slider", "start": [200, 500], "end": [2500, 500]},
    )
    assert result["valid"] is False
    assert any("за пределами экрана" in error for error in result["errors"])


def test_preflight_uses_actual_calibration_slider_status_keys():
    profile = _valid_calibration_profile()
    profile["status"]["points"]["brush_slider_value_1"] = "needs_review"
    result = validate_brush_test_preflight(
        profile, (1920, 1080), brush_control=_valid_brush_control()
    )
    assert result["valid"] is False
    assert any("Конец ползунка end требует повторной проверки" in error for error in result["errors"])


def test_preflight_rejects_region_that_exceeds_screen_bounds():
    profile = _valid_calibration_profile()
    profile["regions"]["board_area"]["x"] = 1500
    result = validate_brush_test_preflight(
        profile, (1920, 1080), brush_control=_valid_brush_control()
    )
    assert result["valid"] is False
    assert any("board_area выходит за пределы" in error for error in result["errors"])


def test_workflow_blocks_progress_when_clear_is_not_verified():
    state = _state()
    state.advance("preflight", {"profile_valid": True})
    state.advance("before_clear", {"clear_requested": True})
    with pytest.raises(BrushWorkflowError, match="очистка доски не подтверждена"):
        state.advance("before_capture", {"clear_click_sent": True})
    assert state.phase == "before_clear"


@pytest.mark.parametrize("clear_status", ["not_restored", "inconclusive", None, ""])
def test_workflow_rejects_uncertain_board_clear(clear_status):
    state = _state()
    state.advance("preflight", {"profile_valid": True})
    state.advance("before_clear", {"clear_requested": True})
    result = {"clear_click_sent": True}
    if clear_status is not None:
        result["board_clear_status"] = clear_status
    with pytest.raises(BrushWorkflowError, match="очистка доски не подтверждена"):
        state.advance("before_capture", result)
    assert state.phase == "before_clear"


def test_workflow_accepts_explicit_blank_reference_match():
    state = _state()
    state.advance("preflight", {"profile_valid": True})
    state.advance("before_clear", {
        "clear_click_sent": True,
        "board_clear_status": "restored_within_pixel_tolerance",
        "reference_type": "explicit_blank_board_roi",
    })
    state.advance("before_capture", {"capture_saved": True})
    assert state.phase == "before_capture"
