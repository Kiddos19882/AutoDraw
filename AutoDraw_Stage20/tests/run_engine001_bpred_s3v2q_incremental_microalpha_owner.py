#!/usr/bin/env python3
"""ENGINE-001/BPRED-S3v2q: prospective original Egret micro-alpha owner evidence.

True original Canvas pre/post/repeated-post per stroke. Source-only E3, not E4
game, not S0 BLIND and never a production blending estimator.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_bpred_s3v2j_new_native_alpha0_owner_influence as j
import run_engine001_bpred_s3v2o_new_native_low_alpha_readback as o
import run_engine001_bpred_s3v2p_native_canvas_readback_vs_composition as p
import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_bpred_s3v2_native_canvas_stage as v2
import run_engine001_bpred_s3v2c_multicapture_trace as trace
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1

EXPERIMENT="ENGINE001_BPRED_S3V2Q_INCREMENTAL_MICROALPHA_NATIVE_SOURCE_V1"
E0_FILE="ENGINE001_BPRED001_S3V2Q_NATIVE_INCREMENTAL_MICROALPHA_OWNER_PREREG_2026-11-20.md"
E0_BLOB="ac0bd08ee45058e890ef16c75efea58ca27bec47"
OBSERVER_NAME="engine001_bpred_s3v2q_incremental_canvas_microalpha.js"
SCHEMA="ENGINE001_BPRED_S3V2Q_TRUE_MAIN_INCREMENTAL_MICROALPHA_V1"
ROI=p.ROI
WIDTHS=j.WIDTHS
RELATIONS=j.RELATIONS
VARIANTS=j.VARIANTS
ANGLES=(31,79,127,163,211,257,293,331,359,47)
COLORS=(
    (0xB73D62,0x298AC1),(0x45B587,0xDC6239),
    (0xA64BCF,0x3B9F6E),(0xE78C2D,0x4D5CCD),
    (0x32A5CF,0xC04581),(0x91C63E,0x3754AD),
    (0xDF5BA4,0x379747),(0x7135C5,0xDB9A31),
    (0x37BDCA,0xBC526A),(0xD8B84E,0x4B72C1)
)
STATES=("pre","post","repeat_post")


def blocked(code):
    raise ValueError("BLOCKED_BPRED_S3V2Q_"+code)


def plans_for(width,relation):
    if type(width) is not int or width not in WIDTHS or relation not in RELATIONS:
        blocked("NOT_FROZEN_SOURCE_MATRIX")
    px=((17*width+9)%53+.125)/64
    py=((19*width+7)%47+.875)/64
    cx,cy=179+px,114+py
    a_deg=ANGLES[width-1]
    a=j.midpoint(cx,cy,a_deg,12+width%4)
    if relation=="CROSS_ROTATED":
        b=j.midpoint(cx+.40625,cy-.34375,(a_deg+113)%360,13+width%3)
    else:
        d=.79*width+.41
        rad=math.radians(a_deg)
        b=j.midpoint(cx-math.sin(rad)*d,cy+math.cos(rad)*d,
                     (a_deg+23)%360,13+width%3)
    if any(not(math.isfinite(point["x"]) and math.isfinite(point["y"])
                  and 0<point["x"]<460 and 0<point["y"]<240)
           for stroke in (a,b) for point in stroke):
        blocked("NONFINITE_OR_CLIPPED_LOGICAL_BOARD")
    ca,cb=COLORS[width-1]
    owners={
        "A":{"strokeId":"bpred-A","width":width,"colorIndex":1,
             "colorRgb":ca,"points":a},
        "B":{"strokeId":"bpred-B","width":width,"colorIndex":2,
             "colorRgb":cb,"points":b}
    }
    orders={"A_ONLY":("A",),"B_ONLY":("B",),
            "A_THEN_B":("A","B"),"B_THEN_A":("B","A")}
    out={}
    for variant,order in orders.items():
        src=[dict(owners[k]) for k in order]
        runtime=[{**s,"strokeId":f"icon-{idx}"} for idx,s in enumerate(src)]
        sid=f"BPRED-S3V2Q-W{width:02d}-{relation}-{variant}"
        out[variant]={
            "sample_id":sid,"width":width,"relation":relation,
            "variant":variant,"phase_xy":[px,py],"angle_deg":a_deg,
            "source_colors":[ca,cb],"source_strokes":src,
            "runtime_strokes":runtime,
            "source_plan_sha256":s3.digest(s3.canonical(src)),
            "runtime_plan_sha256":s3.digest(s3.canonical(runtime))}
    return out


def manifest():
    scenes=[plans_for(w,r)[v] for w in WIDTHS for r in RELATIONS for v in VARIANTS]
    controls=[
        {"sample_id":f"BPRED-S3V2Q-REPLAY-W{w:02d}-{r}",
         "parent_sample_id":plans_for(w,r)["A_THEN_B"]["sample_id"],
         "width":w,"relation":r}
        for w in WIDTHS for r in RELATIONS]
    if (len(scenes),len({s["sample_id"] for s in scenes}),len(controls))!=(80,80,20):
        blocked("WRONG_MATRIX_CARDINALITY")
    return {
        "experiment":EXPERIMENT,"E0_blob":E0_BLOB,
        "original_engine_blob":p4d3.ENGINE_GIT_BLOB,
        "original_renderer_blob":p4d3.RENDERER_GIT_BLOB,
        "true_native_primary":80,"uninstrumented_replays":20,
        "blank":1,"roi_main_node_local":list(ROI),
        "source_owner_known_only":True,"S0_BLIND_used":False,
        "scenes":scenes,"controls":controls}


def verify_source(workspace,engine,renderer,scripts,observer):
    p.check_source(workspace,engine,renderer,scripts,
        workspace/"AutoDraw_Stage20"/"tests"/p.JS_FILE)
    e0=workspace/"AutoDraw_Stage20"/"docs"/E0_FILE
    if not e0.is_file() or p4b1.git_blob(e0.read_bytes())!=E0_BLOB:
        blocked("FIRST_E0_MISSING_OR_DRIFT")
    if observer.name!=OBSERVER_NAME or not observer.is_file():
        blocked("INCREMENTAL_OBSERVER_NOT_FOUND")


def read_bytes(entry,field):
    if not isinstance(entry,dict) or not isinstance(entry.get(field),str):
        blocked("NATIVE_RGBA_BASE64_MISSING_"+field)
    try:
        raw=base64.b64decode(entry[field],validate=True)
    except (base64.binascii.Error,ValueError) as exc:
        raise ValueError("BLOCKED_BPRED_S3V2Q_NONGENUINE_BASE64_"+field) from exc
    if len(raw)!=ROI[2]*ROI[3]*4:
        blocked("RAW_RGBA_SIZE_DRIFT_"+field)
    return raw


def raw_frame(data):
    if not isinstance(data,(bytes,bytearray)) or len(data)!=ROI[2]*ROI[3]*4:
        blocked("RAW_FRAME_SHAPE")
    return np.frombuffer(data,dtype=np.uint8).reshape(ROI[3],ROI[2],4)


def readback_scene(driver,scene,output):
    item=j.extract_scene(driver,scene,output)
    observations=driver.execute_script(
        "var x=window.AutoDrawBPRED_S3v2qLastIncremental;"
        "window.AutoDrawBPRED_S3v2qLastIncremental=null;return x;")
    if (not isinstance(observations,dict) or observations.get("schema")!=SCHEMA
            or observations.get("originalTraceRestored") is not True
            or observations.get("originalMainCount")!=len(item["steps"])
            or not isinstance(observations.get("events"),list)
            or len(observations["events"])!=len(item["steps"])):
        blocked("REAL_SOURCE_EVENT_PROVENANCE_"+scene["sample_id"])
    folder=output/"native"/scene["sample_id"]
    records=[];previous=None;raw_cache=[]
    for step,event in enumerate(observations["events"],1):
        if (event.get("schema")!=SCHEMA or event.get("ordinal")!=step
                or event.get("canvasSize")!=[1392,732]
                or event.get("roi")!={"x":ROI[0],"y":ROI[1],
                                     "width":ROI[2],"height":ROI[3]}
                or not isinstance(event.get("originalContext"),dict)):
            blocked("REAL_EVENT_ID_AND_CONTEXT_DRIFT_"+scene["sample_id"])
        context=event["originalContext"]
        if (not isinstance(context.get("globalCompositeOperation"),str)
                or not isinstance(context.get("globalAlpha"),(int,float))
                or not 0<=context["globalAlpha"]<=1
                or not isinstance(context.get("transform"),list)
                or len(context["transform"])!=6
                or not all(isinstance(c,(int,float)) and math.isfinite(c)
                           for c in context["transform"])):
            blocked("ORIGINAL_CANVAS_CONTEXT_INVALID")
        raw={state:read_bytes(event,state+"_rgba_b64") for state in STATES}
        names={}
        for state,data in raw.items():
            name=f"{scene['sample_id']}_REAL_{state.upper()}_STROKE_{step:02d}.rgba"
            target=folder/name
            if target.exists():
                blocked("NO_RAW_OVERWRITE")
            target.write_bytes(data)
            names[state]={"file":name,"sha256":hashlib.sha256(data).hexdigest()}
        after=raw_frame(raw["post"])
        again=raw_frame(raw["repeat_post"])
        before=raw_frame(raw["pre"])
        repeat_changed=np.any(after!=again,axis=2)
        pre_change=np.any(before!=after,axis=2)
        prev_changed=np.any(before!=raw_frame(previous),axis=2) if previous is not None else None
        pngfile=folder/(scene["sample_id"]+f"_REAL_STROKE_STEP_{step:02d}.png")
        with Image.open(pngfile) as im:
            if im.size!=(1392,732) or im.mode!="RGBA":
                blocked("ORIGINAL_POST_STROKE_PNG_SHAPE")
            png=np.asarray(im)[ROI[1]:ROI[1]+ROI[3],ROI[0]:ROI[0]+ROI[2]]
        mismatch=np.any(after!=png,axis=2)
        records.append({
            "sample_id":scene["sample_id"],"step":step,
            "originalContext":context,"states":names,
            "repeat_changed_pixels":int(repeat_changed.sum()),
            "prepost_changed_pixels":int(pre_change.sum()),
            "pre_vs_previous_post_changed_pixels":
                int(prev_changed.sum()) if prev_changed is not None else None,
            "post_vs_original_PNG_changed_pixels":int(mismatch.sum()),
            "native_png_file":pngfile.name,
            "node_local_physical_ROI":list(ROI)
        })
        previous=raw["post"]
        raw_cache.append({k:raw_frame(x).copy() for k,x in raw.items()})
    # Original actual ink must lie completely within the preregistered ROI.
    x,y,w,h=ROI
    bx,by=x-6,y-6
    for frame in item["steps"]:
        outside=frame[:,:,3].copy()
        outside[by:by+h,bx:bx+w]=0
        if np.any(outside):
            blocked("REAL_NATIVE_SOURCE_INK_OUTSIDE_FROZEN_ROI")
    item["incremental"]=raw_cache
    item["inc_meta"]=records
    item["readback_last"]=raw_cache[-1]["post"]
    # Reuse frozen S3v2p PNG-versus-post diagnostics unmodified.
    item["readback_meta"]=[
        {"step":row["step"],"sample_id":scene["sample_id"],
         "original_main_canvas_png":row["native_png_file"],
         "native_raw_file":row["states"]["post"]["file"],
         "native_raw_sha256":row["states"]["post"]["sha256"],
         "total_roi_pixels":ROI[2]*ROI[3],
         "PNG_vs_getImageData_different_RGBA_pixels":row["post_vs_original_PNG_changed_pixels"],
         "RGB_different_pixels":None,"alpha_different_pixels":None,
         "max_abs_byte_diff":None,"mean_abs_byte_diff":None}
        for row in records]
    return item


def coordinate(x,y):
    return {"node_local_xy":[ROI[0]+int(x),ROI[1]+int(y)],
            "aligned_board_xy":[ROI[0]+int(x)-6,ROI[1]+int(y)-6]}


def analyze_incremental(items,output):
    index={(it["scene"]["width"],it["scene"]["relation"],it["scene"]["variant"]):it
           for it in items}
    events=[];repeats=[];discontinuities=[];records=[]
    direct_owner_events=0; first_owner_readback_diffs=0
    counts={"total_strokes":0,"repeat_different":0,"pre_vs_prev_post_different":0,
            "event_prepost_changed_all":0,"ordered_candidate_damage":0,
            "ordered_candidate_damage_after_first":0}
    for it in items:
        sid=it["scene"]["sample_id"];counts["total_strokes"]+=len(it["incremental"])
        for row,step in zip(it["inc_meta"],it["incremental"]):
            pre,post,again=(step[k] for k in STATES)
            repeat=np.any(post!=again,axis=2)
            changed=np.any(pre!=post,axis=2)
            counts["repeat_different"]+=int(repeat.sum())
            counts["event_prepost_changed_all"]+=int(changed.sum())
            for y,x in np.argwhere(repeat):
                repeats.append({"sample_id":sid,"step":row["step"],
                    **coordinate(x,y),"post_RGBA":post[y,x].tolist(),
                    "repeat_RGBA":again[y,x].tolist()})
        for idx in range(1,len(it["incremental"])):
            before=it["incremental"][idx]["pre"]
            prior=it["incremental"][idx-1]["post"]
            gap=np.any(before!=prior,axis=2)
            counts["pre_vs_prev_post_different"]+=int(gap.sum())
            for y,x in np.argwhere(gap):
                discontinuities.append({
                    "sample_id":sid,"before_step":idx+1,
                    **coordinate(x,y),
                    "previous_post_RGBA":prior[y,x].tolist(),
                    "next_pre_RGBA":before[y,x].tolist()
                })
    for w in WIDTHS:
        for relation in RELATIONS:
            group={v:index[(w,relation,v)] for v in VARIANTS}
            for var in ("A_THEN_B","B_THEN_A"):
                current=group[var]
                lower=group["A_ONLY"] if var=="A_THEN_B" else group["B_ONLY"]
                top=group["B_ONLY"] if var=="A_THEN_B" else group["A_ONLY"]
                lc,tc=lower["readback_last"],top["readback_last"]
                zone=(lc[:,:,3]>0)&(tc[:,:,3]==0)
                first=current["incremental"][0]["post"]
                first_delta=np.any(first!=lc,axis=2)
                first_owner_readback_diffs+=int(first_delta.sum())
                candidate_total=0; after_first=0
                event_stat=[]
                for idx,step in enumerate(current["incremental"]):
                    pre,post=step["pre"],step["post"]
                    delta=post.astype(np.int16)-pre.astype(np.int16)
                    active=zone&(pre[:,:,3]>0)&np.any(delta!=0,axis=2)
                    n=int(active.sum())
                    candidate_total+=n
                    if idx>=1:after_first+=n
                    for y,x in np.argwhere(active):
                        d=delta[y,x]
                        events.append({
                            "sample_id":current["scene"]["sample_id"],"width":w,
                            "relation":relation,"variant":var,"step":idx+1,
                            "after_first_original_main_event":bool(idx>=1),
                            **coordinate(x,y),
                            "independent_lower_RGBA":lc[y,x].tolist(),
                            "independent_top_RGBA":tc[y,x].tolist(),
                            "actual_pre_RGBA":pre[y,x].tolist(),
                            "actual_post_RGBA":post[y,x].tolist(),
                            "delta_RGBA":d.tolist(),
                            "RGB_changed":bool(np.any(d[:3])),
                            "alpha_changed":bool(d[3]),
                            "original_context":current["inc_meta"][idx]["originalContext"]
                        })
                    event_stat.append({"step":idx+1,"owner_zone_changed_prepost":n,
                        "any_prepost_changed":current["inc_meta"][idx]["prepost_changed_pixels"]})
                records.append({
                    "sample_id":current["scene"]["sample_id"],
                    "width":w,"relation":relation,"variant":var,
                    "owner_zone_pixels":int(zone.sum()),
                    "first_native_event_vs_isolated_lower_raw_differences":
                        int(first_delta.sum()),
                    "owner_zone_prepost_changed_occurrences_all_events":candidate_total,
                    "owner_zone_prepost_changed_occurrences_after_first":after_first,
                    "original_main_stroke_events":len(current["incremental"]),
                    "per_event":event_stat
                })
                counts["ordered_candidate_damage"]+=candidate_total
                counts["ordered_candidate_damage_after_first"]+=after_first
    if len(records)!=40 or counts["total_strokes"]!=sum(len(it["steps"]) for it in items):
        blocked("INCREMENTAL_CARDINALITY_OR_ORIGINAL_STROKE_DRIFT")
    v2.write_json(output/"ALL_40_ORDERED_INCREMENTAL_OWNER_TIMELINES.json",records)
    v2.write_json(output/"EVERY_TRUE_STROKE_PRE_POST_OWNER_CHANGED_PIXEL.json",events)
    v2.write_json(output/"EVERY_REPEATED_READBACK_DIFFERENT_PIXEL.json",repeats)
    v2.write_json(output/"EVERY_TRUE_STROKE_PREVIOUS_POST_TO_NEXT_PRE_GAP.json",discontinuities)
    v2.write_json(output/"ALL_NATIVE_INCREMENTAL_STROKE_READBACK_METADATA.json",
                  [r for it in items for r in it["inc_meta"]])
    counts["ordered_first_post_vs_lower_raw_diff_pixels"]=first_owner_readback_diffs
    return counts,events,repeats,discontinuities,records


def run(workspace,engine,renderer,scripts,observer,output):
    if output.exists():
        blocked("OUTPUT_ALREADY_EXISTS")
    verify_source(workspace,engine,renderer,scripts,observer)
    spec=manifest()
    output.mkdir(parents=True,exist_ok=False)
    v2.write_json(output/"FROZEN_S3V2Q_MANIFEST.json",spec)
    items=[]
    with trace.pinned_native_egret_session(workspace) as driver:
        capabilities={k:driver.capabilities.get(k) for k in
                      ("browserName","browserVersion","platformName")}
        if capabilities["browserName"]!="firefox" or not str(capabilities["browserVersion"]).startswith("159."):
            blocked("FIREFOX159_NOT_PINNED")
        for script in scripts:
            driver.execute_script(script.read_text("utf8"))
        driver.execute_script(observer.read_text("utf8"))
        if driver.execute_script(
                "return window.AutoDrawBPRED_S3v2qObserverInstalled;") is not True:
            blocked("MICROALPHA_NATIVE_OBSERVER_NOT_INSTALLED")
        blank,blankmeta=p4d3.read_webgl_result(
            driver.execute_script(p4d3.CMD,[]),output,"S3V2Q_REAL_EGRET_BLANK")
        if blankmeta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or np.any(blank[:,:,3]):
            blocked("REAL_NATIVE_BLANK_NOT_TRANSPARENT")
        with (output/"NATIVE_APPEND_ONLY.jsonl").open("x",encoding="utf8") as ledger:
            for scene in spec["scenes"]:
                try:
                    item=readback_scene(driver,scene,output)
                except Exception as exc:
                    v2.write_json(output/"BLOCKED_OR_FAILED_SCENE.json",{
                        "sample_id":scene["sample_id"],"completed_before_error":len(items),
                        "type":type(exc).__name__,"detail":str(exc)})
                    raise
                items.append(item)
                ledger.write(json.dumps({
                    "sample_id":scene["sample_id"],"source_sha":scene["source_plan_sha256"],
                    "runtime_sha":scene["runtime_plan_sha256"],
                    "true_original_strokes":len(item["steps"]),
                    "raw_pre_post_repeat_sets":len(item["incremental"])},
                    ensure_ascii=False,allow_nan=False)+"\n")
                ledger.flush()
                print("S3V2Q_REAL_ORIGINAL_EGRET",len(items),"/80",flush=True)
        (output/"replays").mkdir(exist_ok=False)
        repeats=[]
        for c in spec["controls"]:
            original=plans_for(c["width"],c["relation"])["A_THEN_B"]
            real,meta=p4d3.read_scene(driver,output/"replays",
                c["sample_id"]+"_REAL_EGRET",original["runtime_strokes"])
            target=next(x["webgl"] for x in items if x["scene"]["sample_id"]==original["sample_id"])
            equal=bool(np.array_equal(p4d3.roi(real,s3.CX,s3.CY),
                                      p4d3.roi(target,s3.CX,s3.CY)))
            repeats.append({"sample_id":c["sample_id"],"parent":original["sample_id"],
                "uninstrumented_original_webgl_ROI_exact":equal,
                "source_png_sha256":meta["source_png_sha256"]})
            if not equal:
                v2.write_json(output/"BLOCKED_UNINSTRUMENTED_REPLAY.json",repeats)
                blocked("READBACK_OBSERVER_CHANGED_ORIGINAL_EGRET_"+c["sample_id"])
    v2.write_json(output/"REPLAY_CONTROLS.json",repeats)
    incremental,owner_events,unstable,gaps,ordered=analyze_incremental(items,output)
    readbacks,readback_diffs,bins=p.compare_readbacks(items,output)
    old_rows,old_damages=j.calculate_pairs(items,output)
    owner,tworeadrows,tworead_events=p.compare_owner_bytes(items,output,old_damages)
    counts,models,misses,buckets=o.analyze_isolated(items,output)
    first=sum(r["first_event_vs_same_run_isolated_owner"]["RGBA_different_physical_pixels"]
              for r in old_rows)
    last=sum(it["last_difference"]["RGBA_different_physical_pixels"] for it in items)
    stage_rgb=sum(x["stage"]["QH"]["rgb_mismatch_pixels"] for x in items)
    stage_alpha=sum(x["stage"]["QH"]["alpha_mismatch_pixels"] for x in items)
    report={
        "experiment":EXPERIMENT,"E0_blob":E0_BLOB,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        "browser":capabilities,"original_game_engine_blob":p4d3.ENGINE_GIT_BLOB,
        "original_renderer_blob":p4d3.RENDERER_GIT_BLOB,
        "new_original_native_sources":len(items),"native_main_PNG":80,"native_mask_PNG":80,
        "native_final_WebGL_PNG":101,"real_main_stroke_events":incremental["total_strokes"],
        "raw_direct_rgba_captures":3*incremental["total_strokes"],
        "uninstrumented_replay_count":len(repeats),
        "all_uninstrumented_replays_ROI_RGBA_exact":all(x["uninstrumented_original_webgl_ROI_exact"] for x in repeats),
        "blank_alpha0":True,"node_local_roi":list(ROI),"Q0_source_integrity":"PASS",
        "Q1_repeated_post_getImageData":"PASS" if not unstable else "FAIL",
        "Q1_same_event_repeat_changed_pixel_occurrences":len(unstable),
        "Q2_incremental_owner_changed_pixel_occurrences_after_first":
            incremental["ordered_candidate_damage_after_first"],
        "Q2_incremental_owner_changed_pixel_occurrences_all":
            incremental["ordered_candidate_damage"],
        "Q2_first_real_event_vs_lower_readback_diff":incremental["ordered_first_post_vs_lower_raw_diff_pixels"],
        "Q2_source_owner_safety":"FAIL" if owner_events or owner["total_union"] else "NO_HARM_OBSERVED_SAMPLE_ONLY",
        "Q2_scientific_interpretation":"BLOCKED_UNSTABLE_READBACK" if unstable else "SOURCE_NATIVE_OBSERVATION_ONLY",
        "Q2_final_PNG_lower_owner_alpha0_harm":owner["PNG_changed"],
        "Q2_final_getImageData_lower_owner_alpha0_harm":owner["getImageData_changed"],
        "Q2_final_owner_classification":owner["classes"],
        "Q2_transient_events_with_no_final_damage":None,
        "Q3_first_owner_40":"PASS" if first==0 else "FAIL",
        "Q3_last_original_stroke_80":"PASS" if last==0 else "FAIL",
        "Q3_original_C0_Canvas_pass_40":sum(int(r["original_fixed_C0_canvas"]["frozen_H1_pass"]) for r in old_rows),
        "Q3_original_C0_QH_WebGL_pass_40":sum(int(r["original_fixed_C0_QH_webgl"]["frozen_H1_pass"]) for r in old_rows),
        "Q3_stage_QH_RGB_misses":stage_rgb,"Q3_stage_QH_alpha_misses":stage_alpha,
        "Q4_new_source_counts":counts,
        "Q4_G3_source_misses":models["G3"]["misses"],
        "Q4_G3_informative_A16_254":models["G3"]["informative"],
        "Q4_G3_fraction":models["G3"]["informative"]/counts["qualified"],
        "Q4_G3_RGB_envelope":"PASS_SOURCE_ONLY" if models["G3"]["misses"]==0 and counts["opaque_miss"]==0 else "FAIL",
        "Q4_G3_informative_gate":"PASS" if models["G3"]["informative"]/counts["qualified"]>=.9 else "FAIL",
        "Q5_PNG_vs_getImageData_different_pixels":len(readback_diffs),
        "Q5_readback_alpha_bins":bins,
        "Q3_pre_vs_previous_post_discontinuities":len(gaps),
        "Q4_original_G3_model_unchanged":True,
        "source_baseline_S3v2p_readback_difference":51275,
        "source_baseline_S3v2p_owner_harm":17,
        "source_baseline_S3v2p_G3_usefulness":"FAIL_7725_OF_8690",
        "original_EF_P4D18_quality":"FAIL_UNCHANGED",
        "source_owner_safety":"NOT_PROMOTED",
        "S0_BLIND_used":False,"S4":"NOT_RUN","E4_game":"NOT_RUN",
        "E5_independent_game":"NOT_RUN","exact_game_CHALK":None,
        "production_promotion":False,
        "all_owner_incremental_negative_records":len(owner_events),
        "all_same_readback_negative_records":len(unstable)
    }
    report["members_sha256"]={
        file.relative_to(output).as_posix():hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(output.rglob("*")) if file.is_file()}
    v2.write_json(output/"report.json",report)
    print("S3V2Q_STABLE_NATIVE_READBACK",report["Q1_repeated_post_getImageData"],len(unstable),flush=True)
    print("S3V2Q_ACTUAL_INCREMENTAL_OWNER_HARM",
          incremental["ordered_candidate_damage_after_first"],
          "FINAL",owner["PNG_changed"],owner["getImageData_changed"],flush=True)
    print("S3V2Q_G3_NATIVE_SOURCE",report["Q4_G3_RGB_envelope"],
          report["Q4_G3_informative_gate"],models["G3"]["informative"],counts["qualified"],flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for key in ("workspace","engine","renderer","trace-js","selector-js","stroke-js","incremental-js","output"):
        parser.add_argument("--"+key,required=True,type=Path)
    a=parser.parse_args()
    run(a.workspace,a.engine,a.renderer,
        (a.trace_js,a.selector_js,a.stroke_js),a.incremental_js,a.output)
