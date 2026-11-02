#!/usr/bin/env python3
"""Research-only pixel geometry audit for INT-006 V1-V5 captures."""
from __future__ import annotations
import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any
import cv2
import numpy as np

PHASES = {"V1", "V2", "V3", "V4", "V5"}
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "data" / "results" / "brush_behavior_tests"
DEFAULT_OUTPUT = ROOT / "data" / "results" / "chalk_png_analysis_int006"

def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value

def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Cannot decode image: {path}")
    return image

def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.") or "run"

def geometry(stroke: dict[str, Any], sx: float, sy: float) -> dict[str, Any]:
    points = np.asarray([[float(p["x"]) * sx, float(p["y"]) * sy] for p in stroke["points"]], dtype=np.float64)
    closed = bool(stroke.get("closed", False))
    if closed and np.linalg.norm(points[-1] - points[0]) > 1e-6:
        points = np.vstack((points, points[0]))
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.r_[0.0, np.cumsum(lengths)]
    return {"name": str(stroke.get("name", "stroke")), "points": points, "closed": closed,
            "lengths": lengths, "cumulative": cumulative, "length": float(cumulative[-1])}

def project(pixels: np.ndarray, g: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(pixels)
    best = np.full(n, np.inf)
    along_best = np.zeros(n)
    cross_best = np.zeros(n)
    for i, length in enumerate(g["lengths"]):
        if length <= 1e-9:
            continue
        start = g["points"][i]
        unit = (g["points"][i + 1] - start) / length
        along = np.clip((pixels - start) @ unit, 0.0, length)
        delta = pixels - (start + along[:, None] * unit)
        d2 = np.einsum("ij,ij->i", delta, delta)
        update = d2 < best
        best[update] = d2[update]
        along_best[update] = g["cumulative"][i] + along[update]
        cross_best[update] = delta[update] @ np.array([-unit[1], unit[0]])
    return np.sqrt(best), along_best, cross_best

def sample_path(g: dict[str, Any], step: float) -> tuple[np.ndarray, np.ndarray]:
    s = np.arange(0.0, g["length"] + step * 0.5, step)
    if not len(s) or s[-1] < g["length"]:
        s = np.r_[s, g["length"]]
    pts = []
    for value in s:
        i = min(max(int(np.searchsorted(g["cumulative"], value, side="right") - 1), 0), len(g["lengths"]) - 1)
        length = g["lengths"][i]
        t = 0.0 if length <= 1e-9 else (value - g["cumulative"][i]) / length
        pts.append(g["points"][i] + t * (g["points"][i + 1] - g["points"][i]))
    return s, np.asarray(pts)

def false_runs(values: np.ndarray, excluded: np.ndarray) -> list[int]:
    runs, current = [], 0
    for value, skip in zip(values, excluded):
        if skip:
            if current:
                runs.append(current)
                current = 0
        elif not value:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs

def cursor_mask(before: np.ndarray, after: np.ndarray, endpoint: np.ndarray) -> np.ndarray:
    bright = ((after.astype(np.int16) - before.astype(np.int16) >= 8) & (after >= 245)).astype(np.uint8)
    count, labels, stats, centers = cv2.connectedComponentsWithStats(bright, connectivity=8)
    candidates = []
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        distance = float(np.linalg.norm(centers[label] - endpoint))
        if 6 <= area <= 2500 and distance <= 36:
            candidates.append((distance, label))
    result = np.zeros(before.shape, dtype=np.uint8)
    if candidates:
        _, label = min(candidates)
        result[labels == label] = 255
        result = cv2.dilate(result, np.ones((5, 5), np.uint8), iterations=1)
    return result

def capture_errors(manifest: dict[str, Any], monitor: dict[str, Any], expected: int) -> list[str]:
    errors = []
    execution = manifest.get("execution_report") or {}
    summary = manifest.get("game_monitor_summary") or {}
    chalk = summary.get("chalk") or {}
    if execution.get("status") != "completed": errors.append("executor_not_completed")
    if int(execution.get("completed_strokes", -1)) != expected: errors.append("stroke_count_mismatch")
    if (manifest.get("monitor_capture") or {}).get("status") != "saved": errors.append("monitor_capture_not_saved")
    if chalk.get("status") != "exact": errors.append("chalk_not_exact")
    if summary.get("point_delta_matches_chalk") is not True: errors.append("chalk_delta_mismatch")
    if (summary.get("observed_brush_radii") or []) not in ([10], [10.0]): errors.append("radius_not_single_10")
    for key in ("dropped_events", "monitor_dropped_events", "monitor_buffer_dropped_events_delta",
                "monitor_error_count_delta", "bridge_send_failures_delta", "collector_sequence_gap_count"):
        if int(summary.get(key, 0) or 0) != 0: errors.append(f"{key}_nonzero")
    pre, post = monitor.get("pre_test_snapshot") or {}, monitor.get("post_test_snapshot") or {}
    if not pre.get("isExact") or not post.get("isExact"): errors.append("pre_post_not_exact")
    try:
        delta = int(post["pointCount"]) - int(pre["pointCount"])
        if delta != int(chalk["consumed_points"]): errors.append("monitor_chalk_delta_mismatch")
    except (KeyError, TypeError, ValueError):
        errors.append("point_count_missing")
    return errors

def stroke_metrics(g: dict[str, Any], assigned: np.ndarray, candidate_count: int, ambiguous_count: int,
                   cursor: np.ndarray, ambiguous: np.ndarray, scale: float, radius: float) -> dict[str, Any]:
    y, x = np.where(assigned > 0)
    pixels = np.c_[x, y].astype(np.float64) if len(x) else np.empty((0, 2))
    _, along, cross = project(pixels, g) if len(x) else (np.empty(0), np.empty(0), np.empty(0))
    bin_size = max(1.0, scale)
    bins = np.clip((along / bin_size).astype(int), 0, max(0, math.ceil(g["length"] / bin_size) - 1)) if len(x) else np.empty(0, int)
    widths, offsets = [], []
    for b in range(max(1, math.ceil(g["length"] / bin_size))):
        values = cross[bins == b]
        if len(values) >= 3:
            widths.append(float(np.quantile(values, .95) - np.quantile(values, .05)))
            offsets.append(float(np.median(values)))
    s, points = sample_path(g, max(.5, scale * .5))
    px = np.clip(np.rint(points[:, 0]).astype(int), 0, assigned.shape[1] - 1)
    py = np.clip(np.rint(points[:, 1]).astype(int), 0, assigned.shape[0] - 1)
    cursor_samples = cursor[py, px] > 0
    ambiguous_samples = ambiguous[py, px] > 0
    excluded = cursor_samples | ambiguous_samples
    if np.any(assigned):
        dmap = cv2.distanceTransform((assigned == 0).astype(np.uint8), cv2.DIST_L2, 5)
        distances = dmap[py, px]
    else:
        distances = np.full(len(points), np.inf)
    tolerance = max(2.0, radius * scale * .35)
    covered = distances <= tolerance
    gaps = false_runs(covered, excluded)
    evaluable = ~excluded
    start = float(distances[0]) if len(distances) and not excluded[0] and np.isfinite(distances[0]) else None
    end = float(distances[-1]) if len(distances) and not excluded[-1] and np.isfinite(distances[-1]) else None
    abs_offsets = np.abs(offsets)
    width_median = float(np.median(widths)) if widths else None
    width_std = float(np.std(widths)) if widths else None
    components = int(cv2.connectedComponents((assigned > 0).astype(np.uint8), connectivity=8)[0] - 1) if np.any(assigned) else 0
    return {
        "stroke_name": g["name"], "closed": g["closed"], "planned_length_logical": round(g["length"] / scale, 4),
        "ink_pixels_assigned": int(len(x)), "candidate_ink_pixels": candidate_count,
        "ambiguous_ink_pixels": ambiguous_count,
        "ambiguous_fraction": round(ambiguous_count / candidate_count, 5) if candidate_count else None,
        "coverage_fraction": round(float(np.mean(covered[evaluable])), 5) if np.any(evaluable) else None,
        "evaluable_path_samples": int(np.count_nonzero(evaluable)),
        "cursor_excluded_path_samples": int(np.count_nonzero(cursor_samples)),
        "ambiguous_excluded_path_samples": int(np.count_nonzero(ambiguous_samples)),
        "gap_count": len(gaps),
        "max_gap_logical": round(max(gaps, default=0) * (s[1] - s[0]) / scale, 4) if len(s) > 1 else 0.0,
        "start_center_distance_logical": round(start / scale, 4) if start is not None else None,
        "end_center_distance_logical": round(end / scale, 4) if end is not None else None,
        "centerline_deviation_median_logical": round(float(np.median(abs_offsets)) / scale, 4) if len(abs_offsets) else None,
        "centerline_deviation_p95_logical": round(float(np.quantile(abs_offsets, .95)) / scale, 4) if len(abs_offsets) else None,
        "centerline_deviation_max_logical": round(float(np.max(abs_offsets)) / scale, 4) if len(abs_offsets) else None,
        "coverage_width_median_logical": round(width_median / scale, 4) if width_median is not None else None,
        "coverage_width_p05_logical": round(float(np.quantile(widths, .05)) / scale, 4) if widths else None,
        "coverage_width_p95_logical": round(float(np.quantile(widths, .95)) / scale, 4) if widths else None,
        "coverage_width_cv": round(width_std / width_median, 5) if width_std is not None and width_median else None,
        "mask_component_count": components,
        "closure_seam_center_distance_logical": round(start / scale, 4) if g["closed"] and start is not None else None,
        "closure_seam_covered": (bool(start <= tolerance) if g["closed"] and start is not None else None),
    }

def parallel_pairs(geometries: list[dict[str, Any]], masks: list[np.ndarray], scale: float) -> list[dict[str, Any]]:
    result = []
    for i, a in enumerate(geometries):
        if len(a["points"]) != 2 or a["lengths"][0] <= 1: continue
        ua = (a["points"][1] - a["points"][0]) / a["lengths"][0]
        for j in range(i + 1, len(geometries)):
            b = geometries[j]
            if len(b["points"]) != 2 or b["lengths"][0] <= 1: continue
            ub = (b["points"][1] - b["points"][0]) / b["lengths"][0]
            angle = math.degrees(math.acos(float(np.clip(abs(np.dot(ua, ub)), -1, 1))))
            if angle > 5: continue
            separation = abs(float(np.dot(b["points"][0] - a["points"][0], [-ua[1], ua[0]])))
            ma, mb = masks[i], masks[j]
            overlap = int(np.count_nonzero((ma > 0) & (mb > 0)))
            if np.any(ma) and np.any(mb):
                dm = cv2.distanceTransform((mb == 0).astype(np.uint8), cv2.DIST_L2, 5)
                distance = float(np.min(dm[ma > 0]))
                touching = bool(distance <= max(5.0, scale * 3.0))
            else:
                touching, distance = False, None
            result.append({"stroke_a": a["name"], "stroke_b": b["name"],
                "axis_separation_logical": round(separation / scale, 4), "axis_angle_difference_deg": round(angle, 4),
                "assigned_mask_overlap_pixels": overlap, "assigned_ink_masks_touch_or_merge": touching,
                "minimum_ink_mask_distance_px": round(distance, 4) if distance is not None else None,
                "minimum_ink_mask_distance_logical": round(distance / scale, 4) if distance is not None else None})
    return result

def analyse_capture(folder: Path, out: Path) -> dict[str, Any]:
    manifest, monitor = read_json(folder / "experiment.json"), read_json(folder / "monitor_report.json")
    matrix = manifest.get("chalk_experiment_matrix") or {}
    phase = matrix.get("phase_id")
    if phase not in PHASES or not str(matrix.get("scenario_id", "")).startswith("int006_"):
        raise ValueError("Not an INT-006 V1-V5 manifest")
    raw_strokes = matrix.get("planned_strokes") or []
    expected = int(matrix.get("expected_strokes", len(raw_strokes)))
    if len(raw_strokes) != expected or not raw_strokes:
        raise ValueError("planned_strokes count does not match expected_strokes")
    before, after = read_image(folder / "before_clear-board.png"), read_image(folder / "after_draw-board.png")
    if before.shape != after.shape: raise ValueError("before/after board dimensions differ")
    pre = monitor.get("pre_test_snapshot") or {}
    logical_w, logical_h = float(pre.get("logicalWidth") or 460), float(pre.get("logicalHeight") or 240)
    h, w = before.shape[:2]
    sx, sy = w / logical_w, h / logical_h
    scale = (sx + sy) / 2
    before_g = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_g = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
    gs = [geometry(s, sx, sy) for s in raw_strokes]
    radius = float(matrix.get("requested_radius", 10) or 10)
    corridor = max(7.0, radius * scale * .65 + 1.0)
    cursor = cursor_mask(before_g, after_g, gs[-1]["points"][-1])
    ink = (((before_g.astype(np.int16) - after_g.astype(np.int16)) >= 22) & (after_g <= 205)).astype(np.uint8) * 255
    ink[cursor > 0] = 0
    y, x = np.where(ink > 0)
    pixels = np.c_[x, y].astype(np.float64) if len(x) else np.empty((0, 2))
    projections = [project(pixels, g) if len(x) else (np.empty(0), np.empty(0), np.empty(0)) for g in gs]
    dists = np.vstack([p[0] for p in projections]).T if len(x) else np.empty((0, len(gs)))
    if len(x):
        order = np.argsort(dists, axis=1)
        nearest = order[:, 0]
        best = dists[np.arange(len(x)), nearest]
        second = dists[np.arange(len(x)), order[:, 1]] if len(gs) > 1 else np.full(len(x), np.inf)
        in_corridor = best <= corridor
        ambiguous_pixels = in_corridor & ((second - best) <= max(2.0, scale * 1.5))
    else:
        nearest, in_corridor, ambiguous_pixels = np.empty(0, int), np.empty(0, bool), np.empty(0, bool)
    ambiguous_mask = np.zeros((h, w), np.uint8)
    if len(x) and np.any(ambiguous_pixels):
        ambiguous_mask[y[ambiguous_pixels], x[ambiguous_pixels]] = 255
        ambiguous_mask = cv2.dilate(ambiguous_mask, np.ones((3, 3), np.uint8), iterations=1)
    assigned_masks, candidate_masks, stroke_rows = [], [], []
    for i, g in enumerate(gs):
        candidate = (dists[:, i] <= corridor) if len(x) else np.empty(0, bool)
        assigned = ((nearest == i) & in_corridor & ~ambiguous_pixels) if len(x) else np.empty(0, bool)
        cm, am = np.zeros((h, w), np.uint8), np.zeros((h, w), np.uint8)
        if len(x) and np.any(candidate): cm[y[candidate], x[candidate]] = 255
        if len(x) and np.any(assigned): am[y[assigned], x[assigned]] = 255
        candidate_masks.append(cm); assigned_masks.append(am)
        stroke_rows.append(stroke_metrics(g, am, int(np.count_nonzero(candidate)),
            int(np.count_nonzero(candidate & ambiguous_pixels)) if len(x) else 0,
            cursor, ambiguous_mask, scale, radius))
    pairs = parallel_pairs(gs, assigned_masks, scale)
    errors = capture_errors(manifest, monitor, expected)
    summary = {
        "experiment_id": manifest.get("experiment_id"), "experiment_dir": str(folder),
        "phase_id": phase, "scenario_id": matrix.get("scenario_id"), "repeat_index": matrix.get("repeat_index"),
        "sampling_profile": {k: (matrix.get("executor_parameters") or {}).get(k) for k in ("point_step_px", "point_delay_ms")},
        "brush_radius": radius, "exact_chalk": (manifest.get("game_monitor_summary") or {}).get("chalk", {}).get("consumed_points"),
        "image_size": {"width": w, "height": h}, "logical_board_size": {"width": logical_w, "height": logical_h},
        "image_to_logical_scale": {"x": round(sx, 6), "y": round(sy, 6)},
        "transform_warning": "non_uniform_scale" if abs(sx - sy) / scale > .03 else None,
        "ink_mask_pixels": int(np.count_nonzero(ink)),
        "unassigned_ink_pixels": int(np.count_nonzero(ink) - np.count_nonzero(in_corridor)) if len(x) else int(np.count_nonzero(ink)),
        "ambiguous_ink_pixels": int(np.count_nonzero(ambiguous_pixels)),
        "cursor_detected_near_final_endpoint": bool(np.any(cursor)),
        "cursor_exclusion_pixels": int(np.count_nonzero(cursor)),
        "capture_valid": not errors, "capture_errors": errors, "strokes": stroke_rows, "parallel_pairs": pairs,
    }
    out.mkdir(parents=True, exist_ok=True)
    name = safe_name(str(manifest.get("experiment_id") or folder.name))
    overlay = after.copy()
    layer = overlay.copy(); layer[ink > 0] = (220, 40, 190)
    overlay = cv2.addWeighted(overlay, .72, layer, .28, 0)
    if len(x) and np.any(ambiguous_pixels): overlay[y[ambiguous_pixels], x[ambiguous_pixels]] = (0, 220, 255)
    overlay[cursor > 0] = (255, 180, 0)
    for g in gs:
        pts = np.rint(g["points"]).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(overlay, [pts], g["closed"], (40, 220, 40), 1, cv2.LINE_AA)
        cv2.putText(overlay, g["name"][:20], tuple(pts[0, 0]), cv2.FONT_HERSHEY_SIMPLEX, .35, (20, 80, 20), 1)
    cv2.imwrite(str(out / f"{name}_overlay.png"), overlay)
    cv2.imwrite(str(out / f"{name}_ink-mask.png"), ink)
    (out / f"{name}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary

def run(results_dir: Path, out: Path, expected_runs: int = 45) -> dict[str, Any]:
    folders = []
    for path in sorted(results_dir.rglob("experiment.json")):
        try:
            m = read_json(path); matrix = m.get("chalk_experiment_matrix") or {}
            if matrix.get("phase_id") in PHASES and str(matrix.get("scenario_id", "")).startswith("int006_"):
                folders.append(path.parent)
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    rows, failures = [], []
    for folder in folders:
        try: rows.append(analyse_capture(folder, out))
        except Exception as exc: failures.append({"experiment_dir": str(folder), "error": f"{type(exc).__name__}: {exc}"})
    cells = [(r["phase_id"], (r["sampling_profile"] or {}).get("point_step_px"),
              (r["sampling_profile"] or {}).get("point_delay_ms"), r.get("repeat_index")) for r in rows]
    expected_cells = {(p, s, d, n) for p in PHASES for s, d in ((2, 10), (4, 5), (4, 10)) for n in (1, 2, 3)}
    counts = {p: sum(r["phase_id"] == p for r in rows) for p in sorted(PHASES)}
    report = {
        "schema_version": 1, "analysis": "INT-006 V1-V5 differential PNG geometry audit",
        "expected_runs": expected_runs, "discovered_runs": len(folders), "analysed_runs": len(rows),
        "capture_valid_runs": sum(r["capture_valid"] for r in rows),
        "capture_invalid_runs": sum(not r["capture_valid"] for r in rows), "phase_counts": counts,
        "duplicate_matrix_cells": [list(c) for c in set(c for c in cells if cells.count(c) > 1)],
        "missing_matrix_cells": [list(c) for c in sorted(expected_cells - set(cells))],
        "unexpected_matrix_cells": [list(c) for c in sorted(set(cells) - expected_cells)],
        "batch_failures": failures,
        "method": {
            "reference": "before_clear-board.png", "observed": "after_draw-board.png",
            "mask": "darkening-only differential, luminance delta >= 22 and observed luminance <= 205",
            "geometry_source": "experiment.json chalk_experiment_matrix.planned_strokes",
            "coordinates": "logical DrawingPlan mapped using board image dimensions / Monitor logicalWidth and logicalHeight",
            "cursor": "bright cursor component near final planned endpoint excluded with a 5x5 dilation",
            "ambiguous": "pixels equidistant between stroke corridors excluded from per-stroke metrics",
            "warning": "Review diagnostic overlays; dark cursor outlines may remain if cursor body detection misses them.",
        },
        "metric_notes": [
            "Image metrics are diagnostics, not exact game acceptance telemetry.",
            "Width depends on the differential threshold and anti-aliasing.",
            "Monitor coalesced coordinates are not used to reconstruct planned geometry.",
            "No automatic pass/fail quality tolerance is imposed; thresholds must be reviewed before closing the pixel gate.",
        ],
        "runs": rows,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stroke_fields = ["experiment_id", "phase_id", "scenario_id", "repeat_index", "point_step_px", "point_delay_ms",
        "exact_chalk", "capture_valid", "stroke_name", "planned_length_logical", "ink_pixels_assigned",
        "ambiguous_fraction", "coverage_fraction", "gap_count", "max_gap_logical",
        "centerline_deviation_median_logical", "centerline_deviation_p95_logical", "centerline_deviation_max_logical",
        "coverage_width_median_logical", "coverage_width_p05_logical", "coverage_width_p95_logical",
        "coverage_width_cv", "mask_component_count", "closure_seam_center_distance_logical", "closure_seam_covered"]
    with (out / "per_stroke_metrics.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=stroke_fields, extrasaction="ignore"); writer.writeheader()
        for r in rows:
            profile = r["sampling_profile"]
            for stroke in r["strokes"]:
                writer.writerow({"experiment_id": r["experiment_id"], "phase_id": r["phase_id"],
                    "scenario_id": r["scenario_id"], "repeat_index": r["repeat_index"],
                    "point_step_px": profile["point_step_px"], "point_delay_ms": profile["point_delay_ms"],
                    "exact_chalk": r["exact_chalk"], "capture_valid": r["capture_valid"], **stroke})
    pair_fields = ["experiment_id", "phase_id", "scenario_id", "repeat_index", "point_step_px",
        "point_delay_ms", "capture_valid", "stroke_a", "stroke_b", "axis_separation_logical",
        "axis_angle_difference_deg", "assigned_mask_overlap_pixels", "assigned_ink_masks_touch_or_merge",
        "minimum_ink_mask_distance_px", "minimum_ink_mask_distance_logical"]
    with (out / "parallel_pair_metrics.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=pair_fields, extrasaction="ignore"); writer.writeheader()
        for r in rows:
            profile = r["sampling_profile"]
            for pair in r["parallel_pairs"]:
                writer.writerow({"experiment_id": r["experiment_id"], "phase_id": r["phase_id"],
                    "scenario_id": r["scenario_id"], "repeat_index": r["repeat_index"],
                    "point_step_px": profile["point_step_px"], "point_delay_ms": profile["point_delay_ms"],
                    "capture_valid": r["capture_valid"], **pair})
    return report

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_dir", nargs="?", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-runs", type=int, default=45)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    if not args.results_dir.exists(): parser.error(f"Results directory does not exist: {args.results_dir}")
    report = run(args.results_dir, args.output_dir, args.expected_runs)
    keys = ("expected_runs", "discovered_runs", "analysed_runs", "capture_valid_runs",
            "capture_invalid_runs", "phase_counts", "duplicate_matrix_cells", "missing_matrix_cells",
            "unexpected_matrix_cells", "batch_failures")
    print(json.dumps({k: report[k] for k in keys}, ensure_ascii=False, indent=2))
    if report["batch_failures"] or report["duplicate_matrix_cells"] or report["unexpected_matrix_cells"] or report["capture_invalid_runs"]:
        return 2
    if not args.allow_incomplete and (report["discovered_runs"] != args.expected_runs or report["missing_matrix_cells"]):
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
