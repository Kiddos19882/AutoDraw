#!/usr/bin/env python3
"""S3v2j E0: independent NEW original-Egret source RGB hidden alpha0 influence.

Source owner and unsafe tiny alpha effects. Not original E/F, not S4 BLIND or game E4.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_bpred_s3v2_native_canvas_stage as v2
import run_engine001_bpred_s3v2f_prospective_native_rgba8 as v2f
import run_engine001_bpred_s3v2i_all_native_stroke_events as v2i
import run_engine001_bpred_s3v2h_native_stroke_steps as h
import run_engine001_bpred_s3v2c_multicapture_trace as trace
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_bpred_s3v2e_rgba8_quantization as q

EXPERIMENT = "ENGINE001_BPRED_S3V2J_NEW_NATIVE_ALPHA0_OWNER_INFLUENCE_V1"
E0_FILE = "ENGINE001_BPRED001_S3V2J_NEW_NATIVE_ALPHA0_OWNER_INFLUENCE_PREREG_2026-11-20.md"
E0_BLOB = "6801292e01a650a2b014ffe09256313ebe10562b"
WIDTHS = tuple(range(1,11))
ANGLES = (9,43,83,137,175,203,241,277,321,353)
RELATIONS = ("CROSS_ROTATED","NEAR_SKEW")
VARIANTS = ("A_ONLY","B_ONLY","A_THEN_B","B_THEN_A")
ODD_COLORS = (0x218C6F,0xE44D9C)
EVEN_COLORS = (0xA5D742,0x2C49F0)


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3V2J_"+reason)


def midpoint(cx,cy,angle,half):
    r=math.radians(angle)
    dx,dy=half*math.cos(r),half*math.sin(r)
    return [{"x":cx-dx,"y":cy-dy},{"x":cx+dx,"y":cy+dy}]


def plans_for(width,relation):
    if type(width) is not int or width not in WIDTHS or relation not in RELATIONS:
        blocked("NOT_FROZEN_NEW_GEOMETRY")
    px=((5*width+1)%31+.5)/32
    py=((7*width+3)%31+.5)/32
    cx,cy=172+px,120+py
    deg=ANGLES[width-1]
    a=midpoint(cx,cy,deg,11+width%3)
    if relation=="CROSS_ROTATED":
        b=midpoint(cx+.4375,cy-.3125,(deg+103)%360,12+width%2)
    else:
        d=.75*width+.6
        rad=math.radians(deg)
        b=midpoint(cx-math.sin(rad)*d,cy+math.cos(rad)*d,
                   (deg+13)%360,11+width%2)
    if any(not 0<point[key]<(460 if key=="x" else 240)
           for stroke in (a,b) for point in stroke for key in ("x","y")):
        blocked("GEOMETRY_OUTSIDE_ORIGINAL_BOARD")
    first,second=ODD_COLORS if width%2 else EVEN_COLORS
    owners={
        "A":{"strokeId":"bpred-A","width":width,"colorIndex":1,
             "colorRgb":first,"points":a},
        "B":{"strokeId":"bpred-B","width":width,"colorIndex":2,
             "colorRgb":second,"points":b}}
    orders={"A_ONLY":("A",),"B_ONLY":("B",),
            "A_THEN_B":("A","B"),"B_THEN_A":("B","A")}
    result={}
    for variant,order in orders.items():
        original=[dict(owners[k]) for k in order]
        runtime=[{**x,"strokeId":f"icon-{i}"} for i,x in enumerate(original)]
        sample=f"BPRED-S3V2J-W{width:02d}-{relation}-{variant}"
        result[variant]={
            "sample_id":sample,"width":width,"relation":relation,"variant":variant,
            "angle_deg":deg,"phase_xy":[px,py],
            "source_colors":[first,second],"source_strokes":original,
            "runtime_strokes":runtime,
            "source_plan_sha256":s3.digest(s3.canonical(original)),
            "runtime_plan_sha256":s3.digest(s3.canonical(runtime))}
    return result


def manifest():
    scenes=[plans_for(w,relation)[var] for w in WIDTHS
            for relation in RELATIONS for var in VARIANTS]
    controls=[{"sample_id":f"BPRED-S3V2J-REPLAY-W{w:02d}",
               "parent_sample_id":plans_for(w,"CROSS_ROTATED")["A_THEN_B"]["sample_id"],
               "width":w} for w in WIDTHS]
    if len(scenes)!=80 or len(controls)!=10 or len({s["sample_id"] for s in scenes})!=80:
        blocked("SOURCE_MATRIX_DUPLICATE")
    return {"experiment":EXPERIMENT,"E0_blob":E0_BLOB,
            "new_true_native_80":True,"S0_BLIND_used":False,
            "scene_count":80,"replays":10,"blank":1,
            "source_original_game_blob":p4d3.ENGINE_GIT_BLOB,
            "source_original_renderer_blob":p4d3.RENDERER_GIT_BLOB,
            "scenes":scenes,"controls":controls}


def check_source(workspace,engine,renderer,scripts):
    v2i.check_source(workspace,engine,renderer,scripts)
    e0=workspace/"AutoDraw_Stage20"/"docs"/E0_FILE
    if not e0.is_file() or p4b1.git_blob(e0.read_bytes())!=E0_BLOB:
        blocked("NEW_NATIVE_E0_NOT_FROZEN")


def extract_scene(driver,scene,output):
    sid=scene["sample_id"]
    folder=output/"native"/sid
    folder.mkdir(parents=True,exist_ok=False)
    v2.write_json(folder/"SOURCE_PLAN.json",scene["source_strokes"])
    v2.write_json(folder/"RUNTIME_PLAN.json",scene["runtime_strokes"])
    response=driver.execute_script(
        "return window.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace(arguments[0]);",
        scene["runtime_strokes"])
    v2.write_json(folder/"REAL_NATIVE_STROKE_COUNTS.json",
                  v2i.response_counts(response,scene))
    source,events,_=v2i.verify_response(response,scene)
    main,mask=v2i.check_main_mask_geometry(source,scene)
    main_raw,main_sha=v2.read_png_data_url(
        main.pop("originalCanvasPngDataUrl"),folder/(sid+"_REAL_MAIN_CANVAS.png"))
    mask_raw,mask_sha=v2.read_png_data_url(
        mask.pop("originalCanvasPngDataUrl"),folder/(sid+"_REAL_MASK_CANVAS.png"))
    if main_raw.shape!=(732,1392,4) or mask_raw.shape!=p4d3.NATIVE_SHAPE:
        blocked("SOURCE_PIXEL_SHAPE_"+sid)
    canvas,mapping=v2.source_stage_align(main_raw,main["node"],main["transform"])
    Image.fromarray(canvas,mode="RGBA").save(folder/(sid+"_ALIGNED_MAIN_RGBA.png"))
    native,meta=p4d3.read_webgl_result(
        source["native"],folder,sid+"_REAL_WEBGL")
    if native.shape!=p4d3.NATIVE_SHAPE or meta.get("renderer")!=(
            "real Egret 5.4.1 BoardPane/WebGLRenderer") or (
                meta.get("strokeCount")!=len(scene["runtime_strokes"])):
        blocked("WEBGL_SOURCE_NOT_NATIVE_"+sid)
    stage={
        "Q0":q.difference(canvas,native),
        "QH":q.difference(v2f.quantize_half_up(canvas),native)}
    steps=[];deltas=[];prev=None
    for index,event in enumerate(events):
        if (event.get("kind")!="original_main"
                or event.get("canvasSize")!=[1392,732]
                or not isinstance(event.get("originalNativePngDataUrl"),str)):
            blocked("NOT_ORIGINAL_MAIN_EVENT_"+sid)
        raster,sha=v2.read_png_data_url(
            event.pop("originalNativePngDataUrl"),
            folder/(sid+f"_REAL_STROKE_STEP_{index+1:02d}.png"))
        if raster.shape!=(732,1392,4):
            blocked("STEP_PIXEL_SHAPE_"+sid)
        aligned,_=v2.source_stage_align(raster,main["node"],main["transform"])
        delta={"previous_event":"PRE_EVENT_UNKNOWN"}
        if prev is not None:
            _,delta=h.full_delta(prev,aligned)
        deltas.append({"step":index+1,"raw_sha256":sha,"metadata":event,
                       "difference_from_previous":delta})
        prev=aligned
        steps.append(aligned)
    _,last=h.full_delta(steps[-1],canvas)
    v2.write_json(folder/"TRUE_NATIVE_PROVENANCE.json",{
        "sample_id":sid,"main":main,"mask":mask,"main_sha":main_sha,
        "mask_sha":mask_sha,"mapping":mapping,"renderer_meta":meta,
        "maskStrokeEvents":response.get("maskStrokeMetadata"),
        "mainEvents":deltas,"stage":stage,"lastStepToFinalCanvas":last})
    return {"scene":scene,"canvas":canvas,"webgl":native,"first":steps[0],
            "last":steps[-1],"steps":steps,"last_difference":last,"stage":stage}


def calculate_pairs(items,output):
    index={(s["scene"]["width"],s["scene"]["relation"],s["scene"]["variant"]):s
           for s in items}
    rows=[]; changed_pixels=[]
    for width in WIDTHS:
        for relation in RELATIONS:
            rows_v={v:index[(width,relation,v)] for v in VARIANTS}
            ac,bc=rows_v["A_ONLY"]["canvas"],rows_v["B_ONLY"]["canvas"]
            for variant in ("A_THEN_B","B_THEN_A"):
                current=rows_v[variant]
                lower,top=(ac,bc) if variant=="A_THEN_B" else (bc,ac)
                first_delta,first_metric=h.full_delta(current["first"],lower)
                del first_delta
                zone=(lower[:,:,3]>0)&(top[:,:,3]==0)
                delta=current["canvas"].astype(np.int16)-lower.astype(np.int16)
                rgb_change=np.any(delta[:,:,:3]!=0,axis=2)
                alpha_change=(delta[:,:,3]!=0)
                affected=zone&(rgb_change|alpha_change)
                positions=np.argwhere(affected)
                for y,x in positions:
                    y,x=int(y),int(x)
                    changed_pixels.append({
                        "sample_id":current["scene"]["sample_id"],"width":width,
                        "relation":relation,"variant":variant,
                        "native_physical_xy":[x,y],"isolated_lower_RGBA":lower[y,x].tolist(),
                        "isolated_top_RGBA":top[y,x].tolist(),
                        "actual_ordered_RGBA":current["canvas"][y,x].tolist(),
                        "signed_actual_minus_lower_RGBA":delta[y,x].tolist(),
                        "lower_owner_alpha_nonzero":True,"top_owner_isolated_alpha0":True})
                pred=s3.source_over(lower,top)
                base_mask=((ac[:,:,3]>0)|(bc[:,:,3]>0)|(current["canvas"][:,:,3]>0))
                # Frozen original ROI (not a rescaled or fitted masking stage).
                roi_mask=p4d3.roi(ac,s3.CX,s3.CY)[:,:,3]>0
                roi_mask|=p4d3.roi(bc,s3.CX,s3.CY)[:,:,3]>0
                roi_mask|=p4d3.roi(current["canvas"],s3.CX,s3.CY)[:,:,3]>0
                original_canvas,_=s3.rgba_difference(
                    p4d3.roi(pred,s3.CX,s3.CY),
                    p4d3.roi(current["canvas"],s3.CX,s3.CY),roi_mask)
                qh_webgl,_=s3.rgba_difference(
                    p4d3.roi(v2f.quantize_half_up(pred),s3.CX,s3.CY),
                    p4d3.roi(current["webgl"],s3.CX,s3.CY),roi_mask)
                for metric in (original_canvas,qh_webgl):
                    metric["frozen_H1_pass"]=bool(
                        metric["max_channel_byte"]<=2 and metric["mean_channel_byte"]<=1)
                rows.append({
                    "sample_id":current["scene"]["sample_id"],"width":width,
                    "relation":relation,"variant":variant,
                    "first_event_vs_same_run_isolated_owner":first_metric,
                    "last_event_vs_same_run_ordered_main":current["last_difference"],
                    "alpha0_top_owner_region_pixels":int(zone.sum()),
                    "alpha0_top_region_RGB_changed_pixels":int((zone&rgb_change).sum()),
                    "alpha0_top_region_alpha_changed_pixels":int((zone&alpha_change).sum()),
                    "alpha0_top_region_any_changed_pixels":int(affected.sum()),
                    "alpha0_top_region_max_absolute_byte_difference":
                        int(np.abs(delta[affected]).max()) if np.any(affected) else 0,
                    "native_true_main_stroke_count":len(current["steps"]),
                    "original_fixed_C0_canvas":original_canvas,
                    "original_fixed_C0_QH_webgl":qh_webgl})
    if len(rows)!=40 or len({x["sample_id"] for x in rows})!=40:
        blocked("FROZEN_PAIR_COUNT_DRIFT")
    v2.write_json(output/"ALL_40_ORDERED_TRUE_OWNER_EFFECT.json",rows)
    v2.write_json(output/"EVERY_ALPHA0_TOP_OWNER_CHANGED_PIXEL.json",changed_pixels)
    return rows,changed_pixels


def run(workspace,engine,renderer,scripts,output):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    check_source(workspace,engine,renderer,scripts)
    spec=manifest()
    output.mkdir(parents=True)
    v2.write_json(output/"FROZEN_S3V2J_MANIFEST.json",spec)
    items=[]
    with trace.pinned_native_egret_session(workspace) as driver:
        caps={k:driver.capabilities.get(k) for k in
              ("browserName","browserVersion","platformName")}
        if caps["browserName"]!="firefox" or not str(caps["browserVersion"]).startswith("159."):
            blocked("NOT_FIREFOX159")
        for script in scripts:
            driver.execute_script(script.read_text("utf8"))
        if driver.execute_script("return typeof window.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace;")!="function":
            blocked("ORIGINAL_STROKE_ENTRYPOINT_UNAVAILABLE")
        blank,bmeta=p4d3.read_webgl_result(
            driver.execute_script(p4d3.CMD,[]),output,"S3V2J_REAL_EGRET_BLANK")
        if bmeta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or np.any(blank[:,:,3]):
            blocked("BLANK_ALPHA_NOT_ZERO")
        with (output/"NATIVE_APPEND_ONLY.jsonl").open("x",encoding="utf8") as ledger:
            for scene in spec["scenes"]:
                try:
                    item=extract_scene(driver,scene,output)
                except Exception as exc:
                    v2.write_json(output/"BLOCKED_OR_FAILED_SCENE.json",{
                        "sample_id":scene["sample_id"],"prior_complete":len(items),
                        "type":type(exc).__name__,"error":str(exc)})
                    raise
                items.append(item)
                ledger.write(json.dumps({
                    "sample_id":scene["sample_id"],"width":scene["width"],
                    "variant":scene["variant"],"actual_stroke_events":len(item["steps"]),
                    "last_delta":item["last_difference"],
                    "stage_QH":item["stage"]["QH"]},ensure_ascii=False,allow_nan=False)+"\n")
                ledger.flush()
                print("BPRED_S3V2J_NEW_NATIVE_SCENE",len(items),"/80",flush=True)
        (output/"replays").mkdir(exist_ok=False)
        replays=[]
        for control in spec["controls"]:
            case=plans_for(control["width"],"CROSS_ROTATED")["A_THEN_B"]
            result,meta=p4d3.read_scene(driver,output/"replays",
                                         control["sample_id"]+"_REAL_EGRET",case["runtime_strokes"])
            target=next(x for x in items if x["scene"]["sample_id"]==case["sample_id"])["webgl"]
            equal=bool(np.array_equal(p4d3.roi(result,s3.CX,s3.CY),
                                      p4d3.roi(target,s3.CX,s3.CY)))
            replays.append({"sample_id":control["sample_id"],
                            "parent_source_id":case["sample_id"],
                            "RGBA_ROI_exact":equal,"sha256":meta["source_png_sha256"]})
            if not equal:
                blocked("REPLAY_ROI_NOT_IDENTICAL_"+control["sample_id"])
    v2.write_json(output/"REPLAY_CONTROLS.json",replays)
    rows,modified=calculate_pairs(items,output)
    first_diff=sum(r["first_event_vs_same_run_isolated_owner"]["RGBA_different_physical_pixels"]
                   for r in rows)
    last_diff=sum(item["last_difference"]["RGBA_different_physical_pixels"]
                  for item in items)
    canvas_original=sum(int(r["original_fixed_C0_canvas"]["frozen_H1_pass"]) for r in rows)
    webgl_original=sum(int(r["original_fixed_C0_QH_webgl"]["frozen_H1_pass"]) for r in rows)
    qh_stage=sum(item["stage"]["QH"]["rgb_mismatch_pixels"] for item in items)
    qh_alpha=sum(item["stage"]["QH"]["alpha_mismatch_pixels"] for item in items)
    report={"experiment":EXPERIMENT,"E0_blob":E0_BLOB,
            "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
            "browser":caps,"original_game_engine_blob":p4d3.ENGINE_GIT_BLOB,
            "original_renderer_blob":p4d3.RENDERER_GIT_BLOB,
            "true_new_native_primary":80,"true_main_canvas_PNG":80,
            "true_mask_canvas_PNG":80,"true_final_webgl_PNG":91,
            "replays":10,"blank_alpha0":True,"true_stroke_snapshots":sum(len(x["steps"]) for x in items),
            "H1_first_owner_exact_40":"PASS" if first_diff==0 else "FAIL",
            "H1_last_native_main_exact_80":"PASS" if last_diff==0 else "FAIL",
            "H1_first_rgba_different_pixels":first_diff,
            "H1_last_rgba_different_pixels":last_diff,
            "H2_hidden_top_alpha0_native_owner_changed_pixel_occurrences":len(modified),
            "H2_hidden_top_alpha0_detection":"DETECTED" if modified else "NOT_DETECTED",
            "H3_original_C0_canvas_pass_count_40":canvas_original,
            "H3_original_C0_QH_webgl_pass_count_40":webgl_original,
            "H3_QH_stage_RGB_mismatch_pixels":qh_stage,
            "H3_QH_stage_alpha_mismatch_pixels":qh_alpha,
            "native_stroke_count_distribution":[{"id":x["scene"]["sample_id"],
                                                 "events":len(x["steps"])} for x in items],
            "original_S3v2f_H2":"FAIL_UNCHANGED",
            "original_S3v2g_P2":"FAIL_UNCHANGED",
            "original_S3v2h_fixed_count":"BLOCKED_UNCHANGED",
            "original_EF_protected_quality":"FAIL_UNCHANGED",
            "S0_BLIND_used":False,"E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
            "exact_game_CHALK":None,"production_promotion":False,
            "model_is_research_only":True}
    report["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):h.digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()}
    v2.write_json(output/"report.json",report)
    print("BPRED_S3V2J_NEW_EGRET_H1",report["H1_first_owner_exact_40"],
          report["H1_last_native_main_exact_80"],flush=True)
    print("BPRED_S3V2J_HIDDEN_ALPHA0_EFFECT",len(modified),flush=True)
    print("BPRED_S3V2J_FROZEN_C0",canvas_original,webgl_original,
          "QH_STAGE",qh_stage,qh_alpha,flush=True)
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for k in ("workspace","engine","renderer","trace-js","selector-js","stroke-js","output"):
        ap.add_argument("--"+k,required=True,type=Path)
    a=ap.parse_args()
    run(a.workspace,a.engine,a.renderer,
        (a.trace_js,a.selector_js,a.stroke_js),a.output)
