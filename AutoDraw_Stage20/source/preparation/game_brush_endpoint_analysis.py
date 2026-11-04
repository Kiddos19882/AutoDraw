from __future__ import annotations

"""Offline analysis of accepted Game Monitor points against Egret smooth-path endpoints.

This is an evidence-analysis utility, not a production brush renderer and not a
pixel-coverage oracle. It measures accepted point spacing and the geometric
reach of an ideal round cap around the midpoint endpoint used by the game's
smooth-path call when its final-line flag is false.
"""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be a finite number.")
    return result


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def _distance_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "median": None,
            "p90": None,
            "p95": None,
            "max": None,
            "over_line_width": 0,
        }
    return {
        "count": len(values),
        "min": min(values),
        "median": median(values),
        "p90": _percentile(values, 0.90),
        "p95": _percentile(values, 0.95),
        "max": max(values),
    }


def analyze_run(run: dict[str, Any]) -> dict[str, Any]:
    """Analyze one Game Monitor run JSON without modifying its evidence."""
    if not isinstance(run, dict):
        raise ValueError("Run must be a JSON object.")

    raw_width = run.get("brush_radius")
    if raw_width is None:
        observed = run.get("observed_brush_radii")
        if not isinstance(observed, list) or len(set(observed)) != 1:
            raise ValueError("A single observed brush line width is required.")
        raw_width = observed[0]
    line_width = _finite_number(raw_width, "brush_radius")
    if line_width <= 0:
        raise ValueError("brush_radius must be greater than zero.")

    raw_points = run.get("accepted_points")
    events = run.get("events")
    if not isinstance(raw_points, list) or not isinstance(events, list):
        raise ValueError("Run must contain accepted_points and events arrays.")

    grouped: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    for index, point in enumerate(raw_points):
        if not isinstance(point, dict):
            raise ValueError(f"accepted_points[{index}] must be an object.")
        stroke_id = point.get("stroke_id")
        if not isinstance(stroke_id, str) or not stroke_id:
            raise ValueError(f"accepted_points[{index}].stroke_id is missing.")
        x = _finite_number(point.get("x"), f"accepted_points[{index}].x")
        y = _finite_number(point.get("y"), f"accepted_points[{index}].y")
        t = _finite_number(point.get("t", index), f"accepted_points[{index}].t")
        grouped[stroke_id].append((t, x, y))

    all_segments: list[float] = []
    final_segments: list[float] = []
    per_stroke: list[dict[str, Any]] = []
    for stroke_id, raw_stroke_points in grouped.items():
        points = sorted(raw_stroke_points, key=lambda item: item[0])
        segments = [
            math.hypot(b[1] - a[1], b[2] - a[2])
            for a, b in zip(points, points[1:])
        ]
        all_segments.extend(segments)
        last_segment = segments[-1] if segments else None
        if last_segment is not None:
            final_segments.append(last_segment)
            # The smooth path ends at the midpoint of the final accepted pair.
            # A round cap has radius line_width/2; the last point is line_width
            # away from the midpoint only when the pair distance exceeds width.
            cap_margin = (line_width - last_segment) / 2.0
            cap_covers_last_sample = cap_margin >= -1e-12
            estimated_gap = max(0.0, -cap_margin)
            path_endpoint = {
                "x": (points[-2][1] + points[-1][1]) / 2.0,
                "y": (points[-2][2] + points[-1][2]) / 2.0,
            }
        else:
            cap_margin = None
            cap_covers_last_sample = None
            estimated_gap = None
            path_endpoint = None

        per_stroke.append({
            "stroke_id": stroke_id,
            "accepted_point_count": len(points),
            "first_accepted_point": {"x": points[0][1], "y": points[0][2]},
            "last_accepted_point": {"x": points[-1][1], "y": points[-1][2]},
            "smooth_path_terminal_point": path_endpoint,
            "last_accepted_segment_length": last_segment,
            "ideal_round_cap_margin_to_last_sample": cap_margin,
            "ideal_round_cap_covers_last_sample_center": cap_covers_last_sample,
            "ideal_geometric_gap_to_last_sample_center": estimated_gap,
        })

    draw_samples = [
        event for event in events
        if isinstance(event, dict) and event.get("type") == "DRAW_SAMPLE"
    ]
    positive_deltas = [
        _finite_number(event.get("pointDelta", 0), "DRAW_SAMPLE.pointDelta")
        for event in draw_samples
        if event.get("pointDelta") is not None
        and _finite_number(event.get("pointDelta", 0), "DRAW_SAMPLE.pointDelta") > 0
    ]
    quota_updates = sum(
        1 for event in events
        if isinstance(event, dict) and event.get("type") == "POINT_QUOTA_UPDATE"
    )
    chalk = run.get("chalk") if isinstance(run.get("chalk"), dict) else {}
    chalk_consumed = chalk.get("consumed_points")
    chalk_consumed_number = (
        _finite_number(chalk_consumed, "chalk.consumed_points")
        if chalk_consumed is not None else None
    )
    positive_delta_sum = int(sum(positive_deltas))
    max_positive_delta = max(positive_deltas, default=0)
    accepted_count = len(raw_points)
    coordinate_capture_complete = (
        accepted_count == positive_delta_sum
        and max_positive_delta <= 1
        and (chalk_consumed_number is None or positive_delta_sum == chalk_consumed_number)
        and (quota_updates == 0 or quota_updates == positive_delta_sum)
    )

    segment_summary = _distance_summary(all_segments)
    segment_summary["over_line_width"] = sum(
        1 for distance in all_segments if distance > line_width
    )
    final_summary = _distance_summary(final_segments)
    final_summary["over_line_width"] = sum(
        1 for distance in final_segments if distance > line_width
    )
    final_cap_covered = sum(
        1 for item in per_stroke
        if item["ideal_round_cap_covers_last_sample_center"] is True
    )
    final_cap_evaluable = sum(
        1 for item in per_stroke
        if item["ideal_round_cap_covers_last_sample_center"] is not None
    )

    return {
        "analysis_version": 1,
        "run_id": run.get("run_id"),
        "brush_line_width": line_width,
        "chalk_consumed_points": chalk_consumed_number,
        "stroke_count_in_run": run.get("stroke_count"),
        "accepted_point_count": accepted_count,
        "draw_sample_count": len(draw_samples),
        "positive_draw_sample_count": len(positive_deltas),
        "positive_draw_sample_point_delta_sum": positive_delta_sum,
        "max_positive_draw_sample_point_delta": max_positive_delta,
        "point_quota_update_count": quota_updates,
        "accepted_point_coordinates_complete_for_observed_deltas": coordinate_capture_complete,
        "within_stroke_segment_lengths": segment_summary,
        "last_segment_per_stroke": final_summary,
        "ideal_round_cap_covers_last_accepted_sample_centers": final_cap_covered,
        "last_sample_center_coverage_evaluable_strokes": final_cap_evaluable,
        "per_stroke": per_stroke,
        "limitations": [
            "This is ideal geometry based on a round cap and the observed line width, not a Canvas2D/WebGL pixel mask.",
            "The mouseup coordinate is not sampled by BoardPane.onDrawingEnd(); this analysis does not infer the distance from the last accepted point to mouseup.",
            "Texture filtering, browser antialiasing, mask/scrollRect clipping and PNG pixel equivalence are not evaluated.",
            "A one-point stroke has no final segment and is not classified as visible or invisible by this geometric cap calculation.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Game Monitor run JSON")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    run = json.loads(args.input.read_text(encoding="utf-8"))
    report = analyze_run(run)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
