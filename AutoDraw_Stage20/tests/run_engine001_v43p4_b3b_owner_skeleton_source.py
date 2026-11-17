#!/usr/bin/env python3
"""V43-P4 B3b SOURCE_ONLY original-owner skeleton after contour rings.

Unlike B3a, this never asks a dilated-mask B0 candidate to pass an owner-
centerline check. Every medial point and its connecting raster segment must
lie in the original owner mask. Same-color overpainting is not penalized.
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
from skimage.morphology import skeletonize

from run_engine001_full_adaptive_fill_v43p4 import (
    COLORS, FROZEN_DETAILS, FROZEN_DETAIL_VERTICES, MAX_STROKES,
    MAX_VERTICES, ROI_X0, SHAPE, SOURCE_SHA, checked_labels, sha,
)
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_v43p4_b3_contour_source import (
    _footprint, _safe_owner_footprint, MAX_OUTSIDE_OWNER_LOGICAL,
)
from run_engine001_v43p4_b3a_contour_medial_source import (
    _make_ring_candidates, _make_micro_candidates,
)

EXP="ENGINE001_V43P4_B3B_ORIGINAL_OWNER_SKELETON_SOURCE_MODEL"
STAGES=("ring10","ring6","ring4","ring2","owner_skeleton2","residual_micro2")
MAX_SKELETON_STRAIGHT_LOOKAHEAD=24
MAX_PATH_POINTS=128
MODEL_COVERAGE_GATE=.99
SAME_OWNER_OVERPAINT_PENALTY=0


def _adjacent_skeleton(mask):
    pixels=sorted((int(y),int(x)) for y,x in zip(*np.nonzero(mask)))
    present=set(pixels)
    adj={}
    for y,x in pixels:
        neighbors=[]
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dy==0 and dx==0:
                    continue
                q=(y+dy,x+dx)
                if q not in present:
                    continue
                if dy and dx and ((y+dy,x) in present or (y,x+dx) in present):
                    # Avoid artificial diagonal triangles in skeleton graphs.
                    continue
                neighbors.append(q)
        adj[(y,x)]=sorted(neighbors)
    return adj


def trace_owner_skeleton(owner_mask: np.ndarray):
    """Deterministic maximal chains of a single original-owner skeleton."""
    if owner_mask.shape!=SHAPE or owner_mask.dtype!=np.bool_:
        raise ValueError("B3b invalid original owner mask")
    sk=skeletonize(owner_mask)
    adj=_adjacent_skeleton(sk)
    used=set()
    output=[]

    def key(a,b):
        return (a,b) if a<b else (b,a)

    def walk(start,first):
        edge=key(start,first)
        if edge in used:
            return []
        used.add(edge)
        path=[start,first]
        last=start
        here=first
        while len(adj[here])==2:
            nxt=next((p for p in adj[here] if p!=last),None)
            if nxt is None or key(here,nxt) in used:
                break
            used.add(key(here,nxt))
            path.append(nxt)
            last,here=here,nxt
            if here==start:
                break
        return path

    for p in sorted(adj):
        if not adj[p]:
            output.append([p])
    for p in sorted(adj):
        if len(adj[p])==2:
            continue
        for q in adj[p]:
            path=walk(p,q)
            if path:
                output.append(path)
    for p in sorted(adj):
        for q in adj[p]:
            path=walk(p,q)
            if path:
                output.append(path)
    return output


def _line_inside(mask, a, b):
    """Raster centerline, original owner only, no interpolated foreign pixels."""
    x0,y0=a
    x1,y1=b
    l,r=min(x0,x1),max(x0,x1)+1
    t,bt=min(y0,y1),max(y0,y1)+1
    roi=np.zeros((bt-t,r-l),np.uint8)
    cv2.line(roi,(x0-l,y0-t),(x1-l,y1-t),255,1,cv2.LINE_8)
    return bool(np.all(mask[t:bt,l:r][roi>0]))


def _simplify_owner_path(mask, chain):
    if len(chain)==1:
        y,x=chain[0]
        return [[(x+.125,y),(x+.375,y)]]
    xy=[(int(x),int(y)) for y,x in chain]
    simplified=[xy[0]]
    i=0
    while i<len(xy)-1:
        far=min(i+MAX_SKELETON_STRAIGHT_LOOKAHEAD,len(xy)-1)
        while far>i+1 and (xy[far]==xy[i] or
                             not _line_inside(mask,xy[i],xy[far])):
            # Do not collapse a closed skeleton loop to a zero-length dot.
            far-=1
        if not _line_inside(mask,xy[i],xy[far]):
            raise ValueError("BLOCKED_CENTERLINE original-owner skeleton edge drift")
        simplified.append(xy[far])
        i=far
    if len(simplified)<2:
        raise ValueError("B3b simplified skeleton path lost motion")
    return [simplified[start:start+MAX_PATH_POINTS]
            for start in range(0,len(simplified)-1,MAX_PATH_POINTS-1)]


def direct_owner_skeleton_candidates(original_mask, remainder, outside):
    if original_mask.shape!=SHAPE or remainder.shape!=SHAPE:
        raise ValueError("B3b mismatching original/residual masks")
    results=[]
    for chain in trace_owner_skeleton(remainder):
        for points in _simplify_owner_path(original_mask,chain):
            if len(points)<2:
                continue
            footprint=_footprint(points,2)
            if not _safe_owner_footprint(footprint,original_mask,outside):
                continue
            owned=np.flatnonzero(footprint & original_mask).astype(np.int32)
            if not len(owned):
                continue
            results.append({
                "points":points,"width":2,"vertices":len(points),
                "owned_index":owned,"kind":"direct_owner_skeleton",
            })
    return results


def source_plan(indexes, max_strokes=MAX_STROKES, max_vertices=MAX_VERTICES):
    checked_labels(indexes)
    if (type(max_strokes) is not int or type(max_vertices) is not int
            or max_strokes<FROZEN_DETAILS or
            max_vertices<FROZEN_DETAIL_VERTICES):
        raise ValueError("B3b invalid resource caps")
    masks={o:indexes==o for o in COLORS}
    if any(not masks[o].any() for o in COLORS):
        raise ValueError("B3b missing frozen original owner")
    remaining={o:masks[o].copy() for o in COLORS}
    areas={o:int(masks[o].sum()) for o in COLORS}
    outside={
        o:cv2.distanceTransform((~masks[o]).astype(np.uint8),
                                cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        for o in COLORS
    }
    paths=[]
    stats={o:Counter() for o in COLORS}
    revisits=Counter()
    vertices=FROZEN_DETAIL_VERTICES
    blocked=None

    def active_gain(option,owner):
        if "owned_index" in option:
            return int(np.count_nonzero(remaining[owner].ravel()[option["owned_index"]]))
        return int(np.count_nonzero(remaining[owner] & option["owned"]))

    def visited_old(option,owner):
        if "owned_index" in option:
            indices=option["owned_index"]
            return int(np.count_nonzero(
                masks[owner].ravel()[indices] & ~remaining[owner].ravel()[indices]))
        return int(np.count_nonzero(
            option["owned"] & masks[owner] & ~remaining[owner]))

    def clear(option,owner):
        if "owned_index" in option:
            remaining[owner].ravel()[option["owned_index"]]=False
        else:
            remaining[owner][option["owned"] & masks[owner]]=False

    def best_for_owner(heap, options, owner):
        while heap:
            _, idx, old_gain=heap[0]
            option=options[idx]
            gain=active_gain(option,owner)
            if gain!=old_gain:
                heapq.heappop(heap)
                if gain:
                    heapq.heappush(heap,(-gain/option["vertices"],idx,gain))
                continue
            if not gain:
                heapq.heappop(heap)
                continue
            return idx,option,gain
        return None

    for stage in STAGES:
        options={}
        heaps={}
        for owner in COLORS:
            mask=masks[owner]
            if stage.startswith("ring"):
                group=_make_ring_candidates(mask,int(stage[4:]),
                                            outside[owner])
            elif stage=="owner_skeleton2":
                group=direct_owner_skeleton_candidates(mask,
                                                       remaining[owner],
                                                       outside[owner])
            else:
                group=_make_micro_candidates(mask,remaining[owner])
            options[owner]=group
            heap=[]
            for i,c in enumerate(group):
                gain=active_gain(c,owner)
                if gain:
                    heapq.heappush(heap,(-gain/c["vertices"],i,gain))
            heaps[owner]=heap
        while True:
            contenders=[]
            for owner in COLORS:
                choice=best_for_owner(heaps[owner],options[owner],owner)
                if choice is None:
                    continue
                i,opt,gain=choice
                remaining_fraction=int(remaining[owner].sum())/areas[owner]
                # Per-owner fairness first, then own area gained per vertex.
                key=(remaining_fraction,gain/opt["vertices"],gain,-owner,-i)
                contenders.append((key,owner,i,opt,gain))
            if not contenders:
                break
            _,owner,i,opt,gain=max(contenders,key=lambda x:x[0])
            heapq.heappop(heaps[owner])
            attempt_vertices=vertices+opt["vertices"]
            attempt_strokes=len(paths)+1+FROZEN_DETAILS
            if attempt_vertices>max_vertices or attempt_strokes>max_strokes:
                blocked={
                    "status":"BLOCKED_RESOURCE",
                    "stage":stage, "owner":owner,
                    "first_rejected_ordinal":len(paths),
                    "attempted_total_strokes":attempt_strokes,
                    "attempted_synthetic_vertices_NOT_CHALK":attempt_vertices,
                    "no_partial_native_render":True,
                }
                break
            revisits[owner]+=visited_old(opt,owner)
            points=[{"x":float(x+ROI_X0),"y":float(y)}
                    for x,y in opt["points"]]
            paths.append({
                "strokeId":f"p4-b3b-{owner}-{len(paths):05d}",
                "colorIndex":owner,"width":opt["width"],
                "stage":stage,"points":points,
                "new_source_pixels_model_only":gain,
            })
            clear(opt,owner)
            vertices=attempt_vertices
            stats[owner][stage]+=1
        if blocked:
            break
    per={}
    for owner in COLORS:
        missing=int(remaining[owner].sum())
        per[str(owner)]={
            "source_pixels":areas[owner],
            "model_missing_pixels":missing,
            "source_model_coverage_NOT_NATIVE":(areas[owner]-missing)/areas[owner],
            "chosen_by_stage":dict(stats[owner]),
            "own_color_revisited_pixels_NOT_PENALIZED":revisits[owner],
        }
    low=any(x["source_model_coverage_NOT_NATIVE"]<MODEL_COVERAGE_GATE
            for x in per.values())
    return {
        "experiment":EXP,
        "stage":"SOURCE_MODEL_ONLY",
        "status":"BLOCKED_RESOURCE" if blocked else (
            "MODEL_LOW_COVERAGE" if low else
            "SOURCE_CANDIDATE_FOR_NATIVE_REVIEW"),
        "first_resource_blocker":blocked,
        "fixed_stage_order":list(STAGES),
        "source_owner_order":list(COLORS),
        "skeleton_simplify_max_lookahead_nodes":MAX_SKELETON_STRAIGHT_LOOKAHEAD,
        "same_owner_overlap_penalty":SAME_OWNER_OVERPAINT_PENALTY,
        "source_distance_limit_logical_px":MAX_OUTSIDE_OWNER_LOGICAL,
        "source_coverage_diagnostic_gate":MODEL_COVERAGE_GATE,
        "per_owner":per,
        "new_paint_strokes":len(paths),
        "total_strokes_including_frozen_contours":len(paths)+FROZEN_DETAILS,
        "synthetic_vertices_NOT_CHALK_including_details":vertices,
        "frozen_original_V44B_details_required_last":FROZEN_DETAILS,
        "frozen_original_detail_vertices":FROZEN_DETAIL_VERTICES,
        "original_A_B0_B1_B2_B3_B3a_paint_retained":0,
        "paint_model_only":paths,
        "safe_to_execute":False,
        "E3_native":"NOT_RUN","E4_game":"NOT_RUN",
        "E5_independent":"NOT_RUN","exact_game_CHALK":None,
        "production_accepted":False,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    a=parser.parse_args()
    if a.output.exists():
        raise ValueError("B3b refuses overwrite previous evidence")
    if sha(a.source)!=SOURCE_SHA:
        raise ValueError("B3b frozen source SHA drift")
    labels=original_labels(a.source)[::3,::3][:,ROI_X0:ROI_X0+SHAPE[1]].copy()
    report=source_plan(labels)
    report["source_sha256"]=SOURCE_SHA
    report["source_labels_sha256"]=hashlib.sha256(labels.tobytes()).hexdigest()
    a.output.mkdir(parents=True)
    (a.output/"b3b-original-owner-skeleton-source-report.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({
        "status":report["status"],
        "paint":report["new_paint_strokes"],
        "total":report["total_strokes_including_frozen_contours"],
        "vertices_NOT_CHALK":report[
            "synthetic_vertices_NOT_CHALK_including_details"],
        "model_source_coverage_NOT_EGRET":{
            k:v["source_model_coverage_NOT_NATIVE"]
            for k,v in report["per_owner"].items()},
        "safe_to_execute":False},ensure_ascii=False))


if __name__=="__main__":
    main()
