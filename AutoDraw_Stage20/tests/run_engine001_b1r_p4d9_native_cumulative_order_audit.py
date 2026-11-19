#!/usr/bin/env python3
"""P4D9 E3: three prespecified order-only arms for protected native 0/1.

P4D7 source sample/phase/isolation and P4D8 native cumulative scoring remain
unchanged. Only the order of whole-scene trial strokes differs between arms.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d5_pixel_state_native_feedback as p4d5
import run_engine001_b1r_p4d7_native_width1_phase_feasibility as p4d7
import run_engine001_b1r_p4d8_native_cumulative_phase_pixel_state as p4d8
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D9_NATIVE_CUMULATIVE_ORDER_AUDIT_V1"
PREREG="ENGINE001_B1R_P4D9_NATIVE_CUMULATIVE_ORDER_AUDIT_PREREG_2026-11-19.md"
ARMS=("BASELINE_P4D8","FIVE_FAILED_SAMPLES_FIRST","SOURCE_OWNER_DESCENDING")
FIVE_FAILED_IDS=(
    "OWNER011_X046_Y046","OWNER113_X046_Y045",
    "OWNER116_X050_Y057","OWNER123_X054_Y045",
    "OWNER127_X062_Y045")
BASELINE_EXPECTED={
    "fixed_sample_correct":16,
    "source_owner_correct":17,
    "accepted":16,
    "attempts":21,
    "remaining":290,
}
SOURCE=p4d7.SOURCE
CROP=p4d7.CROP
WHITE=p4d7.WHITE


def rank_for_arm(row:dict,arm:str)->tuple:
    """Single variable: candidate order only. Keep P4D8 within-sample rank."""
    original=p4d8.rank_candidate(row)
    if arm=="BASELINE_P4D8":
        return original
    if arm=="FIVE_FAILED_SAMPLES_FIRST":
        return (0 if row["sample_id"] in FIVE_FAILED_IDS else 1,)+original
    if arm=="SOURCE_OWNER_DESCENDING":
        return (-int(row["owner"]),)+original
    raise ValueError("BLOCKED_P4D9_UNREGISTERED_ARM")


def order_candidates(rows:list[dict],arm:str)->list[dict]:
    if arm not in ARMS:
        raise ValueError("BLOCKED_P4D9_UNREGISTERED_ARM")
    if len(set(FIVE_FAILED_IDS))!=5:
        raise ValueError("BLOCKED_P4D9_PRIORITY_SET_COLLISION")
    return sorted(rows,key=lambda row:rank_for_arm(row,arm))


def do_arm(driver,output:Path,arm:str,sorted_rows:list[dict],
           samples:dict,index:np.ndarray,palette:np.ndarray,
           original:np.ndarray,variants:dict)->dict:
    """All arm results use unchanged P4D8 trial_metrics from true native PNG."""
    if output.exists():
        raise ValueError("BLOCKED_P4D9_EXISTING_ARM_OUTPUT")
    output.mkdir()
    trial_dir=output/"NATIVE_FULL_SCENE_TRIALS"
    trial_dir.mkdir()
    blank,blank_meta=p4d5._native(driver,output,"REAL_EGRET_BLANK",[])
    if np.any(blank[:,:,3]):
        raise ValueError("BLOCKED_P4D9_BLANK_NONZERO")
    current=blank
    state=np.zeros((240,150),bool)
    strokes=[]
    ledger=[]
    used=set()
    path=output/"NATIVE_ATTEMPT_LEDGER_APPEND_ONLY.jsonl"
    with path.open("a",encoding="utf8") as stream:
        while True:
            eligible=[r for r in sorted_rows
                      if (r["sample_id"],r["variant"]) not in used and
                      not state[samples[r["sample_id"]]["y"],
                                samples[r["sample_id"]]["x"]]]
            if not eligible:
                break
            row=eligible[0]
            sample=samples[row["sample_id"]]
            used.add((row["sample_id"],row["variant"]))
            stroke=p4d7.phase_stroke(sample,variants[row["variant"]],palette)
            if (stroke["width"]!=1 or
                stroke["colorIndex"]!=row["colorIndex"] or
                stroke["points"]!=row["points"] or
                stroke["colorRgb"]!=row["colorRgb"]):
                raise ValueError("BLOCKED_P4D9_P4D7_SOURCE_STROKE_DRIFT")
            n=len(ledger)+1
            rgba,meta=p4d5._native(driver,trial_dir,
                f"ATTEMPT_{n:04d}_{sample['sample_id']}_{row['variant']}",
                strokes+[stroke])
            measured=p4d8.trial_metrics(
                current,rgba,index,palette,state,sample)
            rec={
                "arm":arm,"trial":n,"sample_id":row["sample_id"],
                "owner":stroke["colorIndex"],"variant":row["variant"],
                "exact_points":stroke["points"],
                "native_png_sha256":meta["source_sha256"],
                "isolated_png_sha256":row["native_png_sha256"],
                "renderer":meta["renderer"],
                **measured
            }
            if measured["accepted"]:
                strokes.append(stroke)
                current=rgba
                state=p4d5.actual_state(current,index,palette)
            ledger.append(rec)
            stream.write(json.dumps(rec,ensure_ascii=False,allow_nan=False)+"\n")
            stream.flush()
    replay,replay_meta=p4d5._native(
        driver,output,"REAL_EGRET_FINAL_REPLAY",strokes)
    if not np.array_equal(replay,current):
        raise ValueError("BLOCKED_P4D9_FINAL_REPLAY_NOT_BIT_IDENTICAL")
    score=p4d5.roi_metrics(current,index,palette)
    hit=sum(bool(state[s["y"],s["x"]]) for s in samples.values())
    p4d8.compare_native(original,index,palette,current,state,output)
    accepted=[e for e in ledger if e["accepted"]]
    rejected=[e for e in ledger if not e["accepted"]]
    if (any(e["native_lost_correct_1_to_0"]>0 or
            e["native_changed_foreign_alpha24_backing"]>0 or
            e["native_original_white_alpha24_backing"]>0 for e in accepted)
        or len(strokes)!=len(accepted)
        or score["correct_logical_native_5_of_9"]+score["remaining_zero_logical"]!=307):
        raise ValueError("BLOCKED_P4D9_UNSAFE_ACCEPTANCE")
    result={
        "arm":arm,
        "fixed_sample_correct":hit,
        "source_owner_correct":int(score["correct_logical_native_5_of_9"]),
        "remaining":int(score["remaining_zero_logical"]),
        "accepted":len(accepted),
        "attempts":len(ledger),
        "rejected":len(rejected),
        "rejected_source_foreign_alpha24":[
            {"id":e["sample_id"],
             "owner":e["owner"],"native_foreign":e["native_changed_foreign_alpha24_backing"],
             "new_correct":e["native_new_correct_0_to_1"],
             "lost_correct":e["native_lost_correct_1_to_0"]}
            for e in rejected],
        "full_native_replay_rgba_exact":True,
        "accepted_native_lost_zero":True,
        "accepted_native_foreign_alpha24_zero":True,
        "accepted_source_white_alpha24_zero":True,
        "correct_fraction_full_roi":float(score["correct_fraction"]),
    }
    print("P4D9_REAL_NATIVE_ARM",arm,"sample",hit,"/21","correct",
          result["source_owner_correct"],"/307","accepted",len(accepted),
          "trial",len(ledger),"rejected",len(rejected),flush=True)
    return result


def run(workspace:Path,source:Path,engine_js:Path,
        renderer:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D9_EVIDENCE_EXISTS")
    check_source(source)
    if (p4d5.p4b1.git_blob(renderer.read_bytes())!=p4d5.p4d0.RENDERER_BLOB or
        p4d5.p4b1.git_blob(engine_js.read_bytes())!=p3b.ENGINE_GIT_BLOB_SHA1):
        raise ValueError("BLOCKED_P4D9_ENGINE_OR_RENDERER_PIN_DRIFT")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.exists() or EXPERIMENT not in prereg.read_text("utf8"):
        raise ValueError("BLOCKED_P4D9_NO_PRIOR_FROZEN_E0")
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D9: исходная B1-R картинка и frozen 21 samples/66 real Egret width1 "
        "phases. Три заранее определённых порядка одной и той же cumulative "
        "0/1 покраски; protected source foreign alpha24 zero; все rejected "
        "raw scene PNG и append-only logs сохраняются. Не production/CHALK.\n","utf8")
    p4d7_out=output/"FRESH_P4D7_REAL_EGRET_PHASES"
    frozen=p4d7.run(workspace,source,engine_js,renderer,p4d7_out)
    if (frozen["experiment"]!=p4d7.EXPERIMENT or
        frozen["native_scene_capture_total"]!=1387 or
        frozen["safe_and_correct_samples"]!=21 or
        not frozen["original_EF_frozen_ROI_index_exact_identical"]):
        raise ValueError("BLOCKED_P4D9_P4D7_NATIVE_DRIFT")
    rows=[json.loads(s) for s in
        (p4d7_out/"NATIVE_PHASE_RESULTS_APPEND_ONLY.jsonl").read_text(
            "utf8").splitlines() if s.strip()]
    samples=json.loads((p4d7_out/"FIXED_ORIGINAL_SOURCE_SAMPLES.json").read_text("utf8"))
    if len(samples)!=21 or len(rows)!=1386:
        raise ValueError("BLOCKED_P4D9_NATIVE_SOURCE_ROWS")
    sample_by_id={s["sample_id"]:s for s in samples}
    if len(sample_by_id)!=21 or not set(FIVE_FAILED_IDS).issubset(set(sample_by_id)):
        raise ValueError("BLOCKED_P4D9_FIXED_SAMPLE_DRIFT")
    candidates=p4d8.eligible_rows(rows,set(sample_by_id))
    if not candidates:
        raise ValueError("BLOCKED_P4D9_NO_REAL_FEASIBLE_CANDIDATES")
    variants={v[0]:v for v in p4d7.VARIANTS}
    palette,_=p3b.read_engine_palette(engine_js)
    with tempfile.TemporaryDirectory(prefix="engine001-p4d9-source-") as tmp:
        fresh=Path(tmp)/"fresh_p3d"
        parent=p3d.run(source,engine_js,fresh)
        if (parent["experiment"]!=p3d.EXPERIMENT or
            parent["original_source_sha256"]!=p4d5.SOURCE_SHA or
            not parent["P3B_original_recomputed_in_current_run"] or
            parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D9_NOT_FRESH_SOURCE")
        indices={}
        for method in p4d7.METHODS:
            ix=np.asarray(Image.open(
                fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),np.uint8).copy()
            sel=parent["all_results"][SOURCE]["selected_engine_indices"]
            p4c0.validate_source(ix,palette,sel)
            indices[method]=ix
        x0,y0,x1,y1=CROP
        if not np.array_equal(indices[p4d7.METHODS[0]][y0:y1,x0:x1],
                              indices[p4d7.METHODS[1]][y0:y1,x0:x1]):
            raise ValueError("BLOCKED_P4D9_IDENTICAL_ROI_SOURCE_DRIFT")
        source_index=indices[p4d7.METHODS[0]]
        if (int(p4d5.crop_target(source_index).sum())!=307 or
            p4d7.owner_samples(source_index)!=samples):
            raise ValueError("BLOCKED_P4D9_SAMPLES_NOT_FROZEN")
        original=np.asarray(Image.open(
            fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"),np.uint8)
        results={}
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(240)
            for arm in ARMS:
                ordered=order_candidates(candidates,arm)
                results[arm]=do_arm(driver,output/arm,arm,ordered,sample_by_id,
                                    source_index,palette,original,variants)
        baseline=results["BASELINE_P4D8"]
        for key,val in BASELINE_EXPECTED.items():
            if baseline[key]!=val:
                raise ValueError(f"BLOCKED_P4D9_BASELINE_NOT_P4D8_PARITY_{key}")
        alternative=[results[a] for a in ARMS if a!="BASELINE_P4D8"]
        report={
            "experiment":EXPERIMENT,
            "technical_result":"TRUE_NATIVE_3_ARM_ORDER_ONLY_CUMULATIVE_EGRET",
            "pre_registered_arms":list(ARMS),
            "prespecified_five_prioritized_ids":list(FIVE_FAILED_IDS),
            "original_source_sha256":p4d5.SOURCE_SHA,
            "fresh_original_B1R_P3D":True,
            "same_21_samples_66_positions_and_20_owners":True,
            "source_EF_ROI_indices_identical":True,
            "target_nonwhite":307,"protected_crop_xyxy":list(CROP),
            "p4d7_native_isolated_count":1387,
            "p4d7_safe_samples":frozen["safe_and_correct_samples"],
            "candidate_isolated_safe_count":len(candidates),
            "baseline_P4D8_native_exact_parity":True,
            "results":results,
            "H1_any_alternative_samples_gt16":any(
                r["fixed_sample_correct"]>16 for r in alternative),
            "H2_any_alternative_owner_correct_gt17":any(
                r["source_owner_correct"]>17 for r in alternative),
            "H3_any_alternative_all21":any(
                r["fixed_sample_correct"]==21 for r in alternative),
            "game_engine_git_blob":p3b.ENGINE_GIT_BLOB_SHA1,
            "renderer_git_blob":p4d5.p4d0.RENDERER_BLOB,
            "game_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
            "no_production_or_color_map_or_threshold_changes":True,
            "full_art_owner99_protected0_far3":"NOT_MEASURED",
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
        print("P4D9_HYPOTHESES",report["H1_any_alternative_samples_gt16"],
              report["H2_any_alternative_owner_correct_gt17"],
              report["H3_any_alternative_all21"],flush=True)
        return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--engine-js",type=Path,required=True)
    parser.add_argument("--renderer",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    run(args.workspace,args.source,args.engine_js,args.renderer,args.output)
