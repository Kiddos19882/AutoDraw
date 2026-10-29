from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

STAGE_ROOT = Path(__file__).resolve().parents[3]
TEST_SCRIPTS = STAGE_ROOT / "tests"
if str(TEST_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(TEST_SCRIPTS))

from benchmark_interior_fill import _footprint


def test_footprint_uses_independent_horizontal_and_vertical_scales():
    indexes = np.zeros((20, 20), dtype=np.int32)
    stroke = {
        "brush_value": 4,
        "points": [{"x": 10.0, "y": 10.0}, {"x": 12.0, "y": 10.0}],
    }

    bounds = _footprint(indexes, stroke, scale_x=0.5, scale_y=1.5)

    # Horizontal half-width = 1 px; vertical half-height = 3 px.
    assert bounds == (9, 7, 13, 13)


def test_footprint_default_scale_preserves_isotropic_behavior():
    indexes = np.zeros((20, 20), dtype=np.int32)
    stroke = {
        "brush_value": 4,
        "points": [{"x": 10.0, "y": 10.0}, {"x": 12.0, "y": 10.0}],
    }

    assert _footprint(indexes, stroke) == (8, 8, 14, 12)
