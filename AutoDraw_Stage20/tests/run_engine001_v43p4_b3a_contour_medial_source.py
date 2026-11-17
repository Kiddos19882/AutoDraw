#!/usr/bin/env python3
"""B3a contour rings plus owner-medial and residual micro, MODEL_ONLY.

Unrestricted repetition over SAME-color painted pixels incurs zero cost.
First full-source hypothesis independently preregistered; no old B3 paths
or Egret native pixels are used in the planning coordinates/selection.
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
    COLORS, FROZEN_DETAILS, FROZEN_DETAIL_VERTICES, MAX_STROKES,
    MAX_VERTICES, ROI_X0, SHAPE, SOURCE_SHA, checked_labels, sha,
    candidates_for_width,
)
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_v43p4_b3_contour_source import (
    WIDTHS, MAX_OUTSIDE_OWNER_LOGICAL, _safe_owner_footprint,
    contour_candidates,
)
from run_engine001_v43p4_b2_full_source import micro_candidate

EXP = "ENGINE001_V43P4_B3A_CONTOUR_MEDIAL_REPAIR_SOURCE_MODEL"
STAGES = ("ring10", "ring6", "ring4", "ring2", "owner_medial2", "residual_micro2")
TARGET_MODEL_COVERAGE = .99
SAME_OWNER_OVERPAINT_PENALTY = 0
MICRO_LENGTH = .25


def _medial_on_source(mask: np.ndarray, a, b):
    """Every rasterized centerline pixel belongs to the frozen color owner."""
    center=np.zeros(SHAPE,np.uint8)
    cv2.line(center,tuple(map(int,a)),tuple(map(int,b)),
             255,1,cv2.LINE_8)
    return bool(np.any(center)) and bool(np.all(mask[center>0]))


def _make_ring_candidates(mask, width, outside):
    result=[]
    for x in contour_candidates(mask,width):
        if not _safe_owner_footprint(x["footprint"],mask,outside):
            continue
        points=x["points"]
        result.append({
            "points":points, "width":width,
            "owned":x["footprint"] & mask,
            "vertices":len(points),"route_kind":"contour_ring",
        })
    return result


def _make_medial_candidates(mask, outside):
    result=[]
    for width,a,b,owned_flat,_ in candidates_for_width(mask,2):
        if not _medial_on_source(mask,a,b):
            continue
        footprint=np.zeros(SHAPE,np.uint8)
        cv2.line(footprint,tuple(map(int,a)),tuple(map(int,b)),
                 255,2,cv2.LINE_8)
        fp=footprint!=0
        if not _safe_owner_footprint(fp,mask,outside):
            continue
        result.append({
            "points":[a,b], "width":2,
            "owned_index":np.asarray(owned_flat,dtype=np.int32),"vertices":2,
            "route_kind":"owner_medial",
        })
    return result


def _make_micro_candidates(mask, remaining):
    ys,xs=np.nonzero(remaining)
    result=[]
    for i,(y,x) in enumerate(zip(ys.tolist(),xs.tolist())):
        ids=micro_candidate(mask,int(y),int(x))
        if i%2==0:
            points=[(float(x)+.125,float(y)),
                    (float(x)+.375,float(y))]
        else:
            points=[(float(x),float(y)+.125),
                    (float(x),float(y)+.375)]
        result.append({
            "points":points,"width":2,
            "owned_index":np.asarray(ids,dtype=np.int32),
            "vertices":2, "route_kind":"short_residual",
        })
    return result


def source_plan(indexes: np.ndarray,
                max_strokes: int = MAX_STROKES,
                max_vertices: int = MAX_VERTICES):
    checked_labels(indexes)
    if (type(max_strokes) is not int or type(max_vertices) is not int
            or max_strokes<FROZEN_DETAILS
            or max_vertices<FROZEN_DETAIL_VERTICES):
        raise ValueError("B3a invalid frozen resource caps")
    masks={owner: indexes==owner for owner in COLORS}
    if any(not masks[owner].any() for owner in COLORS):
        raise ValueError("B3a missing original owner class")
    remaining={owner:masks[owner].copy() for owner in COLORS}
    totals={owner:int(masks[owner].sum()) for owner in COLORS}
    outside={
        owner:cv2.distanceTransform((~masks[owner]).astype(np.uint8),
                                    cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        for owner in COLORS
    }
    routes=[]
    counts={owner:Counter() for owner in COLORS}
    own_revisited={owner:0 for owner in COLORS}
    blocked=None
    vertices=FROZEN_DETAIL_VERTICES
    first_rejected=None

    def gain_for(option, remainder):
        if "owned_index" in option:
            return int(np.count_nonzero(remainder.ravel()[option["owned_index"]]))
        return int(np.count_nonzero(option["owned"] & remainder))

    def revisit_count(option, owner):
        # Purely informational: never used for ranking or rejection.
        if "owned_index" in option:
            ix=option["owned_index"]
            return int(np.count_nonzero(
                masks[owner].ravel()[ix] & ~remaining[owner].ravel()[ix]))
        return int(np.count_nonzero(
            option["owned"] & masks[owner] & ~remaining[owner]))

    def mark_covered(option, owner):
        if "owned_index" in option:
            remaining[owner].ravel()[option["owned_index"]]=False
        else:
            remaining[owner][option["owned"] & masks[owner]]=False

    def best_from_heap(heap, options, remainder):
        # Re-score only stale heap roots, not every image candidate per stroke.
        while heap:
            _, idx, prev_gain = heap[0]
            opt=options[idx]
            gain=gain_for(opt,remainder)
            if gain!=prev_gain:
                heapq.heappop(heap)
                if gain:
                    heapq.heappush(heap,(-gain/opt["vertices"],idx,gain))
                continue
            if not gain:
                heapq.heappop(heap)
                continue
            return idx, opt, gain
        return None

    for stage in STAGES:
        options={}
        heaps={}
        for owner in COLORS:
            mask=masks[owner]
            if stage.startswith("ring"):
                width=int(stage[4:])
                choices=_make_ring_candidates(mask,width,outside[owner])
            elif stage=="owner_medial2":
                choices=_make_medial_candidates(mask,outside[owner])
            else:
                choices=_make_micro_candidates(mask,remaining[owner])
            options[owner]=choices
            heap=[]
            for idx,opt in enumerate(choices):
                gain=gain_for(opt,remaining[owner])
                if gain:
                    heapq.heappush(heap,(-gain/opt["vertices"],idx,gain))
            heaps[owner]=heap
        while True:
            eligible=[]
            for owner in COLORS:
                choice=best_from_heap(heaps[owner],options[owner],
                                      remaining[owner])
                if choice is None:
                    continue
                idx,opt,gain=choice
                coverage_deficit=int(remaining[owner].sum())/totals[owner]
                # Fair source owner budget: deficit first, then value/vertex.
                priority=(coverage_deficit,gain/opt["vertices"],
                          gain,-owner,-idx)
                eligible.append((priority,owner,idx,opt,gain))
            if not eligible:
                break
            _,owner,idx,opt,gain=max(eligible,key=lambda x:x[0])
            heapq.heappop(heaps[owner])
            attempted_vertices=vertices+opt["vertices"]
            attempted_strokes=len(routes)+1+FROZEN_DETAILS
            if (attempted_vertices>max_vertices or
                    attempted_strokes>max_strokes):
                first_rejected={
                    "reason":"BLOCKED_RESOURCE",
                    "stage":stage, "owner":owner,
                    "new_paint_ordinal":len(routes),
                    "attempted_total_strokes":attempted_strokes,
                    "attempted_total_vertices_NOT_CHALK":attempted_vertices,
                    "max_total_strokes":max_strokes,
                    "max_total_vertices":max_vertices,
                    "no_partial_native_render":True,
                }
                blocked="BLOCKED_RESOURCE"
                break
            own_revisited[owner]+=revisit_count(opt,owner)
            pts=[{"x":float(x+ROI_X0),"y":float(y)}
                 for x,y in opt["points"]]
            routes.append({
                "strokeId":f"p4-b3a-{owner}-{len(routes):05d}",
                "colorIndex":owner, "width":opt["width"],
                "points":pts,"stage":stage,
                "source_gain_new_pixels":gain,
            })
            mark_covered(opt,owner)
            counts[owner][stage]+=1
            vertices=attempted_vertices
        if blocked:
            break
    report={}
    for owner in COLORS:
        remain=int(remaining[owner].sum())
        report[str(owner)]={
            "original_source_pixels":totals[owner],
            "model_missing_pixels":remain,
            "source_model_coverage_NOT_EGRET":(totals[owner]-remain)/totals[owner],
            "chosen_strokes_by_stage":dict(counts[owner]),
            "own_color_revisited_pixels_NOT_PENALIZED":own_revisited[owner],
        }
    low=any(v["source_model_coverage_NOT_EGRET"]<
            TARGET_MODEL_COVERAGE for v in report.values())
    return {
        "experiment":EXP,
        "stage":"SOURCE_ONLY_NOT_EGRET",
        "status":blocked or ("MODEL_LOW_COVERAGE" if low
                           else "SOURCE_CANDIDATE_FOR_NATIVE_REVIEW"),
        "source_owner_sequence":list(COLORS),
        "fixed_stage_order":list(STAGES),
        "same_owner_overpaint_penalty":SAME_OWNER_OVERPAINT_PENALTY,
        "source_coverage_diagnostic_threshold":TARGET_MODEL_COVERAGE,
        "max_model_foreign_distance_logical_px":MAX_OUTSIDE_OWNER_LOGICAL,
        "micro_length_logical_px":MICRO_LENGTH,
        "resource_blocker":first_rejected,
        "by_owner":report,
        "new_paint_strokes":len(routes),
        "total_strokes_including_frozen_410":len(routes)+FROZEN_DETAILS,
        "synthetic_vertices_including_frozen_1792_NOT_CHALK":vertices,
        "original_A_B0_B1_B2_B3_paint_retained":0,
        "frozen_V44B_410_colored_details_required_last":True,
        "frozen_V44B_details_exact_verified":False,
        "paint_diagnostic_only":routes,
        "safe_to_execute":False,
        "E3_native":"NOT_RUN","E4_game":"NOT_RUN",
        "E5_independent":"NOT_RUN","game_exact_CHALK":None,
        "production_accepted":False,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    a=parser.parse_args()
    if a.output.exists():
        raise ValueError("B3a refuses overwrite of prior evidence")
    if sha(a.source)!=SOURCE_SHA:
        raise ValueError("B3a original SHA drift")
    labels=original_labels(a.source)[::3,::3][:,ROI_X0:ROI_X0+SHAPE[1]].copy()
    result=source_plan(labels)
    result["source_sha256"]=SOURCE_SHA
    result["source_labels_sha256"]=hashlib.sha256(labels.tobytes()).hexdigest()
    a.output.mkdir(parents=True)
    (a.output/"b3a-contour-medial-source-report.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({
        "status":result["status"],
        "paint":result["new_paint_strokes"],
        "total":result["total_strokes_including_frozen_410"],
        "vertices_NOT_CHALK":result[
            "synthetic_vertices_including_frozen_1792_NOT_CHALK"],
        "source_only_model":{owner:r["source_model_coverage_NOT_EGRET"]
                             for owner,r in result["by_owner"].items()},
        "safe_to_execute":False},ensure_ascii=False))


if __name__=="__main__":
    main()
