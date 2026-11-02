from __future__ import annotations

"""Validation and aggregation for controlled CHALK geometry/sampling experiments."""

import hashlib
import json
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Iterable


PHASE_SCENARIOS = {
    "G1": ("horizontal_lengths", "vertical_lengths", "diagonal_lengths", "short_strokes"),
    "G2": (
        "long_isolated_lines",
        "continuous_turns",
        "continuous_closed_contour",
        "repeated_coverage",
        "parallel_spacing",
        "cross_section_intersections",
    ),
    "G3": ("paint_consumption_long_lines",),
    "V1": ("int006_diagonals",),
    "V2": ("int006_short_strokes_followup",),
    "V3": ("int006_turns",),
    "V4": ("int006_closed_contours",),
    "V5": ("int006_intersections_spacing_sweep",),
}
LEGACY_V_SCENARIO_PHASES = {
    "int006_short_strokes": "V2",
    "int006_intersections_spacing": "V5",
}
PHASE_BY_SCENARIO = {
    scenario: phase for phase, scenarios in PHASE_SCENARIOS.items() for scenario in scenarios
}
PHASE_BY_SCENARIO.update(LEGACY_V_SCENARIO_PHASES)
GEOMETRY_MATRIX_SCENARIOS = frozenset(PHASE_BY_SCENARIO)
GEOMETRY_EXECUTOR_CONFIG = {
    "point_step_px": 2,
    "line_extension_px": 0,
    "point_delay_ms": 10,
    "after_mouse_up_ms": 20,
    "before_mouse_down_ms": 20,
    "after_mouse_down_ms": 40,
    "end_hold_ms": 50,
    "countdown_seconds": 5,
}
EXPECTED_STROKES = {
    "horizontal_lengths": 5,
    "vertical_lengths": 4,
    "diagonal_lengths": 3,
    "short_strokes": 7,
    "long_isolated_lines": 6,
    "continuous_turns": 3,
    "continuous_closed_contour": 2,
    "repeated_coverage": 4,
    "parallel_spacing": 8,
    "cross_section_intersections": 4,
    "paint_consumption_long_lines": 6,
    "int006_diagonals": 6,
    "int006_short_strokes_followup": 5,
    "int006_turns": 3,
    "int006_closed_contours": 3,
    "int006_intersections_spacing_sweep": 16,
}

G3_POINT_STEPS = (1, 2, 4)
G3_POINT_DELAYS_MS = (5, 10, 20)
V_SAMPLING_PROFILES = ((2, 10), (4, 5), (4, 10))
V_PHASES = frozenset(("V1", "V2", "V3", "V4", "V5"))


def _validated_executor_parameters(phase_id: str, value: Any = None) -> dict[str, Any]:
    """Validate the complete executor configuration for one matrix phase."""
    parameters = dict(GEOMETRY_EXECUTOR_CONFIG if value is None else value)
    if set(parameters) != set(GEOMETRY_EXECUTOR_CONFIG):
        raise ValueError("Набор параметров исполнителя не совпадает со схемой CHALK.")
    if phase_id == "G3":
        step = parameters.get("point_step_px")
        delay = parameters.get("point_delay_ms")
        if isinstance(step, bool) or not isinstance(step, int) or step not in G3_POINT_STEPS:
            raise ValueError("G3 допускает point_step_px только 1, 2 или 4.")
        if isinstance(delay, bool) or not isinstance(delay, int) or delay not in G3_POINT_DELAYS_MS:
            raise ValueError("G3 допускает point_delay_ms только 5, 10 или 20.")
        expected = dict(GEOMETRY_EXECUTOR_CONFIG)
        expected.update({"point_step_px": step, "point_delay_ms": delay})
        if parameters != expected:
            raise ValueError("В G3 разрешено менять только point_step_px и point_delay_ms.")
    elif phase_id in V_PHASES:
        step = parameters.get("point_step_px")
        delay = parameters.get("point_delay_ms")
        if (step, delay) not in V_SAMPLING_PROFILES:
            raise ValueError("V1–V5 допускают только профили P0=2/10, P1=4/5 и P2=4/10.")
        expected = dict(GEOMETRY_EXECUTOR_CONFIG)
        expected.update({"point_step_px": step, "point_delay_ms": delay})
        if parameters != expected:
            raise ValueError("В V1–V5 разрешено менять только point_step_px и point_delay_ms.")
    elif parameters != GEOMETRY_EXECUTOR_CONFIG:
        raise ValueError("В G1/G2 требуется штатная конфигурация исполнителя.")
    return parameters


def _normalize_series_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("ID серии CHALK должен быть текстом.")
    normalized = value.strip()
    if not normalized or len(normalized) > 64:
        raise ValueError("ID серии CHALK должен содержать от 1 до 64 символов.")
    if any(not (char.isalnum() or char in "-_.") for char in normalized):
        raise ValueError("ID серии может содержать только буквы, цифры, дефис, точку и подчёркивание.")
    return normalized


def inspect_chalk_matrix_series(
    results_dir: str | Path,
    *,
    series_id: str,
    scenario_id: str,
    repeat_index: int,
    executor_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Find an occupied repeat cell and calculate the next chronological series index."""
    normalized_series = _normalize_series_id(series_id)
    if scenario_id not in GEOMETRY_MATRIX_SCENARIOS:
        raise ValueError(f"Неизвестный сценарий CHALK: {scenario_id!r}.")
    if isinstance(repeat_index, bool) or not isinstance(repeat_index, int) or repeat_index not in (1, 2, 3):
        raise ValueError("Номер повтора должен быть целым числом 1, 2 или 3.")
    phase_id = PHASE_BY_SCENARIO[scenario_id]
    parameters = _validated_executor_parameters(phase_id, executor_parameters)

    series_count = 0
    max_order_index = 0
    duplicate_path = None
    root = Path(results_dir)
    if root.exists():
        for manifest_path in root.rglob("experiment.json"):
            try:
                document = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            metadata = document.get("chalk_experiment_matrix") if isinstance(document, dict) else None
            if not isinstance(metadata, dict) or metadata.get("series_id") != normalized_series:
                continue
            series_count += 1
            order = metadata.get("matrix_order_index")
            if isinstance(order, int) and not isinstance(order, bool) and order > max_order_index:
                max_order_index = order
            if (
                metadata.get("scenario_id") == scenario_id
                and metadata.get("repeat_index") == repeat_index
                and metadata.get("executor_parameters", GEOMETRY_EXECUTOR_CONFIG) == parameters
            ):
                duplicate_path = manifest_path
    return {
        "next_matrix_order_index": max(series_count, max_order_index) + 1,
        "duplicate_manifest_path": str(duplicate_path) if duplicate_path else None,
        "series_experiment_count": series_count,
    }


def build_chalk_experiment_matrix_metadata(
    *,
    series_id: str,
    scenario_id: str,
    repeat_index: int,
    requested_radius: int,
    strokes: list[dict[str, Any]],
    matrix_order_index: int = 1,
    executor_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create stable identity for one G1/G2/G3/V1-V5 experiment cell."""
    normalized_series = _normalize_series_id(series_id)
    if not isinstance(scenario_id, str):
        raise ValueError("ID сценария должен быть текстом.")
    phase_id = PHASE_BY_SCENARIO.get(scenario_id)
    if phase_id is None:
        raise ValueError(f"Сценарий {scenario_id!r} не входит в план G1/G2/G3/V1-V5.")
    parameters = _validated_executor_parameters(phase_id, executor_parameters)
    if isinstance(repeat_index, bool) or not isinstance(repeat_index, int) or repeat_index not in (1, 2, 3):
        raise ValueError("Номер повтора должен быть целым числом 1, 2 или 3.")
    if isinstance(matrix_order_index, bool) or not isinstance(matrix_order_index, int) or matrix_order_index < 1:
        raise ValueError("Порядковый номер эксперимента должен быть положительным целым числом.")
    if isinstance(requested_radius, bool) or not isinstance(requested_radius, int) or requested_radius != 10:
        raise ValueError("Для серий G1/G2/G3/V1-V5 требуется фиксированный радиус кисти 10.")
    if not isinstance(strokes, list) or len(strokes) != EXPECTED_STROKES[scenario_id]:
        raise ValueError(f"Сценарий {scenario_id} должен содержать {EXPECTED_STROKES[scenario_id]} штрихов.")
    canonical_geometry = json.dumps(strokes, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    geometry_signature = hashlib.sha256(canonical_geometry.encode("utf-8")).hexdigest()
    return {
        "schema_version": 1,
        "series_id": normalized_series,
        "phase_id": phase_id,
        "scenario_id": scenario_id,
        "repeat_index": repeat_index,
        "matrix_order_index": matrix_order_index,
        "planned_repeats": 3,
        "requested_radius": requested_radius,
        "expected_strokes": EXPECTED_STROKES[scenario_id],
        "geometry_signature": geometry_signature,
        "planned_strokes": json.loads(canonical_geometry),
        "executor_parameters": parameters,
    }


def _stroke_level_breakdown(
    experiment_dir: str | Path | None,
    *,
    expected_strokes: int,
    expected_chalk: int,
) -> dict[str, Any]:
    """Aggregate DRAW_SAMPLE pointDelta by strokeId and fail closed if the split is incomplete."""
    if experiment_dir is None:
        return {"status": "incomplete", "reason": "experiment_dir_unavailable", "strokes": []}
    report_path = Path(experiment_dir) / "monitor_report.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"status": "incomplete", "reason": "monitor_report_unavailable", "strokes": []}
    events = report.get("events") if isinstance(report, dict) else None
    if not isinstance(events, list):
        return {"status": "incomplete", "reason": "monitor_events_unavailable", "strokes": []}

    stroke_order: list[str] = []
    totals: dict[str, int] = {}
    sample_counts: dict[str, int] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        stroke_id = event.get("strokeId")
        if not isinstance(stroke_id, str) or not stroke_id:
            continue
        if stroke_id not in totals:
            stroke_order.append(stroke_id)
            totals[stroke_id] = 0
            sample_counts[stroke_id] = 0
        if event.get("type") == "DRAW_SAMPLE":
            try:
                delta = int(event.get("pointDelta", 0) or 0)
            except (TypeError, ValueError, OverflowError):
                return {"status": "incomplete", "reason": "unreadable_point_delta", "strokes": []}
            if delta < 0:
                return {"status": "incomplete", "reason": "negative_point_delta", "strokes": []}
            totals[stroke_id] += delta
            sample_counts[stroke_id] += 1

    consuming_stroke_order = [stroke_id for stroke_id in stroke_order if totals[stroke_id] > 0]
    non_consuming_stroke_ids = [stroke_id for stroke_id in stroke_order if totals[stroke_id] == 0]
    if len(consuming_stroke_order) != expected_strokes:
        return {
            "status": "incomplete",
            "reason": "stroke_id_count_mismatch",
            "observed_stroke_ids": len(consuming_stroke_order),
            "observed_stroke_candidates": len(stroke_order),
            "non_consuming_stroke_ids": non_consuming_stroke_ids,
            "expected_strokes": expected_strokes,
            "strokes": [],
        }
    if sum(totals.values()) != expected_chalk:
        return {
            "status": "incomplete",
            "reason": "stroke_delta_sum_mismatch",
            "stroke_delta_total": sum(totals.values()),
            "expected_chalk": expected_chalk,
            "strokes": [],
        }
    return {
        "status": "complete",
        "reason": None,
        "observed_stroke_candidates": len(stroke_order),
        "non_consuming_stroke_ids": non_consuming_stroke_ids,
        "strokes": [
            {
                "stroke_index": index + 1,
                "stroke_id": stroke_id,
                "consumed_points": totals[stroke_id],
                "draw_sample_events": sample_counts[stroke_id],
            }
            for index, stroke_id in enumerate(consuming_stroke_order)
        ],
    }


def _validate_manifest(document: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
    metadata = document.get("chalk_experiment_matrix")
    if not isinstance(metadata, dict):
        return False, "matrix_metadata_missing", None
    try:
        expected = build_chalk_experiment_matrix_metadata(
            series_id=metadata.get("series_id"),
            scenario_id=metadata.get("scenario_id"),
            repeat_index=metadata.get("repeat_index"),
            requested_radius=metadata.get("requested_radius"),
            matrix_order_index=metadata.get("matrix_order_index", 1),
            strokes=metadata.get("planned_strokes"),
            executor_parameters=metadata.get("executor_parameters"),
        )
    except (TypeError, ValueError, OverflowError) as exc:
        return False, f"invalid_matrix_metadata:{exc}", None
    for key in ("schema_version", "series_id", "phase_id", "scenario_id", "repeat_index",
                "planned_repeats", "requested_radius", "expected_strokes", "geometry_signature",
                "planned_strokes", "executor_parameters"):
        if metadata.get(key) != expected.get(key):
            return False, f"matrix_metadata_mismatch:{key}", None
    series_id = expected["series_id"]
    phase_id = expected["phase_id"]
    scenario_id = expected["scenario_id"]
    repeat_index = expected["repeat_index"]
    radius = expected["requested_radius"]
    expected_strokes = expected["expected_strokes"]
    signature = expected["geometry_signature"]
    if "matrix_order_index" in metadata and metadata.get("matrix_order_index") != expected["matrix_order_index"]:
        return False, "matrix_metadata_mismatch:matrix_order_index", None
    if document.get("test_case") != scenario_id:
        return False, "scenario_mismatch", None
    if document.get("brush_value_requested") != radius:
        return False, "requested_radius_mismatch", None

    capture = document.get("monitor_capture")
    capture = capture if isinstance(capture, dict) else {}
    summary = document.get("game_monitor_summary")
    summary = summary if isinstance(summary, dict) else {}
    experiment_id = document.get("experiment_id")
    if capture.get("status") != "saved":
        return False, "monitor_capture_not_saved", None
    if not experiment_id or capture.get("experiment_id") != experiment_id:
        return False, "experiment_id_mismatch", None
    if summary.get("autodraw_experiment_id") != experiment_id:
        return False, "summary_experiment_id_mismatch", None
    if capture.get("chalk_experiment_matrix") != metadata or summary.get("chalk_experiment_matrix") != metadata:
        return False, "capture_matrix_metadata_mismatch", None
    if capture.get("stroke_count") != expected_strokes or capture.get("expected_stroke_count") != expected_strokes:
        return False, "capture_stroke_count_mismatch", None
    if capture.get("brush_radius_status") != "single" or capture.get("chalk_status") != "exact":
        return False, "capture_radius_or_chalk_status_invalid", None
    if capture.get("chalk_counter_consistent") is not True or capture.get("point_delta_matches_chalk") is not True:
        return False, "capture_counter_validation_failed", None
    if any(capture.get(key, 0) != 0 for key in (
        "dropped_events", "monitor_error_count_delta", "bridge_send_failures_delta",
        "collector_sequence_gap_count"
    )):
        return False, "capture_has_dropped_events_or_errors", None
    if summary.get("brush_radius_status") != "single" or summary.get("observed_brush_radii") != [radius]:
        return False, "observed_radius_mismatch", None
    if summary.get("stroke_count") != expected_strokes or summary.get("point_delta_matches_chalk") is not True:
        return False, "summary_stroke_or_delta_mismatch", None
    if any(summary.get(key, 0) != 0 for key in (
        "dropped_events", "monitor_error_count_delta", "bridge_send_failures_delta",
        "collector_sequence_gap_count"
    )):
        return False, "summary_has_dropped_events_or_errors", None

    chalk = summary.get("chalk")
    chalk = chalk if isinstance(chalk, dict) else {}
    try:
        pre, post, consumed = int(chalk["pre_point_count"]), int(chalk["post_point_count"]), int(chalk["consumed_points"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return False, "chalk_counter_missing", None
    if chalk.get("status") != "exact" or post < pre or post - pre != consumed or consumed <= 0:
        return False, "chalk_counter_inexact", None
    if summary.get("sampled_point_delta_total") != consumed:
        return False, "sampled_delta_mismatch", None

    execution = document.get("execution_report")
    execution = execution if isinstance(execution, dict) else {}
    if execution.get("status") != "completed":
        return False, "executor_not_completed", None
    if execution.get("completed_strokes") != expected_strokes:
        return False, "executor_stroke_count_mismatch", None
    executor_config = execution.get("executor_config")
    if not isinstance(executor_config, dict) or any(
        executor_config.get(key) != value
        for key, value in expected["executor_parameters"].items()
    ):
        return False, "executor_parameters_mismatch", None

    run_id = capture.get("run_id") or summary.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip() or (
        capture.get("run_id") and summary.get("run_id") and capture.get("run_id") != summary.get("run_id")
    ):
        return False, "monitor_run_id_invalid", None
    return True, "valid", {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "series_id": series_id,
        "phase_id": phase_id,
        "scenario_id": scenario_id,
        "repeat_index": repeat_index,
        "matrix_order_index": expected["matrix_order_index"],
        "radius": radius,
        "executor_parameters": dict(expected["executor_parameters"]),
        "geometry_signature": signature,
        "expected_strokes": expected_strokes,
        "consumed_points": consumed,
        "pre_point_count": pre,
        "post_point_count": post,
    }


def summarize_chalk_experiment_matrix(
    documents: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Validate generic G1/G2 manifests, reject duplicate cells/runs, and aggregate repeats."""
    evaluated = []
    for document in documents:
        if isinstance(document, dict):
            valid, reason, record = _validate_manifest(document)
            evaluated.append((document, valid, reason, record))

    run_counts: dict[str, int] = {}
    cell_counts: dict[tuple[str, str, str, int, int, int, int], int] = {}
    for _, valid, _, record in evaluated:
        if valid and record:
            run_counts[record["run_id"]] = run_counts.get(record["run_id"], 0) + 1
            parameters = record["executor_parameters"]
            key = (
                record["series_id"], record["phase_id"], record["scenario_id"], record["radius"],
                parameters["point_step_px"], parameters["point_delay_ms"], record["repeat_index"],
            )
            cell_counts[key] = cell_counts.get(key, 0) + 1

    accepted, rejected = [], []
    for document, valid, reason, record in evaluated:
        if valid and record:
            parameters = record["executor_parameters"]
            key = (
                record["series_id"], record["phase_id"], record["scenario_id"], record["radius"],
                parameters["point_step_px"], parameters["point_delay_ms"], record["repeat_index"],
            )
            if run_counts[record["run_id"]] > 1:
                valid, reason = False, "duplicate_monitor_run"
            elif cell_counts[key] > 1:
                valid, reason = False, "duplicate_matrix_cell"
        if valid and record:
            breakdown = _stroke_level_breakdown(
                document.get("experiment_dir"),
                expected_strokes=record["expected_strokes"],
                expected_chalk=record["consumed_points"],
            )
            record["stroke_level"] = breakdown
            accepted.append(record)
        else:
            rejected.append({
                "experiment_id": document.get("experiment_id"),
                "reason": reason,
                "experiment_dir": document.get("experiment_dir"),
            })

    grouped: dict[tuple[str, str, str, int, int, int, str], list[dict[str, Any]]] = {}
    for record in accepted:
        parameters = record["executor_parameters"]
        key = (
            record["series_id"], record["phase_id"], record["scenario_id"], record["radius"],
            parameters["point_step_px"], parameters["point_delay_ms"], record["geometry_signature"],
        )
        grouped.setdefault(key, []).append(record)

    results = []
    for (series_id, phase_id, scenario_id, radius, point_step_px, point_delay_ms, geometry_signature), rows in sorted(grouped.items()):
        rows.sort(key=lambda row: row["repeat_index"])
        values = [row["consumed_points"] for row in rows]
        complete = len(rows) == 3 and {row["repeat_index"] for row in rows} == {1, 2, 3}
        results.append({
            "series_id": series_id,
            "phase_id": phase_id,
            "scenario_id": scenario_id,
            "radius": radius,
            "executor_parameters": dict(rows[0]["executor_parameters"]),
            "point_step_px": point_step_px,
            "point_delay_ms": point_delay_ms,
            "geometry_signature": geometry_signature,
            "valid_repeat_count": len(rows),
            "complete": complete,
            "geometry_consistent": True,
            "measurements": rows,
            "mean": mean(values) if complete else None,
            "partial_mean": mean(values) if values else None,
            "median": median(values) if complete else None,
            "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "range": max(values) - min(values) if values else None,
            "population_stddev": pstdev(values) if len(values) > 1 else (0.0 if values else None),
            "stroke_level_complete_repeat_count": sum(
                row["stroke_level"].get("status") == "complete" for row in rows
            ),
        })
    return {
        "schema_version": 1,
        "valid_measurement_count": len(accepted),
        "rejected_measurement_count": len(rejected),
        "scenarios": results,
        "rejected": rejected,
    }
