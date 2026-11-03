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
