#!/usr/bin/env python3
"""BPRED-S3v2f: prospectively frozen original Egret Canvas/WebGL RGB8 test.

Research-only, new native S3 scenes. Never S0 BLIND, production, or game CHALK.
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
import run_engine001_bpred_s3v2c_multicapture_trace as trace_session
import run_engine001_bpred_s3v2e_rgba8_quantization as q
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3

EXPERIMENT = "ENGINE001_BPRED_S3V2F_PROSPECTIVE_ORIGINAL_EGRET_RGBA8_V1"
E0_FILE = "ENGINE001_BPRED001_S3V2F_PROSPECTIVE_NATIVE_RGBA8_PREREG_2026-11-20.md"
E0_BLOB = "24259eeeadb9451c43390bdcf5a01fb67c7cf39a"
RELATIONS = ("CROSS_ROTATED", "NEAR_SKEW")
VARIANTS = ("A_ONLY", "B_ONLY", "A_THEN_B", "B_THEN_A")
WIDTHS = tuple(range(1, 11))
PHASES = ((3/16, 11/16), (13/16, 1/16), (5/16, 7/16), (15/16, 9/16))
ANGLES = (25, 73, 119, 167, 211, 257, 293, 339, 47, 131)
COLORS_ODD = (0x503D35, 0xC54191)
COLORS_EVEN = (0x13B6E2, 0xF4A31D)
S3_BLOB = "1bf56df9507f2a34fd16e68eef190229c3184ce5"
V2_BLOB = "511e81a362c4340e0dfdc36a292faa9cb2ef1e83"
Q_BLOB = "82f8e0c3f3e10fb30ea61d1beb52edf98696563c"
TRACE_PY_BLOB = "974de6a86359e9ff49e2e77ee1f420dffa08064b"
JS_FILES = (
    "engine001_bpred_s3v2c_multicapture_trace.js",
    "engine001_bpred_s3v2d_source_node_selector.js",
    "engine001_bpred_s3v2f_gl_upload_observer.js"
)
JS_BLOBS = (
    "250a6f46c12498c15157825664a08ee4f12a2b83",
    "de3b5c5f956e3de7a71817830874b346904bc9e2",
    "75ee0779cf1bf06ad89f0b0368f6a31725f2fa23"
)


def blocked(label):
    raise ValueError("BLOCKED_BPRED_S3V2F_" + label)


def midpoint_stroke(cx, cy, degrees, half_length):
    r = math.radians(degrees)
    x, y = half_length * math.cos(r), half_length * math.sin(r)
    return [{"x": cx-x, "y": cy-y}, {"x": cx+x, "y": cy+y}]


def plans_for(width, relation):
    if type(width) is not int or width not in WIDTHS or relation not in RELATIONS:
        blocked("UNFROZEN_INPUT")
    px, py = PHASES[(width-1) % 4]
    cx, cy = 172+px, 120+py
    deg = ANGLES[width-1]
    rad = math.radians(deg)
    pa = midpoint_stroke(cx, cy, deg, 10+width%3)
    if relation == "CROSS_ROTATED":
        pb = midpoint_stroke(cx+.375, cy-.25, (deg+97)%360, 11+width%2)
    else:
        displacement = .65*width+.35
        pb = midpoint_stroke(cx-math.sin(rad)*displacement,
                             cy+math.cos(rad)*displacement,
                             (deg+11)%360, 10+width%2)
    if any(not (0 < p["x"] < 460 and 0 < p["y"] < 240)
           for stroke in (pa, pb) for p in stroke):
        blocked("BOARD_CLIPPED")
    c_a, c_b = COLORS_ODD if width % 2 else COLORS_EVEN
    items = {
        "A": {"strokeId": "bpred-A", "width": width,
              "colorIndex": 1, "colorRgb": c_a, "points": pa},
        "B": {"strokeId": "bpred-B", "width": width,
              "colorIndex": 2, "colorRgb": c_b, "points": pb}}
    order = {
        "A_ONLY": ("A",),
        "B_ONLY": ("B",),
        "A_THEN_B": ("A", "B"),
        "B_THEN_A": ("B", "A")}
    result = {}
    for variant in VARIANTS:
        source = [dict(items[key]) for key in order[variant]]
        runtime = [{**item, "strokeId": f"icon-{i}"} for i,item in enumerate(source)]
        if any({k:v for k,v in x.items() if k != "strokeId"} !=
               {k:v for k,v in y.items() if k != "strokeId"}
               for x,y in zip(source, runtime)):
            blocked("RUNTIME_SOURCE_MUTATION")
        sid = f"BPRED-S3V2F-W{width:02d}-{relation}-{variant}"
        result[variant] = {
            "sample_id":sid, "width":width, "relation":relation, "variant":variant,
            "phase": [px,py], "a_direction_deg":deg,
            "color_pair": [c_a,c_b],
            "source_strokes":source, "runtime_strokes":runtime,
            "source_plan_sha256":s3.digest(s3.canonical(source)),
            "runtime_plan_sha256":s3.digest(s3.canonical(runtime))}
    return result


def manifest():
    scenes=[plans_for(w,rel)[v] for w in WIDTHS for rel in RELATIONS for v in VARIANTS]
    controls=[{"sample_id":f"BPRED-S3V2F-REPLAY-W{w:02d}",
               "parent_sample_id":plans_for(w,"CROSS_ROTATED")["A_THEN_B"]["sample_id"],
               "width":w} for w in WIDTHS]
    if (len(scenes),len(controls),len({x["sample_id"] for x in scenes})) != (80,10,80):
        blocked("MANIFEST_CARDINALITY")
    return {"experiment":EXPERIMENT, "E0_blob":E0_BLOB, "new_primary":80,
            "replays":10, "blank":1, "final_webgl_PNG":91, "main_PNG":80,
            "mask_PNG":80, "S0_BLIND_used":False,
            "source_game_blob":p4d3.ENGINE_GIT_BLOB,
            "source_renderer_blob":p4d3.RENDERER_GIT_BLOB,
            "scenes":scenes, "controls":controls}


def quantize_half_up(rgba):
    if not isinstance(rgba,np.ndarray) or rgba.dtype!=np.uint8 or rgba.ndim!=3 or rgba.shape[-1]!=4:
        blocked("QH_INPUT_RGBA")
    out=rgba.copy()
    alpha=rgba[:,:,3]
    mask=(alpha>0)&(alpha<255)
    if np.any(mask):
        a=alpha[mask].astype(np.float64)[:,None]
        rgb=rgba[mask,:3].astype(np.float64)
        p=np.ceil(rgb*a/255.0)
        out[mask,:3]=np.clip(np.floor(255.0*p/a+.5),0,255).astype(np.uint8)
    if not np.array_equal(out[:,:,3],alpha):
        blocked("ALPHA_MUTATED")
    return out


def stage_diff(canvas, native):
    if canvas.shape != p4d3.NATIVE_SHAPE or native.shape != p4d3.NATIVE_SHAPE:
        blocked("STAGE_SHAPE")
    if not np.array_equal(canvas[:,:,3],native[:,:,3]):
        blocked("STAGE_NATIVE_ALPHA_CHANGED")
    return {mode:q.difference(pred,native) for mode,pred in (
        ("Q0",canvas),("QC",q.quantize_stage(canvas,"QC")),
        ("QH",quantize_half_up(canvas)))}


def ordered_metrics(width, relation, frames):
    ordered={}
    for variant in ("A_THEN_B","B_THEN_A"):
        ac,bc=(frames["A_ONLY"]["canvas"],frames["B_ONLY"]["canvas"])
        bottom,top=(ac,bc) if variant=="A_THEN_B" else (bc,ac)
        expected=s3.source_over(bottom,top)
        target_canvas=frames[variant]["canvas"]
        target_webgl=frames[variant]["webgl"]
        union=(ac[:,:,3]>0)|(bc[:,:,3]>0)|(target_webgl[:,:,3]>0)
        canvas_metric,_=s3.rgba_difference(expected,target_canvas,union)
        canvas_metric["frozen_H1_pass"]=bool(
            canvas_metric["max_channel_byte"]<=2 and canvas_metric["mean_channel_byte"]<=1)
        corrected={}
        for mode,pred in (("Q0",expected),
                          ("QC",q.quantize_stage(expected,"QC")),
                          ("QH",quantize_half_up(expected))):
            metric,_=s3.rgba_difference(pred,target_webgl,union)
            metric["frozen_H1_pass"]=bool(
                metric["max_channel_byte"]<=2 and metric["mean_channel_byte"]<=1)
            corrected[mode]=metric
        web_a,web_b=frames["A_ONLY"]["webgl"],frames["B_ONLY"]["webgl"]
        wb,wt=(web_a,web_b) if variant=="A_THEN_B" else (web_b,web_a)
        original=s3.source_over(wb,wt)
        original_metric,_=s3.rgba_difference(original,target_webgl,union)
        original_metric["frozen_H1_pass"]=bool(
            original_metric["max_channel_byte"]<=2 and original_metric["mean_channel_byte"]<=1)
        ordered[variant]={"canvas_native_C0":canvas_metric,
                          "original_webgl_C0":original_metric,
                          "canvas_to_webgl_C0":corrected}
    return {"pair_id":f"BPRED-S3V2F-W{width:02d}-{relation}",
            "width":width,"relation":relation,"ordered_variants":ordered}


def check_inputs(workspace,engine,renderer,js_files):
    pinned=[
        (workspace/"AutoDraw_Stage20"/"docs"/E0_FILE,E0_BLOB),
        (engine,p4d3.ENGINE_GIT_BLOB),(renderer,p4d3.RENDERER_GIT_BLOB),
        (Path(s3.__file__),S3_BLOB),(Path(v2.__file__),V2_BLOB),
        (Path(q.__file__),Q_BLOB),(Path(trace_session.__file__),TRACE_PY_BLOB)]
    pinned.extend(zip(js_files,JS_BLOBS))
    for path,blob in pinned:
        if not path.is_file() or p4b1.git_blob(path.read_bytes())!=blob:
            blocked("PINNED_SOURCE_"+path.name)
    if tuple(path.name for path in js_files)!=JS_FILES:
        blocked("JS_ORDER_DRIFT")
    return True


def read_original_scene(driver,case,out,frames):
    sid=case["sample_id"]
    folder=out/"native"/sid
    folder.mkdir(parents=True,exist_ok=False)
    v2.write_json(folder/"SOURCE_PLAN.json",case["source_strokes"])
    v2.write_json(folder/"RUNTIME_PLAN.json",case["runtime_strokes"])
    response=driver.execute_script(
        "return window.AutoDrawBPRED_S3v2fCapture(arguments[0]);",
        case["runtime_strokes"])
    if (not isinstance(response,dict) or response.get("schema")!=
            "ENGINE001_BPRED_S3V2F_TRUE_ORIGINAL_MAIN_MASK_GL" or
            response.get("originalMethodsRestored") is not True or
            not isinstance(response.get("glUploads"),list) or
            response.get("mainCanvasTypedUploadCount",0)<1 or
            not isinstance(response.get("source"),dict)):
        blocked("TRUE_GL_SOURCE_MISSING_"+sid)
    stage=response["source"]
    if (stage.get("structuralSelectionVersion")!="S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1" or
            stage.get("originalCaptureCount")!=2 or
            not stage.get("originalCanvasRendererRestored") or
            stage.get("sourceStrokeCount")!=len(case["runtime_strokes"]) or
            len(stage.get("captures",[]))!=1 or
            not isinstance(stage.get("mask_capture"),dict)):
        blocked("CANVAS_SOURCE_PROVENANCE_"+sid)
    main=stage["captures"][0]
    mask=stage["mask_capture"]
    if (main.get("node")!={"x":-2,"y":-2,"width":464,"height":244} or
            main.get("canvasSize")!=[1392,732] or
            main.get("transform")!=[3,0,0,3,6,6] or
            main.get("drawDataCount")!=2+len(case["runtime_strokes"]) or
            mask.get("node")!={"x":0,"y":0,"width":460,"height":240} or
            mask.get("canvasSize")!=[1380,720] or
            mask.get("transform")!=[3,0,0,3,0,0] or
            mask.get("drawDataCount")!=1):
        blocked("MAIN_MASK_STRUCTURE_"+sid)
    canvas_raw,main_sha=v2.read_png_data_url(
        main.pop("originalCanvasPngDataUrl"),folder/(sid+"_REAL_MAIN_CANVAS.png"))
    mask_raw,mask_sha=v2.read_png_data_url(
        mask.pop("originalCanvasPngDataUrl"),folder/(sid+"_REAL_MASK_CANVAS.png"))
    if canvas_raw.shape!=(732,1392,4) or mask_raw.shape!=(720,1380,4):
        blocked("CANVAS_PIXEL_SHAPE_"+sid)
    aligned,mapping=v2.source_stage_align(canvas_raw,main["node"],main["transform"])
    native,webgl_meta=p4d3.read_webgl_result(stage["native"],folder,sid+"_REAL_WEBGL")
    if (native.shape!=p4d3.NATIVE_SHAPE or
            webgl_meta.get("schema")!="ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
            webgl_meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer" or
            webgl_meta.get("strokeCount")!=len(case["runtime_strokes"])):
        blocked("NOT_NATIVE_EGRET_"+sid)
    v2.write_json(folder/"GL_PROVENANCE.json",{
        "mainTypedCanvasUploadCount":response["mainCanvasTypedUploadCount"],
        "calls":response["glUploads"],"pixelStoreCalls":response["glPixelStoreEvents"],
        "main":main,"mask":mask,
        "main_sha256":main_sha,"mask_sha256":mask_sha,
        "main_to_webgl_mapping":mapping,
        "webgl_renderer":webgl_meta})
    Image.fromarray(aligned,mode="RGBA").save(folder/(sid+"_ALIGNED_MAIN_RGBA.png"))
    diff=stage_diff(aligned,native)
    v2.write_json(folder/"D1_ALL_CHANNELS.json",diff)
    frames[case["variant"]]={"canvas":p4d3.roi(aligned,s3.CX,s3.CY).copy(),
                              "webgl":p4d3.roi(native,s3.CX,s3.CY).copy()}
    return {"sample_id":sid,"width":case["width"],"relation":case["relation"],
            "variant":case["variant"],"gl_main_typed_uploads":response["mainCanvasTypedUploadCount"],
            "stage_rgb":diff,"webgl_sha256":webgl_meta["source_sha256"]}


def run(workspace,engine,renderer,js_files,output):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    check_inputs(workspace,engine,renderer,js_files)
    spec=manifest()
    output.mkdir(parents=True)
    v2.write_json(output/"FROZEN_S3V2F_MANIFEST.json",spec)
    pairs,stats=[],[]
    native_frames={}
    repeats=[]
    with trace_session.pinned_native_egret_session(workspace) as driver:
        caps={k:driver.capabilities.get(k) for k in
              ("browserName","browserVersion","platformName")}
        if caps["browserName"]!="firefox" or not str(caps["browserVersion"]).startswith("159."):
            blocked("BROWSER_NOT_FIREFOX159")
        for source in js_files:
            driver.execute_script(source.read_text("utf8"))
        if driver.execute_script("return typeof window.AutoDrawBPRED_S3v2fCapture;")!="function":
            blocked("GL_SOURCE_ENTRYPOINT_UNAVAILABLE")
        blank,meta=p4d3.read_webgl_result(
            driver.execute_script(p4d3.CMD,[]),output,"S3V2F_REAL_EGRET_BLANK")
        if (meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or
                np.any(blank[:,:,3])):
            blocked("BLANK_NOT_ALPHA0")
        with (output/"PRIMARY_APPEND_ONLY.jsonl").open("x",encoding="utf8") as ledger:
            for width in WIDTHS:
                for relation in RELATIONS:
                    frames={}
                    for variant in VARIANTS:
                        scene=plans_for(width,relation)[variant]
                        row=read_original_scene(driver,scene,output,frames)
                        stats.append(row)
                        ledger.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                        ledger.flush()
                    native_frames[(width,relation)]=frames
                    pairs.append(ordered_metrics(width,relation,frames))
                    print("BPRED_S3V2F_NATIVE_PAIR",len(pairs),"/20",flush=True)
        for control in spec["controls"]:
            sid=control["sample_id"]
            scene=plans_for(control["width"],"CROSS_ROTATED")["A_THEN_B"]
            replay,rep_meta=p4d3.read_scene(
                driver,output/"replays",sid+"_REAL_EGRET",scene["runtime_strokes"])
            reference=native_frames[(control["width"],"CROSS_ROTATED")]["A_THEN_B"]["webgl"]
            exact=bool(np.array_equal(p4d3.roi(replay,s3.CX,s3.CY),reference))
            repeats.append({"sample_id":sid,"RGBA_ROI_exact":exact,
                            "source_sha256":rep_meta["source_png_sha256"]})
            if not exact:
                blocked("REPLAY_RGBA_DRIFT_"+sid)
    v2.write_json(output/"REPLAY_CONTROLS.json",repeats)
    v2.write_json(output/"D2_ORDERED_40.json",pairs)
    d1={mode:sum(s["stage_rgb"][mode]["rgb_mismatch_pixels"] for s in stats)
        for mode in ("Q0","QC","QH")}
    alpha_changed=sum(s["stage_rgb"]["Q0"]["alpha_mismatch_pixels"] for s in stats)
    count={mode:sum(int(v["canvas_to_webgl_C0"][mode]["frozen_H1_pass"])
                    for p in pairs for v in p["ordered_variants"].values())
           for mode in ("Q0","QC","QH")}
    original_webgl=sum(int(v["original_webgl_C0"]["frozen_H1_pass"])
                      for p in pairs for v in p["ordered_variants"].values())
    canvas=sum(int(v["canvas_native_C0"]["frozen_H1_pass"])
               for p in pairs for v in p["ordered_variants"].values())
    h1=d1["QH"]==0 and alpha_changed==0
    h2=count["QH"]>=30
    report={"experiment":EXPERIMENT,"E0_blob":E0_BLOB,
            "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
            "source_original_game_git_blob":p4d3.ENGINE_GIT_BLOB,
            "source_original_renderer_git_blob":p4d3.RENDERER_GIT_BLOB,
            "native_browser":caps,"true_native_primary":len(stats),
            "true_native_main_canvas_PNG":len(stats),
            "true_native_mask_canvas_PNG":len(stats),
            "true_native_final_webgl_PNG":len(stats)+len(repeats)+1,
            "true_native_replays":len(repeats),"blank_alpha0":True,
            "all_replays_RGBA_ROI_exact":all(r["RGBA_ROI_exact"] for r in repeats),
            "all_source_main_GL_upload_present":all(s["gl_main_typed_uploads"]>0 for s in stats),
            "D1_RGB_mismatch_by_mode":d1,"D1_native_alpha_mismatch":alpha_changed,
            "D2_C0_pass_count_by_mode_40":count,
            "D2_original_final_webgl_C0_pass_count_40":original_webgl,
            "D2_real_main_canvas_C0_pass_count_40":canvas,
            "H1_QH_new_native_exact_stage":"PASS" if h1 else "FAIL",
            "H2_QH_source_over_at_least_30_of_40":"PASS" if h2 else "FAIL",
            "scientific_S3_safe":False,"root_cause_proven":False,
            "previous_S3_native_C0_H1":"FAIL_UNCHANGED",
            "S0_BLIND_used":False,"production_promotion":False,
            "E4_live_game":"NOT_RUN","E5_independent":"NOT_RUN",
            "exact_game_CHALK":None,"protected_original_EF_quality":"FAIL_UNCHANGED"}
    report["members_sha256"]={
        p.relative_to(output).as_posix():s3.digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()}
    v2.write_json(output/"report.json",report)
    print("BPRED_S3V2F_NEW_NATIVE_D1",d1,"alpha_changed",alpha_changed,flush=True)
    print("BPRED_S3V2F_NEW_NATIVE_C0",count,"canvas",canvas,"final",original_webgl,flush=True)
    print("BPRED_S3V2F_SCIENCE",report["H1_QH_new_native_exact_stage"],
          report["H2_QH_source_over_at_least_30_of_40"],flush=True)
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for key in ("workspace","engine","renderer","trace-js","selector-js",
                "gl-observer-js","output"):
        ap.add_argument("--"+key,required=True,type=Path)
    a=ap.parse_args()
    run(a.workspace,a.engine,a.renderer,
        (a.trace_js,a.selector_js,a.gl_observer_js),a.output)
