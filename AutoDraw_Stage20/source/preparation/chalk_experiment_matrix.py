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
}


def _normalize_series_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("ID серии CHALK должен быть текстом.")
    normalized = value.strip()
    if not normalized or len(normalized) > 64:
        raise ValueError("ID серии CHALK должен содержать от 1 до 64 символов.")
    if any(not (char.isalnum() or char in "-_.") for char in normalized):
        raise ValueError("ID серии может содержать только буквы, цифры, дефис, точку и подчёркивание.")
    return normalized


def build_chalk_experiment_matrix_metadata(
    *,
    series_id: str,
    scenario_id: str,
    repeat_index: int,
    requested_radius: int,
    strokes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create stable identity for one G1/G2 scenario repeat."""
    normalized_series = _normalize_series_id(series_id)
    if not isinstance(scenario_id, str):
        raise ValueError("ID сценария должен быть текстом.")
    phase_id = next(
        (phase for phase, scenarios in PHASE_SCENARIOS.items() if scenario_id in scenarios),
        None,
    )
    if phase_id is None:
        raise ValueError(f"Сценарий {scenario_id!r} не входит в план G1/G2.")
    if isinstance(repeat_index, bool) or not isinstance(repeat_index, int) or repeat_index not in (1, 2, 3):
        raise ValueError("Номер повтора должен быть целым числом 1, 2 или 3.")
    if isinstance(requested_radius, bool) or not isinstance(requested_radius, int) or not 1 <= requested_radius <= 30:
        raise ValueError("Радиус кисти должен быть целым числом от 1 до 30.")
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
        "planned_repeats": 3,
        "requested_radius": requested_radius,
        "expected_strokes": EXPECTED_STROKES[scenario_id],
        "geometry_signature": geometry_signature,
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

    if len(stroke_order) != expected_strokes:
        return {
            "status": "incomplete",
            "reason": "stroke_id_count_mismatch",
            "observed_stroke_ids": len(stroke_order),
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
        "strokes": [
            {
                "stroke_index": index + 1,
                "stroke_id": stroke_id,
                "consumed_points": totals[stroke_id],
                "draw_sample_events": sample_counts[stroke_id],
            }
            for index, stroke_id in enumerate(stroke_order)
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
            strokes=metadata.get("planned_strokes") if isinstance(metadata.get("planned_strokes"), list) else [
                {} for _ in range(int(metadata.get("expected_strokes", 0) or 0))
            ],
        )
    except (TypeError, ValueError, OverflowError) as exc:
        return False, f"invalid_matrix_metadata:{exc}", None
    for key in ("schema_version", "series_id", "phase_id", "scenario_id", "repeat_index",
                "planned_repeats", "requested_radius", "expected_strokes", "geometry_signature"):
        if metadata.get(key) != expected.get(key):
            return False, f"matrix_metadata_mismatch:{key}", None
    if metadata.get("geometry_signature") != expected.get("geometry_signature"):
        return False, "geometry_signature_mismatch", None
    if document.get("test_case") != expected["scenario_id"]:
        return False, "scenario_mismatch", None
    if document.get("brush_value_requested") != expected["requested_radius"]:
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
    if capture.get("stroke_count") != expected["expected_strokes"] or capture.get("expected_stroke_count") != expected["expected_strokes"]:
        return False, "capture_stroke_count_mismatch", None
    if capture.get("brush_radius_status") != "single" or capture.get("chalk_status") != "exact":
        return False, "capture_radius_or_chalk_status_invalid", None
    if capture.get("chalk_counter_consistent") is not True or capture.get("point_delta_matches_chalk") is not True:
        return False, "capture_counter_validation_failed", None
    if any(capture.get(key, 0) != 0 for key in ("dropped_events", "monitor_dropped_events", "monitor_error_count")):
        return False, "capture_has_dropped_events_or_errors", None
    if summary.get("brush_radius_status") != "single" or summary.get("observed_brush_radii") != [expected["requested_radius"]]:
        return False, "observed_radius_mismatch", None
    if summary.get("stroke_count") != expected["expected_strokes"] or summary.get("point_delta_matches_chalk") is not True:
        return False, "summary_stroke_or_delta_mismatch", None
    if any(summary.get(key, 0) != 0 for key in ("dropped_events", "monitor_dropped_events", "monitor_error_count")):
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
    if execution.get("completed_strokes") != expected["expected_strokes"]:
        return False, "executor_stroke_count_mismatch", None

    run_id = capture.get("run_id") or summary.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip() or (
        capture.get("run_id") and summary.get("run_id") and capture.get("run_id") != summary.get("run_id")
    ):
        return False, "monitor_run_id_invalid", None
    return True, "valid", {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "series_id": expected["series_id"],
        "phase_id": expected["phase_id"],
        "scenario_id": expected["scenario_id"],
        "repeat_index": expected["repeat_index"],
        "radius": expected["requested_radius"],
        "geometry_signature": expected["geometry_signature"],
        "expected_strokes": expected["expected_strokes"],
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
    cell_counts: dict[tuple[str, str, str, int], int] = {}
    for _, valid, _, record in evaluated:
        if valid and record:
            run_counts[record["run_id"]] = run_counts.get(record["run_id"], 0) + 1
            key = (record["series_id"], record["phase_id"], record["scenario_id"], record["repeat_index"])
            cell_counts[key] = cell_counts.get(key, 0) + 1

    accepted, rejected = [], []
    for document, valid, reason, record in evaluated:
        if valid and record:
            key = (record["series_id"], record["phase_id"], record["scenario_id"], record["repeat_index"])
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

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for record in accepted:
        key = (record["series_id"], record["phase_id"], record["scenario_id"])
        grouped.setdefault(key, []).append(record)

    results = []
    for (series_id, phase_id, scenario_id), rows in sorted(grouped.items()):
        rows.sort(key=lambda row: row["repeat_index"])
        values = [row["consumed_points"] for row in rows]
        signatures = {row["geometry_signature"] for row in rows}
        results.append({
            "series_id": series_id,
            "phase_id": phase_id,
            "scenario_id": scenario_id,
            "valid_repeat_count": len(rows),
            "complete": len(rows) == 3 and {row["repeat_index"] for row in rows} == {1, 2, 3},
            "geometry_consistent": len(signatures) == 1,
            "measurements": rows,
            "mean": mean(values) if values else None,
            "median": median(values) if values else None,
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
