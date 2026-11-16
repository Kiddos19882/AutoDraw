#!/usr/bin/env python3
"""ENGINE-001 V43-P4.1 full source-color replacement candidate, MODEL_ONLY.

OpenCV stroke footprints only rank candidates, not native Egret brush evidence.
This module never sends strokes to Stage6 and does not measure game CHALK.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import SOURCE_SHA, sha
from run_engine001_shape_adaptive_fill_v43p1 import analyze_index_map

EXPERIMENT = "ENGINE001_V43P4_FULL_ADAPTIVE_FILL_REPLACEMENT_P4_1_MODEL_ONLY"
WIDTHS = (10, 6, 4, 2)
COLORS = (4, 5, 6, 7)
ANGLES = (0, 30, 45, 60, 90, 120, 135, 150)
MIN_NEW = {10: 12, 6: 8, 4: 6, 2: 1}
MAX_STROKES = 3000
MAX_VERTICES = 5900
FROZEN_DETAILS = 410
FROZEN_DETAIL_VERTICES = 1792
ROI_X0 = 155
SHAPE = (240, 150)
MAX_LEAKAGE_LOGICAL_PX = 3


def checked_labels(indexes: np.ndarray) -> np.ndarray:
    if (not isinstance(indexes, np.ndarray) or indexes.shape != SHAPE
            or indexes.dtype.kind not in "iu" or np.any(indexes < 0)
            or np.any(indexes > 7)):
        raise ValueError("P4 invalid pinned source labels")
    return indexes


def candidates_for_width(mask: np.ndarray, width: int):
    """Sweep in eight orientations; raster footprint is a model, NOT Egret."""
    if width not in WIDTHS or mask.shape != SHAPE or mask.dtype != np.bool_:
        raise ValueError("P4 invalid owner mask or nominal width")
    height, cols = mask.shape
    distance = cv2.distanceTransform(
        np.pad(mask.astype(np.uint8), 1), cv2.DIST_L2,
        cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
    if width == 2:
        centers = cv2.dilate(mask.astype(np.uint8),
                             np.ones((3, 3), np.uint8)) != 0
    else:
        centers = distance >= width / 2.0 + 0.5
    distance_out = cv2.distanceTransform(
        (~mask).astype(np.uint8), cv2.DIST_L2,
        cv2.DIST_MASK_PRECISE)
    corners = np.array(((0, 0), (cols - 1, 0),
                        (0, height - 1), (cols - 1, height - 1)))
    results = []
    seen = set()

    def append_run(run):
        if len(run) < 2 or run[0] == run[-1]:
            return
        a, b = run[0], run[-1]
        key = (width, a, b)
        if key in seen:
            return
        seen.add(key)
        margin = width // 2 + 2
        left, right = max(0, min(a[0], b[0]) - margin), min(
            cols, max(a[0], b[0]) + margin + 1)
        top, bottom = max(0, min(a[1], b[1]) - margin), min(
            height, max(a[1], b[1]) + margin + 1)
        footprint = np.zeros((bottom - top, right - left), np.uint8)
        cv2.line(footprint, (a[0] - left, a[1] - top),
                 (b[0] - left, b[1] - top), 255, width, cv2.LINE_8)
        y, x = np.nonzero(footprint)
        yy, xx = y + top, x + left
        if np.any(distance_out[yy, xx] > MAX_LEAKAGE_LOGICAL_PX):
            return
        owner_pixels = mask[yy, xx]
        flat = (yy[owner_pixels] * cols + xx[owner_pixels]).astype(np.int32)
        if len(flat) >= 2:
            results.append((width, a, b, flat, len(xx)))

    for angle in ANGLES:
        theta = math.radians(angle)
        direction = np.array((math.cos(theta), math.sin(theta)))
        normal = np.array((-direction[1], direction[0]))
        major = corners @ direction
        minor = corners @ normal
        for lateral in np.arange(math.floor(minor.min()) - 1,
                                 math.ceil(minor.max()) + 2, 1.0):
            run = []
            last = None
            for along in np.arange(math.floor(major.min()) - 1,
                                   math.ceil(major.max()) + 2, 1.0):
                q = along * direction + lateral * normal
                x, y = int(round(float(q[0]))), int(round(float(q[1])))
                if not (0 <= x < cols and 0 <= y < height and centers[y, x]):
                    if run:
                        append_run(run)
                        run = []
                elif last != (x, y):
                    run.append((x, y))
                last = (x, y)
            if run:
                append_run(run)
    return results


def source_plan(indexes: np.ndarray, max_strokes: int = MAX_STROKES,
                max_vertices: int = MAX_VERTICES) -> dict:
    """Whole new paint, no frozen contours synthesized; fail closed on budget."""
    checked_labels(indexes)
    if (type(max_strokes) is not int or type(max_vertices) is not int
            or max_strokes < FROZEN_DETAILS or
            max_vertices < FROZEN_DETAIL_VERTICES):
        raise ValueError("P4 invalid resource caps")
    strokes = []
    diagnostics = {}
    for owner in COLORS:
        mask = indexes == owner
        remaining = mask.reshape(-1).copy()
        initial = int(np.count_nonzero(remaining))
        if initial == 0:
            raise ValueError("P4 missing required source owner")
        by_width = Counter()
        candidates_count = 0
        for width in WIDTHS:
            candidates = candidates_for_width(mask, width)
            candidates_count += len(candidates)
            heap = []
            for i, candidate in enumerate(candidates):
                gain = int(np.count_nonzero(remaining[candidate[3]]))
                heapq.heappush(heap, (-gain, i, gain))
            while heap:
                _, k, previous = heapq.heappop(heap)
                candidate = candidates[k]
                gain = int(np.count_nonzero(remaining[candidate[3]]))
                if gain != previous:
                    heapq.heappush(heap, (-gain, k, gain))
                    continue
                if gain < MIN_NEW[width]:
                    break
                a, b = candidate[1:3]
                strokes.append({
                    "strokeId": f"p4-b0-{owner}-{len(strokes):05d}",
                    "colorIndex": owner, "width": width,
                    "points": [{"x": a[0] + ROI_X0, "y": a[1]},
                               {"x": b[0] + ROI_X0, "y": b[1]}],
                })
                remaining[candidate[3]] = False
                by_width[width] += 1
                if (len(strokes) + FROZEN_DETAILS > max_strokes or
                    len(strokes) * 2 + FROZEN_DETAIL_VERTICES > max_vertices):
                    raise ValueError("BLOCKED_RESOURCE: P4 source planner exceeds caps")
        missed = int(np.count_nonzero(remaining))
        diagnostics[str(owner)] = {
            "source_pixels": initial, "model_missing_pixels": missed,
            "model_coverage": (initial - missed) / initial,
            "strokes": sum(by_width.values()),
            "widths": {str(w): by_width[w] for w in WIDTHS},
            "candidates_considered": candidates_count,
        }
    return {
        "experiment": EXPERIMENT, "candidate": "B0_SOURCE_ONLY",
        "source_shape_hw": list(SHAPE),
        "allowed_nominal_widths_desc": list(WIDTHS),
        "orientation_angles_deg": list(ANGLES),
        "original_paint_retained": 0, "paint_strokes": len(strokes),
        "detail_strokes_required_unchanged": FROZEN_DETAILS,
        "details_exact_verified": False,
        "synthetic_vertices_with_frozen_detail_NOT_CHALK": (
            len(strokes) * 2 + FROZEN_DETAIL_VERTICES),
        "max_total_strokes": max_strokes,
        "max_total_synthetic_vertices": max_vertices,
        "source_model_diagnostics_NOT_EGRET": diagnostics,
        "paint": strokes,
        "model_coverage_is_not_native_quality": True,
        "native_E3": "NOT_RUN", "live_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN", "exact_CHALK": None,
        "production_accepted": False, "safe_to_execute": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("P4 refuses overwrite of any previous source candidate")
    if sha(args.source) != SOURCE_SHA:
        raise ValueError("P4 frozen source SHA256 drift")
    indexes = original_labels(args.source)[::3, ::3][:, 155:305].copy()
    geometry = analyze_index_map(indexes)
    plan = source_plan(indexes)
    plan["source_sha256"] = SOURCE_SHA
    plan["source_labels_sha256"] = hashlib.sha256(indexes.tobytes()).hexdigest()
    plan["source_components"] = geometry["per_color"]
    plan["selection_thresholds"] = {
        "minimum_new_source_pixels_per_stroke_by_width": MIN_NEW,
        "maximum_model_exterior_distance_from_own_source_class": MAX_LEAKAGE_LOGICAL_PX,
        "source_proxy_only": True,
    }
    args.output.mkdir(parents=True)
    (args.output / "candidate-b0-source.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    print(json.dumps({
        "paint_strokes": plan["paint_strokes"],
        "synthetic_vertices_NOT_CHALK": plan[
            "synthetic_vertices_with_frozen_detail_NOT_CHALK"],
        "source_model_coverage_NOT_NATIVE": {
            k: v["model_coverage"] for k, v in
            plan["source_model_diagnostics_NOT_EGRET"].items()},
        "safe_to_execute": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
