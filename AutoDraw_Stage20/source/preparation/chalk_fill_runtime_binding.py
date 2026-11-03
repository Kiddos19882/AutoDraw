from __future__ import annotations

"""Fail-closed binding of FILL-001 tasks to real Bridge and executor artifacts."""

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import uuid

from chalk_fill_matrix import FillMatrixError

FILL001_RUNTIME_PROFILE = {
    "profile_id": "P1",
    "sampling_step": 4,
    "delay_ms": 5,
}
FILL001_EXECUTOR_STEP_PX = 4.0
FILL001_EXECUTOR_DELAY_MS = 5
FILL001_LINE_EXTENSION_PX = 0.0


class RuntimeBindingNotReady(FillMatrixError):
    """The Bridge run has not been finalized or persisted yet."""


_CONTEXT_FIELDS = (
    "phase_id",
    "series_id",
    "task_id",
    "shape_id",
    "requested_radius",
    "repeat_index",
    "expected_strokes",
    "plan_signature",
    "target_mask_sha256",
    "sampling_profile",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_aware_datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise FillMatrixError(f"{label}: отсутствует timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FillMatrixError(f"{label}: некорректный timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FillMatrixError(f"{label}: timestamp должен содержать timezone.")
    return parsed.astimezone(timezone.utc)


def _bridge_run_activity_window(run: dict[str, Any], session: dict[str, Any]) -> tuple[datetime, datetime, datetime]:
    """Return run start, last-event time, and persisted finalization time.

    Bridge event t values and started_at_performance_ms share the browser
    performance clock. finished_at_utc is a persistence timestamp and may
    be later than the actual event window because of idle finalization.
    """
    started = _parse_aware_datetime(run.get("started_at_utc"), "bridge_run.started_at_utc")
    finalized = _parse_aware_datetime(run.get("finished_at_utc"), "bridge_run.finished_at_utc")
    started_perf = run.get("started_at_performance_ms")
    if (
        isinstance(started_perf, bool)
        or not isinstance(started_perf, (int, float))
        or not math.isfinite(float(started_perf))
        or float(started_perf) < 0
    ):
        raise FillMatrixError("bridge_run.started_at_performance_ms должен быть конечным неотрицательным числом.")
    events = run.get("events")
    if not isinstance(events, list) or not events:
        raise FillMatrixError("Bridge run не содержит events для определения activity window.")
    event_times = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise FillMatrixError(f"Bridge run event[{index}] должен быть object.")
        event_time = event.get("t")
        if (
            isinstance(event_time, bool)
            or not isinstance(event_time, (int, float))
            or not math.isfinite(float(event_time))
            or float(event_time) < float(started_perf)
        ):
            raise FillMatrixError(f"Bridge run event[{index}].t некорректен для performance clock.")
        event_times.append(float(event_time))
    activity_ended = started + timedelta(milliseconds=max(event_times) - float(started_perf))
    if activity_ended < started or finalized < activity_ended:
        raise FillMatrixError("Bridge run finalization timestamp предшествует activity window.")
    grace = timedelta(seconds=_session_finalize_grace_seconds(session))
    if finalized - activity_ended > grace:
        raise FillMatrixError("Bridge run превысил idle finalization grace после последнего события.")
    return started, activity_ended, finalized

def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise FillMatrixError(f"{label}: требуется неотрицательное целое число.")
    return value


def _exact_snapshot(snapshot: Any, label: str) -> tuple[int, int]:
    if not isinstance(snapshot, dict) or snapshot.get("isExact") is not True:
        raise FillMatrixError(f"{label}: Bridge snapshot не является exact.")
    point_count = snapshot.get("pointCount")
    max_points = snapshot.get("maxPoints")
    if type(point_count) is not int or type(max_points) is not int:
        raise FillMatrixError(f"{label}: pointCount/maxPoints должны быть целыми.")
    if max_points <= 0 or not 0 <= point_count <= max_points:
        raise FillMatrixError(f"{label}: pointCount вне допустимого диапазона.")
    remaining = snapshot.get("remainingPoints")
    if type(remaining) is not int or point_count + remaining != max_points:
        raise FillMatrixError(f"{label}: exact resource snapshot противоречив.")
    return point_count, max_points


def build_fill001_experiment_context(task: dict[str, Any]) -> dict[str, Any]:
    """Create the immutable task metadata stored beside an executor DrawingPlan."""
    if not isinstance(task, dict):
        raise FillMatrixError("FILL-001 task должен быть JSON object.")
    missing = [key for key in _CONTEXT_FIELDS if key not in task]
    if missing:
        raise FillMatrixError("В FILL-001 task отсутствуют поля: " + ", ".join(missing))
    if task["phase_id"] != "FILL001":
        raise FillMatrixError("Experiment context относится не к FILL-001.")
    for field in ("series_id", "task_id", "shape_id"):
        if not isinstance(task[field], str) or not task[field].strip():
            raise FillMatrixError(f"{field} должен быть непустой строкой.")
    if type(task["requested_radius"]) is not int or task["requested_radius"] not in {1, 5, 10, 20, 30}:
        raise FillMatrixError("Недопустимый requested_radius в FILL-001 context.")
    if type(task["repeat_index"]) is not int or task["repeat_index"] not in {1, 2, 3}:
        raise FillMatrixError("repeat_index должен быть 1, 2 или 3.")
    if type(task["expected_strokes"]) is not int or task["expected_strokes"] < 1:
        raise FillMatrixError("expected_strokes должен быть положительным целым числом.")
    for field in ("plan_signature", "target_mask_sha256"):
        value = task[field]
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise FillMatrixError(f"{field} должен быть SHA-256.")
    if task["sampling_profile"] != FILL001_RUNTIME_PROFILE:
        raise FillMatrixError("FILL-001 task не закрепляет sampling profile P1.")
    return {field: task[field] for field in _CONTEXT_FIELDS}


def _canonical_drawing_plan_document(plan_document: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw JSON through the same DrawingPlan model used by Stage 6."""
    try:
        from geometry_models import DrawingPlan

        return DrawingPlan.from_dict(plan_document).to_dict()
    except (KeyError, TypeError, ValueError) as exc:
        raise FillMatrixError(f"Не удалось нормализовать DrawingPlan для SHA-256: {exc}") from exc


def attach_fill001_experiment_context(
    plan_document: dict[str, Any], task: dict[str, Any]
) -> dict[str, Any]:
    """Return a DrawingPlan JSON document with task metadata and its canonical plan hash."""
    if not isinstance(plan_document, dict):
        raise FillMatrixError("DrawingPlan document должен быть JSON object.")
    if "autodraw_experiment" in plan_document:
        raise FillMatrixError("DrawingPlan уже содержит autodraw_experiment context.")
    canonical_document = _canonical_drawing_plan_document(plan_document)
    canonical = json.dumps(
        canonical_document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    context = build_fill001_experiment_context(task)
    context["executor_plan_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    result = dict(canonical_document)
    result["autodraw_experiment"] = context
    return result


def _validate_executor_report(task: dict[str, Any], report: dict[str, Any]) -> tuple[datetime, datetime, dict[str, Any]]:
    if not isinstance(report, dict) or report.get("schema_version") != 3:
        raise FillMatrixError("Требуется executor report schema_version=3.")
    try:
        execution_id = str(uuid.UUID(report.get("execution_id", "")))
    except (ValueError, TypeError, AttributeError) as exc:
        raise FillMatrixError("Executor report не содержит корректный execution_id.") from exc
    if report.get("status") != "completed":
        raise FillMatrixError("Executor report не завершён успешно.")
    context = report.get("experiment_context")
    expected_context = build_fill001_experiment_context(task)
    if not isinstance(context, dict) or any(
        context.get(field) != value for field, value in expected_context.items()
    ):
        raise FillMatrixError("Executor report связан с другой FILL-001 task.")
    plan_hash = context.get("executor_plan_sha256")
    if (
        not isinstance(plan_hash, str)
        or len(plan_hash) != 64
        or any(c not in "0123456789abcdef" for c in plan_hash)
        or report.get("source_plan_sha256") != plan_hash
    ):
        raise FillMatrixError("Executor report source_plan_sha256 не совпадает с FILL-001 DrawingPlan hash.")
    source_hash = report.get("source_plan_file_sha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64 or any(c not in "0123456789abcdef" for c in source_hash):
        raise FillMatrixError("Executor report не содержит SHA-256 исходного plan-файла.")

    summary = report.get("summary")
    if not isinstance(summary, dict) or summary.get("status") != "completed":
        raise FillMatrixError("Executor summary не завершён успешно.")
    expected_strokes = task.get("expected_strokes")
    if type(expected_strokes) is not int or expected_strokes < 1:
        raise FillMatrixError("Task expected_strokes некорректен.")
    for field in ("completed_strokes", "total_strokes"):
        if summary.get(field) != expected_strokes:
            raise FillMatrixError(f"Executor summary.{field} не совпадает с expected_strokes.")
    executed_plan = report.get("executed_plan")
    if not isinstance(executed_plan, dict) or executed_plan.get("stroke_count") != expected_strokes:
        raise FillMatrixError("Executed DrawingPlan stroke_count не совпадает с task.")

    config = report.get("executor_config")
    summary_config = summary.get("executor_config")
    if not isinstance(config, dict) or not isinstance(summary_config, dict) or config != summary_config:
        raise FillMatrixError("Executor config отсутствует или расходится с summary.")
    step = config.get("point_step_px")
    delay = config.get("point_delay_ms")
    extension = config.get("line_extension_px")
    if isinstance(step, bool) or not isinstance(step, (int, float)) or float(step) != FILL001_EXECUTOR_STEP_PX:
        raise FillMatrixError("Фактический ExecutorConfig.point_step_px не соответствует P1 step=4.")
    if type(delay) is not int or delay != FILL001_EXECUTOR_DELAY_MS:
        raise FillMatrixError("Фактический ExecutorConfig.point_delay_ms не соответствует P1 delay=5.")
    if isinstance(extension, bool) or not isinstance(extension, (int, float)) or float(extension) != FILL001_LINE_EXTENSION_PX:
        raise FillMatrixError("FILL-001 требует line_extension_px=0 для неизменной геометрии.")

    started = _parse_aware_datetime(summary.get("started_at"), "executor.started_at")
    ended = _parse_aware_datetime(summary.get("ended_at"), "executor.ended_at")
    if ended <= started:
        raise FillMatrixError("Executor execution window пуст или имеет обратный порядок.")
    return started, ended, {
        "execution_id": execution_id,
        "executor_config": dict(config),
        "sampling_profile": dict(FILL001_RUNTIME_PROFILE),
        "source_plan_file_sha256": source_hash,
    }


def _session_finalize_grace_seconds(session: dict[str, Any]) -> float:
    if not isinstance(session, dict) or session.get("schema_version") != 2:
        raise FillMatrixError("Требуется Bridge session schema_version=2.")
    idle = session.get("run_idle_seconds")
    if isinstance(idle, bool) or not isinstance(idle, (int, float)) or not 0.5 <= float(idle) <= 15.0:
        raise FillMatrixError("Bridge session не содержит допустимый run_idle_seconds.")
    # RunRecorder finalizes on the next 1 s heartbeat after the configured idle window.
    return float(idle) + 1.5


def _validate_session(session: dict[str, Any], run: dict[str, Any]) -> str:
    if not isinstance(session, dict):
        raise FillMatrixError("Bridge session должен быть JSON object.")
    _session_finalize_grace_seconds(session)
    session_id = session.get("session_id")
    try:
        normalized_session_id = str(uuid.UUID(session_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise FillMatrixError("Bridge session не содержит корректный session_id.") from exc
    if run.get("session_id") != normalized_session_id:
        raise FillMatrixError("Bridge run принадлежит другой session.")
    try:
        str(uuid.UUID(run.get("run_id", "")))
    except (ValueError, TypeError, AttributeError) as exc:
        raise FillMatrixError("Bridge run не содержит корректный run_id.") from exc

    monitor_status = session.get("monitor_status_at_connect")
    if not isinstance(monitor_status, dict) or monitor_status.get("version") != "0.2.1":
        raise FillMatrixError("Bridge session не подтверждает Game Monitor 0.2.1.")
    diagnostics = session.get("bridge_diagnostics")
    if not isinstance(diagnostics, dict):
        raise FillMatrixError("Bridge session не содержит bridge_diagnostics.")
    received_events = _nonnegative_int(diagnostics.get("received_event_count"), "session.received_event_count")
    sequence_gaps = _nonnegative_int(diagnostics.get("collector_sequence_gap_count"), "session.collector_sequence_gap_count")
    run_event_count = _nonnegative_int(run.get("event_count"), "bridge_run.event_count")
    if _nonnegative_int(diagnostics.get("last_sequence"), "session.last_sequence") < 1:
        raise FillMatrixError("Bridge session last_sequence должен быть не меньше 1.")
    browser_bridge = diagnostics.get("browser_bridge")
    if not isinstance(browser_bridge, dict):
        raise FillMatrixError("Bridge session не содержит browser_bridge diagnostics.")
    sent_events = _nonnegative_int(browser_bridge.get("sentEventCount"), "session.browser_bridge.sentEventCount")
    send_failures = _nonnegative_int(browser_bridge.get("sendFailureCount"), "session.browser_bridge.sendFailureCount")
    if sent_events < received_events:
        raise FillMatrixError("Bridge sentEventCount меньше числа принятых событий.")
    if "session_persist_failures" in diagnostics:
        persist_failures = diagnostics["session_persist_failures"]
        if type(persist_failures) is not int or persist_failures != 0:
            raise FillMatrixError("Bridge session содержит ошибки атомарной записи.")
    if received_events < run_event_count:
        raise FillMatrixError("Bridge session event count меньше числа событий run.")
    run_sequence_gaps = _nonnegative_int(
        run.get("collector_sequence_gap_count"), "bridge_run.collector_sequence_gap_count"
    )
    if sequence_gaps < run_sequence_gaps:
        raise FillMatrixError("Bridge session не подтверждает sequence gaps из run.")
    run_send_end = run.get("bridge_send_failures_end")
    if type(run_send_end) is not int or send_failures < run_send_end:
        raise FillMatrixError("Bridge session не подтверждает sendFailureCount из run.")
    return normalized_session_id



def _complete_lifecycle_pairs(
    events: list[dict[str, Any]],
    start_type: str,
    end_type: str,
    expected_strokes: int,
) -> list[tuple[int, int, str]] | None:
    starts = [index for index, event in enumerate(events) if event.get("type") == start_type]
    ends = [index for index, event in enumerate(events) if event.get("type") == end_type]
    if len(starts) != expected_strokes or len(ends) != expected_strokes:
        return None
    pairs: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for start_index, end_index in zip(starts, ends):
        if start_index >= end_index:
            return None
        stroke_id = events[start_index].get("strokeId")
        if not isinstance(stroke_id, str) or not stroke_id or stroke_id in seen:
            return None
        if events[end_index].get("strokeId") != stroke_id:
            return None
        if any(events[index].get("type") == start_type for index in range(start_index + 1, end_index)):
            return None
        seen.add(stroke_id)
        pairs.append((start_index, end_index, stroke_id))
    return pairs


def _validate_bridge_run(
    task: dict[str, Any],
    session: dict[str, Any],
    run: dict[str, Any],
    executor_started: datetime,
    executor_ended: datetime,
) -> dict[str, Any]:
    if not isinstance(run, dict) or run.get("schema_version") != 1:
        raise FillMatrixError("Неподдерживаемая Bridge run schema.")
    if run.get("record_type") != "autodraw_game_monitor_run":
        raise FillMatrixError("Неизвестный Bridge run record_type.")
    session_id = _validate_session(session, run)
    run_id = str(uuid.UUID(run["run_id"]))
    if run.get("execution_status") != "completed":
        raise FillMatrixError("Bridge run не завершён.")
    run_started, activity_ended, _ = _bridge_run_activity_window(run, session)
    grace = timedelta(seconds=_session_finalize_grace_seconds(session))
    if run_started < executor_started or run_started > executor_ended or activity_ended > executor_ended + grace:
        raise FillMatrixError("Bridge run activity window не совпадает с executor window или превысил idle finalization grace.")

    expected_strokes = task["expected_strokes"]
    for field in ("stroke_count", "stroke_candidate_count"):
        if type(run.get(field)) is not int or run[field] != expected_strokes:
            raise FillMatrixError(f"Bridge run {field} не совпадает с task.")
    if type(run.get("non_consuming_stroke_candidate_count")) is not int or run["non_consuming_stroke_candidate_count"] != 0:
        raise FillMatrixError("Bridge run содержит non-consuming stroke candidates.")
    if run.get("brush_radius_status") != "single":
        raise FillMatrixError("Bridge run не подтверждает один фиксированный радиус.")
    radii = run.get("observed_brush_radii")
    if (
        not isinstance(radii, list)
        or len(radii) != 1
        or isinstance(radii[0], bool)
        or not isinstance(radii[0], (int, float))
        or float(radii[0]) != float(task["requested_radius"])
    ):
        raise FillMatrixError("Bridge observed_brush_radii не совпадает с requested_radius.")

    events = run.get("events")
    event_count = _nonnegative_int(run.get("event_count"), "bridge_run.event_count")
    if not isinstance(events, list) or not events or len(events) != event_count:
        raise FillMatrixError("Bridge run event_count не совпадает с events.")
    if any(not isinstance(event, dict) for event in events):
        raise FillMatrixError("Bridge run содержит некорректный event.")
    monitor_versions = {event.get("monitorVersion") for event in events}
    if monitor_versions != {"0.2.1"}:
        raise FillMatrixError("Bridge run events не подтверждают единый Game Monitor version.")

    for field in (
        "dropped_events",
        "monitor_buffer_dropped_events_delta",
        "monitor_error_count_delta",
        "bridge_send_failures_delta",
        "collector_sequence_gap_count",
    ):
        if _nonnegative_int(run.get(field), f"bridge_run.{field}") != 0:
            raise FillMatrixError(f"Bridge run содержит {field}.")

    if run.get("monitor_errors") != []:
        raise FillMatrixError("Bridge run содержит monitor_errors.")
    for field in ("bridge_send_failures_start", "bridge_send_failures_end", "bridge_send_failures_delta"):
        _nonnegative_int(run.get(field), f"bridge_run.{field}")
    if run["bridge_send_failures_end"] - run["bridge_send_failures_start"] != run["bridge_send_failures_delta"]:
        raise FillMatrixError("Bridge run bridge_send_failures delta противоречив.")

    pre_count, pre_max = _exact_snapshot(run.get("pre_test_snapshot"), "bridge_run.pre_test_snapshot")
    post_count, post_max = _exact_snapshot(run.get("post_test_snapshot"), "bridge_run.post_test_snapshot")
    if pre_max != post_max or post_count <= pre_count:
        raise FillMatrixError("Bridge run pre/post resource snapshots несовместимы.")
    chalk = run.get("chalk")
    if (
        not isinstance(chalk, dict)
        or chalk.get("status") != "exact"
        or chalk.get("pre_point_count") != pre_count
        or chalk.get("post_point_count") != post_count
        or chalk.get("consumed_points") != post_count - pre_count
    ):
        raise FillMatrixError("Bridge run exact CHALK не совпадает с pre/post pointCount.")
    sampled_total = run.get("sampled_point_delta_total")
    if (
        type(sampled_total) is not int
        or sampled_total != post_count - pre_count
        or run.get("point_delta_matches_chalk") is not True
    ):
        raise FillMatrixError("Bridge run sampled point deltas не совпадают с exact CHALK.")

    lifecycle_sources = run.get("stroke_lifecycle_sources")
    if (
        not isinstance(lifecycle_sources, list)
        or not lifecycle_sources
        or any(not isinstance(source, str) or source not in {"engine", "pointer_observer"} for source in lifecycle_sources)
        or len(set(lifecycle_sources)) != len(lifecycle_sources)
    ):
        raise FillMatrixError("Bridge run не содержит допустимый stroke_lifecycle_sources.")
    engine_pairs = _complete_lifecycle_pairs(events, "DRAW_START", "DRAW_END", expected_strokes)
    pointer_pairs = _complete_lifecycle_pairs(
        events, "POINTER_DOWN_CANDIDATE", "POINTER_UP_CANDIDATE", expected_strokes
    )
    if engine_pairs is not None and "engine" in lifecycle_sources:
        lifecycle_source = "engine"
    elif pointer_pairs is not None and "pointer_observer" in lifecycle_sources:
        lifecycle_source = "pointer_observer"
    else:
        raise FillMatrixError("Bridge run не содержит полного engine или pointer stroke lifecycle.")
    if any(event.get("monitorVersion") != "0.2.1" for event in events):
        raise FillMatrixError("Bridge run содержит событие с неизвестной версией Monitor.")

    return {
        "session_id": session_id,
        "stroke_lifecycle_source": lifecycle_source,
        "observed_radius": radii[0],
        "run_id": run_id,
        "monitor_version": "0.2.1",
        "event_count": event_count,
        "events": events,
        "pre_point_count": pre_count,
        "post_point_count": post_count,
        "exact_chalk": post_count - pre_count,
        "bridge_failures": run["bridge_send_failures_delta"],
        "sequence_gaps": run["collector_sequence_gap_count"],
        "dropped_events": run["dropped_events"] + run["monitor_buffer_dropped_events_delta"],
        "monitor_errors": list(run["monitor_errors"]),
        "bridge_run": run,
    }


def bind_fill001_runtime_evidence(
    task: dict[str, Any],
    session: dict[str, Any],
    bridge_runs: list[dict[str, Any]],
    executor_report: dict[str, Any],
) -> dict[str, Any]:
    """Bind exactly one real Bridge run to one executor report and frozen task."""
    context = build_fill001_experiment_context(task)
    executor_started, executor_ended, executor_meta = _validate_executor_report(task, executor_report)
    if not isinstance(bridge_runs, list):
        raise FillMatrixError("bridge_runs должен быть списком run records.")

    session_id = session.get("session_id") if isinstance(session, dict) else None
    grace = timedelta(seconds=_session_finalize_grace_seconds(session))
    candidates = []
    for run in bridge_runs:
        if not isinstance(run, dict):
            raise FillMatrixError("Bridge run должен быть JSON object.")
        started, activity_ended, _ = _bridge_run_activity_window(run, session)
        overlaps_executor = started < executor_ended and activity_ended > executor_started
        if overlaps_executor:
            if run.get("session_id") != session_id:
                raise FillMatrixError("Bridge run из executor activity window принадлежит другой session.")
            if started < executor_started:
                raise FillMatrixError("Bridge run activity началась до executor execution window.")
            if activity_ended > executor_ended + grace:
                raise FillMatrixError("Bridge run activity превысила executor window и idle finalization grace.")
            candidates.append(run)
    if not candidates:
        raise RuntimeBindingNotReady("Bridge run ещё не finalized/persisted для executor interval.")
    if len(candidates) != 1:
        raise FillMatrixError(
            f"Executor interval должен содержать ровно один Bridge run; найдено: {len(candidates)}."
        )

    verified = _validate_bridge_run(task, session, candidates[0], executor_started, executor_ended)
    bridge_run = verified["bridge_run"]
    monitor_export = {
        "schemaVersion": 1,
        "monitorVersion": verified["monitor_version"],
        "eventCount": verified["event_count"],
        "droppedEvents": verified["dropped_events"],
        "errors": verified["monitor_errors"],
        "events": verified["events"],
    }
    bridge_diagnostics = {
        "run_id": verified["run_id"],
        "event_count": verified["event_count"],
        "bridge_failures": verified["bridge_failures"],
        "sequence_gaps": verified["sequence_gaps"],
    }
    return {
        "task_id": context["task_id"],
        "session_id": verified["session_id"],
        "run_id": verified["run_id"],
        "execution_id": executor_meta["execution_id"],
        "sampling_profile": executor_meta["sampling_profile"],
        "executor_config": executor_meta["executor_config"],
        "source_plan_file_sha256": executor_meta["source_plan_file_sha256"],
        "pre_point_count": verified["pre_point_count"],
        "post_point_count": verified["post_point_count"],
        "exact_chalk": verified["exact_chalk"],
        "event_count": verified["event_count"],
        "bridge_failures": verified["bridge_failures"],
        "sequence_gaps": verified["sequence_gaps"],
        "stroke_lifecycle_source": verified["stroke_lifecycle_source"],
        "observed_radius": verified["observed_radius"],
        "monitor_export": monitor_export,
        "bridge_diagnostics": bridge_diagnostics,
        "bridge_run": bridge_run,
    }



def _verify_executor_source_plan(report: dict[str, Any]) -> None:
    source_value = report.get("source_plan_file")
    if not isinstance(source_value, str) or not source_value.strip():
        raise FillMatrixError("Executor report не содержит source_plan_file.")
    source_path = Path(source_value)
    try:
        raw = source_path.read_bytes()
    except OSError as exc:
        raise FillMatrixError(f"Source DrawingPlan недоступен: {exc}") from exc
    if hashlib.sha256(raw).hexdigest() != report.get("source_plan_file_sha256"):
        raise FillMatrixError("Source DrawingPlan file SHA-256 не совпадает с executor report.")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FillMatrixError("Source DrawingPlan не является корректным UTF-8 JSON.") from exc
    if not isinstance(document, dict) or document.get("autodraw_experiment") != report.get("experiment_context"):
        raise FillMatrixError("Source DrawingPlan context не совпадает с executor report.")
    plan_document = dict(document)
    plan_document.pop("autodraw_experiment", None)
    canonical_document = _canonical_drawing_plan_document(plan_document)
    canonical = json.dumps(
        canonical_document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    plan_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if plan_hash != report.get("source_plan_sha256"):
        raise FillMatrixError("Source DrawingPlan content не совпадает с executor source_plan_sha256.")


def load_fill001_runtime_binding(
    task: dict[str, Any],
    session_path: str | Path,
    executor_report_path: str | Path,
) -> dict[str, Any]:
    """Load session.json, all sibling run files, and the executor report from disk."""
    session_file = Path(session_path)
    report_file = Path(executor_report_path)
    if not session_file.is_file() or not report_file.is_file():
        raise FillMatrixError("Bridge session.json или executor report отсутствует.")
    try:
        session = json.loads(session_file.read_text(encoding="utf-8"))
        executor_report = json.loads(report_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FillMatrixError(f"Не удалось прочитать runtime evidence: {exc}") from exc
    if not isinstance(session, dict):
        raise FillMatrixError("session.json должен содержать JSON object.")
    if not isinstance(executor_report, dict):
        raise FillMatrixError("Executor report должен содержать JSON object.")
    _verify_executor_source_plan(executor_report)
    session_id = session.get("session_id")
    if session_file.parent.name != session_id:
        raise FillMatrixError("session.json расположен не в каталоге своего session_id.")

    run_files = sorted(session_file.parent.glob("game-monitor-run-*.json"))
    if not run_files:
        raise RuntimeBindingNotReady("В каталоге Bridge session пока нет finalized run-файлов.")
    bridge_runs = []
    run_hashes: dict[str, str] = {}
    for run_file in run_files:
        try:
            run = json.loads(run_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FillMatrixError(f"Не удалось прочитать Bridge run {run_file.name}: {exc}") from exc
        if not isinstance(run, dict):
            raise FillMatrixError(f"Bridge run {run_file.name} должен быть JSON object.")
        run_id = run.get("run_id")
        if not isinstance(run_id, str) or not run_file.name.endswith(f"-{run_id[:8]}.json"):
            raise FillMatrixError(f"Имя Bridge run-файла не соответствует run_id: {run_file.name}.")
        bridge_runs.append(run)
        run_hashes[run_id] = _sha256(run_file)

    binding = bind_fill001_runtime_evidence(task, session, bridge_runs, executor_report)
    binding["session_file"] = str(session_file)
    binding["session_file_sha256"] = _sha256(session_file)
    binding["executor_report_file"] = str(report_file)
    binding["executor_report_file_sha256"] = _sha256(report_file)
    binding["bridge_run_file_sha256"] = run_hashes[binding["run_id"]]
    matching = [
        path for path in run_files
        if path.name.endswith(f"-{binding['run_id'][:8]}.json")
    ]
    if len(matching) != 1:
        raise FillMatrixError("Не удалось однозначно определить Bridge run-файл по run_id.")
    binding["bridge_run_file"] = str(matching[0])
    return binding


def find_fill001_runtime_binding(
    task: dict[str, Any],
    bridge_root: str | Path,
    executor_report_path: str | Path,
) -> dict[str, Any] | None:
    """Discover the unique active Bridge session for an executor report.

    Returns None while the Bridge idle-finalization heartbeat has not persisted
    the run file. Multiple active sessions are rejected rather than guessed.
    """
    report_file = Path(executor_report_path)
    try:
        report = json.loads(report_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FillMatrixError(f"Не удалось прочитать executor report: {exc}") from exc
    if not isinstance(report, dict):
        raise FillMatrixError("Executor report должен быть JSON object.")
    _verify_executor_source_plan(report)
    executor_started, executor_ended, _ = _validate_executor_report(task, report)

    root = Path(bridge_root)
    if not root.is_dir():
        return None
    active_sessions: list[Path] = []
    for session_file in sorted(root.glob("*/session.json")):
        try:
            session = json.loads(session_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FillMatrixError(f"Не удалось прочитать Bridge session {session_file}: {exc}") from exc
        if not isinstance(session, dict):
            raise FillMatrixError(f"Bridge session {session_file} должен быть JSON object.")
        session_id = session.get("session_id")
        if not isinstance(session_id, str) or session_file.parent.name != session_id:
            raise FillMatrixError(f"Каталог Bridge session не совпадает с session_id: {session_file}.")
        try:
            session_started = _parse_aware_datetime(session.get("started_at_utc"), "session.started_at_utc")
            diagnostics = session.get("bridge_diagnostics")
            if not isinstance(diagnostics, dict):
                raise FillMatrixError("Bridge session не содержит bridge_diagnostics.")
            last_message = _parse_aware_datetime(
                diagnostics.get("last_message_at_utc"), "session.bridge_diagnostics.last_message_at_utc"
            )
        except FillMatrixError:
            # A session without timestamps cannot safely be excluded from the
            # executor window, so fail closed instead of silently skipping it.
            raise

        closed_at_value = session.get("connection_closed_at_utc")
        if closed_at_value:
            closed_at = _parse_aware_datetime(closed_at_value, "session.connection_closed_at_utc")
            if closed_at < executor_started:
                continue
        if session_started > executor_ended or last_message < executor_started:
            continue
        if session.get("schema_version") != 2:
            raise FillMatrixError("Активная Bridge session создана по устаревшей schema; требуется schema_version=2.")
        _session_finalize_grace_seconds(session)
        active_sessions.append(session_file)

    if not active_sessions:
        return None
    if len(active_sessions) != 1:
        raise FillMatrixError(
            f"Во время FILL-001 execution обнаружено несколько активных Bridge sessions: {len(active_sessions)}."
        )
    try:
        return load_fill001_runtime_binding(task, active_sessions[0], report_file)
    except RuntimeBindingNotReady:
        return None

