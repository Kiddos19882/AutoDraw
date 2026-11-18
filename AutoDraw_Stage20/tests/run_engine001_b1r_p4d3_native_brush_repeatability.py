#!/usr/bin/env python3
"""P4D3: native Egret 5.4.1 brush repeatability, 1..10 widths x 24 directions.

This is offline native E3 measurement; never a Pillow/OpenCV brush simulator.
The archived renderer, engine code, game/CHALK estimator remain UNMODIFIED.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
from run_engine001_complex_holdout_v5 import read_webgl_result
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT = "ENGINE001_B1R_P4D3_NATIVE_BRUSH_WIDTH_DIRECTION_REPEATABILITY_V1"
PREREG = "ENGINE001_B1R_P4D3_NATIVE_BRUSH_REPEATABILITY_DIRECTION_MATRIX_PREREG_2026-11-19.md"
RENDERER_GIT_BLOB = "76d950e0a8911888a9df3b675b866519ecf7bba4"
ENGINE_GIT_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
WIDTHS = tuple(range(1, 11))
ANGLES = tuple(range(0, 360, 15))
LENGTHS = (4, 34)
EDGE_ANGLES = tuple(range(0, 360, 45))
CENTERS = tuple((x, y) for y in (40, 120, 200) for x in (58, 172, 286, 400))
HALF = 27
SCALE = 3
NATIVE_SHAPE = (720, 1380, 4)
COLOR = 0x503D35
SECONDARY_COLOR = 0xC54191
ALPHA = 24
CMD = ("return window.AutoDrawGameRendererReference."
       "renderP4A2BrushWidths1to10Probe(arguments[0]);")


def two_points(cx: float, cy: float, length: int, angle: int) -> list[dict]:
    """Angle+180 *exactly* swaps endpoints of angle, no trig rounding drift."""
    if (angle not in ANGLES or length not in LENGTHS and length != 8 or
            not 0 <= cx < 460 or not 0 <= cy < 240):
        raise ValueError("BLOCKED_P4D3_POINTS_INPUT")
    rad = math.radians(angle % 180)
    dx = .5 * length * math.cos(rad)
    dy = .5 * length * math.sin(rad)
    points = [{"x": float(cx-dx), "y":float(cy-dy)},
              {"x": float(cx+dx), "y":float(cy+dy)}]
    if angle >= 180:
        points.reverse()
    return points


def stroke(width: int, points: list[dict], color: int = COLOR):
    if width not in WIDTHS or color not in (COLOR, SECONDARY_COLOR) or len(points) != 2:
        raise ValueError("BLOCKED_P4D3_STROKE")
    if any(not math.isfinite(v) for point in points for v in point.values()):
        raise ValueError("BLOCKED_P4D3_NONFINITE_COORD")
    if any(not (0 <= point["x"] < 460 and 0 <= point["y"] < 240)
           for point in points):
        raise ValueError("BLOCKED_P4D3_POINT_OUTSIDE_BOARD")
    return {"strokeId":"icon-0","width":width,
            "colorIndex":1,"colorRgb":color,"points":[dict(p) for p in points]}


def case_id(width: int, angle: int, length: int) -> str:
    return f"W{width:02d}_A{angle:03d}_L{length:02d}"


def build_primary(width: int, angle: int, length: int) -> list[dict]:
    if width not in WIDTHS or angle not in ANGLES or length not in LENGTHS:
        raise ValueError("BLOCKED_P4D3_PLAN_ARGS")
    out = []
    for i in range(12):
        x,y = CENTERS[i]
        points = two_points(x+.25, y+.375, length, angle)
        count = 10 if i==11 else 1
        for _ in range(count):
            out.append(stroke(width,points))
    if len(out)!=21:
        raise AssertionError("BLOCKED_P4D3_REPETITION_COUNT")
    for n,s in enumerate(out):
        s["strokeId"] = f"icon-{n}"
    return out


def build_edge(width: int, angle: int) -> list[dict]:
    """All controls on board; native clipping at border is NOT model geometry."""
    if width not in WIDTHS or angle not in EDGE_ANGLES:
        raise ValueError("BLOCKED_P4D3_EDGE_ARGS")
    pts = two_points(5.25,5.375,8,angle)
    out = [stroke(width,pts) for _ in range(10)]
    # A neighboring different-color line; deterministic overlap is not noise.
    second = two_points(10.25,10.375,8,angle)
    out.append(stroke(width,second,SECONDARY_COLOR))
    for i,s in enumerate(out):
        s["strokeId"] = f"icon-{i}"
    return out


def roi(rgba: np.ndarray, x: int, y: int) -> np.ndarray:
    if rgba.shape != NATIVE_SHAPE or rgba.dtype != np.uint8:
        raise ValueError("BLOCKED_P4D3_NATIVE_RGBA")
    return rgba[(y-HALF)*SCALE:(y+HALF)*SCALE,
                (x-HALF)*SCALE:(x+HALF)*SCALE,:]


def difference(a: np.ndarray, b: np.ndarray) -> dict:
    if a.shape!=b.shape or a.ndim!=3 or a.shape[-1]!=4:
        raise ValueError("BLOCKED_P4D3_DIFFERENCE_SHAPE")
    delta=np.abs(a.astype(np.int16)-b.astype(np.int16))
    return {"rgba_differing_pixels":int(np.any(delta != 0,axis=2).sum()),
            "max_absolute_channel_delta":int(delta.max(initial=0)),
            "alpha24_xor_pixels":int(np.logical_xor(a[:,:,3]>=ALPHA,b[:,:,3]>=ALPHA).sum()),
            "alpha1_xor_pixels":int(np.logical_xor(a[:,:,3]>0,b[:,:,3]>0).sum())}


def alpha_hist(a: np.ndarray) -> dict:
    values,counts = np.unique(a[:,:,3],return_counts=True)
    return {str(int(k)):int(v) for k,v in zip(values,counts) if k}


def scores(rgba: np.ndarray):
    isolated=[roi(rgba,*xy) for xy in CENTERS[:10]]
    reference=isolated[0]
    differences=[difference(reference,x) for x in isolated[1:]]
    baseline=roi(rgba,*CENTERS[10])
    overlay=roi(rgba,*CENTERS[11])
    # Two native single strokes at different integer translations must agree.
    additional=difference(reference,baseline)
    overlay_diff=difference(baseline,overlay)
    return {
        "isolated10_all_exact_rgba":
            all(d["rgba_differing_pixels"]==0 for d in differences),
        "isolated10_mismatch_pixels_total":
            sum(d["rgba_differing_pixels"] for d in differences),
        "isolated10_max_channel_delta":
            max((d["max_absolute_channel_delta"] for d in differences),default=0),
        "isolated10_mismatch_each":differences,
        "single_vs_first_isolated":additional,
        "overlay10_vs_single":overlay_diff,
        "single_native_ink_alpha24_pixels":int((baseline[:,:,3]>=ALPHA).sum()),
        "overlay10_native_ink_alpha24_pixels":int((overlay[:,:,3]>=ALPHA).sum()),
        "single_native_ink_alpha1_pixels":int((baseline[:,:,3]>0).sum()),
        "overlay10_native_ink_alpha1_pixels":int((overlay[:,:,3]>0).sum()),
        "single_alpha_hist_nonzero":alpha_hist(baseline),
        "overlay_alpha_hist_nonzero":alpha_hist(overlay),
        "first_sample_native_png_roi_sha256":hashlib.sha256(reference.tobytes()).hexdigest(),
    }


def read_scene(driver, folder: Path, stem: str, plan: list[dict]):
    response=driver.execute_script(CMD,plan)
    rgba,meta=read_webgl_result(response,folder,stem)
    if (rgba.shape != NATIVE_SHAPE or meta.get("schema") !=
        "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
        meta.get("renderer") != "real Egret 5.4.1 BoardPane/WebGLRenderer" or
        meta.get("strokeCount") != len(plan) or
        meta.get("syntheticAcceptedVerticesNotChalk") != 2*len(plan) or
        meta.get("mode") != "normal"):
        raise ValueError("BLOCKED_P4D3_NOT_PINNED_REAL_EGRET")
    return rgba,{"source_png_sha256":meta["source_sha256"],
                 "stroke_count":len(plan),
                 "accepted_vertices_NOT_CHALK":2*len(plan),
                 "renderer":meta["renderer"],"schema":meta["schema"],
                 "backend":"WebGLRenderer","size":[1380,720]}


def primary_case(driver: object, out: Path, width: int, angle: int, length: int) -> dict:
    key=case_id(width,angle,length)
    case_dir=out/"primary"/f"L{length:02d}"/f"W{width:02d}"
    case_dir.mkdir(parents=True,exist_ok=True)
    plan=build_primary(width,angle,length)
    (case_dir/(key+"_PLAN.json")).write_text(
        json.dumps(plan,ensure_ascii=False,allow_nan=False)+"\n","utf8")
    first,meta1=read_scene(driver,case_dir,key+"_R1",plan)
    second,meta2=read_scene(driver,case_dir,key+"_R2",plan)
    compare=difference(first,second)
    s1=scores(first)
    s2=scores(second)
    if (s1["single_native_ink_alpha1_pixels"]==0 or
        s2["single_native_ink_alpha1_pixels"]==0):
        raise ValueError("BLOCKED_P4D3_EMPTY_NATIVE_STROKE")
    result={
        "kind":"PRIMARY","id":key,"width":width,"angle_deg":angle,
        "length_logical":length,"isolated_strokes":10,
        "overlay_strokes":10,"single_control_strokes":1,
        "total_accepted_strokes":21,"total_accepted_vertices_NOT_CHALK":42,
        "cross_render_exact":compare["rgba_differing_pixels"]==0,
        "cross_render_differences":compare,
        "render1":meta1,"render2":meta2,
        "same_scene1":s1,"same_scene2":s2,
        "pass_predetermined":(compare["rgba_differing_pixels"]==0 and
            s1["isolated10_all_exact_rgba"] and s2["isolated10_all_exact_rgba"] and
            s1["single_vs_first_isolated"]["rgba_differing_pixels"]==0 and
            s2["single_vs_first_isolated"]["rgba_differing_pixels"]==0)
    }
    return result


def edge_case(driver: object, out: Path, width:int, angle:int) -> dict:
    key=f"W{width:02d}_A{angle:03d}_EDGE"
    folder=out/"stress"/f"W{width:02d}"
    folder.mkdir(parents=True,exist_ok=True)
    plan=build_edge(width,angle)
    (folder/(key+"_PLAN.json")).write_text(
        json.dumps(plan,ensure_ascii=False,allow_nan=False)+"\n","utf8")
    first,meta1=read_scene(driver,folder,key+"_R1",plan)
    second,meta2=read_scene(driver,folder,key+"_R2",plan)
    result=difference(first,second)
    return {"kind":"STRESS_EDGE_COLOR","id":key,"width":width,
            "angle_deg":angle,"ten_overlapping_edge_strokes":10,
            "different_color_nearby_strokes":1,
            "total_accepted_strokes":11,"total_accepted_vertices_NOT_CHALK":22,
            "cross_render_exact":result["rgba_differing_pixels"]==0,
            "cross_render_differences":result,
            "native_nonempty":bool(np.any(first[:,:,3]>0)),
            "render1":meta1,"render2":meta2}


def reversal_diagnostics(output: Path) -> list[dict]:
    """Compare the first isolated cell for angles θ and θ+180, native images."""
    measurements=[]
    for length in LENGTHS:
        for width in WIDTHS:
            for angle in range(0,180,15):
                case1=case_id(width,angle,length)
                case2=case_id(width,angle+180,length)
                folder=output/"primary"/f"L{length:02d}"/f"W{width:02d}"
                with Image.open(folder/(case1+"_R1.png")) as a:
                    aa=np.asarray(a.convert("RGBA"),np.uint8)
                with Image.open(folder/(case2+"_R1.png")) as b:
                    bb=np.asarray(b.convert("RGBA"),np.uint8)
                delta=difference(roi(aa,*CENTERS[0]),roi(bb,*CENTERS[0]))
                measurements.append({"width":width,"length_logical":length,
                    "angle_fwd":angle,"angle_reverse":angle+180,**delta})
    return measurements


def heatmaps(output: Path, cases: list[dict]):
    """Summary of *measured native* equality only; never a synthetic brush image."""
    for length in LENGTHS:
        rows={(r["width"],r["angle_deg"]):r for r in cases
              if r["kind"]=="PRIMARY" and r["length_logical"]==length}
        canvas=Image.new("RGB",(24*30+93,10*32+92),(246,246,246))
        draw=ImageDraw.Draw(canvas)
        for j,angle in enumerate(ANGLES):
            draw.text((97+j*30,24),f"{angle:03d}",fill=(28,28,28))
        for i,width in enumerate(WIDTHS):
            draw.text((14,53+i*32),f"W{width:02d}",fill=(28,28,28))
            for j,angle in enumerate(ANGLES):
                r=rows.get((width,angle))
                col=(31,154,84) if r and r["pass_predetermined"] else (202,69,63)
                draw.rectangle((94+j*30,49+i*32,121+j*30,77+i*32),
                                fill=col)
        draw.text((11,8),f"Real Egret exact repeat, length {length}: green PASS red FAIL",
                  fill=(22,22,22))
        canvas.save(output/f"REAL_NATIVE_REPEAT_HEATMAP_LENGTH_{length:02d}.png")


def run(workspace:Path,engine_js:Path,renderer:Path,output:Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D3_OUTPUT_EXISTS")
    if p4b1.git_blob(renderer.read_bytes()) != RENDERER_GIT_BLOB:
        raise ValueError("BLOCKED_P4D3_FROZEN_RENDERER_DRIFT")
    if p4b1.git_blob(engine_js.read_bytes()) != ENGINE_GIT_BLOB:
        raise ValueError("BLOCKED_P4D3_FROZEN_ENGINE_DRIFT")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4D3_PREREG_MISSING")
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D3: 1..10 sizes x24 angles x2 lengths. For EACH case ten translated same "
        "native strokes, single control, ten identical overlays, second replay, "
        "true Egret WebGL PNG. Stress edge and neighbor color at 8 angles per width.\n"
        "GREEN heatmap = strict within-scene copied RGBA + two independent whole-scene "
        "pixel-exact replays (no changed thresholds).\n"
        "ALL raw PNGs stored and hashed, no Pillow/OpenCV stroke substitute. "
        "NOT live gameplay, not CHALK or art coverage proof.\n", "utf8")
    cases=[]
    with p4b7.native_egret_session(workspace) as driver:
        driver.set_script_timeout(180)
        blank_response=driver.execute_script(CMD,[])
        blank,blank_meta=read_webgl_result(blank_response,output,"REAL_EGRET_BLANK")
        if (blank.shape!=NATIVE_SHAPE or blank_meta.get("schema") !=
            "ENGINE001_B1R_P4A2_BLANK_WEBGL" or
            blank_meta.get("renderer") !=
            "real Egret 5.4.1 BoardPane/WebGLRenderer" or
            np.any(blank[:,:,3])):
            raise ValueError("BLOCKED_P4D3_NATIVE_BLANK_INVALID")
        print("P4D3_NATIVE_BLANK_PASS",flush=True)
        ledger=(output/"CASES_APPEND_ONLY.jsonl")
        with ledger.open("a",encoding="utf8") as write:
            for length in LENGTHS:
                for width in WIDTHS:
                    for angle in ANGLES:
                        row=primary_case(driver,output,width,angle,length)
                        cases.append(row)
                        write.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                        write.flush()
                    part=[r for r in cases if r["kind"]=="PRIMARY" and
                          r["length_logical"]==length and r["width"]==width]
                    print("P4D3_PRIMARY_WIDTH",length,width,
                          "exact",sum(r["pass_predetermined"] for r in part),
                          "of",len(part),flush=True)
            for width in WIDTHS:
                for angle in EDGE_ANGLES:
                    row=edge_case(driver,output,width,angle)
                    cases.append(row)
                    write.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                    write.flush()
                print("P4D3_EDGE_WIDTH",width,
                      "exact",sum(r["cross_render_exact"] for r in cases
                                  if r["kind"]=="STRESS_EDGE_COLOR" and
                                  r["width"]==width),
                      "of",len(EDGE_ANGLES),flush=True)

    reversal=reversal_diagnostics(output)
    (output/"REVERSAL_DIRECTION_DIAGNOSTICS.json").write_text(
        json.dumps(reversal,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    heatmaps(output,cases)
    primary=[r for r in cases if r["kind"]=="PRIMARY"]
    stresses=[r for r in cases if r["kind"]=="STRESS_EDGE_COLOR"]
    repeat_exact=sum(r["pass_predetermined"] for r in primary)
    edge_exact=sum(r["cross_render_exact"] and r["native_nonempty"]
                   for r in stresses)
    overlay_changed=sum(r["same_scene1"]["overlay10_vs_single"][
                            "rgba_differing_pixels"]>0 for r in primary)
    reversal_same=sum(r["rgba_differing_pixels"]==0 for r in reversal)
    widths_summary={}
    for width in WIDTHS:
        subset=[r for r in primary if r["width"]==width]
        widths_summary[str(width)]={
            "primary_cases":len(subset),
            "exact_repeat_cases":sum(r["pass_predetermined"] for r in subset),
            "primary_repeat_mismatch_cases":sum(not r["pass_predetermined"] for r in subset),
            "overlay10_differs_from_single_cases":sum(
                r["same_scene1"]["overlay10_vs_single"]["rgba_differing_pixels"]>0
                for r in subset),
            "edge_stress_exact_cases":sum(
                r["cross_render_exact"] and r["native_nonempty"] for r in stresses
                if r["width"]==width)}
    result={
        "experiment":EXPERIMENT,
        "technical_result":"ALL_P4D3_TRUE_NATIVE_BOARD_SCENES_CAPTURED",
        "repeatability_result":("E3_OFFLINE_EXACT_REPEAT_480_OF_480"
                                if repeat_exact==480 and edge_exact==80
                                else "E3_OFFLINE_REPEATABILITY_VARIATION_OBSERVED"),
        "game_board_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
        "pinned_renderer_git_blob":RENDERER_GIT_BLOB,
        "pinned_engine_git_blob":ENGINE_GIT_BLOB,
        "source_original_palette_not_used":True,
        "board_logical_size":[460,240],
        "native_backing_png_size":[1380,720],
        "native_widths":list(WIDTHS),
        "angles_deg":list(ANGLES),
        "line_lengths_logical":list(LENGTHS),
        "native_primary_cases":len(primary),
        "native_edge_stress_cases":len(stresses),
        "full_native_captures":2*(len(primary)+len(stresses))+1,
        "blank_zero_alpha":True,
        "independent_native_strokes_per_primary":10,
        "overlaid_same_path_strokes_per_primary":10,
        "primary_cases_exact":repeat_exact,
        "edge_stress_cases_exact":edge_exact,
        "overlay_changed_cases":overlay_changed,
        "reversed_direction_pairs":len(reversal),
        "reversed_native_footprint_equal_pairs":reversal_same,
        "width_summary":widths_summary,
        "case_data":"CASES_APPEND_ONLY.jsonl",
        "reversal_data":"REVERSAL_DIRECTION_DIAGNOSTICS.json",
        "E4_live_game":"NOT_RUN","E5_independent_live":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "production_promotion":False,
        "source_and_game_code_modified":False,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    result["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    (output/"report.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    print("P4D3_ALL_CAPTURED",result["full_native_captures"],
          "primary exact",repeat_exact,"/480; edge exact",edge_exact,"/80",
          "overlay differs",overlay_changed,"reversal equal",reversal_same,
          "/",len(reversal),flush=True)
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",type=Path,required=True)
    ap.add_argument("--engine-js",type=Path,required=True)
    ap.add_argument("--renderer",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    run(args.workspace,args.engine_js,args.renderer,args.output)
