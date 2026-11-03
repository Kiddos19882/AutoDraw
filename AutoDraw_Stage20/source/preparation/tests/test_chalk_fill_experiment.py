from __future__ import annotations

import re

import numpy as np
import pytest

from chalk_fill_experiment import (
    FILL001_CANVAS_HEIGHT,
    FILL001_CANVAS_WIDTH,
    FILL001_EXPECTED_MASK_SHA256,
    FILL001_RADII,
    FILL001_SHAPES,
    build_fill_target_mask,
    describe_fill_target_mask,
    fill_target_mask_sha256,
)


def test_frozen_masks_are_deterministic_read_only_and_have_expected_dimensions():
    for shape_id in FILL001_SHAPES:
        first = build_fill_target_mask(shape_id)
        second = build_fill_target_mask(shape_id)

        assert first.dtype == np.bool_
        assert first.shape == (FILL001_CANVAS_HEIGHT, FILL001_CANVAS_WIDTH)
        assert np.array_equal(first, second)
        assert not first.flags.writeable
        observed_hash = fill_target_mask_sha256(shape_id, first)
        assert observed_hash == fill_target_mask_sha256(shape_id, second)
        assert observed_hash == FILL001_EXPECTED_MASK_SHA256[shape_id]


def test_frozen_mask_areas_are_matched_within_five_percent():
    areas = [
        int(np.count_nonzero(build_fill_target_mask(shape_id)))
        for shape_id in FILL001_SHAPES
    ]

    assert min(areas) > 0
    assert max(areas) / min(areas) <= 1.05


def test_shape_profiles_have_distinct_wide_and_narrow_aspect_ratios():
    bounds = {}
    for shape_id in FILL001_SHAPES:
        ys, xs = np.where(build_fill_target_mask(shape_id))
        bounds[shape_id] = (
            int(xs.max() - xs.min() + 1),
            int(ys.max() - ys.min() + 1),
        )

    wide_width, wide_height = bounds["wide_irregular"]
    narrow_width, narrow_height = bounds["narrow_irregular"]

    assert wide_width > narrow_width
    assert narrow_height > wide_height
    assert bounds["rectangle"][0] > bounds["rectangle"][1]


def test_each_frozen_mask_is_one_contiguous_run_per_active_row():
    for shape_id in FILL001_SHAPES:
        mask = build_fill_target_mask(shape_id)
        active_rows = np.flatnonzero(np.any(mask, axis=1))

        assert active_rows.size > 0
        for y in active_rows:
            xs = np.flatnonzero(mask[y])
            assert xs.size > 0
            assert np.all(np.diff(xs) == 1), f"{shape_id} has a disconnected row at y={y}"


def test_frozen_masks_are_connected_across_adjacent_rows():
    for shape_id in FILL001_SHAPES:
        mask = build_fill_target_mask(shape_id)
        active_rows = np.flatnonzero(np.any(mask, axis=1))
        assert np.all(np.diff(active_rows) == 1)
        for y1, y2 in zip(active_rows[:-1], active_rows[1:]):
            assert np.any(mask[y1] & mask[y2]), f"{shape_id} is disconnected between rows {y1} and {y2}"


def test_mask_metadata_contains_stable_identity_and_area():
    metadata = describe_fill_target_mask("wide_irregular")

    assert metadata["shape_id"] == "wide_irregular"
    assert metadata["canvas"] == {
        "width": FILL001_CANVAS_WIDTH,
        "height": FILL001_CANVAS_HEIGHT,
    }
    assert metadata["target_area_pixels"] > 0
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["target_mask_sha256"])
    assert metadata["coordinate_system"] == "logical_board_pixels"


def test_supported_radius_matrix_is_frozen():
    assert FILL001_RADII == (1, 5, 10, 20, 30)


def test_unknown_shape_and_invalid_mask_are_rejected():
    with pytest.raises(ValueError):
        build_fill_target_mask("not-a-fill-shape")
    with pytest.raises(ValueError):
        fill_target_mask_sha256("not-a-fill-shape", np.zeros((FILL001_CANVAS_HEIGHT, FILL001_CANVAS_WIDTH), dtype=bool))
    with pytest.raises(ValueError):
        fill_target_mask_sha256("rectangle", np.zeros((4, 4), dtype=bool))
    with pytest.raises(ValueError):
        fill_target_mask_sha256("rectangle", np.zeros((FILL001_CANVAS_HEIGHT, FILL001_CANVAS_WIDTH), dtype=np.uint8))
