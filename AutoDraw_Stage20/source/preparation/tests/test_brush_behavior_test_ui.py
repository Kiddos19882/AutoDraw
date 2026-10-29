from __future__ import annotations

import pytest

import brush_behavior_test_ui as brush_ui
from brush_behavior_test_ui import TEST_CASES, build_brush_test_drawing_plan, build_brush_test_record


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
            assert len(stroke["points"]) == 2
            assert len(stroke["points"][0]) == 2
            assert len(stroke["points"][1]) == 2


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


def test_paint_consumption_case_has_twelve_long_lines_within_default_game_canvas() -> None:
    scenario = TEST_CASES["Расход краски — серия длинных линий"]
    assert scenario["id"] == "paint_consumption_long_lines"
    assert len(scenario["strokes"]) == 12
    total_length = 0
    for index, stroke in enumerate(scenario["strokes"]):
        start, end = stroke["points"]
        assert start == [20, 10 + index * 18]
        assert end == [420, 10 + index * 18]
        assert 0 <= start[0] < 460 and 0 <= end[0] < 460
        assert 0 <= start[1] < 240 and 0 <= end[1] < 240
        total_length += abs(end[0] - start[0]) + abs(end[1] - start[1])
    assert total_length == 4800


def test_paint_consumption_plan_uses_all_long_lines() -> None:
    plan = build_brush_test_drawing_plan("Расход краски — серия длинных линий", (460, 240))
    assert len(plan["strokes"]) == 12
    assert plan["strokes"][-1]["name"] == "consumption_line_12"


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

    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
    tab.root = Root()
    tab.brush_var = Value("14")
    tab.slider_start_var = Value()
    tab.slider_end_var = Value()
    tab.status_var = Value()
    tab.get_brush_control = lambda: {
        "mode": "slider", "start": [100, 500], "end": [390, 500],
        "screen_size": {"width": 1920, "height": 1080},
    }
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
        def after(self, delay, callback):
            self.scheduled.append((delay, callback))

    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
    tab.root = Root()
    tab.brush_var = Value("14")
    tab.slider_start_var = Value()
    tab.slider_end_var = Value()
    tab.status_var = Value()
    tab.get_brush_control = lambda: {
        "mode": "presets", "presets": {"7": [10, 20], "14": [30, 40], "20": [50, 60]}
    }
    monkeypatch.setattr(brush_ui.platform, "system", lambda: "Windows")
    warnings = []
    monkeypatch.setattr(brush_ui.messagebox, "showwarning", lambda *args, **kwargs: warnings.append(args))

    assert tab.set_brush_size() is False
    assert tab.root.minimized is False
    assert tab.root.scheduled == []
    assert warnings
    assert "перетаскиванием" in warnings[0][1]



def test_brush_drag_f12_cancellation_releases_mouse_without_real_input() -> None:
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
        def after_cancel(self, callback_id):
            self.cancelled.append(callback_id)

    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
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
    assert "остановлено по F12" in tab.status_var.value


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

    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
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



def test_f12_is_not_consumed_when_no_brush_drag_is_active() -> None:
    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
    tab._brush_drag_state = None
    assert tab._on_brush_workflow_stop_key() is None



def test_f12_cancels_pending_brush_countdown_and_restores_window(monkeypatch) -> None:
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

    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
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
    assert "отменена по F12" in tab.status_var.value


def test_global_f12_listener_schedules_cancellation_on_tk_thread(monkeypatch) -> None:
    class FakeKeyboard:
        f12 = object()

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

    tab = brush_ui.BrushBehaviorTestTab.__new__(brush_ui.BrushBehaviorTestTab)
    tab.root = Root()
    tab._brush_hotkey_listener = None
    monkeypatch.setattr(brush_ui.keyboard, "Key", FakeKeyboard)
    monkeypatch.setattr(brush_ui.keyboard, "Listener", Listener)

    tab._start_brush_hotkey_listener()
    listener = tab._brush_hotkey_listener
    listener.on_press(FakeKeyboard.f12)

    assert listener.started is True
    assert tab.root.scheduled and tab.root.scheduled[0][0] == 0
