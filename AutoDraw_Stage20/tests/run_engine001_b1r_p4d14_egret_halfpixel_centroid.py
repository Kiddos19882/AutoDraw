#!/usr/bin/env python3
"""P4D14: source-derived Egret 5.4.1 center model versus actual native BoardPane.

The centroid model is NOT a pixel-exact substitute for Canvas2D/WebGL.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import statistics
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D14_EGRET_GRAPHICS_HALFPIXEL_CENTROID_MODEL_V1"
PREREG="ENGINE001_B1R_P4D14_EGRET_GRAPHICS_HALFPIXEL_CENTROID_PREREG_2026-11-19.md"
PARENT_BLOB="3437a9326b381d9c94d6ade80059d40adf233d09"
ANGLES=(0,15,30,45,60,90,135,165)
LENGTHS=(4,34)
WIDTHS=tuple(range(1,11))
EXPECTED_CASES=160
EXPECTED_NATIVE_SCENES=171

def egret_graphics_halfpixel(width:int)->float:
    """Confirmed by Egret 5.4.1 CanvasRenderer.renderGraphics source."""
    if type(width) is not int or width not in WIDTHS:
        raise ValueError("BLOCKED_P4D14_BRUSH_WIDTH")
    return .5 if width in (1,3) else 0.

def model_center(stroke:dict,source_correction:bool)->tuple[float,float]:
    pts=stroke.get("points",())
    width=stroke.get("width")
    if len(pts)!=2 or type(width) is not int or width not in WIDTHS:
        raise ValueError("BLOCKED_P4D14_STROKE_GEOMETRY")
    try:
        x=(float(pts[0]["x"])+float(pts[1]["x"]))/2
        y=(float(pts[0]["y"])+float(pts[1]["y"]))/2
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError("BLOCKED_P4D14_POINT_COORDINATES") from exc
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError("BLOCKED_P4D14_NONFINITE")
    shift=egret_graphics_halfpixel(width) if source_correction else 0.
    return x+shift,y+shift

def native_alpha_centroid(roi:np.ndarray,cx:int,cy:int)->tuple[float,float]:
    n=2*p4d3.HALF*p4d3.SCALE
    if (roi.shape!=(n,n,4) or roi.dtype!=np.uint8 or
        type(cx) is not int or type(cy) is not int):
        raise ValueError("BLOCKED_P4D14_NATIVE_ROI")
    alpha=roi[:,:,3].astype(np.float64)
    total=float(alpha.sum())
    if total<=0 or not math.isfinite(total):
        raise ValueError("BLOCKED_P4D14_EMPTY_NATIVE_ROI")
    yy,xx=np.indices(alpha.shape)
    x=cx-p4d3.HALF+float(np.sum(alpha*(xx+.5)))/total/p4d3.SCALE
    y=cy-p4d3.HALF+float(np.sum(alpha*(yy+.5)))/total/p4d3.SCALE
    return x,y

def euclidean(a:tuple,b:tuple)->float:
    if not all(math.isfinite(v) for v in a+b):
        raise ValueError("BLOCKED_P4D14_NONFINITE_DISTANCE")
    return float(math.hypot(a[0]-b[0],a[1]-b[1]))

def summarize(values:list[float])->dict:
    if not values or any(not math.isfinite(x) for x in values):
        raise ValueError("BLOCKED_P4D14_EMPTY_METRIC")
    return {"count":len(values),"mean":float(statistics.fmean(values)),
            "median":float(statistics.median(values)),
            "p95":float(np.quantile(values,.95)),
            "maximum":float(max(values))}

def measure_case(driver,output:Path,width:int,angle:int,length:int)->tuple[dict,bool]:
    key=p4d3.case_id(width,angle,length)
    folder=output/"native"/f"L{length:02d}"/f"W{width:02d}"
    folder.mkdir(parents=True,exist_ok=True)
    plan=p4d3.build_primary(width,angle,length)
    (folder/(key+"_PLAN.json")).write_text(
        json.dumps(plan,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    rgba,meta=p4d3.read_scene(driver,folder,key+"_REAL_EGRET",plan)
    cells=[]
    for i,(cx,cy) in enumerate(p4d3.CENTERS[:10]):
        native=p4d3.roi(rgba,cx,cy)
        measured=native_alpha_centroid(native,cx,cy)
        m0=model_center(plan[i],False)
        m1=model_center(plan[i],True)
        cells.append({
            "center_grid":[cx,cy],
            "native_centroid_xy":[*measured],
            "naive_predicted_xy":[*m0],
            "egret_predicted_xy":[*m1],
            "source_halfpixel_offset":egret_graphics_halfpixel(width),
            "naive_error_logical":euclidean(measured,m0),
            "egret_error_logical":euclidean(measured,m1),
            "native_alpha_sum":int(native[:,:,3].astype(np.uint64).sum()),
        })
    native_score=p4d3.scores(rgba)
    if len(cells)!=10 or any(c["native_alpha_sum"]<=0 for c in cells):
        raise ValueError("BLOCKED_P4D14_NATIVE_CELLS")
    repeat=False
    if angle==0 and length==4:
        second,meta2=p4d3.read_scene(driver,folder,key+"_REPLAY",plan)
        repeat=bool(np.array_equal(rgba,second))
        if not repeat or meta2["source_png_sha256"]!=meta["source_png_sha256"]:
            raise ValueError("BLOCKED_P4D14_REPLAY_NONDETERMINISM")
    d=native_score["isolated10_mismatch_each"]
    row={"case_id":key,"width":width,"angle_deg":angle,"length_logical":length,
         "cells":cells,"native_png_sha256":meta["source_png_sha256"],
         "native_renderer":meta["renderer"],
         "translated_all10_rgba_identical":native_score["isolated10_all_exact_rgba"],
         "translated_rgba_different_pixels":native_score["isolated10_mismatch_pixels_total"],
         "translated_alpha24_xor":sum(x["alpha24_xor_pixels"] for x in d),
         "translated_alpha1_xor":sum(x["alpha1_xor_pixels"] for x in d),
         "exact_repeat":repeat}
    return row,repeat

def make_plot(per_width:dict,output:Path)->None:
    img=Image.new("RGB",(880,420),"white"); d=ImageDraw.Draw(img)
    d.text((20,15),"P4D14 REAL EGRET alpha-weighted centroid: naive vs +0.5 width 1/3",fill="#222222")
    d.text((20,38),"Dark=naive  Green=Egret source model; horizontal axis: logical pixel error",fill="#222222")
    for width in WIDTHS:
        y=73+(width-1)*31
        x=152
        v=per_width[str(width)]
        a=v["naive_error_logical"]["mean"]
        b=v["source_error_logical"]["mean"]
        d.text((22,y+4),f"BRUSH {width}",fill="#151515")
        d.rectangle((x,y+3,x+min(575,565*a),y+12),fill="#314968")
        d.rectangle((x,y+15,x+min(575,565*b),y+24),fill="#32925c")
        d.text((735,y+5),f"{a:.4f}/{b:.4f}",fill="#151515")
    d.text((22,401),"Centroid only; this does NOT predict each native RGBA pixel.",fill="#222222")
    img.save(output/"P4D14_NATIVE_CENTROID_MODEL_ERROR.png")

def run(workspace:Path,engine_js:Path,renderer:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D14_OUTPUT_EXISTS")
    if (p4b1.git_blob(renderer.read_bytes())!=p4d3.RENDERER_GIT_BLOB or
        p4b1.git_blob(engine_js.read_bytes())!=p4d3.ENGINE_GIT_BLOB or
        p4b1.git_blob(Path(p4d3.__file__).read_bytes())!=PARENT_BLOB):
        raise ValueError("BLOCKED_P4D14_PARENT_PIN_DRIFT")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
        raise ValueError("BLOCKED_P4D14_NOT_PREREG")
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D14 model M0: midpoint. Model M1: midpoint + (0.5,0.5) ONLY for "
        "widths1/3 per real Egret5.4.1 CanvasRenderer. 160 new real native "
        "P4D3-shape BoardPane scenes,10 exact replays+blank. Pixel-level RGBA "
        "translation mismatches tracked, not assumed solved. No production/E4/CHALK.\n","utf8")
    rows=[];repeat_count=0
    with p4b7.native_egret_session(workspace) as driver:
        driver.set_script_timeout(180)
        response=driver.execute_script(p4d3.CMD,[])
        blank,meta=p4d3.read_webgl_result(response,output,"REAL_EGRET_BLANK")
        if (blank.shape!=p4d3.NATIVE_SHAPE or
            meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or
            meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer" or
            np.any(blank[:,:,3])):
            raise ValueError("BLOCKED_P4D14_NATIVE_BLANK")
        with (output/"NATIVE_CASES_APPEND_ONLY.jsonl").open("a",encoding="utf8") as ledger:
            for length in LENGTHS:
                for width in WIDTHS:
                    for angle in ANGLES:
                        case,repeat=measure_case(driver,output,width,angle,length)
                        rows.append(case);repeat_count+=int(repeat)
                        ledger.write(json.dumps(case,ensure_ascii=False,allow_nan=False)+"\n")
                        ledger.flush()
                    print("P4D14_EGRET",width,length,"native cases",len(rows),
                          "replays",repeat_count,flush=True)
    if len(rows)!=EXPECTED_CASES or repeat_count!=10:
        raise ValueError("BLOCKED_P4D14_NOT_COMPLETE_NATIVE")
    groups={}
    for w in WIDTHS:
        cells=[c for r in rows if r["width"]==w for c in r["cells"]]
        d0=[c["naive_error_logical"] for c in cells]
        d1=[c["egret_error_logical"] for c in cells]
        ox=[c["native_centroid_xy"][0]-c["naive_predicted_xy"][0] for c in cells]
        oy=[c["native_centroid_xy"][1]-c["naive_predicted_xy"][1] for c in cells]
        groups[str(w)]={"samples":len(cells),"half_pixel":egret_graphics_halfpixel(w),
             "naive_error_logical":summarize(d0),
             "source_error_logical":summarize(d1),
             "measured_native_dx_mean":float(statistics.fmean(ox)),
             "measured_native_dy_mean":float(statistics.fmean(oy))}
    odd=[c for r in rows if r["width"] in (1,3) for c in r["cells"]]
    other=[c for r in rows if r["width"] not in (1,3) for c in r["cells"]]
    odd0=summarize([c["naive_error_logical"] for c in odd])
    odd1=summarize([c["egret_error_logical"] for c in odd])
    other0=summarize([c["naive_error_logical"] for c in other])
    other1=summarize([c["egret_error_logical"] for c in other])
    equal=sum(bool(r["translated_all10_rgba_identical"]) for r in rows)
    make_plot(groups,output)
    report={
        "experiment":EXPERIMENT,
        "technical_result":"P4D14_TRUE_EGRET_MATH_CENTROID_160_NATIVE_SCENES",
        "renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
        "renderer_blob":p4d3.RENDERER_GIT_BLOB,
        "game_bundle_blob":p4d3.ENGINE_GIT_BLOB,
        "P4D3_unchanged_git_blob":PARENT_BLOB,
        "native_blank_alpha0":True,
        "case_angles_deg":list(ANGLES),"case_lengths_logical":list(LENGTHS),
        "case_widths":list(WIDTHS),
        "cases_native":len(rows),"exact_native_replays":repeat_count,
        "native_png_scenes":len(rows)+repeat_count+1,
        "native_relative_alpha_centroid_measured_samples":len(rows)*10,
        "native_translated_all10_exact_rgba_scenes":equal,
        "native_translated_not_all_exact_rgba_scenes":len(rows)-equal,
        "native_translated_alpha24_xor_pixels":sum(r["translated_alpha24_xor"] for r in rows),
        "native_translated_alpha1_xor_pixels":sum(r["translated_alpha1_xor"] for r in rows),
        "model0_no_shift_widths_1_3":odd0,
        "model1_source_shift_widths_1_3":odd1,
        "model0_no_shift_other_widths":other0,
        "model1_source_shift_other_widths":other1,
        "H1_shift_w1_w3_reduces_centroid_mean_error":odd1["mean"]<odd0["mean"],
        "H2_other_widths_same_model":other0==other1,
        "H3_translation_rgba_invariance_not_complete":equal<len(rows),
        "per_width":groups,
        "history_P4D3_480_replays_exact":480,
        "history_P4D3_480_translated_exact":292,
        "history_P4D4_480_binary_grid_translated_exact":256,
        "scientific_scope":"centroid only; native RGBA remains authoritative",
        "full_pixel_exact_brush_model":"NOT_PROVEN",
        "E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None,"production_promotion":False,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID")}
    report["members_sha256"]={
        str(path.relative_to(output)).replace("\\","/"):digest(path.read_bytes())
        for path in sorted(output.rglob("*")) if path.is_file()
    }
    (output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,allow_nan=False,indent=2)+"\n","utf8")
    print("P4D14_NATIVE_MODEL_RESULT",odd0["mean"],odd1["mean"],
          "translated_exact",equal,"/160","H1 H2 H3",
          report["H1_shift_w1_w3_reduces_centroid_mean_error"],
          report["H2_other_widths_same_model"],
          report["H3_translation_rgba_invariance_not_complete"],flush=True)
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--engine-js",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    run(args.workspace,args.engine_js,args.renderer,args.output)
