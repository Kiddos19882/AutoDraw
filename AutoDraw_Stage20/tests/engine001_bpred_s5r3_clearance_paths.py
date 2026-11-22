#!/usr/bin/env python3
"""S5-R3, E0 clearance-guided long strokes, source pixels, normal no smoothing.

Ideal capsule only. This is not calibrated game-space ink.
"""
from __future__ import annotations

import hashlib
import io
import json

import numpy as np
from scipy import ndimage
import engine001_bpred_s5r2_region_candidates as source

VERSION="ENGINE001_BPRED_S5R3_CLEARANCE_LONG_PATH_V1"


def _digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),
                                     allow_nan=False).encode()).hexdigest()


def build_candidates(arrays, *, max_trials=2000, max_strokes=200):
    if type(max_trials) is not int or max_trials<1 or max_trials>2000:
        raise source.BlockedS5R2("BLOCKED_S5R3_BUDGET_TRIAL")
    if type(max_strokes) is not int or max_strokes<1 or max_strokes>200:
        raise source.BlockedS5R2("BLOCKED_S5R3_BUDGET_STROKE")
    game, ids, rgba, protected, opaque=source._source_arrays(arrays)
    h,w=game.shape
    seeds, dot_count=source._priority_seeds(ids,opaque,protected)
    # Distances in source PIXELS are preflight only, not native Egret clearance.
    walls=np.zeros((h,w),dtype=bool)
    walls[0]=walls[-1]=True
    walls[:,0]=walls[:,-1]=True
    walls[:,1:] |= ids[:,1:] != ids[:,:-1]
    walls[:,:-1] |= ids[:,1:] != ids[:,:-1]
    walls[1:,:] |= ids[1:,:] != ids[:-1,:]
    walls[:-1,:] |= ids[1:,:] != ids[:-1,:]
    walls |= ~opaque
    clearance=ndimage.distance_transform_edt(~walls)
    covered=np.zeros((h,w),bool)
    guaranteed=np.zeros((h,w),bool)
    strokes=[]
    totals={"broad":0,"detail":0}
    trials={"broad":0,"detail":0}
    rejected={"unsafe":0,"zero_gain":0,"coarse":0}
    evaluated_regions=set()
    feasible_regions=set()

    def accept(phase, region, start, end, size, footprint):
        gained=sum(not covered[y,x] for x,y in footprint["potential_cells"])
        touched=sum(protected[y,x] and not covered[y,x]
                    for x,y in footprint["potential_cells"])
        for x,y in footprint["potential_cells"]: covered[y,x]=True
        for x,y in footprint["guaranteed_cells"]: guaranteed[y,x]=True
        strokes.append({"phase":phase,"paintable_id":region,
                        "color_index":int(game[int(start[1]),int(start[0])]),
                        "points":[[float(start[0]),float(start[1])],
                                  [float(end[0]),float(end[1])]],
                        "brush_value":size,"drawing_mode":"normal","smooth":False,
                        "safe_to_execute":False,"status":"MODEL_ONLY_NON_EXECUTABLE",
                        "modeled_new_potential_cells":gained,
                        "modeled_protected_dots_newly_touched":int(touched)})
        totals[phase]+=1

    def test_candidate(phase,region,start,end,size):
        max_phase=1400 if phase=="broad" else 600
        if trials[phase]>=max_phase: return None
        trials[phase]+=1
        model=source.swept_capsule_pixel_masks((start,end),size,1.,1.,w,h)
        potential=model["potential_cells"]
        if not potential or any(ids[y,x]!=region or not opaque[y,x]
                                for x,y in potential):
            rejected["unsafe"]+=1
            return None
        new=sum(not covered[y,x] for x,y in potential)
        if new==0:
            rejected["zero_gain"]+=1
            return None
        return (new,len(model["guaranteed_cells"]),size),model

    # Each seed's orientation is evaluated over full clearance-safe intervals,
    # not a fixed 2/6/12px local extension. Construct two cardinal long
    # centerlines. This is a single S5-R3 research scheduler.
    for region,center,dot,area,maximum in sorted(
            seeds,key=lambda row:(-row[3],-row[4],row[0])):
        if totals["broad"]>=min(80,max_strokes) or trials["broad"]>=min(1400,max_trials):
            break
        if area < 6 or maximum < 1.5: continue
        evaluated_regions.add(region)
        cx,cy=center
        best=None
        preferred=min(10,max(2,int((maximum-.71)*2)))
        for size in tuple(dict.fromkeys((preferred,max(2,preferred//2),2))):
            if trials["broad"]>=min(1400,max_trials): break
            # Require enough clearance to include a whole unit cell with
            # margin; model will perform exact conservative potential check.
            threshold=size/2+.72
            for vertical in (False,True):
                if clearance[cy,cx] < threshold:
                    rejected["coarse"]+=1
                    continue
                if vertical:
                    line_ids=ids[:,cx]; line_clr=clearance[:,cx]
                    at=cy; limit=h
                else:
                    line_ids=ids[cy,:]; line_clr=clearance[cy,:]
                    at=cx; limit=w
                lo=at; hi=at
                while lo>0 and line_ids[lo-1]==region and line_clr[lo-1]>=threshold:
                    lo-=1
                while hi<limit-1 and line_ids[hi+1]==region and line_clr[hi+1]>=threshold:
                    hi+=1
                if hi-lo<2:
                    rejected["coarse"]+=1
                    continue
                start=(float(cx),float(lo)) if vertical else (float(lo),float(cy))
                end=(float(cx),float(hi)) if vertical else (float(hi),float(cy))
                option=test_candidate("broad",region,start,end,size)
                if option is None: continue
                feasible_regions.add(region)
                score,footprint=option
                if best is None or score>best[0]:
                    best=(score,start,end,size,footprint)
        if best is not None:
            _,start,end,size,footprint=best
            accept("broad",region,start,end,size,footprint)

    # Preserved two-ledger detail budget / source-protected dot priority.
    if max_trials>1400 and max_strokes>80:
        yy,xx=np.nonzero(protected & ~covered)
        for y,x in zip(yy.tolist(),xx.tolist()):
            if totals["detail"]>=min(120,max_strokes-80) or \
                    trials["detail"]>=min(600,max_trials-1400):
                break
            region=int(ids[y,x])
            center=(float(x),float(y))
            value=test_candidate("detail",region,center,center,1)
            if value:
                accept("detail",region,center,center,1,value[1])
        if totals["detail"]<min(120,max_strokes-80) and \
                trials["detail"]<min(600,max_trials-1400):
            yy,xx=np.nonzero(opaque & ~covered)
            for y,x in zip(yy.tolist(),xx.tolist()):
                if totals["detail"]>=min(120,max_strokes-80) or \
                        trials["detail"]>=min(600,max_trials-1400):
                    break
                region=int(ids[y,x]); center=(float(x),float(y))
                value=test_candidate("detail",region,center,center,1)
                if value: accept("detail",region,center,center,1,value[1])

    resid=int(np.count_nonzero(opaque & ~covered))
    result={"schema":VERSION,"status":"PARTIAL" if resid else "MODEL_ONLY",
        "source_shape":[int(h),int(w)],"drawing_mode":"normal","smooth":False,
        "source_owner_status":"MISSING","native_calibration":"UNVERIFIED",
        "native_Egret":"NOT_RUN","coordinates":"ORIGINAL_PIXEL_CENTERS_NOT_EGRET",
        "safe_to_execute":False,"admissible_for_gameplay":False,
        "visible_pixel_count":int(opaque.sum()),
        "potential_covered_pixel_count":int((opaque & covered).sum()),
        "guaranteed_covered_pixel_count":int((opaque & guaranteed).sum()),
        "uncovered_potential_pixel_count":resid,
        "protected_original_dot_count":dot_count,
        "protected_dot_potential_covered":int((protected & covered).sum()),
        "protected_dot_remaining":int((protected & ~covered).sum()),
        "regions_total":len(seeds),
        "regions_broad_evaluated":len(evaluated_regions),
        "regions_feasible_corridors":len(feasible_regions),
        "phase_strokes":totals,"phase_trials":trials,
        "stroke_count":len(strokes),"trials":sum(trials.values()),
        "rejected":rejected,"proposals":strokes}
    result["result_sha256"]=_digest(result)
    return result


def build_from_verified_s46(meta_bytes,raw_bytes,original_bytes,**kwargs):
    import engine001_bpred_s4r1_s46_source_contract as s46
    meta=s46.verify_quarantined(meta_bytes,raw_bytes,original_bytes)
    if not (meta.get("source_original_only") is True
            and meta.get("source_owner_status")=="MISSING"
            and meta.get("native_calibration")=="UNVERIFIED"
            and meta.get("admissible_for_gameplay") is False):
        raise source.BlockedS5R2("BLOCKED_S5R3_SOURCE")
    with np.load(io.BytesIO(raw_bytes),allow_pickle=False) as packet:
        arrays={k:packet[k] for k in
                ("game_index","paintable_id","original_rgba","protected_original_dot")}
    result=build_candidates(arrays,**kwargs)
    result["source_packet_sha256"]=hashlib.sha256(meta_bytes).hexdigest()
    result["input_sha256"]=meta["input_sha256"]
    result["engine_git_blob_sha1"]=meta["engine_git_blob_sha1"]
    result["result_sha256"]=_digest({k:v for k,v in result.items()
                                    if k!="result_sha256"})
    return result
