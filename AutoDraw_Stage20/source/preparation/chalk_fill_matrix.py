from __future__ import annotations

"""Isolated FILL-001 45-cell matrix and exact-CHALK capture analyzer."""

import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

from chalk_fill_experiment import FILL001_RADII, FILL001_SHAPES
from chalk_fill_fixed_radius_planner import (
    FILL001_MAX_LEAKAGE_PIXELS,
    FILL001_MIN_COVERAGE,
    build_fixed_radius_fill_plan,
)

FILL001_PHASE_ID = "FILL001"
FILL001_SCHEMA_VERSION = 2
FILL001_REPEATS = (1, 2, 3)
FILL001_TASK_COUNT = len(FILL001_SHAPES) * len(FILL001_RADII) * len(FILL001_REPEATS)
FILL001_RS_PLAN_VARIANT = "FILL001_RS_V1"
FILL001_RS_SELECTION_POLICY = (
    "max_scanline_row_step_with_coverage_ge_0.99_and_leakage_eq_0;"
    "tie_break_max_coverage_then_min_estimated_points_path_strokes"
)
FILL001_RS_SCANLINE_CONFIGS = {
    ("rectangle", 1): (1, 0),
    ("rectangle", 5): (2, 1),
    ("rectangle", 10): (5, 0),
    ("rectangle", 20): (8, 4),
    ("rectangle", 30): (11, 10),
    ("wide_irregular", 1): (1, 0),
    ("wide_irregular", 5): (4, 0),
    ("wide_irregular", 10): (7, 1),
    ("wide_irregular", 20): (5, 0),
    ("wide_irregular", 30): (10, 0),
    ("narrow_irregular", 1): (1, 0),
    ("narrow_irregular", 5): (3, 1),
    ("narrow_irregular", 10): (5, 0),
    ("narrow_irregular", 20): (5, 0),
    ("narrow_irregular", 30): (5, 0),
}
CAPTURE_FIELDS = (
    "task_id", "run_id", "plan_signature", "target_mask_sha256",
    "requested_radius", "observed_radius", "pre_point_count", "post_point_count",
    "exact_chalk", "coverage_fraction", "leakage_pixels", "completed_strokes",
    "expected_strokes", "dropped_events", "monitor_errors", "bridge_failures",
    "sequence_gaps", "stroke_chalk_deltas", "before_png", "after_png", "before_png_sha256",
    "after_png_sha256", "png_audit_status", "sampling_profile", "monitor_version", "event_count",
)


class FillMatrixError(ValueError):
    """FILL-001 matrix or capture violates its frozen contract."""


def _hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_fill001_matrix(series_id: str) -> dict[str, Any]:
    """Create 45 unique shape/radius/repeat tasks with frozen plan identities."""
    if not isinstance(series_id, str) or not 1 <= len(series_id.strip()) <= 64:
        raise FillMatrixError("series_id должен содержать от 1 до 64 символов.")
    series_id = series_id.strip()
    tasks = []
    order = 0
    for shape in FILL001_SHAPES:
        for radius in FILL001_RADII:
            plan = build_fixed_radius_fill_plan(shape, radius)
            summary = plan["summary"]
            for repeat in FILL001_REPEATS:
                order += 1
                tasks.append({
                    "task_id": f"{series_id}-{shape}-r{radius}-rep{repeat}",
                    "matrix_order_index": order,
                    "phase_id": FILL001_PHASE_ID,
                    "series_id": series_id,
                    "shape_id": shape,
                    "requested_radius": radius,
                    "repeat_index": repeat,
                    "planned_repeats": 3,
                    "plan_signature": plan["plan_signature"],
                    "target_mask_sha256": plan["target_mask_sha256"],
                    "expected_strokes": summary["stroke_count"],
                    "target_area_pixels": summary["target_area_pixels"],
                    "planned_path_length": summary["path_length_logical_pixels"],
                    "planned_coverage_fraction": summary["coverage_fraction"],
                    "planned_leakage_pixels": summary["leakage_pixels"],
                    "quality_gate_passed": summary["quality_gate_passed"],
                    "unsupported": summary["unsupported"],
                    "sampling_profile": {"profile_id": "P1", "sampling_step": 4, "delay_ms": 5},
                    "safe_to_execute": False,
                    "capture_status": "pending",
                })
    identity = {
        "schema_version": FILL001_SCHEMA_VERSION,
        "phase_id": FILL001_PHASE_ID,
        "series_id": series_id,
        "shapes": list(FILL001_SHAPES),
        "radii": list(FILL001_RADII),
        "repeats": list(FILL001_REPEATS),
        "tasks": tasks,
    }
    return {
        **identity,
        "matrix_signature": _hash(identity),
        "expected_task_count": FILL001_TASK_COUNT,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_allowed": False,
        "status": "planned",
    }


def build_fill001_rs_matrix(series_id: str) -> dict[str, Any]:
    """Create a separate 45-task FILL-001-RS matrix with frozen scanline spacing."""
    if not isinstance(series_id, str) or not 1 <= len(series_id.strip()) <= 64:
        raise FillMatrixError("series_id должен содержать от 1 до 64 символов.")
    series_id = series_id.strip()
    tasks = []
    order = 0
    for shape in FILL001_SHAPES:
        for radius in FILL001_RADII:
            scanline_row_step, scanline_offset = FILL001_RS_SCANLINE_CONFIGS[(shape, radius)]
            plan = build_fixed_radius_fill_plan(
                shape,
                radius,
                scanline_row_step=scanline_row_step,
                scanline_offset=scanline_offset,
            )
            summary = plan["summary"]
            if summary["quality_gate_passed"] is not True or summary["leakage_pixels"] != 0:
                raise FillMatrixError(
                    f"FILL-001-RS candidate не прошёл quality gate: {shape}/r{radius}."
                )
            for repeat in FILL001_REPEATS:
                order += 1
                tasks.append({
                    "task_id": (
                        f"{series_id}-{shape}-r{radius}-s{scanline_row_step}"
                        f"-o{scanline_offset}-rep{repeat}"
                    ),
                    "matrix_order_index": order,
                    "phase_id": FILL001_PHASE_ID,
                    "series_id": series_id,
                    "shape_id": shape,
                    "requested_radius": radius,
                    "repeat_index": repeat,
                    "planned_repeats": 3,
                    "plan_variant": FILL001_RS_PLAN_VARIANT,
                    "planner_version": plan["planner_version"],
                    "scanline_row_step": scanline_row_step,
                    "scanline_offset": scanline_offset,
                    "plan_signature": plan["plan_signature"],
                    "target_mask_sha256": plan["target_mask_sha256"],
                    "expected_strokes": summary["stroke_count"],
                    "target_area_pixels": summary["target_area_pixels"],
                    "planned_path_length": summary["path_length_logical_pixels"],
                    "planned_coverage_fraction": summary["coverage_fraction"],
                    "planned_leakage_pixels": summary["leakage_pixels"],
                    "quality_gate_passed": summary["quality_gate_passed"],
                    "unsupported": summary["unsupported"],
                    "sampling_profile": {"profile_id": "P1", "sampling_step": 4, "delay_ms": 5},
                    "safe_to_execute": False,
                    "capture_status": "pending",
                })
    identity = {
        "schema_version": FILL001_SCHEMA_VERSION,
        "phase_id": FILL001_PHASE_ID,
        "series_id": series_id,
        "shapes": list(FILL001_SHAPES),
        "radii": list(FILL001_RADII),
        "repeats": list(FILL001_REPEATS),
        "tasks": tasks,
        "plan_variant": FILL001_RS_PLAN_VARIANT,
        "candidate_selection_policy": FILL001_RS_SELECTION_POLICY,
    }
    matrix = {
        **identity,
        "matrix_signature": _hash(identity),
        "expected_task_count": FILL001_TASK_COUNT,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_allowed": False,
        "status": "planned",
    }
    validate_fill001_matrix(matrix)
    return matrix


def validate_fill001_matrix(matrix: Any) -> None:
    """Fail closed on duplicate/missing cells, altered signatures or unsafe plans."""
    if not isinstance(matrix, dict) or matrix.get("phase_id") != FILL001_PHASE_ID:
        raise FillMatrixError("Некорректный FILL-001 manifest.")
    # Versioned, two-run A/B pilot. Legacy 45-cell manifests are unchanged.
    if matrix.get("experiment_protocol") == "FILL001_SMOOTH_AB_V1":
        from fill001_smooth_ab import validate_smooth_ab_matrix
        validate_smooth_ab_matrix(matrix)
        return
    if matrix.get("experiment_protocol") == "FILL001_SMOOTH_AB_V2":
        from fill001_smooth_ab_v2 import validate_smooth_ab_v2_matrix
        validate_smooth_ab_v2_matrix(matrix)
        return
    if "experiment_protocol" in matrix:
        raise FillMatrixError("Unsupported FILL-001 experimental protocol.")
    plan_variant = matrix.get("plan_variant")
    if plan_variant not in (None, FILL001_RS_PLAN_VARIANT):
        raise FillMatrixError("Неизвестная версия FILL-001 plan_variant.")
    if plan_variant == FILL001_RS_PLAN_VARIANT and matrix.get("candidate_selection_policy") != FILL001_RS_SELECTION_POLICY:
        raise FillMatrixError("FILL-001-RS candidate selection policy не совпадает с frozen contract.")
    tasks = matrix.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != FILL001_TASK_COUNT:
        raise FillMatrixError(f"Матрица должна содержать {FILL001_TASK_COUNT} задач.")
    if matrix.get("expected_task_count") != FILL001_TASK_COUNT:
        raise FillMatrixError("expected_task_count не совпадает с размером матрицы.")
    ids = [t.get("task_id") for t in tasks if isinstance(t, dict)]
    if len(ids) != FILL001_TASK_COUNT or len(set(ids)) != FILL001_TASK_COUNT:
        raise FillMatrixError("Отсутствуют или повторяются task_id.")
    expected = {(s, r, n) for s in FILL001_SHAPES for r in FILL001_RADII for n in FILL001_REPEATS}
    actual = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise FillMatrixError("Некорректная задача.")
        cell = (task.get("shape_id"), task.get("requested_radius"), task.get("repeat_index"))
        if cell in actual:
            raise FillMatrixError(f"Повтор ячейки {cell}.")
        actual.add(cell)
        if task.get("phase_id") != FILL001_PHASE_ID or task.get("safe_to_execute") is not False:
            raise FillMatrixError("Неверная фаза или unsafe execution flag.")
        if task.get("sampling_profile") != {"profile_id": "P1", "sampling_step": 4, "delay_ms": 5}:
            raise FillMatrixError("Matrix task не закрепляет frozen sampling P1.")
        if task.get("capture_status") not in {"pending", "running", "completed", "failed", "unsupported"}:
            raise FillMatrixError("Неизвестный capture_status.")
        if task.get("quality_gate_passed") is not True or task.get("unsupported") is not False:
            raise FillMatrixError("Unsupported planner cell запрещён в live matrix.")
        if task.get("planned_leakage_pixels") != FILL001_MAX_LEAKAGE_PIXELS:
            raise FillMatrixError("Planner cell не прошёл leakage gate.")
        coverage = task.get("planned_coverage_fraction")
        if isinstance(coverage, bool) or not isinstance(coverage, (int, float)) or coverage < FILL001_MIN_COVERAGE:
            raise FillMatrixError("Planner cell не прошёл coverage gate.")
        for field in ("plan_signature", "target_mask_sha256"):
            if not isinstance(task.get(field), str) or len(task[field]) != 64:
                raise FillMatrixError(f"Некорректный {field}.")
        count = task.get("expected_strokes")
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise FillMatrixError("expected_strokes должен быть положительным целым.")
        if plan_variant == FILL001_RS_PLAN_VARIANT:
            if task.get("plan_variant") != FILL001_RS_PLAN_VARIANT:
                raise FillMatrixError("FILL-001-RS task не закрепляет plan variant.")
            radius = task.get("requested_radius")
            step, offset = task.get("scanline_row_step"), task.get("scanline_offset")
            if type(radius) is not int or radius not in FILL001_RADII:
                raise FillMatrixError("Некорректный radius в FILL-001-RS task.")
            if (
                type(step) is not int or not 1 <= step <= radius
                or type(offset) is not int or not 0 <= offset < step
            ):
                raise FillMatrixError("Некорректные scanline spacing parameters в FILL-001-RS task.")
            expected_planner_version = 1 if step == 1 and offset == 0 else 2
            if task.get("planner_version") != expected_planner_version:
                raise FillMatrixError("FILL-001-RS task не закрепляет ожидаемую planner version.")
            if (task.get("shape_id"), task.get("requested_radius")) not in FILL001_RS_SCANLINE_CONFIGS:
                raise FillMatrixError("Неизвестная shape/radius ячейка FILL-001-RS.")
            if FILL001_RS_SCANLINE_CONFIGS[(task["shape_id"], task["requested_radius"])] != (step, offset):
                raise FillMatrixError("Scanline spacing не совпадает с frozen FILL-001-RS candidate.")
            plan = build_fixed_radius_fill_plan(
                task["shape_id"], task["requested_radius"],
                scanline_row_step=step, scanline_offset=offset,
            )
            plan_summary = plan["summary"]
            if (
                plan["plan_signature"] != task["plan_signature"]
                or plan["target_mask_sha256"] != task["target_mask_sha256"]
                or plan_summary["stroke_count"] != count
                or plan_summary["coverage_fraction"] != task["planned_coverage_fraction"]
                or plan_summary["leakage_pixels"] != task["planned_leakage_pixels"]
            ):
                raise FillMatrixError("FILL-001-RS task не совпадает с пересчитанным versioned plan.")
        elif any(field in task for field in ("plan_variant", "planner_version", "scanline_row_step", "scanline_offset")):
            raise FillMatrixError("FILL-001 legacy matrix не может содержать FILL-001-RS fields.")
    if actual != expected:
        raise FillMatrixError("Матрица не покрывает все shape/radius/repeat cells.")
    identity_fields = ("schema_version", "phase_id", "series_id", "shapes", "radii", "repeats", "tasks")
    if plan_variant == FILL001_RS_PLAN_VARIANT:
        identity_fields += ("plan_variant", "candidate_selection_policy")
    identity = {k: matrix[k] for k in identity_fields}
    if matrix.get("matrix_signature") != _hash(identity):
        raise FillMatrixError("matrix_signature не совпадает с manifest.")


def write_fill001_matrix(matrix: dict[str, Any], path: str | Path) -> Path:
    """Atomically write a validated manifest."""
    validate_fill001_matrix(matrix)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def load_fill001_matrix(path: str | Path) -> dict[str, Any]:
    """Load a manifest and validate its frozen identity."""
    try:
        matrix = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FillMatrixError(f"Не удалось прочитать manifest: {exc}") from exc
    validate_fill001_matrix(matrix)
    return matrix


def validate_fill001_capture(task: dict[str, Any], capture: Any) -> dict[str, Any]:
    """Validate one Game Monitor capture against the immutable matrix task."""
    if not isinstance(capture, dict):
        raise FillMatrixError("Capture должен быть JSON object.")
    missing = [key for key in CAPTURE_FIELDS if key not in capture]
    if missing:
        raise FillMatrixError("Нет обязательных полей: " + ", ".join(missing))
    if capture["task_id"] != task["task_id"] or not isinstance(capture["run_id"], str) or not capture["run_id"].strip():
        raise FillMatrixError("task_id/run_id невалидны.")
    if capture["plan_signature"] != task["plan_signature"] or capture["target_mask_sha256"] != task["target_mask_sha256"]:
        raise FillMatrixError("Capture связан с другой геометрией.")
    if capture["requested_radius"] != task["requested_radius"] or capture["observed_radius"] != task["requested_radius"]:
        raise FillMatrixError("Requested/observed radius не совпадает с матрицей.")
    integer_fields = (
        "pre_point_count", "post_point_count", "exact_chalk", "leakage_pixels",
        "completed_strokes", "expected_strokes", "dropped_events", "monitor_errors",
        "bridge_failures", "sequence_gaps",
    )
    for field in integer_fields:
        value = capture[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise FillMatrixError(f"{field} должен быть неотрицательным целым.")
    if capture["post_point_count"] - capture["pre_point_count"] != capture["exact_chalk"] or capture["exact_chalk"] <= 0:
        raise FillMatrixError("Exact CHALK не совпадает с post-pre pointCount.")
    if capture["expected_strokes"] != task["expected_strokes"] or capture["completed_strokes"] != task["expected_strokes"]:
        raise FillMatrixError("Число завершённых штрихов не совпадает с dynamic expected_strokes.")
    deltas = capture["stroke_chalk_deltas"]
    if not isinstance(deltas, list) or len(deltas) != task["expected_strokes"]:
        raise FillMatrixError("Per-stroke CHALK deltas не совпадают с expected_strokes.")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in deltas):
        raise FillMatrixError("Per-stroke CHALK delta должен быть неотрицательным целым.")
    if sum(deltas) != capture["exact_chalk"]:
        raise FillMatrixError("Сумма per-stroke CHALK не совпадает с exact CHALK.")
    for field in ("before_png", "after_png"):
        if not isinstance(capture[field], str) or not capture[field].strip():
            raise FillMatrixError(f"{field} evidence path обязателен.")
    for field in ("before_png_sha256", "after_png_sha256"):
        value = capture[field]
        if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise FillMatrixError(f"{field} должен быть SHA-256.")
    expected_sampling = {"profile_id": "P1", "sampling_step": 4, "delay_ms": 5}
    if capture["sampling_profile"] != task.get("sampling_profile") or capture["sampling_profile"] != expected_sampling:
        raise FillMatrixError("Sampling profile не совпадает с frozen P1.")
    if not isinstance(capture["monitor_version"], str) or not capture["monitor_version"]:
        raise FillMatrixError("monitor_version обязателен.")
    if isinstance(capture["event_count"], bool) or not isinstance(capture["event_count"], int) or capture["event_count"] < 1:
        raise FillMatrixError("event_count должен быть положительным целым.")
    if capture["png_audit_status"] != "passed":
        raise FillMatrixError("PNG evidence не прошёл независимый audit.")
    if capture["leakage_pixels"] != 0:
        raise FillMatrixError("Live capture не прошёл leakage=0.")
    coverage = capture["coverage_fraction"]
    if isinstance(coverage, bool) or not isinstance(coverage, (int, float)) or not math.isfinite(coverage) or not 0.99 <= coverage <= 1.0:
        raise FillMatrixError("Live capture не прошёл coverage ≥99%.")
    for field in ("dropped_events", "monitor_errors", "bridge_failures", "sequence_gaps"):
        if capture[field] != 0:
            raise FillMatrixError(f"Недопустимое значение {field}.")
    return {
        "task_id": task["task_id"], "run_id": capture["run_id"],
        "shape_id": task["shape_id"], "radius": task["requested_radius"],
        "repeat_index": task["repeat_index"], "exact_chalk": capture["exact_chalk"],
        "coverage_fraction": float(coverage), "leakage_pixels": 0,
        "completed_strokes": capture["completed_strokes"],
        "plan_signature": capture["plan_signature"], "status": "accepted",
    }


def analyze_fill001_captures(matrix: dict[str, Any], captures: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate the 45-cell journal and summarize exact CHALK by shape/radius."""
    validate_fill001_matrix(matrix)
    if not isinstance(captures, list):
        raise FillMatrixError("captures должен быть списком.")
    by_id = {task["task_id"]: task for task in matrix["tasks"]}
    accepted, rejected, seen, seen_runs = [], [], set(), set()
    for capture in captures:
        task_id = capture.get("task_id") if isinstance(capture, dict) else None
        if task_id in seen:
            rejected.append({"task_id": task_id, "reason": "duplicate_capture"})
            continue
        seen.add(task_id)
        run_id = capture.get("run_id") if isinstance(capture, dict) else None
        if isinstance(run_id, str) and run_id in seen_runs:
            rejected.append({"task_id": task_id, "reason": "duplicate_run_id"})
            continue
        if isinstance(run_id, str):
            seen_runs.add(run_id)
        task = by_id.get(task_id)
        if task is None:
            rejected.append({"task_id": task_id, "reason": "unexpected_task_id"})
            continue
        try:
            accepted.append(validate_fill001_capture(task, capture))
        except FillMatrixError as exc:
            rejected.append({"task_id": task_id, "reason": str(exc)})
    missing = sorted(set(by_id) - {row["task_id"] for row in accepted})
    grouped = defaultdict(list)
    for row in accepted:
        grouped[(row["shape_id"], row["radius"])].append(row)
    summaries = []
    for shape in FILL001_SHAPES:
        area = next(t.get("target_area_pixels") for t in matrix["tasks"] if t["shape_id"] == shape) if matrix["tasks"] else None
        for radius in FILL001_RADII:
            rows = grouped[(shape, radius)]
            values = [r["exact_chalk"] for r in rows]
            summaries.append({
                "shape_id": shape, "radius": radius, "accepted_repeats": len(values),
                "exact_chalk_values": values,
                "mean_exact_chalk": mean(values) if values else None,
                "median_exact_chalk": median(values) if values else None,
                "min_exact_chalk": min(values) if values else None,
                "max_exact_chalk": max(values) if values else None,
                "population_sd": pstdev(values) if len(values) > 1 else (0.0 if values else None),
                "mean_coverage_fraction": mean(r["coverage_fraction"] for r in rows) if rows else None,
                "effective_area_per_chalk": None,
                "target_area_pixels": area,
            })
    complete = len(accepted) == len(matrix["tasks"]) and not missing and not rejected
    return {
        "schema_version": FILL001_SCHEMA_VERSION, "phase_id": FILL001_PHASE_ID,
        "series_id": matrix["series_id"], "matrix_signature": matrix["matrix_signature"],
        "status": "complete" if complete else "incomplete",
        "accepted_count": len(accepted), "expected_count": FILL001_TASK_COUNT,
        "missing_task_ids": missing, "rejected": rejected, "groups": summaries,
        "production_model_changed": False, "safety_margin_status": "not_established",
        "production_eligibility": "not_validated",
    }
