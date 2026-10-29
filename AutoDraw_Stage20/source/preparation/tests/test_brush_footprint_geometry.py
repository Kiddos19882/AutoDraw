from __future__ import annotations

import pytest

from brush_footprint_geometry import footprint_pixel_bounds


def test_unit_brush_at_unit_scale_does_not_cross_cell_boundaries():
    assert footprint_pixel_bounds(3, 3, 3, 1, 1.0, 1.0, 10, 10) == (3, 3, 3, 3)


def test_scaled_unit_brush_includes_neighboring_cells_with_positive_overlap():
    assert footprint_pixel_bounds(3, 3, 3, 1, 1.4, 1.4, 10, 10) == (2, 4, 2, 4)


def test_footprint_clips_to_canvas_edges():
    assert footprint_pixel_bounds(0, 0, 0, 1, 1.4, 1.4, 10, 10) == (0, 1, 0, 1)


def test_footprint_rejects_invalid_geometry():
    with pytest.raises(ValueError):
        footprint_pixel_bounds(4, 3, 3, 1, 1.0, 1.0, 10, 10)
