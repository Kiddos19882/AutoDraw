#!/usr/bin/env python3
"""BPRED-S3v2r: ONE bounded E3 true original Egret repeated stroke contrast study.

Original Canvas2D Egret stroke before/post, original main+mask PNG and actual
final WebGL, without game code changes, synthetic brushes or model fitting.
Scientific original protected zero remains unchanged: visual is DIAGNOSTIC.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import numpy as np
from PIL import Image

import run_engine001_bpred_s3v2q_incremental_microalpha_owner as q
import run_engine001_bpred_s3v2p_native_canvas_readback_vs_composition as p
import run_engine001_bpred_s3v2_native_canvas_stage as v2
import run_engine001_bpred_s3v2f_prospective_native_rgba8 as v2f
import run_engine001_bpred_s3v2c_multicapture_trace as trace
import run_engine001_bpred_s3v2j_new_native_alpha0_owner_influence as j
import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1

EXPERIMENT="ENGINE001_BPRED_S3V2R_BOUNDED_NATIVE_CONTRAST_REPEATED_STROKES_V1"
E0_NAME="ENGINE001_BPRED001_S3V2R_BOUNDED_REPEAT_CONTRAST_NATIVE_PREREG_2026-11-20.md"
E0_BLOB="1909565e0a9e4fc7b742e88f2324b848d8f9e017"
OBSERVER="engine001_bpred_s3v2r_original_contrast_repeat_observer.js"
SCHEMA="ENGINE001_BPRED_S3V2R_ORIGINAL_NATIVE_REPEAT_CONTRAST_V1"
ROI=p.ROI
WIDTHS=(3,7,10)
RELATIONS=("CROSS_ROTATED","NEAR_SKEW")
BACKGROUNDS=("DARK","LIGHT")
COLORS={"DARK":0x183A53,"LIGHT":0xE9CA9B}
TOP=0xD95A83
ANGLES={3:53,7:171,10:289}
REPEATS=(1,8)
SCENE_COUNT=42
EXPECTED_EVENTS=150


def blocked(message):
    raise ValueError("BLOCKED_BPRED_S3V2R_"+message)


def make_scene(width,relation,variant):
    if type(width) is not int or width not in WIDTHS or relation not in RELATIONS:
        blocked("UNFROZEN_WIDTH_RELATION")
    if variant not in ("TOP_ONLY","DARK_ONLY","LIGHT_ONLY",
                       "DARK_R1","LIGHT_R1","DARK_R8","LIGHT_R8"):
        blocked("UNFROZEN_VARIANT")
    cx=178+((11*width+3)%37+.25)/64
    cy=116+((7*width+5)%41+.75)/64
    angle=ANGLES[width]
    a=j.midpoint(cx,cy,angle,13)
    if relation=="CROSS_ROTATED":
        b=j.midpoint(cx+.375,cy-.4375,(angle+107)%360,14)
    else:
        rad=math.radians(angle)
        d=.82*width+.65
        b=j.midpoint(cx-math.sin(rad)*d,cy+math.cos(rad)*d,
                     (angle+19)%360,14)
    if any(not (math.isfinite(z["x"]) and math.isfinite(z["y"]) and
                   0<z["x"]<460 and 0<z["y"]<240)
           for path in (a,b) for z in path):
        blocked("SOURCE_GEOMETRY_INVALID")
    key="DARK" if variant.startswith("DARK") else "LIGHT"
    repeat=8 if variant.endswith("R8") else 1
    lower={"strokeId":"bpred-A","colorIndex":1,
           "colorRgb":COLORS[key],"width":width,"points":a}
    upper={"strokeId":"bpred-B","colorIndex":2,
           "colorRgb":TOP,"width":width,"points":b}
    if variant=="TOP_ONLY":
        sources=[upper]
    elif variant.endswith("ONLY"):
        sources=[lower]
    else:
        sources=[lower]+[{**upper,"strokeId":f"bpred-B-{i:02d}"} for i in range(1,repeat+1)]
    runtime=[{**stroke,"strokeId":f"icon-{idx}"} for idx,stroke in enumerate(sources)]
    sid=f"BPRED-S3V2R-W{width:02d}-{relation}-{variant}"
    return {
        "sample_id":sid,"width":width,"relation":relation,"variant":variant,
        "background":key,"repeat":repeat,"phase_xy":[cx-178,cy-116],
        "angle_deg":angle,"lower_color":COLORS[key],"upper_color":TOP,
        "source_strokes":sources,"runtime_strokes":runtime,
        "source_plan_sha256":s3.digest(s3.canonical(sources)),
        "runtime_plan_sha256":s3.digest(s3.canonical(runtime))
    }


def manifest():
    scenes=[]
    for width in WIDTHS:
        for relation in RELATIONS:
            for v in ("TOP_ONLY","DARK_ONLY","LIGHT_ONLY","DARK_R1",
                      "LIGHT_R1","DARK_R8","LIGHT_R8"):
                scenes.append(make_scene(width,relation,v))
    replays=[{"sample_id":f"BPRED-S3V2R-REPLAY-W{w:02d}-{r}",
              "parent_sample_id":make_scene(w,r,"DARK_R8")["sample_id"],
              "width":w,"relation":r}
             for w in WIDTHS for r in RELATIONS]
    if len(scenes)!=SCENE_COUNT or len(replays)!=6 or len({x["sample_id"] for x in scenes})!=SCENE_COUNT or sum(len(x["runtime_strokes"]) for x in scenes)!=EXPECTED_EVENTS:
        blocked("FROZEN_EXPERIMENT_CARDINALITY")
    return {
        "experiment":EXPERIMENT,"E0_blob":E0_BLOB,
        "game_source_blob":p4d3.ENGINE_GIT_BLOB,
        "renderer_source_blob":p4d3.RENDERER_GIT_BLOB,
        "source_native_scenes":SCENE_COUNT,"original_main_stroke_events":EXPECTED_EVENTS,
        "direct_rgba_expected":2*EXPECTED_EVENTS,"independent_controls":6,"blank":1,
        "native_ROI_node_local_physical":list(ROI),"S0_BLIND_used":False,
        "protected_foreign_policy_unchanged":True,"scenes":scenes,"replays":replays
    }


def verify_source(workspace,engine,renderer,scripts,observer):
    original_q_observer=workspace/"AutoDraw_Stage20"/"tests"/q.OBSERVER_NAME
    q.verify_source(workspace,engine,renderer,scripts,original_q_observer)
    e0=workspace/"AutoDraw_Stage20"/"docs"/E0_NAME
    if not e0.is_file() or p4b1.git_blob(e0.read_bytes())!=E0_BLOB:
        blocked("FIRST_FROZEN_E0_MISSING_OR_DRIFT")
    if observer.name!=OBSERVER or not observer.is_file():
        blocked("NEW_OBSERVER_MISSING")


def decode_rgba64(data):
    if type(data) is not str:
        blocked("ORIGINAL_NATIVE_RAW_BASE64_MISSING")
    try:
        b=base64.b64decode(data,validate=True)
    except (ValueError,base64.binascii.Error) as exc:
        raise ValueError("BLOCKED_BPRED_S3V2R_INVALID_BASE64") from exc
    if len(b)!=ROI[2]*ROI[3]*4:
        blocked("RAW_SOURCE_ROI_LENGTH_DRIFT")
    return b


def raw_frame(raw):
    if not isinstance(raw,(bytes,bytearray)) or len(raw)!=ROI[2]*ROI[3]*4:
        blocked("INVALID_RGBA_RAW_FRAME")
    return np.frombuffer(raw,dtype=np.uint8).reshape(ROI[3],ROI[2],4)


def xy(x,y):
    return {"node_local_physical":[int(ROI[0]+x),int(ROI[1]+y)],
            "aligned_board_physical":[int(ROI[0]+x-6),int(ROI[1]+y-6)]}


def native_scene(driver,scene,output):
    folder=output/"native"/scene["sample_id"]
    folder.mkdir(parents=True,exist_ok=False)
    v2.write_json(folder/"SOURCE_PLAN.json",scene["source_strokes"])
    v2.write_json(folder/"RUNTIME_PLAN.json",scene["runtime_strokes"])
    response=driver.execute_script(
        "return window.AutoDrawBPRED_S3v2rOriginalNativeSequence(arguments[0]);",
        scene["runtime_strokes"])
    if (not isinstance(response,dict) or response.get("schema")!=SCHEMA
            or response.get("originalMethodsRestored") is not True
            or response.get("strokes")!=len(scene["runtime_strokes"])
            or response.get("roi")!={"x":ROI[0],"y":ROI[1],
                                      "width":ROI[2],"height":ROI[3]}
            or not isinstance(response.get("events"),list)
            or len(response["events"])!=len(scene["runtime_strokes"])):
        blocked("NATIVE_TRUE_STROKE_EVENT_MISMATCH_"+scene["sample_id"])
    main=response.get("main")
    mask=response.get("mask")
    if (not isinstance(main,dict) or not isinstance(mask,dict)
            or main.get("node")!={"x":-2,"y":-2,"width":464,"height":244}
            or main.get("size")!=[1392,732]
            or main.get("drawDataCount")!=2+len(scene["runtime_strokes"])
            or main.get("transform")!=[3,0,0,3,6,6]
            or mask.get("node")!={"x":0,"y":0,"width":460,"height":240}
            or mask.get("size")!=[1380,720]
            or mask.get("drawDataCount")!=1
            or mask.get("transform")!=[3,0,0,3,0,0]):
        blocked("ORIGINAL_MAIN_MASK_GEOMETRY_DRIFT")
    canvas,main_sha=v2.read_png_data_url(
        main.pop("nativeCanvasPngDataUrl"),
        folder/(scene["sample_id"]+"_REAL_MAIN_CANVAS.png"))
    m,mask_sha=v2.read_png_data_url(
        mask.pop("nativeCanvasPngDataUrl"),
        folder/(scene["sample_id"]+"_REAL_MASK_CANVAS.png"))
    if canvas.shape!=(732,1392,4) or m.shape!=p4d3.NATIVE_SHAPE:
        blocked("SOURCE_CANVAS_SHAPE_DRIFT")
    aligned,mapping=v2.source_stage_align(canvas,main["node"],main["transform"])
    native,metadata=p4d3.read_webgl_result(
        response["native"],folder,scene["sample_id"]+"_REAL_WEBGL")
    if (native.shape!=p4d3.NATIVE_SHAPE or metadata.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer"
            or metadata.get("strokeCount")!=len(scene["runtime_strokes"])):
        blocked("SOURCE_NATIVE_WEBGL_INVALID")
    source_steps=[];records=[];previous=None
    last_native=None
    for i,event in enumerate(response["events"],1):
        if (not isinstance(event,dict) or event.get("step")!=i
                or not isinstance(event.get("originalContext"),dict)):
            blocked("STROKE_EVENT_CHRONOLOGY_OR_CONTEXT")
        context=event["originalContext"]
        if (context.get("globalCompositeOperation")!="source-over" or
            context.get("globalAlpha")!=1 or
            context.get("lineCap")!="round" or
            context.get("lineJoin")!="round" or
            not isinstance(context.get("transform"),list) or
            len(context["transform"])!=6):
            blocked("ORIGINAL_NATIVE_CANVAS_CONTEXT_CHANGED")
        raws={}
        for stage in ("pre","post"):
            raw=decode_rgba64(event.get(stage+"RGBA_b64"))
            name=f"{scene['sample_id']}_REAL_{stage.upper()}_STROKE_{i:02d}.rgba"
            path=folder/name
            if path.exists():
                blocked("RAW_SOURCE_APPEND_ONLY_OVERWRITE")
            path.write_bytes(raw)
            raws[stage]=raw
        real_png=folder/(scene["sample_id"]+f"_REAL_STROKE_STEP_{i:02d}.png")
        step_png,_=v2.read_png_data_url(event["actualCanvasPngDataUrl"],real_png)
        if step_png.shape!=(732,1392,4):
            blocked("TRUE_ORIGINAL_STEP_PNG_SHAPE")
        pre=raw_frame(raws["pre"]).copy()
        post=raw_frame(raws["post"]).copy()
        expected_png=step_png[ROI[1]:ROI[1]+ROI[3],ROI[0]:ROI[0]+ROI[2]]
        readback_diff=post.astype(np.int16)-expected_png.astype(np.int16)
        gap=0 if previous is None else int(np.any(previous!=pre,axis=2).sum())
        records.append({
            "sample_id":scene["sample_id"],"step":i,"context":context,
            "pre_sha":hashlib.sha256(raws["pre"]).hexdigest(),
            "post_sha":hashlib.sha256(raws["post"]).hexdigest(),
            "post_PNG":real_png.name,
            "pre_vs_previous_post_pixel_gap":gap,
            "same_stroke_prepost_changed_pixels":int(np.any(pre!=post,axis=2).sum()),
            "post_direct_minus_PNG_changed_pixels":int(np.any(readback_diff!=0,axis=2).sum()),
            "post_direct_minus_PNG_alpha_changed_pixels":int(np.count_nonzero(readback_diff[:,:,3]))
        })
        previous=post.copy()
        last_native=post.copy()
        source_steps.append((pre,post))
        # Original true ink must always fit within the frozen original ROI.
        aligned_step,_=v2.source_stage_align(step_png,main["node"],main["transform"])
        outside=aligned_step[:,:,3].copy()
        bx,by=ROI[0]-6,ROI[1]-6
        outside[by:by+ROI[3],bx:bx+ROI[2]]=0
        if np.any(outside):
            blocked("ORIGINAL_TRUE_STROKE_OUTSIDE_PREDECLARED_ROI")
    final_roi=canvas[ROI[1]:ROI[1]+ROI[3],ROI[0]:ROI[0]+ROI[2]]
    if not np.array_equal(last_native[:,:,3],final_roi[:,:,3]):
        blocked("FINAL_NATIVE_GETIMAGEDATA_VS_PNG_ALPHA_DIFFERENCE")
    final_delta=last_native.astype(np.int16)-final_roi.astype(np.int16)
    stage=v2f.quantize_half_up(aligned)
    if stage.shape!=native.shape:
        blocked("ORIGINAL_STAGE_RGBA_SIZE_MISMATCH")
    original_stage={
        "QH_RGB_mismatch_pixels":int(np.any(stage[:,:,:3]!=native[:,:,:3],axis=2).sum()),
        "QH_alpha_mismatch_pixels":int(np.count_nonzero(stage[:,:,3]!=native[:,:,3]))
    }
    v2.write_json(folder/"TRUE_ORIGINAL_NATIVE_PROVENANCE.json",{
        "sample_id":scene["sample_id"],"main":main,"mask":mask,
        "main_PNG_sha256":main_sha,"mask_PNG_sha256":mask_sha,
        "mapping":mapping,"webgl":metadata,"original_stage":original_stage,
        "stroke_events":records
    })
    return {
        "scene":scene,"events":source_steps,"events_meta":records,
        "final_rb":last_native,"final_png":final_roi.copy(),
        "stage":original_stage,
        "final_webgl_roi":p4d3.roi(native,s3.CX,s3.CY).copy(),
        "final_png_readback_difference":int(np.any(final_delta!=0,axis=2).sum())
    }


def analyze(items,output):
    index={(s["scene"]["width"],s["scene"]["relation"],s["scene"]["variant"]):s for s in items}
    effects=[];cases=[];details=[]
    totals={"true_event_gaps":0,"first_owner_mismatches":0,"incremental_changed_occurrences":0,
            "alpha_changed_occurrences":0,"nonmicro_channel_occurrences":0,
            "final_nonmicro_RGB_pixels":0,"final_alpha_changed_pixels":0}
    for width in WIDTHS:
        for relation in RELATIONS:
            top=index[(width,relation,"TOP_ONLY")]["final_rb"]
            for bg in BACKGROUNDS:
                low=index[(width,relation,bg+"_ONLY")]["final_rb"]
                zone=(top[:,:,3]==0)&(low[:,:,3]>0)
                records={}
                for n in REPEATS:
                    source=index[(width,relation,bg+"_R"+str(n))]
                    event=source["events"]
                    first_mismatch=int(np.any(event[0][1]!=low,axis=2).sum())
                    totals["first_owner_mismatches"]+=first_mismatch
                    gaps=sum(row["pre_vs_previous_post_pixel_gap"] for row in source["events_meta"])
                    totals["true_event_gaps"]+=gaps
                    changed=0;alpha_changed=0
                    all_event_positions=set()
                    for k,(pre,post) in enumerate(event):
                        if k==0:
                            continue
                        delta=post.astype(np.int16)-pre.astype(np.int16)
                        activity=zone & np.any(delta!=0,axis=2)
                        changed+=int(activity.sum())
                        alpha_changed+=int((activity&(delta[:,:,3]!=0)).sum())
                        for y,x in np.argwhere(activity):
                            y=int(y);x=int(x)
                            d=delta[y,x]
                            effects.append({
                                "sample_id":source["scene"]["sample_id"],
                                "background":bg,"width":width,"relation":relation,
                                "original_top_event_ordinal":k,
                                **xy(x,y),
                                "pre_RGBA":pre[y,x].tolist(),
                                "post_RGBA":post[y,x].tolist(),
                                "delta_RGBA":d.tolist(),
                                "independent_top_RGBA":top[y,x].tolist(),
                                "independent_lower_RGBA":low[y,x].tolist(),
                                "abs_max_RGB_channel":int(np.abs(d[:3]).max()),
                                "alpha_changed":bool(d[3])
                            })
                            all_event_positions.add((y,x))
                    final=source["final_rb"]
                    difference=final.astype(np.int16)-low.astype(np.int16)
                    anyfinal=zone & np.any(difference!=0,axis=2)
                    alpha=zone & (difference[:,:,3]!=0)
                    nonmicro=zone & np.any(np.abs(difference[:,:,:3])>2,axis=2)
                    maxrgb=int(np.max(np.abs(difference[:,:,:3][zone]))) if np.any(zone) else 0
                    for y,x in np.argwhere(nonmicro|alpha):
                        y=int(y);x=int(x)
                        details.append({
                            "sample_id":source["scene"]["sample_id"],
                            "width":width,"relation":relation,"background":bg,
                            "repeat":n,**xy(x,y),
                            "isolated_top_RGBA":top[y,x].tolist(),
                            "isolated_lower_RGBA":low[y,x].tolist(),
                            "final_RGBA":final[y,x].tolist(),
                            "signed_final_minus_lower_RGBA":difference[y,x].tolist(),
                            "non_micro_RGB":bool(nonmicro[y,x]),
                            "alpha_changed":bool(alpha[y,x])
                        })
                    totals["incremental_changed_occurrences"]+=changed
                    totals["alpha_changed_occurrences"]+=alpha_changed
                    totals["final_nonmicro_RGB_pixels"]+=int(nonmicro.sum())
                    totals["final_alpha_changed_pixels"]+=int(alpha.sum())
                    records[n]={
                        "sample_id":source["scene"]["sample_id"],
                        "original_main_strokes":len(event),
                        "original_lower_vs_first_original_event_RGBA_miss":first_mismatch,
                        "pre_vs_previous_post_gap":gaps,
                        "independent_upper_alpha0_lower_alpha_positive_pixels":int(zone.sum()),
                        "incremental_owner_RGBA_changed_occurrences":changed,
                        "incremental_owner_alpha_changed_occurrences":alpha_changed,
                        "unique_pixels_ever_changed_in_true_B_events":len(all_event_positions),
                        "final_RGBA_changed_owner_pixels":int(anyfinal.sum()),
                        "final_alpha_changed_owner_pixels":int(alpha.sum()),
                        "final_RGB_abs_over2_owner_pixels":int(nonmicro.sum()),
                        "final_RGB_max_abs_channel_delta":maxrgb,
                        "final_original_post_readback_vs_PNG_changed":
                            source["final_png_readback_difference"]
                    }
                cases.append({
                    "width":width,"relation":relation,"lower_background":bg,
                    "R1":records[1],"R8":records[8],
                    "additional_final_changed_owner_pixels_R8_vs_R1":
                        records[8]["final_RGBA_changed_owner_pixels"]-
                        records[1]["final_RGBA_changed_owner_pixels"],
                    "additional_final_over2_owner_pixels_R8_vs_R1":
                        records[8]["final_RGB_abs_over2_owner_pixels"]-
                        records[1]["final_RGB_abs_over2_owner_pixels"]
                })
    if len(cases)!=12 or len({r["sample_id"] for r in effects})>24:
        blocked("FROZEN_CONTRAST_ANALYSIS_CARDINALITY")
    v2.write_json(output/"ALL_12_TRUE_REPEATED_NATIVE_OWNER_PAIRS.json",cases)
    v2.write_json(output/"EVERY_TRUE_INCREMENTAL_OWNER_CHANGED_PIXEL.json",effects)
    v2.write_json(output/"EVERY_FINAL_NON_MICRO_OR_ALPHA_CHANGED_PIXEL.json",details)
    v2.write_json(output/"ALL_TRUE_NATIVE_STROKE_EVENT_METADATA.json",
                  [r for it in items for r in it["events_meta"]])
    return totals,effects,details,cases


def run(workspace,engine,renderer,scripts,observer,output):
    if output.exists():
        blocked("EXISTING_OUTPUT_MUST_NOT_BE_OVERWRITTEN")
    verify_source(workspace,engine,renderer,scripts,observer)
    spec=manifest()
    output.mkdir(parents=True,exist_ok=False)
    v2.write_json(output/"FROZEN_S3V2R_MANIFEST.json",spec)
    with trace.pinned_native_egret_session(workspace) as driver:
        browser={k:driver.capabilities.get(k) for k in
                 ("browserName","browserVersion","platformName")}
        if browser["browserName"]!="firefox" or not str(browser["browserVersion"]).startswith("159."):
            blocked("PINNED_ORIGINAL_BROWSER_MISSING")
        driver.execute_script(observer.read_text("utf8"))
        if driver.execute_script("return window.AutoDrawBPRED_S3v2rObserverInstalled;") is not True:
            blocked("ORIGINAL_SOURCE_OBSERVER_NOT_INSTALLED")
        blank,meta=p4d3.read_webgl_result(
            driver.execute_script(p4d3.CMD,[]),output,"S3V2R_REAL_ORIGINAL_BLANK")
        if meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or np.any(blank[:,:,3]):
            blocked("NOT_TRUE_ORIGINAL_BLANK")
        items=[]
        with (output/"NATIVE_APPEND_ONLY.jsonl").open("x",encoding="utf8") as ledger:
            for scene in spec["scenes"]:
                try:
                    item=native_scene(driver,scene,output)
                except Exception as exc:
                    v2.write_json(output/"BLOCKED_OR_FAILED_SCENE.json",{
                        "sample_id":scene["sample_id"],
                        "previous_completed":len(items),
                        "error_class":type(exc).__name__,"error":str(exc)})
                    raise
                items.append(item)
                ledger.write(json.dumps({
                    "sample_id":scene["sample_id"],
                    "original_main_events":len(item["events"]),
                    "source_sha256":scene["source_plan_sha256"],
                    "runtime_sha256":scene["runtime_plan_sha256"]},
                    ensure_ascii=False,allow_nan=False)+"\n")
                ledger.flush()
                print("S3V2R_REAL_ORIGINAL_EGRET",len(items),"/42",flush=True)
        (output/"replays").mkdir(exist_ok=False)
        replay=[]
        for control in spec["replays"]:
            parent=make_scene(control["width"],control["relation"],"DARK_R8")
            arr,metadata=p4d3.read_scene(
                driver,output/"replays",control["sample_id"]+"_REAL_EGRET",
                parent["runtime_strokes"])
            original=next(x for x in items if x["scene"]["sample_id"]==parent["sample_id"])
            same=bool(np.array_equal(p4d3.roi(arr,s3.CX,s3.CY),
                                     original["final_webgl_roi"]))
            replay.append({
                "sample_id":control["sample_id"],"parent":parent["sample_id"],
                "uninstrumented_native_webgl_ROI_exact":same,
                "PNG_sha256":metadata["source_png_sha256"]})
            if not same:
                v2.write_json(output/"BLOCKED_INDEPENDENT_REPLAY.json",replay)
                blocked("NATIVE_OBSERVER_CHANGED_TRUE_EGRET_OUTCOME")
    v2.write_json(output/"INDEPENDENT_REPLAY_CONTROLS.json",replay)
    totals,effects,details,cases=analyze(items,output)
    eventcount=sum(len(it["events"]) for it in items)
    maxabs=max((max(c["R1"]["final_RGB_max_abs_channel_delta"],
                     c["R8"]["final_RGB_max_abs_channel_delta"]) for c in cases),default=0)
    nonmicro=totals["final_nonmicro_RGB_pixels"]>0
    alpha=totals["final_alpha_changed_pixels"]>0
    report={
        "experiment":EXPERIMENT,"E0_blob":E0_BLOB,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        "browser":browser,"game_source_blob":p4d3.ENGINE_GIT_BLOB,
        "renderer_source_blob":p4d3.RENDERER_GIT_BLOB,
        "new_original_source_scenes":len(items),"native_original_main_PNG":42,
        "native_original_mask_PNG":42,"original_native_webgl_PNG":49,
        "original_main_strokes":eventcount,"original_direct_prepost_RGBA":2*eventcount,
        "uninstrumented_replays":len(replay),
        "replay_all_ROI_exact":all(c["uninstrumented_native_webgl_ROI_exact"] for c in replay),
        "blank_original_alpha0":True,
        "T0_provenance":"PASS",
        "T1_affected_original_pixel_occurrences":len(effects),
        "T1_strict_foreign_zero": "FAIL" if effects else "NO_HARM_OBSERVED_IN_NEW_SAMPLE_ONLY",
        "T1_first_event_vs_isolated_lower_RGBA_different":totals["first_owner_mismatches"],
        "T1_between_actual_event_gap_pixels":totals["true_event_gaps"],
        "T2_final_nonmicro_RGB_abs_gt2_pixels":totals["final_nonmicro_RGB_pixels"],
        "T2_final_changed_alpha_pixels":totals["final_alpha_changed_pixels"],
        "T2_max_final_RGB_abs_channel":maxabs,
        "T2_next_decision":"MATERIAL_EFFECT_OBSERVED" if (nonmicro or alpha) else "SMALL_BYTE_ONLY_IN_SAMPLE",
        "T2_micro_threshold2_diagnostic_only":True,
        "T2_visually_acceptable_unproven":True,
        "T3_source_stage_QH_RGB_misses":sum(it["stage"]["QH_RGB_mismatch_pixels"] for it in items),
        "T3_source_stage_QH_alpha_misses":sum(it["stage"]["QH_alpha_mismatch_pixels"] for it in items),
        "T3_original_post_direct_PNG_different_pixel_occurrences":
            sum(r["post_direct_minus_PNG_changed_pixels"] for it in items for r in it["events_meta"]),
        "T3_actual_step_post_PNG_alpha_different_pixels":
            sum(r["post_direct_minus_PNG_alpha_changed_pixels"] for it in items for r in it["events_meta"]),
        "T4_original_EF_protected_quality":"FAIL_UNCHANGED",
        "T4_previous_S3v2q_strict_foreign":"FAIL_20",
        "T4_previous_S3v2q_G3_usefulness":"FAIL_7653_OF_8633",
        "T4_internal_fractional_alpha":"UNKNOWN",
        "S0_BLIND_used":False,"production_promotion":False,"S4":"NOT_RUN",
        "E4_game":"NOT_RUN","E5_game":"NOT_RUN","exact_game_CHALK":None
    }
    report["members_sha256"]={
        file.relative_to(output).as_posix():hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(output.rglob("*")) if file.is_file()
    }
    v2.write_json(output/"report.json",report)
    print("S3V2R_TRUE_NATIVE_ACCUMULATION",report["T2_next_decision"],
          "MAX_CHANNEL",maxabs,"NON_MICRO",totals["final_nonmicro_RGB_pixels"],
          "ALPHA",totals["final_alpha_changed_pixels"],flush=True)
    print("S3V2R_ORIGINAL_OWNER_CHANGED",len(effects),
          "FIRST_BASELINE",totals["first_owner_mismatches"],
          "EVENT_GAPS",totals["true_event_gaps"],flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for arg in ("workspace","engine","renderer","trace-js","selector-js",
                "stroke-js","observer-js","output"):
        parser.add_argument("--"+arg,type=Path,required=True)
    args=parser.parse_args()
    run(args.workspace,args.engine,args.renderer,
        (args.trace_js,args.selector_js,args.stroke_js),args.observer_js,args.output)
