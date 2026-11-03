from __future__ import annotations

from copy import deepcopy

import pytest

from chalk_fill_execution import (
    FILL001_EXECUTOR_OVERRIDE,
    prepare_fill001_single_task_plan,
)
from chalk_fill_matrix import FillMatrixError, build_fill001_matrix


@pytest.fixture(scope="module")
def matrix():
    return build_fill001_matrix("fill001-execution-test")


def _first_task(document):
    return document["tasks"][0]


def test_single_task_handoff_requires_explicit_operator_approval(matrix):
    task = _first_task(matrix)
    with pytest.raises(FillMatrixError, match="явного подтверждения"):
        prepare_fill001_single_task_plan(matrix, task["task_id"])


def test_single_task_handoff_rejects_tampered_matrix_signature(matrix):
    altered = deepcopy(matrix)
    altered["tasks"][0]["plan_signature"] = "0" * 64
    with pytest.raises(FillMatrixError, match="matrix_signature"):
        prepare_fill001_single_task_plan(
            altered,
            altered["tasks"][0]["task_id"],
            operator_approved_single_task_preflight=True,
        )


def test_single_task_handoff_rejects_non_pending_task(matrix):
    altered = deepcopy(matrix)
    altered["tasks"][0]["capture_status"] = "completed"
    # Recompute the manifest signature so the task-state guard, not hash validation, is exercised.
    import hashlib
    import json

    identity = {
        key: altered[key]
        for key in ("schema_version", "phase_id", "series_id", "shapes", "radii", "repeats", "tasks")
    }
    altered["matrix_signature"] = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    with pytest.raises(FillMatrixError, match="только pending"):
        prepare_fill001_single_task_plan(
            altered,
            altered["tasks"][0]["task_id"],
            operator_approved_single_task_preflight=True,
        )


def test_single_task_handoff_builds_exact_frozen_plan_without_enabling_matrix(matrix):
    task = _first_task(matrix)
    original = deepcopy(matrix)
    plan, selected = prepare_fill001_single_task_plan(
        matrix,
        task["task_id"],
        operator_approved_single_task_preflight=True,
    )

    assert selected == task
    assert plan["coordinate_system"] == "logical_board_pixels"
    assert plan["canvas"] == {"width": 460, "height": 240}
    assert len(plan["strokes"]) == task["expected_strokes"]
    assert plan["generation"]["chalk_fill001_task"]["task_id"] == task["task_id"]
    assert plan["generation"]["matrix_batch_execution_allowed"] is False
    assert matrix == original
    assert matrix["execution_allowed"] is False
    assert all(item["safe_to_execute"] is False for item in matrix["tasks"])


def test_p1_executor_override_is_ephemeral_and_exact():
    assert FILL001_EXECUTOR_OVERRIDE == {
        "point_step_px": 4.0,
        "point_delay_ms": 5,
        "line_extension_px": 0.0,
    }
