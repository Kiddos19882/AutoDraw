from __future__ import annotations

from dataclasses import dataclass
import math
import threading
import time
from typing import Callable

import pyautogui
from pynput import keyboard

from models import DrawingPlan, Point


@dataclass(frozen=True, slots=True)
class ExecutorConfig:
    point_step_px: float = 2.0
    point_delay_ms: int = 10
    after_mouse_up_ms: int = 20
    before_mouse_down_ms: int = 20
    after_mouse_down_ms: int = 40
    end_hold_ms: int = 50
    countdown_seconds: int = 5

    def validate(self) -> None:
        if isinstance(self.point_step_px, bool) or not math.isfinite(float(self.point_step_px)):
            raise ValueError("Шаг между точками должен быть конечным числом.")
        if not 0.5 <= self.point_step_px <= 20:
            raise ValueError("Шаг между точками должен быть в диапазоне 0.5–20 px.")
        limits = {
            "point_delay_ms": (0, 100),
            "after_mouse_up_ms": (0, 500),
            "before_mouse_down_ms": (0, 500),
            "after_mouse_down_ms": (0, 500),
            "end_hold_ms": (0, 500),
            "countdown_seconds": (1, 30),
        }
        for name, (minimum, maximum) in limits.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} должно быть целым числом.")
            if not minimum <= value <= maximum:
                raise ValueError(f"{name} должно быть в диапазоне {minimum}–{maximum}.")

    def to_dict(self) -> dict:
        return {
            "point_step_px": self.point_step_px,
            "point_delay_ms": self.point_delay_ms,
            "after_mouse_up_ms": self.after_mouse_up_ms,
            "before_mouse_down_ms": self.before_mouse_down_ms,
            "after_mouse_down_ms": self.after_mouse_down_ms,
            "end_hold_ms": self.end_hold_ms,
            "countdown_seconds": self.countdown_seconds,
        }


@dataclass(slots=True)
class ExecutionSummary:
    status: str
    completed_strokes: int
    total_strokes: int
    started_at: str
    ended_at: str
    duration_seconds: float
    move_calls: int
    error: str | None = None
    stop_reason: str | None = None
    mouse_release_attempted: bool = False
    mouse_release_succeeded: bool = False
    mouse_release_errors: tuple[str, ...] = ()

    def to_dict(self, config: ExecutorConfig) -> dict:
        return {
            "status": self.status,
            "completed_strokes": self.completed_strokes,
            "total_strokes": self.total_strokes,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": round(self.duration_seconds, 3),
            "move_calls": self.move_calls,
            "error": self.error,
            "stop_reason": self.stop_reason,
            "mouse_release": {
                "attempted": self.mouse_release_attempted,
                "succeeded": self.mouse_release_succeeded,
                "errors": list(self.mouse_release_errors),
            },
            "executor_config": config.to_dict(),
        }


ProgressCallback = Callable[[int, int, str], None]
StopReasonProvider = Callable[[], str | None]
PreflightCallback = Callable[["MouseExecutor"], str | None]
BeforeStrokeCallback = Callable[["MouseExecutor", int, object], str | None]


class MouseExecutor:
    """Воспроизводит DrawingPlan; остановка проверяется между точками и в задержках."""

    def __init__(
        self,
        stop_event: threading.Event,
        config: ExecutorConfig | None = None,
        *,
        stop_reason_provider: StopReasonProvider | None = None,
    ):
        self.stop_event = stop_event
        self.config = config or ExecutorConfig()
        self.config.validate()
        self.stop_reason_provider = stop_reason_provider
        self._reason_lock = threading.Lock()
        self._hotkey_stop_requested = False
        self.move_calls = 0
        self._release_attempted = False
        self._release_succeeded = False
        self._release_errors: list[str] = []
        # Все паузы контролируются этим исполнителем; FAILSAFE остаётся включённым.
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = True

    def _request_hotkey_stop(self) -> None:
        with self._reason_lock:
            self._hotkey_stop_requested = True
        self.stop_event.set()

    def _current_stop_reason(self) -> str:
        # If F12 was pressed first, a subsequent window-close stop request must not rewrite its cause.
        with self._reason_lock:
            if self._hotkey_stop_requested:
                return "F12"
        try:
            external_reason = self.stop_reason_provider() if self.stop_reason_provider else None
        except Exception:
            external_reason = None
        return external_reason or "stop_event"

    def _check_stop(self) -> None:
        if self.stop_event.is_set():
            raise InterruptedError(f"Исполнение остановлено: {self._current_stop_reason()}.")

    def _wait_interruptibly(self, seconds: float) -> None:
        """Wait no longer than requested, but return immediately when stop is requested."""
        self._check_stop()
        if seconds <= 0:
            return
        if self.stop_event.wait(seconds):
            raise InterruptedError(f"Исполнение остановлено: {self._current_stop_reason()}.")

    def _screen_point(self, point: Point, area_x: int, area_y: int) -> tuple[int, int]:
        return round(area_x + point.x), round(area_y + point.y)

    def _move_segment(self, start: Point, end: Point, area_x: int, area_y: int) -> None:
        distance = start.distance_to(end)
        steps = max(1, math.ceil(distance / self.config.point_step_px))
        for step_index in range(1, steps + 1):
            self._check_stop()
            fraction = step_index / steps
            point = Point(
                start.x + (end.x - start.x) * fraction,
                start.y + (end.y - start.y) * fraction,
            )
            screen_x, screen_y = self._screen_point(point, area_x, area_y)
            pyautogui.moveTo(screen_x, screen_y, duration=0)
            self.move_calls += 1
            self._wait_interruptibly(self.config.point_delay_ms / 1000.0)

    def _release_mouse(self) -> bool:
        self._release_attempted = True
        try:
            pyautogui.mouseUp()
            self._release_succeeded = True
            return True
        except Exception as exc:
            self._release_succeeded = False
            self._release_errors.append(f"{type(exc).__name__}: {exc}")
            return False

    def execute(
        self,
        plan: DrawingPlan,
        area_x: int,
        area_y: int,
        progress: ProgressCallback | None = None,
        *,
        preflight: PreflightCallback | None = None,
        before_stroke: BeforeStrokeCallback | None = None,
    ) -> ExecutionSummary:
        from datetime import datetime

        self.config.validate()
        plan.validate_bounds()
        listener = None
        completed = 0
        status = "completed"
        error: str | None = None
        stop_reason: str | None = None
        start_clock = time.monotonic()
        started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self.move_calls = 0
        self._release_attempted = False
        self._release_succeeded = False
        self._release_errors = []
        last_mouse_up = False

        def notify(current: int, detail: str) -> None:
            if progress is not None:
                progress(current, len(plan.strokes), detail)

        try:
            listener = keyboard.GlobalHotKeys({"<f12>": self._request_hotkey_stop})
            listener.start()
            for remaining in range(self.config.countdown_seconds, 0, -1):
                self._check_stop()
                notify(0, f"Начало через {remaining} с. Переключитесь на браузер; F12 — остановить.")
                self._wait_interruptibly(1.0)

            if preflight is not None:
                self._check_stop()
                notify(0, "Проверка палитры и экранной калибровки перед рисованием…")
                preflight_detail = preflight(self)
                self._check_stop()
                if preflight_detail:
                    notify(0, preflight_detail)

            for stroke_index, stroke in enumerate(plan.strokes, start=1):
                self._check_stop()
                notify(stroke_index - 1, f"Штрих {stroke_index}/{len(plan.strokes)}: {stroke.name}")

                if last_mouse_up:
                    self._wait_interruptibly(self.config.after_mouse_up_ms / 1000.0)

                if before_stroke is not None:
                    self._check_stop()
                    color_detail = before_stroke(self, stroke_index, stroke)
                    self._check_stop()
                    if color_detail:
                        notify(stroke_index - 1, color_detail)

                start_x, start_y = self._screen_point(stroke.points[0], area_x, area_y)
                pyautogui.moveTo(start_x, start_y, duration=0)
                self.move_calls += 1
                self._wait_interruptibly(self.config.before_mouse_down_ms / 1000.0)
                self._check_stop()
                pyautogui.mouseDown()
                last_mouse_up = False

                try:
                    self._wait_interruptibly(self.config.after_mouse_down_ms / 1000.0)
                    for segment_start, segment_end in stroke.iter_segments():
                        self._move_segment(segment_start, segment_end, area_x, area_y)
                    self._wait_interruptibly(self.config.end_hold_ms / 1000.0)
                finally:
                    if not self._release_mouse():
                        raise RuntimeError("Не удалось отпустить кнопку мыши после штриха: " + self._release_errors[-1])
                    last_mouse_up = True

                completed += 1
                notify(completed, f"Завершён штрих {completed}/{len(plan.strokes)}: {stroke.name}")

        except InterruptedError as exc:
            status = "stopped"
            stop_reason = self._current_stop_reason()
            error = str(exc)
        except pyautogui.FailSafeException as exc:
            status = "stopped"
            stop_reason = "pyautogui_failsafe"
            error = "Сработал аварийный механизм PyAutoGUI (указатель в углу основного экрана)."
            if str(exc):
                error += f" Детали: {exc}"
        except Exception as exc:
            status = "failed"
            error = f"{type(exc).__name__}: {exc}"
        finally:
            # Последняя cleanup-попытка выполняется во всех сценариях, включая ошибку mouseDown/moveTo.
            if not self._release_mouse():
                release_message = "Не удалось подтвердить отпускание кнопки мыши при завершении: " + self._release_errors[-1]
                error = f"{error}; {release_message}" if error else release_message
                status = "failed"
                stop_reason = stop_reason or "mouse_release_failed"
            if listener is not None:
                try:
                    listener.stop()
                except Exception as exc:
                    listener_message = f"Не удалось остановить обработчик F12: {type(exc).__name__}: {exc}"
                    error = f"{error}; {listener_message}" if error else listener_message
                    if status == "completed":
                        status = "failed"

        ended_at = datetime.now().astimezone().isoformat(timespec="seconds")
        return ExecutionSummary(
            status=status,
            completed_strokes=completed,
            total_strokes=len(plan.strokes),
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=time.monotonic() - start_clock,
            move_calls=self.move_calls,
            error=error,
            stop_reason=stop_reason,
            mouse_release_attempted=self._release_attempted,
            mouse_release_succeeded=self._release_succeeded,
            mouse_release_errors=tuple(self._release_errors),
        )
