#!/usr/bin/env python3
"""P4D10: frozen 10 conflicting original-owner pixels, 5x5 fine true Egret phases.

Only diagnostic single-stroke feasibility under approved source foreign0;
P4D11 softened experimental acceptance is NOT imported.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d5_pixel_state_native_feedback as p4d5
import run_engine001_b1r_p4d7_native_width1_phase_feasibility as p4d7
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D10_NATIVE_FINE_PHASE_CONFLICT10_V1"
PREREG="ENGINE001_B1R_P4D10_NATIVE_FINE_PHASE_CONFLICT10_PREREG_2026-11-19.md"
CONFLICT_IDS=(
    "OWNER011_X046_Y046","OWNER113_X046_Y045",
    "OWNER116_X050_Y057","OWNER123_X054_Y045",
    "OWNER127_X062_Y045","OWNER010_X047_Y045",
    "OWNER013_X055_Y045","OWNER015_X061_Y045",
    "OWNER079_X063_Y045","OWNER115_X049_Y057")
DELTAS=(0.,1/32,2/32,3/32,4/32)
PHASES=tuple((f"FINE_X{ix}_Y{iy}",dx,dy)
              for ix,dx in enumerate(DELTAS) for iy,dy in enumerate(DELTAS))
CONTROL="FINE_X0_Y0"
WIDTH=1
EXPECTED_ROWS=250
CROP=p4d7.CROP
SOURCE=p4d7.SOURCE


def exact_phase_stroke(sample:dict,variant:tuple,palette:np.ndarray)->dict:
    name,dx,dy=variant
    if (name not in {v[0] for v in PHASES} or
        (name,dx,dy) not in PHASES):
        raise ValueError("BLOCKED_P4D10_UNREGISTERED_MICRO_PHASE")
    x,y,owner=int(sample["x"]),int(sample["y"]),int(sample["owner"])
    return p4d5.make_stroke(owner,palette,WIDTH,
        x+dx-.01,y+dy,x+dx+.01,y+dy)


def selected_samples(index:np.ndarray)->list[dict]:
    all_samples=p4d7.owner_samples(index)
    m={s["sample_id"]:s for s in all_samples}
    if len(m)!=21 or len(CONFLICT_IDS)!=10 or len(set(CONFLICT_IDS))!=10 or (
        not set(CONFLICT_IDS).issubset(m)):
        raise ValueError("BLOCKED_P4D10_FROZEN_TEN_NOT_IN_21")
    ans=[m[name] for name in CONFLICT_IDS]
    if not p4b4.source_critical_rois()[p4d5.crop_target(index)].all():
        raise ValueError("BLOCKED_P4D10_NOT_PROTECTED")
    return ans


def summarize(samples:list[dict],rows:list[dict])->list[dict]:
    out=[]
    for sample in samples:
        sub=[r for r in rows if r["sample_id"]==sample["sample_id"]]
        if len(sub)!=len(PHASES) or len({r["variant"] for r in sub})!=len(PHASES):
            raise ValueError("BLOCKED_P4D10_MISSING_NATIVE_VARIANTS")
        controls=[r for r in sub if r["variant"]==CONTROL]
        if len(controls)!=1 or not controls[0]["measured"]["phase_feasible"]:
            raise ValueError("BLOCKED_P4D10_ORIGINAL_GRID_X0_Y0_NOT_FEASIBLE")
        extra=[r for r in sub if r["variant"]!=CONTROL and r["measured"]["phase_feasible"]]
        out.append({
            **sample,
            "tested_true_native_fine_phases":len(sub),
            "original_grid_zero_control_feasible":True,
            "additional_safe_correct_fine_phases":len(extra),
            "additional_safe_variants":[r["variant"] for r in extra],
            "foreign_zero_and_correct_total_including_original":len(extra)+1,
            "minimum_actual_source_foreign_alpha24_backing":min(
                r["measured"]["native_alpha24_genuine_foreign_backing"] for r in sub),
        })
    if len(out)!=len(CONFLICT_IDS):
        raise ValueError("BLOCKED_P4D10_SAMPLES_MISSING")
    return out


def heatmap(samples:list[dict],rows:list[dict],output:Path):
    lookup={(r["sample_id"],r["variant"]):r for r in rows}
    cell=24
    img=Image.new("RGB",(500,len(samples)*125+52),(245,245,245))
    draw=ImageDraw.Draw(img)
    draw.text((8,8),"Real Egret: green=safe owner, red=foreign, amber=not correct",
              fill=(25,25,25))
    for i,s in enumerate(samples):
        oy=37+i*125
        draw.text((5,oy+3),s["sample_id"],fill=(22,22,22))
        for ix in range(5):
            for iy in range(5):
                r=lookup[(s["sample_id"],f"FINE_X{ix}_Y{iy}")]
                m=r["measured"]
                color=(54,150,84) if m["phase_feasible"] else (
                    (201,67,67) if m["native_alpha24_genuine_foreign_backing"] else
                    (234,183,63))
                x=265+ix*cell
                y=oy+iy*cell
                draw.rectangle((x,y,x+cell-2,y+cell-2),fill=color)
    img.save(output/"P4D10_ACTUAL_EGRET_FINE_PHASE_HEATMAP.png")


def run(workspace:Path,source:Path,engine_js:Path,
        renderer:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D10_OUTPUT_EXISTS")
    check_source(source)
    if (p4d5.p4b1.git_blob(renderer.read_bytes())!=p4d5.p4d0.RENDERER_BLOB or
        p4d5.p4b1.git_blob(engine_js.read_bytes())!=p3b.ENGINE_GIT_BLOB_SHA1):
        raise ValueError("BLOCKED_P4D10_RENDERER_SOURCE_CHANGED")
    p=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not p.is_file() or EXPERIMENT not in p.read_text("utf8"):
        raise ValueError("BLOCKED_P4D10_E0_NOT_FROZEN")
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D10: 10 конфликтных sample от P4D9 × 25 near-zero fractional "
        "native width1 Egret. Protected original source-owner foreign alpha24=0, "
        "source exact color5/9; CONTROL dx=dy=0. Только isolated evidence; "
        "никакой мягкой краски P4D11 и никакого production.\n","utf8")
    with tempfile.TemporaryDirectory(prefix="engine001-p4d10-fresh-") as tmp:
        fresh=Path(tmp)/"fresh_p3d"
        source_result=p3d.run(source,engine_js,fresh)
        if (source_result["experiment"]!=p3d.EXPERIMENT or
            source_result["original_source_sha256"]!=p4d5.SOURCE_SHA or
            not source_result["P3B_original_recomputed_in_current_run"] or
            source_result["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D10_NOT_FRESH_B1R_ORIGINAL")
        palette,_=p3b.read_engine_palette(engine_js)
        indices={}
        for method in p4d7.METHODS:
            ix=np.asarray(Image.open(
                fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),np.uint8).copy()
            p4c0.validate_source(ix,palette,
                source_result["all_results"][SOURCE]["selected_engine_indices"])
            indices[method]=ix
            Image.fromarray(ix[CROP[1]:CROP[3],CROP[0]:CROP[2]]).save(
                output/(method+"_INDEX_ROI.png"))
        a,b=indices[p4d7.METHODS[0]],indices[p4d7.METHODS[1]]
        x0,y0,x1,y1=CROP
        if not np.array_equal(a[y0:y1,x0:x1],b[y0:y1,x0:x1]):
            raise ValueError("BLOCKED_P4D10_EF_SOURCE_ROI_DIFFERENT")
        samples=selected_samples(a)
        protected=p4b4.source_critical_rois()
        (output/"FROZEN_CONFLICT_SAMPLES.json").write_text(json.dumps(
            samples,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
        native_dir=output/"REAL_EGRET_WIDTH1_FINE_PHASE_SCENES"
        native_dir.mkdir()
        rows=[]
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(180)
            blank,_=p4d5._native(driver,output,"REAL_EGRET_BLANK",[])
            if np.any(blank[:,:,3]):
                raise ValueError("BLOCKED_P4D10_REAL_NATIVE_BLANK")
            with (output/"NATIVE_FINE_PHASES_APPEND_ONLY.jsonl").open("a",encoding="utf8") as stream:
                for sample in samples:
                    folder=native_dir/sample["sample_id"]
                    folder.mkdir()
                    for phase in PHASES:
                        stroke=exact_phase_stroke(sample,phase,palette)
                        if phase[0]==CONTROL and stroke!=p4d7.phase_stroke(
                            sample,("GRID_X0_Y0",0.,0.),palette):
                            raise ValueError("BLOCKED_P4D10_CONTROL_NOT_P4D7_ORIGINAL")
                        native,meta=p4d5._native(driver,folder,phase[0],[stroke])
                        measured=p4d7.actual_native_single_metrics(
                            native,a,palette,protected,sample)
                        row={
                            "sample_id":sample["sample_id"],
                            "owner":sample["owner"],"x":sample["x"],"y":sample["y"],
                            "variant":phase[0],"dx":phase[1],"dy":phase[2],
                            "width":stroke["width"],"colorIndex":stroke["colorIndex"],
                            "stroke_points":stroke["points"],
                            "renderer":meta["renderer"],
                            "native_png_sha256":meta["source_sha256"],
                            "measured":measured,
                        }
                        rows.append(row)
                        stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                        stream.flush()
                    print("P4D10_REAL_NATIVE_SAMPLE",sample["sample_id"],
                          "safe_phases",sum(r["measured"]["phase_feasible"]
                                            for r in rows[-25:]),"of25",flush=True)
        if len(rows)!=EXPECTED_ROWS:
            raise ValueError("BLOCKED_P4D10_MISSING_NATIVE_250")
        results=summarize(samples,rows)
        heatmap(samples,rows,output)
        additional=sum(1 for x in results if x["additional_safe_correct_fine_phases"]>0)
        total_extra=sum(x["additional_safe_correct_fine_phases"] for x in results)
        report={
            "experiment":EXPERIMENT,
            "technical_result":"REAL_EGRET_250_NATIVE_FINE_PHASES_PLUS_BLANK",
            "original_source_sha256":p4d5.SOURCE_SHA,
            "original_P3D_fresh_B1R_not_G32_V44":True,
            "E_F_index_crop_identical":True,
            "p4d7_selected_21_samples_rechecked":True,
            "protected_original_source_CROP":list(CROP),
            "original_nonwhite_target":307,
            "fixed_conflict_sample_ids":list(CONFLICT_IDS),
            "sample_count":len(samples),
            "fine_phase_deltas":list(DELTAS),
            "phases_per_sample":len(PHASES),
            "native_stroke_scene_count":len(rows),
            "native_blank_count":1,
            "native_blank_alpha_zero":True,
            "original_grid_zero_control_feasible_count":sum(
                x["original_grid_zero_control_feasible"] for x in results),
            "samples_with_additional_strict_safe_correct_phases":additional,
            "total_additional_strict_safe_correct_fine_phases":total_extra,
            "sample_results":results,
            "H1_any_of_ten_gains_safe_phase":additional>=1,
            "H2_at_least_five_gain_safe_phase":additional>=5,
            "H3_all_ten_original_controls_safe":True,
            "approved_native_source_foreign_alpha24":0,
            "required_correct_5of9":5,
            "native_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
            "renderer_git_blob":p4d5.p4d0.RENDERER_BLOB,
            "game_engine_git_blob":p3b.ENGINE_GIT_BLOB_SHA1,
            "no_import_of_P4D11_relaxed_foreign":True,
            "full_cumulative_image_quality":"NOT_MEASURED",
            "E4_live":"NOT_RUN","E5_independent":"NOT_RUN",
            "exact_run_bound_CHALK":None,
            "production_promotion":False,
            "github_sha":os.getenv("GITHUB_SHA"),
            "github_run_id":os.getenv("GITHUB_RUN_ID"),
        }
        report["members_sha256"]={
            str(path.relative_to(output)).replace("\\","/"):digest(path.read_bytes())
            for path in sorted(output.rglob("*")) if path.is_file()
        }
        (output/"report.json").write_text(json.dumps(
            report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
        print("P4D10_RESULT",additional,"of10 gains additional phases",
              total_extra,"total extra",len(rows),"native strokes",
              "H1",report["H1_any_of_ten_gains_safe_phase"],
              "H2",report["H2_at_least_five_gain_safe_phase"],flush=True)
        return report


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--workspace",type=Path,required=True)
    cli.add_argument("--source",type=Path,required=True)
    cli.add_argument("--engine-js",type=Path,required=True)
    cli.add_argument("--renderer",type=Path,required=True)
    cli.add_argument("--output",type=Path,required=True)
    args=cli.parse_args()
    run(args.workspace,args.source,args.engine_js,args.renderer,args.output)
