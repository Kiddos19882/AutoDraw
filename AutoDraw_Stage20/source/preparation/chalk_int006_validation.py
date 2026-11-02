from __future__ import annotations

"""Frozen INT-006 CHALK predictions and independent validation analysis.

This module is experimental-only. It never changes the production estimator.
"""

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from chalk_experiment_matrix import (
    GEOMETRY_EXECUTOR_CONFIG,
    INDEPENDENT_VALIDATION_PHASE,
    V_SAMPLING_PROFILES,
    _validate_manifest,
    _stroke_level_breakdown,
)

MODEL_ID = "chalk-int006-frozen-2026-11-02"
MODEL_VERSION = 1
RADIUS = 10
PROFILES = {
    "P0": {"point_step_px": 2, "point_delay_ms": 10, "intercept": 1.765, "slope": 0.2988},
    "P1": {"point_step_px": 4, "point_delay_ms": 5, "intercept": 1.475, "slope": 0.148865},
    "P2": {"point_step_px": 4, "point_delay_ms": 10, "intercept": 1.440, "slope": 0.149151},
}
SHORT_LOOKUP = {
    1: {"P0": 2.00, "P1": 2.00, "P2": 2.00},
    2: {"P0": 2.67, "P1": 2.00, "P2": 2.00},
    3: {"P0": 2.67, "P1": 2.00, "P2": 2.00},
    5: {"P0": 3.67, "P1": 2.33, "P2": 2.67},
    8: {"P0": 4.00, "P1": 3.00, "P2": 3.00},
    10: {"P0": 5.00, "P1": 3.67, "P2": 3.67},
}
EXPECTED_TOTALS = {
    "int006_validation_d1_mixed_lines": {"P0": 120.30, "P1": 62.32, "P2": 62.29},
    "int006_validation_d2_polygon": {"P0": 135.79, "P1": 70.63, "P2": 70.58},
    "int006_validation_d3_intersections": {"P0": 193.71, "P1": 100.08, "P2": 100.05},
    "int006_validation_d4_short_details": {"P0": 20.01, "P1": 15.00, "P2": 15.34},
    "int006_validation_d5_repeated_coverage": {"P0": 171.94, "P1": 89.24, "P2": 89.18},
}
DRAWING_PLANS = {
    "int006_validation_d1_mixed_lines": [
        {"name": "d1_horizontal_100", "points": [[30, 30], [130, 30]]},
        {"name": "d1_vertical_80", "points": [[160, 20], [160, 100]]},
        {"name": "d1_diagonal_1", "points": [[210, 25], [280, 95]]},
        {"name": "d1_diagonal_2", "points": [[310, 100], [390, 40]]},
    ],
    "int006_validation_d2_polygon": [
        {"name": "d2_side_1", "points": [[40, 35], [130, 25]]},
        {"name": "d2_side_2", "points": [[130, 25], [170, 85]]},
        {"name": "d2_side_3", "points": [[170, 85], [110, 155]]},
        {"name": "d2_side_4", "points": [[110, 155], [30, 115]]},
        {"name": "d2_side_5", "points": [[30, 115], [40, 35]]},
    ],
    "int006_validation_d3_intersections": [
        {"name": "d3_x_a", "points": [[40, 30], [140, 130]]},
        {"name": "d3_x_b", "points": [[40, 130], [140, 30]]},
        {"name": "d3_cross_vertical", "points": [[230, 30], [230, 150]]},
        {"name": "d3_cross_horizontal", "points": [[170, 90], [290, 90]]},
        {"name": "d3_t_horizontal", "points": [[330, 40], [390, 40]]},
        {"name": "d3_t_vertical", "points": [[360, 10], [360, 40]]},
    ],
    "int006_validation_d4_short_details": [
        {"name": "d4_length_1", "points": [[30, 30], [31, 30]]},
        {"name": "d4_length_2", "points": [[60, 30], [60, 32]]},
        {"name": "d4_length_3", "points": [[90, 30], [93, 30]]},
        {"name": "d4_length_5", "points": [[130, 30], [130, 35]]},
        {"name": "d4_length_8", "points": [[170, 30], [178, 30]]},
        {"name": "d4_length_10", "points": [[210, 30], [210, 40]]},
    ],
    "int006_validation_d5_repeated_coverage": [
        {"name": "d5_line_50_pass_1", "points": [[40, 40], [90, 40]]},
        {"name": "d5_line_50_pass_2", "points": [[40, 40], [90, 40]]},
        {"name": "d5_line_100_pass_1", "points": [[40, 90], [140, 90]]},
        {"name": "d5_line_100_pass_2", "points": [[40, 90], [140, 90]]},
        {"name": "d5_line_120_pass_1", "points": [[40, 150], [160, 150]]},
        {"name": "d5_line_120_pass_2", "points": [[40, 150], [160, 150]]},
    ],
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _distance(stroke: dict[str, Any]) -> float:
    points = stroke.get("points")
    if not isinstance(points, list) or len(points) != 2:
        raise ValueError("INT-006 допускает только прямой stroke с двумя конечными точками.")
    (x1, y1), (x2, y2) = points
    return math.hypot(float(x2) - float(x1), float(y2) - float(y1))


def _profile_name(parameters: dict[str, Any]) -> str:
    for name, profile in PROFILES.items():
        if (parameters.get("point_step_px"), parameters.get("point_delay_ms")) == (
            profile["point_step_px"], profile["point_delay_ms"]
        ):
            return name
    raise ValueError("Неизвестный sampling profile INT-006.")


def _prediction_for_stroke(stroke: dict[str, Any], profile_name: str) -> dict[str, Any]:
    length = _distance(stroke)
    rounded_length = round(length)
    if abs(length - rounded_length) < 1e-9 and rounded_length in SHORT_LOOKUP:
        return {
            "stroke_id": stroke["name"],
            "length_logical_px": length,
            "rule": "exact_short_lookup",
            "predicted_chalk": SHORT_LOOKUP[rounded_length][profile_name],
        }
    profile = PROFILES[profile_name]
    return {
        "stroke_id": stroke["name"],
        "length_logical_px": length,
        "rule": "straight_line_linear",
        "predicted_chalk": profile["intercept"] + profile["slope"] * length,
    }


def build_int006_prediction_artifact(series_id: str) -> dict[str, Any]:
    """Create a complete, hash-sealed 15-record prediction snapshot before live captures."""
    if not isinstance(series_id, str) or not series_id.strip():
        raise ValueError("Для prediction artifact требуется series_id.")
    records = {}
    for scenario_id, strokes in DRAWING_PLANS.items():
        geometry_signature = _sha256(strokes)
        for profile_name, profile in PROFILES.items():
            prediction_id = f"{MODEL_ID}:{scenario_id}:{profile_name}"
            stroke_predictions = [_prediction_for_stroke(stroke, profile_name) for stroke in strokes]
            calculated_total = sum(item["predicted_chalk"] for item in stroke_predictions)
            frozen_total = EXPECTED_TOTALS[scenario_id][profile_name]
            if abs(calculated_total - frozen_total) > 0.011:
                raise ValueError(f"Сумма stroke predictions не совпадает с frozen total: {prediction_id}")
            records[prediction_id] = {
                "prediction_id": prediction_id,
                "model_id": MODEL_ID,
                "model_version": MODEL_VERSION,
                "series_id": series_id,
                "phase_id": INDEPENDENT_VALIDATION_PHASE,
                "scenario_id": scenario_id,
                "profile_id": profile_name,
                "executor_parameters": {
                    **GEOMETRY_EXECUTOR_CONFIG,
                    "point_step_px": profile["point_step_px"],
                    "point_delay_ms": profile["point_delay_ms"],
                },
                "radius": RADIUS,
                "geometry_signature": geometry_signature,
                "drawing_plan_sha256": geometry_signature,
                "planned_strokes": strokes,
                "stroke_predictions": stroke_predictions,
                "prediction_rule": "exact_short_lookup" if scenario_id == "int006_validation_d4_short_details" else "straight_line_linear",
                "predicted_chalk": frozen_total,
                "calculated_unrounded_total": calculated_total,
                "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
    body = {
        "schema_version": 1,
        "record_type": "autodraw_int006_frozen_prediction_artifact",
        "artifact_id": f"{MODEL_ID}:{series_id}",
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "series_id": series_id,
        "phase_id": INDEPENDENT_VALIDATION_PHASE,
        "radius": RADIUS,
        "profiles": PROFILES,
        "short_lookup": SHORT_LOOKUP,
        "expected_cell_count": 45,
        "predictions": records,
    }
    # Seal the exact JSON representation persisted by the block journal.
    body = json.loads(json.dumps(body, ensure_ascii=False, allow_nan=False))
    body["artifact_sha256"] = _sha256(body)
    return body


def validate_int006_prediction_artifact(artifact: Any, *, expected_series_id: str | None = None) -> tuple[bool, str]:
    if not isinstance(artifact, dict) or artifact.get("record_type") != "autodraw_int006_frozen_prediction_artifact":
        return False, "prediction_artifact_missing_or_invalid"
    supplied_hash = artifact.get("artifact_sha256")
    body = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    if not isinstance(supplied_hash, str) or _sha256(body) != supplied_hash:
        return False, "prediction_artifact_hash_mismatch"
    if artifact.get("model_id") != MODEL_ID or artifact.get("model_version") != MODEL_VERSION:
        return False, "prediction_model_version_mismatch"
    if expected_series_id is not None and artifact.get("series_id") != expected_series_id:
        return False, "prediction_series_mismatch"
    if artifact.get("artifact_id") != f"{MODEL_ID}:{artifact.get('series_id')}":
        return False, "prediction_artifact_identity_mismatch"
    if artifact.get("phase_id") != INDEPENDENT_VALIDATION_PHASE or artifact.get("radius") != RADIUS:
        return False, "prediction_artifact_contract_mismatch"
    if artifact.get("expected_cell_count") != 45:
        return False, "prediction_expected_cell_count_mismatch"
    if artifact.get("profiles") != PROFILES or artifact.get("short_lookup") != SHORT_LOOKUP:
        return False, "prediction_model_parameters_mismatch"
    predictions = artifact.get("predictions")
    if not isinstance(predictions, dict) or len(predictions) != 15:
        return False, "prediction_record_count_mismatch"
    expected_ids = {
        f"{MODEL_ID}:{scenario}:{profile}"
        for scenario in DRAWING_PLANS for profile in PROFILES
    }
    if set(predictions) != expected_ids:
        return False, "prediction_record_identity_mismatch"
    for prediction_id, record in predictions.items():
        if not isinstance(record, dict):
            return False, "prediction_record_schema_invalid"
        scenario_id = record.get("scenario_id")
        profile_id = record.get("profile_id")
        if scenario_id not in DRAWING_PLANS or profile_id not in PROFILES:
            return False, "prediction_record_schema_invalid"
        profile = PROFILES[profile_id]
        expected_parameters = {
            **GEOMETRY_EXECUTOR_CONFIG,
            "point_step_px": profile["point_step_px"],
            "point_delay_ms": profile["point_delay_ms"],
        }
        expected_strokes = DRAWING_PLANS[scenario_id]
        expected_signature = _sha256(expected_strokes)
        expected_stroke_predictions = [
            _prediction_for_stroke(stroke, profile_id) for stroke in expected_strokes
        ]
        expected_rule = "exact_short_lookup" if scenario_id == "int006_validation_d4_short_details" else "straight_line_linear"
        if (
            record.get("prediction_id") != prediction_id
            or record.get("model_id") != MODEL_ID
            or record.get("model_version") != MODEL_VERSION
            or record.get("series_id") != artifact.get("series_id")
            or record.get("phase_id") != INDEPENDENT_VALIDATION_PHASE
            or record.get("radius") != RADIUS
            or record.get("executor_parameters") != expected_parameters
            or record.get("geometry_signature") != expected_signature
            or record.get("drawing_plan_sha256") != expected_signature
            or record.get("planned_strokes") != expected_strokes
            or record.get("stroke_predictions") != expected_stroke_predictions
            or record.get("prediction_rule") != expected_rule
            or record.get("predicted_chalk") != EXPECTED_TOTALS[scenario_id][profile_id]
            or not isinstance(record.get("created_at_utc"), str)
        ):
            return False, "prediction_record_content_mismatch"
    return True, "valid"



def analyze_int006_validation(
    journal_path: str | Path,
    results_dir: str | Path,
) -> dict[str, Any]:
    """Validate accepted manifests against the journal's frozen artifact and calculate errors."""
    journal_path = Path(journal_path)
    results_dir = Path(results_dir)
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"status": "invalid", "reason": f"journal_unreadable:{exc}", "accepted_count": 0}
    if journal.get("phase_id") != INDEPENDENT_VALIDATION_PHASE:
        return {"status": "invalid", "reason": "journal_phase_mismatch", "accepted_count": 0}
    artifact = journal.get("prediction_artifact")
    artifact_ok, artifact_reason = validate_int006_prediction_artifact(
        artifact, expected_series_id=journal.get("series_id")
    )
    if not artifact_ok:
        return {"status": "invalid", "reason": artifact_reason, "accepted_count": 0}
    tasks = journal.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 45:
        return {"status": "invalid", "reason": "journal_task_count_mismatch", "accepted_count": 0}
    task_index = {task.get("task_id"): task for task in tasks if isinstance(task, dict)}
    if len(task_index) != 45:
        return {"status": "invalid", "reason": "journal_task_identity_mismatch", "accepted_count": 0}

    expected_cells = set()
    for scenario_id in DRAWING_PLANS:
        for profile_name, profile in PROFILES.items():
            for repeat in (1, 2, 3):
                expected_cells.add((scenario_id, profile_name, repeat))
    seen_cells: set[tuple[str, str, int]] = set()
    seen_runs: set[str] = set()
    accepted = []
    rejected = []
    for manifest_path in sorted(results_dir.rglob("experiment.json")):
        try:
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        block = document.get("chalk_test_block") if isinstance(document, dict) else None
        if not isinstance(block, dict) or block.get("block_id") != journal.get("block_id"):
            continue
        task = task_index.get(block.get("task_id"))
        if task is None:
            rejected.append({"path": str(manifest_path), "reason": "unknown_block_task"})
            continue
        matrix = document.get("chalk_experiment_matrix")
        if not isinstance(matrix, dict):
            rejected.append({"path": str(manifest_path), "reason": "matrix_metadata_missing"})
            continue
        try:
            profile_name = _profile_name(matrix.get("executor_parameters", {}))
            repeat = matrix.get("repeat_index")
            cell = (matrix.get("scenario_id"), profile_name, repeat)
        except (TypeError, ValueError):
            rejected.append({"path": str(manifest_path), "reason": "profile_invalid"})
            continue
        if cell not in expected_cells:
            rejected.append({"path": str(manifest_path), "reason": "unexpected_matrix_cell"})
            continue
        if cell in seen_cells:
            rejected.append({"path": str(manifest_path), "reason": "duplicate_matrix_cell"})
            continue
        if task.get("scenario_id") != cell[0] or task.get("repeat_index") != cell[2]:
            rejected.append({"path": str(manifest_path), "reason": "journal_task_mismatch"})
            continue
        prediction_id = f"{MODEL_ID}:{cell[0]}:{cell[1]}"
        prediction = artifact["predictions"].get(prediction_id)
        if not isinstance(prediction, dict):
            rejected.append({"path": str(manifest_path), "reason": "frozen_prediction_missing"})
            continue
        if matrix.get("prediction_id") != prediction_id:
            rejected.append({"path": str(manifest_path), "reason": "prediction_id_mismatch"})
            continue
        if matrix.get("geometry_signature") != prediction["geometry_signature"]:
            rejected.append({"path": str(manifest_path), "reason": "geometry_signature_mismatch"})
            continue
        if matrix.get("requested_radius") != RADIUS or matrix.get("planned_strokes") != prediction["planned_strokes"]:
            rejected.append({"path": str(manifest_path), "reason": "radius_or_geometry_mismatch"})
            continue
        if matrix.get("executor_parameters") != prediction["executor_parameters"]:
            rejected.append({"path": str(manifest_path), "reason": "executor_profile_mismatch"})
            continue
        valid, reason, record = _validate_manifest(document)
        if not valid or not isinstance(record, dict):
            rejected.append({"path": str(manifest_path), "reason": f"capture_invalid:{reason}"})
            continue
        stroke_level = _stroke_level_breakdown(
            manifest_path.parent,
            expected_strokes=record["expected_strokes"],
            expected_chalk=record["consumed_points"],
        )
        if stroke_level.get("status") != "complete":
            rejected.append({"path": str(manifest_path), "reason": "stroke_level_incomplete:" + str(stroke_level.get("reason"))})
            continue
        run_id = record.get("run_id")
        if not isinstance(run_id, str) or run_id in seen_runs:
            rejected.append({"path": str(manifest_path), "reason": "duplicate_or_missing_run_id"})
            continue
        seen_cells.add(cell)
        seen_runs.add(run_id)
        actual = record["consumed_points"]
        predicted = prediction["predicted_chalk"]
        residual = actual - predicted
        accepted.append({
            "path": str(manifest_path),
            "scenario_id": cell[0],
            "profile_id": cell[1],
            "repeat_index": cell[2],
            "prediction_id": prediction_id,
            "run_id": run_id,
            "actual_chalk": actual,
            "predicted_chalk": predicted,
            "residual": residual,
            "absolute_error": abs(residual),
            "relative_error": abs(residual) / actual if actual else None,
            "stroke_level": stroke_level,
        })

    missing = sorted(expected_cells - seen_cells)
    groups = {}
    for scenario_id in DRAWING_PLANS:
        for profile_name in PROFILES:
            rows = sorted(
                [row for row in accepted if row["scenario_id"] == scenario_id and row["profile_id"] == profile_name],
                key=lambda row: row["repeat_index"],
            )
            residuals = [row["residual"] for row in rows]
            actuals = [row["actual_chalk"] for row in rows]
            absolute = [abs(value) for value in residuals]
            groups[f"{scenario_id}:{profile_name}"] = {
                "scenario_id": scenario_id,
                "profile_id": profile_name,
                "count": len(rows),
                "complete_repeats": len(rows) == 3 and [row["repeat_index"] for row in rows] == [1, 2, 3],
                "mae": mean(absolute) if rows else None,
                "rmse": math.sqrt(mean(value * value for value in residuals)) if rows else None,
                "bias_actual_minus_predicted": mean(residuals) if rows else None,
                "mape": mean(row["relative_error"] for row in rows) * 100 if rows else None,
                "max_absolute_error": max(absolute) if rows else None,
                "max_underprediction": max([value for value in residuals if value > 0], default=0) if rows else None,
                "actual_mean": mean(actuals) if rows else None,
                "actual_repeat_pstdev": pstdev(actuals) if len(actuals) > 1 else (0.0 if rows else None),
                "runs": rows,
            }
    complete = len(accepted) == 45 and not missing and not rejected and all(
        group["complete_repeats"] for group in groups.values()
    )
    return {
        "schema_version": 1,
        "record_type": "autodraw_int006_validation_analysis",
        "status": "complete" if complete else "incomplete",
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "series_id": journal.get("series_id"),
        "block_id": journal.get("block_id"),
        "prediction_artifact_sha256": artifact["artifact_sha256"],
        "expected_capture_count": 45,
        "accepted_count": len(accepted),
        "missing_cells": [
            {"scenario_id": item[0], "profile_id": item[1], "repeat_index": item[2]}
            for item in missing
        ],
        "rejected": rejected,
        "groups": groups,
        "accepted": accepted,
        "safety_margin_status": "not_established",
        "production_eligibility": "not_validated",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze_int006_validation(args.journal, args.results_dir)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result.get("status") == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
