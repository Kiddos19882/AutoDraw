from __future__ import annotations

"""Single-task, operator-approved FILL-001 execution handoff.

The 45-cell matrix remains non-executable as a batch. This module only prepares
one explicitly selected task for a controlled preflight; it does not start input.
"""

from copy import deepcopy
from typing import Any

from chalk_fill_experiment import FILL001_CANVAS_HEIGHT, FILL001_CANVAS_WIDTH
from chalk_fill_fixed_radius_planner import build_fixed_radius_fill_plan
from chalk_fill_matrix import FillMatrixError, validate_fill001_matrix


FILL001_EXECUTOR_OVERRIDE = {
    "point_step_px": 4.0,
    "point_delay_ms": 5,
    "line_extension_px": 0.0,
}


def prepare_fill001_single_task_plan(
    matrix: Any,
    task_id: str,
    *,
    operator_approved_single_task_preflight: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a logical-board DrawingPlan for exactly one approved FILL-001 task.

    The matrix-level execution flags intentionally remain false. A separate,
    explicit operator approval is required for this one-task preflight. This
    function never authorizes or schedules the remaining matrix cells.
    """
    validate_fill001_matrix(matrix)
    if operator_approved_single_task_preflight is not True:
        raise FillMatrixError(
            "FILL-001 требует явного подтверждения оператора для одиночного preflight."
        )
    if not isinstance(task_id, str) or not task_id.strip():
        raise FillMatrixError("Не задан task_id выбранной задачи FILL-001.")
    if matrix.get("execution_allowed") is not False:
        raise FillMatrixError("Matrix-level execution flag должен оставаться false.")
    if matrix.get("status") not in {"planned", "in_progress"}:
        raise FillMatrixError("Серия FILL-001 не находится в состоянии planned/in_progress.")

    matches = [task for task in matrix["tasks"] if task.get("task_id") == task_id]
    if len(matches) != 1:
        raise FillMatrixError("Выбранная задача отсутствует или неоднозначна в manifest.")
    task = deepcopy(matches[0])
    if task.get("capture_status") != "pending":
        raise FillMatrixError("Разрешается подготовить только pending task; повторный запуск запрещён.")
    if task.get("safe_to_execute") is not False:
        raise FillMatrixError("Task-level safe_to_execute должен оставаться false.")
    if task.get("quality_gate_passed") is not True or task.get("unsupported") is not False:
        raise FillMatrixError("Planner quality gate не пройден; исполнение запрещено.")
    if task.get("planned_coverage_fraction", 0) < 0.99 or task.get("planned_leakage_pixels") != 0:
        raise FillMatrixError("Требуются coverage >=99% и leakage=0.")

    plan = build_fixed_radius_fill_plan(task["shape_id"], task["requested_radius"])
    if (
        plan.get("plan_signature") != task.get("plan_signature")
        or plan.get("target_mask_sha256") != task.get("target_mask_sha256")
        or plan.get("summary", {}).get("stroke_count") != task.get("expected_strokes")
        or plan.get("summary", {}).get("quality_gate_passed") is not True
        or plan.get("summary", {}).get("leakage_pixels") != 0
        or plan.get("summary", {}).get("coverage_fraction", 0) < 0.99
    ):
        raise FillMatrixError("Пересчитанный planner result не совпадает с frozen manifest task.")

    strokes = []
    for index, item in enumerate(plan["strokes"], start=1):
        points = item.get("points")
        if not isinstance(points, list) or len(points) != 2:
            raise FillMatrixError(f"Planner stroke {index} имеет некорректную геометрию.")
        strokes.append({
            "name": f"fill001_{task['task_id']}_{index:04d}",
            "closed": False,
            "points": [{"x": float(point["x"]), "y": float(point["y"])} for point in points],
            "metadata": {
                "role": "fill001_fixed_radius_scanline",
                "task_id": task["task_id"],
                "brush_value": str(task["requested_radius"]),
                "plan_signature": task["plan_signature"],
            },
        })

    document = {
        "schema_version": 1,
        "name": f"FILL-001 {task['task_id']}",
        "created_at": matrix.get("created_at_utc"),
        "coordinate_system": "logical_board_pixels",
        "canvas": {"width": FILL001_CANVAS_WIDTH, "height": FILL001_CANVAS_HEIGHT},
        "width": FILL001_CANVAS_WIDTH,
        "height": FILL001_CANVAS_HEIGHT,
        "strokes": strokes,
        "generation": {
            "method": "fill001_fixed_radius_single_task_preflight",
            "planner_version": plan["planner_version"],
            "plan_signature": plan["plan_signature"],
            "target_mask_sha256": plan["target_mask_sha256"],
            "chalk_fill001_task": task,
            "sampling_profile": {
                "profile_id": "P1",
                "sampling_step": 4,
                "delay_ms": 5,
            },
            "execution_scope": "single_task_preflight",
            "operator_approved": True,
            "matrix_batch_execution_allowed": False,
        },
        "summary": {
            "stroke_count": len(strokes),
            "coverage_fraction": plan["summary"]["coverage_fraction"],
            "leakage_pixels": plan["summary"]["leakage_pixels"],
            "path_length_logical_pixels": plan["summary"]["path_length_logical_pixels"],
            "estimated_sampling_points": plan["summary"]["estimated_sampling_points"],
            "estimated_sampling_points_are_exact_chalk": False,
        },
    }
    return document, task
