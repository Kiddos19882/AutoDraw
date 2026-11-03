from __future__ import annotations

import hashlib
import json
from pathlib import Path
import uuid

import numpy as np
from PIL import Image
import pytest

from chalk_fill_capture_adapter import build_fill001_capture_from_runtime
from chalk_fill_experiment import build_fill_target_mask, fill_target_mask_sha256
from chalk_fill_matrix import FillMatrixError
from chalk_fill_runtime_binding import (
    attach_fill001_experiment_context,
    bind_fill001_runtime_evidence,
    build_fill001_experiment_context,
    find_fill001_runtime_binding,
)


def _task():
    return {
        "phase_id": "FILL001",
        "series_id": "RUNTIME-TEST",
        "task_id": "RUNTIME-TEST-rectangle-r5-rep1",
        "shape_id": "rectangle",
        "requested_radius": 5,
        "repeat_index": 1,
        "plan_signature": "a" * 64,
        "target_mask_sha256": fill_target_mask_sha256("rectangle"),
        "expected_strokes": 1,
        "sampling_profile": {"profile_id": "P1", "sampling_step": 4, "delay_ms": 5},
    }


def _snapshot(count):
    return {
        "logicalWidth": 460,
        "logicalHeight": 240,
        "maxPoints": 6000,
        "remainingPoints": 6000 - count,
        "pointCount": count,
        "isExact": True,
        "validationStatus": "valid",
        "currentRadius": 5,
    }


def _runtime_documents(tmp_path):
    task = _task()
    session_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    plan_document = attach_fill001_experiment_context({
        "schema_version": 1,
        "canvas": {"width": 460, "height": 240},
        "strokes": [{"name": "fill001", "points": [{"x": 1, "y": 1}, {"x": 19, "y": 1}]}],
    }, task)
    plan_path = tmp_path / "fill001-plan.json"
    plan_path.write_text(json.dumps(plan_document), encoding="utf-8")

    config = {
        "point_step_px": 4.0,
        "line_extension_px": 0.0,
        "point_delay_ms": 5,
        "after_mouse_up_ms": 20,
        "before_mouse_down_ms": 20,
        "after_mouse_down_ms": 40,
        "end_hold_ms": 50,
        "countdown_seconds": 5,
    }
    summary = {
        "status": "completed",
        "completed_strokes": 1,
        "total_strokes": 1,
        "started_at": "2026-11-03T10:00:00+00:00",
        "ended_at": "2026-11-03T10:00:10+00:00",
        "executor_config": config,
    }
    report = {
        "schema_version": 3,
        "execution_id": str(uuid.uuid4()),
        "status": "completed",
        "experiment_context": plan_document["autodraw_experiment"],
        "source_plan_file": str(plan_path),
        "source_plan_sha256": plan_document["autodraw_experiment"]["executor_plan_sha256"],
        "source_plan_file_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "summary": summary,
        "executor_config": config,
        "executed_plan": {"stroke_count": 1},
    }
    report_path = tmp_path / "execution_fill001.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    events = [
        {
            "monitorVersion": "0.2.1", "t": 100.0, "type": "POINTER_DOWN_CANDIDATE",
            "strokeId": "pointer-stroke-1", "board": _snapshot(100),
        },
        {
            "monitorVersion": "0.2.1", "t": 101.0, "type": "DRAW_SAMPLE",
            "strokeId": "pointer-stroke-1", "pointDelta": 0, "after": _snapshot(100),
        },
        {
            "monitorVersion": "0.2.1", "t": 102.0, "type": "DRAW_SAMPLE",
            "strokeId": "pointer-stroke-1", "pointDelta": 5, "after": _snapshot(105),
        },
        {
            "monitorVersion": "0.2.1", "t": 103.0, "type": "POINTER_UP_CANDIDATE",
            "strokeId": "pointer-stroke-1", "board": _snapshot(105),
        },
    ]
    run = {
        "schema_version": 1,
        "record_type": "autodraw_game_monitor_run",
        "session_id": session_id,
        "run_id": run_id,
        "started_at_utc": "2026-11-03T10:00:02+00:00",
        "finished_at_utc": "2026-11-03T10:00:12+00:00",
        "execution_status": "completed",
        "pre_test_snapshot": _snapshot(100),
        "post_test_snapshot": _snapshot(105),
        "chalk": {
            "status": "exact", "consumed_points": 5,
            "pre_point_count": 100, "post_point_count": 105, "max_points": 6000,
        },
        "events": events,
        "event_count": len(events),
        "dropped_events": 0,
        "monitor_buffer_dropped_events_delta": 0,
        "monitor_error_count_delta": 0,
        "bridge_send_failures_start": 0,
        "bridge_send_failures_end": 0,
        "bridge_send_failures_delta": 0,
        "collector_sequence_gap_count": 0,
        "monitor_errors": [],
        "stroke_count": 1,
        "stroke_candidate_count": 1,
        "non_consuming_stroke_candidate_count": 0,
        "stroke_lifecycle_sources": ["pointer_observer"],
        "brush_radius_status": "single",
        "observed_brush_radii": [5],
        "sampled_point_delta_total": 5,
        "point_delta_matches_chalk": True,
    }
    session_dir = tmp_path / session_id
    session_dir.mkdir()
    session_path = session_dir / "session.json"
    session = {
        "schema_version": 2,
        "session_id": session_id,
        "run_idle_seconds": 2.5,
        "monitor_status_at_connect": {"version": "0.2.1"},
        "bridge_diagnostics": {
            "received_event_count": len(events),
            "last_message_at_utc": "2026-11-03T10:00:12+00:00",
            "collector_sequence_gap_count": 0,
            "last_sequence": len(events) + 2,
            "browser_bridge": {
                "sentEventCount": len(events),
                "sendFailureCount": 0,
            },
            "session_persist_failures": 0,
        },
    }
    session_path.write_text(json.dumps(session), encoding="utf-8")
    run_path = session_dir / f"game-monitor-run-20261103T100012000000Z-{run_id[:8]}.json"
    run_path.write_text(json.dumps(run), encoding="utf-8")
    return task, session_path, report_path, run_path, run, session, report


def _png_pair(tmp_path):
    mask = build_fill_target_mask("rectangle")
    before = np.zeros((240, 460, 3), dtype=np.uint8)
    after = before.copy()
    after[mask] = 255
    before_path = tmp_path / "before.png"
    after_path = tmp_path / "after.png"
    Image.fromarray(before).save(before_path)
    Image.fromarray(after).save(after_path)
    return before_path, after_path


def test_runtime_binding_uses_bridge_session_run_and_executor_config(tmp_path):
    task, session_path, report_path, _, run, session, report = _runtime_documents(tmp_path)
    binding = bind_fill001_runtime_evidence(task, session, [run], report)
    assert binding["task_id"] == task["task_id"]
    assert binding["run_id"] == run["run_id"]
    assert binding["session_id"] == session["session_id"]
    assert binding["sampling_profile"] == task["sampling_profile"]
    assert binding["exact_chalk"] == 5
    assert binding["stroke_lifecycle_source"] == "pointer_observer"
    assert binding["observed_radius"] == 5
    assert binding["bridge_failures"] == 0
    assert binding["sequence_gaps"] == 0


def test_runtime_capture_entrypoint_loads_real_artifact_shapes_and_pngs(tmp_path):
    task, session_path, report_path, _, _, _, _ = _runtime_documents(tmp_path)
    before, after = _png_pair(tmp_path)
    capture = build_fill001_capture_from_runtime(
        task,
        session_path=session_path,
        executor_report_path=report_path,
        before_png=before,
        after_png=after,
    )
    assert capture["runtime_binding_status"] == "passed"
    assert capture["task_id"] == task["task_id"]
    assert capture["exact_chalk"] == 5
    assert capture["stroke_lifecycle_source"] == "pointer_observer"
    assert capture["executor_config"]["point_step_px"] == 4.0
    assert capture["executor_config"]["point_delay_ms"] == 5
    assert len(capture["session_file_sha256"]) == 64
    assert len(capture["bridge_run_file_sha256"]) == 64
    assert len(capture["executor_report_file_sha256"]) == 64


def test_pointer_observer_parser_matches_committed_bridge_capture():
    from chalk_fill_capture_adapter import _extract_stroke_chalk_deltas

    repo_root = Path(__file__).resolve().parents[3]
    run_path = (
        repo_root / "data/results/brush_behavior_tests/game_monitor_bridge/"
        "ee3f841c-cef2-4c75-af0d-7bbd2b6d4cc1/"
        "game-monitor-run-20261102T173651271503Z-5aeab741.json"
    )
    run = json.loads(run_path.read_text(encoding="utf-8"))
    assert run["stroke_lifecycle_sources"] == ["pointer_observer"]
    deltas, pre_count, post_count = _extract_stroke_chalk_deltas(
        run["events"], run["stroke_count"], "pointer_observer"
    )
    assert len(deltas) == 16
    assert pre_count == run["pre_test_snapshot"]["pointCount"]
    assert post_count == run["post_test_snapshot"]["pointCount"]
    assert sum(deltas) == run["chalk"]["consumed_points"] == 219
    assert sum(deltas) == run["sampled_point_delta_total"]
    assert run["point_delta_matches_chalk"] is True


def test_runtime_binding_accepts_bridge_idle_finalization_after_executor_end(tmp_path):
    task, _, _, _, run, session, report = _runtime_documents(tmp_path)
    assert report["summary"]["ended_at"] < run["finished_at_utc"]
    binding = bind_fill001_runtime_evidence(task, session, [run], report)
    assert binding["run_id"] == run["run_id"]


def test_runtime_binding_rejects_run_past_bridge_idle_finalization_grace(tmp_path):
    task, _, _, _, run, session, report = _runtime_documents(tmp_path)
    run["finished_at_utc"] = "2026-11-03T10:00:15+00:00"
    with pytest.raises(FillMatrixError, match="idle finalization grace"):
        bind_fill001_runtime_evidence(task, session, [run], report)


def test_runtime_loader_rejects_source_plan_changed_after_executor_report(tmp_path):
    task, session_path, report_path, _, _, _, report = _runtime_documents(tmp_path)
    source_path = Path(report["source_plan_file"])
    document = json.loads(source_path.read_text(encoding="utf-8"))
    document["strokes"][0]["points"][0]["x"] = 999
    source_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(FillMatrixError, match="Source DrawingPlan file SHA-256"):
        from chalk_fill_runtime_binding import load_fill001_runtime_binding
        load_fill001_runtime_binding(task, session_path, report_path)


def test_runtime_binding_rejects_wrong_sampling_or_line_extension(tmp_path):
    task, session_path, report_path, _, run, session, report = _runtime_documents(tmp_path)
    report["executor_config"]["point_step_px"] = 2.0
    report["summary"]["executor_config"]["point_step_px"] = 2.0
    with pytest.raises(FillMatrixError, match="point_step_px"):
        bind_fill001_runtime_evidence(task, session, [run], report)

    task, session_path, report_path, _, run, session, report = _runtime_documents(tmp_path)
    report["executor_config"]["line_extension_px"] = 2.0
    report["summary"]["executor_config"]["line_extension_px"] = 2.0
    with pytest.raises(FillMatrixError, match="line_extension_px"):
        bind_fill001_runtime_evidence(task, session, [run], report)


def test_runtime_binding_rejects_run_session_mismatch_and_sequence_gap(tmp_path):
    task, _, _, _, run, session, report = _runtime_documents(tmp_path)
    run["session_id"] = str(uuid.uuid4())
    with pytest.raises(FillMatrixError, match="другой session"):
        bind_fill001_runtime_evidence(task, session, [run], report)

    task, _, _, _, run, session, report = _runtime_documents(tmp_path)
    run["collector_sequence_gap_count"] = 1
    session["bridge_diagnostics"]["collector_sequence_gap_count"] = 1
    with pytest.raises(FillMatrixError, match="collector_sequence_gap_count"):
        bind_fill001_runtime_evidence(task, session, [run], report)


def test_runtime_binding_rejects_ambiguous_bridge_run_candidates(tmp_path):
    task, _, _, _, run, session, report = _runtime_documents(tmp_path)
    duplicate = dict(run)
    duplicate["run_id"] = str(uuid.uuid4())
    with pytest.raises(FillMatrixError, match="ровно один Bridge run"):
        bind_fill001_runtime_evidence(task, session, [run, duplicate], report)


def test_runtime_context_rejects_task_mismatch_and_duplicate_context(tmp_path):
    task = _task()
    context = build_fill001_experiment_context(task)
    assert context["task_id"] == task["task_id"]
    with pytest.raises(FillMatrixError, match="уже содержит"):
        attach_fill001_experiment_context({"autodraw_experiment": context}, task)
    task["task_id"] = "OTHER-TASK"
    _, _, _, _, run, session, report = _runtime_documents(tmp_path)
    with pytest.raises(FillMatrixError, match="другой FILL-001 task"):
        bind_fill001_runtime_evidence(task, session, [run], report)


def test_find_runtime_binding_discovers_the_unique_active_session(tmp_path):
    task, session_path, report_path, _, _, _, _ = _runtime_documents(tmp_path)
    bridge_root = tmp_path / "bridge-root"
    bridge_root.mkdir()
    destination = bridge_root / session_path.parent.name
    session_path.parent.rename(destination)
    binding = find_fill001_runtime_binding(
        task, bridge_root, report_path
    )
    assert binding is not None
    assert binding["task_id"] == task["task_id"]
    assert binding["run_id"]


def test_find_runtime_binding_waits_until_bridge_run_file_is_finalized(tmp_path):
    task, session_path, report_path, run_path, _, _, _ = _runtime_documents(tmp_path)
    bridge_root = tmp_path / "bridge-root"
    bridge_root.mkdir()
    destination = bridge_root / session_path.parent.name
    session_path.parent.rename(destination)
    (destination / run_path.name).unlink()
    assert find_fill001_runtime_binding(task, bridge_root, report_path) is None


def test_find_runtime_binding_rejects_multiple_active_sessions(tmp_path):
    task, session_path, report_path, _, _, session, _ = _runtime_documents(tmp_path)
    bridge_root = tmp_path / "bridge-root"
    bridge_root.mkdir()
    destination = bridge_root / session_path.parent.name
    session_path.parent.rename(destination)
    second_id = str(uuid.uuid4())
    second_dir = bridge_root / second_id
    second_dir.mkdir()
    second_session = dict(session)
    second_session["session_id"] = second_id
    (second_dir / "session.json").write_text(json.dumps(second_session), encoding="utf-8")
    with pytest.raises(FillMatrixError, match="несколько активных Bridge sessions"):
        find_fill001_runtime_binding(task, bridge_root, report_path)

