#!/usr/bin/env python3
"""V43-P4 B2-FULL source-only: oriented broad fill + micro residual, not Egret.

Independently preregistered before this code; never reuse A/B0/B1 accepted routes.
A model width2 dot footprint is NOT true BoardPane brush coverage.
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
    ANGLES, COLORS, FROZEN_DETAILS, FROZEN_DETAIL_VERTICES,
    MAX_STROKES, MAX_VERTICES, MIN_NEW, ROI_X0, SHAPE,
    SOURCE_SHA, candidates_for_width, checked_labels, sha,
)
from run_engine001_native_color_boundary_audit_v38 import original_labels

EXP="ENGINE001_V43P4_B2_FULL_ADAPTIVE_BOUNDARY_REPAIR_SOURCE_MODEL"
BROAD_WIDTHS=(10,6,4)
MICRO_WIDTH=2
MICRO_LENGTH=.25
MICRO_GAIN_MIN=1
BUDGET_PAINTER_VERTICES=2

# OpenCV rasterization only for candidate ordering, never real Egret coverage.
_kernel=np.zeros((5,5),np.uint8)
cv2.line(_kernel,(2,2),(2,2),255,2,cv2.LINE_8)
MICRO_OFFSETS=tuple((int(y-2),int(x-2))
                    for y,x in zip(*np.nonzero(_kernel)))


def micro_candidate(owner_mask, y, x):
    """Tentative owner-covered source pixels for a 0.25px two-point stroke."""
    if owner_mask.shape!=SHAPE or owner_mask.dtype!=np.bool_:
        raise ValueError("B2 owner source shape/type invalid")
    if not (0<=x<SHAPE[1] and 0<=y<SHAPE[0] and owner_mask[y,x]):
        raise ValueError("B2 micro center must be original owner pixel")
    h,w=SHAPE
    owned=[]
    for dy,dx in MICRO_OFFSETS:
        yy,xx=y+dy,x+dx
        if 0<=yy<h and 0<=xx<w and owner_mask[yy,xx]:
            owned.append(yy*w+xx)
    if y*w+x not in owned:
        raise ValueError("B2 model kernel did not include owner center")
    return tuple(owned)


def source_plan(indexes, max_strokes=MAX_STROKES, max_vertices=MAX_VERTICES):
    checked_labels(indexes)
    if (type(max_strokes) is not int or type(max_vertices) is not int
            or max_strokes<FROZEN_DETAILS
            or max_vertices<FROZEN_DETAIL_VERTICES):
        raise ValueError("B2 invalid frozen resource caps")
    strokes=[]
    stats={}
    remaining_by_owner={}
    blocked=None

    def create_stroke(owner,width,a,b,stage):
        nonlocal blocked
        next_paint=len(strokes)+1
        total=next_paint+FROZEN_DETAILS
        vertices=2*next_paint+FROZEN_DETAIL_VERTICES
        if total>max_strokes or vertices>max_vertices:
            blocked={
                "status":"BLOCKED_RESOURCE",
                "first_rejected_stroke":f"p4-b2-{owner}-{len(strokes):05d}",
                "attempted_paint_strokes":next_paint,
                "attempted_total_strokes":total,
                "attempted_vertices_NOT_CHALK":vertices,
                "max_total_strokes":max_strokes,
                "max_total_vertices":max_vertices,
                "first_rejected_owner":owner,
                "first_rejected_width":width,
                "first_rejected_stage":stage,
                "no_partial_native_render":True,
            }
            return False
        strokes.append({
            "strokeId":f"p4-b2-{owner}-{len(strokes):05d}",
            "colorIndex":owner,"width":width,
            "points":[{"x":float(a[0]),"y":float(a[1])},
                      {"x":float(b[0]),"y":float(b[1])}],
            "source_only_stage":stage,
        })
        return True

    for owner in COLORS:
        mask=(indexes==owner)
        if not mask.any():
            raise ValueError("B2 required original owner missing")
        remain=mask.ravel().copy()
        broad=Counter()
        micro_count=0
        broad_candidates=0
        attempted_micro=0
        source_pixels=int(mask.sum())
        for width in BROAD_WIDTHS:
            proposals=candidates_for_width(mask,width)
            broad_candidates+=len(proposals)
            heap=[]
            for i,candidate in enumerate(proposals):
                gain=int(np.count_nonzero(remain[candidate[3]]))
                heapq.heappush(heap,(-gain,i,gain))
            while heap:
                _,i,old=heapq.heappop(heap)
                candidate=proposals[i]
                gain=int(np.count_nonzero(remain[candidate[3]]))
                if gain!=old:
                    heapq.heappush(heap,(-gain,i,gain))
                    continue
                if gain<MIN_NEW[width]:
                    break
                a,b=candidate[1:3]
                if not create_stroke(owner,width,
                        (a[0]+ROI_X0,a[1]),(b[0]+ROI_X0,b[1]),"broad"):
                    break
                remain[candidate[3]]=False
                broad[width]+=1
            if blocked:break
        if blocked:
            stats[str(owner)]={
                "source_pixels":source_pixels,
                "model_missing_pixels_at_block":int(remain.sum()),
                "broad_by_width":{str(w):int(broad[w]) for w in BROAD_WIDTHS},
                "micro_strokes_added":micro_count,
                "broad_candidate_count":broad_candidates,
                "blocked":True,
            }
            remaining_by_owner[str(owner)]=int(remain.sum())
            break

        # Every remaining original owner pixel is a potential short microstroke
        # center, never a distant-color center. A native micro probe for 12
        # singletons is limited evidence, not permission to extrapolate quality.
        micro_candidates=[]
        ys,xs=np.nonzero(mask)
        for y,x in zip(ys,xs):
            if not remain[y*SHAPE[1]+x]:
                continue
            hits=micro_candidate(mask,int(y),int(x))
            micro_candidates.append((int(y),int(x),hits))
        heap=[]
        for i,(_,_,hits) in enumerate(micro_candidates):
            gain=sum(int(remain[h]) for h in hits)
            heapq.heappush(heap,(-gain,i,gain))
        while heap:
            _,i,previous=heapq.heappop(heap)
            y,x,hits=micro_candidates[i]
            gain=sum(int(remain[h]) for h in hits)
            if gain!=previous:
                heapq.heappush(heap,(-gain,i,gain))
                continue
            if gain<MICRO_GAIN_MIN:
                break
            # The source model uses an integer-centered dot approximation ONLY
            # for ranking. Actual P4-B2 micro coordinates are always fractional.
            count=len(strokes)
            if count%2==0:
                a=(x+ROI_X0+.125,y)
                b=(x+ROI_X0+.375,y)
            else:
                a=(x+ROI_X0,y+.125)
                b=(x+ROI_X0,y+.375)
            attempted_micro+=1
            if not create_stroke(owner,MICRO_WIDTH,a,b,"micro"):
                break
            remain[list(hits)]=False
            micro_count+=1
        residual=int(remain.sum())
        stats[str(owner)]={
            "source_pixels":source_pixels,
            "source_model_missing":residual,
            "source_model_coverage_NOT_EGRET":(source_pixels-residual)/source_pixels,
            "broad_by_width":{str(w):int(broad[w]) for w in BROAD_WIDTHS},
            "micro_strokes_added":micro_count,
            "micro_centers_considered":len(micro_candidates),
            "broad_candidate_count":broad_candidates,
            "micro_strokes_attempted":attempted_micro,
            "blocked":bool(blocked),
        }
        remaining_by_owner[str(owner)]=residual
        if blocked:break
    if blocked:
        for owner in COLORS:
            if str(owner) not in remaining_by_owner:
                remaining_by_owner[str(owner)]=int(np.count_nonzero(indexes==owner))
    return {
        "experiment":EXP,
        "stage":"SOURCE_ONLY_NOT_NATIVE",
        "status":"BLOCKED_RESOURCE" if blocked else "MODEL_CANDIDATE_READY_FOR_REVIEW",
        "source_original_owner_sequence":list(COLORS),
        "width_sequence":[*BROAD_WIDTHS,MICRO_WIDTH],
        "broad_angles_deg":list(ANGLES),
        "min_new_by_broad_width":{str(k):MIN_NEW[k] for k in BROAD_WIDTHS},
        "micro_segment_length_logical_px":MICRO_LENGTH,
        "micro_model_footprint_offsets_NOT_EGRET":[list(x) for x in MICRO_OFFSETS],
        "original_A_paint_retained":0,
        "original_B0_paint_retained":0,
        "original_B1_paint_retained":0,
        "required_frozen_V44B_details":FROZEN_DETAILS,
        "required_frozen_detail_vertices":FROZEN_DETAIL_VERTICES,
        "details_exact_verified":False,
        "paint_count_generated_before_block":len(strokes),
        "projected_total_strokes":len(strokes)+FROZEN_DETAILS,
        "projected_synthetic_vertices_NOT_CHALK":
            len(strokes)*BUDGET_PAINTER_VERTICES+FROZEN_DETAIL_VERTICES,
        "model_missing_pixels_by_owner_after_attempt":remaining_by_owner,
        "source_model_by_owner":stats,
        "blocked_resource":blocked,
        "native_allowed":False,
        "safe_to_execute":False,
        "E3":"NOT_RUN","E4":"NOT_RUN","E5":"NOT_RUN",
        "game_exact_CHALK":None,"production_accepted":False,
        "paint_diagnostic_only":strokes,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists():
        raise ValueError("B2 full source refuse evidence overwrite")
    if sha(a.source)!=SOURCE_SHA:
        raise ValueError("B2 source identity SHA drift")
    labels=original_labels(a.source)[::3,::3][:,ROI_X0:ROI_X0+SHAPE[1]].copy()
    result=source_plan(labels)
    result["source_sha256"]=SOURCE_SHA
    result["source_labels_sha256"]=hashlib.sha256(labels.tobytes()).hexdigest()
    a.output.mkdir(parents=True)
    (a.output/"b2-full-source-report.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({
        "status":result["status"],
        "attempted_paint_count":result["paint_count_generated_before_block"],
        "blocked":result["blocked_resource"],
        "model_missing_by_owner":result["model_missing_pixels_by_owner_after_attempt"],
        "safe_to_execute":False},ensure_ascii=False))

if __name__=="__main__":
    main()
