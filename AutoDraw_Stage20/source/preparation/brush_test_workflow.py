from __future__ import annotations

"""Pure state model for one autonomous brush experiment.

This module intentionally contains no Tk, mouse, screenshot, or browser operations.
The UI/controller performs side effects and advances this model only after each
side effect has returned a result. Keeping transitions pure makes cancellation
and partial-report behavior testable without controlling a real desktop.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


PHASES = (
    "created",
    "preflight",
    "before_clear",
    "before_capture",
    "set_brush",
    "drawing",
    "after_draw_capture",
    "after_clear",
    "after_clear_capture",
    "restore_brush_30",
    "completed",
)
TERMINAL_STATES = frozenset({"completed", "stopped", "failed", "inconclusive"})


def should_run_postdraw_workflow(execution_status: object) -> bool:
    """Allow automatic post-draw actions only after an explicitly completed execution."""
    return isinstance(execution_status, str) and execution_status.strip().lower() == "completed"
_ALLOWED_NEXT = {
    "created": {"preflight"},
    "preflight": {"before_clear"},
    "before_clear": {"before_capture"},
    "before_capture": {"set_brush"},
    "set_brush": {"drawing"},
    "drawing": {"after_draw_capture"},
    "after_draw_capture": {"after_clear"},
    "after_clear": {"after_clear_capture"},
    "after_clear_capture": {"restore_brush_30"},
    "restore_brush_30": {"completed"},
}


def calculate_slider_target(
    start_30: tuple[int, int] | list[int],
    end_1: tuple[int, int] | list[int],
    brush_value: int,
) -> tuple[int, int]:
    """Map brush radius 30 at the left/start point to radius 1 at the right/end."""
    if isinstance(brush_value, bool) or not isinstance(brush_value, int) or not 1 <= brush_value <= 30:
        raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
    if not isinstance(start_30, (tuple, list)) or len(start_30) != 2:
        raise ValueError("Начальная точка кисти 30 должна содержать X и Y.")
    if not isinstance(end_1, (tuple, list)) or len(end_1) != 2:
        raise ValueError("Конечная точка кисти 1 должна содержать X и Y.")
    try:
        sx, sy = int(start_30[0]), int(start_30[1])
        ex, ey = int(end_1[0]), int(end_1[1])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Координаты ползунка должны быть целыми числами.") from exc
    if (sx, sy) != tuple(start_30) or (ex, ey) != tuple(end_1):
        raise ValueError("Координаты ползунка должны быть целыми числами.")
    ratio = (30 - brush_value) / 29
    return round(sx + (ex - sx) * ratio), round(sy + (ey - sy) * ratio)



def validate_observed_brush_radius(
    requested_brush: int,
    observed_radii: object,
) -> dict[str, Any]:
    """Fail closed unless a pre-draw Game Monitor snapshot confirms one exact radius."""
    if isinstance(requested_brush, bool) or not isinstance(requested_brush, int) or not 1 <= requested_brush <= 30:
        raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
    values = observed_radii
    if isinstance(values, str):
        import json
        try:
            values = json.loads(values.strip())
        except (TypeError, ValueError):
            return {"valid": False, "status": "unavailable", "observed_radii": []}
    if isinstance(values, bool):
        values = None
    elif isinstance(values, (int, float)):
        values = [values]
    if not isinstance(values, (list, tuple)) or not values:
        return {"valid": False, "status": "unavailable", "observed_radii": []}
    radii: set[int] = set()
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value or not 1 <= int(value) <= 30:
            return {"valid": False, "status": "unavailable", "observed_radii": []}
        radii.add(int(value))
    observed = sorted(radii)
    if observed == [requested_brush]:
        return {"valid": True, "status": "match", "observed_radii": observed}
    return {
        "valid": False,
        "status": "mixed" if requested_brush in observed else "mismatch",
        "observed_radii": observed,
    }

def validate_brush_test_preflight(
    profile: dict[str, Any] | None,
    screen_size: tuple[int, int],
    *,
    brush_control: dict[str, Any] | None = None,
    require_slider: bool = True,
) -> dict[str, Any]:
    """Validate calibration before any automated mouse action; never performs I/O."""
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(profile, dict):
        return {"valid": False, "errors": ["Профиль калибровки недоступен."], "warnings": []}

    try:
        screen_width, screen_height = int(screen_size[0]), int(screen_size[1])
        if screen_width < 1 or screen_height < 1:
            raise ValueError
    except (TypeError, ValueError, IndexError, OverflowError):
        return {"valid": False, "errors": ["Не удалось определить разрешение экрана."], "warnings": []}

    saved_size = profile.get("screen_size")
    if isinstance(saved_size, dict):
        try:
            saved = (int(saved_size["width"]), int(saved_size["height"]))
        except (KeyError, TypeError, ValueError, OverflowError):
            errors.append("В профиле некорректно указано разрешение экрана.")
        else:
            if saved != (screen_width, screen_height):
                errors.append(
                    f"Разрешение экрана изменилось: профиль {saved[0]} × {saved[1]}, "
                    f"текущее {screen_width} × {screen_height}."
                )
    else:
        errors.append("В профиле не сохранено разрешение экрана.")

    regions = profile.get("regions")
    statuses = profile.get("status")
    region_status = statuses.get("regions", {}) if isinstance(statuses, dict) else {}
    for name in ("board_area", "paint_meter_area"):
        region = regions.get(name) if isinstance(regions, dict) else None
        if not isinstance(region, dict):
            errors.append(f"В профиле отсутствует область {name}.")
            continue
        try:
            x, y = int(region["x"]), int(region["y"])
            width, height = int(region["width"]), int(region["height"])
        except (KeyError, TypeError, ValueError, OverflowError):
            errors.append(f"Область {name} содержит некорректные координаты.")
            continue
        if x < 0 or y < 0 or width < 2 or height < 2 or x + width > screen_width or y + height > screen_height:
            errors.append(f"Область {name} выходит за пределы текущего экрана.")
        if isinstance(region_status, dict) and region_status.get(name) == "needs_review":
            errors.append(f"Область {name} помечена как требующая повторной проверки.")

    points = profile.get("points")
    point_status = statuses.get("points", {}) if isinstance(statuses, dict) else {}
    clear_point = points.get("clear_board") if isinstance(points, dict) else None
    if not isinstance(clear_point, dict):
        errors.append("Не откалибрована точка очистки Clear.")
    else:
        try:
            clear_x, clear_y = int(clear_point["x"]), int(clear_point["y"])
        except (KeyError, TypeError, ValueError, OverflowError):
            errors.append("Координата Clear некорректна.")
        else:
            if not (0 <= clear_x < screen_width and 0 <= clear_y < screen_height):
                errors.append("Координата Clear находится за пределами экрана.")
        if isinstance(point_status, dict) and point_status.get("clear_board") == "needs_review":
            errors.append("Точка Clear помечена как требующая повторной проверки.")

    if require_slider:
        brush = brush_control if brush_control is not None else profile.get("brush_control")
        if not isinstance(brush, dict):
            errors.append("В профиле отсутствует калибровка ползунка кисти.")
        elif brush.get("mode") != "slider":
            errors.append("Для автоматического перетаскивания нужен режим «Расширенный ползунок 1–30».")
        else:
            for name in ("start", "end"):
                point = brush.get(name)
                try:
                    px, py = int(point[0]), int(point[1])
                except (TypeError, ValueError, IndexError, KeyError, OverflowError):
                    errors.append(f"Не откалиброван конец ползунка {name}.")
                    continue
                if not (0 <= px < screen_width and 0 <= py < screen_height):
                    errors.append(f"Конец ползунка {name} находится за пределами экрана.")
                status_key = "brush_slider_value_30" if name == "start" else "brush_slider_value_1"
                if isinstance(point_status, dict) and point_status.get(status_key) == "needs_review":
                    errors.append(f"Конец ползунка {name} требует повторной проверки.")

    if profile.get("needs_review") is True:
        errors.append("Профиль целиком помечен как требующий повторной проверки.")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


class BrushWorkflowError(RuntimeError):
    """Invalid experiment transition or attempted continuation after termination."""


@dataclass
class BrushExperimentState:
    requested_brush: int
    test_case_id: str
    experiment_id: str
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    phase: str = "created"
    status: str = "running"
    phase_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    stop_reason: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.requested_brush, bool) or not isinstance(self.requested_brush, int):
            raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
        if not 1 <= self.requested_brush <= 30:
            raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
        if not self.test_case_id.strip():
            raise ValueError("Не указан идентификатор сценария.")
        if not self.experiment_id.strip():
            raise ValueError("Не указан идентификатор опыта.")

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_STATES

    def advance(self, next_phase: str, result: dict[str, Any] | None = None) -> None:
        if self.terminal:
            raise BrushWorkflowError(f"Опыт уже завершён со статусом {self.status}.")
        allowed = _ALLOWED_NEXT.get(self.phase, set())
        if next_phase not in allowed:
            raise BrushWorkflowError(
                f"Недопустимый переход {self.phase!r} -> {next_phase!r}; "
                f"ожидалось одно из {sorted(allowed)}."
            )
        if result is not None and not isinstance(result, dict):
            raise ValueError("Результат этапа должен быть JSON-совместимым объектом.")
        # A Clear click alone is not evidence that the board is empty.
        if self.phase == "before_clear" and next_phase == "before_capture":
            clear_status = result.get("board_clear_status") if isinstance(result, dict) else None
            if clear_status not in {"restored", "restored_within_pixel_tolerance"}:
                raise BrushWorkflowError(
                    "Нельзя продолжить: очистка доски не подтверждена сравнением с эталоном пустой доски."
                )
        if result is not None:
            self.phase_results[self.phase] = dict(result)
        self.phase = next_phase
        if next_phase == "completed":
            self.status = "completed"

    def stop(self, reason: str) -> None:
        if self.terminal:
            return
        self.status = "stopped"
        self.stop_reason = reason.strip() or "stop_requested"

    def fail(self, error: str) -> None:
        if self.terminal:
            return
        self.status = "failed"
        self.error = error.strip() or "unknown_error"

    def mark_inconclusive(self, reason: str) -> None:
        if self.terminal:
            return
        self.status = "inconclusive"
        self.warnings.append(reason.strip() or "result_inconclusive")

    def add_warning(self, warning: str) -> None:
        if self.terminal:
            raise BrushWorkflowError("Нельзя изменять завершённый опыт.")
        warning = warning.strip()
        if warning:
            self.warnings.append(warning)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot suitable for partial/final manifests."""
        return {
            "schema_version": 1,
            "record_type": "autodraw_brush_test_workflow",
            "experiment_id": self.experiment_id,
            "created_at_utc": self.created_at_utc,
            "requested_brush": self.requested_brush,
            "test_case_id": self.test_case_id,
            "phase": self.phase,
            "status": self.status,
            "terminal": self.terminal,
            "phase_results": self.phase_results,
            "warnings": list(self.warnings),
            "error": self.error,
            "stop_reason": self.stop_reason,
        }
