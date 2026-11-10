from __future__ import annotations

import json

import pytest

from fill001_v5_handoff import (
    CANDIDATES, Fill001V5Error, build_fill001_v5_source_plan,
)


@pytest.mark.parametrize("candidate,width,y", [
    ("K_trim_0_y190_w2", 2, 190),
    ("K_trim_0_y189_w3", 3, 189),
])
def test_v5_adapter_produces_pinned_mixed_width_not_executable(candidate, width, y):
    first = build_fill001_v5_source_plan(candidate)
    again = build_fill001_v5_source_plan(candidate)
    assert first == again
    assert first["coordinate_system"] == "logical_board_pixels"
    assert first["canvas"] == {"width": 460, "height": 240}
    assert len(first["strokes"]) == 29
    assert [int(x["metadata"]["brush_value"]) for x in first["strokes"]] == [10]*28 + [width]
    assert first["strokes"][-1]["points"] == [
        {"x": 97.0, "y": float(y)}, {"x": 363.0, "y": float(y)}
    ]
    generation = first["generation"]
    assert generation["automatic_execution_allowed"] is False
    assert generation["requires_verified_mixed_width_stage6"] is True
    assert generation["actual_chalk"] is None
    assert generation["source_strokes_sha256"]
    assert first["summary"]["quality_status"] == "NOT_EVALUATED"


def test_v5_adapter_strict_candidate_allowlist():
    for candidate in ("K_trim_1_y190_w2", "V4_y190_w2_control", "", "../../escape"):
        with pytest.raises(Fill001V5Error, match="DEC-030"):
            build_fill001_v5_source_plan(candidate)


def test_v5_adapter_json_serialization_is_deterministic():
    plan = build_fill001_v5_source_plan(CANDIDATES[0])
    assert json.loads(json.dumps(plan, allow_nan=False)) == plan
