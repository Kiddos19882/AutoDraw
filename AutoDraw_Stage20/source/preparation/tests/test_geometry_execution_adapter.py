from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PREPARATION_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PREPARATION_ROOT.parent
EXECUTOR_ROOT = SOURCE_ROOT / "executor"
for candidate in (str(PREPARATION_ROOT), str(EXECUTOR_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from color_scanline import build_color_scanline_plan
from drawing.color_plan_execution import (
    ColorPlanExecutionError,
    color_plan_to_drawing_plan,
    geometry_color_plan_to_drawing_plan,
    validate_color_plan,
)
from geometry_color_plan import build_geometry_color_plan


PALETTE = [
    {"id": "black", "name": "Black", "rgb": [0, 0, 0], "hex": "#000000"},
    {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
]


def test_geometry_adapter_preserves_closed_contours_and_marker_metadata():
    indexes = np.full((20, 20), -1, dtype=np.int32)
    indexes[3:17, 3:17] = 0
    indexes[7:13, 7:13] = 1
    plan = build_geometry_color_plan(indexes, PALETTE, mode="contour", simplify_tolerance_px=0)

    validated = validate_color_plan(plan)
    converted = geometry_color_plan_to_drawing_plan(validated)

    assert converted.width == 20
    assert converted.height == 20
    assert converted.stroke_count == len(plan["strokes"])
    assert any(stroke.closed for stroke in converted.strokes)
    assert all("palette_index" in stroke.metadata for stroke in converted.strokes)
    assert all(stroke.metadata["line_extension_px_override"] == "0" for stroke in converted.strokes)
    converted.validate_bounds()


def test_geometry_adapter_expands_single_pixel_to_a_real_drawable_stroke():
    indexes = np.full((9, 9), -1, dtype=np.int32)
    indexes[4, 4] = 0
    plan = build_geometry_color_plan(
        indexes, PALETTE, mode="skeleton", simplify_tolerance_px=0
    )

    converted = geometry_color_plan_to_drawing_plan(plan)

    assert converted.stroke_count == 1
    stroke = converted.strokes[0]
    assert stroke.metadata["single_pixel_expanded"] == "true"
    assert stroke.points[1].x - stroke.points[0].x == 1
    assert stroke.points[1].y == stroke.points[0].y
    converted.validate_bounds()


def test_legacy_scanline_adapter_remains_compatible():
    indexes = np.full((8, 12), -1, dtype=np.int32)
    indexes[3, 2:8] = 0
    plan = build_color_scanline_plan(indexes, PALETTE)

    converted = color_plan_to_drawing_plan(plan)

    assert converted.width == 12
    assert converted.height == 8
    assert converted.strokes[0].metadata["color_scanline_order"] == "1"
    assert "line_extension_px_override" not in converted.strokes[0].metadata
    assert not converted.strokes[0].closed
    converted.validate_bounds()


def test_geometry_adapter_rejects_legacy_scanline_plan():
    indexes = np.full((8, 12), -1, dtype=np.int32)
    indexes[3, 2:8] = 0
    legacy_plan = build_color_scanline_plan(indexes, PALETTE)

    with pytest.raises(ColorPlanExecutionError):
        geometry_color_plan_to_drawing_plan(legacy_plan)


def test_two_pixel_geometry_contour_converts_to_open_drawing_stroke():
    indexes = np.full((7, 7), -1, dtype=np.int32)
    indexes[3, 2:4] = 0
    plan = build_geometry_color_plan(
        indexes, PALETTE, mode="contour", simplify_tolerance_px=5
    )

    converted = geometry_color_plan_to_drawing_plan(plan)

    assert converted.stroke_count == 1
    assert converted.strokes[0].closed is False
    converted.validate_bounds()
