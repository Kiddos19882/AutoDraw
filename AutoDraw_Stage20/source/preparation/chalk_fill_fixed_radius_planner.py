from __future__ import annotations

"""Experimental fixed-width fill planner for the isolated FILL-001 study.

The planner uses one brush width per plan, a conservative distance-transform
inset, horizontal centerline runs, and an independent OpenCV raster simulation.
It never marks a plan as executor-ready: the simulated footprint is not a
substitute for live game-renderer validation.
"""

import hashlib
import json
import math
from typing import Any

import cv2
import numpy as np

from chalk_fill_experiment import (
    FILL001_CANVAS_HEIGHT,
    FILL001_CANVAS_WIDTH,
    FILL001_RADII,
    FILL001_SHAPES,
    FILL001_EXPECTED_MASK_SHA256,
    build_fill_target_mask,
    fill_target_mask_sha256,
)


FILL001_PLANNER_VERSION = 1
FILL001_MIN_COVERAGE = 0.99
FILL001_MAX_LEAKAGE_PIXELS = 0
FILL001_SAMPLING_STEP = 4


class FillPlannerError(ValueError):
    """Raised when a fixed-radius FILL-001 plan cannot be built safely."""


def _iter_true_runs(row: np.ndarray):
    """Yield inclusive start/end coordinates for contiguous true values."""
    positions = np.flatnonzero(row)
    if positions.size == 0:
        return
    breaks = np.flatnonzero(np.diff(positions) > 1) + 1
    for run in np.split(positions, breaks):
        if run.size:
            yield int(run[0]), int(run[-1])


def _rounding_allowance(brush_value: int) -> float:
    """Compensate for the rasterizer's odd-width line quantization."""
    return 0.5 if brush_value == 5 else 0.0


def _draw_round_capped_stroke(
    canvas: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    brush_value: int,
) -> None:
    """Rasterize a round-capped line using the pinned OpenCV line-width model."""
    cap_radius = max(0, int(round(brush_value / 2.0)))
    if start == end:
        if brush_value == 1:
            canvas[start[1], start[0]] = 1
        else:
            cv2.circle(canvas, start, cap_radius, 1, thickness=-1, lineType=cv2.LINE_8)
        return

    cv2.line(canvas, start, end, 1, thickness=brush_value, lineType=cv2.LINE_8)
    if brush_value > 1:
        cv2.circle(canvas, start, cap_radius, 1, thickness=-1, lineType=cv2.LINE_8)
        cv2.circle(canvas, end, cap_radius, 1, thickness=-1, lineType=cv2.LINE_8)


def rasterize_fill_strokes(
    mask: Any,
    strokes: list[dict[str, Any]],
    brush_value: int,
) -> dict[str, Any]:
    """Rasterize fixed-width strokes and measure coverage and leakage.

    This result is a geometric estimate only; it does not estimate exact game
    CHALK consumption.
    """
    target = np.asarray(mask)
    if (
        target.ndim != 2
        or target.dtype.kind != "b"
        or target.shape != (FILL001_CANVAS_HEIGHT, FILL001_CANVAS_WIDTH)
        or not bool(np.any(target))
    ):
        raise FillPlannerError("Некорректная frozen mask FILL-001.")
    if (
        isinstance(brush_value, bool)
        or not isinstance(brush_value, int)
        or brush_value not in FILL001_RADII
    ):
        raise FillPlannerError("Недопустимый фиксированный размер кисти FILL-001.")
    if not isinstance(strokes, list):
        raise FillPlannerError("Список штрихов должен быть массивом.")

    raster = np.zeros(target.shape, dtype=np.uint8)
    for index, stroke in enumerate(strokes):
        if not isinstance(stroke, dict) or stroke.get("brush_value") != brush_value:
            raise FillPlannerError(f"Штрих {index} использует другой размер кисти.")
        points = stroke.get("points")
        if not isinstance(points, list) or len(points) != 2:
            raise FillPlannerError(f"Штрих {index} должен иметь две конечные точки.")
        parsed = []
        for point in points:
            if not isinstance(point, dict):
                raise FillPlannerError(f"Некорректная точка штриха {index}.")
            x, y = point.get("x"), point.get("y")
            if (
                isinstance(x, bool)
                or isinstance(y, bool)
                or not isinstance(x, int)
                or not isinstance(y, int)
                or not (0 <= x < target.shape[1] and 0 <= y < target.shape[0])
            ):
                raise FillPlannerError(f"Координата штриха {index} вне logical canvas.")
            parsed.append((x, y))
        _draw_round_capped_stroke(raster, parsed[0], parsed[1], brush_value)

    painted = raster.astype(bool)
    target_area = int(np.count_nonzero(target))
    covered_area = int(np.count_nonzero(painted & target))
    leakage = int(np.count_nonzero(painted & ~target))
    return {
        "target_area_pixels": target_area,
        "covered_target_pixels": covered_area,
        "uncovered_target_pixels": target_area - covered_area,
        "coverage_fraction": covered_area / target_area,
        "leakage_pixels": leakage,
        "rasterized_pixels": int(np.count_nonzero(painted)),
    }


def build_fixed_radius_fill_plan(
    shape_id: str,
    radius: int,
    *,
    sampling_step: int = FILL001_SAMPLING_STEP,
) -> dict[str, Any]:
    """Build a deterministic plan using exactly one brush width.

    Centerlines are restricted to pixels whose distance from the target
    boundary can contain the modeled brush footprint. Every logical row is
    sampled to avoid coverage holes between adjacent passes. A plan that fails
    coverage/leakage acceptance is returned as unsupported and is never marked
    safe for automatic execution.
    """
    if not isinstance(shape_id, str) or shape_id not in FILL001_SHAPES:
        raise FillPlannerError(f"Неизвестная форма FILL-001: {shape_id!r}.")
    if isinstance(radius, bool) or not isinstance(radius, int) or radius not in FILL001_RADII:
        raise FillPlannerError("Радиус должен быть одним из значений 1/5/10/20/30.")
    if isinstance(sampling_step, bool) or not isinstance(sampling_step, int) or sampling_step < 1:
        raise FillPlannerError("Шаг оценки sampling должен быть положительным целым числом.")

    mask = build_fill_target_mask(shape_id)
    mask_hash = fill_target_mask_sha256(shape_id, mask)
    if mask_hash != FILL001_EXPECTED_MASK_SHA256[shape_id]:
        raise FillPlannerError("SHA-256 frozen mask не совпадает с закреплённым значением.")

    distance = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    inset = radius / 2.0 + _rounding_allowance(radius)
    centerline_mask = distance >= (inset + 0.01)

    strokes: list[dict[str, Any]] = []
    path_length = 0.0
    for y in range(FILL001_CANVAS_HEIGHT):
        for x_start, x_end in _iter_true_runs(centerline_mask[y]):
            path_length += float(x_end - x_start)
            strokes.append({
                "stroke_index": len(strokes),
                "points": [{"x": x_start, "y": y}, {"x": x_end, "y": y}],
                "brush_value": radius,
                "role": "fixed_radius_interior_scanline",
                "safe_for_target_mask": True,
                "safe_to_execute": False,
            })

    raster_metrics = rasterize_fill_strokes(mask, strokes, radius)
    coverage = float(raster_metrics["coverage_fraction"])
    leakage = int(raster_metrics["leakage_pixels"])
    quality_passed = coverage >= FILL001_MIN_COVERAGE and leakage <= FILL001_MAX_LEAKAGE_PIXELS
    sampling_estimate = sum(
        max(1, int(math.ceil(
            math.hypot(
                stroke["points"][1]["x"] - stroke["points"][0]["x"],
                stroke["points"][1]["y"] - stroke["points"][0]["y"],
            ) / sampling_step
        )) + 1)
        for stroke in strokes
    )
    identity = {
        "planner_version": FILL001_PLANNER_VERSION,
        "shape_id": shape_id,
        "radius": radius,
        "target_mask_sha256": mask_hash,
        "strokes": [
            [stroke["points"][0]["x"], stroke["points"][0]["y"],
             stroke["points"][1]["x"], stroke["points"][1]["y"]]
            for stroke in strokes
        ],
    }
    signature = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "schema_version": 1,
        "plan_type": "autodraw_fill001_fixed_radius_experimental",
        "planner_version": FILL001_PLANNER_VERSION,
        "shape_id": shape_id,
        "radius": radius,
        "canvas": {"width": FILL001_CANVAS_WIDTH, "height": FILL001_CANVAS_HEIGHT},
        "target_mask_sha256": mask_hash,
        "plan_signature": signature,
        "brush_configuration": {
            "brush_value": radius,
            "footprint_model": "opencv_round_capped_line",
            "centerline_inset_pixels": inset,
            "scanline_row_step": 1,
            "sampling_step_for_estimate": sampling_step,
            "automatic_execution_allowed": False,
        },
        "summary": {
            **raster_metrics,
            "coverage_percent": round(coverage * 100.0, 6),
            "quality_gate_passed": quality_passed,
            "unsupported": not quality_passed,
            "unsupported_reason": None if quality_passed else "coverage_or_leakage_gate_failed",
            "stroke_count": len(strokes),
            "path_length_logical_pixels": round(path_length, 3),
            "estimated_sampling_points": sampling_estimate,
            "estimated_sampling_points_are_exact_chalk": False,
            "ready_for_automatic_execution": False,
        },
        "strokes": strokes,
    }
