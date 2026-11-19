#!/usr/bin/env python3
"""P4D15: compare GENUINE Egret CanvasRenderer intermediate to final WebGL.
Source and final PNGs are both from the unchanged game renderer, not a model.
Research only. No Stage6/production/CHALK/acceptance-threshold changes.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D15_CANVAS_TEXTURE_VS_WEBGL_TRANSLATION_V1"
PREREG="ENGINE001_B1R_P4D15_CANVAS_TEXTURE_TRANSLATION_PREREG_2026-11-19.md"
PARENT_SHA="3437a9326b381d9c94d6ade80059d40adf233d09"
ANGLES=(0,45,135)
LENGTHS=(4,34)
WIDTHS=(1,2,3,4,10)
CASE_COUNT=30
REPEATS=(1,3,10)
TOTAL_NATIVE=34
TOTAL_SOURCE=33
NATIVE_SHAPE=(720,1380,4)
SCALE=3
SIDE=162


def read_source_capture(payload:dict,folder:Path,stem:str)->tuple[np.ndarray,dict]:
    if payload.get("schema")!="ENGINE001_B1R_P4D15_TRUE_NATIVE_CANVAS_STAGE_PAIR" or (
        payload.get("underlyingCanvasRendererRestored") is not True):
        raise ValueError("BLOCKED_P4D15_INJECTION_NOT_RESTORED")
    src=payload["intermediate"]
    data=src.pop("originalCanvasPngDataUrl")
    if not isinstance(data,str) or not data.startswith("data:image/png;base64,"):
        raise ValueError("BLOCKED_P4D15_INVALID_INTERMEDIATE_DATA")
    raw=base64.b64decode(data.partition(",")[2],validate=True)
    (folder/(stem+"_CANVAS_SOURCE.png")).write_bytes(raw)
    with Image.open(BytesIO(raw)) as im:
        if im.mode!="RGBA":
            raise ValueError("BLOCKED_P4D15_SOURCE_NOT_RGBA")
        rgba=np.asarray(im).copy()
    node=src["node"]
    if (rgba.ndim!=3 or rgba.shape[2]!=4 or rgba.dtype!=np.uint8 or
        rgba.shape!=(src["canvasHeight"],src["canvasWidth"],4) or
        not all(np.isfinite(float(node[k])) for k in ("x","y","width","height")) or
        src["drawDataCount"]<21 or
        rgba.shape[0] not in range(1,2001) or rgba.shape[1] not in range(1,2001)):
        raise ValueError("BLOCKED_P4D15_SOURCE_METADATA_DRIFT")
    return rgba,{"source_png_sha256":digest(raw),"drawDataCount":src["drawDataCount"],
                 "node":node,"canvasWidth":src["canvasWidth"],
                 "canvasHeight":src["canvasHeight"],"transform":src["transform"]}


def crop_source(rgba:np.ndarray,node:dict,cx:int,cy:int)->np.ndarray:
    """10 source-canvas crops with the frozen integer 3x cell translations."""
    if rgba.ndim!=3 or rgba.shape[2]!=4 or rgba.dtype!=np.uint8:
        raise ValueError("BLOCKED_P4D15_BAD_SOURCE_RGBA")
    left=int(round(SCALE*(cx-p4d3.HALF-node["x"])))
    top=int(round(SCALE*(cy-p4d3.HALF-node["y"])))
    # The genuine Canvas texture contains only the GraphicsNode bounds.
    # The 54-logical-unit measurement ROI may extend outside that texture;
    # the missing region is transparent, not an invalid native source.
    sx0=max(0,left)
    sy0=max(0,top)
    sx1=min(rgba.shape[1],left+SIDE)
    sy1=min(rgba.shape[0],top+SIDE)
    if sx1<=sx0 or sy1<=sy0:
        raise ValueError("BLOCKED_P4D15_SOURCE_CROP_NO_TEXTURE_OVERLAP")
    padded=np.zeros((SIDE,SIDE,4),np.uint8)
    padded[sy0-top:sy1-top,sx0-left:sx1-left,:]=rgba[sy0:sy1,sx0:sx1,:]
    return padded


def compare_copies(roi_list:list[np.ndarray])->dict:
    if len(roi_list)!=10 or any(
        x.shape!=(SIDE,SIDE,4) or x.dtype!=np.uint8 for x in roi_list):
        raise ValueError("BLOCKED_P4D15_EXPECTED_TEN_NATIVE_RGBA_CELLS")
    ref=roi_list[0]
    differences=[p4d3.difference(ref,other) for other in roi_list[1:]]
    return {
        "isolated10_exact_rgba":all(v["rgba_differing_pixels"]==0 for v in differences),
        "translated_rgba_different_pixels_total":
            sum(v["rgba_differing_pixels"] for v in differences),
        "translated_alpha24_xor_pixels_total":
            sum(v["alpha24_xor_pixels"] for v in differences),
        "translated_alpha1_xor_pixels_total":
            sum(v["alpha1_xor_pixels"] for v in differences),
        "nine_individual_mismatches":differences
    }


def classify(source:dict,final:dict)->str:
    a=source["isolated10_exact_rgba"];b=final["isolated10_exact_rgba"]
    return ("both_exact" if a and b else
            "canvas_exact_webgl_changed" if a and not b else
            "canvas_changed_webgl_exact" if not a and b else
            "both_changed")


def render_case(driver,source_js:str,folder:Path,
                width:int,angle:int,length:int,extra:str="")->tuple[dict,np.ndarray,np.ndarray]:
    plan=p4d3.build_primary(width,angle,length)
    case=p4d3.case_id(width,angle,length)+extra
    (folder/(case+"_PLAN.json")).write_text(
        json.dumps(plan,ensure_ascii=False,allow_nan=False)+"\n","utf8")
    response=driver.execute_script(
        "return window.AutoDrawP4D15Capture(arguments[0]);",plan)
    if response["schema"]!="ENGINE001_B1R_P4D15_TRUE_NATIVE_CANVAS_STAGE_PAIR":
        raise ValueError("BLOCKED_P4D15_CAPTURE_SCHEMA")
    source,metadata=read_source_capture(response,folder,case)
    real,meta=p4d3.read_webgl_result(response["native"],folder,case+"_REAL_EGRET")
    if (real.shape!=NATIVE_SHAPE or
        meta.get("schema")!="ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
        meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer" or
        meta.get("strokeCount")!=21):
        raise ValueError("BLOCKED_P4D15_NOT_REAL_NATIVE")
    owners=p4d3.CENTERS[:10]
    canvas_cells=[crop_source(source,metadata["node"],x,y) for x,y in owners]
    webgl_cells=[p4d3.roi(real,x,y) for x,y in owners]
    check_source=compare_copies(canvas_cells)
    check_gl=compare_copies(webgl_cells)
    control=p4d3.scores(real)
    if control["isolated10_all_exact_rgba"]!=check_gl["isolated10_exact_rgba"] or (
        control["isolated10_mismatch_pixels_total"] !=
        check_gl["translated_rgba_different_pixels_total"]):
        raise ValueError("BLOCKED_P4D15_NATIVE_PARENT_SCORING_DISAGREEMENT")
    result={
        "case":case,"width":width,"angle_deg":angle,"length_logical":length,
        "source_image_sha256":metadata["source_png_sha256"],
        "native_image_sha256":meta["source_png_sha256"],
        "source_native_graphics_bounds":metadata["node"],
        "source_texture_dimensions":[metadata["canvasWidth"],metadata["canvasHeight"]],
        "source_texture_transform":metadata["transform"],
        "canvas_intermediate":check_source,
        "native_webgl_final":check_gl,
        "classification":classify(check_source,check_gl)
    }
    return result,source,real


def panel_from_case(source:np.ndarray,node:dict,real:np.ndarray,out:Path)->None:
    picks=(p4d3.CENTERS[0],p4d3.CENTERS[1])
    parts=[]
    for xy in picks:
        parts.append(crop_source(source,node,*xy))
        parts.append(p4d3.roi(real,*xy))
    image=Image.new("RGB",(SIDE*4, SIDE+24),"white")
    draw=ImageDraw.Draw(image)
    for i,p in enumerate(parts):
        image.paste(Image.fromarray(p,"RGBA").convert("RGB"),(i*SIDE,24))
        draw.text((i*SIDE+2,3),
                  ("Canvas texture" if i%2==0 else "Final Egret WebGL")+
                  (" cell 1" if i<2 else " cell 2"),
                  fill="black")
    image.save(out)


def run(workspace:Path,engine_js:Path,renderer:Path,
        js_patch:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D15_EVIDENCE_EXISTS")
    if (p4b1.git_blob(renderer.read_bytes())!=p4d3.RENDERER_GIT_BLOB or
        p4b1.git_blob(engine_js.read_bytes())!=p4d3.ENGINE_GIT_BLOB or
        p4b1.git_blob(Path(p4d3.__file__).read_bytes())!=PARENT_SHA):
        raise ValueError("BLOCKED_P4D15_PINNED_ORIGINAL_DRIFT")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
        raise ValueError("BLOCKED_P4D15_NOT_PREREG")
    source_js=js_patch.read_text("utf8")
    if "proto.renderGraphics = original;" not in source_js or (
        "renderP4A2BrushWidths1to10Probe" not in source_js):
        raise ValueError("BLOCKED_P4D15_SCOPED_INJECTION_UNREVIEWED")
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D15: каждый PNG из НАСТОЯЩЕГО Egret BoardPane/CanvasRenderer"
        " против итоговой WebGL текстуры. Оригинальные шейдеры/игра не изменены."
        " 30 сцен,3 точных повтора,blank=34 native PNG и 33 реальных intermediate."
        " Сравниваются десять отдельных пространственных копий; это E3"
        " исследование, не математическая подмена, E4/E5/CHALK NOT_RUN.\n","utf8")
    rows=[]
    first=None
    matched_replay=[]
    with p4b7.native_egret_session(workspace) as driver:
        driver.set_script_timeout(240)
        # installs only a test-only wrapper function, NOT a renderer replacement.
        driver.execute_script(source_js)
        blank=driver.execute_script(p4d3.CMD,[])
        zero,meta=p4d3.read_webgl_result(blank,output,"REAL_EGRET_BLANK")
        if (zero.shape!=NATIVE_SHAPE or np.any(zero[:,:,3]) or
            meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL"):
            raise ValueError("BLOCKED_P4D15_BLANK")
        with (output/"CASE_RESULTS_APPEND_ONLY.jsonl").open("a",encoding="utf8") as ledger:
            for length in LENGTHS:
                for width in WIDTHS:
                    for angle in ANGLES:
                        folder=output/"source_native"/f"L{length:02d}"/f"W{width:02d}"
                        folder.mkdir(parents=True,exist_ok=True)
                        row,can,web=render_case(
                            driver,source_js,folder,width,angle,length)
                        rows.append(row)
                        ledger.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                        ledger.flush()
                        if first is None:
                            first=(can,row["source_native_graphics_bounds"],web)
                        if angle==0 and length==4 and width in REPEATS:
                            duplicate,ca2,wb2=render_case(
                                driver,source_js,folder,width,angle,length,"_REPEAT")
                            matched=bool(np.array_equal(ca2,can) and
                                         np.array_equal(wb2,web))
                            if not matched:
                                raise ValueError("BLOCKED_P4D15_REPLAY_DIFFERENT")
                            matched_replay.append({
                                "width":width,
                                "identical_source_texture_and_native":matched,
                                "source_png_sha256":duplicate["source_image_sha256"],
                                "native_png_sha256":duplicate["native_image_sha256"],
                            })
                    print("P4D15_NATIVE_CANVAS_VS_WEBGL",length,width,
                          "scenes",len(rows),flush=True)
    if len(rows)!=CASE_COUNT or len(matched_replay)!=3:
        raise ValueError("BLOCKED_P4D15_SCENE_COUNT")
    if first:
        panel_from_case(*first,output/"P4D15_NATIVE_CANVAS_VS_WEBGL_FIRST_CASE.png")
    groups={}
    for row in rows:
        grp=row["classification"]
        groups[grp]=groups.get(grp,0)+1
    source_changed=sum(not x["canvas_intermediate"]["isolated10_exact_rgba"] for x in rows)
    gl_changed=sum(not x["native_webgl_final"]["isolated10_exact_rgba"] for x in rows)
    if sum(groups.values())!=CASE_COUNT:
        raise ValueError("BLOCKED_P4D15_DIAGNOSTIC_TOTAL")
    by_width={}
    for width in WIDTHS:
        subset=[r for r in rows if r["width"]==width]
        by_width[str(width)]={
            "scenes":len(subset),
            "canvas_changed":sum(not r["canvas_intermediate"]["isolated10_exact_rgba"]
                                 for r in subset),
            "webgl_changed":sum(not r["native_webgl_final"]["isolated10_exact_rgba"]
                                for r in subset)
        }
    report={
        "experiment":EXPERIMENT,
        "technical_result":"P4D15_REAL_CANVAS_GRAPHICS_SOURCE_VS_FINAL_WEBGL",
        "native_renderer":"real Egret 5.4.1 BoardPane/CanvasRenderer/WebGLRenderer",
        "original_engine_git_blob":p4d3.ENGINE_GIT_BLOB,
        "original_renderer_git_blob":p4d3.RENDERER_GIT_BLOB,
        "original_P4D3_runner_git_blob":PARENT_SHA,
        "native_scenes_including_blank_repeats":TOTAL_NATIVE,
        "native_canvas_source_pngs":TOTAL_SOURCE,
        "native_blank_alpha_zero":True,
        "exact_full_scenes_repeated":len(matched_replay),
        "pairwise_original_isolated_strokes_per_scene":10,
        "cases":CASE_COUNT,"widths":list(WIDTHS),
        "angles":list(ANGLES),"lengths":list(LENGTHS),
        "canvas_rgba_noninvariant_cases":source_changed,
        "final_webgl_rgba_noninvariant_cases":gl_changed,
        "classification":groups,
        "by_width":by_width,
        "H1_any_canvas_stage_translation_mismatch":source_changed>0,
        "H2_any_webgl_stage_translation_mismatch":gl_changed>0,
        "H3_most_source_equal_remain_webgl_equal":(
            "NOT_EVALUABLE" if source_changed==CASE_COUNT else
            groups.get("both_exact",0) >
            groups.get("canvas_exact_webgl_changed",0)),
        "replays":matched_replay,
        "research_only_no_production":True,
        "E4_live":"NOT_RUN","E5_independent_quality":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID")
    }
    report["members_sha256"]={
        str(f.relative_to(output)).replace("\\","/"):digest(f.read_bytes())
        for f in sorted(output.rglob("*")) if f.is_file()
    }
    (output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,allow_nan=False,indent=2)+"\n","utf8")
    print("P4D15_NATIVE_CANVAS_WEBGL_CLASSIFICATION",groups,flush=True)
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--engine-js",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--injection-js",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    run(a.workspace,a.engine_js,a.renderer,a.injection_js,a.output)
