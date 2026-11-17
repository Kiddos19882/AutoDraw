#!/usr/bin/env python3
"""V43-P4 B1 owner-constrained source-only correction candidate, not Egret.

B0 and frozen A are never overwritten. Penalty rule preregistered in
ENGINE001_V43P4_B1_OWNER_CONSTRAINED_PROTOCOL_2026-11-17.md.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from run_engine001_full_adaptive_fill_v43p4 import (
    ANGLES, COLORS, FROZEN_DETAILS, FROZEN_DETAIL_VERTICES, MAX_STROKES,
    MAX_VERTICES, MIN_NEW, ROI_X0, SHAPE, SOURCE_SHA, WIDTHS,
    candidates_for_width, checked_labels, sha,
)
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_shape_adaptive_fill_v43p1 import analyze_index_map

EXPERIMENT = "ENGINE001_V43P4_B1_OWNER_CONSTRAINED_FILL_SOURCE_ONLY"
FOREIGN_PENALTY = 2.0
OTHER_PENALTY = 0.5


def candidate_penalty(indexes: np.ndarray, owner: int, candidate: tuple):
    """Fixed OpenCV model penalty and width2 owner-center filter, not ink truth."""
    width, a, b, own_pixels, _ = candidate
    if width not in WIDTHS or owner not in COLORS:
        raise ValueError("B1 invalid owner/width")
    ax, ay = a
    bx, by = b
    margin = width // 2 + 2
    left = max(0, min(ax, bx) - margin)
    right = min(SHAPE[1], max(ax, bx) + margin + 1)
    top = max(0, min(ay, by) - margin)
    bottom = min(SHAPE[0], max(ay, by) + margin + 1)
    roi = np.zeros((bottom - top, right - left), dtype=np.uint8)
    p0, p1 = (ax-left, ay-top), (bx-left, by-top)
    if width == 2:
        center = np.zeros_like(roi)
        cv2.line(center, p0, p1, 255, 1, cv2.LINE_8)
        yy, xx = np.nonzero(center)
        if not len(xx) or not np.all(indexes[yy+top, xx+left] == owner):
            return None
    cv2.line(roi, p0, p1, 255, width, cv2.LINE_8)
    yy, xx = np.nonzero(roi)
    under = indexes[yy+top, xx+left]
    foreign = int(np.count_nonzero(np.isin(under, COLORS) & (under != owner)))
    other = int(np.count_nonzero(~np.isin(under, COLORS)))
    if len(own_pixels) < 2:
        raise ValueError("B1 source candidate lacks owner support")
    return foreign, other


def b1_source_plan(indexes: np.ndarray, max_strokes: int = MAX_STROKES,
                   max_vertices: int = MAX_VERTICES) -> dict:
    checked_labels(indexes)
    if (type(max_strokes) is not int or type(max_vertices) is not int
            or max_strokes < FROZEN_DETAILS
            or max_vertices < FROZEN_DETAIL_VERTICES):
        raise ValueError("B1 invalid resource caps")
    strokes = []
    stats = {}
    for owner in COLORS:
        mask = indexes == owner
        remaining = mask.ravel().copy()
        if not remaining.any():
            raise ValueError("B1 missing required owner")
        source_count = int(remaining.sum())
        selected = Counter()
        rejected_center = 0
        candidates_total = 0
        total_penalized_foreign = 0
        total_penalized_other = 0
        for width in WIDTHS:
            candidates = candidates_for_width(mask, width)
            candidates_total += len(candidates)
            pool = []
            for candidate in candidates:
                penalty = candidate_penalty(indexes, owner, candidate)
                if penalty is None:
                    rejected_center += 1
                    continue
                pool.append((candidate, penalty))
            heap = []
            for i, (candidate, (foreign, other)) in enumerate(pool):
                gain = int(np.count_nonzero(remaining[candidate[3]]))
                score = gain - FOREIGN_PENALTY * foreign - OTHER_PENALTY * other
                heapq.heappush(heap, (-score, i, gain))
            while heap:
                negative_score, index, prev_gain = heapq.heappop(heap)
                candidate, (foreign, other) = pool[index]
                gain = int(np.count_nonzero(remaining[candidate[3]]))
                score = gain - FOREIGN_PENALTY * foreign - OTHER_PENALTY * other
                if gain != prev_gain:
                    heapq.heappush(heap, (-score, index, gain))
                    continue
                if score <= 0:
                    break
                if gain < MIN_NEW[width]:
                    continue
                point0, point1 = candidate[1:3]
                stroke = {
                    "strokeId": f"p4-b1-{owner}-{len(strokes):05d}",
                    "colorIndex": owner,
                    "width": width,
                    "points": [
                        {"x": int(point0[0] + ROI_X0), "y": int(point0[1])},
                        {"x": int(point1[0] + ROI_X0), "y": int(point1[1])},
                    ],
                }
                strokes.append(stroke)
                remaining[candidate[3]] = False
                selected[width] += 1
                total_penalized_foreign += foreign
                total_penalized_other += other
                if (len(strokes) + FROZEN_DETAILS > max_strokes or
                    len(strokes) * 2 + FROZEN_DETAIL_VERTICES > max_vertices):
                    raise ValueError("BLOCKED_RESOURCE B1 exceeds frozen caps")
        missed = int(remaining.sum())
        stats[str(owner)] = {
            "source_pixels": source_count, "source_model_missing": missed,
            "source_model_coverage_NOT_NATIVE": (source_count-missed) / source_count,
            "paint_strokes": sum(selected.values()),
            "per_width": {str(w): selected[w] for w in WIDTHS},
            "width2_center_rejected_candidates": rejected_center,
            "model_foreign_footprint_sum_NOT_NATIVE": total_penalized_foreign,
            "model_other_footprint_sum_NOT_NATIVE": total_penalized_other,
            "total_candidate_paths": candidates_total,
        }
    return {
        "experiment": EXPERIMENT, "candidate": "B1_SOURCE_ONLY",
        "source_shape_hw": list(SHAPE), "width_order": list(WIDTHS),
        "angles_deg": list(ANGLES),
        "fixed_candidate_score": {
            "uncovered_own_gain_factor": 1.0,
            "foreign_required_penalty": FOREIGN_PENALTY,
            "other_class_penalty": OTHER_PENALTY,
            "min_new_by_width": {str(w): MIN_NEW[w] for w in WIDTHS},
            "width2_centerline_all_owner_required": True,
        },
        "source_model_diagnostics_NOT_EGRET": stats,
        "original_A_paint_retained": 0, "original_B0_paint_retained": 0,
        "detail_410_exact_required": True,
        "detail_verified_at_source_stage": False,
        "paint_count": len(strokes),
        "projected_total_strokes": len(strokes) + FROZEN_DETAILS,
        "projected_synthetic_vertices_NOT_CHALK": (
            2*len(strokes) + FROZEN_DETAIL_VERTICES),
        "paint": strokes, "safe_to_execute": False,
        "E3_native": "NOT_RUN", "E4_game": "NOT_RUN",
        "E5_independent": "NOT_RUN", "exact_CHALK": None,
        "production_accepted": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("B1 refuse overwrite of any experiment output")
    if sha(args.source) != SOURCE_SHA:
        raise ValueError("B1 source SHA drift")
    labels = original_labels(args.source)[::3, ::3][:, ROI_X0:ROI_X0+SHAPE[1]].copy()
    plan = b1_source_plan(labels)
    plan["source_sha256"] = SOURCE_SHA
    plan["source_labels_sha256"] = hashlib.sha256(labels.tobytes()).hexdigest()
    plan["components_by_owner"] = analyze_index_map(labels)["per_color"]
    args.output.mkdir(parents=True)
    (args.output / "candidate-b1-source.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({
        "paint": plan["paint_count"],
        "projected_total": plan["projected_total_strokes"],
        "synthetic_vertices_NOT_CHALK": plan[
            "projected_synthetic_vertices_NOT_CHALK"],
        "source_model_coverage_NOT_NATIVE": {
            k:v["source_model_coverage_NOT_NATIVE"] for k,v in
            plan["source_model_diagnostics_NOT_EGRET"].items()},
        "safe_to_execute": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
