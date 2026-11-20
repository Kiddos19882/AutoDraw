#!/usr/bin/env python3
"""S3v2i: frozen full original Egret stroke-event capture; no guessed count/owner.

Research-only source-known S3; never S0 BLIND, original RGB paint/executor/master.
"""
from __future__ import annotations
import argparse
import io
import json
import os
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_bpred_s3v2h_native_stroke_steps as h
import run_engine001_bpred_s3v2_native_canvas_stage as v2
import run_engine001_bpred_s3v2c_multicapture_trace as ctrace
import run_engine001_bpred_s3v2f_prospective_native_rgba8 as v2f
import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
from engine001_bpred_s3v2b_png_equivalence import verify_parent_png_equivalence

EXPERIMENT = "ENGINE001_BPRED_S3V2I_ALL_ORIGINAL_NATIVE_STROKE_EVENTS_V1"
E0_NAME = "ENGINE001_BPRED001_S3V2I_ALL_NATIVE_STROKE_EVENTS_PREREG_2026-11-20.md"
E0_BLOB = "9350e69c5f83747a46c71eeb9142065be928a7a5"


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3V2I_" + reason)


def check_source(workspace, engine, renderer, scripts):
    h.check_pins(workspace,engine,renderer,scripts)
    e0=workspace/"AutoDraw_Stage20"/"docs"/E0_NAME
    if not e0.is_file() or p4b1.git_blob(e0.read_bytes()) != E0_BLOB:
        blocked("FROZEN_E0_MISSING_OR_MUTATED")
    return True


def response_counts(response, scene):
    if not isinstance(response,dict):
        blocked("NOT_DICT_SOURCE")
    src=response.get("source")
    events=response.get("mainStrokeSnapshots")
    if not isinstance(src,dict) or not isinstance(events,list):
        blocked("MISSING_SOURCE_OR_EVENTS")
    return {
        "sample_id":scene["sample_id"],"variant":scene["variant"],
        "source_stroke_count":len(scene["runtime_strokes"]),
        "original_main_stroke_calls":response.get("trueMainStrokeCalls"),
        "actual_main_event_count":len(events),
        "original_mask_stroke_calls":response.get("originalMaskStrokeCalls"),
        "original_stroke_method_restored":response.get("originalStrokeMethodRestored"),
        "original_renderer_method_restored":src.get("originalCanvasRendererRestored"),
        "original_render_capture_count":src.get("originalCaptureCount")
    }


def verify_response(response, scene):
    counts=response_counts(response,scene)
    source=response["source"]
    events=response["mainStrokeSnapshots"]
    if (response.get("schema")!="ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE"
            or counts["original_stroke_method_restored"] is not True
            or counts["original_renderer_method_restored"] is not True
            or source.get("originalCaptureCount")!=2
            or source.get("structuralSelectionVersion")!="S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1"
            or source.get("sourceStrokeCount")!=len(scene["runtime_strokes"])
            or not isinstance(source.get("captures"),list)
            or len(source["captures"])!=1
            or not isinstance(source.get("mask_capture"),dict)):
        blocked("ORIGINAL_NATIVE_SOURCE_PROVENANCE_"+scene["sample_id"])
    # Unlike v2h, the count is an observation, never forced to 1/2.
    if (counts["original_main_stroke_calls"] != len(events)
            or not 1 <= len(events) <= 32):
        blocked("UNSUPPORTED_NATIVE_MAIN_CALL_COUNT_"+scene["sample_id"]+
                "_"+str(len(events)))
    mask_events=response.get("maskStrokeMetadata")
    if (not isinstance(mask_events,list)
            or counts["original_mask_stroke_calls"]!=len(mask_events)):
        blocked("MASK_EVENT_METADATA_INVALID_"+scene["sample_id"])
    return source,events,counts


def check_main_mask_geometry(source, scene):
    main,mask=source["captures"][0],source["mask_capture"]
    if (main.get("node")!={"x":-2,"y":-2,"width":464,"height":244}
            or main.get("canvasSize")!=[1392,732]
            or main.get("transform")!=[3,0,0,3,6,6]
            or main.get("drawDataCount")!=2+len(scene["runtime_strokes"])
            or mask.get("node")!={"x":0,"y":0,"width":460,"height":240}
            or mask.get("canvasSize")!=[1380,720]
            or mask.get("transform")!=[3,0,0,3,0,0]
            or mask.get("drawDataCount")!=1):
        blocked("MAIN_MASK_NODE_DRIFT_"+scene["sample_id"])
    return main,mask


def native_scene(driver,z,scene,output):
    sid=scene["sample_id"]
    folder=output/"native"/sid
    folder.mkdir(parents=True,exist_ok=False)
    v2.write_json(folder/"SOURCE_PLAN.json",scene["source_strokes"])
    v2.write_json(folder/"RUNTIME_PLAN.json",scene["runtime_strokes"])
    response=driver.execute_script(
        "return window.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace(arguments[0]);",
        scene["runtime_strokes"])
    counts=response_counts(response,scene)
    v2.write_json(folder/"REAL_NATIVE_STROKE_COUNTS.json",counts)
    source,events,_=verify_response(response,scene)
    main,mask=check_main_mask_geometry(source,scene)
    true_main,main_sha=v2.read_png_data_url(
        main.pop("originalCanvasPngDataUrl"),folder/(sid+"_REAL_MAIN_CANVAS.png"))
    true_mask,mask_sha=v2.read_png_data_url(
        mask.pop("originalCanvasPngDataUrl"),folder/(sid+"_REAL_MASK_CANVAS.png"))
    if true_main.shape!=(732,1392,4) or true_mask.shape!=p4d3.NATIVE_SHAPE:
        blocked("CANVAS_SHAPE_"+sid)
    aligned,mapping=v2.source_stage_align(true_main,main["node"],main["transform"])
    Image.fromarray(aligned,mode="RGBA").save(folder/(sid+"_ALIGNED_MAIN_RGBA.png"))
    webgl,webgl_meta=p4d3.read_webgl_result(
        source["native"],folder,sid+"_REAL_WEBGL")
    if (webgl.shape!=p4d3.NATIVE_SHAPE
            or webgl_meta.get("schema")!="ENGINE001_B1R_P4A2_NATIVE_1_TO_10"
            or webgl_meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer"
            or webgl_meta.get("strokeCount")!=len(scene["runtime_strokes"])):
        blocked("WEBGL_NOT_TRUE_NATIVE_"+sid)
    parent_prefix="native/"+sid+"/"+sid
    parent_eq=verify_parent_png_equivalence(
        z.read(parent_prefix+"_REAL_WEBGL.png"),
        (folder/(sid+"_REAL_WEBGL.png")).read_bytes())
    with Image.open(io.BytesIO(z.read(parent_prefix+"_ALIGNED_MAIN_RGBA.png"))) as im:
        old=np.asarray(im.convert("RGBA"),dtype=np.uint8).copy()
    if not np.array_equal(old,aligned):
        blocked("PARENT_MAIN_RGBA_CHANGED_"+sid)
    v2.write_json(folder/"REAL_NATIVE_SOURCE_PROVENANCE.json",{
        "sample_id":sid,"main":main,"mask":mask,"main_sha256":main_sha,
        "mask_sha256":mask_sha,"node_mapping":mapping,
        "webgl_native_meta":webgl_meta,
        "parent_real_webgl_equivalent":parent_eq})
    steps=[]; event_summaries=[]; previous=None
    for i,event in enumerate(events):
        if (not isinstance(event,dict)
                or event.get("kind")!="original_main"
                or event.get("canvasSize")!=[1392,732]
                or not isinstance(event.get("originalNativePngDataUrl"),str)
                or not isinstance(event.get("transform"),list)
                or len(event["transform"])!=6
                or any(not isinstance(x,(int,float)) or not np.isfinite(x)
                       for x in event["transform"])):
            blocked("NATIVE_STROKE_EVENT_PROVENANCE_"+sid+"_"+str(i))
        raster,raw_sha=v2.read_png_data_url(
            event.pop("originalNativePngDataUrl"),
            folder/(sid+f"_REAL_NATIVE_STEP_{i+1:02d}.png"))
        if raster.shape!=(732,1392,4):
            blocked("NATIVE_STEP_SHAPE_"+sid+"_"+str(i))
        step,m=v2.source_stage_align(raster,main["node"],main["transform"])
        event["raw_png_sha256"]=raw_sha
        event["chronological_step"]=i+1
        if previous is None:
            metric={"previous_event":"PRE_EVENT_UNKNOWN"}
        else:
            delta,metric=h.full_delta(previous,step)
            Image.fromarray(delta,mode="RGBA").save(
                folder/(sid+f"_DELTA_STEP_{i:02d}_TO_{i+1:02d}.png"))
            metric["previous_event"]="REAL_NATIVE_STEP_"+str(i)
        event_summaries.append({"event":event,"delta_from_previous":metric})
        previous=step
        steps.append(step)
    final_delta,final_metric=h.full_delta(steps[-1],aligned)
    Image.fromarray(final_delta,mode="RGBA").save(folder/"LAST_STEP_TO_FINAL_MAIN_RGBA_DELTA.png")
    v2.write_json(folder/"REAL_NATIVE_ALL_EVENT_METADATA.json",{
        "main_event_count":len(events),"original_mask_events":response["maskStrokeMetadata"],
        "chronological_event_deltas":event_summaries,
        "last_step_to_real_original_main":final_metric,
        "source_plan_sha256":scene["source_plan_sha256"],
        "runtime_plan_sha256":scene["runtime_plan_sha256"]})
    return {"scene":scene,"canvas":aligned,"webgl":webgl,
            "steps":steps,"last_metric":final_metric,
            "parent_webgl_equivalent":parent_eq}


def comparisons(items,output):
    seen={(x["scene"]["width"],x["scene"]["relation"],x["scene"]["variant"]):x
          for x in items}
    result=[]
    for width in h.WIDTHS:
        for relation in h.RELATIONS:
            pair={v:seen[(width,relation,v)] for v in h.VARIANTS}
            a,b=pair["A_ONLY"]["canvas"],pair["B_ONLY"]["canvas"]
            for variant in h.VARIANTS:
                item=pair[variant]
                sid=item["scene"]["sample_id"]
                observations=[]
                for i,step in enumerate(item["steps"]):
                    _,against_a=h.full_delta(step,a)
                    _,against_b=h.full_delta(step,b)
                    observations.append({"event_number":i+1,
                                         "exact_rgba_different_vs_actual_A_ONLY":against_a,
                                         "exact_rgba_different_vs_actual_B_ONLY":against_b})
                row={"sample_id":sid,"width":width,"relation":relation,
                     "variant":variant,"true_main_stroke_calls":len(item["steps"]),
                     "last_to_original_main":item["last_metric"],
                     "all_events_vs_both_original_isolated_owners":observations}
                if variant in ("A_THEN_B","B_THEN_A"):
                    expected=s3.source_over(a,b) if variant=="A_THEN_B" else s3.source_over(b,a)
                    roi_expected=p4d3.roi(expected,s3.CX,s3.CY)
                    native_main=p4d3.roi(item["canvas"],s3.CX,s3.CY)
                    native_webgl=p4d3.roi(item["webgl"],s3.CX,s3.CY)
                    mask=((p4d3.roi(a,s3.CX,s3.CY)[:,:,3]>0)
                          |(p4d3.roi(b,s3.CX,s3.CY)[:,:,3]>0)
                          |(native_main[:,:,3]>0))
                    ca,_=s3.rgba_difference(roi_expected,native_main,mask)
                    we,_=s3.rgba_difference(v2f.quantize_half_up(roi_expected),
                                            native_webgl,mask)
                    for m in (ca,we):
                        m["original_H1_pass"]=bool(
                            m["max_channel_byte"]<=2 and m["mean_channel_byte"]<=1)
                    row["original_frozen_canvas_C0"]=ca
                    row["original_frozen_QH_webgl_C0"]=we
                result.append(row)
    return result


def run(workspace,engine,renderer,scripts,source_zip,output):
    if output.exists():
        blocked("OUTPUT_ALREADY_EXISTS")
    check_source(workspace,engine,renderer,scripts)
    with zipfile.ZipFile(source_zip) as z:
        matrix=h.verify_parent(z)
        output.mkdir(parents=True)
        selected=[matrix[(w,r,v)] for w in h.WIDTHS for r in h.RELATIONS for v in h.VARIANTS]
        v2.write_json(output/"FROZEN_EXISTING_S3V2F_24_SOURCE_PLANS.json",selected)
        items=[]
        with ctrace.pinned_native_egret_session(workspace) as driver:
            caps={k:driver.capabilities.get(k) for k in
                  ("browserName","browserVersion","platformName")}
            if caps["browserName"]!="firefox" or not str(caps["browserVersion"]).startswith("159."):
                blocked("NOT_FIREFOX159")
            for script in scripts:
                driver.execute_script(script.read_text("utf8"))
            if driver.execute_script("return typeof window.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace;")!="function":
                blocked("NATIVE_STROKE_OBSERVER_NOT_INSTALLED")
            blank,blank_meta=p4d3.read_webgl_result(
                driver.execute_script(p4d3.CMD,[]),output,"S3V2I_REAL_EGRET_BLANK")
            if blank_meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or np.any(blank[:,:,3]):
                blocked("REAL_BLANK_ALPHA_NONZERO")
            with (output/"OBSERVED_ORIGINAL_NATIVE_EVENT_COUNTS.jsonl").open("x",encoding="utf8") as ledger:
                for scene in selected:
                    try:
                        item=native_scene(driver,z,scene,output)
                    except Exception as exc:
                        v2.write_json(output/"BLOCKED_OR_FAILED_SCENE.json",{
                            "sample_id":scene["sample_id"],"successful_before_failure":len(items),
                            "exception":str(exc),"exception_type":type(exc).__name__})
                        raise
                    items.append(item)
                    row={"sample_id":scene["sample_id"],"variant":scene["variant"],
                         "width":scene["width"],"relation":scene["relation"],
                         "native_main_stroke_calls":len(item["steps"]),
                         "last_vs_final_main_RGBA_differing_pixels":
                             item["last_metric"]["RGBA_different_physical_pixels"]}
                    ledger.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                    ledger.flush()
                    print("BPRED_S3V2I_REAL_EVENT_SCENE",len(items),"/24",flush=True)
            (output/"replays").mkdir(exist_ok=False)
            replay_rows=[]
            for width in h.WIDTHS:
                scene=matrix[(width,"CROSS_ROTATED","A_THEN_B")]
                sid=f"BPRED-S3V2I-REPLAY-W{width:02d}"
                native,meta=p4d3.read_scene(
                    driver,output/"replays",sid+"_REAL_EGRET",scene["runtime_strokes"])
                compare=next(i for i in items if i["scene"]["sample_id"]==scene["sample_id"])["webgl"]
                exact=bool(np.array_equal(p4d3.roi(native,s3.CX,s3.CY),
                                          p4d3.roi(compare,s3.CX,s3.CY)))
                replay_rows.append({"sample_id":sid,"parent":scene["sample_id"],
                                    "RGBA_ROI_exact":exact,
                                    "raw_sha256":meta["source_png_sha256"]})
                if not exact:
                    blocked("REPLAY_ROI_DRIFT_"+sid)
        v2.write_json(output/"REPLAY_CONTROLS.json",replay_rows)
        rows=comparisons(items,output)
        v2.write_json(output/"ALL_NATIVE_STROKE_COMPARISONS_24.json",rows)
        s1=sum(r["last_to_original_main"]["RGBA_different_physical_pixels"] for r in rows)
        old_canvas=sum(int(r["original_frozen_canvas_C0"]["original_H1_pass"])
                       for r in rows if r["variant"] in ("A_THEN_B","B_THEN_A"))
        old_webgl=sum(int(r["original_frozen_QH_webgl_C0"]["original_H1_pass"])
                        for r in rows if r["variant"] in ("A_THEN_B","B_THEN_A"))
        event_distribution=[
            {"sample_id":i["scene"]["sample_id"],"variant":i["scene"]["variant"],
             "number_of_true_main_stroke_events":len(i["steps"])}
            for i in items]
        report={"experiment":EXPERIMENT,"E0_blob":E0_BLOB,
                "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
                "native_browser":caps,"source_original_E3_run":h.PARENT_RUN,
                "source_original_E3_sha":h.PARENT_SHA,
                "source_original_E3_verified_member_SHA":h.PARENT_MEMBER_COUNT,
                "true_original_scenes":24,"true_main_canvas_PNG":24,"true_mask_canvas_PNG":24,
                "true_final_webgl_PNG":28,"true_replays":3,"blank_alpha0":True,
                "native_main_event_distribution":event_distribution,
                "native_main_stroke_event_PNG":sum(len(i["steps"]) for i in items),
                "last_step_vs_real_main_different_RGBA_pixels":s1,
                "H1_native_final_stroke_exact":"PASS" if s1==0 else "FAIL",
                "original_C0_real_canvas_pass_count_12":old_canvas,
                "original_C0_QH_webgl_pass_count_12":old_webgl,
                "original_S3v2f_two_owner_H2":"FAIL_UNCHANGED",
                "original_S3v2g_integer_P2":"FAIL_UNCHANGED",
                "original_S3v2h_fixed_operation_count":"BLOCKED_PRESERVED",
                "owner_operation_attribution":"UNKNOWN",
                "no_new_model_validation":True,"S0_BLIND_used":False,
                "E4_live_game":"NOT_RUN","E5_independent":"NOT_RUN",
                "exact_game_CHALK":None,"production_promotion":False}
        report["members_sha256"]={
            str(p.relative_to(output)).replace("\\","/"):h.digest(p.read_bytes())
            for p in sorted(output.rglob("*")) if p.is_file()}
        v2.write_json(output/"report.json",report)
        print("BPRED_S3V2I_NATIVE_EVENTS_24",report["native_main_stroke_event_PNG"],flush=True)
        print("BPRED_S3V2I_LAST_TO_FINAL",report["H1_native_final_stroke_exact"],s1,flush=True)
        print("BPRED_S3V2I_ORIGINAL_C0",old_canvas,old_webgl,flush=True)
        return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for name in ("workspace","engine","renderer","trace-js","selector-js","stroke-js",
                 "source-zip","output"):
        ap.add_argument("--"+name,required=True,type=Path)
    a=ap.parse_args()
    run(a.workspace,a.engine,a.renderer,(a.trace_js,a.selector_js,a.stroke_js),
        a.source_zip,a.output)
