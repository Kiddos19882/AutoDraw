from __future__ import annotations

import sys
import threading
import types
import unittest
from unittest.mock import patch


class FastEvent:
    """Event-compatible test double: waits return immediately rather than sleeping."""
    def __init__(self, stop_after_wait: int | None = None):
        self.flag = False
        self.wait_count = 0
        self.stop_after_wait = stop_after_wait

    def is_set(self):
        return self.flag

    def set(self):
        self.flag = True

    def wait(self, timeout=None):
        self.wait_count += 1
        if self.stop_after_wait is not None and self.wait_count >= self.stop_after_wait:
            self.flag = True
        return self.flag


class FakePyAutoGUI(types.ModuleType):
    def __init__(self):
        super().__init__("pyautogui")
        self.PAUSE = 0
        self.FAILSAFE = True
        self.FailSafeException = type("FailSafeException", (Exception,), {})
        self.moves = []
        self.down_calls = 0
        self.up_calls = 0
        self.up_failures_remaining = 0
        self.fail_move_number = None
        self.fail_safe_move_number = None
        self.on_move = None
        self._size = (1920, 1080)

    def reset(self):
        self.moves.clear()
        self.down_calls = 0
        self.up_calls = 0
        self.up_failures_remaining = 0
        self.fail_move_number = None
        self.fail_safe_move_number = None
        self.on_move = None

    def moveTo(self, x, y, duration=0):
        self.moves.append((x, y, duration))
        if self.on_move:
            self.on_move(x, y, duration)
        if self.fail_safe_move_number == len(self.moves):
            raise self.FailSafeException("test failsafe")
        if self.fail_move_number == len(self.moves):
            raise RuntimeError("test move failure")

    def mouseDown(self):
        self.down_calls += 1

    def mouseUp(self):
        self.up_calls += 1
        if self.up_failures_remaining > 0:
            self.up_failures_remaining -= 1
            raise RuntimeError("test mouseUp failure")

    def size(self):
        return self._size


FAKE_PYAUTOGUI = FakePyAutoGUI()


class FakeGlobalHotKeys:
    trigger_f12_on_start = False
    last_instance = None

    def __init__(self, mapping):
        self.mapping = mapping
        self.started = False
        self.stopped = False
        FakeGlobalHotKeys.last_instance = self

    def start(self):
        self.started = True
        if FakeGlobalHotKeys.trigger_f12_on_start:
            self.mapping["<f12>"]()

    def stop(self):
        self.stopped = True


fake_keyboard = types.ModuleType("pynput.keyboard")
fake_keyboard.GlobalHotKeys = FakeGlobalHotKeys
fake_pynput = types.ModuleType("pynput")
fake_pynput.keyboard = fake_keyboard
sys.modules["pyautogui"] = FAKE_PYAUTOGUI
sys.modules["pynput"] = fake_pynput
sys.modules["pynput.keyboard"] = fake_keyboard

from drawing.mouse_executor import ExecutorConfig, MouseExecutor
from models import DrawingPlan, Point, Stroke


def small_plan() -> DrawingPlan:
    return DrawingPlan(
        width=20,
        height=20,
        name="Regression drawing",
        strokes=[Stroke("line", [Point(1, 1), Point(9, 1)])],
    )


class ExecutorConfigTests(unittest.TestCase):
    def test_calibrated_defaults_are_valid_and_preserved(self):
        config = ExecutorConfig()
        config.validate()
        self.assertEqual(config.to_dict(), {
            "point_step_px": 2.0,
            "line_extension_px": 2.0,
            "point_delay_ms": 10,
            "after_mouse_up_ms": 20,
            "before_mouse_down_ms": 20,
            "after_mouse_down_ms": 40,
            "end_hold_ms": 50,
            "countdown_seconds": 5,
        })

    def test_point_step_bounds_and_non_finite_values_rejected(self):
        for step in (0.1, 20.1, float("inf"), float("nan")):
            with self.subTest(step=step), self.assertRaises(ValueError):
                ExecutorConfig(point_step_px=step).validate()

    def test_line_extension_bounds_and_non_finite_values_rejected(self):
        for extension in (-0.1, 20.1, float("inf"), float("nan"), True):
            with self.subTest(extension=extension), self.assertRaises(ValueError):
                ExecutorConfig(line_extension_px=extension).validate()

    def test_timing_bounds_rejected(self):
        for field, value in (("point_delay_ms", 101), ("after_mouse_up_ms", -1), ("before_mouse_down_ms", 501), ("countdown_seconds", 0)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                ExecutorConfig(**{field: value}).validate()


class MouseExecutorTests(unittest.TestCase):
    def setUp(self):
        FAKE_PYAUTOGUI.reset()
        FakeGlobalHotKeys.trigger_f12_on_start = False
        FakeGlobalHotKeys.last_instance = None

    def config(self, **overrides):
        values = dict(
            point_step_px=2.0,
            point_delay_ms=0,
            after_mouse_up_ms=0,
            before_mouse_down_ms=0,
            after_mouse_down_ms=0,
            end_hold_ms=0,
            countdown_seconds=1,
        )
        values.update(overrides)
        return ExecutorConfig(**values)

    def test_success_reports_progress_and_final_release(self):
        events = []
        executor = MouseExecutor(FastEvent(), self.config())
        summary = executor.execute(small_plan(), 100, 200, progress=lambda *args: events.append(args))
        self.assertEqual(summary.status, "completed")
        self.assertEqual(summary.completed_strokes, 1)
        self.assertTrue(summary.mouse_release_attempted)
        self.assertTrue(summary.mouse_release_succeeded)
        self.assertEqual(summary.mouse_release_errors, ())
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 1)
        self.assertGreaterEqual(FAKE_PYAUTOGUI.up_calls, 2)  # end-of-stroke and final cleanup
        self.assertTrue(any("Завершён штрих" in event[2] for event in events))
        self.assertTrue(FakeGlobalHotKeys.last_instance.stopped)

    def test_external_stop_during_countdown_is_immediate(self):
        stop = FastEvent(stop_after_wait=1)
        summary = MouseExecutor(stop, self.config()).execute(small_plan(), 0, 0)
        self.assertEqual(summary.status, "stopped")
        self.assertEqual(summary.completed_strokes, 0)
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 0)
        self.assertEqual(summary.stop_reason, "stop_event")
        self.assertTrue(summary.mouse_release_succeeded)

    def test_button_stop_reason_is_recorded(self):
        stop = FastEvent()
        reason = {"value": "stop_button"}
        stop.set()
        summary = MouseExecutor(stop, self.config(), stop_reason_provider=lambda: reason["value"]).execute(small_plan(), 0, 0)
        self.assertEqual(summary.status, "stopped")
        self.assertEqual(summary.stop_reason, "stop_button")

    def test_f12_stop_reason_is_recorded(self):
        FakeGlobalHotKeys.trigger_f12_on_start = True
        summary = MouseExecutor(FastEvent(), self.config()).execute(small_plan(), 0, 0)
        self.assertEqual(summary.status, "stopped")
        self.assertEqual(summary.stop_reason, "F12")
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 0)

    def test_stop_during_stroke_releases_mouse(self):
        stop = FastEvent()
        def on_move(*_args):
            if FAKE_PYAUTOGUI.down_calls:
                stop.set()
        FAKE_PYAUTOGUI.on_move = on_move
        summary = MouseExecutor(stop, self.config()).execute(small_plan(), 50, 60)
        self.assertEqual(summary.status, "stopped")
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 1)
        self.assertGreaterEqual(FAKE_PYAUTOGUI.up_calls, 2)
        self.assertTrue(summary.mouse_release_succeeded)

    def test_stop_during_point_delay_wait_is_prompt(self):
        stop = FastEvent(stop_after_wait=4)  # countdown, before-down, after-down, then point delay
        summary = MouseExecutor(stop, self.config(point_delay_ms=10)).execute(small_plan(), 50, 60)
        self.assertEqual(summary.status, "stopped")
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 1)
        self.assertTrue(summary.mouse_release_succeeded)
        self.assertGreaterEqual(FAKE_PYAUTOGUI.up_calls, 2)

    def test_movement_error_is_reported_and_cleanup_runs(self):
        FAKE_PYAUTOGUI.fail_move_number = 2  # first move is the stroke start, second is the segment
        summary = MouseExecutor(FastEvent(), self.config()).execute(small_plan(), 10, 20)
        self.assertEqual(summary.status, "failed")
        self.assertIn("test move failure", summary.error)
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 1)
        self.assertTrue(summary.mouse_release_succeeded)

    def test_pyautogui_failsafe_has_distinct_stop_reason(self):
        FAKE_PYAUTOGUI.fail_safe_move_number = 1
        summary = MouseExecutor(FastEvent(), self.config()).execute(small_plan(), 0, 0)
        self.assertEqual(summary.status, "stopped")
        self.assertEqual(summary.stop_reason, "pyautogui_failsafe")
        self.assertTrue(summary.mouse_release_succeeded)

    def test_release_failure_is_not_reported_as_success(self):
        FAKE_PYAUTOGUI.up_failures_remaining = 5
        summary = MouseExecutor(FastEvent(), self.config()).execute(small_plan(), 0, 0)
        self.assertEqual(summary.status, "failed")
        self.assertFalse(summary.mouse_release_succeeded)
        self.assertTrue(summary.mouse_release_errors)
        self.assertIn("mouseUp failure", summary.error)




class LineExtensionTests(unittest.TestCase):
    def setUp(self):
        FAKE_PYAUTOGUI.reset()
        FakeGlobalHotKeys.trigger_f12_on_start = False
        FakeGlobalHotKeys.last_instance = None

    def make_config(self, **overrides):
        values = dict(
            point_step_px=2.0, line_extension_px=2.0, point_delay_ms=0,
            after_mouse_up_ms=0, before_mouse_down_ms=0, after_mouse_down_ms=0,
            end_hold_ms=0, countdown_seconds=1,
        )
        values.update(overrides)
        return ExecutorConfig(**values)

    def test_open_line_is_drawn_two_pixels_longer_by_default(self):
        plan = small_plan()
        summary = MouseExecutor(FastEvent(), self.make_config()).execute(plan, 100, 200)
        self.assertEqual(summary.status, "completed")
        self.assertEqual(FAKE_PYAUTOGUI.moves[0][:2], (101, 201))
        self.assertEqual(FAKE_PYAUTOGUI.moves[-1][:2], (111, 201))
        self.assertEqual(plan.strokes[0].points[-1], Point(9, 1))

    def test_zero_extension_keeps_original_endpoint(self):
        MouseExecutor(FastEvent(), self.make_config(line_extension_px=0)).execute(small_plan(), 100, 200)
        self.assertEqual(FAKE_PYAUTOGUI.moves[-1][:2], (109, 201))

    def test_closed_contour_is_not_extended(self):
        plan = DrawingPlan(
            width=20, height=20,
            strokes=[Stroke("triangle", [Point(1, 1), Point(9, 1), Point(9, 9)], closed=True)],
        )
        MouseExecutor(FastEvent(), self.make_config()).execute(plan, 100, 200)
        self.assertEqual(FAKE_PYAUTOGUI.moves[-1][:2], (101, 201))

    def test_extension_is_clamped_to_canvas_bounds(self):
        plan = DrawingPlan(
            width=20, height=20,
            strokes=[Stroke("edge line", [Point(18, 10), Point(20, 10)])],
        )
        MouseExecutor(FastEvent(), self.make_config()).execute(plan, 100, 200)
        self.assertEqual(FAKE_PYAUTOGUI.moves[-1][:2], (120, 210))


if __name__ == "__main__":
    unittest.main(verbosity=2)
