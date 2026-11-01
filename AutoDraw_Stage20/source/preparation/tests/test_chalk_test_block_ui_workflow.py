from __future__ import annotations

from pathlib import Path

import brush_behavior_test_ui as ui_module
from brush_behavior_test_ui import BrushBehaviorTestTab
from chalk_test_blocks import (
    build_chalk_test_block_plan,
    claim_next_chalk_block_task,
    create_chalk_test_block_journal,
    load_chalk_test_block_journal,
)


class _Value:
    def __init__(self):
        self.value = ""

    def set(self, value):
        self.value = value


class _Root:
    def __init__(self):
        self.scheduled = []

    def after(self, delay, callback):
        self.scheduled.append((delay, callback))
        return f"after-{len(self.scheduled)}"


def _active_ui(tmp_path: Path):
    plan = build_chalk_test_block_plan(series_id="ui-series", phase_id="G1", seed=4)
    journal_path = tmp_path / "block.json"
    create_chalk_test_block_journal(journal_path, plan)
    task = claim_next_chalk_block_task(journal_path)
    experiment_dir = tmp_path / "experiment"
    experiment_dir.mkdir()
    ui = object.__new__(BrushBehaviorTestTab)
    ui._chalk_block_journal_path = journal_path
    ui._chalk_block_task = task
    ui._chalk_block_capture_poll_id = None
    ui.experiment_phases = {"monitor_capture": {"status": "saved"}}
    ui.experiment_dir = experiment_dir
    ui._experiment_id = "experiment-ui"
    ui.status_var = _Value()
    ui.root = _Root()
    ui._update_chalk_block_progress = lambda: None
    return ui, journal_path, task


def test_ui_capture_gate_accepts_task_before_advancing(tmp_path, monkeypatch):
    ui, journal_path, task = _active_ui(tmp_path)
    advanced = []
    monkeypatch.setattr(
        ui_module,
        "validate_chalk_block_experiment",
        lambda _path: (True, "accepted", {"consumed_points": 25}),
    )
    ui._start_next_chalk_block_task = lambda: advanced.append(True)

    ui._wait_for_chalk_block_capture()

    journal = load_chalk_test_block_journal(journal_path)
    saved_task = next(item for item in journal["tasks"] if item["task_id"] == task["task_id"])
    assert saved_task["status"] == "completed"
    assert saved_task["attempts"][-1]["experiment_id"] == "experiment-ui"
    assert advanced == [True]
    assert "полный per-stroke" in ui.status_var.value


def test_ui_capture_gate_pauses_without_advancing_on_incomplete_evidence(tmp_path, monkeypatch):
    ui, _journal_path, _task = _active_ui(tmp_path)
    failures = []
    advanced = []
    monkeypatch.setattr(
        ui_module,
        "validate_chalk_block_experiment",
        lambda _path: (False, "stroke_level_stroke_id_count_mismatch", None),
    )
    ui._fail_chalk_test_block = lambda reason: failures.append(reason)
    ui._start_next_chalk_block_task = lambda: advanced.append(True)

    ui._wait_for_chalk_block_capture()

    assert failures == ["stroke_level_stroke_id_count_mismatch"]
    assert advanced == []


def test_ui_capture_gate_times_out_closed(tmp_path):
    ui, _journal_path, _task = _active_ui(tmp_path)
    failures = []
    ui._fail_chalk_test_block = lambda reason: failures.append(reason)

    ui._wait_for_chalk_block_capture(attempt=60)

    assert failures == ["monitor_capture_gate_timeout:saved"]


def test_ui_executor_failure_pauses_block_without_starting_postdraw(tmp_path):
    ui, _journal_path, _task = _active_ui(tmp_path)
    ui.experiment_dir = None
    failures = []
    ui._fail_chalk_test_block = lambda reason: failures.append(reason)
    ui._start_automated_postdraw = lambda: (_ for _ in ()).throw(AssertionError("postdraw must not start"))

    result = ui.handle_executor_finished({"status": "failed"}, None)

    assert result is True
    assert failures == ["executor_status_failed"]
