#!/usr/bin/env python3
"""S3v2p: prospective original Egret main Canvas getImageData/PNG byte readbacks.

Observes true original Canvas2D strokes without replacing the original renderer.
Research E2/E3 only, no source-owner safety or production promotion.
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

import run_engine001_bpred_s3v2j_new_native_alpha0_owner_influence as j
import run_engine001_bpred_s3v2o_new_native_low_alpha_readback as o
import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_bpred_s3v2_native_canvas_stage as v2
import run_engine001_bpred_s3v2c_multicapture_trace as trace
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1

EXPERIMENT="ENGINE001_BPRED_S3V2P_TRUE_CANVAS_READBACK_VS_COMPOSITION_V1"
E0_FILE="ENGINE001_BPRED001_S3V2P_NATIVE_CANVAS_READBACK_VS_COMPOSITION_PREREG_2026-11-20.md"
E0_BLOB="44d6f3d72ed6c62f38054d11f050ee16cab50bc2"
JS_FILE="engine001_bpred_s3v2p_canvas_readback_observer.js"
SCHEMA="ENGINE001_BPRED_S3V2P_TRUE_MAIN_GETIMAGEDATA_ROI_V1"
ROI=(400,220,270,270)    # True original main Canvas NODE-LOCAL physical pixels.
NATIVE_ORIGIN=(-6,-6)      # Original Egret main GraphicsNode x=-2,y=-2 and scale=3.
WIDTHS=tuple(range(1,11))
RELATIONS=j.RELATIONS
VARIANTS=j.VARIANTS
ANGLES=(29,71,113,157,199,233,281,313,347,11)
COLORS=(
    (0xC82E59,0x167FAE),(0x3DBA91,0xDD7041),
    (0xAA4BC8,0x32946F),(0xF09135,0x4851C4),
    (0x28A6D9,0xBB4378),(0x94C135,0x315CA9),
    (0xE9569F,0x378F4C),(0x6940D2,0xD59D28),
    (0x43BDD0,0xB94B65),(0xD6B84C,0x4D6CB9)
)


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3V2P_"+reason)


def plans_for(width,relation):
    if type(width) is not int or width not in WIDTHS or relation not in RELATIONS:
        blocked("UNFROZEN_WIDTH_OR_RELATION")
    px=((9*width+3)%41+.375)/64
    py=((15*width+11)%43+.625)/64
    cx,cy=182+px,112+py
    a_deg=ANGLES[width-1]
    a=j.midpoint(cx,cy,a_deg,12+width%4)
    if relation=="CROSS_ROTATED":
        b=j.midpoint(cx+.34375,cy-.40625,(a_deg+109)%360,13+width%3)
    else:
        d=.77*width+.53
        rad=math.radians(a_deg)
        b=j.midpoint(cx-math.sin(rad)*d,cy+math.cos(rad)*d,
                     (a_deg+17)%360,13+width%3)
    if any(not (math.isfinite(p["x"]) and math.isfinite(p["y"])
                and 0<p["x"]<460 and 0<p["y"]<240)
           for stroke in (a,b) for p in stroke):
        blocked("INVALID_NATIVE_BOARD_GEOMETRY")
    ca,cb=COLORS[width-1]
    owners={
        "A":{"strokeId":"bpred-A","width":width,"colorIndex":1,
             "colorRgb":ca,"points":a},
        "B":{"strokeId":"bpred-B","width":width,"colorIndex":2,
             "colorRgb":cb,"points":b}}
    orders={"A_ONLY":("A",),"B_ONLY":("B",),
            "A_THEN_B":("A","B"),"B_THEN_A":("B","A")}
    out={}
    for variant,order in orders.items():
        source=[dict(owners[k]) for k in order]
        runtime=[{**x,"strokeId":f"icon-{i}"} for i,x in enumerate(source)]
        sid=f"BPRED-S3V2P-W{width:02d}-{relation}-{variant}"
        out[variant]={
            "sample_id":sid,"width":width,"relation":relation,
            "variant":variant,"angle_deg":a_deg,"phase_xy":[px,py],
            "source_colors":[ca,cb],"source_strokes":source,
            "runtime_strokes":runtime,
            "source_plan_sha256":s3.digest(s3.canonical(source)),
            "runtime_plan_sha256":s3.digest(s3.canonical(runtime))}
    return out


def manifest():
    scenes=[plans_for(w,r)[v] for w in WIDTHS for r in RELATIONS for v in VARIANTS]
    controls=[{
        "sample_id":f"BPRED-S3V2P-REPLAY-W{w:02d}-{r}",
        "parent_sample_id":plans_for(w,r)["A_THEN_B"]["sample_id"],
        "width":w,"relation":r} for w in WIDTHS for r in RELATIONS]
    if (len(scenes),len(set(x["sample_id"] for x in scenes)),
            len(controls),len(set(x["sample_id"] for x in controls)))!=(80,80,20,20):
        blocked("FROZEN_SCENE_CARDINALITY")
    return {
        "experiment":EXPERIMENT,"E0_blob":E0_BLOB,
        "source_original_game_blob":p4d3.ENGINE_GIT_BLOB,
        "source_original_renderer_blob":p4d3.RENDERER_GIT_BLOB,
        "roi_node_local_physical":list(ROI),"new_native_primary":80,
        "independent_uninstrumented_replays":20,"blank":1,
        "S0_BLIND_used":False,"scenes":scenes,"controls":controls}


def check_source(workspace,engine,renderer,scripts,observer):
    j.check_source(workspace,engine,renderer,scripts)
    o.verify_source(workspace,engine,renderer,scripts)
    e0=workspace/"AutoDraw_Stage20"/"docs"/E0_FILE
    if not e0.is_file() or p4b1.git_blob(e0.read_bytes())!=E0_BLOB:
        blocked("NEW_FROZEN_E0_MISSING_OR_CHANGED")
    if observer.name!=JS_FILE or not observer.is_file():
        blocked("NEW_READBACK_OBSERVER_MISSING")


def roi_png(item):
    # Node-local (400,220) means aligned BOARD (394,214), not same coordinates.
    rx,ry,w,h=ROI
    x,y=rx+NATIVE_ORIGIN[0],ry+NATIVE_ORIGIN[1]
    frame=item["canvas"]
    if frame.shape!=p4d3.NATIVE_SHAPE or frame.dtype!=np.uint8:
        blocked("ORIGINAL_ALIGNED_MAIN_SHAPE")
    return frame[y:y+h,x:x+w]


def bucket_label(alpha):
    if alpha==0:return "A0"
    if alpha<=15:return "A01_15"
    if alpha<=63:return "A16_63"
    if alpha<=127:return "A64_127"
    if alpha<=254:return "A128_254"
    return "A255"


def readback_scene(driver,scene,output):
    # Original verified S3v2j extractor captures ALL original PNGs and WebGL.
    item=j.extract_scene(driver,scene,output)
    raw=driver.execute_script(
        "var d=window.AutoDrawBPRED_S3v2pLastReadback;"
        "window.AutoDrawBPRED_S3v2pLastReadback=null;return d;")
    if (not isinstance(raw,dict) or raw.get("schema")!=SCHEMA
            or raw.get("originalTraceRestored") is not True
            or raw.get("sampleCount")!=len(item["steps"])
            or not isinstance(raw.get("samples"),list)
            or len(raw["samples"])!=len(item["steps"])):
        blocked("READBACK_WRAPPER_DID_NOT_OBSERVE_ORIGINAL_STROKES_"+scene["sample_id"])
    folder=output/"native"/scene["sample_id"]
    observations=[]
    last=None
    for step,entry in enumerate(raw["samples"],1):
        if (not isinstance(entry,dict) or entry.get("schema")!=SCHEMA
                or entry.get("sampleIndex")!=step
                or entry.get("canvasSize")!=[1392,732]
                or entry.get("roi")!={"x":ROI[0],"y":ROI[1],
                                     "width":ROI[2],"height":ROI[3]}
                or not isinstance(entry.get("rawRGBA_base64"),str)):
            blocked("TRUE_MAIN_RGBA_SOURCE_DRIFT_"+scene["sample_id"])
        try:
            bytes_=base64.b64decode(entry["rawRGBA_base64"],validate=True)
        except (ValueError,base64.binascii.Error) as exc:
            raise ValueError("BLOCKED_BPRED_S3V2P_BAD_NATIVE_BASE64") from exc
        if len(bytes_)!=ROI[2]*ROI[3]*4:
            blocked("GETIMAGEDATA_BYTE_COUNT_DRIFT_"+scene["sample_id"])
        native= np.frombuffer(bytes_,dtype=np.uint8).reshape(ROI[3],ROI[2],4)
        name=f"{scene['sample_id']}_REAL_GETIMAGEDATA_STEP_{step:02d}.rgba"
        path=folder/name
        if path.exists():
            blocked("RAW_READBACK_WOULD_OVERWRITE")
        path.write_bytes(bytes_)
        real_png=folder/(scene["sample_id"]+f"_REAL_STROKE_STEP_{step:02d}.png")
        with Image.open(real_png) as im:
            if im.size!=(1392,732) or im.mode!="RGBA":
                blocked("REAL_NATIVE_STEP_PNG_SHAPE_"+scene["sample_id"])
            png=np.asarray(im)[ROI[1]:ROI[1]+ROI[3],ROI[0]:ROI[0]+ROI[2]]
        if png.shape!=native.shape:
            blocked("PNG_GETIMAGEDATA_ROI_SHAPE_DRIFT")
        diff=native.astype(np.int16)-png.astype(np.int16)
        pixel_changed=np.any(diff!=0,axis=2)
        observations.append({
            "step":step,"sample_id":scene["sample_id"],
            "original_main_canvas_png":real_png.name,
            "native_raw_file":name,"native_raw_sha256":hashlib.sha256(bytes_).hexdigest(),
            "total_roi_pixels":ROI[2]*ROI[3],
            "PNG_vs_getImageData_different_RGBA_pixels":int(pixel_changed.sum()),
            "RGB_different_pixels":int(np.any(diff[:,:,:3]!=0,axis=2).sum()),
            "alpha_different_pixels":int((diff[:,:,3]!=0).sum()),
            "max_abs_byte_diff":int(np.abs(diff).max()),
            "mean_abs_byte_diff":float(np.abs(diff).mean())
        })
        last=native.copy()
    if last is None:
        blocked("READBACK_EMPTY")
    # Enforce true source ink contained in predetermined node-local ROI
    # on ALL steps, not only the last.
    for index in range(1,len(item["steps"])+1):
        aligned=item["steps"][index-1]
        rx,ry,w,h=ROI
        bx,by=rx+NATIVE_ORIGIN[0],ry+NATIVE_ORIGIN[1]
        outside=aligned[:,:,3].copy()
        outside[by:by+h,bx:bx+w]=0
        if np.any(outside):
            blocked("TRUE_NATIVE_STROKE_INK_OUTSIDE_FROZEN_ROI_"+scene["sample_id"])
    item["readback_last"]=last
    item["readback_meta"]=observations
    return item


def compare_readbacks(items,output):
    # ALL pixel-level readback-vs-PNG negatives, including alpha0.
    cases=[];errors=[];bins={}
    for item in items:
        scene=item["scene"]
        sid=scene["sample_id"]
        folder=output/"native"/sid
        for obs in item["readback_meta"]:
            step=obs["step"]
            file=folder/obs["native_raw_file"]
            rb=np.frombuffer(file.read_bytes(),dtype=np.uint8).reshape(ROI[3],ROI[2],4)
            with Image.open(folder/obs["original_main_canvas_png"]) as im:
                png=np.asarray(im)[ROI[1]:ROI[1]+ROI[3],ROI[0]:ROI[0]+ROI[2]]
            mask=np.any(png!=rb,axis=2)
            if int(mask.sum())!=obs["PNG_vs_getImageData_different_RGBA_pixels"]:
                blocked("READBACK_MISMATCH_COUNT_DRIFT")
            for y,x in np.argwhere(mask):
                x,y=int(x),int(y)
                a=int(png[y,x,3]);b=bucket_label(a)
                binobj=bins.setdefault(b,{"mismatches":0,"RGB_mismatches":0,
                                         "alpha_mismatches":0})
                binobj["mismatches"]+=1
                binobj["RGB_mismatches"]+=int(np.any(rb[y,x,:3]!=png[y,x,:3]))
                binobj["alpha_mismatches"]+=int(rb[y,x,3]!=png[y,x,3])
                errors.append({
                    "sample_id":sid,"step":step,"width":scene["width"],
                    "relation":scene["relation"],"variant":scene["variant"],
                    "node_local_physical_xy":[ROI[0]+x,ROI[1]+y],
                    "aligned_board_physical_xy":[ROI[0]+x-6,ROI[1]+y-6],
                    "PNG_RGBA":png[y,x].tolist(),
                    "getImageData_RGBA":rb[y,x].tolist(),
                    "getImageData_minus_PNG":[int(t) for t in
                                              rb[y,x].astype(np.int16)-png[y,x].astype(np.int16)]})
            cases.append(obs)
    if len(cases)!=sum(len(i["steps"]) for i in items):
        blocked("READBACK_STEP_CARDINALITY")
    v2.write_json(output/"EVERY_TRUE_MAIN_READBACK_VS_PNG_DIFFERENT_PIXEL.json",errors)
    v2.write_json(output/"ALL_ORIGINAL_READBACK_STROKE_STEPS.json",cases)
    v2.write_json(output/"READBACK_DIFFERENCE_ALPHA_STRATA.json",bins)
    return cases,errors,bins


def compare_owner_bytes(items,output,original_png_damage):
    index={(x["scene"]["width"],x["scene"]["relation"],x["scene"]["variant"]):x
           for x in items}
    records=[];events=[];classes={"BOTH":0,"PNG_ONLY":0,"GETIMAGE_ONLY":0}
    png_total=0;rb_total=0
    # Pixel-indexed by original **aligned** original board coordinates.
    for width in WIDTHS:
        for relation in RELATIONS:
            f={v:index[(width,relation,v)] for v in VARIANTS}
            for variant in ("A_THEN_B","B_THEN_A"):
                lo=f["A_ONLY"] if variant=="A_THEN_B" else f["B_ONLY"]
                top=f["B_ONLY"] if variant=="A_THEN_B" else f["A_ONLY"]
                actual=f[variant]
                pp,pt,pa=(roi_png(x) for x in (lo,top,actual))
                bp,bt,ba=(x["readback_last"] for x in (lo,top,actual))
                pzone=(pp[:,:,3]>0)&(pt[:,:,3]==0)
                bzone=(bp[:,:,3]>0)&(bt[:,:,3]==0)
                pdelta=pa.astype(np.int16)-pp.astype(np.int16)
                bdelta=ba.astype(np.int16)-bp.astype(np.int16)
                pchange=pzone&np.any(pdelta!=0,axis=2)
                bchange=bzone&np.any(bdelta!=0,axis=2)
                union=pchange|bchange
                png_total+=int(pchange.sum())
                rb_total+=int(bchange.sum())
                for y,x in np.argwhere(union):
                    x,y=int(x),int(y)
                    is_png=bool(pchange[y,x]); is_rb=bool(bchange[y,x])
                    label="BOTH" if is_png and is_rb else "PNG_ONLY" if is_png else "GETIMAGE_ONLY"
                    classes[label]+=1
                    events.append({
                        "sample_id":actual["scene"]["sample_id"],"width":width,
                        "relation":relation,"variant":variant,
                        "native_aligned_board_xy":[ROI[0]+x-6,ROI[1]+y-6],
                        "node_local_xy":[ROI[0]+x,ROI[1]+y],
                        "type":label,"PNG_risk":is_png,"getImageData_risk":is_rb,
                        "PNG_lower_RGBA":pp[y,x].tolist(),"PNG_top_RGBA":pt[y,x].tolist(),
                        "PNG_ordered_RGBA":pa[y,x].tolist(),
                        "PNG_delta_RGBA":pdelta[y,x].tolist(),
                        "getImageData_lower_RGBA":bp[y,x].tolist(),
                        "getImageData_top_RGBA":bt[y,x].tolist(),
                        "getImageData_ordered_RGBA":ba[y,x].tolist(),
                        "getImageData_delta_RGBA":bdelta[y,x].tolist()})
                records.append({
                    "sample_id":actual["scene"]["sample_id"],
                    "width":width,"relation":relation,"variant":variant,
                    "PNG_lower_visible_top_alpha0_changed":int(pchange.sum()),
                    "getImageData_lower_visible_top_alpha0_changed":int(bchange.sum()),
                    "BOTH":int((pchange&bchange).sum()),
                    "PNG_ONLY":int((pchange&~bchange).sum()),
                    "GETIMAGE_ONLY":int((bchange&~pchange).sum())})
    old={ (x["sample_id"],*x["native_physical_xy"]) for x in original_png_damage }
    new={ (x["sample_id"],*x["native_aligned_board_xy"]) for x in events if x["PNG_risk"] }
    if old!=new or len(records)!=40 or len(old)!=png_total:
        blocked("ORIGINAL_S3V2J_PNG_OWNER_HARM_MUST_BE_UNCHANGED")
    v2.write_json(output/"ALL_40_NEW_ORDERED_TWO_READBACK_OWNER_EFFECTS.json",records)
    v2.write_json(output/"EVERY_TWO_READBACK_FOREIGN_OWNER_PIXEL.json",events)
    return {"PNG_changed":png_total,"getImageData_changed":rb_total,
            "classes":classes,"total_union":len(events)},records,events


def run(workspace,engine,renderer,scripts,observer,output):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    check_source(workspace,engine,renderer,scripts,observer)
    spec=manifest()
    output.mkdir(parents=True,exist_ok=False)
    v2.write_json(output/"FROZEN_S3V2P_MANIFEST.json",spec)
    items=[]
    with trace.pinned_native_egret_session(workspace) as driver:
        caps={k:driver.capabilities.get(k)
              for k in ("browserName","browserVersion","platformName")}
        if caps["browserName"]!="firefox" or not str(caps["browserVersion"]).startswith("159."):
            blocked("PINNED_FIREFOX159_NOT_USED")
        for script in scripts:
            driver.execute_script(script.read_text("utf8"))
        driver.execute_script(observer.read_text("utf8"))
        if driver.execute_script("return window.AutoDrawBPRED_S3v2pReadbackWrapperInstalled;") is not True:
            blocked("NEW_NATIVE_READBACK_OBSERVER_NOT_INSTALLED")
        blank,bmeta=p4d3.read_webgl_result(
            driver.execute_script(p4d3.CMD,[]),output,"S3V2P_REAL_EGRET_BLANK")
        if bmeta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or np.any(blank[:,:,3]):
            blocked("REAL_ORIGINAL_EGRET_BLANK_ALPHA_NOT_ZERO")
        with (output/"NATIVE_APPEND_ONLY.jsonl").open("x",encoding="utf8") as ledger:
            for scene in spec["scenes"]:
                try:
                    item=readback_scene(driver,scene,output)
                except Exception as exc:
                    v2.write_json(output/"BLOCKED_OR_FAILED_SCENE.json",{
                        "sample_id":scene["sample_id"],"prior_complete":len(items),
                        "error_type":type(exc).__name__,"error":str(exc)})
                    raise
                items.append(item)
                ledger.write(json.dumps({
                    "sample_id":scene["sample_id"],"source_plan_sha256":scene["source_plan_sha256"],
                    "runtime_plan_sha256":scene["runtime_plan_sha256"],
                    "original_main_stroke_calls":len(item["steps"]),
                    "getImageData_samples":len(item["readback_meta"])},
                    ensure_ascii=False,allow_nan=False)+"\n")
                ledger.flush()
                print("S3V2P_TRUE_NATIVE_READBACK",len(items),"/80",flush=True)
        (output/"replays").mkdir(exist_ok=False)
        replays=[]
        for control in spec["controls"]:
            parent=plans_for(control["width"],control["relation"])["A_THEN_B"]
            frame,meta=p4d3.read_scene(driver,output/"replays",
                control["sample_id"]+"_REAL_EGRET",parent["runtime_strokes"])
            expected=next(x["webgl"] for x in items if x["scene"]["sample_id"]==parent["sample_id"])
            equal=bool(np.array_equal(p4d3.roi(frame,s3.CX,s3.CY),
                                      p4d3.roi(expected,s3.CX,s3.CY)))
            replays.append({"sample_id":control["sample_id"],"parent":parent["sample_id"],
                            "uninstrumented_original_webgl_ROI_RGBA_exact":equal,
                            "sha256":meta["source_png_sha256"]})
            if not equal:
                v2.write_json(output/"BLOCKED_REPLAY_UNINSTRUMENTED.json",replays)
                blocked("READBACK_INSTRUMENTATION_ALTERS_REAL_EGRET_"+control["sample_id"])
    v2.write_json(output/"REPLAY_CONTROLS.json",replays)
    cases,errors,bins=compare_readbacks(items,output)
    original_rows,original_damage=j.calculate_pairs(items,output)
    owner,owner_rows,owner_events=compare_owner_bytes(items,output,original_damage)
    counts,totals,all_misses,source_bins=o.analyze_isolated(items,output)
    first=sum(r["first_event_vs_same_run_isolated_owner"]["RGBA_different_physical_pixels"]
              for r in original_rows)
    last=sum(x["last_difference"]["RGBA_different_physical_pixels"] for x in items)
    qh_rgb=sum(x["stage"]["QH"]["rgb_mismatch_pixels"] for x in items)
    qh_alpha=sum(x["stage"]["QH"]["alpha_mismatch_pixels"] for x in items)
    report={
        "experiment":EXPERIMENT,"E0_blob":E0_BLOB,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        "browser":caps,"original_game_engine_blob":p4d3.ENGINE_GIT_BLOB,
        "original_renderer_blob":p4d3.RENDERER_GIT_BLOB,
        "new_native_primary":len(items),"native_main_canvas_PNG":80,
        "native_mask_canvas_PNG":80,"native_final_webgl_PNG":101,
        "native_main_stroke_steps":sum(len(x["steps"]) for x in items),
        "direct_getImageData_snapshots":len(cases),
        "native_uninstrumented_replays":len(replays),
        "native_uninstrumented_replays_all_ROI_exact":all(x["uninstrumented_original_webgl_ROI_RGBA_exact"] for x in replays),
        "blank_alpha0":True,"readback_roi_node_local_physical":list(ROI),
        "H0_provenance":"PASS",
        "H1_PNG_vs_getImageData":"SAME_OBSERVED_READBACK" if not errors else "DIFFERENT_OBSERVED_READBACK",
        "H1_different_pixel_occurrences":len(errors),
        "H1_source_alpha_bins":bins,
        "H2_original_ordered_owner_PNG_changed":owner["PNG_changed"],
        "H2_original_ordered_owner_getImageData_changed":owner["getImageData_changed"],
        "H2_owner_risk_classification":owner["classes"],
        "H2_source_owner_foreign_safe":"FAIL" if owner["total_union"] else "NO_EFFECT_IN_TEST_ONLY",
        "H3_first_actual_owner_40":"PASS" if first==0 else "FAIL",
        "H3_last_true_main_80":"PASS" if last==0 else "FAIL",
        "H3_original_C0_canvas_pass40":sum(bool(x["original_fixed_C0_canvas"]["frozen_H1_pass"]) for x in original_rows),
        "H3_original_C0_QH_webgl_pass40":sum(bool(x["original_fixed_C0_QH_webgl"]["frozen_H1_pass"]) for x in original_rows),
        "H3_QH_stage_RGB_misses":qh_rgb,
        "H3_QH_stage_alpha_misses":qh_alpha,
        "H4_new_source_counts":counts,
        "H4_G3_source_misses":totals["G3"]["misses"],
        "H4_G3_informative_A16_254":totals["G3"]["informative"],
        "H4_G3_fraction":totals["G3"]["informative"]/counts["qualified"],
        "H4_G3_coverage":"PASS_SOURCE_ONLY" if totals["G3"]["misses"]==0 and counts["opaque_miss"]==0 else "FAIL",
        "H4_G3_usefulness":"PASS" if totals["G3"]["informative"]/counts["qualified"]>=.90 else "FAIL",
        "H4_single_mode_selection":"FORBIDDEN",
        "source_baseline_S3v2n_D2":"FAIL_6851_OF_7753",
        "source_baseline_S3v2o_D2":"FAIL_7602_OF_8614",
        "source_baseline_S3v2o_alpha0_owner_harm":17,
        "original_EF_protected_quality":"FAIL_UNCHANGED",
        "source_owner_safety":"NOT_PROMOTED",
        "S0_BLIND_used":False,"E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_game_CHALK":None,"production_promotion":False,
        "source_RGB_miss_report_records":all_misses,
        "owner_risk_union":owner["total_union"]
    }
    report["members_sha256"]={
        p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    v2.write_json(output/"report.json",report)
    print("S3V2P_OBSERVED_READBACK",report["H1_PNG_vs_getImageData"],
          len(errors),"/",len(cases),"snapshots",flush=True)
    print("S3V2P_OWNER_RISK",report["H2_original_ordered_owner_PNG_changed"],
          report["H2_original_ordered_owner_getImageData_changed"],
          owner["classes"],flush=True)
    print("S3V2P_G3_SOURCE",report["H4_G3_coverage"],report["H4_G3_usefulness"],
          totals["G3"]["informative"],"/",counts["qualified"],flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for flag in ("workspace","engine","renderer","trace-js","selector-js","stroke-js","readback-js","output"):
        parser.add_argument("--"+flag,required=True,type=Path)
    args=parser.parse_args()
    run(args.workspace,args.engine,args.renderer,
        (args.trace_js,args.selector_js,args.stroke_js),args.readback_js,args.output)
