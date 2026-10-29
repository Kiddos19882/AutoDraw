from __future__ import annotations

import json

import pytest

from brush_test_workflow import BrushExperimentState, BrushWorkflowError, PHASES


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
        state.advance(phase, {"confirmed": True})

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
