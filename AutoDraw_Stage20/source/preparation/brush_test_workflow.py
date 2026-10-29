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
