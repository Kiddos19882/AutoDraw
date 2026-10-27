from __future__ import annotations

import numpy as np

from interval_quota_fit import fit_interval_censored_quota


def test_historical_observations_have_a_positive_interval_feasible_fit():
    visible_lengths = np.asarray([25350, 24800, 22700, 15370], dtype=float)
    visible_strokes = np.asarray([39, 124, 454, 1537], dtype=float)
    stroke_lengths = np.asarray([650, 200, 50, 10], dtype=float)
    midpoint_matrix = np.column_stack((
        visible_lengths + stroke_lengths / 2.0,
        visible_strokes + 0.5,
    ))
    midpoint_coefficients = np.linalg.lstsq(
        midpoint_matrix,
        np.full(4, 6000.0),
        rcond=None,
    )[0]

    result = fit_interval_censored_quota(
        midpoint_matrix,
        visible_lengths,
        visible_strokes,
        stroke_lengths,
        6000,
        midpoint_coefficients,
    )

    assert result["status"] == "feasible"
    assert result["points_per_path_px"] > 0
    assert result["points_per_stroke"] > 0
    assert result["feasible_vertex_count"] > 0
    assert result["coefficient_ranges"]["points_per_path_px"]["minimum"] <= result["points_per_path_px"]
    assert result["coefficient_ranges"]["points_per_path_px"]["maximum"] >= result["points_per_path_px"]


def test_contradictory_intervals_are_reported_as_infeasible():
    visible_lengths = np.asarray([100.0, 1.0])
    visible_strokes = np.asarray([100.0, 1.0])
    stroke_lengths = np.asarray([1.0, 1.0])
    midpoint_matrix = np.column_stack((
        visible_lengths + stroke_lengths / 2.0,
        visible_strokes + 0.5,
    ))

    result = fit_interval_censored_quota(
        midpoint_matrix,
        visible_lengths,
        visible_strokes,
        stroke_lengths,
        100.0,
        np.asarray([0.5, 0.5]),
    )

    assert result["status"] == "infeasible"
    assert result["feasible_vertex_count"] == 0
