#!/usr/bin/env python3
"""ENGINE-001 P4c0: bounded ALL G32 owners B3 contour feasibility, MODEL_ONLY.

No native brush conclusions, no game/executor and no exact CHALK.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import os
import platform
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_color32_s2_edge_protection import strong_edges,protected_merge
from run_engine001_palette32_region_study import read_source,read_palette,nearest32,sha
from run_engine001_color32_s2b_egret_p1 import (
    FROZEN_PALETTE_GIT_BLOB,git_blob_sha,ROI_SHAPE,ROI_X0)
from run_engine001_v43p4_b3_contour_source import contour_candidates

EXP="ENGINE001_COLOR32_P4C0_ALL_OWNER_B3_RESOURCE_SOURCE_ONLY"
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
G_PNG_SHA="b8dcd5f00d2c39c81997aaae084eaae19a776454e6fd6466209839288c1e5637"
WHITE=30
WIDTHS=(10,6,4,2)
MAX_CANDIDATES_PER_WIDTH_OWNER=32
MAX_PAINT_STROKES=2590
MAX_PAINT_VERTICES=4108
FROZEN_DETAILS=410
FROZEN_DETAIL_VERTICES=1792
SOURCE_OUTSIDE_LIMIT=2.0
TARGET_MODEL_DIAGNOSTIC=.99


def _png_sha(indices):
    b=io.BytesIO()
    Image.fromarray(indices,"L").save(b,format="PNG")
    return hashlib.sha256(b.getvalue()).hexdigest()


def _validate(labels,palette):
    if (not isinstance(labels,np.ndarray) or labels.shape!=ROI_SHAPE or
        labels.dtype!=np.uint8 or int(labels.max())>=32 or
        not isinstance(palette,np.ndarray) or palette.shape!=(32,3) or
        palette.dtype!=np.uint8):
        raise ValueError("BLOCKED_P4C0_SOURCE_OR_PALETTE_SHAPE")
    owners=[int(x) for x in np.unique(labels) if int(x)!=WHITE]
    if not owners:
        raise ValueError("BLOCKED_P4C0_NO_COLOR_OWNERS")
    return owners


def _candidates_for(owner,mask,width,cap):
    """Reuse B3 implementation, return bounded sparse own-cell footprints."""
    background_dist=cv2.distanceTransform(
        (~mask).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    valid=[]
    generated=unsafe=bad=0
    for i,raw in enumerate(contour_candidates(mask,width)):
        generated+=1
        if not 2<=raw["vertices"]<=128:
            bad+=1
            continue
        fp=raw["footprint"]
        if np.any(fp & (~mask) & (background_dist>SOURCE_OUTSIDE_LIMIT)):
            unsafe+=1
            continue
        idx=np.flatnonzero(fp & mask).astype(np.int32)
        gain=len(idx)
        if not gain:continue
        # footprint index arrays are compact; do not retain 36000-cell bools
        valid.append((gain/raw["vertices"],gain,-raw["vertices"],-i,
                      i,raw["points"],raw["vertices"],idx))
    valid.sort(reverse=True)
    truncated=max(0,len(valid)-cap)
    selected=[]
    for score,gain,negvert,negi,i,points,vertices,idx in valid[:cap]:
        selected.append({"width":width,"owner":owner,"candidate_index":i,
                         "vertices":vertices,"points":points,
                         "own_indices":idx})
    return selected,{
        "generated":generated,
        "unsafe_model_beyond_2px":unsafe,
        "bad_vertices":bad,
        "eligible":len(valid),
        "retained":len(selected),"truncated":truncated
    }


def plan_all_owners(labels,palette,*,max_strokes=MAX_PAINT_STROKES,
                    max_vertices=MAX_PAINT_VERTICES,
                    cap=MAX_CANDIDATES_PER_WIDTH_OWNER):
    owners=_validate(labels,palette)
    if (type(max_strokes)!=int or not 0<max_strokes<=MAX_PAINT_STROKES or
        type(max_vertices)!=int or not 0<max_vertices<=MAX_PAINT_VERTICES or
        type(cap)!=int or not 0<cap<=MAX_CANDIDATES_PER_WIDTH_OWNER):
        raise ValueError("BLOCKED_P4C0_RESOURCE_ARGUMENT")
    masks={o:labels==o for o in owners}
    residual={o:masks[o].copy().ravel() for o in owners}
    targets={o:int(masks[o].sum()) for o in owners}
    count=vertices=0
    strokes=[]
    found_first_resource=None
    inventories={}
    counts={str(o):{str(w):0 for w in WIDTHS} for o in owners}
    for width in WIDTHS:
        candidates={}
        for owner in owners:
            candidates[owner],summary=_candidates_for(
                owner,masks[owner],width,cap)
            inventories[f"{owner}:{width}"]=summary
        used={o:set() for o in owners}
        while True:
            # Fairness: owner with most relative uncovered fraction first,
            # then marginal source-only gain per vertex. Deterministic ties.
            proposals=[]
            for owner in owners:
                own_left=residual[owner]
                if not np.any(own_left):
                    continue
                left_fraction=float(np.count_nonzero(own_left))/targets[owner]
                best=None
                for i,c in enumerate(candidates[owner]):
                    if i in used[owner]:
                        continue
                    gain=int(np.count_nonzero(own_left[c["own_indices"]]))
                    if gain<=0:
                        continue
                    score=(left_fraction,gain/c["vertices"],gain,-c["vertices"],-i)
                    if best is None or score>best[0]:
                        best=(score,i,c,gain)
                if best:
                    proposals.append((best[0],-owner,owner,best))
            if not proposals:
                break
            _,_,owner,(_,i,c,gain)=max(proposals)
            used[owner].add(i)
            if count+1>max_strokes or vertices+c["vertices"]>max_vertices:
                found_first_resource={
                    "reason":"BLOCKED_RESOURCE",
                    "owner":owner,"width":width,"candidate_index":c["candidate_index"],
                    "attempted_paint_strokes":count+1,
                    "attempted_paint_vertices_NOT_CHALK":vertices+c["vertices"],
                    "remaining_paint_vertices_NOT_CHALK":max_vertices-vertices,
                }
                break
            rgb=palette[owner]
            strokes.append({
                "strokeId":f"icon-{count}",
                "colorIndex":owner,
                "colorRgb":(int(rgb[0])<<16)|(int(rgb[1])<<8)|int(rgb[2]),
                "width":width,
                "points":[{"x":float(x+ROI_X0),"y":float(y)}
                          for x,y in c["points"]],
            })
            residual[owner][c["own_indices"]]=False
            count+=1
            vertices+=c["vertices"]
            counts[str(owner)][str(width)]+=1
        if found_first_resource:
            break
    measures={}
    for o in owners:
        left=int(np.count_nonzero(residual[o]))
        measures[str(o)]={
            "original_G_target_source_pixels":targets[o],
            "uncovered_SOURCE_MODEL_ONLY_pixels":left,
            "SOURCE_MODEL_ONLY_fraction":(targets[o]-left)/targets[o],
            "selected_by_width":counts[str(o)],
            "source_target_not_native":True,
        }
    deficient=[int(o) for o,m in measures.items()
               if m["SOURCE_MODEL_ONLY_fraction"]<TARGET_MODEL_DIAGNOSTIC]
    status=("BLOCKED_RESOURCE" if found_first_resource else
            "MODEL_LOW_OWNER_COVERAGE" if deficient else
            "SOURCE_CANDIDATE_NEEDS_NATIVE_E3")
    return strokes,{
        "experiment":EXP,"status":status,
        "source_model_only_NOT_NATIVE_EGRET":True,
        "source_swatch_count_including_white":len(np.unique(labels)),
        "nonwhite_owners":owners,
        "original_white_index":WHITE,
        "original_G_unchanged":True,
        "candidate_widths_desc":list(WIDTHS),
        "max_retained_candidate_per_owner_width":cap,
        "candidate_inventory_by_owner_width":inventories,
        "SOURCE_MODEL_ONLY_per_owner":measures,
        "owners_below_99_percent_SOURCE_MODEL_ONLY":deficient,
        "model_all_owners_99pct_diagnostic":not deficient,
        "source_model_outside_limit_logical_px":SOURCE_OUTSIDE_LIMIT,
        "game_foreign_3px":"NOT_RUN",
        "same_color_overpaint_penalty":0,
        "paint_strokes":count,"paint_vertices_NOT_CHALK":vertices,
        "reserved_original_V44B_detail_strokes_LAST":FROZEN_DETAILS,
        "reserved_original_V44B_detail_vertices_NOT_CHALK":FROZEN_DETAIL_VERTICES,
        "planned_total_strokes_with_V44B410":count+FROZEN_DETAILS,
        "planned_total_vertices_with_V44B1792_NOT_CHALK":vertices+FROZEN_DETAIL_VERTICES,
        "first_rejected_resource":found_first_resource,
        "partial_source_paths_not_accepted":status!="SOURCE_CANDIDATE_NEEDS_NATIVE_E3",
        "original_V44B_detail_unchanged_not_rendered":True,
        "safe_to_execute_game":False,"native_E3":"NOT_RUN",
        "live_E4":"NOT_RUN","E5":"NOT_RUN","exact_CHALK":None,
        "production_accepted":False,
    }


def run(source,palette_path,output):
    if output.exists():
        raise ValueError("BLOCKED_P4C0_IMMUTABLE_OUTPUT_EXISTS")
    if (sha(source)!=SOURCE_SHA or
        git_blob_sha(palette_path)!=FROZEN_PALETTE_GIT_BLOB):
        raise ValueError("BLOCKED_P4C0_SOURCE_DRIFT")
    _,rgb=read_source(source)
    palette=read_palette(palette_path)
    b=nearest32(rgb,palette)
    protected,_=strong_edges(rgb)
    g,_=protected_merge(rgb,b,palette,protected)
    if _png_sha(g)!=G_PNG_SHA:
        raise ValueError("BLOCKED_P4C0_FROZEN_G_DRIFT")
    strokes,measure=plan_all_owners(g,palette)
    output.mkdir(parents=True)
    Image.fromarray(g,"L").save(output/"frozen_G32_index.png")
    Image.fromarray(palette[g],"RGB").save(output/"frozen_G32_color.png")
    # Red means uncovered source pixels from this bounded model. This is a
    # model heatmap, NOT actual native BoardPane alpha.
    residual=np.zeros(ROI_SHAPE,np.uint8)
    byowner={int(x):g==int(x) for x in measure["nonwhite_owners"]}
    for s in strokes:
        mask=np.zeros(ROI_SHAPE,np.uint8)
        points=np.array([(round(p["x"]-ROI_X0),round(p["y"]))
                         for p in s["points"]],np.int32)
        cv2.polylines(mask,[points],False,255,s["width"],cv2.LINE_8)
        byowner[s["colorIndex"]][mask>0]=False
    for owner,mask in byowner.items():
        residual[mask]=255
    Image.fromarray(residual,"L").save(output/"source_model_uncovered_not_Egret.png")
    (output/"source_paths.json").write_text(json.dumps({
        "experiment":EXP,
        "source_only":True,"strokes":strokes,
        "V44B410_last_reserved_not_rendered":True,
        "exact_CHALK":None},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    links={str(p.relative_to(output)):sha(p) for p in output.iterdir() if p.is_file()}
    report={
        **measure,
        "github_sha":os.environ.get("GITHUB_SHA"),
        "github_run_id":os.environ.get("GITHUB_RUN_ID"),
        "source_sha256":sha(source),
        "palette_git_blob":FROZEN_PALETTE_GIT_BLOB,
        "G_frozen_index_png_sha":G_PNG_SHA,
        "source_only_artifacts_sha256":links,
        "versions":{"python":platform.python_version(),
                    "numpy":np.__version__,"opencv":cv2.__version__},
    }
    (output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return report


def main():
    ap=argparse.ArgumentParser()
    for option in ("source","palette","output"):
        ap.add_argument("--"+option,required=True,type=Path)
    a=ap.parse_args()
    r=run(a.source,a.palette,a.output)
    print(json.dumps({
        "experiment":EXP,"status":r["status"],
        "owners":r["nonwhite_owners"],
        "model_below99":r["owners_below_99_percent_SOURCE_MODEL_ONLY"],
        "paint_strokes":r["paint_strokes"],
        "paint_vertices_NOT_CHALK":r["paint_vertices_NOT_CHALK"],
        "projected_total_vertices_NOT_CHALK":r["planned_total_vertices_with_V44B1792_NOT_CHALK"],
        "first_resource_failure":r["first_rejected_resource"],
        "native_E3":"NOT_RUN","exact_CHALK":None},ensure_ascii=False))


if __name__=="__main__":
    main()
