from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import uuid
from typing import Any



def validate_target_area(
    x: int, y: int, width: int, height: int, screen_width: int, screen_height: int
) -> None:
    """Pure preflight validation used before starting mouse input."""
    values = (x, y, width, height, screen_width, screen_height)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("Координаты, размеры области и экрана должны быть целыми числами.")
    if screen_width <= 0 or screen_height <= 0:
        raise ValueError("Не удалось определить корректный размер экрана.")
    if x < 0 or y < 0 or width < 50 or height < 50:
        raise ValueError("Координаты должны быть неотрицательными, область — не меньше 50 × 50 px.")
    if x + width > screen_width or y + height > screen_height:
        raise ValueError(
            f"Область выходит за границы экрана {screen_width} × {screen_height} px. "
            "Проверьте масштаб Windows и выберите область повторно."
        )

def canonical_sha256(value: Any) -> str:
    """Hash the logical JSON data (not the source file's formatting or whitespace)."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_execution_report(
    *,
    stage: int,
    source_plan_path: str | Path | None,
    source_plan: Any | None,
    executed_plan: Any | None,
    target_area: dict[str, int] | None,
    fit_info: Any | None,
    summary: dict[str, Any],
    config: dict[str, Any] | None,
    status: str,
    error: str | None = None,
) -> dict[str, Any]:
    source_doc = source_plan.to_dict() if source_plan is not None else None
    executed_doc = executed_plan.to_dict() if executed_plan is not None else None
    return {
        "schema_version": 2,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "stage": stage,
        "status": status,
        "source_plan_file": str(source_plan_path) if source_plan_path is not None else None,
        "source_plan_name": getattr(source_plan, "name", None),
        "source_plan_sha256": canonical_sha256(source_doc) if source_doc is not None else None,
        "executed_plan": {
            "name": getattr(executed_plan, "name", None),
            "width": getattr(executed_plan, "width", None),
            "height": getattr(executed_plan, "height", None),
            "stroke_count": getattr(executed_plan, "stroke_count", None),
            "sha256": canonical_sha256(executed_doc) if executed_doc is not None else None,
        } if executed_plan is not None else None,
        "target_area": target_area,
        "plan_fit": fit_info.to_dict() if fit_info is not None else None,
        "executor_config": config,
        "summary": summary,
        "error": error,
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "python_implementation": platform.python_implementation(),
        },
    }


def build_crash_summary(error: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "completed_strokes": None,
        "total_strokes": None,
        "duration_seconds": None,
        "move_calls": None,
        "stop_reason": "worker_exception",
        "mouse_release": {
            "attempted": False,
            "succeeded": False,
            "errors": ["Исполнитель завершился до возврата итоговой сводки; состояние кнопки нужно проверить."]
        },
        "error": error,
    }


def write_execution_report(results_dir: str | Path, report: dict[str, Any]) -> Path:
    """Atomically save a uniquely named report so an interruption cannot truncate an old report."""
    directory = Path(results_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    destination = directory / f"execution_{stamp}_{uuid.uuid4().hex[:6]}.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=".execution_", suffix=".tmp", dir=str(directory))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, destination)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return destination
