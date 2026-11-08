from __future__ import annotations

from copy import deepcopy

import pytest

from chalk_fill_matrix import FillMatrixError, validate_fill001_matrix
from fill001_smooth_ab_v3 import (
    COORDINATE_PREFLIGHT, PROTOCOL, build_fill001_smooth_ab_v3_matrix,
    validate_smooth_ab_v3_matrix,
)


def test_v3_is_frozen_27_stroke_new_series_and_versioned_preflight():
    series = build_fill001_smooth_ab_v3_matrix("v3-safe-probe-001")
    assert series["experiment_protocol"] == PROTOCOL
    assert series["coordinate_preflight_protocol"] == COORDINATE_PREFLIGHT
    assert series["execution_allowed"] is False
    assert [t["expected_smooth"] for t in series["tasks"]] == [True, False]
    assert all(t["coordinate_preflight_protocol"] == COORDINATE_PREFLIGHT
               and t["expected_strokes"] == 27 and t["safe_to_execute"] is False
               and t["task_id"].find("-v3-smooth-") > 0 for t in series["tasks"])
    assert len({t["plan_signature"] for t in series["tasks"]}) == 1
    validate_fill001_matrix(series)
    assert series["matrix_signature"] != build_fill001_smooth_ab_v3_matrix("other-v3")["matrix_signature"]


def test_v3_rejects_mixed_coordinates_protocol_and_tampering():
    original = build_fill001_smooth_ab_v3_matrix("v3-proof")
    for field, bad in (
        ("experiment_protocol", "FILL001_SMOOTH_AB_V2"),
        ("coordinate_preflight_protocol", "legacy_roi"),
        ("matrix_signature", "0"*64),
    ):
        mutated = deepcopy(original)
        mutated[field] = bad
        with pytest.raises(FillMatrixError):
            validate_smooth_ab_v3_matrix(mutated)
    mutated = deepcopy(original)
    mutated["tasks"][1]["task_id"] = "legacy-task"
    with pytest.raises(FillMatrixError):
        validate_smooth_ab_v3_matrix(mutated)


def test_v3_rejects_old_v2_manifest_without_new_identity():
    from fill001_smooth_ab_v2 import build_fill001_smooth_ab_v2_matrix
    old = build_fill001_smooth_ab_v2_matrix("old-v2")
    with pytest.raises(FillMatrixError):
        validate_smooth_ab_v3_matrix(old)
