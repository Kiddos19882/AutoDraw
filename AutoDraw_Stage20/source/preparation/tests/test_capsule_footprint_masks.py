import pytest

from brush_footprint_geometry import swept_capsule_pixel_masks


def test_horizontal_capsule_separates_potential_and_guaranteed_cells_from_bbox():
    result = swept_capsule_pixel_masks(
        [(5, 5), (15, 5)],
        brush_value=10,
        scale_x=1.0,
        scale_y=1.0,
        width=24,
        height=15,
    )

    assert result["bounds"] == (0, 20, 0, 10)
    potential = result["potential_cells"]
    guaranteed = result["guaranteed_cells"]

    # The AABB corner is not part of the rounded capsule endpoint.
    assert (0, 0) not in potential
    assert (0, 0) not in guaranteed
    assert (5, 5) in guaranteed
    assert (10, 5) in guaranteed
    assert guaranteed <= potential
    assert potential < {
        (x, y)
        for x in range(21)
        for y in range(11)
    }


def test_single_point_is_modeled_as_a_disk_and_clips_to_canvas():
    result = swept_capsule_pixel_masks(
        [(0, 0)],
        brush_value=2,
        scale_x=1.0,
        scale_y=1.0,
        width=4,
        height=4,
    )

    assert result["bounds"] == (0, 1, 0, 1)
    assert (0, 0) in result["guaranteed_cells"]
    assert (1, 1) in result["potential_cells"]
    assert (1, 1) not in result["guaranteed_cells"]
    assert all(0 <= x < 4 and 0 <= y < 4 for x, y in result["potential_cells"])


def test_non_uniform_scale_maps_pixel_cells_back_to_logical_space():
    result = swept_capsule_pixel_masks(
        [(5, 5)],
        brush_value=4,
        scale_x=2.0,
        scale_y=1.0,
        width=20,
        height=12,
    )

    assert result["bounds"] == (6, 14, 3, 7)
    assert (10, 5) in result["potential_cells"]
    assert (10, 5) in result["guaranteed_cells"]
    assert (6, 3) not in result["potential_cells"]


def test_polyline_union_covers_round_join_without_bbox_corner_overclaim():
    points = [(2, 2), (8, 2), (8, 8)]
    forward = swept_capsule_pixel_masks(
        points, 2, 1.0, 1.0, 12, 12
    )
    reverse = swept_capsule_pixel_masks(
        list(reversed(points)), 2, 1.0, 1.0, 12, 12
    )

    assert forward["potential_cells"] == reverse["potential_cells"]
    assert forward["guaranteed_cells"] == reverse["guaranteed_cells"]
    assert (8, 2) in forward["guaranteed_cells"]
    assert guaranteed_is_subset(forward)


def guaranteed_is_subset(result):
    return result["guaranteed_cells"] <= result["potential_cells"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"brush_value": 0},
        {"brush_value": True},
        {"scale_x": 0.0},
        {"scale_x": True},
        {"scale_y": float("inf")},
        {"width": 0},
        {"height": -1},
    ],
)
def test_invalid_brush_scale_and_canvas_are_rejected(kwargs):
    arguments = {
        "points": [(1, 1)],
        "brush_value": 2,
        "scale_x": 1.0,
        "scale_y": 1.0,
        "width": 5,
        "height": 5,
    }
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        swept_capsule_pixel_masks(**arguments)


@pytest.mark.parametrize(
    "points",
    [
        [],
        [(0, float("nan"))],
        [(0, 0), (float("inf"), 2)],
        [(0,)],
        ["xy"],
        [{"x": 1}],
    ],
)
def test_malformed_polyline_points_are_rejected(points):
    with pytest.raises(ValueError):
        swept_capsule_pixel_masks(points, 2, 1.0, 1.0, 5, 5)


def _horizontal_reference_masks(x_start, x_end, y, brush, sx, sy, width, height):
    radius_squared = (brush / 2.0) ** 2
    tolerance = 1e-12 * max(1.0, radius_squared)
    potential = set()
    guaranteed = set()
    for py in range(height):
        top = (py - 0.5) / sy
        bottom = (py + 0.5) / sy
        for px in range(width):
            left = (px - 0.5) / sx
            right = (px + 0.5) / sx
            dx = max(x_start - right, 0.0, left - x_end)
            dy = max(y - bottom, 0.0, top - y)
            if dx * dx + dy * dy < radius_squared:
                potential.add((px, py))
            corner_distances = []
            for cx, cy in ((left, top), (right, top), (left, bottom), (right, bottom)):
                corner_dx = max(x_start - cx, 0.0, cx - x_end)
                corner_distances.append(corner_dx * corner_dx + (cy - y) ** 2)
            if max(corner_distances) <= radius_squared - tolerance:
                guaranteed.add((px, py))
    return potential, guaranteed


def test_horizontal_capsule_masks_match_independent_analytic_cell_oracle():
    result = swept_capsule_pixel_masks([(3, 4), (9, 4)], 4, 1.5, 0.75, 20, 10)
    expected_potential, expected_guaranteed = _horizontal_reference_masks(
        3, 9, 4, 4, 1.5, 0.75, 20, 10
    )
    assert result["potential_cells"] == expected_potential
    assert result["guaranteed_cells"] == expected_guaranteed



def _global_bounds_reference(points, brush, sx, sy, width, height):
    """Slow global-AABB reference for the per-segment broad-phase implementation."""
    import math

    from brush_footprint_geometry import (
        _point_segment_distance_squared,
        _segment_rectangle_distance_squared,
    )

    radius = brush / 2.0
    segments = list(zip(points, points[1:])) or [(points[0], points[0])]
    epsilon = 1e-9
    left = max(0, math.floor((min(p[0] for p in points) - radius) * sx - 0.5 + epsilon) + 1)
    right = min(width - 1, math.ceil((max(p[0] for p in points) + radius) * sx + 0.5 - epsilon) - 1)
    top = max(0, math.floor((min(p[1] for p in points) - radius) * sy - 0.5 + epsilon) + 1)
    bottom = min(height - 1, math.ceil((max(p[1] for p in points) + radius) * sy + 0.5 - epsilon) - 1)
    potential, guaranteed = set(), set()
    radius_squared = radius * radius
    tolerance = 1e-12 * max(1.0, radius_squared)

    for py in range(top, bottom + 1):
        cell_top, cell_bottom = (py - 0.5) / sy, (py + 0.5) / sy
        for px in range(left, right + 1):
            cell_left, cell_right = (px - 0.5) / sx, (px + 0.5) / sx
            corners = (
                (cell_left, cell_top), (cell_right, cell_top),
                (cell_left, cell_bottom), (cell_right, cell_bottom),
            )
            for start, end in segments:
                if _segment_rectangle_distance_squared(
                    start, end, cell_left, cell_top, cell_right, cell_bottom
                ) < radius_squared:
                    potential.add((px, py))
                if all(
                    _point_segment_distance_squared(corner, start, end)
                    <= radius_squared - tolerance
                    for corner in corners
                ):
                    guaranteed.add((px, py))
                if (px, py) in potential and (px, py) in guaranteed:
                    break
    return potential, guaranteed


def test_per_segment_broad_phase_matches_global_reference_for_winding_polyline():
    points = [
        (4.0, 5.0), (18.0, 5.0), (18.0, 34.0),
        (7.0, 34.0), (7.0, 13.0), (31.0, 13.0),
        (31.0, 42.0), (44.0, 42.0),
    ]
    expected_potential, expected_guaranteed = _global_bounds_reference(
        points, 6, 1.25, 0.8, 64, 52
    )
    result = swept_capsule_pixel_masks(points, 6, 1.25, 0.8, 64, 52)

    assert result["potential_cells"] == expected_potential
    assert result["guaranteed_cells"] == expected_guaranteed


def test_collinear_vertex_subdivision_preserves_capsule_masks():
    straight = [(3.0, 7.0), (27.0, 19.0)]
    subdivided = [(3.0, 7.0), (9.0, 10.0), (18.0, 14.5), (27.0, 19.0)]
    direct = swept_capsule_pixel_masks(straight, 5, 1.4, 0.75, 48, 32)
    split = swept_capsule_pixel_masks(subdivided, 5, 1.4, 0.75, 48, 32)

    assert direct["bounds"] == split["bounds"]
    assert direct["potential_cells"] == split["potential_cells"]
    assert direct["guaranteed_cells"] == split["guaranteed_cells"]
