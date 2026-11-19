#!/usr/bin/env python3
"""P4D12 research: strict cumulative native Egret with prevalidated dy=1/32.

Each accepted stroke retains *approved* original protected source foreign0.
P4D11 soft/adaptive research policies are NOT imported or used.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d5_pixel_state_native_feedback as p4d5
import run_engine001_b1r_p4d7_native_width1_phase_feasibility as p4d7
import run_engine001_b1r_p4d8_native_cumulative_phase_pixel_state as p4d8
import run_engine001_b1r_p4d10_native_fine_phase_conflict10 as p4d10
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D12_NATIVE_STRICT_CUMULATIVE_FINE10_V1"
PREREG="ENGINE001_B1R_P4D12_NATIVE_CUMULATIVE_FINE10_PREREG_2026-11-19.md"
ARMS=("BASELINE_P4D8_STRICT","FINE10_DY_1_32_STRICT")
FINE_VARIANT="FINE_X0_Y1"
FINE_PHASE=("FINE_X0_Y1",0.,1/32)
BASELINE={"fixed_sample_correct":16,"source_owner_correct":17,
          "accepted":16,"attempts":21,"remaining":290}
CROP=p4d7.CROP
SOURCE=p4d7.SOURCE


def phase_for_original(row:dict,sample:dict,palette:np.ndarray,
                       ordinary_variants:dict)->dict:
    variant=row["variant"]
    if variant not in ordinary_variants:
        raise ValueError("BLOCKED_P4D12_INVALID_ORIGINAL_PHASE")
    return p4d7.phase_stroke(sample,ordinary_variants[variant],palette)


def replacement_order(original_rows:list[dict],fine_rows:list[dict],
                      conflict_ids:tuple[str,...])->list[dict]:
    """Exact same order; change only one true native phase in each 10 conflicts."""
    if (len(conflict_ids)!=10 or len(set(conflict_ids))!=10 or
        set(conflict_ids)!=set(p4d10.CONFLICT_IDS)):
        raise ValueError("BLOCKED_P4D12_CONFLICT_SET_DRIFT")
    source={name:[] for name in conflict_ids}
    for r in original_rows:
        if r["sample_id"] in source:
            source[r["sample_id"]].append(r)
    if any(len(g)!=1 or g[0]["variant"]!="GRID_X0_Y0" for g in source.values()):
        raise ValueError("BLOCKED_P4D12_NOT_ONE_ORIGINAL_SAFE_FOR_TEN")
    fine={}
    for r in fine_rows:
        if r["sample_id"] not in source:
            raise ValueError("BLOCKED_P4D12_UNKNOWN_FINE_SAMPLE")
        if r["variant"]==FINE_VARIANT:
            if (r["sample_id"] in fine or not r["measured"]["phase_feasible"] or
                not r["measured"]["native_exact_sample_cell_correct_5of9"] or
                r["measured"]["native_alpha24_genuine_foreign_backing"]):
                raise ValueError("BLOCKED_P4D12_UNSAFE_FINE_PHASE")
            fine[r["sample_id"]]=r
    if set(fine)!=set(source):
        raise ValueError("BLOCKED_P4D12_MISSING_FINE_SOURCE_NATIVE")
    output=[]
    for row in original_rows:
        if row["sample_id"] in fine:
            r=fine[row["sample_id"]]
            output.append({
                **row,
                "variant":FINE_VARIANT,
                "points":r["stroke_points"],
                "native_png_sha256":r["native_png_sha256"],
                "measured":r["measured"],
                "width":r["width"],
                "colorIndex":r["colorIndex"],
                "source_0_1_natively_feasible":True,
            })
        else:
            output.append(dict(row))
    if ([x["sample_id"] for x in output]!=
        [x["sample_id"] for x in original_rows] or
        sum(r["variant"]==FINE_VARIANT for r in output)!=10):
        raise ValueError("BLOCKED_P4D12_NOT_ORDER_ONLY_FINE10")
    return output


def do_arm(driver,folder:Path,arm:str,
           ordered:list[dict],samples:dict,variants:dict,
           index:np.ndarray,palette:np.ndarray,original:np.ndarray)->dict:
    if arm not in ARMS or folder.exists():
        raise ValueError("BLOCKED_P4D12_ARM_EXISTS_OR_UNKNOWN")
    folder.mkdir()
    images=folder/"REAL_NATIVE_ALL_CUMULATIVE_TRIALS"
    images.mkdir()
    current,_=p4d5._native(driver,folder,"REAL_EGRET_BLANK",[])
    if np.any(current[:,:,3]):
        raise ValueError("BLOCKED_P4D12_NATIVE_BLANK")
    state=np.zeros((240,150),bool)
    strokes=[]
    used=set()
    records=[]
    with (folder/"CUMULATIVE_NATIVE_ATTEMPT_LEDGER.jsonl").open("a",encoding="utf8") as stream:
        while True:
            choices=[r for r in ordered
                     if (r["sample_id"],r["variant"]) not in used and
                     not state[samples[r["sample_id"]]["y"],
                               samples[r["sample_id"]]["x"]]]
            if not choices:
                break
            row=choices[0]
            sample=samples[row["sample_id"]]
            used.add((row["sample_id"],row["variant"]))
            stroke=(p4d10.exact_phase_stroke(sample,FINE_PHASE,palette)
                    if row["variant"]==FINE_VARIANT
                    else phase_for_original(row,sample,palette,variants))
            if (stroke["width"]!=row["width"] or
                stroke["colorIndex"]!=row["colorIndex"] or
                stroke["colorRgb"]!=row["colorRgb"] or
                stroke["points"]!=(
                    row["stroke_points"] if row["variant"]==FINE_VARIANT
                    else row["points"])):
                raise ValueError("BLOCKED_P4D12_NON_NATIVE_STROKE_PARAMS")
            n=len(records)+1
            native,meta=p4d5._native(
                driver,images,
                f"ATTEMPT_{n:04d}_{sample['sample_id']}_{row['variant']}",
                strokes+[stroke])
            measured=p4d8.trial_metrics(
                current,native,index,palette,state,sample)
            event={
                "arm":arm,"trial":n,
                "sample_id":row["sample_id"],"variant":row["variant"],
                "owner":stroke["colorIndex"],"width":stroke["width"],
                "points":stroke["points"],
                "isolated_native_sha256":row["native_png_sha256"],
                "real_cumulative_native_sha256":meta["source_sha256"],
                **measured,
            }
            if measured["accepted"]:
                strokes.append(stroke)
                current=native
                state=p4d5.actual_state(current,index,palette)
            records.append(event)
            stream.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+"\n")
            stream.flush()
    replay,_=p4d5._native(driver,folder,"REAL_EGRET_FINAL_REPLAY",strokes)
    if not np.array_equal(current,replay):
        raise ValueError("BLOCKED_P4D12_NOT_DETERMINISTIC_NATIVE_REPLAY")
    score=p4d5.roi_metrics(current,index,palette)
    hits=sum(int(state[s["y"],s["x"]]) for s in samples.values())
    p4d8.compare_native(original,index,palette,current,state,folder)
    accepted=[r for r in records if r["accepted"]]
    if (len(accepted)!=len(strokes) or
        any(r["native_changed_foreign_alpha24_backing"] or
            r["native_original_white_alpha24_backing"] or
            r["native_lost_correct_1_to_0"] for r in accepted) or
        score["correct_logical_native_5_of_9"]+score["remaining_zero_logical"]!=307):
        raise ValueError("BLOCKED_P4D12_NATIVE_APPROVED_PROTECTION")
    result={
        "arm":arm,
        "fixed_sample_correct":hits,
        "source_owner_correct":int(score["correct_logical_native_5_of_9"]),
        "remaining":int(score["remaining_zero_logical"]),
        "accepted":len(accepted),
        "attempts":len(records),
        "rejected":len(records)-len(accepted),
        "approved_protected_original_foreign_zero":True,
        "accepted_lost_correct_zero":True,
        "accepted_original_white_alpha24_zero":True,
        "real_native_final_replay_bit_exact":True,
        "rejected_samples":[
            {"sample_id":r["sample_id"],"foreign_backing":
              r["native_changed_foreign_alpha24_backing"]}
            for r in records if not r["accepted"]],
        "native_final_roi_score":score,
    }
    print("P4D12_REAL_NATIVE_ARM",arm,
          "fixed",hits,"/21","correct",result["source_owner_correct"],"/307",
          "accepted",len(accepted),"attempts",len(records),flush=True)
    return result


def run(workspace:Path,source:Path,engine_js:Path,
        renderer:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D12_OUTPUT_EXISTS")
    check_source(source)
    if (p4d5.p4b1.git_blob(renderer.read_bytes())!=p4d5.p4d0.RENDERER_BLOB or
        p4d5.p4b1.git_blob(engine_js.read_bytes())!=p3b.ENGINE_GIT_BLOB_SHA1):
        raise ValueError("BLOCKED_P4D12_PINNED_ENGINE_OR_RENDERER_DRIFT")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
        raise ValueError("BLOCKED_P4D12_E0_NOT_PREREGISTERED")
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D12: неизменный P4D8 STRICT native 0/1 versus только 10 \n"
        "микрофаз FINE_X0_Y1 по P4D10, все 21 исходных owner samples, \n"
        "real cumulative full Egret board per trial. protected foreign24=0 \n"
        "без мягких P4D11 допусков. Не production/E4/CHALK.\n","utf8")
    isolated7=output/"P4D7_FRESH_NATIVE_GRID"
    parent7=p4d7.run(workspace,source,engine_js,renderer,isolated7)
    isolated10=output/"P4D10_FRESH_NATIVE_FINE_PHASES"
    parent10=p4d10.run(workspace,source,engine_js,renderer,isolated10)
    if (parent7["experiment"]!=p4d7.EXPERIMENT or
        parent7["native_scene_capture_total"]!=1387 or
        parent7["safe_and_correct_samples"]!=21 or
        parent10["experiment"]!=p4d10.EXPERIMENT or
        parent10["native_stroke_scene_count"]!=250 or
        parent10["original_grid_zero_control_feasible_count"]!=10 or
        parent10["samples_with_additional_strict_safe_correct_phases"]!=10 or
        parent10["total_additional_strict_safe_correct_fine_phases"]!=10):
        raise ValueError("BLOCKED_P4D12_PARENT_NATIVE_OR_SOURCE_CHANGED")
    samples_list=json.loads((isolated7/"FIXED_ORIGINAL_SOURCE_SAMPLES.json").read_text("utf8"))
    sample_map={x["sample_id"]:x for x in samples_list}
    if len(samples_list)!=21 or len(sample_map)!=21:
        raise ValueError("BLOCKED_P4D12_SOURCE_SAMPLES_DRIFT")
    rows7=[json.loads(x) for x in
           (isolated7/"NATIVE_PHASE_RESULTS_APPEND_ONLY.jsonl").read_text("utf8").splitlines() if x.strip()]
    rows10=[json.loads(x) for x in
            (isolated10/"NATIVE_FINE_PHASES_APPEND_ONLY.jsonl").read_text("utf8").splitlines() if x.strip()]
    if len(rows7)!=1386 or len(rows10)!=250:
        raise ValueError("BLOCKED_P4D12_PARENT_NATIVE_ROWS_MISSING")
    ordered=p4d8.eligible_rows(rows7,set(sample_map))
    fine_order=replacement_order(ordered,rows10,p4d10.CONFLICT_IDS)
    variants={x[0]:x for x in p4d7.VARIANTS}
    palette,_=p3b.read_engine_palette(engine_js)
    with tempfile.TemporaryDirectory(prefix="engine001-p4d12-original-") as tmp:
        fresh=Path(tmp)/"fresh_p3d"
        original_src=p3d.run(source,engine_js,fresh)
        if (original_src["experiment"]!=p3d.EXPERIMENT or
            original_src["original_source_sha256"]!=p4d5.SOURCE_SHA or
            not original_src["P3B_original_recomputed_in_current_run"] or
            original_src["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D12_NOT_ORIGINAL_RGB_B1R")
        ix={}
        for method in p4d7.METHODS:
            arr=np.asarray(Image.open(
                fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),np.uint8).copy()
            p4c0.validate_source(arr,palette,
                original_src["all_results"][SOURCE]["selected_engine_indices"])
            ix[method]=arr
        x0,y0,x1,y1=CROP
        if not np.array_equal(
            ix[p4d7.METHODS[0]][y0:y1,x0:x1],
            ix[p4d7.METHODS[1]][y0:y1,x0:x1]):
            raise ValueError("BLOCKED_P4D12_EF_SOURCE_ROI_DIFFERENCE")
        idx=ix[p4d7.METHODS[0]]
        if (p4d7.owner_samples(idx)!=samples_list or
            p4d10.selected_samples(idx)!=[
                sample_map[x] for x in p4d10.CONFLICT_IDS] or
            int(p4d5.crop_target(idx).sum())!=307 or
            not p4b4.source_critical_rois()[y0:y1,x0:x1].all()):
            raise ValueError("BLOCKED_P4D12_PROTECTED_SOURCE_DRIFT")
        original=np.asarray(Image.open(
            fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"),np.uint8)
        results={}
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(240)
            for arm,order in zip(ARMS,(ordered,fine_order)):
                results[arm]=do_arm(driver,output/arm,arm,order,sample_map,
                                    variants,idx,palette,original)
    baseline=results[ARMS[0]]
    for name,val in BASELINE.items():
        if baseline[name]!=val:
            raise ValueError("BLOCKED_P4D12_BASELINE_P4D8_PARITY_"+name)
    fine=results[ARMS[1]]
    report={
        "experiment":EXPERIMENT,
        "technical_result":"TRUE_EGRET_STRICT_TWO_ARM_FINE10_CUMULATIVE",
        "original_source_sha256":p4d5.SOURCE_SHA,
        "fresh_P3D_original_B1R_no_G32_V44":True,
        "E_F_index_crop_identical":True,
        "source_crop":list(CROP),
        "target_nonwhite":307,
        "fixed_samples":21,
        "P4D7_remeasured_true_native_scenes":1387,
        "P4D10_remeasured_true_native_scenes":251,
        "P4D10_exact_new_dy":1/32,
        "fine10_source_sample_ids":list(p4d10.CONFLICT_IDS),
        "replaced_only_ten_paths_and_kept_candidate_order":True,
        "strict_original_source_alpha24_foreign_gate":0,
        "strict_original_white_alpha24_gate":0,
        "correct_pixel_required_backing":5,
        "rgb_tolerance":32,
        "baseline_P4D8_exact_parity":True,
        "results":results,
        "H1_fine_strict_better_samples_and_correct":
            (fine["fixed_sample_correct"]>baseline["fixed_sample_correct"] and
             fine["source_owner_correct"]>baseline["source_owner_correct"]),
        "H2_fine_all_21_fixed_samples_source_safe":fine["fixed_sample_correct"]==21,
        "H3_control_exact_P4D8":True,
        "all_accepted_original_source_foreign_alpha24_zero":
            all(x["approved_protected_original_foreign_zero"] for x in results.values()),
        "game_engine_git_blob":p3b.ENGINE_GIT_BLOB_SHA1,
        "renderer_git_blob":p4d5.p4d0.RENDERER_BLOB,
        "real_game_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
        "no_soft_P4D11_any_arm_applied":True,
        "production_promotion":False,
        "full_art_quality":"NOT_MEASURED",
        "E4_live":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    report["members_sha256"]={
        str(path.relative_to(output)).replace("\\","/"):digest(path.read_bytes())
        for path in sorted(output.rglob("*")) if path.is_file()
    }
    (output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    print("P4D12_HYPOTHESES",report["H1_fine_strict_better_samples_and_correct"],
          report["H2_fine_all_21_fixed_samples_source_safe"],flush=True)
    return report


if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--source",type=Path,required=True)
    a.add_argument("--engine-js",type=Path,required=True)
    a.add_argument("--renderer",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    run(args.workspace,args.source,args.engine_js,args.renderer,args.output)
