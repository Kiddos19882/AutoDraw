"""Interval-censored fitting for browser game point-quota observations.

The game quota is only known to lie between the cost of the last fully visible
stroke and the cost of the next stroke. This module finds positive coefficients
that satisfy every observed interval, when such coefficients exist, and chooses
the feasible point with the smallest midpoint least-squares error.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np


def fit_interval_censored_quota(
    midpoint_matrix: np.ndarray,
    visible_lengths: np.ndarray,
    visible_strokes: np.ndarray,
    stroke_lengths: np.ndarray,
    quota: float,
    midpoint_coefficients: np.ndarray,
) -> dict[str, Any]:
    """Fit positive path/stroke costs under all observed quota intervals.

    Each run contributes the inequalities:
      cost(last visible stroke) <= quota
      cost(last visible stroke + next stroke) >= quota

    The optimization is two-dimensional. We enumerate intersections of the
    inequality boundaries and projections of the midpoint least-squares fit
    onto each boundary. Feasible candidates are ranked by midpoint SSE.
    """
    matrix = np.asarray(midpoint_matrix, dtype=np.float64)
    lengths = np.asarray(visible_lengths, dtype=np.float64)
    strokes = np.asarray(visible_strokes, dtype=np.float64)
    stroke_lengths_array = np.asarray(stroke_lengths, dtype=np.float64)
    midpoint = np.asarray(midpoint_coefficients, dtype=np.float64)
    quota_value = float(quota)

    if matrix.ndim != 2 or matrix.shape[1] != 2 or matrix.shape[0] == 0:
        raise ValueError("midpoint_matrix должен иметь форму (n, 2), n > 0.")
    count = matrix.shape[0]
    if any(values.shape != (count,) for values in (lengths, strokes, stroke_lengths_array)):
        raise ValueError("Массивы наблюдений должны иметь одинаковую длину.")
    if midpoint.shape != (2,):
        raise ValueError("midpoint_coefficients должен содержать два коэффициента.")
    arrays = (matrix, lengths, strokes, stroke_lengths_array, midpoint)
    if any(not np.all(np.isfinite(values)) for values in arrays):
        raise ValueError("Наблюдения и коэффициенты должны быть конечными числами.")
    if quota_value <= 0 or np.any(lengths < 0) or np.any(strokes < 0) or np.any(stroke_lengths_array <= 0):
        raise ValueError("Квота должна быть положительной, а длины и количества — допустимыми.")

    epsilon = 1e-12
    # Every constraint has form A @ [path_cost, stroke_cost] <= b.
    lower_bounds = np.column_stack((lengths, strokes))
    upper_bounds = np.column_stack((lengths + stroke_lengths_array, strokes + 1.0))
    constraints = np.vstack((
        lower_bounds,
        -upper_bounds,
        np.array([[-1.0, 0.0], [0.0, -1.0]], dtype=np.float64),
    ))
    limits = np.concatenate((
        np.full(count, quota_value),
        np.full(count, -quota_value),
        np.array([-epsilon, -epsilon], dtype=np.float64),
    ))

    tolerance = max(1e-7, quota_value * 1e-9)

    def is_feasible(candidate: np.ndarray) -> bool:
        return bool(
            np.all(np.isfinite(candidate))
            and np.all(candidate > 0)
            and np.all(constraints @ candidate <= limits + tolerance)
        )

    candidates: list[np.ndarray] = []
    boundary_candidates: list[np.ndarray] = []
    for first, second in combinations(range(len(limits)), 2):
        equations = constraints[[first, second]]
        determinant = float(np.linalg.det(equations))
        if abs(determinant) <= 1e-12:
            continue
        point = np.linalg.solve(equations, limits[[first, second]])
        if is_feasible(point):
            candidates.append(point)
            boundary_candidates.append(point)

    # The unconstrained midpoint solution is optimal whenever it also obeys
    # every interval. Otherwise test its orthogonal projection onto each edge.
    if is_feasible(midpoint):
        candidates.append(midpoint.copy())
    # Minimize the actual midpoint SSE along each constraint boundary.
    # Euclidean projection would be feasible but would not generally minimize
    # ||matrix @ coefficients - quota||^2 when the columns have different scales.
    hessian = matrix.T @ matrix
    for normal, limit in zip(constraints, limits):
        try:
            hessian_inverse_normal = np.linalg.solve(hessian, normal)
        except np.linalg.LinAlgError:
            hessian_inverse_normal = np.linalg.pinv(hessian) @ normal
        denominator = float(normal @ hessian_inverse_normal)
        if denominator <= 1e-18:
            continue
        projected = midpoint - hessian_inverse_normal * (
            float(normal @ midpoint) - float(limit)
        ) / denominator
        if is_feasible(projected):
            candidates.append(projected)

    if not candidates:
        return {
            "status": "infeasible",
            "note": "Нет положительных коэффициентов, которые одновременно объясняют все интервалы порога.",
            "feasible_vertex_count": 0,
        }

    def objective(candidate: np.ndarray) -> float:
        residuals = matrix @ candidate - quota_value
        return float(residuals @ residuals)

    best = min(candidates, key=objective)
    vertices = boundary_candidates or candidates
    path_values = [float(point[0]) for point in vertices]
    stroke_values = [float(point[1]) for point in vertices]
    midpoint_objective = objective(midpoint)
    best_objective = objective(best)

    return {
        "status": "feasible",
        "points_per_path_px": float(best[0]),
        "points_per_stroke": float(best[1]),
        "midpoint_sse_points_squared": midpoint_objective,
        "interval_fit_sse_points_squared": best_objective,
        "midpoint_sse_change_percent": (
            (best_objective - midpoint_objective) / midpoint_objective * 100.0
            if midpoint_objective > 0
            else 0.0
        ),
        "feasible_vertex_count": len(boundary_candidates),
        "coefficient_ranges": {
            "points_per_path_px": {
                "minimum": min(path_values),
                "maximum": max(path_values),
            },
            "points_per_stroke": {
                "minimum": min(stroke_values),
                "maximum": max(stroke_values),
            },
        },
        "note": (
            "Диапазоны показывают коэффициенты, совместимые с наблюдаемыми интервалами, "
            "а не статистический доверительный интервал. Реальные браузерные повторы всё ещё необходимы."
        ),
    }
