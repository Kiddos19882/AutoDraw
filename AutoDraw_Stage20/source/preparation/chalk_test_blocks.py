from __future__ import annotations

"""Durable, deterministic block plans and journals for CHALK geometry experiments."""

import json
import os
import random
import uuid
import functools
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chalk_int006_validation import (
    MODEL_ID as INT006_MODEL_ID,
    build_int006_prediction_artifact,
    validate_int006_prediction_artifact,
)
from chalk_experiment_matrix import (
    EXPECTED_STROKES,
    GEOMETRY_EXECUTOR_CONFIG,
    G3_POINT_STEPS,
    G3_POINT_DELAYS_MS,
    PHASE_SCENARIOS,
    LEGACY_V_SCENARIO_PHASES,
    V_SAMPLING_PROFILES,
)


BLOCK_SCHEMA_VERSION = 1
BLOCK_PHASES = frozenset(PHASE_SCENARIOS)



def _journal_locked(function):
    """Serialize journal read-modify-write transitions across processes."""
    @functools.wraps(function)
    def wrapped(journal_path, *args, **kwargs):
        path = Path(journal_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(path.name + ".lock")
        with lock_path.open("a+b") as lock_file:
            if os.name == "nt":
                import msvcrt
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write(b"\\0")
                    lock_file.flush()
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    return function(journal_path, *args, **kwargs)
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    return function(journal_path, *args, **kwargs)
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    return wrapped



def acquire_chalk_block_owner_lock(journal_path: str | Path):
    """Acquire an exclusive lifetime lock for one active block UI session.

    Returns an open lock handle, or None when another process owns the journal.
    The caller must retain the handle until the block is completed, stopped, or
    handed back to recovery UI.
    """
    path = Path(journal_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.parent / ".active-block.owner.lock"
        lock_file = lock_path.open("a+b")
    except OSError:
        return None
    try:
        if os.name == "nt":
            import msvcrt
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\\0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except (OSError, BlockingIOError):
        lock_file.close()
        return None


def release_chalk_block_owner_lock(lock_file) -> None:
    """Release a previously acquired block-session ownership lock."""
    if lock_file is None or lock_file.closed:
        return
    try:
        if os.name == "nt":
            import msvcrt
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except OSError:
        # Closing the descriptor still releases the OS lock.
        pass
    finally:
        lock_file.close()

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
        raise ValueError("Для G1/G2/G3/V1-V5/INT006 требуется ровно три независимых повтора.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("Seed порядка тестов должен быть целым числом.")
    if isinstance(radius, bool) or not isinstance(radius, int) or radius != 10:
        raise ValueError("Для блоков G1/G2/G3/V1-V5/INT006 требуется фиксированный радиус 10.")

    scenarios = PHASE_SCENARIOS[phase_id]
    if phase_id == "G3":
        cells = []
        for point_step_px in G3_POINT_STEPS:
            for point_delay_ms in G3_POINT_DELAYS_MS:
                parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
                parameters.update({
                    "point_step_px": point_step_px,
                    "point_delay_ms": point_delay_ms,
                })
                for repeat_index in range(1, repeats + 1):
                    cells.append({
                        "scenario_id": "paint_consumption_long_lines",
                        "repeat_index": repeat_index,
                        "expected_strokes": EXPECTED_STROKES["paint_consumption_long_lines"],
                        "requested_radius": radius,
                        "executor_parameters": parameters,
                    })
    elif phase_id in {"V1", "V2", "V3", "V4", "V5", "INT006"}:
        cells = []
        for point_step_px, point_delay_ms in V_SAMPLING_PROFILES:
            parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
            parameters.update({"point_step_px": point_step_px, "point_delay_ms": point_delay_ms})
            for repeat_index in range(1, repeats + 1):
                for scenario_id in scenarios:
                    cells.append({
                        "scenario_id": scenario_id,
                        "repeat_index": repeat_index,
                        "expected_strokes": EXPECTED_STROKES[scenario_id],
                        "requested_radius": radius,
                        "executor_parameters": dict(parameters),
                    })
    else:
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
    prediction_artifact = build_int006_prediction_artifact(normalized_series) if phase_id == "INT006" else None
    tasks = []
    for order_index, cell in enumerate(cells, start=1):
        parameters = cell["executor_parameters"]
        task_id = (
            f"{cell['scenario_id']}-s{parameters['point_step_px']}-"
            f"d{parameters['point_delay_ms']}-r{cell['repeat_index']}"
            if phase_id == "G3" or phase_id.startswith("V") or phase_id == "INT006"
            else f"{cell['scenario_id']}-r{cell['repeat_index']}"
        )
        task_record = {
            "task_id": task_id,
            **cell,
            "matrix_order_index": order_index,
            "status": "pending",
            "attempts": [],
        }
        if phase_id == "INT006":
            profile_name = next(
                name for name, profile in (
                    ("P0", {"point_step_px": 2, "point_delay_ms": 10}),
                    ("P1", {"point_step_px": 4, "point_delay_ms": 5}),
                    ("P2", {"point_step_px": 4, "point_delay_ms": 10}),
                )
                if (parameters["point_step_px"], parameters["point_delay_ms"])
                == (profile["point_step_px"], profile["point_delay_ms"])
            )
            task_record["prediction_id"] = f"{INT006_MODEL_ID}:{cell['scenario_id']}:{profile_name}"
        tasks.append(task_record)
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
        "executor_parameter_matrix": (
            [
                {"point_step_px": step, "point_delay_ms": delay}
                for step in G3_POINT_STEPS for delay in G3_POINT_DELAYS_MS
            ] if phase_id == "G3" else (
                [
                    {"point_step_px": step, "point_delay_ms": delay}
                    for step, delay in V_SAMPLING_PROFILES
                ] if phase_id.startswith("V") or phase_id == "INT006" else [dict(GEOMETRY_EXECUTOR_CONFIG)]
            )
        ),
        "expected_task_count": len(tasks),
        "status": "ready",
        "created_at_utc": _utc_now(),
        "updated_at_utc": _utc_now(),
        "tasks": tasks,
        **({"prediction_artifact": prediction_artifact} if prediction_artifact is not None else {}),
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


@_journal_locked
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


def _validate_chalk_test_block_journal(document: Any, path: Path) -> dict[str, Any]:
    """Reject structurally inconsistent journals before any recovery or state transition."""
    if (
        not isinstance(document, dict)
        or document.get("record_type") != "autodraw_chalk_test_block"
        or document.get("schema_version") != BLOCK_SCHEMA_VERSION
        or not isinstance(document.get("phase_id"), str)
        or document.get("phase_id") not in BLOCK_PHASES
        or not isinstance(document.get("status"), str)
        or document.get("status") not in {"ready", "running", "paused", "completed", "stopped", "failed"}
        or not isinstance(document.get("tasks"), list)
    ):
        raise ValueError(f"Некорректный журнал блока CHALK: {path}")

    tasks = document["tasks"]
    expected_count = document.get("expected_task_count")
    if (
        isinstance(expected_count, bool)
        or not isinstance(expected_count, int)
        or expected_count != len(tasks)
        or expected_count <= 0
    ):
        raise ValueError(f"Некорректное число задач в журнале CHALK: {path}")

    task_ids: set[str] = set()
    running_tasks = []
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError(f"Некорректная запись задачи в журнале CHALK: {path}")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id or task_id in task_ids:
            raise ValueError(f"Отсутствует или повторяется task_id в журнале CHALK: {path}")
        task_ids.add(task_id)
        if not isinstance(task.get("status"), str) or task.get("status") not in {"pending", "running", "completed", "failed", "interrupted"}:
            raise ValueError(f"Неизвестный статус задачи {task_id!r} в журнале CHALK: {path}")
        attempts = task.get("attempts")
        if not isinstance(attempts, list) or any(not isinstance(item, dict) for item in attempts):
            raise ValueError(f"Некорректный список попыток задачи {task_id!r}: {path}")
        attempt_ids: set[str] = set()
        running_attempts = []
        for attempt in attempts:
            attempt_id = attempt.get("attempt_id")
            if not isinstance(attempt_id, str) or not attempt_id or attempt_id in attempt_ids:
                raise ValueError(f"Отсутствует или повторяется attempt_id задачи {task_id!r}: {path}")
            attempt_ids.add(attempt_id)
            if not isinstance(attempt.get("status"), str) or attempt.get("status") not in {"running", "completed", "failed", "interrupted"}:
                raise ValueError(f"Неизвестный статус попытки задачи {task_id!r}: {path}")
            if attempt.get("status") == "running":
                running_attempts.append(attempt)
        if task.get("status") == "running":
            running_tasks.append(task)
            active_attempt_id = task.get("active_attempt_id")
            if (
                not isinstance(active_attempt_id, str)
                or sum(item.get("attempt_id") == active_attempt_id for item in running_attempts) != 1
                or len(running_attempts) != 1
            ):
                raise ValueError(f"Активная попытка задачи {task_id!r} не согласована с журналом: {path}")
        elif task.get("active_attempt_id") is not None or running_attempts:
            raise ValueError(f"У неактивной задачи {task_id!r} осталась running-попытка: {path}")

    phase_id = document["phase_id"]
    if phase_id == "G3":
        expected_cells = {
            (step, delay, repeat)
            for step in G3_POINT_STEPS
            for delay in G3_POINT_DELAYS_MS
            for repeat in (1, 2, 3)
        }
        observed_cells = set()
        observed_order_indices = set()
        for task in tasks:
            parameters = task.get("executor_parameters")
            if not isinstance(parameters, dict):
                raise ValueError(f"В G3-задаче {task['task_id']!r} отсутствуют параметры исполнителя: {path}")
            step, delay = parameters.get("point_step_px"), parameters.get("point_delay_ms")
            repeat_index = task.get("repeat_index")
            order_index = task.get("matrix_order_index")
            cell = (step, delay, repeat_index)
            expected_parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
            expected_parameters.update({"point_step_px": step, "point_delay_ms": delay})
            if (
                isinstance(step, bool) or not isinstance(step, int)
                or isinstance(delay, bool) or not isinstance(delay, int)
                or isinstance(repeat_index, bool) or not isinstance(repeat_index, int)
                or isinstance(order_index, bool) or not isinstance(order_index, int)
                or order_index < 1 or order_index > 27 or order_index in observed_order_indices
                or task.get("scenario_id") != "paint_consumption_long_lines"
                or task.get("expected_strokes") != EXPECTED_STROKES["paint_consumption_long_lines"]
                or task.get("requested_radius") != 10
                or parameters != expected_parameters
                or cell not in expected_cells
                or cell in observed_cells
            ):
                raise ValueError(f"Некорректная или повторная ячейка G3 в журнале: {path}")
            observed_cells.add(cell)
            observed_order_indices.add(order_index)
        expected_parameter_matrix = [
            {"point_step_px": step, "point_delay_ms": delay}
            for step in G3_POINT_STEPS for delay in G3_POINT_DELAYS_MS
        ]
        if (
            observed_cells != expected_cells
            or observed_order_indices != set(range(1, 28))
            or len(tasks) != 27
            or document.get("executor_parameters") != GEOMETRY_EXECUTOR_CONFIG
            or document.get("executor_parameter_matrix") != expected_parameter_matrix
        ):
            raise ValueError(f"Журнал G3 должен содержать все 27 уникальных ячеек: {path}")
    elif phase_id == "INT006":
        artifact_ok, artifact_reason = validate_int006_prediction_artifact(
            document.get("prediction_artifact"), expected_series_id=document.get("series_id")
        )
        if not artifact_ok:
            raise ValueError(f"INT006 frozen prediction artifact invalid ({artifact_reason}): {path}")
        expected_cells = {
            (scenario_id, step, delay, repeat)
            for scenario_id in PHASE_SCENARIOS[phase_id]
            for step, delay in V_SAMPLING_PROFILES
            for repeat in (1, 2, 3)
        }
        observed_cells = set()
        observed_order_indices = set()
        for task in tasks:
            parameters = task.get("executor_parameters")
            if not isinstance(parameters, dict):
                raise ValueError(f"В INT006-задаче {task['task_id']!r} отсутствуют параметры исполнителя: {path}")
            step, delay = parameters.get("point_step_px"), parameters.get("point_delay_ms")
            repeat_index = task.get("repeat_index")
            order_index = task.get("matrix_order_index")
            scenario_id = task.get("scenario_id")
            cell = (scenario_id, step, delay, repeat_index)
            expected_parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
            expected_parameters.update({"point_step_px": step, "point_delay_ms": delay})
            profile_name = next(
                (name for name, profile in (
                    ("P0", {"point_step_px": 2, "point_delay_ms": 10}),
                    ("P1", {"point_step_px": 4, "point_delay_ms": 5}),
                    ("P2", {"point_step_px": 4, "point_delay_ms": 10}),
                ) if (step, delay) == (profile["point_step_px"], profile["point_delay_ms"])),
                None,
            )
            expected_prediction_id = f"{INT006_MODEL_ID}:{scenario_id}:{profile_name}" if profile_name else None
            if (
                scenario_id not in PHASE_SCENARIOS[phase_id]
                or isinstance(step, bool) or not isinstance(step, int)
                or isinstance(delay, bool) or not isinstance(delay, int)
                or isinstance(repeat_index, bool) or not isinstance(repeat_index, int)
                or isinstance(order_index, bool) or not isinstance(order_index, int)
                or order_index < 1 or order_index > 45 or order_index in observed_order_indices
                or task.get("expected_strokes") != EXPECTED_STROKES.get(scenario_id)
                or task.get("requested_radius") != 10
                or parameters != expected_parameters
                or (step, delay) not in V_SAMPLING_PROFILES
                or cell not in expected_cells
                or cell in observed_cells
                or task.get("prediction_id") != expected_prediction_id
                or expected_prediction_id not in document["prediction_artifact"]["predictions"]
            ):
                raise ValueError(f"Некорректная/повторная ячейка INT006 или prediction binding: {path}")
            observed_cells.add(cell)
            observed_order_indices.add(order_index)
        expected_parameter_matrix = [
            {"point_step_px": step, "point_delay_ms": delay}
            for step, delay in V_SAMPLING_PROFILES
        ]
        if (
            observed_cells != expected_cells
            or observed_order_indices != set(range(1, 46))
            or len(tasks) != 45
            or document.get("executor_parameters") != GEOMETRY_EXECUTOR_CONFIG
            or document.get("executor_parameter_matrix") != expected_parameter_matrix
        ):
            raise ValueError(f"Журнал INT006 должен содержать все 45 уникальных ячеек: {path}")
    elif phase_id in {"V1", "V2", "V3", "V4", "V5"}:
        scenario_id = PHASE_SCENARIOS[phase_id][0]
        compatible_scenarios = {scenario_id, *(
            legacy_id for legacy_id, legacy_phase in LEGACY_V_SCENARIO_PHASES.items()
            if legacy_phase == phase_id
        )}
        expected_cells = {
            (step, delay, repeat)
            for step, delay in V_SAMPLING_PROFILES
            for repeat in (1, 2, 3)
        }
        observed_cells = set()
        observed_order_indices = set()
        observed_scenarios = set()
        for task in tasks:
            parameters = task.get("executor_parameters")
            if not isinstance(parameters, dict):
                raise ValueError(f"В {phase_id}-задаче {task['task_id']!r} отсутствуют параметры исполнителя: {path}")
            step, delay = parameters.get("point_step_px"), parameters.get("point_delay_ms")
            repeat_index = task.get("repeat_index")
            order_index = task.get("matrix_order_index")
            task_scenario_id = task.get("scenario_id")
            cell = (step, delay, repeat_index)
            expected_parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
            expected_parameters.update({"point_step_px": step, "point_delay_ms": delay})
            if (
                isinstance(step, bool) or not isinstance(step, int)
                or isinstance(delay, bool) or not isinstance(delay, int)
                or isinstance(repeat_index, bool) or not isinstance(repeat_index, int)
                or isinstance(order_index, bool) or not isinstance(order_index, int)
                or order_index < 1 or order_index > 9 or order_index in observed_order_indices
                or task_scenario_id not in compatible_scenarios
                or task.get("expected_strokes") != EXPECTED_STROKES.get(task_scenario_id)
                or task.get("requested_radius") != 10
                or parameters != expected_parameters
                or cell not in expected_cells
                or cell in observed_cells
            ):
                raise ValueError(f"Некорректная или повторная ячейка {phase_id} в журнале: {path}")
            observed_cells.add(cell)
            observed_order_indices.add(order_index)
            observed_scenarios.add(task_scenario_id)
        expected_parameter_matrix = [
            {"point_step_px": step, "point_delay_ms": delay}
            for step, delay in V_SAMPLING_PROFILES
        ]
        if (
            observed_cells != expected_cells
            or observed_order_indices != set(range(1, 10))
            or len(observed_scenarios) != 1
            or len(tasks) != 9
            or document.get("executor_parameters") != GEOMETRY_EXECUTOR_CONFIG
            or document.get("executor_parameter_matrix") != expected_parameter_matrix
        ):
            raise ValueError(f"Журнал {phase_id} должен содержать все 9 уникальных ячеек: {path}")
    else:
        for task in tasks:
            if (
                task.get("scenario_id") not in PHASE_SCENARIOS[phase_id]
                or task.get("executor_parameters") != GEOMETRY_EXECUTOR_CONFIG
            ):
                raise ValueError(f"Параметры задачи не соответствуют фазе {phase_id}: {path}")

    if len(running_tasks) > 1:
        raise ValueError(f"В журнале CHALK обнаружено несколько running-задач: {path}")
    if (document.get("status") == "running") != (len(running_tasks) == 1):
        raise ValueError(f"Статус блока не согласован с активной задачей: {path}")
    block_status = document["status"]
    task_statuses = {task["status"] for task in tasks}
    if block_status == "completed" and task_statuses != {"completed"}:
        raise ValueError(f"Завершённый блок содержит незавершённые задачи: {path}")
    if block_status == "ready" and not task_statuses.issubset({"pending", "completed"}):
        raise ValueError(f"Ready-блок содержит failed/interrupted/running задачу: {path}")
    if block_status == "paused" and (
        running_tasks or not task_statuses.intersection({"failed", "interrupted"})
    ):
        raise ValueError(f"Paused-блок не содержит корректной причины остановки: {path}")
    if block_status == "failed" and (
        running_tasks or "failed" not in task_statuses
    ):
        raise ValueError(f"Failed-блок не согласован с failed-задачей: {path}")
    if block_status == "stopped" and running_tasks:
        raise ValueError(f"Остановленный блок содержит running-задачу: {path}")
    return document


def load_chalk_test_block_journal(journal_path: str | Path) -> dict[str, Any]:
    path = Path(journal_path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Не удалось разобрать журнал блока CHALK: {path}: {exc}") from exc
    return _validate_chalk_test_block_journal(document, path)


def _save_journal(path: Path, journal: dict[str, Any]) -> None:
    journal["updated_at_utc"] = _utc_now()
    _atomic_write_json(path, journal)


@_journal_locked
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


@_journal_locked
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


@_journal_locked
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
    *,
    expected_task: dict[str, Any] | None = None,
    expected_block: dict[str, Any] | None = None,
    expected_experiment_id: str | None = None,
    expected_experiment_dir: str | Path | None = None,
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
    if (
        expected_task is not None or expected_block is not None
        or expected_experiment_id is not None or expected_experiment_dir is not None
    ):
        if not isinstance(expected_task, dict) or not isinstance(expected_block, dict) or expected_experiment_dir is None:
            return False, "expected_block_task_identity_unavailable", None
        block_ref = document.get("chalk_test_block")
        matrix = document.get("chalk_experiment_matrix")
        if not isinstance(block_ref, dict) or not isinstance(matrix, dict):
            return False, "block_task_identity_missing", None
        identity_pairs = (
            (block_ref.get("block_id"), expected_block.get("block_id"), "block_id"),
            (block_ref.get("task_id"), expected_task.get("task_id"), "task_id"),
            (block_ref.get("phase_id"), expected_block.get("phase_id"), "block_phase_id"),
            (matrix.get("series_id"), expected_block.get("series_id"), "series_id"),
            (matrix.get("phase_id"), expected_block.get("phase_id"), "phase_id"),
            (matrix.get("scenario_id"), expected_task.get("scenario_id"), "scenario_id"),
            (matrix.get("repeat_index"), expected_task.get("repeat_index"), "repeat_index"),
            (matrix.get("requested_radius"), expected_task.get("requested_radius"), "requested_radius"),
            (matrix.get("expected_strokes"), expected_task.get("expected_strokes"), "expected_strokes"),
            (matrix.get("matrix_order_index"), expected_task.get("matrix_order_index"), "matrix_order_index"),
            (matrix.get("executor_parameters"), expected_task.get("executor_parameters"), "executor_parameters"),
            (document.get("experiment_id"), expected_experiment_id, "experiment_id"),
            (path.parent.resolve(), Path(expected_experiment_dir).resolve(), "experiment_dir"),
        )
        for actual, expected, field in identity_pairs:
            if actual != expected:
                return False, f"block_task_identity_mismatch:{field}", None
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


@_journal_locked
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
    if journal.get("status") in {"paused", "failed"} and board_checked is not True:
        raise ValueError("Приостановленный/failed блок можно закрыть только после явной проверки игровой доски.")
    if journal.get("status") in {"completed", "stopped"}:
        return journal
    if journal.get("status") in {"paused", "failed"}:
        # A rejected experiment pauses the block, but its task remains failed.
        # Preserve that distinction in the closure audit instead of deriving it
        # from the block-level "paused" state alone.
        has_failed_task = any(
            task.get("status") == "failed" for task in journal.get("tasks", [])
        )
        journal.setdefault("recovery_decisions", []).append({
            "decision": "close_failed_block" if has_failed_task else "close_paused_block",
            "board_checked": True,
            "decided_at_utc": _utc_now(),
        })
    journal["status"] = "stopped"
    journal["stopped_at_utc"] = _utc_now()
    _save_journal(path, journal)
    return journal

@_journal_locked
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

@_journal_locked
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
