from __future__ import annotations

"""Pure validation and aggregation for controlled CHALK radius experiments."""

import json
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Iterable


RADIUS_LEVELS = (1, 5, 10, 15, 20, 25, 30)
MATRIX_BLOCKS = {
    1: (1, 5, 10, 15, 20, 25, 30),
    2: (30, 25, 20, 15, 10, 5, 1),
    3: (10, 20, 30, 1, 15, 25, 5),
}
MATRIX_SCENARIO_ID = "paint_consumption_long_lines"
EXPECTED_STROKES = 6


def build_chalk_radius_matrix_metadata(
    *, series_id: str, block: int, requested_radius: int
) -> dict[str, Any]:
    """Validate and normalize metadata for one independently measured matrix cell."""
    if not isinstance(series_id, str):
        raise ValueError("ID серии CHALK должен быть текстом.")
    normalized_id = series_id.strip()
    if not normalized_id or len(normalized_id) > 64:
        raise ValueError("ID серии CHALK должен содержать от 1 до 64 символов.")
    if any(not (char.isalnum() or char in "-_.") for char in normalized_id):
        raise ValueError("ID серии может содержать только буквы, цифры, дефис, точку и подчёркивание.")
    if isinstance(block, bool) or not isinstance(block, int) or block not in MATRIX_BLOCKS:
        raise ValueError("Блок матрицы должен быть целым числом 1, 2 или 3.")
    if isinstance(requested_radius, bool) or not isinstance(requested_radius, int):
        raise ValueError("Радиус матрицы должен быть целым числом.")
    if requested_radius not in RADIUS_LEVELS:
        raise ValueError(f"Для этой матрицы допустимы радиусы: {', '.join(map(str, RADIUS_LEVELS))}.")
    if requested_radius not in MATRIX_BLOCKS[block]:
        raise ValueError(f"Радиус {requested_radius} не входит в последовательность блока {block}.")
    return {
        "schema_version": 1,
        "series_id": normalized_id,
        "block": block,
        "repeat_index": block,
        "requested_radius": requested_radius,
        "planned_radii": list(RADIUS_LEVELS),
        "block_order": list(MATRIX_BLOCKS[block]),
        "scenario_id": MATRIX_SCENARIO_ID,
        "expected_strokes": EXPECTED_STROKES,
    }


def is_monitor_run_claimed(
    output_dir: str | Path,
    run_id: str | None,
    *,
    exclude_experiment_dir: str | Path | None = None,
) -> bool:
    """Return True when a Game Monitor run is already linked to another experiment."""
    if not isinstance(run_id, str) or not run_id.strip():
        return False
    excluded = Path(exclude_experiment_dir).resolve() if exclude_experiment_dir else None
    root = Path(output_dir)
    if not root.is_dir():
        return False
    for manifest_path in root.rglob("experiment.json"):
        if excluded is not None and manifest_path.parent.resolve() == excluded:
            continue
        try:
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(document, dict):
            continue
        capture = document.get("monitor_capture")
        summary = document.get("game_monitor_summary")
        capture = capture if isinstance(capture, dict) else {}
        summary = summary if isinstance(summary, dict) else {}
        if capture.get("run_id") == run_id or summary.get("run_id") == run_id:
            return True
    return False


def _manifest_measurement(document: dict[str, Any]) -> tuple[bool, str, dict[str, Any] | None]:
    matrix = document.get("chalk_radius_matrix")
    if not isinstance(matrix, dict):
        return False, "matrix_metadata_missing", None
    try:
        metadata = build_chalk_radius_matrix_metadata(
            series_id=matrix.get("series_id"),
            block=matrix.get("block"),
            requested_radius=matrix.get("requested_radius"),
        )
    except (TypeError, ValueError) as exc:
        return False, f"invalid_matrix_metadata:{exc}", None
    if matrix.get("scenario_id") != MATRIX_SCENARIO_ID:
        return False, "wrong_test_scenario", None

    capture = document.get("monitor_capture")
    capture = capture if isinstance(capture, dict) else {}
    if capture.get("status") != "saved":
        return False, f"monitor_capture_{capture.get('status', 'missing')}", None
    if capture.get("stroke_count") != EXPECTED_STROKES or capture.get("expected_stroke_count") != EXPECTED_STROKES:
        return False, "stroke_count_mismatch", None

    summary = document.get("game_monitor_summary")
    summary = summary if isinstance(summary, dict) else {}
    if summary.get("brush_radius_status") != "single":
        return False, "brush_radius_not_single", None
    if summary.get("observed_brush_radii") != [metadata["requested_radius"]]:
        return False, "observed_radius_mismatch", None
    if summary.get("point_delta_matches_chalk") is not True:
        return False, "sampled_delta_mismatch", None
    if summary.get("stroke_count") != EXPECTED_STROKES:
        return False, "monitor_stroke_count_mismatch", None

    chalk = summary.get("chalk")
    chalk = chalk if isinstance(chalk, dict) else {}
    try:
        pre = int(chalk["pre_point_count"])
        post = int(chalk["post_point_count"])
        consumed = int(chalk["consumed_points"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return False, "chalk_counter_missing", None
    if chalk.get("status") != "exact" or post < pre or post - pre != consumed or consumed <= 0:
        return False, "chalk_counter_inexact", None

    run_id = capture.get("run_id") or summary.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        return False, "monitor_run_id_missing", None
    if capture.get("run_id") and summary.get("run_id") and capture.get("run_id") != summary.get("run_id"):
        return False, "monitor_run_id_mismatch", None

    execution = document.get("execution_report")
    execution = execution if isinstance(execution, dict) else {}
    if execution.get("status") != "completed":
        return False, "executor_not_completed", None
    if int(execution.get("completed_strokes", EXPECTED_STROKES) or 0) != EXPECTED_STROKES:
        return False, "executor_stroke_count_mismatch", None

    return True, "valid", {
        "experiment_id": document.get("experiment_id"),
        "series_id": metadata["series_id"],
        "block": metadata["block"],
        "radius": metadata["requested_radius"],
        "consumed_points": consumed,
        "pre_point_count": pre,
        "post_point_count": post,
        "run_id": run_id,
    }


def summarize_chalk_radius_matrix(documents: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Validate manifests, reject duplicate runs/cells, and calculate per-radius statistics."""
    evaluated: list[tuple[dict[str, Any], bool, str, dict[str, Any] | None]] = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        valid, reason, record = _manifest_measurement(document)
        evaluated.append((document, valid, reason, record))

    run_counts: dict[str, int] = {}
    cell_counts: dict[tuple[str, int, int], int] = {}
    for _, valid, _, record in evaluated:
        if not valid or record is None:
            continue
        run_counts[record["run_id"]] = run_counts.get(record["run_id"], 0) + 1
        key = (record["series_id"], record["block"], record["radius"])
        cell_counts[key] = cell_counts.get(key, 0) + 1

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for document, valid, reason, record in evaluated:
        if valid and record is not None:
            if run_counts[record["run_id"]] > 1:
                valid, reason = False, "duplicate_monitor_run"
            elif cell_counts[(record["series_id"], record["block"], record["radius"])] > 1:
                valid, reason = False, "duplicate_matrix_cell"
        if valid and record is not None:
            accepted.append(record)
        else:
            rejected.append({
                "experiment_id": document.get("experiment_id"),
                "reason": reason,
                "experiment_dir": document.get("experiment_dir"),
            })

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for record in accepted:
        grouped.setdefault((record["series_id"], record["radius"]), []).append(record)

    series_ids = sorted({record["series_id"] for record in accepted} | {
        doc.get("chalk_radius_matrix", {}).get("series_id")
        for doc, _, _, _ in evaluated
        if isinstance(doc.get("chalk_radius_matrix"), dict)
        and isinstance(doc["chalk_radius_matrix"].get("series_id"), str)
    })
    series_results = []
    for series_id in series_ids:
        radius_results = []
        for radius in RADIUS_LEVELS:
            rows = sorted(grouped.get((series_id, radius), []), key=lambda item: item["block"])
            values = [row["consumed_points"] for row in rows]
            radius_results.append({
                "radius": radius,
                "measurements": rows,
                "valid_repeat_count": len(rows),
                "missing_blocks": sorted(set(MATRIX_BLOCKS) - {row["block"] for row in rows}),
                "complete": len(rows) == 3 and {row["block"] for row in rows} == {1, 2, 3},
                "mean": mean(values) if values else None,
                "median": median(values) if values else None,
                "minimum": min(values) if values else None,
                "maximum": max(values) if values else None,
                "range": max(values) - min(values) if values else None,
                "population_stddev": pstdev(values) if len(values) > 1 else (0.0 if values else None),
            })
        series_results.append({"series_id": series_id, "radii": radius_results})

    return {
        "schema_version": 1,
        "valid_measurement_count": len(accepted),
        "rejected_measurement_count": len(rejected),
        "series": series_results,
        "rejected": rejected,
    }
