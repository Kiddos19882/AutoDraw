#!/usr/bin/env python3
"""Measure brush screenshots using distance to each planned stroke centerline.

This is a geometry-aware supplement to analyze_brush_behavior_results.py. It
reports nearby ink separately from pixels close to the expected path, and it
never counts a zero-length control as a successful line. It still cannot prove
that the game registered a stroke or consumed paint.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image


def point_segment_metrics(px: float, py: float, ax: float, ay: float,
                          bx: float, by: float) -> tuple[float, float]:
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy), t * math.sqrt(length_sq)


def nearest_path_metrics(px: float, py: float,
                         points: list[tuple[float, float]]) -> tuple[float, float]:
    """Return distance and cumulative along-path position of nearest segment."""
    best_distance = float("inf")
    best_along = 0.0
    accumulated = 0.0
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        segment_length = math.hypot(bx - ax, by - ay)
        distance, local_along = point_segment_metrics(px, py, ax, ay, bx, by)
        if distance < best_distance:
            best_distance = distance
            best_along = accumulated + local_along
        accumulated += segment_length
    return best_distance, best_along


def analyze_pair(plan_path: Path, screenshot_path: Path,
                 crop: tuple[int, int, int, int], threshold: int,
                 padding: float) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plan.get("strokes"), list):
        raise ValueError(f"Plan has no strokes list: {plan_path}")
    with Image.open(screenshot_path) as image:
        screenshot = image.convert("RGB")
    cx, cy, cw, ch = crop
    if cx < 0 or cy < 0 or cw <= 0 or ch <= 0 or cx + cw > screenshot.width or cy + ch > screenshot.height:
        raise ValueError(f"Invalid crop {crop} for screenshot {screenshot.width}x{screenshot.height}")
    board = screenshot.crop((cx, cy, cx + cw, cy + ch))
    canvas_w = float(plan.get("width") or plan["canvas"]["width"])
    canvas_h = float(plan.get("height") or plan["canvas"]["height"])
    sx, sy = cw / canvas_w, ch / canvas_h
    brush = plan.get("generation", {}).get("requested_brush_value")
    # Treat the named brush value as an approximate diameter, not as a proven
    # engine measurement. The extra 2px accommodates antialiasing/scale error.
    corridor = max(2.0, float(brush or 1) / 2.0 + 2.0)
    pixels = board.load()
    rows = []

    for stroke in plan["strokes"]:
        raw_points = stroke.get("points", [])
        if len(raw_points) < 2:
            rows.append({"stroke": stroke.get("name", "unnamed"), "classification": "invalid_plan", "reason": "fewer than two points"})
            continue
        points = [(float(p["x"]), float(p["y"])) for p in raw_points]
        segments = [math.hypot(b[0]-a[0], b[1]-a[1]) for a, b in zip(points, points[1:])]
        planned = sum(segments)
        min_x = min(p[0] for p in points); max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points); max_y = max(p[1] for p in points)
        x0 = max(0, math.floor((min_x - padding - corridor) * sx))
        x1 = min(board.width, math.ceil((max_x + padding + corridor) * sx) + 1)
        y0 = max(0, math.floor((min_y - padding - corridor) * sy))
        y1 = min(board.height, math.ceil((max_y + padding + corridor) * sy) + 1)
        nearby = []
        centerline = []
        for iy in range(y0, y1):
            for ix in range(x0, x1):
                if max(pixels[ix, iy]) >= threshold:
                    continue
                px, py = ix / sx, iy / sy
                nearby.append((px, py))
                distance, along = nearest_path_metrics(px, py, points)
                if distance <= corridor:
                    centerline.append((px, py, distance, along))

        if planned <= 0.01:
            # Zero-length tests are negative controls, never successful lines.
            near_center = [p for p in nearby if math.hypot(p[0]-points[0][0], p[1]-points[0][1]) <= min(3.0, corridor)]
            classification = "zero_length_control"
            line_detected = False
            span = 0.0
            width_est = None
            note = "Any nearby dark pixels are reported as a dot candidate, not a line."
            dot_candidate = bool(near_center)
        else:
            if centerline:
                alongs = [p[3] for p in centerline]
                span = max(alongs) - min(alongs)
                distances = sorted(p[2] for p in centerline)
                # 95th percentile of distance to centerline; rough full width.
                idx = min(len(distances)-1, math.ceil(0.95 * len(distances))-1)
                # Pixel-center distance needs a +1 pixel footprint; without it,\n                # a perfectly centered 1px line would incorrectly measure as 0px.\n                width_est = round(2.0 * distances[idx] + 1.0, 2)
            else:
                span, width_est = 0.0, None
            line_detected = len(centerline) >= 2 and span >= max(1.5, planned * 0.25)
            classification = "line_trace_candidate" if line_detected else "weak_or_missing_trace"
            note = "Centerline proximity is geometric evidence only, not proof of game registration."
            dot_candidate = False

        rows.append({
            "stroke": stroke.get("name", "unnamed"),
            "planned_length_px": round(planned, 2),
            "classification": classification,
            "nearby_dark_pixel_count": len(nearby),
            "centerline_pixel_count": len(centerline),
            "line_trace_candidate": line_detected,\n            "line_shape_dominated_by_brush": classification == "brush_width_dominated_short_trace",
            "dot_candidate_for_zero_length_control": dot_candidate,
            "observed_along_path_span_px": round(span, 2),
            "estimated_full_width_px_rough": width_est,
            "centerline_corridor_radius_px": round(corridor, 2),
            "note": note,
        })

    return {
        "plan_file": str(plan_path),
        "screenshot_file": str(screenshot_path),
        "screenshot_size": {"width": screenshot.width, "height": screenshot.height},
        "board_crop_screenshot_px": {"x": cx, "y": cy, "width": cw, "height": ch},
        "plan_canvas_size": {"width": canvas_w, "height": canvas_h},
        "screenshot_scale": {"x": round(sx, 6), "y": round(sy, 6)},
        "threshold_max_rgb": threshold,
        "requested_brush_value": brush,
        "test_case": plan.get("generation", {}).get("test_case"),
        "measurements": rows,
        "limitations": [
            "Brush value is treated as an approximate diameter for centerline tolerance.",
            "Screenshots contain multiple strokes, so overlapping marks can still interfere.",
            "Image pixels cannot prove the game registered a stroke or consumed paint.",
        ],
    }


def parse_pair(value: str) -> tuple[Path, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected PLAN.json=SCREENSHOT.png")
    a, b = value.split("=", 1)
    if not a or not b:
        raise argparse.ArgumentTypeError("Both paths are required")
    return Path(a), Path(b)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", action="append", type=parse_pair, required=True)
    parser.add_argument("--crop-x", type=int, default=504)
    parser.add_argument("--crop-y", type=int, default=280)
    parser.add_argument("--crop-width", type=int, default=645)
    parser.add_argument("--crop-height", type=int, default=328)
    parser.add_argument("--threshold", type=int, default=100)
    parser.add_argument("--padding", type=float, default=6.0)
    parser.add_argument("--output", type=Path, default=Path("brush_centerline_measurements.json"))
    args = parser.parse_args()
    crop = (args.crop_x, args.crop_y, args.crop_width, args.crop_height)
    results = [analyze_pair(p, s, crop, args.threshold, args.padding) for p, s in args.pair]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema_version": 1, "result_count": len(results), "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Analyzed {len(results)} plan/screenshot pair(s).")
    for result in results:
        rows = result["measurements"]
        candidate = sum(r.get("line_trace_candidate", False) for r in rows)
        controls = sum(r.get("classification") == "zero_length_control" for r in rows)
        dots = sum(r.get("dot_candidate_for_zero_length_control", False) for r in rows)
        print(f"- brush={result['requested_brush_value']} case={result['test_case']}: {candidate} line-trace candidates; {controls} zero-length controls ({dots} dot candidates)")
    print("Reminder: this is image analysis, not proof of in-game registration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
