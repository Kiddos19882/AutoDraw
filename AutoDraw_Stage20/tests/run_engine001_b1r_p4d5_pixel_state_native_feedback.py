#!/usr/bin/env python3
"""ENGINE-001 P4D5: native pixel-state 0/1 owner-aware fill-search PILOT.

Original B1-R P3D E/F source, native Egret 5.4.1 BoardPane WebGL exact-position
isolated probes and cumulative feedback after every accepted stroke.
cv2 is ONLY a bounded candidate proposal heuristic, NEVER native evidence.
No production/export/executor behavior is changed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as p4d0
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import read_webgl_result

EXPERIMENT="ENGINE001_B1R_P4D5_PIXEL_STATE_NATIVE_FEEDBACK_V1"
PREREG="ENGINE001_B1R_P4D5_PIXEL_STATE_NATIVE_FEEDBACK_PREREG_2026-11-19.md"
SOURCE_SHA=p4d0.SOURCE_SHA
SOURCE=p4d0.SOURCE
METHODS=p4d0.METHODS
WHITE=p4d0.WHITE
CROP=(40,45,64,69)  # x0,y0,x1,y1, frozen on original 150x240 index
SCALE=3
BOARD_SHAPE=(720,1380,4)
X0=p4d0.X0
ALPHA=24
RGB_TOL=32
LOGICAL_REQUIRED_SUBPIXELS=5  # out of nine backing pixels in each 3x3
MAX_NATIVE_PROBES=240  # finite pilot diagnostic; never a quality gate
MIN_WIDTH1_PROBES=60
DIRECTIONS=((1,0),(0,1),(1,1),(1,-1))
CMD=("return window.AutoDrawGameRendererReference."
     "renderP4A2BrushWidths1to10Probe(arguments[0]);")


def _rgb(owner:int,palette:np.ndarray)->int:
    c=palette[owner]
    return int(c[0])*65536+int(c[1])*256+int(c[2])


def make_stroke(owner:int,palette:np.ndarray,width:int,
                x0:float,y0:float,x1:float,y1:float)->dict:
    if not(0<=owner<128 and owner!=WHITE and 1<=width<=10 and
           0<=x0<150 and 0<=x1<150 and 0<=y0<240 and 0<=y1<240):
        raise ValueError("BLOCKED_P4D5_STROKE_ARGS")
    return {"strokeId":"icon-0","colorIndex":owner,
            "colorRgb":_rgb(owner,palette),"width":int(width),
            "points":[{"x":float(X0+x0),"y":float(y0)},
                      {"x":float(X0+x1),"y":float(y1)}]}


def _renumber(strokes:list[dict])->list[dict]:
    return p4c0.renumber(strokes)


def crop_target(index:np.ndarray)->np.ndarray:
    if index.shape!=(240,150) or index.dtype!=np.uint8:
        raise ValueError("BLOCKED_P4D5_INDEX_SHAPE")
    x0,y0,x1,y1=CROP
    mask=np.zeros_like(index,dtype=bool)
    mask[y0:y1,x0:x1]=index[y0:y1,x0:x1]!=WHITE
    return mask


def _source_candidate(owner:int,width:int,points:list[tuple[int,int]],
                      palette:np.ndarray,index:np.ndarray):
    """MODEL_ONLY geometric screening; every passing candidate needs native probe."""
    if not points or len(points)>128:
        return None
    x0,y0=points[0]
    x1,y1=points[-1]
    mask=np.zeros(index.shape,np.uint8)
    cv2.line(mask,(x0,y0),(x1,y1),255,thickness=width,lineType=cv2.LINE_8)
    hits=mask!=0
    roi=crop_target(index)
    if (np.any(hits & (~roi)) or np.any(hits & (index!=owner))
        or not np.any(hits)):
        return None
    if x0==x1 and y0==y1:  # real two accepted points, not duplicate
        b0,b1=(x0+.125,y0),(x0+.375,y0)
    else:
        b0,b1=(x0+.125,y0+.125),(x1+.125,y1+.125)
    return {"stroke":make_stroke(owner,palette,width,*b0,*b1),
            "model_gain_ONLY":int(hits.sum()),
            "line_length_logical":float(np.hypot(x1-x0,y1-y0)),
            "model_only":True}


def candidate_pool(index:np.ndarray,palette:np.ndarray)->list[dict]:
    """Proposal lanes in all four undirected directions × all 10 widths.

    Prioritize real owner coverage, always retain >=60 width1 fallback probes.
    No translated native footprint assumption is made.
    """
    roi=crop_target(index)
    owners=sorted(int(v) for v in np.unique(index[roi]) if int(v)!=WHITE)
    if not owners:
        raise ValueError("BLOCKED_P4D5_EMPTY_CROP")
    by_owner=defaultdict(list)
    x0,y0,x1,y1=CROP
    for owner in owners:
        full=(index==owner).astype(np.uint8)
        dist=cv2.distanceTransform(np.pad(full,1),cv2.DIST_L2,
                                   cv2.DIST_MASK_PRECISE)[1:-1,1:-1]
        for width in range(10,0,-1):
            allowed=(dist>=width/2+.22) & roi & (index==owner)
            for dx,dy in DIRECTIONS:
                for y in range(y0,y1):
                    for x in range(x0,x1):
                        if not allowed[y,x]:
                            continue
                        prev_y,prev_x=y-dy,x-dx
                        if (x0<=prev_x<x1 and y0<=prev_y<y1 and
                            allowed[prev_y,prev_x]):
                            continue
                        walk=[(x,y)]
                        px,py=x,y
                        while (x0<=px+dx<x1 and y0<=py+dy<y1 and
                               allowed[py+dy,px+dx]):
                            px+=dx;py+=dy
                            walk.append((px,py))
                        if len(walk)>=2:
                            prop=_source_candidate(owner,width,walk,palette,index)
                            if prop is not None:
                                by_owner[owner].append(prop)
        # Width-1 single-pixel strokes reserve fine-grained residual attempts.
        for y,x in np.argwhere(roi & (index==owner)):
            prop=_source_candidate(owner,1,[(int(x),int(y))],palette,index)
            if prop is not None:
                by_owner[owner].append(prop)
    dedup=set()
    for owner in owners:
        filtered=[]
        for prop in by_owner[owner]:
            s=prop["stroke"]
            key=(owner,s["width"],tuple((p["x"],p["y"]) for p in s["points"]))
            if key not in dedup:
                dedup.add(key)
                filtered.append(prop)
        by_owner[owner]=filtered
    # Expose varied owners before one large color dominates the pilot.
    sorted_groups={}
    for owner in owners:
        sorted_groups[owner]=sorted(by_owner[owner],
            key=lambda p:(-p["model_gain_ONLY"],-p["stroke"]["width"],
                          -p["line_length_logical"],
                          p["stroke"]["points"][0]["y"],
                          p["stroke"]["points"][0]["x"]))
    wide={o:[p for p in sorted_groups[o] if p["stroke"]["width"]>1] for o in owners}
    fine={o:[p for p in sorted_groups[o] if p["stroke"]["width"]==1] for o in owners}
    # Round robin each owner, preserving candidate ranking within owner.
    def allocate(groups,quota):
        chosen=[]
        ptr={o:0 for o in owners}
        while len(chosen)<quota:
            changed=False
            for owner in owners:
                if ptr[owner]<len(groups[owner]):
                    chosen.append(groups[owner][ptr[owner]])
                    ptr[owner]+=1
                    changed=True
                    if len(chosen)==quota:
                        break
            if not changed:
                break
        return chosen
    selected=allocate(wide,MAX_NATIVE_PROBES-MIN_WIDTH1_PROBES)
    selected+=allocate(fine,MAX_NATIVE_PROBES-len(selected))
    if len(selected)>MAX_NATIVE_PROBES:
        raise AssertionError("BLOCKED_P4D5_PROBE_LIMIT")
    # no duplication introduced across wide and fine; stable ids for evidence
    for i,prop in enumerate(selected):
        prop["candidate_id"]=f"candidate-{i:04d}"
    return selected


def backing_allowed(index:np.ndarray,owner:int):
    """Full native-board bool mask; true only inside patch, on this owner."""
    if index.shape!=(240,150):
        raise ValueError("BLOCKED_P4D5_INDEX_SHAPE")
    allow=crop_target(index) & (index==owner)
    full=np.zeros(BOARD_SHAPE[:2],dtype=bool)
    full[:,X0*SCALE:(X0+150)*SCALE]=np.repeat(
        np.repeat(allow,SCALE,axis=0),SCALE,axis=1)
    return full


def real_composite_rgb(native:np.ndarray):
    if native.shape!=BOARD_SHAPE or native.dtype!=np.uint8:
        raise ValueError("BLOCKED_P4D5_NOT_NATIVE")
    # Preserve exact Pillow's RGBA-over-white composite behavior.
    return np.asarray(p4c0.preview_native(native),dtype=np.uint8)


def actual_state(native:np.ndarray,index:np.ndarray,palette:np.ndarray)->np.ndarray:
    """Fresh state from cumulative real Egret image; NOT union of brush models."""
    if palette.shape!=(128,3):
        raise ValueError("BLOCKED_P4D5_BAD_PALETTE")
    expected=np.repeat(np.repeat(palette[index],SCALE,0),SCALE,1)
    observed=real_composite_rgb(native)
    ink=native[:,X0*SCALE:(X0+150)*SCALE,3]>=ALPHA
    good=ink & (np.max(np.abs(observed.astype(np.int16)-
                           expected.astype(np.int16)),axis=2)<=RGB_TOL)
    count=good.reshape(240,SCALE,150,SCALE).sum(axis=(1,3))
    return (count>=LOGICAL_REQUIRED_SUBPIXELS) & crop_target(index)


def single_native_candidate(candidate:dict,native:np.ndarray,
                            index:np.ndarray,palette:np.ndarray):
    owner=int(candidate["stroke"]["colorIndex"])
    if candidate["stroke"]["colorRgb"]!=_rgb(owner,palette):
        raise ValueError("BLOCKED_P4D5_FOREIGN_STROKE_SWATCH")
    ink=native[:,:,3]>=ALPHA
    allowed=backing_allowed(index,owner)
    foreign=int((ink & ~allowed).sum())
    alpha1_foreign=int(((native[:,:,3]>0) & ~allowed).sum())
    state=actual_state(native,index,palette) & (index==owner)
    return {"native_foreign_alpha24_backing_px":foreign,
            "native_foreign_alpha1_backing_px":alpha1_foreign,
            "native_isolated_owner_correct_logical_px":int(state.sum()),
            "stamp_correct_logical":state}


def next_choice(probed:list[dict],state:np.ndarray):
    """Greedy actual oracle gain; never count already-correct pixels as new."""
    candidates=[]
    for i,record in enumerate(probed):
        if record["used"] or record["unsafe"] or record["stamp"] is None:
            continue
        gain=int((record["stamp"] & ~state).sum())
        if gain:
            s=record["stroke"]
            candidates.append((-gain,-int(s["width"]),
                               -float(record["length"]),i,gain))
    if not candidates:
        return None
    _,_,_,i,gain=min(candidates)
    return i,gain


def _native(driver,folder:Path,stem:str,strokes:list[dict]):
    render=driver.execute_script(CMD,_renumber(strokes))
    rgba,meta=read_webgl_result(render,folder,stem)
    expected="ENGINE001_B1R_P4A2_BLANK_WEBGL" if not strokes else "ENGINE001_B1R_P4A2_NATIVE_1_TO_10"
    if (rgba.shape!=BOARD_SHAPE or
        meta.get("schema")!=expected or
        meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer" or
        (bool(strokes) and
         (meta.get("strokeCount")!=len(strokes) or
          meta.get("syntheticAcceptedVerticesNotChalk")!=2*len(strokes)))):
        raise ValueError("BLOCKED_P4D5_NOT_REAL_EGRET")
    return rgba,meta


def scanline_control(index:np.ndarray,palette:np.ndarray):
    x0,y0,x1,y1=CROP
    ans=[]
    for y in range(y0,y1):
        x=x0
        while x<x1:
            owner=int(index[y,x])
            start=x
            while x+1<x1 and index[y,x+1]==owner:
                x+=1
            if owner!=WHITE:
                ans.append(make_stroke(owner,palette,1,start+.125,y,
                                       x+.375,y))
            x+=1
    return _renumber(ans)


def roi_metrics(native:np.ndarray,index:np.ndarray,palette:np.ndarray):
    x0,y0,x1,y1=CROP
    state=actual_state(native,index,palette)
    target=crop_target(index)
    crop_in=native[y0*SCALE:y1*SCALE,
                   (X0+x0)*SCALE:(X0+x1)*SCALE,3]>=ALPHA
    white=np.repeat(np.repeat((index[y0:y1,x0:x1]==WHITE),SCALE,0),SCALE,1)
    all_ink=native[:,:,3]>=ALPHA
    cropfull=np.zeros(BOARD_SHAPE[:2],bool)
    cropfull[y0*SCALE:y1*SCALE,(X0+x0)*SCALE:(X0+x1)*SCALE]=True
    return {
        "target_nonwhite_logical":int(target.sum()),
        "correct_logical_native_5_of_9":int(state.sum()),
        "correct_fraction":float(state.sum()/target.sum()) if target.any() else 1.0,
        "remaining_zero_logical":int((target & ~state).sum()),
        "white_target_ink_alpha24_backing":int((crop_in & white).sum()),
        "any_ink_outside_crop_alpha24_backing":int((all_ink & ~cropfull).sum()),
        "total_ink_alpha24_backing":int(all_ink.sum()),
        "provenance":"actual Egret native composite; source ROI only, not full-art gates"
    }


def _review(original:np.ndarray,index:np.ndarray,palette:np.ndarray,
            baseline:np.ndarray,greedy:np.ndarray,output:Path):
    x0,y0,x1,y1=CROP
    cards=[
        ("ORIGINAL",Image.fromarray(original[y0:y1,x0:x1]).resize((288,288))),
        ("CURRENT B1-R E/F",Image.fromarray(palette[index[y0:y1,x0:x1]]).resize((288,288),Image.Resampling.NEAREST)),
        ("NATIVE SCANLINE W1",p4c0.preview_native(baseline).crop((x0*SCALE,y0*SCALE,x1*SCALE,y1*SCALE)).resize((288,288))),
        ("NATIVE 0/1 FEEDBACK",p4c0.preview_native(greedy).crop((x0*SCALE,y0*SCALE,x1*SCALE,y1*SCALE)).resize((288,288))),
    ]
    out=Image.new("RGB",(1152,318),"white");d=ImageDraw.Draw(out)
    for j,(label,img) in enumerate(cards):
        out.paste(img,(288*j,30))
        d.text((288*j+8,7),label,fill=(0,0,0))
    out.save(output/"COMPARISON_REAL_NATIVE.png")


def run(workspace:Path,source:Path,engine_js:Path,
        renderer:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D5_EVIDENCE_EXISTS")
    check_source(source)
    if (p4b1.git_blob(renderer.read_bytes())!=p4d0.RENDERER_BLOB or
        p4b1.git_blob(engine_js.read_bytes())!=p3b.ENGINE_GIT_BLOB_SHA1):
        raise ValueError("BLOCKED_P4D5_PINNED_ENGINE_OR_RENDERER_DRIFT")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4D5_PREREG_MISSING")
    palette,_=p3b.read_engine_palette(engine_js)
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D5: цветные пиксели 0/1 обновляются из ПОЛНОГО фактического Egret WebGL "
        "после каждого принятого штриха. Отдельные candidate native PNG at exact "
        "position, safe own-color alpha24, greedy gain, widths1..10, four "
        "directions, width1 residual attempts. Только pilot 24x24 female-face "
        "detail E/F, НЕ полный рисунок и НЕ native per-owner global 99% gate. "
        "Compare against native crop scanline W1. Никакой G32/V44 или тёмной обводки.\n",
        "utf8")
    summary={}
    with tempfile.TemporaryDirectory(prefix="engine001-p4d5-source-") as tmp:
        fresh=Path(tmp)/"fresh_p3d"
        parent=p3d.run(source,engine_js,fresh)
        if (parent["experiment"]!=p3d.EXPERIMENT or
            parent["original_source_sha256"]!=SOURCE_SHA or
            not parent["P3B_original_recomputed_in_current_run"] or
            parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D5_SOURCE_NOT_FRESH_B1R")
        original=np.asarray(Image.open(fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"),np.uint8)
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(240)
            blank,_=_native(driver,output,"REAL_EGRET_BLANK",[])
            if np.any(blank[:,:,3]):
                raise ValueError("BLOCKED_P4D5_NONEMPTY_BLANK")
            for method in METHODS:
                folder=output/method
                folder.mkdir()
                index=np.asarray(Image.open(
                    fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),np.uint8).copy()
                selected=parent["all_results"][SOURCE]["selected_engine_indices"]
                p4c0.validate_source(index,palette,selected)
                if parent["all_results"][SOURCE]["methods"][method]["status"]!=(
                    "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED"):
                    raise ValueError("BLOCKED_P4D5_SOURCE_SELECTION_DRIFT")
                x0,y0,x1,y1=CROP
                Image.fromarray(index[y0:y1,x0:x1]).save(folder/"SOURCE_ROI_ENGINE_INDICES.png")
                Image.fromarray(palette[index[y0:y1,x0:x1]]).save(folder/"SOURCE_ROI_RGB.png")
                target=crop_target(index)
                candidates=candidate_pool(index,palette)
                if not candidates:
                    raise ValueError("BLOCKED_P4D5_NO_PROPOSALS")
                probes=[]
                probe_dir=folder/"NATIVE_SINGLE_PROBES"
                probe_dir.mkdir()
                for candidate in candidates:
                    stem=candidate["candidate_id"]
                    native,meta=_native(driver,probe_dir,stem,[candidate["stroke"]])
                    record=single_native_candidate(candidate,native,index,palette)
                    probes.append({
                        "id":stem,"stroke":candidate["stroke"],
                        "model_gain_only":candidate["model_gain_ONLY"],
                        "length":candidate["line_length_logical"],
                        "native_foreign_alpha24":record["native_foreign_alpha24_backing_px"],
                        "native_foreign_alpha1":record["native_foreign_alpha1_backing_px"],
                        "native_isolated_correct":record["native_isolated_owner_correct_logical_px"],
                        "stamp":record["stamp_correct_logical"],
                        "unsafe":record["native_foreign_alpha24_backing_px"]>0,
                        "used":False,
                        "native_png_sha256":meta["source_sha256"]
                    })
                print("P4D5_ORACLE_PROBES",method,len(probes),"safe",
                      sum(not p["unsafe"] for p in probes),"unsafe",
                      sum(p["unsafe"] for p in probes),flush=True)
                plan=[]
                current=blank
                state=np.zeros_like(target)
                accepted=[]
                cumulative=folder/"NATIVE_CUMULATIVE_ACCEPTED"
                cumulative.mkdir()
                attempts=0
                while True:
                    choice=next_choice(probes,state)
                    if choice is None:
                        break
                    i,estimated_gain=choice
                    trial=probes[i]
                    trial["used"]=True
                    attempts+=1
                    new_plan=_renumber(plan+[trial["stroke"]])
                    native,meta=_native(driver,cumulative,
                                        f"STEP_{attempts:04d}_CANDIDATE_{i:04d}",new_plan)
                    after=actual_state(native,index,palette)
                    before_count=int(state.sum());after_count=int(after.sum())
                    # Return 0/1 state from REAL composited native PNG. A later
                    # stroke may revert old 1→0; never fake OR on model masks.
                    improvement=after_count-before_count
                    trial["attempt_id"]=attempts
                    trial["predicted_new_zeros"]=estimated_gain
                    trial["actual_net_gain"]=improvement
                    trial["previous_ones_erased"]=int((state & ~after).sum())
                    trial["native_cumulative_png_sha256"]=meta["source_sha256"]
                    if improvement>0:
                        plan=new_plan
                        state=after
                        current=native
                        accepted.append(i)
                    else:
                        trial["rejected_no_real_gain"]=True
                    if attempts%10==0:
                        print("P4D5_FEEDBACK",method,"attempts",attempts,"accepted",
                              len(plan),"correct",int(state.sum()),"of",
                              int(target.sum()),flush=True)
                # A complete, matched baseline from blank using unmodified
                # native Egret width1 row-run strokes (no fake model).
                control=scanline_control(index,palette)
                base,base_meta=_native(driver,folder,"NATIVE_SCANLINE_W1_CONTROL",control)
                final,final_meta=_native(driver,folder,"NATIVE_GREEDY_PIXEL_STATE_FINAL",plan) if plan else (blank,{})
                if not np.array_equal(final,current):
                    raise ValueError("BLOCKED_P4D5_FINAL_NATIVE_REPLAY_DRIFT")
                final_score=roi_metrics(final,index,palette)
                base_score=roi_metrics(base,index,palette)
                Image.fromarray((state[y0:y1,x0:x1]*255).astype(np.uint8)).save(
                    folder/"FINAL_STATE_1_NATIVE_CONFIRMED.png")
                Image.fromarray(((target & ~state)[y0:y1,x0:x1]*255).astype(np.uint8)).save(
                    folder/"REMAINING_ZERO_NATIVE.png")
                Image.fromarray(palette[index[y0:y1,x0:x1]]).save(folder/"CURRENT_SOURCE_RGB.png")
                _review(original,index,palette,base,final,folder)
                (folder/"ACCEPTED_FULL_STROKES.json").write_text(json.dumps(
                    plan,ensure_ascii=False,allow_nan=False)+"\n","utf8")
                slim=[]
                for p in probes:
                    slim.append({k:v for k,v in p.items() if k!="stamp"})
                (folder/"NATIVE_CANDIDATES_AND_REJECTIONS.json").write_text(
                    json.dumps(slim,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
                numerical=(final_score["correct_fraction"]>base_score["correct_fraction"] and
                           final_score["white_target_ink_alpha24_backing"]<=
                           base_score["white_target_ink_alpha24_backing"] and
                           final_score["any_ink_outside_crop_alpha24_backing"]<=
                           base_score["any_ink_outside_crop_alpha24_backing"])
                summary[method]={
                    "source":SOURCE,"crop_xyxy":list(CROP),
                    "target_nonwhite_pixels":int(target.sum()),
                    "owners_in_crop":sorted(int(v) for v in np.unique(index[target])),
                    "total_model_proposals_NATIVE_NOT_CLAIMED":len(candidates),
                    "oracle_single_native_probes":len(probes),
                    "width1_candidate_probes":sum(p["stroke"]["width"]==1 for p in probes),
                    "isolated_native_safe_candidates":sum(not p["unsafe"] for p in probes),
                    "isolated_native_unsafe_candidates":sum(p["unsafe"] for p in probes),
                    "attempted_real_cumulative_native":attempts,
                    "accepted_real_cumulative_native":len(plan),
                    "accepted_stroke_width_histogram":{
                        str(w):sum(s["width"]==w for s in plan) for w in range(1,11)},
                    "source_owner_correct_zero_to_one_native_baseline":base_score,
                    "source_owner_correct_zero_to_one_native_greedy":final_score,
                    "baseline_paint_strokes":len(control),
                    "native_final_replay_equal":True,
                    "accepted_candidate_native_foreign_alpha24_zero":
                        all(probes[i]["native_foreign_alpha24"]==0 for i in accepted),
                    "numeric_candidate":(
                        "PILOT_COMPOSITE_CANDIDATE_VISUAL_AND_FULL_ART_PENDING"
                        if numerical else "PILOT_NO_STRICT_NUMERIC_IMPROVEMENT"),
                    "global_owner99_protected0_far3":"NOT_MEASURED_FULL_IMAGE",
                    "P3D_SOURCE_ONLY_NO_G32_V44":True,
                    "accepted_candidate_indices":accepted,
                }
                print("P4D5_FINAL",method,"baseline correct",
                      base_score["correct_logical_native_5_of_9"],"greedy correct",
                      final_score["correct_logical_native_5_of_9"],"of",
                      int(target.sum()),"accepted",len(plan),"remaining",
                      final_score["remaining_zero_logical"],flush=True)
    report={
        "experiment":EXPERIMENT,
        "technical_result":"P4D5_EF_ORIGINAL_ROI_TRUE_NATIVE_ORACLE_AND_FEEDBACK",
        "original_source_sha256":SOURCE_SHA,
        "original_recomputed_current_run":True,
        "source_active":SOURCE,"methods":summary,
        "native_blank_alpha0":True,
        "no_global_dark_contour":True,
        "game_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
        "renderer_git_blob":p4d0.RENDERER_BLOB,
        "source_game_engine_blob":p3b.ENGINE_GIT_BLOB_SHA1,
        "candidate_frozen_MAX_NATIVE_PROBES":MAX_NATIVE_PROBES,
        "native_state_5of9_threshold":LOGICAL_REQUIRED_SUBPIXELS,
        "native_alpha_threshold":ALPHA,"native_rgb_distance_threshold":RGB_TOL,
        "global_99_protected0_max3":"NOT_MEASURED",
        "E4_live_game":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "production_promotion":False,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    report["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,
                                                indent=2,allow_nan=False)+"\n","utf8")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--engine-js",type=Path,required=True)
    parser.add_argument("--renderer",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    params=parser.parse_args()
    run(params.workspace,params.source,params.engine_js,params.renderer,params.output)
