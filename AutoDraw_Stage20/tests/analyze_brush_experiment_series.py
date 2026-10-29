#!/usr/bin/env python3
"""Aggregate brush geometry measurements from saved experiment folders.

The analyzer compares each after-draw board ROI to the explicit blank-board
reference and estimates the cross-track width of isolated planned strokes.
It deliberately treats execution completion as the user's working assumption
for registration; image measurements describe geometry only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

from PIL import Image


def distance_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> tuple[float, float, float]:
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return math.hypot(px - ax, py - ay), 0.0, 0.0
    length = math.sqrt(length_sq)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    qx, qy = ax + t * dx, ay + t * dy
    signed_cross = (dx * (py - ay) - dy * (px - ax)) / length
    return math.hypot(px - qx, py - qy), t, signed_cross


def polyline_distance(points_a: list[tuple[float, float]], points_b: list[tuple[float, float]]) -> float:
    """Approximate minimum centerline distance between two planned polylines."""
    if len(points_a) < 2 or len(points_b) < 2:
        return math.inf
    best = math.inf
    for ax, ay in zip(points_a, points_a[1:]):
        pass
    for (ax, ay), (bx, by) in zip(points_a, points_a[1:]):
        for (cx, cy), (dx, dy) in zip(points_b, points_b[1:]):
            # A crossing or touching pair of segments has zero separation.
            denominator = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx)
            if abs(denominator) > 1e-9:
                t = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / denominator
                u = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / denominator
                if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
                    return 0.0
            best = min(best,
                       distance_to_segment(ax, ay, cx, cy, dx, dy)[0],
                       distance_to_segment(bx, by, cx, cy, dx, dy)[0],
                       distance_to_segment(cx, cy, ax, ay, bx, by)[0],
                       distance_to_segment(dx, dy, ax, ay, bx, by)[0])
    return best


def difference_points(blank: Image.Image, drawn: Image.Image, threshold: float) -> list[tuple[int, int]]:
    if blank.size != drawn.size:
        raise ValueError(f"Board ROI sizes differ: blank={blank.size}, drawn={drawn.size}")
    a, b = blank.convert("RGB"), drawn.convert("RGB")
    ap, bp = a.load(), b.load()
    result = []
    threshold_sq = threshold * threshold
    for y in range(a.height):
        for x in range(a.width):
            p, q = ap[x, y], bp[x, y]
            if sum((p[i] - q[i]) ** 2 for i in range(3)) > threshold_sq:
                result.append((x, y))
    return result


def analyze_stroke(stroke: dict[str, Any], ink: list[tuple[int, int]], brush: float | None,
                   other_strokes: list[dict[str, Any]] | None = None,
                   minimum_coverage: float = 0.45) -> dict[str, Any]:
    raw = stroke.get("points", [])
    points = [(float(p["x"]), float(p["y"])) for p in raw if isinstance(p, dict) and "x" in p and "y" in p]
    if len(points) < 2:
        return {"stroke": stroke.get("name", "unnamed"), "status": "invalid_plan", "planned_length_px": None}
    ax, ay = points[0]
    bx, by = points[-1]
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if length <= 0.01:
        return {"stroke": stroke.get("name", "unnamed"), "status": "zero_length_control",
                "planned_length_px": 0.0, "estimated_width_px": None, "confidence": "not_applicable"}

    # Use a broad capture corridor, then estimate width from the central part of
    # the trajectory. This avoids using a padded ROI's bounding box as brush size.
    corridor = max(5.0, (float(brush or 1) * 0.9) + 4.0)
    other_points = []
    for other in other_strokes or []:
        if other is stroke:
            continue
        raw_other = other.get("points", [])
        parsed = [(float(p["x"]), float(p["y"])) for p in raw_other
                  if isinstance(p, dict) and "x" in p and "y" in p]
        if len(parsed) >= 2:
            other_points.append(parsed)
    nearest_other = min((polyline_distance(points, candidate) for candidate in other_points), default=math.inf)
    overlap_risk = nearest_other <= 2.0 * corridor + 1.0
    samples: list[tuple[float, float]] = []
    along_values: list[float] = []
    for x, y in ink:
        distance, t, signed = distance_to_segment(x + 0.5, y + 0.5, ax, ay, bx, by)
        if distance <= corridor:
            samples.append((t, signed))
            along_values.append(t * length)

    central = [signed for t, signed in samples if 0.20 <= t <= 0.80]
    covered_bins = set(min(19, max(0, int(t * 20))) for t, _ in samples if 0.05 <= t <= 0.95)
    coverage = len(covered_bins) / 18.0
    if len(central) < 5 or coverage < minimum_coverage:
        return {
            "stroke": stroke.get("name", "unnamed"), "status": "insufficient_trace",
            "planned_length_px": round(length, 2), "estimated_width_px": None,
            "changed_pixels_near_path": len(samples), "centerline_coverage": round(min(1.0, coverage), 3),
            "confidence": "low", "note": "Not enough changed pixels distributed along the central path."
        }

    central.sort()
    lo = central[int((len(central) - 1) * 0.05)]
    hi = central[int((len(central) - 1) * 0.95)]
    width = max(1.0, hi - lo + 1.0)
    along_span = max(along_values) - min(along_values) if along_values else 0.0
    if length <= (float(brush or 1) * 2.0 + 8.0):
        status, confidence = "short_trace_width_confounded", "low"
    elif overlap_risk:
        status, confidence = "potential_overlap_confounded", "low"
    elif coverage >= 0.8 and len(central) >= 20:
        status, confidence = "measured_candidate", "medium"
    else:
        status, confidence = "measured_candidate", "low"
    return {
        "stroke": stroke.get("name", "unnamed"), "status": status,
        "planned_length_px": round(length, 2), "observed_along_path_span_px": round(along_span, 2),
        "estimated_width_px": round(width, 2), "changed_pixels_near_path": len(samples),
        "central_cross_track_samples": len(central), "centerline_coverage": round(min(1.0, coverage), 3),
        "nearest_other_centerline_px": None if math.isinf(nearest_other) else round(nearest_other, 2),
        "potential_overlap": overlap_risk,
        "confidence": confidence,
        "note": "Width is the 5th–95th percentile cross-track span plus one pixel; isolated long strokes are most reliable."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/results/brush_behavior_tests"))
    parser.add_argument("--blank", type=Path, default=Path("data/results/brush_behavior_tests/blank-board-reference.png"))
    parser.add_argument("--threshold", type=float, default=24.0)
    parser.add_argument("--output-json", type=Path, default=Path("data/results/brush_behavior_tests/brush-geometry-summary.json"))
    parser.add_argument("--output-csv", type=Path, default=Path("data/results/brush_behavior_tests/brush-geometry-summary.csv"))
    args = parser.parse_args()

    with Image.open(args.blank) as image:
        blank = image.convert("RGB")
    experiments = sorted(args.data_dir.glob("experiment-*/experiment.json"))
    rows: list[dict[str, Any]] = []
    series: list[dict[str, Any]] = []
    for record_path in experiments:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        phases = record.get("phases", {})
        draw_phase = phases.get("after_draw", {})
        board_name = draw_phase.get("files", {}).get("board_roi")
        if not board_name:
            continue
        board_path = record_path.parent / board_name
        plan_name = Path(record.get("drawing_plan_path", "")).name
        plan_path = args.data_dir / plan_name
        if not plan_path.exists() or not board_path.exists():
            rows.append({
                "experiment": record_path.parent.name,
                "brush": record.get("brush_value_requested"),
                "scenario": record.get("test_case"),
                "status": "missing_plan_or_board_image",
                "plan_file": plan_name,
                "board_file": board_name,
            })
            continue
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        with Image.open(board_path) as image:
            drawn = image.convert("RGB")
        if drawn.size != blank.size:
            rows.append({
                "experiment": record_path.parent.name,
                "brush": record.get("brush_value_requested"),
                "scenario": record.get("test_case"),
                "status": "roi_size_mismatch",
                "blank_size": list(blank.size),
                "drawn_size": list(drawn.size),
            })
            continue
        ink = difference_points(blank, drawn, args.threshold)
        brush = record.get("brush_value_requested")
        strokes = plan.get("strokes", [])
        stroke_results = [analyze_stroke(s, ink, float(brush) if brush is not None else None,
                                         other_strokes=strokes) for s in strokes]
        execution = record.get("execution_report", {})
        row = {
            "experiment": record_path.parent.name,
            "brush": brush,
            "scenario": record.get("test_case"),
            "execution_status": execution.get("status"),
            "completed_strokes": execution.get("completed_strokes"),
            "total_strokes": execution.get("total_strokes"),
            "duration_seconds": execution.get("duration_seconds"),
            "blank_roi_width": blank.width,
            "blank_roi_height": blank.height,
            "drawn_roi_width": drawn.width,
            "drawn_roi_height": drawn.height,
            "changed_pixels_vs_blank": len(ink),
            "stroke_count_in_plan": len(strokes),
            "meter_status": draw_phase.get("paint_meter_measurement", {}).get("status"),
            "meter_confidence": draw_phase.get("paint_meter_measurement", {}).get("confidence"),
            "measurements": stroke_results,
        }
        series.append(row)
        for measurement in stroke_results:
            rows.append({
                "experiment": row["experiment"], "brush": brush, "scenario": row["scenario"],
                "execution_status": row["execution_status"],
                "completed_strokes": row["completed_strokes"], "total_strokes": row["total_strokes"],
                "duration_seconds": row["duration_seconds"],
                "stroke": measurement.get("stroke"), "planned_length_px": measurement.get("planned_length_px"),
                "observed_along_path_span_px": measurement.get("observed_along_path_span_px"),
                "estimated_width_px": measurement.get("estimated_width_px"),
                "centerline_coverage": measurement.get("centerline_coverage"),
                "measurement_status": measurement.get("status"), "confidence": measurement.get("confidence"),
                "nearest_other_centerline_px": measurement.get("nearest_other_centerline_px"),
                "potential_overlap": measurement.get("potential_overlap"),
                "changed_pixels_near_path": measurement.get("changed_pixels_near_path"),
                "changed_pixels_vs_blank": len(ink),
                "meter_status": row["meter_status"], "meter_confidence": row["meter_confidence"],
            })

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "method": "blank_board_pixel_difference_and_cross_track_percentile",
        "working_assumption": "All strokes completed by executor are treated as registered, per user decision; image analysis measures geometry only.",
        "blank_reference": str(args.blank),
        "blank_size": {"width": blank.width, "height": blank.height},
        "threshold_rgb_euclidean": args.threshold,
        "experiment_count_analyzed": len(series),
        "measurement_row_count": len(rows),
        "experiments": series,
        "measurements": rows,
        "limitations": [
            "The brush-size setting expands the search corridor; it is not treated as a measured diameter.",
            "Width estimates are most reliable for isolated long strokes; short strokes, corners, and overlapping traces are lower confidence.",
            "Paint-meter results remain separate and are not inferred from board geometry.",
            "Execution completion is treated as registered only as the user's current working assumption."
        ],
    }
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fieldnames = sorted({key for row in rows for key in row})
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Analyzed experiments: {len(series)}")
    print(f"Per-stroke rows: {len(rows)}")
    print(f"Blank ROI: {blank.width}x{blank.height}; threshold={args.threshold}")
    for brush in sorted({str(s.get("brush")) for s in series}):
        subset = [s for s in series if str(s.get("brush")) == brush]
        print(f"brush={brush}: {len(subset)} experiment(s)")
    print(f"JSON: {args.output_json}")
    print(f"CSV: {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
