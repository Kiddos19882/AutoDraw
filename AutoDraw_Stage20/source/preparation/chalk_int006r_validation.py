from __future__ import annotations

"""Independent analysis for the INT006R radius × geometry cross-validation block."""

import argparse
import json
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

from PIL import Image

from chalk_experiment_matrix import (
    EXPECTED_STROKES,
    GEOMETRY_EXECUTOR_CONFIG,
    PHASE_SCENARIOS,
    RADIUS_GEOMETRY_VALIDATION_PHASE,
    RADIUS_GEOMETRY_VALIDATION_PROFILE,
    RADIUS_GEOMETRY_VALIDATION_RADII,
)
from chalk_test_blocks import load_chalk_test_block_journal, validate_chalk_block_experiment


def _stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None, "population_sd": None}
    return {
        "count": len(values),
        "mean": round(mean(values), 6),
        "median": round(median(values), 6),
        "min": min(values),
        "max": max(values),
        "population_sd": round(pstdev(values), 6),
    }


def _validate_board_png_evidence(
    manifest_path: Path,
    document: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    phases = document.get("phases")
    if not isinstance(phases, dict):
        return None, "phase_evidence_missing"
    evidence: dict[str, Any] = {}
    dimensions: set[tuple[int, int]] = set()
    for phase_name in ("before_draw", "after_draw"):
        phase = phases.get(phase_name)
        files = phase.get("files") if isinstance(phase, dict) else None
        filename = files.get("board_roi") if isinstance(files, dict) else None
        if not isinstance(filename, str) or not filename or Path(filename).name != filename:
            return None, f"{phase_name}_board_png_reference_invalid"
        png_path = manifest_path.parent / filename
        if not png_path.is_file() or png_path.suffix.lower() != ".png":
            return None, f"{phase_name}_board_png_missing"
        try:
            with Image.open(png_path) as image_file:
                size = tuple(int(value) for value in image_file.size)
                image_file.verify()
        except (OSError, ValueError, Image.DecompressionBombError):
            return None, f"{phase_name}_board_png_unreadable"
        if len(size) != 2 or min(size) <= 0:
            return None, f"{phase_name}_board_png_dimensions_invalid"
        dimensions.add(size)
        evidence[phase_name] = {
            "file": filename,
            "width": size[0],
            "height": size[1],
        }
    if len(dimensions) != 1:
        return None, "before_after_board_png_dimensions_mismatch"
    return evidence, None


def analyze_int006r_validation(
    journal_path: str | Path,
    results_dir: str | Path,
) -> dict[str, Any]:
    """Validate the complete 45-cell journal/capture set and report radius effects.

    This analyzer deliberately does not load or modify the frozen INT-006 prediction
    model: INT006R is a measured radius/geometry experiment, not a model-fit phase.
    """
    journal_path = Path(journal_path)
    results_dir = Path(results_dir)
    try:
        journal = load_chalk_test_block_journal(journal_path)
    except (OSError, ValueError) as exc:
        return {"status": "invalid", "reason": f"journal_invalid:{exc}", "accepted_count": 0}

    if journal.get("phase_id") != RADIUS_GEOMETRY_VALIDATION_PHASE:
        return {"status": "invalid", "reason": "journal_phase_mismatch", "accepted_count": 0}

    tasks = journal.get("tasks")
    expected_scenarios = PHASE_SCENARIOS[RADIUS_GEOMETRY_VALIDATION_PHASE]
    expected_cells = {
        (scenario_id, radius, repeat)
        for scenario_id in expected_scenarios
        for radius in RADIUS_GEOMETRY_VALIDATION_RADII
        for repeat in (1, 2, 3)
    }
    task_index = {
        task.get("task_id"): task for task in tasks
        if isinstance(task, dict) and isinstance(task.get("task_id"), str)
    }
    if len(tasks) != 45 or len(task_index) != 45:
        return {"status": "invalid", "reason": "journal_task_identity_mismatch", "accepted_count": 0}

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen_cells: set[tuple[str, int, int]] = set()
    seen_runs: set[str] = set()
    seen_experiments: set[str] = set()

    if not results_dir.exists():
        return {
            "status": "incomplete", "reason": "results_directory_missing",
            "expected_count": 45, "accepted_count": 0, "missing_count": 45,
            "missing_cells": [list(cell) for cell in sorted(expected_cells)],
            "rejected": [],
            "safety_margin_status": "not_established",
            "production_eligibility": "not_validated",
        }

    for manifest_path in sorted(results_dir.rglob("experiment.json")):
        try:
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        block_ref = document.get("chalk_test_block") if isinstance(document, dict) else None
        if not isinstance(block_ref, dict) or block_ref.get("block_id") != journal.get("block_id"):
            continue

        task_id = block_ref.get("task_id")
        task = task_index.get(task_id)
        if task is None:
            rejected.append({"path": str(manifest_path), "reason": "unknown_block_task"})
            continue
        if task.get("status") != "completed":
            rejected.append({"path": str(manifest_path), "reason": "journal_task_not_completed"})
            continue

        matrix = document.get("chalk_experiment_matrix")
        if not isinstance(matrix, dict):
            rejected.append({"path": str(manifest_path), "reason": "matrix_metadata_missing"})
            continue
        scenario_id = matrix.get("scenario_id")
        radius = matrix.get("requested_radius")
        repeat = matrix.get("repeat_index")
        cell = (scenario_id, radius, repeat)
        if cell not in expected_cells:
            rejected.append({"path": str(manifest_path), "reason": "unexpected_matrix_cell"})
            continue
        if cell in seen_cells:
            rejected.append({"path": str(manifest_path), "reason": "duplicate_matrix_cell"})
            continue

        experiment_id = document.get("experiment_id")
        if not isinstance(experiment_id, str) or not experiment_id:
            rejected.append({"path": str(manifest_path), "reason": "experiment_id_missing"})
            continue
        matching_attempts = [
            attempt for attempt in task.get("attempts", [])
            if isinstance(attempt, dict)
            and attempt.get("status") == "completed"
            and attempt.get("experiment_id") == experiment_id
        ]
        if len(matching_attempts) != 1:
            rejected.append({"path": str(manifest_path), "reason": "journal_attempt_binding_mismatch"})
            continue
        attempt = matching_attempts[0]
        attempt_dir = attempt.get("experiment_dir")
        if not isinstance(attempt_dir, str) or Path(attempt_dir).name != manifest_path.parent.name:
            rejected.append({"path": str(manifest_path), "reason": "journal_experiment_directory_mismatch"})
            continue

        valid, reason, record = validate_chalk_block_experiment(
            manifest_path,
            expected_task=task,
            expected_block=journal,
            expected_experiment_id=experiment_id,
            expected_experiment_dir=manifest_path.parent,
        )
        if not valid or record is None:
            rejected.append({"path": str(manifest_path), "reason": str(reason)})
            continue
        png_evidence, png_error = _validate_board_png_evidence(manifest_path, document)
        if png_error is not None or png_evidence is None:
            rejected.append({"path": str(manifest_path), "reason": str(png_error)})
            continue
        run_id = record.get("run_id")
        if run_id in seen_runs or experiment_id in seen_experiments:
            rejected.append({"path": str(manifest_path), "reason": "duplicate_run_or_experiment"})
            continue

        stroke_level = record.get("stroke_level", {})
        accepted.append({
            "task_id": task_id,
            "experiment_id": experiment_id,
            "run_id": run_id,
            "scenario_id": scenario_id,
            "radius": radius,
            "repeat_index": repeat,
            "actual_chalk": record["consumed_points"],
            "pre_point_count": record["pre_point_count"],
            "post_point_count": record["post_point_count"],
            "stroke_count": record["expected_strokes"],
            "stroke_level": stroke_level.get("strokes", []),
            "png_evidence": png_evidence,
            "visual_quality_status": "pending_manual_review",
        })
        seen_cells.add(cell)
        seen_runs.add(run_id)
        seen_experiments.add(experiment_id)

    missing_cells = sorted(expected_cells - seen_cells)
    groups: dict[str, Any] = {}
    for scenario_id in expected_scenarios:
        groups[scenario_id] = {}
        for radius in RADIUS_GEOMETRY_VALIDATION_RADII:
            rows = sorted(
                (row for row in accepted if row["scenario_id"] == scenario_id and row["radius"] == radius),
                key=lambda row: row["repeat_index"],
            )
            groups[scenario_id][str(radius)] = {
                "repeat_chalk": [row["actual_chalk"] for row in rows],
                **_stats([float(row["actual_chalk"]) for row in rows]),
                "per_stroke_chalk": [
                    stroke["consumed_points"]
                    for row in rows for stroke in row["stroke_level"]
                ],
            }

    radius_comparisons: dict[str, Any] = {}
    for scenario_id in expected_scenarios:
        baseline = groups[scenario_id]["10"]["mean"]
        radius_comparisons[scenario_id] = {}
        for radius in (1, 30):
            observed = groups[scenario_id][str(radius)]["mean"]
            delta = None if baseline is None or observed is None else round(observed - baseline, 6)
            relative = None if baseline in (None, 0) or delta is None else round(delta / baseline * 100.0, 6)
            radius_comparisons[scenario_id][str(radius)] = {
                "absolute_delta_vs_radius_10": delta,
                "relative_delta_percent_vs_radius_10": relative,
            }

    complete = (
        journal.get("status") == "completed"
        and len(accepted) == 45
        and not missing_cells
        and not rejected
        and len(seen_runs) == 45
        and len(seen_experiments) == 45
    )
    return {
        "schema_version": 1,
        "record_type": "autodraw_int006r_radius_geometry_analysis",
        "status": "complete" if complete else "incomplete",
        "reason": None if complete else "capture_set_or_journal_incomplete",
        "series_id": journal.get("series_id"),
        "block_id": journal.get("block_id"),
        "phase_id": RADIUS_GEOMETRY_VALIDATION_PHASE,
        "expected_count": 45,
        "accepted_count": len(accepted),
        "missing_count": len(missing_cells),
        "missing_cells": [list(cell) for cell in missing_cells],
        "rejected": rejected,
        "sampling_profile": {
            "name": "P1",
            "point_step_px": RADIUS_GEOMETRY_VALIDATION_PROFILE[0],
            "point_delay_ms": RADIUS_GEOMETRY_VALIDATION_PROFILE[1],
            "other_executor_parameters": GEOMETRY_EXECUTOR_CONFIG,
        },
        "radii": list(RADIUS_GEOMETRY_VALIDATION_RADII),
        "groups": groups,
        "radius_comparisons": radius_comparisons,
        "captures": accepted,
        "png_evidence_status": "complete" if len(accepted) == 45 else "incomplete",
        "visual_quality_gate": "pending_manual_review",
        "production_model_changed": False,
        "safety_margin_status": "not_established",
        "production_eligibility": "not_validated",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze INT006R radius × geometry CHALK captures.")
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = analyze_int006r_validation(args.journal, args.results_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report.get("status"),
        "accepted_count": report.get("accepted_count"),
        "missing_count": report.get("missing_count"),
        "rejected_count": len(report.get("rejected", [])),
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0 if report.get("status") == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
