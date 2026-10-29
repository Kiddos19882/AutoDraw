from __future__ import annotations

"""Compare interior-fill fallback merge tolerances on deterministic synthetic maps."""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import numpy as np

APP_ROOT = Path(__file__).resolve().parents[1]
for import_root in (APP_ROOT / "source" / "preparation", APP_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from brush_footprint_geometry import footprint_pixel_bounds  # noqa: E402
from interior_fill_planner import build_interior_fill_plan  # noqa: E402


GAPS = (0, 1, 3, 5, 8, 12)


def make_cases() -> dict[str, np.ndarray]:
    """Build fixed maps with broad, thin, isolated and fragmented geometry."""
    cases: dict[str, np.ndarray] = {}

    broad = np.full((160, 320), -1, dtype=np.int32)
    broad[12:146, 12:170] = 0
    broad[42:108, 55:121] = -1
    broad[12:146, 171:308] = 1
    broad[38:119, 205:271] = 2
    cases["broad_regions_holes_neighbors"] = broad

    thin = np.full((160, 320), -1, dtype=np.int32)
    for i in range(148):
        x, y = 8 + i, 150 - i
        thin[y:y + 2, x:x + 2] = 0
        x2, y2 = 165 + i, 8 + i
        thin[y2:y2 + 3, x2:x2 + 3] = 1
    thin[79:82, 8:312] = 2
    thin[8:153, 79:81] = 3
    cases["thin_diagonals_crossings"] = thin

    isolated = np.full((160, 320), -1, dtype=np.int32)
    colors = (0, 1, 2, 3)
    for y in range(8, 153, 9):
        for x in range(8 + (y // 9 % 3), 313, 11):
            if ((x // 11) + (y // 9)) % 5:
                isolated[y, x] = colors[((x // 11) + (y // 9)) % len(colors)]
    cases["isolated_multicolor_pixels"] = isolated

    fragmented = np.full((160, 320), -1, dtype=np.int32)
    for row in range(4):
        for col in range(8):
            x, y = 8 + col * 39, 8 + row * 37
            color = colors[(row * 3 + col) % len(colors)]
            if (row + col) % 3 == 0:
                fragmented[y:y + 21, x:x + 21] = color
            elif (row + col) % 3 == 1:
                fragmented[y:y + 23, x:x + 23] = color
                fragmented[y + 7:y + 16, x + 7:x + 16] = -1
            else:
                for offset in range(0, 21):
                    px = x + offset
                    py = y + 20 - offset
                    if 0 <= px < fragmented.shape[1] and 0 <= py < fragmented.shape[0]:
                        fragmented[py:py + 3, px:px + 3] = color
    cases["fragmented_components_holes"] = fragmented
    return cases


def _stroke_points(stroke: dict[str, Any]) -> list[tuple[float, float]]:
    """Normalize supported benchmark stroke representations to XY points."""
    raw_points = stroke.get("points")
    if raw_points is not None:
        points = [
            (float(point["x"]), float(point["y"]))
            if isinstance(point, dict)
            else (float(point.x), float(point.y))
            for point in raw_points
        ]
    elif "start" in stroke and "end" in stroke:
        endpoints = (stroke["start"], stroke["end"])
        points = [
            (float(point["x"]), float(point["y"]))
            if isinstance(point, dict)
            else (float(point.x), float(point.y))
            for point in endpoints
        ]
    else:
        points = []
    return points


def _stroke_path_length(stroke: dict[str, Any]) -> float:
    points = _stroke_points(stroke)
    total = sum(
        math.hypot(x2 - x1, y2 - y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    )
    if stroke.get("closed") and len(points) > 2:
        total += math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1])
    return total


def _path_length(strokes: list[dict[str, Any]]) -> float:
    return sum(_stroke_path_length(stroke) for stroke in strokes)


def _zero_length_stroke_count(strokes: list[dict[str, Any]]) -> int:
    return sum(_stroke_path_length(stroke) == 0.0 for stroke in strokes)


def _fallback_path_length(strokes: list[dict[str, Any]]) -> float:
    return _path_length([s for s in strokes if s.get("role") == "boundary_fallback"])


def _bresenham_pixels(x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
    """Return integer pixel centers along a segment, including both endpoints."""
    points: list[tuple[int, int]] = []
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    error = dx - dy
    x, y = x1, y1
    while True:
        points.append((x, y))
        if x == x2 and y == y2:
            break
        doubled = 2 * error
        if doubled > -dy:
            error -= dy
            x += sx
        if doubled < dx:
            error += dx
            y += sy
    return points


def _coverage_path_metrics(strokes: list[dict[str, Any]], index_map: np.ndarray) -> dict[str, int]:
    """Classify centerline pixel visits against prior modeled brush footprints."""
    height, width = index_map.shape
    covered_by_color: dict[int, np.ndarray] = {}
    fresh_visits = revisit_visits = invalid_visits = 0
    for stroke in strokes:
        color = int(stroke["color_index"])
        covered = covered_by_color.setdefault(color, np.zeros((height, width), dtype=bool))
        points = _stroke_points(stroke)
        if not points:
            continue
        segments = list(zip(points, points[1:]))
        if len(points) == 1:
            segments = [(points[0], points[0])]
        elif stroke.get("closed") and len(points) > 2:
            segments.append((points[-1], points[0]))
        centerline: list[tuple[int, int]] = []
        for (x1, y1), (x2, y2) in segments:
            pixels = _bresenham_pixels(round(x1), round(y1), round(x2), round(y2))
            centerline.extend(pixels if not centerline else pixels[1:])
        for x, y in centerline:
            if not (0 <= x < width and 0 <= y < height) or int(index_map[y, x]) != color:
                invalid_visits += 1
            elif covered[y, x]:
                revisit_visits += 1
            else:
                fresh_visits += 1

        brush = int(stroke.get("brush_value", 1))
        xs = [round(point[0]) for point in points]
        ys = [round(point[1]) for point in points]
        # Planner strokes are horizontal; the rectangle also safely bounds
        # multi-point routes for this diagnostic approximation.
        for y in range(min(ys), max(ys) + 1):
            bounds = footprint_pixel_bounds(
                min(xs), max(xs), y, brush, 1.0, 1.0, width, height
            )
            if bounds is None:
                continue
            left, right, top, bottom = bounds
            region = index_map[top:bottom + 1, left:right + 1]
            covered[top:bottom + 1, left:right + 1] |= region == color

    return {
        "fresh_centerline_pixel_visits": fresh_visits,
        "revisit_centerline_pixel_visits": revisit_visits,
        "invalid_centerline_pixel_visits": invalid_visits,
    }


def run_sweep() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case_name, index_map in make_cases().items():
        baseline_fallback_path: float | None = None
        baseline_fallback_count: int | None = None
        case_rows: list[dict[str, Any]] = []
        for gap in GAPS:
            plan = build_interior_fill_plan(index_map, fallback_merge_gap_px=gap)
            strokes = plan["strokes"]
            fallback = [s for s in strokes if s.get("role") == "boundary_fallback"]
            fallback_path = _fallback_path_length(strokes)
            if gap == 0:
                baseline_fallback_path = fallback_path
                baseline_fallback_count = len(fallback)
            case_rows.append({
                "merge_gap_px": gap,
                "total_stroke_count": len(strokes),
                "interior_fill_stroke_count": len(strokes) - len(fallback),
                "fallback_stroke_count": len(fallback),
                "fallback_zero_length_stroke_count": _zero_length_stroke_count(fallback),
                "fallback_path_length_px": round(fallback_path, 3),
                "total_path_length_px": round(_path_length(strokes), 3),
                **_coverage_path_metrics(strokes, index_map),
                "zero_length_stroke_count": _zero_length_stroke_count(strokes),
                "fallback_stroke_reduction_vs_gap_0_percent": round(
                    100.0 * (baseline_fallback_count - len(fallback)) / baseline_fallback_count, 4
                ) if baseline_fallback_count else 0.0,
                "fallback_path_delta_vs_gap_0_px": round(
                    fallback_path - baseline_fallback_path, 3
                ) if baseline_fallback_path is not None else 0.0,
                "modeled_coverage_percent": plan["summary"]["coverage_percent"],
                "all_strokes_safe_for_color_map": plan["summary"]["all_strokes_safe_for_color_map"],
                "automatic_execution_allowed": plan["brush_configuration"]["automatic_execution_allowed"],
            })
        results.append({
            "case": case_name,
            "canvas": {"width": int(index_map.shape[1]), "height": int(index_map.shape[0])},
            "visible_pixel_count": int(np.count_nonzero(index_map >= 0)),
            "sweep": case_rows,
        })
    return {
        "schema_version": 1,
        "benchmark": "stage7_fallback_merge_gap_sweep",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "merge_gap_values_px": list(GAPS),
        "model_scope": "offline conservative rectangular footprint; not browser measurements",
        "cases": results,
        "interpretation_limits": [
            "Synthetic maps are deterministic stress cases, not a representative sample of all user images.",
            "A one-pixel or otherwise degenerate stroke can have zero centerline length while still counting as a stroke and potentially consuming an in-game action/resource.",
            "Fresh/revisit centerline visits use rasterized centerlines and modeled footprints; they are geometric proxies, not real brush or paint measurements.",
            "Fallback path delta is a geometric proxy for added centerline travel, not paint consumption.",
            "Paint and game-point estimates are intentionally not inferred from stroke count alone.",
            "A 100% modeled coverage result does not validate the real in-game brush footprint.",
            "Automatic execution remains disabled for all generated plans.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=APP_ROOT / "benchmark-results" / "stage7-fallback-merge-sweep.json")
    args = parser.parse_args()
    report = run_sweep()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Stage 7 fallback merge sweep (offline model)")
    for case in report["cases"]:
        print(f"\n{case['case']}")
        for row in case["sweep"]:
            print(
                f"gap={row['merge_gap_px']:>2}px fallback={row['fallback_stroke_count']:>5} "
                f"({row['fallback_stroke_reduction_vs_gap_0_percent']:>6.2f}% fewer), "
                f"path={row['fallback_path_length_px']:>9.1f}px "
                f"(delta {row['fallback_path_delta_vs_gap_0_px']:+.1f}px), "
                f"zero-length={row['fallback_zero_length_stroke_count']}, "
                f"coverage={row['modeled_coverage_percent']:.2f}%"
            )
    print(f"\nJSON report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
