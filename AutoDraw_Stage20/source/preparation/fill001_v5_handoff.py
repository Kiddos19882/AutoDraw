"""DEC-030 FILL-001 V5 frozen geometry -> logical DrawingPlan, NOT executable yet.

No screenshot fitting, no CHALK approximation, no automatic game input.
A separate Stage6 mixed-width gate is required before any execution.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from chalk_fill_experiment import FILL001_EXPECTED_MASK_SHA256
from chalk_fill_strategy_comparison import export_chalk_first_v5_fixture

PROTOCOL = "FILL001_CHALK_FIRST_NATIVE_V5"
POLICY = "FILL001_CHALK_FIRST_PERIMETER_V2"
CANDIDATES = ("K_trim_0_y190_w2", "K_trim_0_y189_w3")


class Fill001V5Error(ValueError):
    pass


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def build_fill001_v5_source_plan(candidate_id: str) -> dict[str, Any]:
    """Generate exactly one pinned native candidate, without granting execution."""
    if candidate_id not in CANDIDATES:
        raise Fill001V5Error("Only the two DEC-030 trim0 candidates are eligible.")
    with tempfile.TemporaryDirectory(prefix="fill001-v5-") as folder:
        fixture = export_chalk_first_v5_fixture(Path(folder) / "fixture.json")
    if (fixture.get("schema") != PROTOCOL
            or fixture.get("quality_policy_id") != POLICY
            or fixture.get("frozen_mask_sha256") != FILL001_EXPECTED_MASK_SHA256["rectangle"]
            or fixture.get("executor_ready") is not False
            or fixture.get("measured_chalk") is not None):
        raise Fill001V5Error("Frozen V5 fixture has an invalid identity.")
    cases = fixture.get("cases")
    if not isinstance(cases, dict) or len(cases) != 9:
        raise Fill001V5Error("Frozen V5 fixture must have exactly nine cases.")
    raw_strokes = cases[candidate_id]
    expected_last = {"K_trim_0_y190_w2": (190, 2),
                     "K_trim_0_y189_w3": (189, 3)}[candidate_id]
    if not isinstance(raw_strokes, list) or len(raw_strokes) != 29:
        raise Fill001V5Error("Expected exactly 29 frozen strokes.")
    if ([st.get("width") for st in raw_strokes] != [10] * 28 + [expected_last[1]]
            or [st.get("mode") for st in raw_strokes] != ["normal"] * 29):
        raise Fill001V5Error("Frozen brush width / mode sequence changed.")
    if raw_strokes[-1].get("points") != [
        {"x": 97, "y": expected_last[0]},
        {"x": 363, "y": expected_last[0]},
    ]:
        raise Fill001V5Error("Frozen bottom stroke changed.")
    strokes = []
    for index, raw in enumerate(raw_strokes):
        points = raw.get("points")
        if not isinstance(points, list) or len(points) < 2:
            raise Fill001V5Error("Frozen source stroke has invalid points.")
        for p in points:
            if not isinstance(p, dict) or not (
                type(p.get("x")) in (int, float) and type(p.get("y")) in (int, float)
                and 0 <= p["x"] < 460 and 0 <= p["y"] < 240
            ):
                raise Fill001V5Error("Frozen point outside logical board.")
        strokes.append({
            "name": f"fill001_v5_{candidate_id}_{index + 1:02d}",
            "closed": False,
            "points": [{"x": float(p["x"]), "y": float(p["y"])} for p in points],
            "metadata": {
                "brush_value": str(raw["width"]),
                "source_stroke_index": str(index),
                "fill001_v5_candidate": candidate_id,
            },
        })
    source_hash = _canonical_sha(raw_strokes)
    return {
        "schema_version": 1,
        "name": f"FILL-001 V5 {candidate_id}",
        "coordinate_system": "logical_board_pixels",
        "canvas": {"width": 460, "height": 240},
        "width": 460,
        "height": 240,
        "strokes": strokes,
        "generation": {
            "method": "fill001_v5_dec030_frozen_mixed_width",
            "candidate_id": candidate_id,
            "protocol": PROTOCOL,
            "quality_policy_id": POLICY,
            "frozen_mask_sha256": fixture["frozen_mask_sha256"],
            "baseline_plan_signature": fixture["baseline_plan_signature"],
            "source_strokes_sha256": source_hash,
            "brush_sequence": [10] * 28 + [expected_last[1]],
            "expected_strokes": 29,
            "execution_scope": "single_v5_candidate_diagnostic",
            "automatic_execution_allowed": False,
            "requires_verified_mixed_width_stage6": True,
            "actual_chalk": None,
            "game_png_quality_status": "NOT_EVALUATED",
        },
        "summary": {
            "stroke_count": 29,
            "actual_chalk": None,
            "quality_status": "NOT_EVALUATED",
        },
    }
