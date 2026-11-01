from __future__ import annotations

"""Durable, deterministic block plans and journals for CHALK geometry experiments."""

import json
import os
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chalk_experiment_matrix import (
    EXPECTED_STROKES,
    GEOMETRY_EXECUTOR_CONFIG,
    PHASE_SCENARIOS,
)


BLOCK_SCHEMA_VERSION = 1
BLOCK_PHASES = frozenset(PHASE_SCENARIOS)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _validate_series_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("ID серии должен быть текстом.")
    normalized = value.strip()
    if not normalized or len(normalized) > 64:
        raise ValueError("ID серии должен содержать от 1 до 64 символов.")
    if any(not (char.isalnum() or char in "-_.") for char in normalized):
        raise ValueError("ID серии может содержать только буквы, цифры, дефис, точку и подчёркивание.")
    return normalized


def build_chalk_test_block_plan(
    *,
    series_id: str,
    phase_id: str,
    repeats: int = 3,
    seed: int = 20261101,
    radius: int = 10,
) -> dict[str, Any]:
    """Build every scenario/repeat cell in a phase, with deterministic randomized order."""
    normalized_series = _validate_series_id(series_id)
    if phase_id not in BLOCK_PHASES:
        raise ValueError(f"Неизвестный блок CHALK: {phase_id!r}.")
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats != 3:
        raise ValueError("Для G1/G2 требуется ровно три независимых повтора.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("Seed порядка тестов должен быть целым числом.")
    if isinstance(radius, bool) or not isinstance(radius, int) or radius != 10:
        raise ValueError("Для блоков G1/G2 требуется фиксированный радиус 10.")

    scenarios = PHASE_SCENARIOS[phase_id]
    cells = [
        {
            "scenario_id": scenario_id,
            "repeat_index": repeat_index,
            "expected_strokes": EXPECTED_STROKES[scenario_id],
            "requested_radius": radius,
            "executor_parameters": dict(GEOMETRY_EXECUTOR_CONFIG),
        }
        for scenario_id in scenarios
        for repeat_index in range(1, repeats + 1)
    ]
    random.Random(seed).shuffle(cells)
    tasks = []
    for order_index, cell in enumerate(cells, start=1):
        task_id = f"{cell['scenario_id']}-r{cell['repeat_index']}"
        tasks.append({
            "task_id": task_id,
            **cell,
            "matrix_order_index": order_index,
            "status": "pending",
            "attempts": [],
        })
    return {
        "schema_version": BLOCK_SCHEMA_VERSION,
        "record_type": "autodraw_chalk_test_block",
        "block_id": uuid.uuid4().hex,
        "series_id": normalized_series,
        "phase_id": phase_id,
        "repeat_count": repeats,
        "random_seed": seed,
        "requested_radius": radius,
        "executor_parameters": dict(GEOMETRY_EXECUTOR_CONFIG),
        "expected_task_count": len(tasks),
        "status": "ready",
        "created_at_utc": _utc_now(),
        "updated_at_utc": _utc_now(),
        "tasks": tasks,
    }


def _atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp_path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def create_chalk_test_block_journal(
    journal_path: str | Path,
    plan: dict[str, Any],
) -> Path:
    """Create a new durable journal; never overwrite an existing block."""
    path = Path(journal_path)
    if path.exists():
        raise FileExistsError(f"Журнал блока уже существует: {path}")
    if plan.get("record_type") != "autodraw_chalk_test_block":
        raise ValueError("Передан некорректный план блока CHALK.")
    _atomic_write_json(path, dict(plan))
    return path


def load_chalk_test_block_journal(journal_path: str | Path) -> dict[str, Any]:
    path = Path(journal_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or document.get("record_type") != "autodraw_chalk_test_block"
        or document.get("schema_version") != BLOCK_SCHEMA_VERSION
        or not isinstance(document.get("tasks"), list)
    ):
        raise ValueError(f"Некорректный журнал блока CHALK: {path}")
    return document


def _save_journal(path: Path, journal: dict[str, Any]) -> None:
    journal["updated_at_utc"] = _utc_now()
    _atomic_write_json(path, journal)


def claim_next_chalk_block_task(
    journal_path: str | Path,
    *,
    now_utc: str | None = None,
) -> dict[str, Any] | None:
    """Claim the next pending task; an unfinished running task blocks progression."""
    path = Path(journal_path)
    journal = load_chalk_test_block_journal(path)
    if journal.get("status") in {"completed", "stopped", "failed", "paused"}:
        return None
    tasks = journal["tasks"]
    if any(task.get("status") == "running" for task in tasks):
        raise RuntimeError("В блоке уже есть незавершённый выполняемый тест.")
    task = next((item for item in tasks if item.get("status") == "pending"), None)
    if task is None:
        journal["status"] = "completed" if all(item.get("status") == "completed" for item in tasks) else "paused"
        _save_journal(path, journal)
        return None
    attempt = {
        "attempt_id": uuid.uuid4().hex,
        "status": "running",
        "started_at_utc": now_utc or _utc_now(),
        "experiment_id": None,
        "experiment_dir": None,
        "reason": None,
    }
    task.setdefault("attempts", []).append(attempt)
    task["status"] = "running"
    task["active_attempt_id"] = attempt["attempt_id"]
    journal["status"] = "running"
    _save_journal(path, journal)
    return dict(task)


def finish_chalk_block_task(
    journal_path: str | Path,
    task_id: str,
    *,
    accepted: bool,
    experiment_id: str | None,
    experiment_dir: str | Path | None,
    reason: str | None = None,
    finished_at_utc: str | None = None,
) -> dict[str, Any]:
    """Close the active attempt. A failed/inconclusive run pauses the entire block."""
    if not isinstance(accepted, bool):
        raise ValueError("accepted должен быть bool.")
    path = Path(journal_path)
    journal = load_chalk_test_block_journal(path)
    task = next((item for item in journal["tasks"] if item.get("task_id") == task_id), None)
    if task is None or task.get("status") != "running":
        raise ValueError(f"Тест {task_id!r} не является активным заданием блока.")
    attempt_id = task.get("active_attempt_id")
    attempt = next(
        (item for item in reversed(task.get("attempts", [])) if item.get("attempt_id") == attempt_id),
        None,
    )
    if attempt is None or attempt.get("status") != "running":
        raise ValueError("Не найдена активная попытка теста.")
    attempt.update({
        "status": "completed" if accepted else "failed",
        "finished_at_utc": finished_at_utc or _utc_now(),
        "experiment_id": experiment_id,
        "experiment_dir": str(experiment_dir) if experiment_dir is not None else None,
        "reason": reason,
    })
    task["status"] = "completed" if accepted else "failed"
    task.pop("active_attempt_id", None)
    if accepted:
        all_done = all(item.get("status") == "completed" for item in journal["tasks"])
        journal["status"] = "completed" if all_done else "ready"
    else:
        journal["status"] = "paused"
        journal["pause_reason"] = reason or "experiment_not_accepted"
    _save_journal(path, journal)
    return dict(task)


def mark_interrupted_chalk_block_task(
    journal_path: str | Path,
    *,
    reason: str = "application_restarted_during_experiment",
) -> dict[str, Any]:
    """Mark a running task interrupted after restart; never silently replay it."""
    path = Path(journal_path)
    journal = load_chalk_test_block_journal(path)
    running = [task for task in journal["tasks"] if task.get("status") == "running"]
    if len(running) != 1:
        raise ValueError("В журнале должен быть ровно один незавершённый тест.")
    task = running[0]
    attempt_id = task.get("active_attempt_id")
    attempt = next(
        (item for item in reversed(task.get("attempts", [])) if item.get("attempt_id") == attempt_id),
        None,
    )
    if attempt is None:
        raise ValueError("Для незавершённого теста отсутствует попытка.")
    attempt.update({"status": "interrupted", "reason": reason, "finished_at_utc": _utc_now()})
    task["status"] = "interrupted"
    task.pop("active_attempt_id", None)
    journal["status"] = "paused"
    journal["pause_reason"] = reason
    _save_journal(path, journal)
    return dict(task)


def chalk_test_block_progress(journal: dict[str, Any]) -> dict[str, int | str]:
    tasks = journal.get("tasks", [])
    counts = {
        status: sum(1 for task in tasks if task.get("status") == status)
        for status in ("pending", "running", "completed", "failed", "interrupted")
    }
    counts["total"] = len(tasks)
    counts["status"] = str(journal.get("status", "unknown"))
    return counts


def validate_chalk_block_experiment(
    manifest_path: str | Path,
) -> tuple[bool, str, dict[str, Any] | None]:
    """Apply the strict matrix and per-stroke acceptance gates to one saved experiment."""
    path = Path(manifest_path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return False, f"experiment_manifest_unavailable:{exc}", None
    if not isinstance(document, dict):
        return False, "experiment_manifest_invalid", None

    document["experiment_dir"] = str(path.parent)
    phases = document.get("phases") if isinstance(document.get("phases"), dict) else {}
    before_clear = phases.get("before_clear") if isinstance(phases.get("before_clear"), dict) else {}
    before_draw = phases.get("before_draw") if isinstance(phases.get("before_draw"), dict) else {}
    after_draw = phases.get("after_draw") if isinstance(phases.get("after_draw"), dict) else {}
    postdraw = phases.get("postdraw_workflow") if isinstance(phases.get("postdraw_workflow"), dict) else {}
    if before_clear.get("status") not in {"restored", "restored_within_pixel_tolerance"}:
        return False, "preclear_not_verified", None
    if not before_draw.get("captured_at_utc"):
        return False, "before_draw_capture_missing", None
    if after_draw.get("status") != "captured":
        return False, "after_draw_capture_missing", None
    if postdraw.get("status") != "completed":
        return False, "postdraw_workflow_not_completed", None

    from chalk_experiment_matrix import _validate_manifest, _stroke_level_breakdown

    valid, reason, record = _validate_manifest(document)
    if not valid or record is None:
        return False, str(reason), None
    stroke_level = _stroke_level_breakdown(
        path.parent,
        expected_strokes=int(record["expected_strokes"]),
        expected_chalk=int(record["consumed_points"]),
    )
    record["stroke_level"] = stroke_level
    if not isinstance(stroke_level, dict) or stroke_level.get("status") != "complete":
        reason = stroke_level.get("reason") if isinstance(stroke_level, dict) else "stroke_breakdown_missing"
        return False, f"stroke_level_{reason}", None

    summary = document.get("game_monitor_summary")
    summary = summary if isinstance(summary, dict) else {}
    frame_probe = summary.get("frame_probe")
    frame_probe = frame_probe if isinstance(frame_probe, dict) else {}
    if frame_probe.get("status") != "measured" or frame_probe.get("visibility_interruption") is not False:
        return False, "frame_probe_not_clean", None
    trajectory = summary.get("trajectory")
    trajectory = trajectory if isinstance(trajectory, dict) else {}
    try:
        accepted_samples = int(trajectory.get("accepted_sample_count", 0) or 0)
    except (TypeError, ValueError, OverflowError):
        accepted_samples = 0
    if accepted_samples <= 0:
        return False, "trajectory_samples_missing", None

    return True, "accepted", record


def stop_chalk_test_block(
    journal_path: str | Path,
    *,
    board_checked: bool = False,
) -> dict[str, Any]:
    """Stop a block at a task boundary; paused blocks require an explicit board check."""
    path = Path(journal_path)
    journal = load_chalk_test_block_journal(path)
    if any(task.get("status") == "running" for task in journal["tasks"]):
        raise RuntimeError("Нельзя остановить блок посреди опыта; дождитесь безопасной границы.")
    if journal.get("status") == "paused" and board_checked is not True:
        raise ValueError("Приостановленный блок можно закрыть только после явной проверки игровой доски.")
    if journal.get("status") in {"completed", "stopped"}:
        return journal
    journal["status"] = "stopped"
    journal["stopped_at_utc"] = _utc_now()
    _save_journal(path, journal)
    return journal

def record_chalk_block_task_experiment(
    journal_path: str | Path,
    task_id: str,
    *,
    experiment_id: str,
    experiment_dir: str | Path,
) -> dict[str, Any]:
    """Persist experiment identity/path on the active attempt before the first mouse action."""
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("experiment_id обязателен.")
    path = Path(journal_path)
    journal = load_chalk_test_block_journal(path)
    task = next((item for item in journal["tasks"] if item.get("task_id") == task_id), None)
    if task is None or task.get("status") != "running":
        raise ValueError(f"Тест {task_id!r} не является активным заданием блока.")
    attempt_id = task.get("active_attempt_id")
    attempt = next(
        (item for item in reversed(task.get("attempts", [])) if item.get("attempt_id") == attempt_id),
        None,
    )
    if attempt is None or attempt.get("status") != "running":
        raise ValueError("Не найдена активная попытка теста.")
    if attempt.get("experiment_id") or attempt.get("experiment_dir"):
        raise ValueError("Для активной попытки уже зарегистрирован experiment.")
    attempt["experiment_id"] = experiment_id
    attempt["experiment_dir"] = str(Path(experiment_dir).resolve())
    attempt["experiment_registered_at_utc"] = _utc_now()
    _save_journal(path, journal)
    return dict(task)

def resolve_interrupted_chalk_block_task(
    journal_path: str | Path,
    task_id: str,
    *,
    board_checked: bool,
    decision: str,
) -> dict[str, Any]:
    """Require explicit board inspection before retrying or closing an interrupted block."""
    if board_checked is not True:
        raise ValueError("Перед решением требуется явно подтвердить проверку игровой доски.")
    if decision not in {"retry", "stop"}:
        raise ValueError("decision должен быть retry или stop.")
    path = Path(journal_path)
    journal = load_chalk_test_block_journal(path)
    task = next((item for item in journal["tasks"] if item.get("task_id") == task_id), None)
    if task is None or task.get("status") != "interrupted":
        raise ValueError(f"Тест {task_id!r} не находится в состоянии interrupted.")
    if decision == "retry":
        task["status"] = "pending"
        journal["status"] = "ready"
        journal.pop("pause_reason", None)
        journal.setdefault("recovery_decisions", []).append({
            "task_id": task_id,
            "decision": "retry",
            "board_checked": True,
            "decided_at_utc": _utc_now(),
        })
    else:
        journal["status"] = "stopped"
        journal["stopped_at_utc"] = _utc_now()
        journal.setdefault("recovery_decisions", []).append({
            "task_id": task_id,
            "decision": "stop",
            "board_checked": True,
            "decided_at_utc": _utc_now(),
        })
    _save_journal(path, journal)
    return dict(task)
