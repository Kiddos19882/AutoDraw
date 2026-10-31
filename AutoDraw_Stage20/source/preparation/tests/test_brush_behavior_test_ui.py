from __future__ import annotations

from pathlib import Path

import pytest

import brush_behavior_test_ui as brush_ui
from brush_behavior_test_ui import TEST_CASES, build_brush_test_drawing_plan, build_brush_test_record

def _make_test_tab():
    """Build a UI controller shell with the same lifecycle defaults as __init__ without creating Tk."""
    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
    tab._start_executor_after_brush_drag = False
    tab._brush_drag_state = None
    tab._brush_drag_after_id = None
    tab._brush_drag_countdown_id = None
    tab._brush_hotkey_listener = None
    tab._brush_drag_mouse_down = False
    tab._brush_drag_purpose = "set_brush_size"
    tab._experiment_requested_brush = None
    tab._postdraw_final_status = "completed"
    tab._postdraw_final_reason = ""
    tab.experiment_phases = {}
    tab.experiment_dir = None
    tab.current_plan_path = None
    tab.execution_report_path = None
    tab.execution_report = None
    tab.game_monitor_report_path = None
    tab.game_monitor_summary = None
    tab.get_calibration_profile = None
    tab._automated_preclear_active = False
    tab._automated_preclear_after_id = None
    tab._automated_postdraw_active = False
    tab._automated_postdraw_stop_requested = False
    tab._automated_postdraw_after_id = None
    return tab



def test_brush_test_record_contains_reproducible_stroke_template() -> None:
    record = build_brush_test_record(
        brush_value=7,
        test_case="Горизонтальные линии",
        canvas_area={"x": 100, "y": 200, "width": 646, "height": 323},
        screen_area={"x": 500, "y": 300, "width": 646, "height": 323},
        screenshot_path="capture.png",
        drawing_plan_path="brush-plan.json",
        drawing_plan={"strokes": [{"name": "line"}]},
        execution_report_path="execution.json",
        execution_report={"status": "completed", "stroke_count": 5},
        measurements={
            "observed_stroke_count": 4,
            "visible_stroke_names": ["horizontal_10", "horizontal_20"],
            "missing_stroke_names": ["horizontal_50"],
            "measured_footprint_width_px": 7,
            "paint_points_before": 6000,
            "paint_points_after": 5900,
        },
        notes="Проверка кисти 7",
        outcome="partial",
    )

    assert record["schema_version"] == 1
    assert record["record_type"] == "autodraw_brush_behavior_observation"
    assert record["brush_value"] == 7
    assert record["test_case"]["id"] == "horizontal_lengths"
    assert len(record["planned_strokes"]) == 5
    assert record["planned_strokes"][2]["points"] == [[20, 70], [70, 70]]
    assert record["screen_area"]["width"] == 646
    assert record["board_selection_origin"] == {"x": 100, "y": 200}
    assert record["board_selection_size"] == {"width": 646, "height": 323}
    assert record["screen_resolution"] is None
    assert record["screenshot_path"] == "capture.png"
    assert record["drawing_plan_path"] == "brush-plan.json"
    assert record["drawing_plan"]["strokes"][0]["name"] == "line"
    assert record["execution_report_path"] == "execution.json"
    assert record["execution_report"]["stroke_count"] == 5
    assert record["measurement_fields"]["visible_stroke_names"] == ["horizontal_10", "horizontal_20"]
    assert record["measurement_fields"]["missing_stroke_names"] == ["horizontal_50"]
    assert record["measurement_fields"]["measured_footprint_width_px"] == 7
    assert record["measurement_fields"]["paint_points_before"] == 6000
    assert record["outcome"] == "partial"
    assert record["interpretation"]["automatic_execution_allowed"] is False


def test_brush_test_record_can_link_passive_game_monitor_evidence() -> None:
    summary = {
        "monitor_version": "0.1.2",
        "event_count": 411,
        "dropped_events": 0,
        "draw_sample_count": 145,
        "interpretation": "passive_browser_telemetry_not_direct_paint_resource_measurement",
    }
    record = build_brush_test_record(
        brush_value=14,
        test_case="Непрерывные повороты",
        game_monitor_report_path="monitor-report.json",
        game_monitor_summary=summary,
    )
    assert record["game_monitor_report_path"] == "monitor-report.json"
    assert record["game_monitor_summary"]["event_count"] == 411
    assert record["game_monitor_summary"]["interpretation"].endswith("not_direct_paint_resource_measurement")


def test_game_monitor_summary_extracts_only_active_draw_radii_and_detects_match() -> None:
    document = {
        "monitorVersion": "0.1.2",
        "eventCount": 5,
        "droppedEvents": 0,
        "errors": [],
        "boardDetected": True,
        "events": [
            {"type": "DRAW_SAMPLE", "source": "onDrawStart", "board": {"radius": [0, 30]}},
            {"type": "DRAW_SAMPLE", "source": "onDrawing_wrapper", "board": {"radius": [0, 7, 7]}},
            {"type": "DRAW_SAMPLE", "source": "onDrawing_wrapper", "board": {"radius": [0, 7, 7]}},
            {"type": "POINTER_DOWN_CANDIDATE"},
            {"type": "POINTER_UP_CANDIDATE"},
        ],
    }
    summary = brush_ui.summarize_game_monitor_report(document, requested_brush_value=7)
    assert summary["observed_draw_radii"] == [7]
    assert summary["brush_value_status"] == "match"
    assert summary["brush_value_matches_requested"] is True
    assert summary["drawing_sample_count"] == 2
    assert summary["draw_sample_count"] == 3


def test_game_monitor_summary_detects_requested_vs_actual_brush_mismatch() -> None:
    document = {
        "events": [
            {"type": "DRAW_SAMPLE", "source": "onDrawing_wrapper", "board": {"radius": [0, 13, 13]}},
        ],
    }
    summary = brush_ui.summarize_game_monitor_report(document, requested_brush_value=14)
    assert summary["observed_draw_radii"] == [13]
    assert summary["brush_value_status"] == "mismatch"
    assert summary["brush_value_matches_requested"] is False


def test_game_monitor_summary_marks_mixed_brushes_and_missing_draw_samples() -> None:
    mixed = brush_ui.summarize_game_monitor_report({
        "events": [
            {"type": "DRAW_SAMPLE", "source": "onDrawing_wrapper", "board": {"radius": [0, 6]}},
            {"type": "DRAW_SAMPLE", "source": "onDrawing_wrapper", "board": {"radius": [0, 13]}},
        ],
    }, requested_brush_value=6)
    assert mixed["brush_value_status"] == "mixed"
    assert mixed["observed_draw_radii"] == [6, 13]

    empty = brush_ui.summarize_game_monitor_report({"events": []}, requested_brush_value=6)
    assert empty["brush_value_status"] == "unavailable"
    assert empty["brush_value_matches_requested"] is None


def test_loading_game_monitor_report_persists_link_and_warns_on_radius_mismatch(monkeypatch, tmp_path) -> None:
    import json

    class Value:
        def __init__(self, value=""):
            self.value = value
        def get(self):
            return self.value
        def set(self, value):
            self.value = value

    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
    tab.root = object()
    tab.output_dir = tmp_path / "output"
    tab._experiment_requested_brush = 14
    tab.experiment_phases = {"brush_setup": {"requested_value": 14}}
    tab.brush_var = Value("30")
    tab.status_var = Value()
    tab.game_monitor_report_path = None
    tab.game_monitor_summary = None
    writes = []
    tab._write_experiment_manifest = lambda: writes.append(
        (tab.game_monitor_report_path, tab.game_monitor_summary)
    ) or (tmp_path / "experiment.json")
    report_path = tmp_path / "monitor.json"
    report_path.write_text(json.dumps({
        "monitorVersion": "0.1.2",
        "events": [
            {"type": "DRAW_SAMPLE", "source": "onDrawing_wrapper", "board": {"radius": [0, 13]}},
        ],
    }), encoding="utf-8")
    warnings = []
    monkeypatch.setattr(brush_ui.filedialog, "askopenfilename", lambda **kwargs: str(report_path))
    monkeypatch.setattr(brush_ui.messagebox, "showwarning", lambda *args, **kwargs: warnings.append(args))

    tab.load_game_monitor_report()

    assert tab.game_monitor_report_path == report_path.resolve()
    assert tab.game_monitor_summary["brush_value_status"] == "mismatch"
    assert len(writes) == 1
    assert writes[0][0] == report_path.resolve()
    assert writes[0][1]["observed_draw_radii"] == [13]
    assert warnings and warnings[0][0] == "Размер кисти не совпал"
    assert "Манифест обновлён" in tab.status_var.value or "Манифест обновлён" in warnings[0][1]


def test_experiment_manifest_persists_chalk_matrix_identity_and_cell(tmp_path):
    import json

    class Value:
        def __init__(self, value=""):
            self.value = value
        def get(self):
            return self.value

    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
    tab.experiment_dir = tmp_path
    tab.get_calibration_profile = lambda: None
    tab._experiment_id = "experiment-unique-001"
    tab._chalk_matrix_metadata = brush_ui.build_chalk_radius_matrix_metadata(
        series_id="matrix-20261031", block=2, requested_radius=15
    )
    tab.case_var = Value("Расход краски — серия длинных линий")
    tab.brush_var = Value("15")
    tab._experiment_requested_brush = 15
    tab.current_plan_path = None
    tab.execution_report_path = None
    tab.execution_report = None
    tab.game_monitor_report_path = None
    tab.game_monitor_summary = None
    tab.experiment_phases = {}

    manifest_path = tab._write_experiment_manifest()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["experiment_id"] == "experiment-unique-001"
    assert manifest["chalk_radius_matrix"]["series_id"] == "matrix-20261031"
    assert manifest["chalk_radius_matrix"]["block"] == 2
    assert manifest["chalk_radius_matrix"]["requested_radius"] == 15


def test_brush_test_record_defaults_unmeasured_paint_points_to_none() -> None:
    record = build_brush_test_record(brush_value=7, test_case="Горизонтальные линии")

    assert record["measurement_fields"]["paint_points_before"] is None
    assert record["measurement_fields"]["paint_points_after"] is None


@pytest.mark.parametrize("brush_value", [0, 31, -1, True, 7.5])
def test_brush_test_record_rejects_invalid_brush_value(brush_value) -> None:
    with pytest.raises(ValueError):
        build_brush_test_record(brush_value=brush_value, test_case="Диагонали")


def test_all_test_cases_have_named_strokes_with_two_endpoints() -> None:
    assert len(TEST_CASES) >= 5
    for scenario in TEST_CASES.values():
        assert scenario["strokes"]
        for stroke in scenario["strokes"]:
            assert stroke["name"]
            assert len(stroke["points"]) >= 2
            assert all(len(point) == 2 for point in stroke["points"])
            assert len(stroke["points"][1]) == 2


def test_new_polyline_scenarios_preserve_intermediate_points_in_executor_plan() -> None:
    for case_name in ("Непрерывные повороты", "Замкнутый контур одной траекторией"):
        scenario = TEST_CASES[case_name]
        assert any(len(stroke["points"]) > 2 for stroke in scenario["strokes"])
        plan = build_brush_test_drawing_plan(case_name, (460, 240))
        assert len(plan["strokes"]) == len(scenario["strokes"])
        for source, planned in zip(scenario["strokes"], plan["strokes"]):
            assert len(planned["points"]) == len(source["points"])
            assert planned["points"] == [
                {"x": float(x), "y": float(y)} for x, y in source["points"]
            ]


def test_all_brush_scenarios_fit_engine_logical_board_and_have_unique_stroke_names() -> None:
    for scenario in TEST_CASES.values():
        names = [stroke["name"] for stroke in scenario["strokes"]]
        assert len(names) == len(set(names))
        plan = build_brush_test_drawing_plan(
            next(name for name, value in TEST_CASES.items() if value is scenario),
            (460, 240),
            coordinate_system="logical_board_pixels",
        )
        assert plan["canvas"] == {"width": 460, "height": 240}


def test_parallel_spacing_case_has_controlled_centerline_distances() -> None:
    strokes = TEST_CASES["Параллельные линии и расстояние"]["strokes"]
    pairs = [(strokes[index]["points"][0][1], strokes[index + 1]["points"][0][1])
             for index in range(0, len(strokes), 2)]
    assert [second - first for first, second in pairs] == [4, 8, 16, 24]


def test_brush_test_record_rejects_unknown_case() -> None:
    with pytest.raises(ValueError, match="Неизвестный тест"):
        build_brush_test_record(brush_value=7, test_case="не существует")



def test_brush_test_plan_uses_standard_executor_schema_and_canvas_dimensions() -> None:
    plan = build_brush_test_drawing_plan("Горизонтальные линии", (646, 323))

    assert plan["coordinate_system"] == "local_canvas_pixels"
    assert plan["canvas"] == {"width": 646, "height": 323}
    assert plan["width"] == 646
    assert len(plan["strokes"]) == 5
    assert plan["strokes"][0]["points"] == [{"x": 20.0, "y": 20.0}, {"x": 30.0, "y": 20.0}]
    assert plan["strokes"][0]["metadata"]["role"] == "brush_behavior_test"


def test_brush_test_plan_can_use_explicit_logical_board_coordinates() -> None:
    plan = build_brush_test_drawing_plan(
        "Расход краски — серия длинных линий",
        (460, 240),
        coordinate_system="logical_board_pixels",
    )

    assert plan["coordinate_system"] == "logical_board_pixels"
    assert plan["canvas"] == {"width": 460, "height": 240}
    assert plan["strokes"][0]["points"][-1] == {"x": 420.0, "y": 18.0}
    assert plan["strokes"][0]["metadata"]["line_extension_px_override"] == 0.0


def test_board_boundary_probe_reaches_all_four_inclusive_board_edges() -> None:
    plan = build_brush_test_drawing_plan(
        "Проверка границ доски",
        (460, 240),
        coordinate_system="logical_board_pixels",
    )

    assert len(plan["strokes"]) == 4
    endpoints = [stroke["points"][-1] for stroke in plan["strokes"]]
    assert endpoints == [
        {"x": 460.0, "y": 120.0},
        {"x": 0.0, "y": 120.0},
        {"x": 230.0, "y": 240.0},
        {"x": 230.0, "y": 0.0},
    ]
    assert all(stroke["metadata"]["line_extension_px_override"] == 0.0 for stroke in plan["strokes"])


def test_logical_brush_plan_rejects_points_beyond_supplied_canvas_bounds() -> None:
    with pytest.raises(ValueError, match="выходит за пределы"):
        build_brush_test_drawing_plan(
            "Длинные изолированные линии", (419, 240),
            coordinate_system="logical_board_pixels",
        )


def test_brush_test_plan_rejects_points_outside_canvas() -> None:
    with pytest.raises(ValueError, match="выходит за пределы"):
        build_brush_test_drawing_plan("Горизонтальные линии", (100, 100))


def test_brush_test_plan_rejects_invalid_canvas_size() -> None:
    with pytest.raises(ValueError, match="положительным"):
        build_brush_test_drawing_plan("Диагонали", (0, 323))


def test_brush_test_record_persists_screen_and_brush_calibration_metadata() -> None:
    record = build_brush_test_record(
        brush_value=14,
        test_case="Короткие линии и точки",
        canvas_area={"x": 504, "y": 280, "width": 645, "height": 328},
        screen_area={"x": 0, "y": 0, "width": 1920, "height": 1080},
        screen_resolution={"width": 1920, "height": 1080},
        brush_control={"type": "linear_slider", "min_value": 1, "max_value": 30, "start": [100, 500], "end": [390, 500]},
    )
    assert record["screen_resolution"] == {"width": 1920, "height": 1080}
    assert record["board_selection_origin"] == {"x": 504, "y": 280}
    assert record["board_selection_size"] == {"width": 645, "height": 328}
    assert record["screen_area"] == {"x": 0, "y": 0, "width": 1920, "height": 1080}
    assert record["brush_control"]["start"] == [100, 500]
    assert record["brush_control"]["end"] == [390, 500]


def test_paint_consumption_case_has_six_non_overlapping_long_lines_within_default_game_canvas() -> None:
    scenario = TEST_CASES["Расход краски — серия длинных линий"]
    assert scenario["id"] == "paint_consumption_long_lines"
    assert len(scenario["strokes"]) == 6
    total_length = 0
    for index, stroke in enumerate(scenario["strokes"]):
        start, end = stroke["points"]
        expected_y = 18 + index * 36
        assert start == [20, expected_y]
        assert end == [420, expected_y]
        assert 0 <= start[0] < 460 and 0 <= end[0] < 460
        assert 0 <= start[1] < 240 and 0 <= end[1] < 240
        if index:
            previous_y = scenario["strokes"][index - 1]["points"][0][1]
            assert expected_y - previous_y == 36
        total_length += abs(end[0] - start[0]) + abs(end[1] - start[1])
    assert total_length == 2400


def test_paint_consumption_plan_uses_all_six_non_overlapping_long_lines() -> None:
    plan = build_brush_test_drawing_plan("Расход краски — серия длинных линий", (460, 240))
    assert len(plan["strokes"]) == 6
    assert plan["strokes"][-1]["name"] == "consumption_line_06"


def test_set_brush_size_uses_profile_coordinates_and_minimizes_before_drag(monkeypatch) -> None:
    class Value:
        def __init__(self, value=""):
            self.value = value
        def get(self):
            return self.value
        def set(self, value):
            self.value = value

    class Root:
        def __init__(self):
            self.minimized = False
            self.scheduled = []
        def iconify(self):
            self.minimized = True
        def after(self, delay, callback):
            self.scheduled.append((delay, callback))

    tab = _make_test_tab()
    tab.root = Root()
    tab.brush_var = Value("14")
    tab.slider_start_var = Value()
    tab.slider_end_var = Value()
    tab.status_var = Value()
    tab.get_brush_control = lambda: {
        "mode": "slider", "start": [100, 500], "end": [390, 500],
        "screen_size": {"width": 1920, "height": 1080},
    }
    tab._read_live_brush_radius = lambda: {"radius": 30, "session_id": "test"}
    tab.brush_slider_start = None
    tab.brush_slider_end = None
    class FakeListener:
        def __init__(self, on_press):
            self.on_press = on_press
            self.daemon = False
            self.started = False
            self.stopped = False
        def start(self):
            self.started = True
        def stop(self):
            self.stopped = True

    monkeypatch.setattr(brush_ui.platform, "system", lambda: "Windows")
    monkeypatch.setattr(brush_ui.keyboard, "Listener", FakeListener)

    assert tab.set_brush_size() is True
    assert tab.slider_start_var.get() == "100, 500"
    assert tab.slider_end_var.get() == "390, 500"
    assert tab.root.minimized is True
    assert len(tab.root.scheduled) == 1
    delay, callback = tab.root.scheduled[0]
    assert delay == 3000

    # Running the scheduled callback would control the real mouse, so assert
    # only that the expected action is queued and do not invoke it in a unit test.


def test_set_brush_size_rejects_preset_click_mode(monkeypatch) -> None:
    class Value:
        def __init__(self, value=""):
            self.value = value
        def get(self):
            return self.value
        def set(self, value):
            self.value = value

    class Root:
        def __init__(self):
            self.minimized = False
            self.scheduled = []
        def iconify(self):
            self.minimized = True
        def deiconify(self):
            self.minimized = False
        def lift(self):
            pass
        def after(self, delay, callback):
            self.scheduled.append((delay, callback))

    tab = _make_test_tab()
    tab.root = Root()
    tab.brush_var = Value("14")
    tab.slider_start_var = Value()
    tab.slider_end_var = Value()
    tab.status_var = Value()
    tab.get_brush_control = lambda: {
        "mode": "presets", "presets": {"7": [10, 20], "14": [30, 40], "20": [50, 60]}
    }
    tab._read_live_brush_radius = lambda: {"radius": 30, "session_id": "test"}
    monkeypatch.setattr(brush_ui.platform, "system", lambda: "Windows")
    warnings = []
    monkeypatch.setattr(brush_ui.messagebox, "showwarning", lambda *args, **kwargs: warnings.append(args))

    assert tab.set_brush_size() is False
    assert tab.root.minimized is False
    assert tab.root.scheduled == []
    assert warnings
    assert "перетаскиванием" in warnings[0][1]



def test_brush_drag_alt_cancellation_releases_mouse_without_real_input() -> None:
    class Value:
        def __init__(self, value=""):
            self.value = value
        def set(self, value):
            self.value = value

    class FakeUser32:
        def __init__(self):
            self.events = []
        def mouse_event(self, flags, *_args):
            self.events.append(flags)

    class Root:
        def __init__(self):
            self.cancelled = []
            self.restored = False
        def after_cancel(self, callback_id):
            self.cancelled.append(callback_id)
        def deiconify(self):
            self.restored = True
        def lift(self):
            pass

    tab = _make_test_tab()
    tab.root = Root()
    tab.status_var = Value()
    tab._brush_drag_after_id = "scheduled-step"
    tab._brush_drag_countdown_id = None
    tab._brush_hotkey_listener = None
    tab._brush_drag_mouse_down = True
    user32 = FakeUser32()
    tab._brush_drag_state = {
        "user32": user32,
        "target": (250, 500),
        "brush": 14,
    }

    assert tab._on_brush_workflow_stop_key() == "break"

    assert user32.events == [0x0004]  # MOUSEEVENTF_LEFTUP
    assert tab._brush_drag_state is None
    assert tab._brush_drag_mouse_down is False
    assert tab._brush_drag_after_id is None
    assert tab.root.cancelled == ["scheduled-step"]
    assert tab.root.restored is True
    assert "остановлено по Alt" in tab.status_var.value


def test_brush_drag_completion_releases_mouse_and_does_not_claim_verified_value() -> None:
    class Value:
        def __init__(self, value=""):
            self.value = value
        def set(self, value):
            self.value = value

    class FakeUser32:
        def __init__(self):
            self.events = []
        def mouse_event(self, flags, *_args):
            self.events.append(flags)

    class Root:
        def after_cancel(self, _callback_id):
            raise AssertionError("No pending callback expected")

    tab = _make_test_tab()
    tab.root = Root()
    tab.status_var = Value()
    tab._brush_drag_after_id = None
    tab._brush_drag_countdown_id = None
    tab._brush_hotkey_listener = None
    tab._brush_drag_mouse_down = True
    user32 = FakeUser32()
    tab._brush_drag_state = {
        "user32": user32,
        "target": (250, 500),
        "brush": 14,
    }

    tab._finish_brush_drag()

    assert user32.events == [0x0004]
    assert tab._brush_drag_state is None
    assert tab._brush_drag_mouse_down is False
    assert "не подтверждён игрой" in tab.status_var.value



def test_automatic_brush_setup_requires_visual_confirmation_before_executor(monkeypatch):
    class Value:
        def __init__(self, value=""):
            self.value = value
        def set(self, value):
            self.value = value

    class Root:
        def __init__(self):
            self.restored = False
            self.scheduled = []
        def deiconify(self):
            self.restored = True
        def lift(self):
            pass
        def after(self, delay, callback):
            self.scheduled.append((delay, callback))
            return "scheduled"

    tab = _make_test_tab()
    tab.root = Root()
    tab.status_var = Value()
    tab._start_executor_after_brush_drag = True
    tab.on_brush_ready = lambda brush: tab.status_var.set(f"executor:{brush}")
    tab._brush_feedback_state = {
        "requested_radius": 10, "start_30": (100, 500), "end_1": (390, 500),
        "current_point": (300, 500), "attempt": 0, "observations": [],
    }
    monkeypatch.setattr(brush_ui.messagebox, "askyesno", lambda *args, **kwargs: False)

    tab._complete_brush_radius_feedback({
        "radius": 10, "session_id": "session", "observed_at_utc": "2026-10-31T00:00:00+00:00"
    })

    assert tab.root.restored is True
    assert tab.experiment_phases["brush_setup"]["status"] == "declined_by_user"
    assert tab._start_executor_after_brush_drag is False
    assert tab.root.scheduled == []


def test_automatic_brush_setup_starts_executor_only_after_exact_monitor_match(monkeypatch):
    class Value:
        def __init__(self, value=""):
            self.value = value
        def set(self, value):
            self.value = value

    class Root:
        def __init__(self):
            self.restored = False
            self.scheduled = []
        def deiconify(self):
            self.restored = True
        def lift(self):
            pass
        def after(self, delay, callback):
            self.scheduled.append((delay, callback))
            return "scheduled"

    tab = _make_test_tab()
    tab.root = Root()
    tab.status_var = Value()
    tab._start_executor_after_brush_drag = True
    started = []
    tab.on_brush_ready = lambda brush: started.append(brush)
    tab._brush_feedback_state = {
        "requested_radius": 10, "start_30": (100, 500), "end_1": (390, 500),
        "current_point": (300, 500), "attempt": 0, "observations": [],
    }
    monkeypatch.setattr(brush_ui.messagebox, "askyesno", lambda *args, **kwargs: True)

    tab._complete_brush_radius_feedback({
        "radius": 10, "session_id": "session", "observed_at_utc": "2026-10-31T00:00:00+00:00"
    })

    assert tab.experiment_phases["brush_setup"]["status"] == "confirmed_by_user"
    assert tab.experiment_phases["brush_setup"]["confirmation_method"] == "game_monitor_exact_radius_plus_user_visual_check"
    assert len(tab.root.scheduled) == 1
    delay, callback = tab.root.scheduled[0]
    assert delay == 0
    callback()
    assert started == [10]


def test_game_monitor_radius_mismatch_schedules_automatic_correction(monkeypatch):
    class Value:
        def __init__(self, value=""):
            self.value = value
        def set(self, value):
            self.value = value

    class Root:
        def __init__(self):
            self.minimized = False
            self.scheduled = []
        def iconify(self):
            self.minimized = True
        def after(self, delay, callback):
            self.scheduled.append((delay, callback))
            return "scheduled"

    tab = _make_test_tab()
    tab.root = Root()
    tab.status_var = Value()
    current = (350, 500)
    tab._brush_feedback_state = {
        "requested_radius": 5,
        "start_30": (100, 500), "end_1": (390, 500),
        "high_point": (100, 500), "high_radius": 30,
        "low_point": (390, 500), "low_radius": 1,
        "current_point": current, "attempt": 0, "poll_count": 0,
        "observations": [], "await_after_utc": "2026-10-31T00:00:00+00:00",
    }
    tab._read_live_brush_radius = lambda **kwargs: {
        "radius": 4, "session_id": "session", "observed_at_utc": "2026-10-31T00:00:01+00:00"
    }
    tab._start_brush_hotkey_listener = lambda: None
    scheduled = []
    tab._begin_brush_drag = lambda start, x, y, brush: scheduled.append((start, x, y, brush))

    tab._poll_brush_radius_feedback()

    assert scheduled
    start, target_x, target_y, brush = scheduled[0]
    assert start == current
    assert target_x < current[0]  # Radius 4 is too small: move towards radius 30.
    assert target_y == current[1]
    assert brush == 5
    assert tab._brush_feedback_state["attempt"] == 1
    assert tab.root.minimized is True


def test_bridge_status_reader_uses_fresh_active_heartbeat(tmp_path):
    import json
    from datetime import datetime, timezone
    from pathlib import Path

    tab = _make_test_tab()
    tab.output_dir = Path(tmp_path)
    session_dir = tmp_path / "game_monitor_bridge" / "session-1"
    session_dir.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    record = {
        "session_id": "session-1",
        "bridge_diagnostics": {
            "connection_closed": False,
            "last_message_type": "heartbeat",
            "last_message_at_utc": now,
            "last_monitor_status": {"snapshot": {"currentRadius": 4, "radius": [30, 4]}},
        },
    }
    (session_dir / "session.json").write_text(json.dumps(record), encoding="utf-8")

    observed = tab._read_live_brush_radius()

    assert observed is not None
    assert observed["radius"] == 4
    assert observed["session_id"] == "session-1"


def test_alt_is_not_consumed_when_no_brush_drag_is_active() -> None:
    tab = _make_test_tab()
    tab._brush_drag_state = None
    assert tab._on_brush_workflow_stop_key() is None



def test_alt_cancels_pending_brush_countdown_and_restores_window(monkeypatch) -> None:
    class Value:
        def __init__(self, value=""):
            self.value = value
        def set(self, value):
            self.value = value

    class Listener:
        def __init__(self):
            self.stopped = False
        def stop(self):
            self.stopped = True

    class Root:
        def __init__(self):
            self.cancelled = []
            self.restored = False
        def after_cancel(self, callback_id):
            self.cancelled.append(callback_id)
        def deiconify(self):
            self.restored = True
        def lift(self):
            pass

    tab = _make_test_tab()
    tab.root = Root()
    tab.status_var = Value()
    tab._brush_drag_state = None
    tab._brush_drag_after_id = None
    tab._brush_drag_countdown_id = "countdown"
    tab._brush_drag_mouse_down = False
    tab._brush_hotkey_listener = Listener()
    listener = tab._brush_hotkey_listener

    tab.cancel_brush_drag()

    assert tab.root.cancelled == ["countdown"]
    assert tab._brush_drag_countdown_id is None
    assert listener.stopped is True
    assert tab._brush_hotkey_listener is None
    assert tab.root.restored is True
    assert "отменена по Alt" in tab.status_var.value


def test_global_alt_listener_schedules_cancellation_on_tk_thread(monkeypatch) -> None:
    class FakeKeyboard:
        alt = object()
        alt_l = object()
        alt_r = object()

    class Listener:
        def __init__(self, on_press):
            self.on_press = on_press
            self.daemon = False
            self.started = False
        def start(self):
            self.started = True
        def stop(self):
            pass

    class Root:
        def __init__(self):
            self.scheduled = []
        def after(self, delay, callback):
            self.scheduled.append((delay, callback))

    tab = _make_test_tab()
    tab.root = Root()
    tab._brush_hotkey_listener = None
    monkeypatch.setattr(brush_ui.keyboard, "Key", FakeKeyboard)
    monkeypatch.setattr(brush_ui.keyboard, "Listener", Listener)

    tab._start_brush_hotkey_listener()
    listener = tab._brush_hotkey_listener
    listener.on_press(FakeKeyboard.alt_l)

    assert listener.started is True
    assert tab.root.scheduled and tab.root.scheduled[0][0] == 0



def test_brush_restore_starts_at_tested_value_and_drags_to_calibrated_30(monkeypatch) -> None:
    class Value:
        def __init__(self, value=""):
            self.value = value
        def get(self):
            return self.value
        def set(self, value):
            self.value = value

    class Root:
        def __init__(self):
            self.minimized = False
            self.scheduled = []
        def iconify(self):
            self.minimized = True
        def deiconify(self):
            self.minimized = False
        def lift(self):
            pass
        def after(self, delay, callback):
            self.scheduled.append((delay, callback))
            return "restore-countdown"

    class Listener:
        def __init__(self, on_press):
            self.on_press = on_press
        def start(self):
            pass
        def stop(self):
            pass

    tab = _make_test_tab()
    tab.root = Root()
    tab.brush_var = Value("14")
    tab.status_var = Value()
    tab.get_brush_control = lambda: {
        "mode": "slider", "start": [100, 500], "end": [390, 500]
    }
    captured = []
    tab._start_scheduled_brush_drag = lambda start, x, y, brush: captured.append((start, x, y, brush))
    monkeypatch.setattr(brush_ui.platform, "system", lambda: "Windows")
    monkeypatch.setattr(brush_ui.keyboard, "Listener", Listener)

    assert tab._schedule_brush_restore_30(14) is True
    assert tab.root.minimized is True
    assert tab.brush_var.get() == "30"
    assert tab._brush_drag_purpose == "restore_brush_30"
    assert len(tab.root.scheduled) == 1
    delay, callback = tab.root.scheduled[0]
    assert delay == 3000
    callback()

    expected_start = brush_ui.calculate_slider_target((100, 500), (390, 500), 14)
    assert captured == [(expected_start, 100, 500, 30)]


def test_postdraw_completion_notification_is_shown_after_restore_drag(monkeypatch, tmp_path) -> None:
    class Value:
        def __init__(self, value=""):
            self.value = value
        def get(self):
            return self.value
        def set(self, value):
            self.value = value

    class Root:
        def __init__(self):
            self.restored = False
        def deiconify(self):
            self.restored = True
        def lift(self):
            pass

    tab = _make_test_tab()
    tab.root = Root()
    tab.status_var = Value()
    tab.case_var = Value("Горизонтальные линии")
    tab.brush_var = Value("30")
    tab.experiment_dir = tmp_path
    tab._experiment_requested_brush = 14
    tab.get_calibration_profile = lambda: None
    notifications = []
    monkeypatch.setattr(brush_ui.messagebox, "showinfo", lambda *args, **kwargs: notifications.append(("info", args)))
    monkeypatch.setattr(brush_ui.messagebox, "showwarning", lambda *args, **kwargs: notifications.append(("warning", args)))

    tab._record_brush_restore_result(
        "drag_completed_unverified",
        "Перетаскивание завершено; проверь размер в игре.",
        state={"start": (250, 500), "target": (100, 500)},
    )

    manifest = __import__("json").loads((tmp_path / "experiment.json").read_text(encoding="utf-8"))
    assert manifest["brush_value_requested"] == 14
    assert manifest["phases"]["restore_brush_30"]["status"] == "drag_completed_unverified"
    assert tab.root.restored is True
    assert notifications and notifications[0][0] == "info"
    assert "Тест завершён" in tab.status_var.value


def test_paint_consumption_scenario_uses_non_overlapping_lines_for_maximum_brush() -> None:
    strokes = TEST_CASES["Расход краски — серия длинных линий"]["strokes"]
    assert len(strokes) == 6
    ys = [stroke["points"][0][1] for stroke in strokes]
    assert [second - first for first, second in zip(ys, ys[1:])] == [36] * 5
    assert all(stroke["points"] == [[20, y], [420, y]] for stroke, y in zip(strokes, ys))
    assert all(
        second - first > brush_ui.MAX_BRUSH_LINE_WIDTH_LOGICAL_PX
        for first, second in zip(ys, ys[1:])
    )


def test_long_isolated_line_scenario_covers_multiple_lengths_and_axes() -> None:
    strokes = TEST_CASES["Длинные изолированные линии"]["strokes"]
    lengths = {
        (abs(item["points"][-1][0] - item["points"][0][0]),
         abs(item["points"][-1][1] - item["points"][0][1]))
        for item in strokes
    }
    assert (400, 0) in lengths
    assert (0, 180) in lengths
    plan = build_brush_test_drawing_plan("Длинные изолированные линии", (460, 240))
    assert len(plan["strokes"]) == len(strokes)


def test_repeated_coverage_scenario_reuses_exact_path_and_keeps_control_line() -> None:
    strokes = TEST_CASES["Повторное покрытие одного следа"]["strokes"]
    repeated = [item["points"] for item in strokes[:3]]
    assert repeated[0] == repeated[1] == repeated[2]
    assert strokes[3]["points"] != repeated[0]
    plan = build_brush_test_drawing_plan("Повторное покрытие одного следа", (460, 240))
    assert len(plan["strokes"]) == 4


def test_cross_section_scenario_contains_horizontal_and_vertical_intersections() -> None:
    strokes = TEST_CASES["Поперечный профиль и пересечения"]["strokes"]
    assert len(strokes) == 4
    horizontal = [item for item in strokes if item["points"][0][1] == item["points"][-1][1]]
    vertical = [item for item in strokes if item["points"][0][0] == item["points"][-1][0]]
    assert len(horizontal) == 2
    assert len(vertical) == 2
    plan = build_brush_test_drawing_plan("Поперечный профиль и пересечения", (460, 240))
    assert len(plan["strokes"]) == 4



def test_automated_postdraw_capture_preserves_board_without_clicking_clear() -> None:
    import inspect

    source = inspect.getsource(brush_ui.BrushBehaviorTestTab._capture_automated_after_draw)

    assert "pyautogui.click" not in source
    assert "_capture_automated_after_clear" not in source
    assert '_finish_automated_postdraw(' in source


def test_logical_plan_strokes_are_transformed_for_screenshot_roi() -> None:
    plan = build_brush_test_drawing_plan(
        "Проверка границ доски", (460, 240),
        coordinate_system="logical_board_pixels",
    )
    plan["generation"]["screen_transform"] = {
        "logical_board": {"width": 460, "height": 240},
        "screen_roi": {"x": 563, "y": 253, "width": 578, "height": 301},
        "scale_x": 577 / 460,
        "scale_y": 300 / 240,
    }
    strokes, error = brush_ui._screen_local_strokes_for_capture(plan, (578, 301))
    assert error is None
    assert strokes is not None
    assert strokes[0]["points"][-1]["x"] == pytest.approx(577.0)
    assert strokes[2]["points"][-1]["y"] == pytest.approx(300.0)


def test_logical_plan_visibility_rejects_screenshot_roi_mismatch() -> None:
    plan = build_brush_test_drawing_plan(
        "Проверка границ доски", (460, 240),
        coordinate_system="logical_board_pixels",
    )
    plan["generation"]["screen_transform"] = {
        "logical_board": {"width": 460, "height": 240},
        "screen_roi": {"x": 563, "y": 253, "width": 578, "height": 301},
        "scale_x": 577 / 460,
        "scale_y": 300 / 240,
    }
    strokes, error = brush_ui._screen_local_strokes_for_capture(plan, (553, 301))
    assert strokes is None
    assert error == "drawing_plan_screen_transform_roi_mismatch"



def _monitor_run_fixture(*, started, finished, strokes=6, radius=1, radii=None, chalk_status="exact",
                         pre=10, post=40, consumed=30):
    return {
        "record_type": "autodraw_game_monitor_run",
        "execution_status": "completed",
        "started_at_utc": started,
        "finished_at_utc": finished,
        "brush_radius": radius,
        "observed_brush_radii": [radius] if radii is None else radii,
        "brush_radius_status": "single" if radii is None or radii == [radius] else "mixed",
        "stroke_count": strokes,
        "chalk": {
            "status": chalk_status,
            "pre_point_count": pre,
            "post_point_count": post,
            "consumed_points": consumed,
        },
    }


def test_execution_monitor_selection_uses_executor_window_stroke_count_and_radius(tmp_path):
    execution = {
        "started_at": "2026-10-31T21:50:15+03:00",
        "ended_at": "2026-10-31T21:50:45+03:00",
    }
    stale_before = _monitor_run_fixture(
        started="2026-10-31T18:50:06+00:00", finished="2026-10-31T18:50:09+00:00",
        strokes=6,
    )
    valid = _monitor_run_fixture(
        started="2026-10-31T18:50:16+00:00", finished="2026-10-31T18:50:40+00:00",
        strokes=6,
    )
    manual_after = _monitor_run_fixture(
        started="2026-10-31T18:52:11+00:00", finished="2026-10-31T18:52:22+00:00",
        strokes=6,
    )
    wrong_stroke_count = _monitor_run_fixture(
        started="2026-10-31T18:50:17+00:00", finished="2026-10-31T18:50:30+00:00",
        strokes=1,
    )
    wrong_radius = _monitor_run_fixture(
        started="2026-10-31T18:50:17+00:00", finished="2026-10-31T18:50:30+00:00",
        strokes=6, radius=30,
    )
    candidates = [
        (tmp_path / "old.json", stale_before),
        (tmp_path / "manual.json", manual_after),
        (tmp_path / "wrong-count.json", wrong_stroke_count),
        (tmp_path / "wrong-radius.json", wrong_radius),
        (tmp_path / "valid.json", valid),
    ]

    selected, reason, count = brush_ui.select_execution_monitor_run(
        candidates,
        execution_report=execution,
        requested_brush=1,
        expected_strokes=6,
        before_draw_at="2026-10-31T18:50:08+00:00",
    )

    assert selected == candidates[-1]
    assert reason == "matched_executor_window"
    assert count == 1


def test_execution_monitor_selection_rejects_ambiguous_runs_in_same_window(tmp_path):
    execution = {
        "started_at": "2026-10-31T21:50:15+03:00",
        "ended_at": "2026-10-31T21:50:45+03:00",
    }
    first = _monitor_run_fixture(
        started="2026-10-31T18:50:16+00:00", finished="2026-10-31T18:50:30+00:00",
    )
    second = _monitor_run_fixture(
        started="2026-10-31T18:50:20+00:00", finished="2026-10-31T18:50:40+00:00",
    )

    selected, reason, count = brush_ui.select_execution_monitor_run(
        [(tmp_path / "first.json", first), (tmp_path / "second.json", second)],
        execution_report=execution,
        requested_brush=1,
        expected_strokes=6,
    )

    assert selected is None
    assert reason == "ambiguous_executor_window"
    assert count == 2


def test_execution_monitor_selection_fails_closed_without_executor_timestamps(tmp_path):
    report = _monitor_run_fixture(
        started="2026-10-31T18:50:16+00:00", finished="2026-10-31T18:50:40+00:00",
    )

    selected, reason, count = brush_ui.select_execution_monitor_run(
        [(tmp_path / "run.json", report)],
        execution_report={"status": "completed"},
        requested_brush=1,
        expected_strokes=6,
    )

    assert selected is None
    assert reason == "execution_time_window_unavailable"
    assert count == 0


def test_exact_chalk_measurement_rejects_counter_reset_and_zero_consumption():
    reset = {
        "status": "inconclusive",
        "pre_point_count": 721,
        "post_point_count": 48,
        "consumed_points": -673,
    }
    zero = {
        "status": "exact",
        "pre_point_count": 1,
        "post_point_count": 1,
        "consumed_points": 0,
    }
    valid = {
        "status": "exact",
        "pre_point_count": 10,
        "post_point_count": 40,
        "consumed_points": 30,
    }

    assert brush_ui.is_exact_positive_chalk_measurement(reset) is False
    assert brush_ui.is_exact_positive_chalk_measurement(zero) is False
    assert brush_ui.is_exact_positive_chalk_measurement(valid) is True
