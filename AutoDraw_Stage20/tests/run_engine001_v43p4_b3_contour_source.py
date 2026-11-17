#!/usr/bin/env python3
"""ENGINE-001 V43-P4 B3 contour-parallel source geometry, MODEL_ONLY.

Overpainting the SAME owner is free: no penalty/revisit counter. No Stage6,
game replay, production promotion, or claims about true Egret brush shape.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from run_engine001_full_adaptive_fill_v43p4 import (
    COLORS, FROZEN_DETAILS, FROZEN_DETAIL_VERTICES, MAX_STROKES,
    MAX_VERTICES, ROI_X0, SHAPE, SOURCE_SHA, checked_labels, sha,
)
from run_engine001_native_color_boundary_audit_v38 import original_labels

EXP = "ENGINE001_V43P4_B3_CONTOUR_PARALLEL_SOURCE_MODEL"
WIDTHS = (10, 6, 4, 2)
MAX_PATH_POINTS = 128
MAX_OUTSIDE_OWNER_LOGICAL = 3.0
TARGET_MODEL_COVERAGE_DIAGNOSTIC = .99
OWN_COLOR_OVERLAP_PENALTY = 0
RING_STEP_FACTOR = .70


def _footprint(points: list[tuple[float, float]], width: int):
    """OpenCV polygon stroke proxy; never use this as Egret acceptance."""
    canvas = np.zeros(SHAPE, np.uint8)
    integer = np.rint(np.asarray(points)).astype(np.int32)
    if len(integer) < 2:
        raise ValueError("B3 contour with fewer than two points")
    cv2.polylines(canvas, [integer.reshape(-1, 1, 2)], False,
                  255, width, cv2.LINE_8)
    return canvas != 0


def contour_candidates(mask: np.ndarray, width: int):
    """Stable contour-equidistant rings from source owner boundaries.

    The masks are erosion/distance levels, not rectangular row sweeps.
    A ring can contain multiple disconnected islands and holes; never bridge
    them. A closed loop is represented by first point repeated at the end.
    """
    if mask.shape != SHAPE or mask.dtype != np.bool_ or width not in WIDTHS:
        raise ValueError("B3 invalid source owner mask or width")
    # Padding guarantees full-image edge is treated as an exterior boundary.
    dt = cv2.distanceTransform(np.pad(mask.astype(np.uint8), 1), cv2.DIST_L2,
                               cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
    max_dist = float(dt.max(initial=0))
    base = width / 2.0 + .25
    step = max(1.0, width * RING_STEP_FACTOR)
    if max_dist < base:
        return []
    result = []
    distance = base
    while distance <= max_dist + .00001:
        ring_mask = (dt >= distance).astype(np.uint8)
        contours, _ = cv2.findContours(ring_mask, cv2.RETR_LIST,
                                       cv2.CHAIN_APPROX_SIMPLE)
        # Stable connected contour ordering, including inner holes.
        contours.sort(key=lambda c: (
            int(cv2.boundingRect(c)[1]), int(cv2.boundingRect(c)[0]),
            int(cv2.boundingRect(c)[2]), int(cv2.boundingRect(c)[3])))
        for raw in contours:
            if len(raw) == 0:
                continue
            approx = cv2.approxPolyDP(raw, max(.35, width*.07), True)
            pts = [tuple(map(int, p)) for p in approx.reshape(-1, 2).tolist()]
            if len(pts) == 1:
                # Actual motion is still non-zero to avoid BoardPane rejection.
                x, y = pts[0]
                paths = [[(x+.125, y), (x+.375, y)]]
            else:
                closed = pts + [pts[0]]
                # Every split shares exactly the previous endpoint; no jumps.
                paths = [closed[start:start + MAX_PATH_POINTS]
                         for start in range(0, len(closed)-1, MAX_PATH_POINTS-1)]
            for points in paths:
                if len(points) < 2:
                    continue
                footprint = _footprint(points, width)
                if not np.any(footprint & mask):
                    continue
                result.append({
                    "width": width, "distance": float(round(distance, 5)),
                    "points": points,
                    "footprint": footprint,
                    "vertices": len(points),
                })
        distance += step
    return result


def _safe_owner_footprint(footprint: np.ndarray, owner_mask: np.ndarray,
                          outside_dist: np.ndarray):
    # A tiny amount of spill into other owner classes is allowed only up to
    # the original fixed 3 logical px boundary, never at arbitrary distance.
    return not np.any(footprint & ~owner_mask &
                      (outside_dist > MAX_OUTSIDE_OWNER_LOGICAL))


def source_plan(indexes: np.ndarray, max_strokes: int = MAX_STROKES,
                max_vertices: int = MAX_VERTICES):
    checked_labels(indexes)
    if (type(max_strokes) is not int or type(max_vertices) is not int or
            max_strokes < FROZEN_DETAILS or
            max_vertices < FROZEN_DETAIL_VERTICES):
        raise ValueError("B3 invalid frozen resource caps")
    mask = {owner: indexes == owner for owner in COLORS}
    if not all(np.any(mask[x]) for x in COLORS):
        raise ValueError("B3 required color owner missing")
    # Original target pixels remain the unit of accounting.
    uncovered = {owner: mask[owner].copy() for owner in COLORS}
    source_count = {owner: int(mask[owner].sum()) for owner in COLORS}
    candidates = {}
    rejected_excess = Counter()
    for owner in COLORS:
        outside_dt = cv2.distanceTransform(
            (~mask[owner]).astype(np.uint8), cv2.DIST_L2,
            cv2.DIST_MASK_PRECISE)
        for width in WIDTHS:
            accepted = []
            for item in contour_candidates(mask[owner], width):
                footprint = item["footprint"]
                if not _safe_owner_footprint(footprint, mask[owner], outside_dt):
                    rejected_excess[owner] += 1
                    continue
                accepted.append(item)
            candidates[owner, width] = accepted

    paths = []
    selected = {owner: Counter() for owner in COLORS}
    blocked = None
    # All owners compete at each width before any narrower-width stage.
    # Fairness: maximize fractional residual per owner, then fraction of
    # pixels actually gained per vertex, with deterministic owner/route ties.
    for width in WIDTHS:
        used = {(owner, i): False for owner in COLORS
                for i in range(len(candidates[owner, width]))}
        while True:
            proposals = []
            for owner in COLORS:
                own_left = uncovered[owner]
                area = source_count[owner]
                if not own_left.any():
                    continue
                best = None
                for i, cand in enumerate(candidates[owner, width]):
                    if used[owner, i]:
                        continue
                    gain = int(np.count_nonzero(cand["footprint"] & own_left))
                    if gain == 0:
                        continue
                    # Own-color footprint revisits incur ZERO penalty.
                    # Fairness score combines residual fraction and path value.
                    score = ((int(own_left.sum()) / area),
                             gain / cand["vertices"], gain,
                             -cand["vertices"], -i)
                    if best is None or score > best[0]:
                        best = (score, i, cand, gain)
                if best is not None:
                    proposals.append((best[0], -owner, owner, best))
            if not proposals:
                break
            _, _, owner, choice = max(proposals)
            _, idx, cand, gain = choice
            used[owner, idx] = True
            if (len(paths)+1+FROZEN_DETAILS > max_strokes or
                    sum(len(p["points"]) for p in paths) +
                    cand["vertices"]+FROZEN_DETAIL_VERTICES > max_vertices):
                blocked = {
                    "reason": "BLOCKED_RESOURCE",
                    "first_rejected_owner": owner,
                    "first_rejected_width": width,
                    "attempted_total_strokes": len(paths)+1+FROZEN_DETAILS,
                    "attempted_total_vertices_NOT_CHALK": (
                        sum(len(p["points"]) for p in paths) +
                        cand["vertices"]+FROZEN_DETAIL_VERTICES),
                    "max_strokes": max_strokes,
                    "max_vertices": max_vertices,
                    "no_partial_native_render": True,
                }
                break
            points = [{"x":float(x+ROI_X0),"y":float(y)}
                      for x,y in cand["points"]]
            paths.append({
                "strokeId": f"p4-b3-{owner}-{len(paths):05d}",
                "colorIndex": owner, "width": width,
                "points": points, "ring_depth_logical": cand["distance"],
                "source_gain_new_pixels": gain,
            })
            uncovered[owner][cand["footprint"] & mask[owner]] = False
            selected[owner][width] += 1
        if blocked:
            break

    diagnostics = {}
    for owner in COLORS:
        missed = int(uncovered[owner].sum())
        diagnostics[str(owner)] = {
            "source_pixels": source_count[owner],
            "model_missing": missed,
            "source_model_coverage_NOT_EGRET":
                (source_count[owner]-missed)/source_count[owner],
            "contour_widths": {str(w): selected[owner][w] for w in WIDTHS},
            "model_candidates_rejected_excess_3px": rejected_excess[owner],
        }
    model_low = any(v["source_model_coverage_NOT_EGRET"] <
                    TARGET_MODEL_COVERAGE_DIAGNOSTIC
                    for v in diagnostics.values())
    vertices = FROZEN_DETAIL_VERTICES + sum(
        len(s["points"]) for s in paths)
    return {
        "experiment": EXP,
        "stage": "SOURCE_MODEL_ONLY_NOT_EGRET",
        "source_shape_hw": list(SHAPE),
        "status": "BLOCKED_RESOURCE" if blocked else (
            "MODEL_LOW_COVERAGE" if model_low else
            "SOURCE_CANDIDATE_FOR_NATIVE_FOOTPRINT_REVIEW"),
        "blocked_resource": blocked,
        "source_model_coverage_diagnostic_threshold": TARGET_MODEL_COVERAGE_DIAGNOSTIC,
        "nominal_widths_desc": list(WIDTHS),
        "own_color_overlap_penalty": OWN_COLOR_OVERLAP_PENALTY,
        "ring_step_width_factor": RING_STEP_FACTOR,
        "outside_owner_limit_logical_px": MAX_OUTSIDE_OWNER_LOGICAL,
        "source_only_diagnostics": diagnostics,
        "no_original_A_B0_B1_B2_paint": True,
        "required_original_V44B_detail_strokes_last": FROZEN_DETAILS,
        "frozen_detail_vertices": FROZEN_DETAIL_VERTICES,
        "contour_paint_count": len(paths),
        "projected_total_strokes": len(paths)+FROZEN_DETAILS,
        "projected_total_vertices_NOT_CHALK": vertices,
        "paint_diagnostic_only": paths,
        "native_footprint_E3": "NOT_RUN",
        "safe_to_execute": False, "E4_game": "NOT_RUN",
        "E5_independent": "NOT_RUN",
        "game_exact_CHALK": None, "production_accepted": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError("B3 refuses overwrite of existing evidence")
    if sha(a.source) != SOURCE_SHA:
        raise ValueError("B3 original source SHA mismatch")
    labels = original_labels(a.source)[::3,::3][:,ROI_X0:ROI_X0+SHAPE[1]].copy()
    report = source_plan(labels)
    report["source_sha256"] = SOURCE_SHA
    report["source_labels_sha256"] = hashlib.sha256(labels.tobytes()).hexdigest()
    a.output.mkdir(parents=True)
    (a.output/"b3-contour-source-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "paint": report["contour_paint_count"],
        "total": report["projected_total_strokes"],
        "vertices_NOT_CHALK": report["projected_total_vertices_NOT_CHALK"],
        "model_owner_coverage_NOT_EGRET": {
            k:v["source_model_coverage_NOT_EGRET"]
            for k,v in report["source_only_diagnostics"].items()},
        "safe_to_execute": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
