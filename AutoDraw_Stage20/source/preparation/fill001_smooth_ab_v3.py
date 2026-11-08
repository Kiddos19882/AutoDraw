from __future__ import annotations

"""FILL001_SMOOTH_AB_V3: same frozen target, NEW preflight BoardPane mapping.

A new protocol is mandatory because the coordinate transform is a changed
experimental variable. V1/V2 runs must never be compared as a V3 pair.
"""
from copy import deepcopy
from pathlib import Path
from typing import Any

from chalk_fill_matrix import FillMatrixError, _hash
from fill001_smooth_ab_v2 import (
    PROTOCOL as V2, SCREEN_MASK, V2_IDENTITY_FIELDS,
    build_fill001_smooth_ab_v2_matrix, validate_smooth_ab_v2_matrix,
)

PROTOCOL = "FILL001_SMOOTH_AB_V3"
COORDINATE_PREFLIGHT = "FILL001_BOARDPANE_PREFLIGHT_V1"
V3_IDENTITY_FIELDS = (*V2_IDENTITY_FIELDS, "coordinate_preflight_protocol")


def _name(series: str, mode: bool) -> str:
    return f"{series}-rectangle-r10-s5-o0-v3-smooth-{'on' if mode else 'off'}"


def build_fill001_smooth_ab_v3_matrix(series_id: str) -> dict[str, Any]:
    matrix = deepcopy(build_fill001_smooth_ab_v2_matrix(series_id))
    matrix["experiment_protocol"] = PROTOCOL
    matrix["coordinate_preflight_protocol"] = COORDINATE_PREFLIGHT
    for task in matrix["tasks"]:
        task["task_id"] = _name(series_id, task["expected_smooth"])
        task["experiment_protocol"] = PROTOCOL
        task["coordinate_preflight_protocol"] = COORDINATE_PREFLIGHT
    matrix["matrix_signature"] = _hash({key: matrix[key] for key in V3_IDENTITY_FIELDS})
    validate_smooth_ab_v3_matrix(matrix)
    return matrix


def validate_smooth_ab_v3_matrix(matrix: Any) -> None:
    if (not isinstance(matrix, dict)
            or matrix.get("experiment_protocol") != PROTOCOL
            or matrix.get("coordinate_preflight_protocol") != COORDINATE_PREFLIGHT
            or set(V3_IDENTITY_FIELDS) - set(matrix)
            or matrix.get("matrix_signature") != _hash(
                {key: matrix[key] for key in V3_IDENTITY_FIELDS}
            )):
        raise FillMatrixError("V3 protocol/BoardPane-preflight/signature mismatch.")
    tasks = matrix.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 2:
        raise FillMatrixError("V3 requires two ordered ON/OFF tasks.")
    original = deepcopy(matrix)
    original.pop("coordinate_preflight_protocol")
    original["experiment_protocol"] = V2
    for task in original["tasks"]:
        if (not isinstance(task, dict)
                or task.get("coordinate_preflight_protocol") != COORDINATE_PREFLIGHT
                or task.get("experiment_protocol") != PROTOCOL
                or type(task.get("expected_smooth")) is not bool
                or task.get("task_id") != _name(matrix["series_id"], task["expected_smooth"])):
            raise FillMatrixError("V3 task protocol, name, or declared smooth mismatch.")
        task.pop("coordinate_preflight_protocol")
        task["experiment_protocol"] = V2
        task["task_id"] = (
            f"{matrix['series_id']}-rectangle-r10-s5-o0-v2-smooth-"
            f"{'on' if task['expected_smooth'] else 'off'}"
        )
    original["matrix_signature"] = _hash(
        {key: original[key] for key in V2_IDENTITY_FIELDS}
    )
    validate_smooth_ab_v2_matrix(original)


def analyze_smooth_ab_v3_pair(matrix: dict, rows: list[dict]) -> dict[str, Any]:
    validate_smooth_ab_v3_matrix(matrix)
    if not isinstance(rows, list) or len(rows) != 2:
        raise FillMatrixError("V3 requires two separate fresh captures.")
    run_ids = set()
    for task, row in zip(matrix["tasks"], rows):
        before, after = (Path(row.get(key) or "").name
                         for key in ("before_png", "after_png"))
        preflight = row.get("boardpane_preflight")
        audit = row.get("v2_audit")
        if (not isinstance(row, dict) or row.get("protocol") != PROTOCOL
                or row.get("task_id") != task["task_id"]
                or row.get("expected_smooth") is not task["expected_smooth"]
                or row.get("screen_mask_version") != SCREEN_MASK
                or row.get("raw_e4_status") != "PASS_E4_RAW_CAPTURE"
                or before != task["task_id"]+"-before.png"
                or after != task["task_id"]+"-after.png"
                or not isinstance(preflight, dict)
                or preflight.get("schema") != COORDINATE_PREFLIGHT
                or preflight.get("session_id") != row.get("session_id")
                or preflight.get("boardpane_mapping_sha256") != row.get("boardpane_mapping_sha256")
                or preflight.get("screen_roi") != row.get("screen_roi")
                or not isinstance(audit, dict) or audit.get("schema") != SCREEN_MASK
                or audit.get("run_id") != row.get("run_id")
                or audit.get("acceptance_override") is not False
                or audit.get("frozen_target_mask_sha256") != task["target_mask_sha256"]
                or audit.get("before_png_sha256") != row.get("before_png_sha256")
                or audit.get("after_png_sha256") != row.get("after_png_sha256")
                or row.get("v2_binding_provenance", {}).get("raw_run_sha256")
                   != row.get("raw_run_sha256")
                or audit.get("geometry_evidence_sha256") != row.get("raw_run_sha256")):
            raise FillMatrixError("V3 capture provenance or preflight binding mismatch.")
        run_id = row.get("run_id")
        if not isinstance(run_id, str) or not run_id or run_id in run_ids:
            raise FillMatrixError("V3 requires two distinct run IDs.")
        run_ids.add(run_id)
    on, off = rows
    comparable = (on["screen_roi"] == off["screen_roi"]
                  and on["boardpane_mapping_sha256"] == off["boardpane_mapping_sha256"]
                  and on["before_png_sha256"] == off["before_png_sha256"])
    return {
        "protocol": PROTOCOL, "series_id": matrix["series_id"],
        "matrix_signature": matrix["matrix_signature"],
        "status": ("ANALYZED_COMPARABLE" if comparable else
                   "PARTIAL_BASELINE_ROI_OR_GEOMETRY_MISMATCH"),
        "conditions": rows,
        "off_minus_on": ({
            "exact_chalk": off["exact_chalk"] - on["exact_chalk"],
            "v2_coverage_percentage_points": 100*(
                off["v2_audit"]["coverage_fraction"]-on["v2_audit"]["coverage_fraction"]),
            "v2_leakage_pixels": (
                off["v2_audit"]["leakage_pixels"]-on["v2_audit"]["leakage_pixels"]),
        } if comparable else None),
        "acceptance_override": False,
        "limits": ["New V3 run-bound preflight required before game input.",
                   "Never compare V3 with V1/V2 as a paired Smooth effect.",
                   "Original PNG quality gates, mask and CHALK are unchanged."],
    }
