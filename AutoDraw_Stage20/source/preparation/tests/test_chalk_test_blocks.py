from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

import pytest

from chalk_test_blocks import (
    build_chalk_test_block_plan,
    claim_next_chalk_block_task,
    chalk_test_block_progress,
    create_chalk_test_block_journal,
    finish_chalk_block_task,
    load_chalk_test_block_journal,
    mark_interrupted_chalk_block_task,
    validate_chalk_block_experiment,
    stop_chalk_test_block,
    record_chalk_block_task_experiment,
    resolve_interrupted_chalk_block_task,
    acquire_chalk_block_owner_lock,
    release_chalk_block_owner_lock,
)


@pytest.mark.parametrize(("phase", "expected_count"), [("G1", 12), ("G2", 18)])
def test_block_plan_contains_every_scenario_repeat_cell_and_unique_order(phase, expected_count):
    plan = build_chalk_test_block_plan(
        series_id="block-series",
        phase_id=phase,
        repeats=3,
        seed=12345,
    )
    assert len(plan["tasks"]) == expected_count
    assert plan["expected_task_count"] == expected_count
    assert len({task["task_id"] for task in plan["tasks"]}) == expected_count
    assert sorted(task["matrix_order_index"] for task in plan["tasks"]) == list(range(1, expected_count + 1))
    for scenario in {task["scenario_id"] for task in plan["tasks"]}:
        repeats = sorted(task["repeat_index"] for task in plan["tasks"] if task["scenario_id"] == scenario)
        assert repeats == [1, 2, 3]
    assert all(task["requested_radius"] == 10 for task in plan["tasks"])


def test_block_order_is_deterministic_for_same_seed():
    first = build_chalk_test_block_plan(series_id="series", phase_id="G1", seed=777)
    second = build_chalk_test_block_plan(series_id="series", phase_id="G1", seed=777)
    assert [
        (task["scenario_id"], task["repeat_index"]) for task in first["tasks"]
    ] == [
        (task["scenario_id"], task["repeat_index"]) for task in second["tasks"]
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"series_id": "series", "phase_id": "G9"},
        {"series_id": "series", "phase_id": "G1", "repeats": 2},
        {"series_id": "series", "phase_id": "G1", "radius": 5},
        {"series_id": "bad id", "phase_id": "G1"},
    ],
)
def test_block_plan_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        build_chalk_test_block_plan(**kwargs)


def test_journal_claim_finish_and_progress(tmp_path):
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1", seed=1)
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(path, plan)
    with pytest.raises(FileExistsError):
        create_chalk_test_block_journal(path, plan)

    task = claim_next_chalk_block_task(path, now_utc="2026-11-01T00:00:00Z")
    assert task is not None
    assert task["status"] == "running"
    with pytest.raises(RuntimeError):
        claim_next_chalk_block_task(path)

    finish_chalk_block_task(
        path,
        task["task_id"],
        accepted=True,
        experiment_id="exp-1",
        experiment_dir=tmp_path / "experiment-1",
        finished_at_utc="2026-11-01T00:01:00Z",
    )
    journal = load_chalk_test_block_journal(path)
    progress = chalk_test_block_progress(journal)
    assert progress["completed"] == 1
    assert progress["pending"] == 11
    assert journal["status"] == "ready"


def test_failed_task_pauses_block_and_does_not_skip_to_next(tmp_path):
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(path, plan)
    task = claim_next_chalk_block_task(path)
    finish_chalk_block_task(
        path,
        task["task_id"],
        accepted=False,
        experiment_id="exp-failed",
        experiment_dir=tmp_path / "failed",
        reason="monitor_capture_not_exact",
    )
    journal = load_chalk_test_block_journal(path)
    assert journal["status"] == "paused"
    assert chalk_test_block_progress(journal)["failed"] == 1
    assert claim_next_chalk_block_task(path) is None


def test_interrupted_task_is_not_silently_replayed(tmp_path):
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(path, plan)
    claimed = claim_next_chalk_block_task(path)
    interrupted = mark_interrupted_chalk_block_task(path)
    assert interrupted["task_id"] == claimed["task_id"]
    assert interrupted["status"] == "interrupted"
    journal = load_chalk_test_block_journal(path)
    assert journal["status"] == "paused"
    assert chalk_test_block_progress(journal)["interrupted"] == 1
    assert claim_next_chalk_block_task(path) is None



def test_block_experiment_acceptance_requires_complete_stroke_breakdown(tmp_path, monkeypatch):
    import chalk_experiment_matrix

    manifest_path = tmp_path / "experiment.json"
    manifest_path.write_text(json.dumps({"record_type": "autodraw_brush_paint_experiment", "phases": {
                "before_clear": {"status": "restored"},
                "before_draw": {"captured_at_utc": "2026-11-01T00:00:00Z"},
                "after_draw": {"status": "captured"},
                "postdraw_workflow": {"status": "completed"},
            },}), encoding="utf-8")
    record = {"expected_strokes": 5, "consumed_points": 25, "stroke_level": {"status": "incomplete", "reason": "stroke_id_count_mismatch"}}
    monkeypatch.setattr(chalk_experiment_matrix, "_validate_manifest", lambda _document: (True, "valid", record))
    monkeypatch.setattr(
        chalk_experiment_matrix,
        "_stroke_level_breakdown",
        lambda *_args, **_kwargs: record["stroke_level"],
    )
    accepted, reason, details = validate_chalk_block_experiment(manifest_path)
    assert accepted is False
    assert reason == "stroke_level_stroke_id_count_mismatch"
    assert details is None


def test_block_experiment_acceptance_requires_clean_frame_probe_and_trajectory(tmp_path, monkeypatch):
    import chalk_experiment_matrix

    manifest_path = tmp_path / "experiment.json"
    manifest_path.write_text(
        json.dumps({
            "record_type": "autodraw_brush_paint_experiment",
            "phases": {
                "before_clear": {"status": "restored"},
                "before_draw": {"captured_at_utc": "2026-11-01T00:00:00Z"},
                "after_draw": {"status": "captured"},
                "postdraw_workflow": {"status": "completed"},
            },
            "game_monitor_summary": {
                "frame_probe": {"status": "measured", "visibility_interruption": False},
                "trajectory": {"accepted_sample_count": 12},
            },
        }),
        encoding="utf-8",
    )
    record = {"expected_strokes": 5, "consumed_points": 25, "stroke_level": {"status": "complete", "strokes": []}}
    monkeypatch.setattr(chalk_experiment_matrix, "_validate_manifest", lambda _document: (True, "valid", record))
    monkeypatch.setattr(
        chalk_experiment_matrix,
        "_stroke_level_breakdown",
        lambda *_args, **_kwargs: record["stroke_level"],
    )
    accepted, reason, details = validate_chalk_block_experiment(manifest_path)
    assert accepted is True
    assert reason == "accepted"
    assert details is record

    manifest_path.write_text(
        json.dumps({
            "record_type": "autodraw_brush_paint_experiment",
            "phases": {
                "before_clear": {"status": "restored"},
                "before_draw": {"captured_at_utc": "2026-11-01T00:00:00Z"},
                "after_draw": {"status": "captured"},
                "postdraw_workflow": {"status": "completed"},
            },
            "game_monitor_summary": {
                "frame_probe": {"status": "measured", "visibility_interruption": True},
                "trajectory": {"accepted_sample_count": 12},
            },
        }),
        encoding="utf-8",
    )
    accepted, reason, details = validate_chalk_block_experiment(manifest_path)
    assert accepted is False
    assert reason == "frame_probe_not_clean"
    assert details is None



@pytest.mark.parametrize(
    ("identity_change", "expected_reason"),
    [
        ({"task_id": "another-task"}, "task_id"),
        ({"scenario_id": "vertical_lengths"}, "scenario_id"),
        ({"repeat_index": 2}, "repeat_index"),
        ({"matrix_order_index": 9}, "matrix_order_index"),
        ({"block_id": "another-block"}, "block_id"),
        ({"experiment_id": "another-experiment"}, "experiment_id"),
        ({"experiment_dir": "another-directory"}, "experiment_dir"),
    ],
)
def test_block_experiment_acceptance_is_bound_to_active_task_identity(
    tmp_path, monkeypatch, identity_change, expected_reason
):
    import chalk_experiment_matrix

    manifest_path = tmp_path / "experiment.json"
    block = {
        "block_id": "block-001",
        "series_id": "series-001",
        "phase_id": "G1",
    }
    task = {
        "task_id": "horizontal_lengths-r1",
        "scenario_id": "horizontal_lengths",
        "repeat_index": 1,
        "requested_radius": 10,
        "expected_strokes": 5,
        "matrix_order_index": 3,
        "executor_parameters": {"point_step_px": 2},
    }
    document = {
        "record_type": "autodraw_brush_paint_experiment",
        "experiment_id": "experiment-001",
        "chalk_test_block": {
            "block_id": block["block_id"],
            "task_id": task["task_id"],
            "phase_id": block["phase_id"],
        },
        "chalk_experiment_matrix": {
            "series_id": block["series_id"],
            "phase_id": block["phase_id"],
            "scenario_id": task["scenario_id"],
            "repeat_index": task["repeat_index"],
            "requested_radius": task["requested_radius"],
            "expected_strokes": task["expected_strokes"],
            "matrix_order_index": task["matrix_order_index"],
            "executor_parameters": task["executor_parameters"],
        },
        "phases": {
            "before_clear": {"status": "restored"},
            "before_draw": {"captured_at_utc": "2026-11-01T00:00:00Z"},
            "after_draw": {"status": "captured"},
            "postdraw_workflow": {"status": "completed"},
        },
        "game_monitor_summary": {
            "frame_probe": {"status": "measured", "visibility_interruption": False},
            "trajectory": {"accepted_sample_count": 12},
        },
    }
    expected_experiment_dir = tmp_path
    for key, value in identity_change.items():
        if key == "experiment_dir":
            expected_experiment_dir = tmp_path / value
            continue
        if key in {"block_id", "task_id"}:
            target = "chalk_test_block"
        elif key == "experiment_id":
            document[key] = value
            continue
        else:
            target = "chalk_experiment_matrix"
        field = "block_id" if key == "block_id" else key
        document[target][field] = value
    manifest_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(chalk_experiment_matrix, "_validate_manifest", lambda _doc: (True, "valid", {
        "expected_strokes": 5, "consumed_points": 25
    }))
    monkeypatch.setattr(chalk_experiment_matrix, "_stroke_level_breakdown", lambda *_a, **_k: {
        "status": "complete", "strokes": []
    })

    accepted, reason, details = validate_chalk_block_experiment(
        manifest_path,
        expected_task=task,
        expected_block=block,
        expected_experiment_id="experiment-001",
        expected_experiment_dir=expected_experiment_dir,
    )

    assert accepted is False
    assert reason == f"block_task_identity_mismatch:{expected_reason}"
    assert details is None


def test_block_experiment_acceptance_accepts_matching_active_task_identity(tmp_path, monkeypatch):
    import chalk_experiment_matrix

    manifest_path = tmp_path / "experiment.json"
    block = {"block_id": "block-001", "series_id": "series-001", "phase_id": "G1"}
    task = {
        "task_id": "horizontal_lengths-r1", "scenario_id": "horizontal_lengths",
        "repeat_index": 1, "requested_radius": 10, "expected_strokes": 5,
        "matrix_order_index": 3, "executor_parameters": {"point_step_px": 2},
    }
    document = {
        "record_type": "autodraw_brush_paint_experiment", "experiment_id": "experiment-001",
        "chalk_test_block": {"block_id": "block-001", "task_id": task["task_id"], "phase_id": "G1"},
        "chalk_experiment_matrix": {
            "series_id": "series-001", "phase_id": "G1", "scenario_id": "horizontal_lengths",
            "repeat_index": 1, "requested_radius": 10, "expected_strokes": 5,
            "matrix_order_index": 3, "executor_parameters": {"point_step_px": 2},
        },
        "phases": {
            "before_clear": {"status": "restored"}, "before_draw": {"captured_at_utc": "2026-11-01T00:00:00Z"},
            "after_draw": {"status": "captured"}, "postdraw_workflow": {"status": "completed"},
        },
        "game_monitor_summary": {
            "frame_probe": {"status": "measured", "visibility_interruption": False},
            "trajectory": {"accepted_sample_count": 12},
        },
    }
    manifest_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(chalk_experiment_matrix, "_validate_manifest", lambda _doc: (True, "valid", {
        "expected_strokes": 5, "consumed_points": 25
    }))
    monkeypatch.setattr(chalk_experiment_matrix, "_stroke_level_breakdown", lambda *_a, **_k: {
        "status": "complete", "strokes": []
    })

    accepted, reason, details = validate_chalk_block_experiment(
        manifest_path,
        expected_task=task,
        expected_block=block,
        expected_experiment_id="experiment-001",
        expected_experiment_dir=tmp_path,
    )

    assert accepted is True
    assert reason == "accepted"
    assert details is not None


def test_block_can_stop_only_at_task_boundary(tmp_path):
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(path, plan)
    running = claim_next_chalk_block_task(path)
    with pytest.raises(RuntimeError):
        stop_chalk_test_block(path)
    finish_chalk_block_task(
        path,
        running["task_id"],
        accepted=True,
        experiment_id="exp-1",
        experiment_dir=tmp_path / "exp-1",
    )
    stopped = stop_chalk_test_block(path)
    assert stopped["status"] == "stopped"
    assert claim_next_chalk_block_task(path) is None



def test_running_attempt_records_experiment_identity_before_completion(tmp_path):
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(path, plan)
    task = claim_next_chalk_block_task(path)
    experiment_dir = tmp_path / "experiment"
    experiment_dir.mkdir()
    record_chalk_block_task_experiment(
        path,
        task["task_id"],
        experiment_id="experiment-123",
        experiment_dir=experiment_dir,
    )
    journal = load_chalk_test_block_journal(path)
    saved_task = next(item for item in journal["tasks"] if item["task_id"] == task["task_id"])
    attempt = saved_task["attempts"][-1]
    assert attempt["experiment_id"] == "experiment-123"
    assert attempt["experiment_dir"] == str(experiment_dir.resolve())
    with pytest.raises(ValueError):
        record_chalk_block_task_experiment(
            path,
            task["task_id"],
            experiment_id="experiment-456",
            experiment_dir=experiment_dir,
        )



def test_interrupted_block_requires_board_check_before_retry(tmp_path):
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(path, plan)
    claimed = claim_next_chalk_block_task(path)
    mark_interrupted_chalk_block_task(path)
    with pytest.raises(ValueError):
        resolve_interrupted_chalk_block_task(
            path, claimed["task_id"], board_checked=False, decision="retry"
        )
    resolved = resolve_interrupted_chalk_block_task(
        path, claimed["task_id"], board_checked=True, decision="retry"
    )
    assert resolved["status"] == "pending"
    journal = load_chalk_test_block_journal(path)
    assert journal["status"] == "ready"
    assert journal["recovery_decisions"][-1]["decision"] == "retry"
    assert journal["tasks"][0]["attempts"][-1]["status"] == "interrupted"


def test_interrupted_block_can_be_stopped_after_explicit_board_check(tmp_path):
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(path, plan)
    claimed = claim_next_chalk_block_task(path)
    mark_interrupted_chalk_block_task(path)
    resolve_interrupted_chalk_block_task(
        path, claimed["task_id"], board_checked=True, decision="stop"
    )
    journal = load_chalk_test_block_journal(path)
    assert journal["status"] == "stopped"
    assert journal["recovery_decisions"][-1]["board_checked"] is True
    assert claim_next_chalk_block_task(path) is None



def test_paused_block_cannot_be_closed_without_board_check(tmp_path):
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(path, plan)
    task = claim_next_chalk_block_task(path)
    finish_chalk_block_task(
        path,
        task["task_id"],
        accepted=False,
        experiment_id="exp-failed",
        experiment_dir=tmp_path / "failed",
        reason="monitor_capture_not_exact",
    )
    with pytest.raises(ValueError):
        stop_chalk_test_block(path)
    stopped = stop_chalk_test_block(path, board_checked=True)
    assert stopped["status"] == "stopped"
    assert stopped["recovery_decisions"][-1]["board_checked"] is True



@pytest.mark.parametrize(
    "mutate",
    [
        lambda journal: journal["tasks"].__setitem__(0, "not-a-task"),
        lambda journal: journal["tasks"][0].update({"task_id": ""}),
        lambda journal: journal["tasks"][1].update({"task_id": journal["tasks"][0]["task_id"]}),
        lambda journal: journal["tasks"][0].update({"status": "unknown"}),
        lambda journal: journal.update({"status": []}),
        lambda journal: journal.update({"phase_id": {}}),
        lambda journal: journal["tasks"][0].update({"status": []}),
        lambda journal: journal["tasks"][0].update({"attempts": [{"attempt_id": "attempt-1", "status": {}}]}),
        lambda journal: journal.update({"expected_task_count": 999}),
        lambda journal: journal.update({"status": "running"}),
        lambda journal: journal["tasks"][0].update({"status": "running", "active_attempt_id": "missing"}),
        lambda journal: journal["tasks"][0].update({
            "attempts": [{"attempt_id": "attempt-1", "status": "running"}]
        }),
        lambda journal: journal.update({
            "status": "completed",
            "tasks": [dict(task, status="pending") for task in journal["tasks"]],
        }),
    ],
)
def test_load_journal_rejects_corrupt_or_inconsistent_state(tmp_path, mutate):
    import copy

    journal = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    corrupt = copy.deepcopy(journal)
    mutate(corrupt)
    path = tmp_path / "corrupt.json"
    path.write_text(json.dumps(corrupt), encoding="utf-8")

    with pytest.raises(ValueError):
        load_chalk_test_block_journal(path)


def test_load_journal_accepts_consistent_running_attempt(tmp_path):
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(
        path, build_chalk_test_block_plan(series_id="series", phase_id="G1")
    )
    claimed = claim_next_chalk_block_task(path)

    journal = load_chalk_test_block_journal(path)

    assert journal["status"] == "running"
    assert next(task for task in journal["tasks"] if task["task_id"] == claimed["task_id"])["status"] == "running"


def test_load_journal_converts_invalid_json_to_value_error(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(ValueError, match="Не удалось разобрать журнал"):
        load_chalk_test_block_journal(path)



@pytest.mark.parametrize(
    ("block_status", "task_status"),
    [
        ("ready", "failed"),
        ("ready", "interrupted"),
        ("ready", "running"),
        ("paused", "pending"),
        ("failed", "pending"),
    ],
)
def test_load_journal_rejects_inconsistent_block_and_task_status(block_status, task_status, tmp_path):
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    plan["status"] = block_status
    plan["tasks"][0]["status"] = task_status
    path = tmp_path / "inconsistent.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(ValueError):
        load_chalk_test_block_journal(path)


def test_atomic_write_replace_failure_preserves_previous_journal(tmp_path, monkeypatch):
    import chalk_test_blocks

    path = tmp_path / "block.json"
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    create_chalk_test_block_journal(path, plan)
    original = path.read_bytes()

    def fail_replace(_source, _destination):
        raise PermissionError("simulated replace failure")

    monkeypatch.setattr(chalk_test_blocks.os, "replace", fail_replace)
    with pytest.raises(PermissionError):
        claim_next_chalk_block_task(path)

    assert path.read_bytes() == original
    assert load_chalk_test_block_journal(path)["status"] == "ready"


def test_atomic_write_temp_creation_failure_preserves_previous_journal(tmp_path, monkeypatch):
    import chalk_test_blocks

    path = tmp_path / "block.json"
    plan = build_chalk_test_block_plan(series_id="series", phase_id="G1")
    create_chalk_test_block_journal(path, plan)
    original = path.read_bytes()
    original_write_text = Path.write_text

    def fail_temp_write(self, *args, **kwargs):
        if self.name.endswith(".tmp"):
            raise OSError("simulated temp write failure")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_temp_write)
    with pytest.raises(OSError):
        claim_next_chalk_block_task(path)

    assert path.read_bytes() == original
    assert load_chalk_test_block_journal(path)["status"] == "ready"


def test_journal_mutations_use_a_stable_cross_process_lock_file(tmp_path):
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(
        path, build_chalk_test_block_plan(series_id="series", phase_id="G1")
    )
    claimed = claim_next_chalk_block_task(path)
    assert claimed is not None
    assert path.with_name(path.name + ".lock").exists()
    mark_interrupted_chalk_block_task(path)
    assert load_chalk_test_block_journal(path)["status"] == "paused"



def test_block_owner_lock_is_exclusive_until_released(tmp_path):
    path = tmp_path / "block.json"
    first = acquire_chalk_block_owner_lock(path)
    assert first is not None
    assert acquire_chalk_block_owner_lock(path) is None
    assert acquire_chalk_block_owner_lock(tmp_path / "another-block.json") is None

    release_chalk_block_owner_lock(first)
    second = acquire_chalk_block_owner_lock(path)
    assert second is not None
    release_chalk_block_owner_lock(second)



def test_failed_block_requires_board_check_before_stop(tmp_path):
    path = tmp_path / "block.json"
    create_chalk_test_block_journal(
        path, build_chalk_test_block_plan(series_id="failed-close", phase_id="G1")
    )
    task = claim_next_chalk_block_task(path)
    finish_chalk_block_task(
        path, task["task_id"], accepted=False,
        experiment_id="exp-failed", experiment_dir=tmp_path / "failed",
        reason="test_failure",
    )
    with pytest.raises(ValueError):
        stop_chalk_test_block(path)
    assert stop_chalk_test_block(path, board_checked=True)["status"] == "stopped"



def test_owner_lock_io_failure_fails_closed(tmp_path, monkeypatch):
    original_open = Path.open

    def fail_owner_lock_open(self, *args, **kwargs):
        if self.name == ".active-block.owner.lock":
            raise PermissionError("simulated owner lock permission failure")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_owner_lock_open)
    assert acquire_chalk_block_owner_lock(tmp_path / "block.json") is None


def _owner_lock_child_attempt(journal_path, result_queue):
    lock_file = acquire_chalk_block_owner_lock(journal_path)
    result_queue.put(lock_file is not None)
    if lock_file is not None:
        release_chalk_block_owner_lock(lock_file)


def test_block_owner_lock_is_exclusive_across_processes(tmp_path):
    path = tmp_path / "block.json"
    parent_lock = acquire_chalk_block_owner_lock(path)
    assert parent_lock is not None
    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue()
    process = context.Process(target=_owner_lock_child_attempt, args=(str(path), result_queue))
    try:
        process.start()
        assert result_queue.get(timeout=10) is False
        process.join(timeout=10)
        assert process.exitcode == 0
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
        release_chalk_block_owner_lock(parent_lock)
