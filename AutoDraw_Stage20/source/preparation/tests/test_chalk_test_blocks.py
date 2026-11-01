from __future__ import annotations

import json

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
    manifest_path.write_text(json.dumps({"record_type": "autodraw_brush_paint_experiment"}), encoding="utf-8")
    record = {"stroke_level": {"status": "incomplete", "reason": "stroke_id_count_mismatch"}}
    monkeypatch.setattr(
        chalk_experiment_matrix,
        "summarize_chalk_experiment_matrix",
        lambda _documents: {
            "valid_measurement_count": 1,
            "accepted": [record],
            "rejected": [],
        },
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
            "game_monitor_summary": {
                "frame_probe": {"status": "measured", "visibility_interruption": False},
                "trajectory": {"accepted_sample_count": 12},
            },
        }),
        encoding="utf-8",
    )
    record = {"stroke_level": {"status": "complete", "strokes": []}}
    monkeypatch.setattr(
        chalk_experiment_matrix,
        "summarize_chalk_experiment_matrix",
        lambda _documents: {
            "valid_measurement_count": 1,
            "accepted": [record],
            "rejected": [],
        },
    )
    accepted, reason, details = validate_chalk_block_experiment(manifest_path)
    assert accepted is True
    assert reason == "accepted"
    assert details is record

    manifest_path.write_text(
        json.dumps({
            "record_type": "autodraw_brush_paint_experiment",
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
