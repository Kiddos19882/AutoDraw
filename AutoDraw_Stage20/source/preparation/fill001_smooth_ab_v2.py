from __future__ import annotations

"""FILL001_SMOOTH_AB_V2: fresh ON/OFF with run-bound Screen Mask V2.

The logical target is intentionally still frozen: Screen Mask V2 changes
measurement projection, not the shape/planner. No old V1 evidence is imported.
"""

from copy import deepcopy
from typing import Any

from chalk_fill_matrix import FillMatrixError, _hash
from fill001_smooth_ab import (
    PROTOCOL as LEGACY, IDENTITY_FIELDS, build_fill001_smooth_ab_matrix,
    validate_smooth_ab_matrix,
)

PROTOCOL = "FILL001_SMOOTH_AB_V2"
SCREEN_MASK = "FILL001_SCREEN_MASK_V2"
V2_IDENTITY_FIELDS = (*IDENTITY_FIELDS, "screen_mask_version")


def _v2_task_id(series: str, smooth: bool) -> str:
    return f"{series}-rectangle-r10-s5-o0-v2-smooth-{'on' if smooth else 'off'}"


def build_fill001_smooth_ab_v2_matrix(series_id: str) -> dict[str, Any]:
    old = build_fill001_smooth_ab_matrix(series_id)
    matrix = deepcopy(old)
    matrix["experiment_protocol"] = PROTOCOL
    matrix["screen_mask_version"] = SCREEN_MASK
    for task in matrix["tasks"]:
        task["task_id"] = _v2_task_id(series_id, task["expected_smooth"])
        task["experiment_protocol"] = PROTOCOL
        task["screen_mask_version"] = SCREEN_MASK
    matrix["matrix_signature"] = _hash({
        key: matrix[key] for key in V2_IDENTITY_FIELDS
    })
    validate_smooth_ab_v2_matrix(matrix)
    return matrix


def validate_smooth_ab_v2_matrix(matrix: Any) -> None:
    if (not isinstance(matrix, dict) or matrix.get("experiment_protocol") != PROTOCOL
            or matrix.get("screen_mask_version") != SCREEN_MASK
            or set(V2_IDENTITY_FIELDS) - set(matrix)
            or matrix.get("matrix_signature") != _hash({
                key: matrix[key] for key in V2_IDENTITY_FIELDS
            })):
        raise FillMatrixError("FILL-001 V2 protocol/mask/signature mismatch.")
    tasks = matrix.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 2:
        raise FillMatrixError("FILL-001 V2 needs exactly two tasks.")
    old = deepcopy(matrix)
    old.pop("screen_mask_version")
    old["experiment_protocol"] = LEGACY
    for task in old["tasks"]:
        if (not isinstance(task, dict)
                or task.get("screen_mask_version") != SCREEN_MASK
                or task.get("experiment_protocol") != PROTOCOL
                or type(task.get("expected_smooth")) is not bool
                or task.get("task_id") != _v2_task_id(
                    matrix["series_id"], task["expected_smooth"]
                )):
            raise FillMatrixError("FILL-001 V2 task identity or mode mismatch.")
        task.pop("screen_mask_version")
        task["experiment_protocol"] = LEGACY
        task["task_id"] = (
            f"{matrix['series_id']}-rectangle-r10-s5-o0-smooth-"
            f"{'on' if task['expected_smooth'] else 'off'}"
        )
    old["matrix_signature"] = _hash({key: old[key] for key in IDENTITY_FIELDS})
    validate_smooth_ab_matrix(old)


def analyze_smooth_ab_v2_pair(matrix: dict, evidence: list[dict]) -> dict[str, Any]:
    validate_smooth_ab_v2_matrix(matrix)
    if not isinstance(evidence, list) or len(evidence) != 2:
        raise FillMatrixError("V2 needs two separate fresh evidence reports.")
    results = []
    run_ids = set()
    for task, row in zip(matrix["tasks"], evidence):
        if (not isinstance(row, dict) or row.get("protocol") != PROTOCOL
                or row.get("screen_mask_version") != SCREEN_MASK
                or row.get("task_id") != task["task_id"]
                or row.get("expected_smooth") is not task["expected_smooth"]
                or row.get("raw_e4_status") != "PASS_E4_RAW_CAPTURE"
                or row.get("plan_signature") != task["plan_signature"]
                or row.get("target_mask_sha256") != task["target_mask_sha256"]
                or row.get("v2_audit", {}).get("schema") != SCREEN_MASK
                or row["v2_audit"].get("run_id") != row.get("run_id")
                or row["v2_audit"].get("acceptance_override") is not False
                or row["v2_audit"].get("before_png_sha256") != row.get("before_png_sha256")
                or row["v2_audit"].get("after_png_sha256") != row.get("after_png_sha256")
                or row["v2_audit"].get("frozen_target_mask_sha256") != task["target_mask_sha256"]
                or row["v2_audit"].get("v1_original") != {
                    "coverage_fraction": row["png_audit"]["coverage_fraction"],
                    "leakage_pixels": row["png_audit"]["leakage_pixels"],
                    "png_audit_status": row["png_audit"]["png_audit_status"],
                }):
            raise FillMatrixError("V2 report is mismatched or not run-bound.")
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or not run_id or run_id in run_ids:
            raise FillMatrixError("V2 requires unique Game Monitor run IDs.")
        run_ids.add(run_id)
        results.append(row)
    comparable = (
        results[0]["screen_roi"] == results[1]["screen_roi"]
        and results[0]["renderer_geometry_sha256"] ==
            results[1]["renderer_geometry_sha256"]
        and results[0]["before_png_sha256"] == results[1]["before_png_sha256"]
    )
    on, off = (r["v2_audit"] for r in results)
    return {
        "schema_version": 2,
        "protocol": PROTOCOL,
        "screen_mask_version": SCREEN_MASK,
        "series_id": matrix["series_id"],
        "matrix_signature": matrix["matrix_signature"],
        "status": ("ANALYZED_COMPARABLE" if comparable
                   else "PARTIAL_BASELINE_ROI_OR_GEOMETRY_MISMATCH"),
        "conditions": results,
        "off_minus_on": {
            "exact_chalk": results[1]["exact_chalk"] - results[0]["exact_chalk"],
            "v2_coverage_percentage_points": 100 * (
                off["coverage_fraction"] - on["coverage_fraction"]
            ),
            "v2_leakage_pixels": off["leakage_pixels"] - on["leakage_pixels"],
            "v1_leakage_pixels": (
                off["v1_original"]["leakage_pixels"]
                - on["v1_original"]["leakage_pixels"]
            ),
        } if comparable else None,
        "acceptance_override": False,
        "limitations": [
            "Two fresh one-task runs with separate raw Monitor/PNG are mandatory.",
            "The logical target and 27-stroke plan remain frozen, not a new target geometry.",
            "Screen Mask V2 only measures quality using run-bound desktop projection.",
            "Native Egret pixel equivalence remains independent, not established here.",
            "Old V1 capture quality and acceptance thresholds are unchanged.",
        ],
    }
