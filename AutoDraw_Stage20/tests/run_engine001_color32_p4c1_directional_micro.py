#!/usr/bin/env python3
"""ENGINE-001 P4c1: frozen all-owner B3 rings + adaptive directed residuals.

Source-only MODEL; OpenCV footprint is not original Egret BoardPane ink or CHALK.
"""
from __future__ import annotations
import argparse
import hashlib
import heapq
import io
import json
import math
import os
import platform
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_color32_p4c0_all_owner_feasibility import (
    EXP as P4C0_EXP, plan_all_owners, _validate, _png_sha,
    SOURCE_SHA, G_PNG_SHA, WHITE, FROZEN_DETAILS,
    FROZEN_DETAIL_VERTICES, MAX_PAINT_STROKES, MAX_PAINT_VERTICES,
    SOURCE_OUTSIDE_LIMIT, ROI_SHAPE, ROI_X0,
)
from run_engine001_color32_s2b_egret_p3 import (
    _candidate as original_p3_candidate, _model_footprint,
)
from run_engine001_color32_s2_edge_protection import strong_edges,protected_merge
from run_engine001_palette32_region_study import read_source,read_palette,nearest32,sha
from run_engine001_color32_s2b_egret_p1 import (
    FROZEN_PALETTE_GIT_BLOB,git_blob_sha,
)

EXP="ENGINE001_COLOR32_P4C1_DIRECTIONAL_MICRO_ALL_OWNER_SOURCE_ONLY"
FROZEN_P4C0_PLAN_SHA="b9ca97fde1b3ed205b8b69cd3c6dc3bf6ef6af7d52060a3b1e93a07a1b1f7901"
WIDTHS=(30,15,10,6,4,2)
ANGLE_BASE=(0,45,90,135)
MAX_SEEDS_PER_OWNER=1024
TARGET_MODEL=.99
MIN_INCREMENTAL_GAIN_PP=1.0


def _frozen_base_paths_sha(paths):
    raw=(json.dumps({
        "experiment":P4C0_EXP,
        "source_only":True,
        "strokes":paths,
        "V44B410_last_reserved_not_rendered":True,
        "exact_CHALK":None,
    },indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _axis(xy):
    """Approximate major shape orientation modulo 180, 15-degree precision."""
    if len(xy)<3:
        return 135
    coords=np.asarray(xy,dtype=np.float64)
    centered=coords-coords.mean(axis=0)
    xx=float(np.dot(centered[:,0],centered[:,0]))
    yy=float(np.dot(centered[:,1],centered[:,1]))
    xyv=float(np.dot(centered[:,0],centered[:,1]))
    angle=.5*math.degrees(math.atan2(2*xyv,xx-yy))
    return int(round(angle/15)*15)%180


def _seeds_for(owner_mask,rem):
    """One seed for each residual 8conn island + compact source grid peaks."""
    dist=cv2.distanceTransform(owner_mask.astype(np.uint8),
                               cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    n,cc,stats,_=cv2.connectedComponentsWithStats(rem.astype(np.uint8),8)
    result=[]
    used=set()
    # Large source components first, then smaller source island diagnostics.
    order=sorted(range(1,n),
                 key=lambda i:(-int(stats[i,cv2.CC_STAT_AREA]),
                               int(stats[i,cv2.CC_STAT_TOP]),
                               int(stats[i,cv2.CC_STAT_LEFT])))
    for i in order:
        ys,xs=np.nonzero(cc==i)
        if not len(xs):
            continue
        best=int(np.argmax(dist[ys,xs]))
        x,y=int(xs[best]),int(ys[best])
        result.append((x,y,_axis(list(zip(xs,ys)))))
        used.add((x,y))
        if len(result)>=MAX_SEEDS_PER_OWNER:
            break
    original_components=n-1
    if len(result)<MAX_SEEDS_PER_OWNER:
        # Multiple seeds per broad residual region: deterministic 8x8 cells
        for cy in range(0,ROI_SHAPE[0],8):
            for cx in range(0,ROI_SHAPE[1],8):
                window=rem[cy:cy+8,cx:cx+8]
                if not np.any(window):
                    continue
                ys,xs=np.nonzero(window)
                ys=ys+cy; xs=xs+cx
                best=int(np.argmax(dist[ys,xs]))
                x,y=int(xs[best]),int(ys[best])
                if (x,y) in used:
                    continue
                local=owner_mask[max(y-5,0):min(y+6,ROI_SHAPE[0]),
                                 max(x-5,0):min(x+6,ROI_SHAPE[1])]
                ly,lx=np.nonzero(local)
                result.append((x,y,_axis(list(zip(lx,ly)))))
                used.add((x,y))
                if len(result)>=MAX_SEEDS_PER_OWNER:break
            if len(result)>=MAX_SEEDS_PER_OWNER:break
    return result,{
        "original_residual_8connected_components":int(original_components),
        "selected_seed_count":len(result),
        "seed_limit_reached":len(result)>=MAX_SEEDS_PER_OWNER,
    }


def _micro(owner,x,y,palette,mask,outside):
    """Two distinct subpixel endpoints in same logical source cell, model only."""
    if not (1<=x<ROI_SHAPE[1]-1 and 1<=y<ROI_SHAPE[0]-1
            and mask[y,x]):
        return None
    pts=[{"x":float(x+ROI_X0)+.125,"y":float(y)},
         {"x":float(x+ROI_X0)+.375,"y":float(y)}]
    fp=_model_footprint(pts,2)
    if np.any(fp & (~mask) & (outside>SOURCE_OUTSIDE_LIMIT)):
        return None
    idx=np.flatnonzero(fp & mask)
    if not len(idx):
        return None
    rgb=palette[owner]
    return {
        "width":2,"angle":0,
        "points":pts,"own_indices":idx.astype(np.int32),
        "colorRgb":(int(rgb[0])<<16)|(int(rgb[1])<<8)|int(rgb[2]),
        "micro":True,
    }


def _build_owner_candidates(owner,mask,residual,palette):
    seeds,seed_stats=_seeds_for(mask,residual.reshape(ROI_SHAPE))
    dist=cv2.distanceTransform(mask.astype(np.uint8),
                               cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    outside=cv2.distanceTransform((~mask).astype(np.uint8),
                                  cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    candidates=[]
    dedup=set()
    rejected_far=0
    for si,(x,y,principal) in enumerate(seeds):
        angles=[0,45,90,135,principal]
        # At most 4, keep locally relevant principal and broad orientations.
        angles=sorted(set(angles),
                      key=lambda angle:(min(abs(angle-principal),
                          180-abs(angle-principal)),angle))[:4]
        regular=False
        for width in WIDTHS:
            for angle in angles:
                item=original_p3_candidate(owner,(x,y),width,angle,mask,
                                            dist,outside,palette)
                if item is None:
                    continue
                points=item["points"]
                fp=_model_footprint(points,width)
                if np.any(fp & (~mask) & (outside>SOURCE_OUTSIDE_LIMIT)):
                    rejected_far+=1
                    continue
                # Additional ROI margin: no width>2 centerline near edge.
                margin=max(0.,width/2.0-SOURCE_OUTSIDE_LIMIT)
                if any(p["x"]-ROI_X0<margin or
                       p["x"]-ROI_X0>ROI_SHAPE[1]-1-margin or
                       p["y"]<margin or
                       p["y"]>ROI_SHAPE[0]-1-margin for p in points):
                    continue
                key=(width,angle,
                     tuple((p["x"],p["y"]) for p in points))
                if key in dedup:
                    continue
                dedup.add(key)
                idx=np.flatnonzero(fp & mask).astype(np.int32)
                if not len(idx):
                    continue
                candidates.append({
                    "width":width,"angle":angle,
                    "owner":owner,"seed_index":si,
                    "points":points,"own_indices":idx,
                    "colorRgb":item["colorRgb"],
                    "micro":False,
                })
                regular=True
        if not regular:
            item=_micro(owner,x,y,palette,mask,outside)
            if item is not None:
                key=(2,0,tuple((p["x"],p["y"]) for p in item["points"]))
                if key not in dedup:
                    dedup.add(key)
                    item.update(owner=owner,seed_index=si)
                    candidates.append(item)
    return candidates,{
        **seed_stats,
        "directional_source_candidates":len(candidates),
        "micro_candidates":sum(bool(c["micro"]) for c in candidates),
        "rejected_source_model_beyond_2px":rejected_far,
        "same_owner_overlap_penalty":0,
    }


def plan_residual(g,palette,base_paths,*,max_paint_strokes=MAX_PAINT_STROKES,
                  max_paint_vertices=MAX_PAINT_VERTICES):
    owners=_validate(g,palette)
    if (type(max_paint_strokes)!=int or type(max_paint_vertices)!=int or
        not 1<=max_paint_strokes<=MAX_PAINT_STROKES or
        not 2<=max_paint_vertices<=MAX_PAINT_VERTICES):
        raise ValueError("BLOCKED_P4C1_BUDGET_ARGUMENT")
    if not isinstance(base_paths,list) or not base_paths:
        raise ValueError("BLOCKED_P4C1_EMPTY_BASE")
    if any(s["colorIndex"] not in owners for s in base_paths):
        raise ValueError("BLOCKED_P4C1_BASE_OWNERS")
    existing_count=len(base_paths)
    existing_vertices=sum(len(s["points"]) for s in base_paths)
    if existing_count>max_paint_strokes or existing_vertices>max_paint_vertices:
        raise ValueError("BLOCKED_P4C1_EXISTING_BUDGET")
    masks={o:g==o for o in owners}
    remaining={o:masks[o].copy().ravel() for o in owners}
    for s in base_paths:
        rem=remaining[s["colorIndex"]]
        fp=_model_footprint(s["points"],s["width"]).ravel()
        rem[fp]=False
    totals={o:int(masks[o].sum()) for o in owners}
    baseline={o:int(np.count_nonzero(remaining[o])) for o in owners}
    candidates={}
    source_inventory={}
    heaps={}
    for o in owners:
        candidates[o],source_inventory[str(o)]=_build_owner_candidates(
            o,masks[o],remaining[o],palette)
        heap=[]
        for i,c in enumerate(candidates[o]):
            gain=int(np.count_nonzero(remaining[o][c["own_indices"]]))
            if gain:
                heapq.heappush(heap,(-gain,c["width"],c["angle"],
                                     c["seed_index"],i))
        heaps[o]=heap

    def best_available(o):
        heap=heaps[o]
        while heap:
            neg,_,_,_,i=heap[0]
            c=candidates[o][i]
            actual=int(np.count_nonzero(remaining[o][c["own_indices"]]))
            if actual != -neg:
                heapq.heappop(heap)
                if actual:
                    heapq.heappush(heap,(-actual,c["width"],c["angle"],
                                         c["seed_index"],i))
                continue
            if actual<=0:
                heapq.heappop(heap)
                continue
            return c,i,actual
        return None

    added=[]
    first_resource=None
    histogram=Counter()
    angles=Counter()
    while True:
        proposal=[]
        for o in owners:
            if int(np.count_nonzero(remaining[o]))/totals[o] <= 1.-TARGET_MODEL:
                continue
            choice=best_available(o)
            if choice is None:
                continue
            c,i,gain=choice
            residual_frac=int(np.count_nonzero(remaining[o]))/totals[o]
            # Fairness followed by source own gain/2 (every candidate 2 points).
            score=(residual_frac,gain/2.,gain,-o,-c["width"],
                   -c["angle"],-c["seed_index"])
            proposal.append((score,o,i,c,gain))
        if not proposal:
            break
        _,o,i,c,gain=max(proposal,key=lambda t:t[0])
        if (existing_count+len(added)+1>max_paint_strokes or
            existing_vertices+2*(len(added)+1)>max_paint_vertices):
            first_resource={
                "reason":"BLOCKED_RESOURCE",
                "owner":o,"width":c["width"],"angle":c["angle"],
                "attempted_total_paint_strokes":existing_count+len(added)+1,
                "attempted_total_paint_vertices_NOT_CHALK":
                    existing_vertices+2*(len(added)+1),
            }
            break
        # The selected proposal is the current peek; discard it.
        old=heapq.heappop(heaps[o])
        if old[-1]!=i:
            raise AssertionError("P4c1 lazy greedy peak drift")
        s={"strokeId":f"icon-{existing_count+len(added)}",
           "colorIndex":o,"colorRgb":c["colorRgb"],
           "width":c["width"],"points":c["points"]}
        added.append(s)
        remaining[o][c["own_indices"]]=False
        histogram[str(c["width"])]+=1
        angles[str(c["angle"])]+=1
    ending={}
    changed_model=0
    for o in owners:
        left=int(np.count_nonzero(remaining[o]))
        improved=baseline[o]-left
        coverage=(totals[o]-left)/totals[o]
        before=(totals[o]-baseline[o])/totals[o]
        gain_pp=100.*improved/totals[o]
        changed_model=max(changed_model,gain_pp)
        ending[str(o)]={
            "source_original_target_pixels":totals[o],
            "baseline_P4c0_model_uncovered_pixels":baseline[o],
            "source_model_after_uncovered_pixels":left,
            "original_P4c0_SOURCE_MODEL_pct":100.*before,
            "P4c1_SOURCE_MODEL_pct":100.*coverage,
            "incremental_SOURCE_MODEL_pp":gain_pp,
        }
    deficient=[o for o in owners if
               ending[str(o)]["P4c1_SOURCE_MODEL_pct"]<99.]
    status=("BLOCKED_RESOURCE" if first_resource else
            "SOURCE_INCREMENTAL_PASS_NATIVE_PENDING"
            if changed_model>=MIN_INCREMENTAL_GAIN_PP else
            "MODEL_LOW_INCREMENTAL_GAIN")
    return added,{
        "experiment":EXP,"status":status,
        "baseline_P4c0_paths":existing_count,
        "baseline_P4c0_vertices_NOT_CHALK":existing_vertices,
        "additional_strokes":len(added),"additional_vertices_NOT_CHALK":2*len(added),
        "max_P4c1_source_incremental_gain_pp":changed_model,
        "source_incremental_at_least_1pp":changed_model>=MIN_INCREMENTAL_GAIN_PP,
        "owners_at_or_beyond99_SOURCE_MODEL_ONLY":[o for o in owners if o not in deficient],
        "owners_below99_SOURCE_MODEL_ONLY":deficient,
        "model_only_per_owner":ending,
        "original_owners":owners,
        "source_candidate_inventory":source_inventory,
        "width_histogram":dict(histogram),
        "angle_mod180_histogram":dict(angles),
        "micro_strokes_0_25_logical_MODEL_ONLY":sum(
            abs(s["points"][1]["x"]-s["points"][0]["x"])<0.5 and
            s["width"]==2 for s in added),
        "source_only_halo_limit_logical_px":SOURCE_OUTSIDE_LIMIT,
        "candidate_widths":list(WIDTHS),
        "angle_precision_all_360_not_tested":True,
        "same_color_overpainting_penalty":0,
        "total_paint_strokes":existing_count+len(added),
        "total_paint_vertices_NOT_CHALK":existing_vertices+2*len(added),
        "projected_total_strokes_with_frozen_V44B410_LAST":
            existing_count+len(added)+FROZEN_DETAILS,
        "projected_total_vertices_with_frozen_V44B1792_NOT_CHALK":
            existing_vertices+2*len(added)+FROZEN_DETAIL_VERTICES,
        "first_resource_rejection":first_resource,
        "partial_candidate_not_approved_for_execution":True,
        "original_410_colored_details_LAST_not_rendered":True,
        "full_Egret_alpha24_128":"NOT_RUN",
        "game_E4":"NOT_RUN","independent_E5":"NOT_RUN",
        "exact_CHALK":None,"production_accepted":False,
    }


def run(source,palette_path,output):
    if output.exists():
        raise ValueError("BLOCKED_P4C1_IMMUTABLE_OUTPUT")
    if (sha(source)!=SOURCE_SHA or
            git_blob_sha(palette_path)!=FROZEN_PALETTE_GIT_BLOB):
        raise ValueError("BLOCKED_P4C1_SOURCE_DRIFT")
    _,rgb=read_source(source)
    palette=read_palette(palette_path)
    b=nearest32(rgb,palette)
    protected,_=strong_edges(rgb)
    g,_=protected_merge(rgb,b,palette,protected)
    if _png_sha(g)!=G_PNG_SHA:
        raise ValueError("BLOCKED_P4C1_ORIGINAL_G_DRIFT")
    base,base_report=plan_all_owners(g,palette)
    if (base_report["status"]!="MODEL_LOW_OWNER_COVERAGE" or
            len(base)!=119 or
            sum(len(s["points"]) for s in base)!=1457 or
            _frozen_base_paths_sha(base)!=FROZEN_P4C0_PLAN_SHA):
        raise ValueError("BLOCKED_P4C1_FROZEN_P4C0_BASELINE_DRIFT")
    additions,info=plan_residual(g,palette,base)
    output.mkdir(parents=True)
    Image.fromarray(g,"L").save(output/"original_G32_index.png")
    Image.fromarray(palette[g],"RGB").save(output/"original_G32_RGB.png")
    before={int(o):g==int(o) for o in info["original_owners"]}
    after={int(o):g==int(o) for o in info["original_owners"]}
    for p in base:
        fp=_model_footprint(p["points"],p["width"])
        before[p["colorIndex"]][fp]=False
    for o in before:
        after[o][:]=before[o]
    for p in additions:
        fp=_model_footprint(p["points"],p["width"])
        after[p["colorIndex"]][fp]=False
    out_before=np.zeros(ROI_SHAPE,np.uint8)
    out_after=np.zeros(ROI_SHAPE,np.uint8)
    for o in before:
        out_before[before[o]]=255
        out_after[after[o]]=255
    Image.fromarray(out_before,"L").save(output/"P4c0_SOURCE_MODEL_uncovered.png")
    Image.fromarray(out_after,"L").save(output/"P4c1_SOURCE_MODEL_uncovered.png")
    (output/"source_paths.json").write_text(json.dumps({
        "experiment":EXP,
        "source_only":True,
        "frozen_P4c0_119_strokes_SHA256":FROZEN_P4C0_PLAN_SHA,
        "original_P4c0_strokes":base,
        "P4c1_additions":additions,
        "safe_to_execute_game":False,"exact_CHALK":None,
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    files={str(p.relative_to(output)):sha(p) for p in output.iterdir()
           if p.is_file()}
    report={
        **info,
        "original_P4c0_strokes_SHA256":FROZEN_P4C0_PLAN_SHA,
        "original_P4c0_run_id":44096977608,
        "original_P4c0_report_sha256":
            "9bf7a13cfa317fabae753e485d4f611db4ba0689c57af20bc6f4fb9c6022ca07",
        "github_sha":os.environ.get("GITHUB_SHA"),
        "github_run_id":os.environ.get("GITHUB_RUN_ID"),
        "source_sha256":sha(source),
        "original_G_index_png_SHA256":G_PNG_SHA,
        "game_palette_git_blob":FROZEN_PALETTE_GIT_BLOB,
        "source_file_sha256":files,
        "versions":{"python":platform.python_version(),
                    "numpy":np.__version__,"opencv":cv2.__version__},
    }
    (output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser()
    for name in ("source","palette","output"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    report=run(a.source,a.palette,a.output)
    print(json.dumps({
        "status":report["status"],
        "extra_strokes":report["additional_strokes"],
        "extra_vertices":report["additional_vertices_NOT_CHALK"],
        "source_below99":report["owners_below99_SOURCE_MODEL_ONLY"],
        "max_gain_pp":report["max_P4c1_source_incremental_gain_pp"],
        "total_with_410_V44B_NOT_CHALK":
           report["projected_total_vertices_with_frozen_V44B1792_NOT_CHALK"],
        "game_E4":"NOT_RUN","exact_CHALK":None
    },ensure_ascii=False))


if __name__=="__main__":
    main()
