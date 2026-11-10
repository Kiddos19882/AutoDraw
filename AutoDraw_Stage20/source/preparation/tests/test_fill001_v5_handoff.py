from __future__ import annotations

import json

import pytest

from fill001_v5_handoff import (
    CANDIDATES, Fill001V5Error, build_fill001_v5_source_plan,
    validate_fill001_v5_source_plan,
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

@pytest.mark.parametrize("candidate", CANDIDATES)
def test_v5_source_plan_validator_rejects_every_kind_of_tampering(candidate):
    original = build_fill001_v5_source_plan(candidate)
    assert validate_fill001_v5_source_plan(original) == candidate
    attacks = [
        ("strokes", 0, "points", 0, "x", 1),
        ("strokes", 28, "metadata", "brush_value", "10"),
        ("generation", "automatic_execution_allowed", True),
        ("generation", "source_strokes_sha256", "0"*64),
        ("generation", "actual_chalk", 123),
    ]
    for path in attacks:
        corrupt = json.loads(json.dumps(original))
        *keys, new_value = path
        obj = corrupt
        for key in keys[:-1]:
            obj = obj[key]
        obj[keys[-1]] = new_value
        with pytest.raises(Fill001V5Error, match="differs"):
            validate_fill001_v5_source_plan(corrupt)

@pytest.mark.parametrize("candidate", CANDIDATES)
def test_v5_source_plan_is_compatible_with_existing_drawing_model(candidate):
    from models import DrawingPlan
    document = build_fill001_v5_source_plan(candidate)
    plan = DrawingPlan.from_dict(document)
    plan.validate_bounds()
    assert plan.stroke_count == 29
    assert plan.width == 460 and plan.height == 240
    assert [stroke.metadata["brush_value"] for stroke in plan.strokes] == [
        str(width) for width in document["generation"]["brush_sequence"]
    ]
