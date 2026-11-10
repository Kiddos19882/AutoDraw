"""The frozen V5 diagnostic DrawingPlan cannot bypass Stage6's mixed-brush gate."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from fill001_v5_handoff import build_fill001_v5_source_plan
from stage6_execute_plan import Stage6App


@pytest.mark.parametrize("candidate", ("K_trim_0_y190_w2", "K_trim_0_y189_w3"))
def test_stage6_rejects_v5_source_even_if_coordinate_system_is_relabelled(tmp_path, candidate):
    payload = build_fill001_v5_source_plan(candidate)
    # An attacker or erroneous handoff might relabel it as a local_canvas plan.
    payload["coordinate_system"] = "local_canvas_pixels"
    path = tmp_path / "v5.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    app = Stage6App.__new__(Stage6App)
    app.running = False
    with pytest.raises(ValueError, match="mixed-width source plan"):
        app.load_plan_from_path(path)
    assert not hasattr(app, "plan_path")


def test_stage6_rejects_forged_v5_protocol_even_without_generation_method(tmp_path):
    payload = build_fill001_v5_source_plan("K_trim_0_y190_w2")
    payload["coordinate_system"] = "local_canvas_pixels"
    payload["generation"]["method"] = "unknown"
    path = tmp_path / "forged.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    app = Stage6App.__new__(Stage6App)
    app.running = False
    with pytest.raises(ValueError, match="mixed-width source plan"):
        app.load_plan_from_path(path)

@pytest.mark.parametrize("candidate", ("K_trim_0_y190_w2", "K_trim_0_y189_w3"))
def test_stage6_rejects_v5_after_normal_model_serialization_strips_generation(tmp_path, candidate):
    from models import DrawingPlan
    original = build_fill001_v5_source_plan(candidate)
    stripped = DrawingPlan.from_dict(original).to_dict()
    assert "generation" not in stripped
    assert stripped["strokes"][0]["metadata"]["fill001_v5_candidate"] == candidate
    path = tmp_path / "model-round-trip.json"
    path.write_text(json.dumps(stripped), encoding="utf-8")
    app = Stage6App.__new__(Stage6App)
    app.running = False
    with pytest.raises(ValueError, match="mixed-width source plan"):
        app.load_plan_from_path(path)
    assert not hasattr(app, "plan_path")
