#!/usr/bin/env python3
"""ENGINE001_TWO_ICON_PAINTED_FRONTIER_V2: source-bound native offline diagnostic.

The actual FRONTIER is extracted from the PREVIEW OF PAINTED BASELINE STROKES,
not the outer target-mask contour. Frozen protocol in TASKS.md predates the
first V2 native render. No exact CHALK or real-game E4 is inferred.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_two_icon_mask_probe import (
    ALPHA_THRESHOLD, HEIGHT, WIDTH, compare, composite_mask, plan_strokes
)
from run_engine001_predictive_contour_probe import (
    SCALE, footprint, proxy_union, render_native, stroke_length
)

EXPERIMENT_ID = "ENGINE001_TWO_ICON_PAINTED_FRONTIER_V2"
MAX_CONTOURS = 24
MIN_CONTOUR_LENGTH = 30.0
MAX_CONTOUR_LENGTH = 90.0
MIN_NEW_PIXELS = 48
MIN_OVERLAP_FRACTION = 0.15
MAX_OVERLAP_FRACTION = 0.85
MAX_ENDPOINT_TRIM = 4
MIN_FILL_LENGTH = 8.0
HALO_LOGICAL = 3.0
HALO_BACKING = HALO_LOGICAL * SCALE
BASELINE = {
    "source": "ENGINE001_TWO_ICON_HOME_ENVELOPE_V1",
    "source_strokes": 380, "coverage": 0.9210937202482958,
    "iou": 0.9191568600129207, "outside": 332
}
PREVIOUS = {
    "source": "ENGINE001_TWO_ICON_PREDICTIVE_CONTOUR_V1",
    "source_strokes": 381, "coverage": 0.9272884217474644,
    "iou": 0.9253268139440616, "outside": 334
}


def permitted_halo(target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if target.dtype != np.dtype(bool) or target.shape != (HEIGHT*SCALE, WIDTH*SCALE):
        raise ValueError("Expected fixed binary 3x target")
    # BACKING pixel centres; Euclidean width 9 backing pixels is a
    # conservative offline metric, not unverified screen calibration.
    exterior = (~target).astype(np.uint8)
    distance = cv2.distanceTransform(exterior, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    return distance <= HALO_BACKING + 1e-6, distance


def _subdivide_border(raw: np.ndarray, source: int) -> list[dict]:
    """Follow the border, splitting only after a MIN-length arc is complete."""
    if len(raw) < 3:
        return []
    polygon = cv2.approxPolyDP(raw, 1.5, True)[:, 0, :]
    if len(polygon) < 3:
        return []
    expanded = np.concatenate([polygon, polygon[:1]], axis=0)
    pieces = []
    current = [expanded[0]]
    length = 0.0
    for point in expanded[1:]:
        step = float(np.linalg.norm(point-current[-1]))
        if step == 0.0:
            continue
        current.append(point)
        length += step
        # The native probe has a 128 point upper bound, enforced here too.
        if length >= MIN_CONTOUR_LENGTH*SCALE and (
                length >= MAX_CONTOUR_LENGTH*SCALE or len(current) >= 127):
            pieces.append({"source_painted_contour": source,
                           "points": [{"x": float(x)/SCALE, "y": float(y)/SCALE}
                                      for x,y in current],
                           "length": length / SCALE})
            current = [point]
            length = 0.0
    if length >= MIN_CONTOUR_LENGTH*SCALE and len(current)>=2:
        pieces.append({"source_painted_contour": source,
                       "points": [{"x": float(x)/SCALE, "y": float(y)/SCALE}
                                  for x,y in current],
                       "length": length/SCALE})
    return pieces


def painted_frontier_candidates(painted: np.ndarray) -> list[dict]:
    if painted.shape != (HEIGHT*SCALE, WIDTH*SCALE):
        raise ValueError("Native preview geometry mismatch")
    # This line is the essential distinction from V1 target-border research.
    raw, _ = cv2.findContours(painted.astype(np.uint8)*255,
                              cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for i, border in enumerate(raw):
        candidates.extend(_subdivide_border(border, i))
    return candidates


def plan_painted_frontier(logical: np.ndarray) -> tuple[list[dict], dict, dict[str, np.ndarray]]:
    if logical.dtype != np.dtype(bool) or logical.shape != (HEIGHT,WIDTH):
        raise ValueError("Fixed logical mask required")
    target = np.repeat(np.repeat(logical,SCALE,axis=0),SCALE,axis=1)
    source_plan = plan_strokes(logical)
    painted = proxy_union(source_plan,target.shape)
    missing = target & ~painted
    allowed, distance = permitted_halo(target)
    candidates = painted_frontier_candidates(painted)
    evaluated = []
    for candidate in candidates:
        pts = candidate["points"]
        if len(pts)>128 or candidate["length"]>MAX_CONTOUR_LENGTH*1.5:
            continue
        # True source of proposed centres: native-scale painted stroke border.
        stroke_mask = footprint(pts,target.shape)
        pixels = int(np.count_nonzero(stroke_mask))
        if not pixels:
            continue
        hit = int(np.count_nonzero(stroke_mask & missing))
        overlap = int(np.count_nonzero(stroke_mask & painted))
        outside_far = int(np.count_nonzero(stroke_mask & ~allowed))
        evaluated.append({
            "source_painted_contour":candidate["source_painted_contour"],
            "points":pts, "length":candidate["length"],
            "mask":stroke_mask, "score":hit/candidate["length"],
            "initial_gain":hit, "overlap_fraction":overlap/pixels,
            "initial_far_outside":outside_far
        })
    evaluated.sort(key=lambda x:(-x["score"],-x["initial_gain"],
                                  x["source_painted_contour"]))
    selected = []
    selected_mask = np.zeros_like(target)
    decisions = []
    for c in evaluated:
        if len(selected)>=MAX_CONTOURS:
            break
        coverage = c["mask"] & ~selected_mask
        gain = int(np.count_nonzero(coverage & missing))
        far = int(np.count_nonzero(coverage & ~allowed))
        # Preview overlap with existing paint: portion of ROUND brush
        # footprint safely reuses the old painted stripe.
        valid = (c["length"]>=MIN_CONTOUR_LENGTH and gain>=MIN_NEW_PIXELS
                 and MIN_OVERLAP_FRACTION<=c["overlap_fraction"]<=MAX_OVERLAP_FRACTION
                 and far==0)
        decisions.append({
            "source_painted_contour":c["source_painted_contour"],
            "length":round(c["length"],3),
            "gain":gain, "painted_overlap_fraction":round(c["overlap_fraction"],6),
            "far_overshoot_pixels":far, "accepted":valid
        })
        if valid:
            selected.append({"width":2, "points":c["points"]})
            selected_mask|=c["mask"]
    horizontal=[]
    dropped=0
    shortened=0
    for original in source_plan:
        pts = [dict(p) for p in original["points"]]
        unpainted_without_contour = footprint(pts,target.shape) & target & ~selected_mask
        if not np.any(unpainted_without_contour):
            dropped+=1
            continue
        if stroke_length(original)<MIN_FILL_LENGTH:
            dropped+=1
            continue
        y=round(pts[0]["y"]*SCALE)
        for _ in range(MAX_ENDPOINT_TRIM):
            if pts[-1]["x"]-pts[0]["x"]<=MIN_FILL_LENGTH+1: break
            if selected_mask[y,round(pts[0]["x"]*SCALE)]:
                pts[0]["x"]+=1
                shortened+=1
            else: break
        for _ in range(MAX_ENDPOINT_TRIM):
            if pts[-1]["x"]-pts[0]["x"]<=MIN_FILL_LENGTH+1: break
            if selected_mask[y,round(pts[-1]["x"]*SCALE)]:
                pts[-1]["x"]-=1
                shortened+=1
            else: break
        horizontal.append({"width":2,"points":pts})
    # Contours FIRST, horizontals SECOND. No short standalone hole patches.
    combined=selected+horizontal
    for i,s in enumerate(combined):
        s["strokeId"]=f"icon-{i}"
    n_points=sum(len(s["points"]) for s in combined)
    if not combined or len(combined)>2500 or n_points>5900:
        raise ValueError("Native geometry quota exceeded")
    preview=proxy_union(combined,target.shape)
    notes={
        "algorithm":"internal_painted_strip_frontier_contour_then_joint_horizontal",
        "preview_algorithm":"OpenCV LINE_8 6px on 3x grid; not actual Egret",
        "baseline_strokes":len(source_plan),
        "painted_contour_candidate_count":len(candidates),
        "scored_candidate_count":len(evaluated),
        "accepted_frontier_contours":len(selected),
        "retained_horizontal_strokes":len(horizontal),
        "dropped_horizontal_strokes":dropped,
        "trimmed_endpoint_logical_px":shortened,
        "total_strokes":len(combined),
        "total_vertices_not_chalk":n_points,
        "contour_length_logical":sum(stroke_length(s) for s in selected),
        "horizontal_length_logical":sum(stroke_length(s) for s in horizontal),
        "baseline_length_logical":sum(stroke_length(s) for s in source_plan),
        "candidate_decisions":decisions,
        "preview_baseline":compare(target,painted),
        "preview_joint":compare(target,preview),
        "parameters_frozen_before_native":{
            "preview_scale":SCALE,"preview_line_diameter":6,
            "approx_epsilon_native_px":1.5,
            "min_length_logical":MIN_CONTOUR_LENGTH,
            "max_length_logical":MAX_CONTOUR_LENGTH,
            "min_gain_native_px":MIN_NEW_PIXELS,
            "min_overlap_fraction":MIN_OVERLAP_FRACTION,
            "max_overlap_fraction":MAX_OVERLAP_FRACTION,
            "max_contours":MAX_CONTOURS,
            "max_endpoint_trim_logical":MAX_ENDPOINT_TRIM,
            "max_far_leak_distance_logical":HALO_LOGICAL
        }
    }
    return combined,notes,{
        "target":target,"painted_baseline_preview":painted,
        "predicted_missing":missing,"selected_painted_frontier":selected_mask,
        "joint_preview":preview,"distance_to_target_native":distance
    }


def measure_halo(target:np.ndarray, paint:np.ndarray) -> dict:
    _,dist=permitted_halo(target)
    leaked = paint & ~target
    all_d=dist[leaked]
    far = int(np.count_nonzero(all_d>HALO_BACKING+1e-6))
    return {
        "leaked_native_pixels":int(leaked.sum()),
        "farther_than_3logical_native_pixels":far,
        "max_leak_distance_logical":float(all_d.max()/SCALE) if all_d.size else 0.0,
        "all_leakage_in_3logical_halo":far==0,
        "geometry_policy":"DEC-030 perimeter distance offline sensitivity only; NOT a live PASS"
    }


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,default=Path("."))
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    workspace=args.workspace.resolve()
    output=args.output_dir.resolve()
    output.mkdir(parents=True,exist_ok=True)
    logical,sources=composite_mask(workspace)
    plan,planning,previews=plan_painted_frontier(logical)
    for name,data in previews.items():
        if name=="distance_to_target_native":
            continue
        Image.fromarray(data.astype(np.uint8)*255,"L").save(output/(name+".png"))
    (output/"painted-frontier-plan.json").write_text(
        json.dumps({"experiment_id":EXPERIMENT_ID,"strokes":plan},
                   indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    result=render_native(plan,workspace)
    url=result.pop("webglPngDataUrl")
    if not url.startswith("data:image/png;base64,"):
        raise ValueError("No native actual Egret PNG")
    png=base64.b64decode(url.partition(",")[2],validate=True)
    (output/"painted-frontier-native-egret.png").write_bytes(png)
    with Image.open(BytesIO(png)) as im:
        rgba=np.asarray(im.convert("RGBA"))
    if rgba.shape!=(HEIGHT*SCALE,WIDTH*SCALE,4):
        raise ValueError("Unexpected native PNG dimensions")
    painted=rgba[:,:,3]>=ALPHA_THRESHOLD
    target=previews["target"]
    metrics=compare(target,painted)
    halo=measure_halo(target,painted)
    visualization=np.full((*target.shape,3),255,dtype=np.uint8)
    visualization[target & painted]=(44,145,76)
    visualization[target & ~painted]=(230,80,70)
    visualization[~target & painted]=(65,95,205)
    Image.fromarray(visualization,"RGB").save(output/"painted-frontier-overlay.png")
    passes=metrics["coverage"]>=0.99 and halo["all_leakage_in_3logical_halo"]
    report={
        "schema":EXPERIMENT_ID,
        "status":"OFFLINE_GEOMETRIC_PASS_NOT_GAME" if passes else "OFFLINE_QUALITY_FAIL",
        "source":sources,"baseline_frozen":BASELINE,
        "previous_target_contour_frozen":PREVIOUS,
        "target_pixels":int(target.sum()),"native_scale":SCALE,
        "normal_mode":True,"radius":2,"native_alpha_threshold":ALPHA_THRESHOLD,
        "native":result,"native_png_sha256":hashlib.sha256(png).hexdigest(),
        "planning":planning,"native_comparison":metrics,"native_halo":halo,
        "diagnostic_goal":{"coverage_min":0.99,"max_leak_distance_logical":3.0,
                           "offline_result":"PASS" if passes else "FAIL"},
        "limitations":[
            "Not a live game or exact CHALK measurement",
            "Native alpha mask sensitivity does not implement run-bound screen RGB DEC-030 policy",
            "Proxy forecast uses OpenCV LINE_8 and must not be conflated with Egret rendering",
            "No short per-hole corrective strokes, no post-result parameter tuning",
            "E4 real live GPU/accepted point count and independent E5 remain open"
        ]
    }
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                                       encoding="utf-8")
    print("ENGINE001_PAINTED_FRONTIER_V2",report["status"],
          "coverage",metrics["coverage"],"IoU",metrics["iou"],
          "leak",halo["leaked_native_pixels"],"far",halo["farther_than_3logical_native_pixels"],
          "frontiers",planning["accepted_frontier_contours"],
          "strokes",planning["total_strokes"],flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
