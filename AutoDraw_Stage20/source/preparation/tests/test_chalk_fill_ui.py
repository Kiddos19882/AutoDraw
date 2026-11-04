from __future__ import annotations

from PIL import Image

import chalk_fill_ui


class _BrushTab:
    def __init__(self, region):
        self.region = region

    def get_calibration_profile(self):
        return {
            "screen_size": {"width": 1000, "height": 800},
            "regions": {"board_area": dict(self.region)},
        }

    def get_canvas_area(self):
        return dict(self.region)


def test_fill_ui_captures_actual_calibrated_roi_without_460x240_requirement(
    tmp_path, monkeypatch
):
    region = {"x": 120, "y": 80, "width": 581, "height": 304}
    screen = Image.new("RGB", (1000, 800), (240, 240, 240))
    tab = chalk_fill_ui.Fill001Tab.__new__(chalk_fill_ui.Fill001Tab)
    tab.output_dir = tmp_path
    tab.brush_tab = _BrushTab(region)
    tab.capture_region = dict(region)

    monkeypatch.setattr(chalk_fill_ui.ImageGrab, "grab", lambda: screen.copy())
    monkeypatch.setattr(chalk_fill_ui.pyautogui, "mouseUp", lambda: None)
    monkeypatch.setattr(chalk_fill_ui.pyautogui, "moveTo", lambda *_args: None)
    monkeypatch.setattr(chalk_fill_ui.time, "sleep", lambda *_args: None)
    monkeypatch.setattr(
        chalk_fill_ui,
        "_cursor_safe_point_outside_region",
        lambda *_args, **_kwargs: (10, 10),
    )

    path = tab._capture_board_png({"task_id": "roi-581x304"}, phase="after")

    with Image.open(path) as captured:
        assert captured.size == (581, 304)
        assert captured.getpixel((0, 0)) == (240, 240, 240)


def test_finalize_capture_writes_valid_capture_and_attempt_json(tmp_path, monkeypatch):
    import json
    import chalk_fill_capture_adapter

    task = {"task_id": "task-finalize"}
    matrix = {
        "schema_version": 2,
        "phase_id": "FILL001",
        "series_id": "SERIES",
        "shapes": ["rectangle"],
        "radii": [10],
        "repeats": [1],
        "tasks": [{**task, "capture_status": "pending"}],
        "matrix_signature": "frozen-signature",
    }
    report_path = tmp_path / "execution.json"
    report_path.write_text(json.dumps({
        "runtime_binding_status": "passed",
        "runtime_binding": {"session_file": str(tmp_path / "session.json")},
    }), encoding="utf-8")
    attempt_path = tmp_path / "attempt.json"
    attempt_path.write_text(json.dumps({
        "execution_report_path": str(report_path),
        "before_png": str(tmp_path / "before.png"),
        "after_png": str(tmp_path / "after.png"),
        "screen_roi": {"x": 1, "y": 2, "width": 581, "height": 304},
    }), encoding="utf-8")
    (tmp_path / "captures").mkdir()

    capture = {
        "run_id": "run-1",
        "exact_chalk": 5999,
        "coverage_fraction": 0.999,
        "leakage_pixels": 0,
        "png_audit_status": "passed",
        "runtime_binding_status": "passed",
    }
    monkeypatch.setattr(
        chalk_fill_capture_adapter,
        "build_fill001_capture_from_runtime",
        lambda *_args, **_kwargs: dict(capture),
    )
    monkeypatch.setattr(chalk_fill_ui, "load_fill001_matrix", lambda _path: {
        "matrix_signature": "frozen-signature"
    })
    monkeypatch.setattr(chalk_fill_ui, "write_fill001_matrix", lambda *_args, **_kwargs: None)

    tab = chalk_fill_ui.Fill001Tab.__new__(chalk_fill_ui.Fill001Tab)
    tab.active_task = task
    tab.active_run_record = attempt_path
    tab.manifest_path = tmp_path / "manifest.json"
    tab.output_dir = tmp_path
    tab.matrix = matrix
    tab.status_var = _Var()
    tab._refresh_tasks = lambda: None

    tab.finalize_capture()

    capture_path = tmp_path / "captures" / "task-finalize-capture.json"
    saved_capture = json.loads(capture_path.read_text(encoding="utf-8"))
    saved_attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    assert saved_capture["exact_chalk"] == 5999
    assert saved_attempt["status"] == "capture_accepted"
    assert saved_attempt["capture_path"] == str(capture_path)


class _Var:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


class _Root:
    def after(self, _delay, callback):
        self.callback = callback

    def deiconify(self):
        pass

    def lift(self):
        pass


def test_finalize_capture_retries_runtime_binding_before_png_acceptance(tmp_path, monkeypatch):
    import json
    import chalk_fill_capture_adapter
    import chalk_fill_runtime_binding

    task = {
        "phase_id": "FILL001",
        "series_id": "SERIES",
        "task_id": "task-rebind",
        "shape_id": "rectangle",
        "requested_radius": 10,
        "repeat_index": 1,
        "expected_strokes": 1,
        "plan_signature": "a" * 64,
        "target_mask_sha256": "b" * 64,
        "sampling_profile": {"profile_id": "P1", "sampling_step": 4, "delay_ms": 5},
    }
    matrix = {
        "schema_version": 2,
        "phase_id": "FILL001",
        "series_id": "SERIES",
        "shapes": ["rectangle"],
        "radii": [10],
        "repeats": [1],
        "tasks": [{**task, "capture_status": "pending"}],
        "matrix_signature": "frozen-signature",
    }
    session_path = tmp_path / "session.json"
    report_path = tmp_path / "execution.json"
    report_path.write_text(json.dumps({
        "experiment_context": task,
        "runtime_binding_status": "failed",
        "runtime_binding_error": "Bridge session не содержит bridge_diagnostics.",
    }), encoding="utf-8")
    attempt_path = tmp_path / "attempt.json"
    attempt_path.write_text(json.dumps({
        "execution_report_path": str(report_path),
        "before_png": str(tmp_path / "before.png"),
        "after_png": str(tmp_path / "after.png"),
        "screen_roi": {"x": 1, "y": 2, "width": 581, "height": 304},
    }), encoding="utf-8")
    output_dir = tmp_path / "fill001"
    (output_dir / "captures").mkdir(parents=True)

    runtime_binding = {
        "task_id": task["task_id"],
        "session_id": "session-1",
        "run_id": "run-1",
        "execution_id": "execution-1",
        "stroke_lifecycle_source": "pointer_observer",
        "observed_radius": 10,
        "sampling_profile": task["sampling_profile"],
        "executor_config": {"point_step_px": 4.0},
        "source_plan_file_sha256": "c" * 64,
        "pre_point_count": 10,
        "post_point_count": 25,
        "exact_chalk": 15,
        "event_count": 4,
        "bridge_failures": 0,
        "sequence_gaps": 0,
        "session_file": str(session_path),
        "session_file_sha256": "d" * 64,
        "bridge_run_file": str(tmp_path / "run.json"),
        "bridge_run_file_sha256": "e" * 64,
    }
    capture = {
        "run_id": "run-1",
        "exact_chalk": 15,
        "coverage_fraction": 1.0,
        "leakage_pixels": 0,
        "png_audit_status": "passed",
        "runtime_binding_status": "passed",
    }
    observed = {}
    monkeypatch.setattr(
        chalk_fill_runtime_binding,
        "find_fill001_runtime_binding",
        lambda _task, root, _report: (observed.update({"bridge_root": root}) or runtime_binding),
    )
    monkeypatch.setattr(
        chalk_fill_runtime_binding,
        "build_fill001_runtime_binding_summary",
        lambda binding: {
            "binding_method": "unique_run_in_executor_window",
            "session_file": binding["session_file"],
            "run_id": binding["run_id"],
            "exact_chalk": binding["exact_chalk"],
        },
    )
    monkeypatch.setattr(
        chalk_fill_capture_adapter,
        "build_fill001_capture_from_runtime",
        lambda *_args, **_kwargs: dict(capture),
    )
    monkeypatch.setattr(chalk_fill_ui, "load_fill001_matrix", lambda _path: {
        "matrix_signature": "frozen-signature"
    })
    monkeypatch.setattr(chalk_fill_ui, "write_fill001_matrix", lambda *_args, **_kwargs: None)

    tab = chalk_fill_ui.Fill001Tab.__new__(chalk_fill_ui.Fill001Tab)
    tab.active_task = task
    tab.active_run_record = attempt_path
    tab.manifest_path = tmp_path / "manifest.json"
    tab.output_dir = output_dir
    tab.matrix = matrix
    tab.status_var = _Var()
    tab._refresh_tasks = lambda: None

    tab.finalize_capture()

    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    saved_capture = json.loads(
        (output_dir / "captures" / "task-rebind-capture.json").read_text(encoding="utf-8")
    )
    assert saved_report["runtime_binding_status"] == "passed"
    assert saved_report["runtime_binding"]["run_id"] == "run-1"
    assert saved_capture["exact_chalk"] == 15
    assert observed["bridge_root"] == tmp_path / "game_monitor_bridge"


def test_executor_completion_and_after_png_keep_attempt_record_valid(tmp_path):
    import json

    attempt_path = tmp_path / "attempt.json"
    attempt_path.write_text('{"status": "running"}', encoding="utf-8")
    after_png = tmp_path / "after.png"
    after_png.write_bytes(b"png-placeholder")

    tab = chalk_fill_ui.Fill001Tab.__new__(chalk_fill_ui.Fill001Tab)
    tab.active_task = {"task_id": "task-1"}
    tab.active_run_record = attempt_path
    tab.root = _Root()
    tab.status_var = _Var()
    tab._capture_board_png = lambda _task, *, phase: after_png

    assert tab.handle_executor_finished({"status": "completed"}, tmp_path / "report.json") is True
    completed = json.loads(attempt_path.read_text(encoding="utf-8"))
    assert completed["status"] == "execution_completed_pending_runtime_and_png_audit"
    assert tab.root.callback is not None

    tab._capture_after_png()
    saved = json.loads(attempt_path.read_text(encoding="utf-8"))
    assert saved["after_png"] == str(after_png)
    assert saved["after_png_captured_at_utc"]
