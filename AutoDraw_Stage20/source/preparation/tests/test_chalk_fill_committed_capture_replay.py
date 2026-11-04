from __future__ import annotations

import json
from pathlib import Path
import shutil

import chalk_fill_ui
from chalk_fill_matrix import load_fill001_matrix


TASK_ID = "fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1"
SESSION_ID = "bb261898-8296-41f5-a333-eb0b81016410"


class _StatusVar:
    def __init__(self):
        self.value = ""

    def set(self, value):
        self.value = value


def test_real_committed_fill001_evidence_runs_through_capture_button(tmp_path, monkeypatch, capsys):
    """Replay the user's committed FILL-001 attempt through Fill001Tab.finalize_capture.

    This intentionally uses the actual manifest, attempt, executor report, Bridge
    session/run JSON and before/after PNGs committed with the 2026-11-04 preflight.
    Only absolute machine-local paths are relocated into tmp_path; evidence bytes
    and all validation criteria remain unchanged.
    """
    repo_root = Path(__file__).resolve().parents[3]
    results_root = repo_root / "data" / "results" / "brush_behavior_tests"
    manifest_source = results_root / "fill001_rs" / "fill001-rs-preflight-20261104-7.04.json"
    attempt_source = (
        results_root / "fill001" / "attempts" / f"{TASK_ID}.json"
    )
    report_source = (
        repo_root / "data" / "results" / "execution_20261104_070545_500355_cf845f.json"
    )
    source_plan = repo_root / "data" / "runtime" / "current_brush_behavior_test.json"
    before_source = results_root / "fill001" / "captures" / f"{TASK_ID}-before.png"
    after_source = results_root / "fill001" / "captures" / f"{TASK_ID}-after.png"
    session_source = results_root / "game_monitor_bridge" / SESSION_ID
    legacy_session_id = "3323cf8e-01ca-4009-8f16-27d657d857f8"
    legacy_session_source = results_root / "game_monitor_bridge" / legacy_session_id / "session.json"

    required = (
        manifest_source,
        attempt_source,
        report_source,
        source_plan,
        before_source,
        after_source,
        session_source / "session.json",
        legacy_session_source,
        session_source / "game-monitor-run-20261104T040456791496Z-9ea6d0bb.json",
        session_source / "game-monitor-run-20261104T040548835772Z-6a17a297.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    assert not missing, "Committed live evidence bundle is incomplete: " + ", ".join(missing)

    sandbox_results = tmp_path / "results" / "brush_behavior_tests"
    output_dir = sandbox_results / "fill001"
    captures_dir = output_dir / "captures"
    captures_dir.mkdir(parents=True)
    bridge_root = sandbox_results / "game_monitor_bridge"
    bridge_root.mkdir(parents=True)
    session_destination = bridge_root / SESSION_ID
    shutil.copytree(session_source, session_destination)
    # This real pre-schema-2 session has no Bridge diagnostics and must not
    # block a later FILL-001 binding merely because its directory still exists.
    legacy_session_destination = bridge_root / legacy_session_id
    legacy_session_destination.mkdir()
    shutil.copy2(legacy_session_source, legacy_session_destination / "session.json")

    manifest_path = sandbox_results / "fill001_rs" / manifest_source.name
    manifest_path.parent.mkdir(parents=True)
    shutil.copy2(manifest_source, manifest_path)

    plan_destination = tmp_path / "runtime" / source_plan.name
    plan_destination.parent.mkdir(parents=True)
    shutil.copy2(source_plan, plan_destination)

    report_path = tmp_path / "execution.json"
    report = json.loads(report_source.read_text(encoding="utf-8"))
    report["source_plan_file"] = str(plan_destination)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    before_png = captures_dir / before_source.name
    after_png = captures_dir / after_source.name
    shutil.copy2(before_source, before_png)
    shutil.copy2(after_source, after_png)

    attempt_path = output_dir / "attempts" / attempt_source.name
    attempt_path.parent.mkdir(parents=True)
    attempt = json.loads(attempt_source.read_text(encoding="utf-8"))
    attempt["manifest_path"] = str(manifest_path)
    attempt["execution_report_path"] = str(report_path)
    attempt["before_png"] = str(before_png)
    attempt["after_png"] = str(after_png)
    attempt_path.write_text(json.dumps(attempt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    matrix = load_fill001_matrix(manifest_path)
    matching_tasks = [task for task in matrix["tasks"] if task.get("task_id") == TASK_ID]
    assert len(matching_tasks) == 1
    task = matching_tasks[0]
    assert task["expected_strokes"] == 27
    assert task["requested_radius"] == 10
    assert task["scanline_row_step"] == 5
    assert task["scanline_offset"] == 0

    import chalk_fill_capture_adapter

    ui_errors = []
    png_audit_result = {}
    original_png_audit = chalk_fill_capture_adapter.audit_fill001_png_pair

    def _record_png_audit(*args, **kwargs):
        result = original_png_audit(*args, **kwargs)
        png_audit_result.update(result)
        return result

    monkeypatch.setattr(
        chalk_fill_capture_adapter, "audit_fill001_png_pair", _record_png_audit
    )
    monkeypatch.setattr(
        chalk_fill_ui.messagebox,
        "showerror",
        lambda title, message, **_kwargs: ui_errors.append((title, message)),
    )
    monkeypatch.setattr(
        chalk_fill_ui.messagebox,
        "showwarning",
        lambda title, message, **_kwargs: ui_errors.append((title, message)),
    )

    tab = chalk_fill_ui.Fill001Tab.__new__(chalk_fill_ui.Fill001Tab)
    tab.root = None
    tab.output_dir = output_dir
    tab.matrix = matrix
    tab.manifest_path = manifest_path
    tab.active_task = task
    tab.active_run_record = attempt_path
    tab.active_plan_path = None
    tab.before_png_path = before_png
    tab.after_png_path = after_png
    tab.capture_region = dict(attempt["screen_roi"])
    tab.status_var = _StatusVar()
    tab._refresh_tasks = lambda: None

    tab.finalize_capture()

    assert len(ui_errors) == 1
    assert "PNG evidence не прошёл независимый audit." in ui_errors[0][1]
    assert png_audit_result["png_audit_status"] == "failed"
    assert (
        png_audit_result["coverage_fraction"] < 0.99
        or png_audit_result["leakage_pixels"] > 0
    )
    with capsys.disabled():
        print(
            "FILL-001 committed PNG audit: "
            f"coverage={png_audit_result['coverage_fraction']:.6%}, "
            f"leakage={png_audit_result['leakage_pixels']}, "
            f"status={png_audit_result['png_audit_status']}"
        )

    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    saved_attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    saved_matrix = load_fill001_matrix(manifest_path)
    capture_path = captures_dir / f"{TASK_ID}-capture.json"

    # Runtime binding must succeed even in the presence of the stale legacy
    # session, while the independent PNG gate must continue to reject capture.
    assert saved_report["runtime_binding_status"] == "passed"
    assert saved_report["runtime_binding"]["run_id"] == "6a17a297-ea14-4527-9527-bfd8de3bd335"
    assert saved_report["runtime_binding"]["exact_chalk"] == 1260
    assert saved_attempt["status"] == "execution_completed_pending_runtime_and_png_audit"
    assert saved_attempt["capture_path"] is None
    assert not capture_path.exists()
    pending = [task for task in saved_matrix["tasks"] if task.get("task_id") == TASK_ID]
    assert len(pending) == 1
    assert pending[0]["capture_status"] == "pending"
    assert pending[0].get("capture_path") is None
