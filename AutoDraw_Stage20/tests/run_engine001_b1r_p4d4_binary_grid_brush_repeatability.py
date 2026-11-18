#!/usr/bin/env python3
"""P4D4: 1/256-logical-point exact binary endpoint grid, ALL same native scenes.

The ONLY variable from original P4D3 is input endpoint snap before replay.
No renderer or parent modification. Reuse real Egret BoardPane and P4D3 metrics.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4d3_native_brush_repeatability as parent
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import read_webgl_result

EXPERIMENT = "ENGINE001_B1R_P4D4_BINARY_GRID_TRANSLATION_REPRODUCIBILITY_V1"
PREREG = "ENGINE001_B1R_P4D4_BINARY_GRID_BRUSH_REPEATABILITY_DIAGNOSTIC_PREREG_2026-11-19.md"
PARENT_BLOB = "3437a9326b381d9c94d6ade80059d40adf233d09"
GRID = 256
FROZEN_P4D3_WITHIN_SAME_SCENE_EXACT = 292
EXPECTED_PRIMARY = 480


def quantized_primary(width: int,angle: int,length: int) -> list[dict]:
    """Only the exact 1/256 rounding of same original per-stroke coordinates."""
    plan=parent.build_primary(width,angle,length)
    for s in plan:
        for p in s["points"]:
            for k in ("x","y"):
                p[k]=round(p[k]*GRID)/GRID
    offsets=[
        tuple((float(pt["x"]-parent.CENTERS[0][0]),
               float(pt["y"]-parent.CENTERS[0][1]))
              for pt in plan[0]["points"])
    ]
    baseline=offsets[0]
    for i in range(10):
        cx,cy=parent.CENTERS[i]
        translated=tuple((float(p["x"]-cx),float(p["y"]-cy))
                         for p in plan[i]["points"])
        if translated != baseline:
            raise ValueError("BLOCKED_P4D4_NOT_BINARY_IDENTICAL_TRANSLATED_ENDPOINTS")
    if plan[11]["points"]!=plan[12]["points"] or len(plan)!=21:
        raise ValueError("BLOCKED_P4D4_OVERLAP_BROKEN")
    return plan


def run(workspace:Path,engine_js:Path,renderer:Path,output:Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D4_OUTPUT_EXISTS")
    if (p4b1.git_blob(renderer.read_bytes())!=parent.RENDERER_GIT_BLOB or
        p4b1.git_blob(engine_js.read_bytes())!=parent.ENGINE_GIT_BLOB or
        p4b1.git_blob(Path(parent.__file__).read_bytes())!=PARENT_BLOB):
        raise ValueError("BLOCKED_P4D4_FROZEN_PARENT_OR_RENDERER_SHA")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4D4_NO_PRE_REG")
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D4: same P4D3 native Egret width1..10 x angles0..345 step15, "
        "length4/34, 10 independent +10 overlaid, two replays. ONLY change: "
        "1/256 logical pixel binary endpoint snap before BoardPane. "
        "P4D3 original 292/480 equal translated footprint cases remains immutable. "
        "Game/renderer/production/E4/CHALK unchanged.\n","utf8")
    cases=[]
    with p4b7.native_egret_session(workspace) as driver:
        driver.set_script_timeout(180)
        blank=driver.execute_script(parent.CMD,[])
        rgba,meta=read_webgl_result(blank,output,"REAL_EGRET_BLANK")
        if (rgba.shape!=parent.NATIVE_SHAPE or
            meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or
            meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer" or
            np.any(rgba[:,:,3])):
            raise ValueError("BLOCKED_P4D4_NATIVE_BLANK")
        with (output/"CASES_APPEND_ONLY.jsonl").open("a",encoding="utf8") as writer:
            for length in parent.LENGTHS:
                for width in parent.WIDTHS:
                    for angle in parent.ANGLES:
                        key=parent.case_id(width,angle,length)
                        folder=output/"primary"/f"L{length:02d}"/f"W{width:02d}"
                        folder.mkdir(parents=True,exist_ok=True)
                        plan=quantized_primary(width,angle,length)
                        (folder/(key+"_PLAN.json")).write_text(
                            json.dumps(plan,ensure_ascii=False,allow_nan=False)+"\n","utf8")
                        a,m1=parent.read_scene(driver,folder,key+"_R1",plan)
                        b,m2=parent.read_scene(driver,folder,key+"_R2",plan)
                        cross=parent.difference(a,b)
                        s1=parent.scores(a)
                        s2=parent.scores(b)
                        if (s1["single_native_ink_alpha1_pixels"]==0 or
                            s2["single_native_ink_alpha1_pixels"]==0):
                            raise ValueError("BLOCKED_P4D4_NATIVE_BLANK_STROKE")
                        exact=(cross["rgba_differing_pixels"]==0 and
                               s1["isolated10_all_exact_rgba"] and
                               s2["isolated10_all_exact_rgba"] and
                               s1["single_vs_first_isolated"]["rgba_differing_pixels"]==0 and
                               s2["single_vs_first_isolated"]["rgba_differing_pixels"]==0)
                        row={
                            "kind":"PRIMARY","id":key,"width":width,"angle_deg":angle,
                            "length_logical":length,"endpoint_snap_grid_per_logical":GRID,
                            "relative_endpoints_binary_exact":True,
                            "isolated_strokes":10,"overlay_strokes":10,
                            "single_control_strokes":1,
                            "total_accepted_strokes":21,
                            "total_accepted_vertices_NOT_CHALK":42,
                            "cross_render_exact":cross["rgba_differing_pixels"]==0,
                            "cross_render_differences":cross,
                            "render1":m1,"render2":m2,
                            "same_scene1":s1,"same_scene2":s2,
                            "pass_predetermined":bool(exact),
                        }
                        cases.append(row)
                        writer.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                        writer.flush()
                    subset=[x for x in cases if x["length_logical"]==length and
                            x["width"]==width]
                    print("P4D4_WIDTH",length,width,
                          "exact",sum(x["pass_predetermined"] for x in subset),
                          "of",len(subset),flush=True)
    reverse=parent.reversal_diagnostics(output)
    (output/"REVERSAL_DIRECTION_DIAGNOSTICS.json").write_text(
        json.dumps(reverse,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    parent.heatmaps(output,cases)
    exact=sum(r["pass_predetermined"] for r in cases)
    two_replays=sum(r["cross_render_exact"] for r in cases)
    no_overlay_diff=sum(r["same_scene1"]["overlay10_vs_single"][
                            "rgba_differing_pixels"]==0 for r in cases)
    widths={str(w):{
        "cases":len([r for r in cases if r["width"]==w]),
        "translated_exact_cases":sum(r["pass_predetermined"] for r in cases if r["width"]==w),
        "cross_replays_exact":sum(r["cross_render_exact"] for r in cases if r["width"]==w),
        "overlay_changed_cases":sum(r["same_scene1"]["overlay10_vs_single"][
                                    "rgba_differing_pixels"]>0 for r in cases if r["width"]==w),
        } for w in parent.WIDTHS}
    report={
        "experiment":EXPERIMENT,
        "technical_result":"ALL_961_PINNED_EGRET_IMAGES_CAPTURED",
        "translation_result":("EXACT_NATIVE_TRANSLATION_480_OF_480"
                              if exact==EXPECTED_PRIMARY else
                              "NATIVE_TRANSLATION_VARIATION_PERSISTS"),
        "original_p4d3_exact_translation_292_of_480":FROZEN_P4D3_WITHIN_SAME_SCENE_EXACT,
        "native_same_input_cross_run_exact":two_replays,
        "translation_exact_cases":exact,
        "translation_delta_cases_vs_P4D3":exact-FROZEN_P4D3_WITHIN_SAME_SCENE_EXACT,
        "grid_resolution_inverse":GRID,
        "all_relative_stroke_endpoints_bit_exact_by_construction":True,
        "widths":list(parent.WIDTHS),"directed_angles":list(parent.ANGLES),
        "lengths_logical":list(parent.LENGTHS),
        "native_cases":len(cases),"full_native_captures":2*len(cases)+1,
        "native_single_vs_overlay_exact_cases":no_overlay_diff,
        "reversed_pairs":len(reverse),
        "reversed_equal_pairs":sum(r["rgba_differing_pixels"]==0 for r in reverse),
        "widths_summary":widths,
        "renderer_git_blob":parent.RENDERER_GIT_BLOB,
        "engine_git_blob":parent.ENGINE_GIT_BLOB,
        "parent_test_blob":PARENT_BLOB,
        "renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
        "blank_native_zero_alpha":True,
        "E4_live_game":"NOT_RUN","E5_independent_live":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "production_promotion":False,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    report["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    print("P4D4_NATIVE_RESULT",exact,"/480 exact; P4D3",FROZEN_P4D3_WITHIN_SAME_SCENE_EXACT,
          "two-run",two_replays,"/480 overlay equal",no_overlay_diff,
          "reversed",report["reversed_equal_pairs"],"/240",flush=True)
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--engine-js",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    opts=p.parse_args()
    run(opts.workspace,opts.engine_js,opts.renderer,opts.output)
