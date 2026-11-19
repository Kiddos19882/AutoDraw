#!/usr/bin/env python3
"""ENGINE-001 P4D11: native five-arm soft/adaptive foreign-touch experiment.

PROTECTED original source foreign=0 remains the *approved* gate.
Relaxed arms are unaccepted scientific diagnostics and never production.
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
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D11_SOFT_ADAPTIVE_NATIVE_FOREIGN_TOUCH_V1"
PREREG="ENGINE001_B1R_P4D11_SOFT_ADAPTIVE_NATIVE_FOREIGN_TOUCH_PREREG_2026-11-19.md"
ARMS=("STRICT_P4D8","SOFT_1_BACKING","SOFT_2_BACKING",
      "SOFT_3_BACKING","ADAPTIVE_RGB12_REPAIRABLE")
BUDGETS={"STRICT_P4D8":0,"SOFT_1_BACKING":1,"SOFT_2_BACKING":2,
         "SOFT_3_BACKING":3,"ADAPTIVE_RGB12_REPAIRABLE":2}
RGB_MAX_DELTA=12
REPAIR_DISTANCE=1
CROP=p4d7.CROP
SOURCE=p4d7.SOURCE
WHITE=p4d5.WHITE
BASELINE={"fixed_sample_correct":16,"source_owner_correct":17,
          "remaining":290,"accepted":16,"attempts":21}


def actual_foreign_impact(before:np.ndarray,after:np.ndarray,
                          index:np.ndarray,owner:int,
                          sample:dict,samples:dict)->tuple[dict,np.ndarray]:
    """Only actual changed original-foreign backing alpha>=24 from native RGBA.

    Computes *incremental* RGB perturbation before/after, not final source
    fidelity and not a prediction that a neighbor can be fully repaired.
    """
    if (before.shape!=p4d5.BOARD_SHAPE or
        after.shape!=p4d5.BOARD_SHAPE or
        before.dtype!=np.uint8 or after.dtype!=np.uint8 or
        index.shape!=(240,150) or index.dtype!=np.uint8 or
        int(index[sample["y"],sample["x"]])!=owner or owner==WHITE):
        raise ValueError("BLOCKED_P4D11_INVALID_NATIVE_OWNER_INPUT")
    changed=np.any(before!=after,axis=2)
    own=p4d7.full_backing_source_mask(index==owner)
    foreign=changed & (after[:,:,3]>=p4d5.ALPHA) & ~own
    ys,xs=np.nonzero(foreign)
    count=len(xs)
    maxrgb=0
    max_cheby=0
    outboard=0
    repairable=0
    protected_count=0
    touched=[]
    if count:
        before_rgb=p4d5.real_composite_rgb(before)
        after_rgb=p4d5.real_composite_rgb(after)
        protection=p4b4.source_critical_rois()
        if protection.shape!=index.shape:
            raise ValueError("BLOCKED_P4D11_PROTECTION_MASK")
        for by,bx in zip(ys.tolist(),xs.tolist()):
            xx=bx//p4d5.SCALE-p4d5.X0
            yy=by//p4d5.SCALE
            delta=int(np.max(np.abs(
                before_rgb[by,bx].astype(np.int16)-
                after_rgb[by,bx].astype(np.int16))))
            maxrgb=max(maxrgb,delta)
            near=max(abs(xx-sample["x"]),abs(yy-sample["y"]))
            max_cheby=max(max_cheby,near)
            if not (0<=xx<150 and 0<=yy<240):
                outboard+=1
                touched.append({"x":xx,"y":yy,"max_RGB_delta":delta,
                                "owner":None,"protected":False,
                                "repairable_sample":False})
                continue
            other=int(index[yy,xx])
            protected_count+=int(protection[yy,xx])
            if other==WHITE:
                # P4D8 additional native white gate must also reject.
                pass
            can_repair=any(
                int(s["owner"])==other and
                max(abs(xx-int(s["x"])),abs(yy-int(s["y"])))<=REPAIR_DISTANCE
                for s in samples.values())
            repairable+=int(can_repair)
            touched.append({"x":xx,"y":yy,"owner":other,
                            "max_RGB_delta":delta,
                            "protected":bool(protection[yy,xx]),
                            "repairable_sample":bool(can_repair),
                            "sample_distance":near})
    return {
        "foreign_changed_alpha24":count,
        "foreign_backing_max_visible_RGB_channel_delta":maxrgb,
        "foreign_max_Chebyshev_logical_distance_from_sample":max_cheby,
        "foreign_outboard_backing":outboard,
        "foreign_repairable_sample_backing":repairable,
        "foreign_protected_backing":protected_count,
        "foreign_pixel_details":touched,
    },foreign


def select_by_policy(arm:str,baseline:dict,impact:dict)->bool:
    if arm not in ARMS:
        raise ValueError("BLOCKED_P4D11_UNKNOWN_POLICY")
    foreign=int(impact["foreign_changed_alpha24"])
    if (not baseline["target_sample_after"] or
        baseline["target_sample_before"] or
        baseline["native_new_correct_0_to_1"]<=0 or
        baseline["native_lost_correct_1_to_0"]!=0 or
        baseline["native_original_white_alpha24_backing"]!=0 or
        impact["foreign_outboard_backing"]!=0 or
        foreign!=baseline["native_changed_foreign_alpha24_backing"]):
        return False
    if foreign>BUDGETS[arm]:
        return False
    if arm=="STRICT_P4D8":
        if bool(baseline["accepted"]) != (foreign==0):
            raise ValueError("BLOCKED_P4D11_STRICT_PARENT_DECISION_DRIFT")
        return bool(baseline["accepted"])
    if arm=="ADAPTIVE_RGB12_REPAIRABLE":
        return (impact["foreign_backing_max_visible_RGB_channel_delta"]<=RGB_MAX_DELTA
                and impact["foreign_max_Chebyshev_logical_distance_from_sample"]<=1
                and impact["foreign_repairable_sample_backing"]==foreign)
    return True


def run_arm(driver,root:Path,arm:str,candidates:list[dict],
            samples:dict,variants:dict,
            index:np.ndarray,palette:np.ndarray,original:np.ndarray)->dict:
    if root.exists() or arm not in ARMS:
        raise ValueError("BLOCKED_P4D11_ARM_DIRECTORY_OR_NAME")
    root.mkdir()
    trials=root/"REAL_EGRET_ALL_FULL_CUMULATIVE_TRIALS"
    trials.mkdir()
    current,_=p4d5._native(driver,root,"REAL_EGRET_BLANK",[])
    if np.any(current[:,:,3]):
        raise ValueError("BLOCKED_P4D11_BLANK_NOT_EMPTY")
    used=set()
    state=np.zeros((240,150),bool)
    strokes=[]
    rows=[]
    protected_touch_union=np.zeros(p4d5.BOARD_SHAPE[:2],bool)
    with (root/"NATIVE_TRIALS_APPEND_ONLY.jsonl").open("a",encoding="utf8") as ledger:
        while True:
            possible=[r for r in candidates
                      if (r["sample_id"],r["variant"]) not in used and
                      not state[samples[r["sample_id"]]["y"],
                                samples[r["sample_id"]]["x"]]]
            if not possible:
                break
            row=possible[0]
            used.add((row["sample_id"],row["variant"]))
            sample=samples[row["sample_id"]]
            stroke=p4d7.phase_stroke(sample,variants[row["variant"]],palette)
            if (stroke["width"]!=1 or
                stroke["points"]!=row["points"] or
                stroke["colorIndex"]!=row["colorIndex"] or
                stroke["colorRgb"]!=row["colorRgb"]):
                raise ValueError("BLOCKED_P4D11_EXACT_STROKE_DRIFT")
            i=len(rows)+1
            native,meta=p4d5._native(
                driver,trials,
                f"TRIAL_{i:04d}_{sample['sample_id']}_{row['variant']}",
                strokes+[stroke])
            baseline=p4d8.trial_metrics(current,native,index,palette,state,sample)
            impact,foreign_mask=actual_foreign_impact(
                current,native,index,stroke["colorIndex"],sample,samples)
            accepted=select_by_policy(arm,baseline,impact)
            event={
                "arm":arm,"trial":i,"sample_id":row["sample_id"],
                "variant":row["variant"],"owner":stroke["colorIndex"],
                "width":stroke["width"],"exact_stroke_points":stroke["points"],
                "true_native_scene_sha256":meta["source_sha256"],
                "native_isolated_sha256":row["native_png_sha256"],
                **baseline,
                **impact,
                "approved_STRICT_P4D8_accept":bool(baseline["accepted"]),
                "experimental_policy_accept":accepted,
                "accepted_protected_rule_violation":bool(
                    accepted and impact["foreign_protected_backing"]>0),
            }
            if accepted:
                strokes.append(stroke)
                current=native
                state=p4d5.actual_state(current,index,palette)
                protected_touch_union|=foreign_mask & p4d7.full_backing_source_mask(
                    p4b4.source_critical_rois())
            rows.append(event)
            ledger.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+"\n")
            ledger.flush()
    replay,_=p4d5._native(driver,root,"REAL_EGRET_FINAL_REPLAY",strokes)
    if not np.array_equal(replay,current):
        raise ValueError("BLOCKED_P4D11_REPLAY_NONDETERMINISTIC")
    score=p4d5.roi_metrics(current,index,palette)
    hit=sum(bool(state[s["y"],s["x"]]) for s in samples.values())
    p4d8.compare_native(original,index,palette,current,state,root)
    accepted=[r for r in rows if r["experimental_policy_accept"]]
    new_wrong=sum(r["foreign_protected_backing"] for r in accepted)
    if (any(r["native_lost_correct_1_to_0"] or
            r["native_original_white_alpha24_backing"]
            for r in accepted)
        or len(strokes)!=len(accepted)
        or score["correct_logical_native_5_of_9"]+score["remaining_zero_logical"]!=307):
        raise ValueError("BLOCKED_P4D11_COMMON_HARD_GATES")
    if (arm=="STRICT_P4D8" and any(
            r["native_changed_foreign_alpha24_backing"] for r in accepted)):
        raise ValueError("BLOCKED_P4D11_STRICT_FOREIGN")
    out={
        "arm":arm,
        "foreign_budget_per_accepted_native_stroke":BUDGETS[arm],
        "adaptive_max_RGB_delta":RGB_MAX_DELTA if arm=="ADAPTIVE_RGB12_REPAIRABLE" else None,
        "fixed_sample_correct":hit,
        "source_owner_correct":int(score["correct_logical_native_5_of_9"]),
        "remaining":int(score["remaining_zero_logical"]),
        "accepted":len(accepted),
        "attempts":len(rows),
        "rejected":len(rows)-len(accepted),
        "accepted_foreign_alpha24_touch_sum":sum(
            e["foreign_changed_alpha24"] for e in accepted),
        "accepted_protected_foreign_alpha24_touch_sum":new_wrong,
        "accepted_protected_foreign_unique_backing":int(protected_touch_union.sum()),
        "accepted_max_incremental_RGB_delta":max((
            e["foreign_backing_max_visible_RGB_channel_delta"] for e in accepted),default=0),
        "accepted_source_white_alpha24_zero":True,
        "accepted_native_1_to_0_zero":True,
        "approved_protected0_gate_PASS":new_wrong==0,
        "scientific_relaxed_arm_not_accepted_for_production":arm!="STRICT_P4D8",
        "real_native_final_replay_equal":True,
        "rejected_sample_ids":[r["sample_id"] for r in rows
                               if not r["experimental_policy_accept"]],
    }
    print("P4D11_REAL_NATIVE_ARM",arm,
          "samples",out["fixed_sample_correct"],"/21",
          "correct",out["source_owner_correct"],"/307",
          "accepted",out["accepted"],"attempts",out["attempts"],
          "protected_touch",out["accepted_protected_foreign_alpha24_touch_sum"],
          "approved_PROTECTED0",out["approved_protected0_gate_PASS"],
          flush=True)
    return out


def run(workspace:Path,source:Path,engine_js:Path,
        renderer:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D11_OUTPUT_EXISTS")
    check_source(source)
    if (p4d5.p4b1.git_blob(renderer.read_bytes())!=p4d5.p4d0.RENDERER_BLOB or
        p4d5.p4b1.git_blob(engine_js.read_bytes())!=p3b.ENGINE_GIT_BLOB_SHA1):
        raise ValueError("BLOCKED_P4D11_NATIVE_SOURCE_DRIFT")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
        raise ValueError("BLOCKED_P4D11_NOT_PREREGISTERED")
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D11: пять реальных cumulative Egret arms, источник только B1-R. "
        "SOFT 1/2/3 и ADAPTIVE RGB12 — экспериментальные допуски на "
        "защищённом лице, даже если native покрытие растёт. Любое "
        "protected source-foreign>0 = FROZEN QUALITY FAIL. "
        "Не production, E4/E5/CHALK NOT_RUN.\n","utf8")
    isolated=output/"P4D7_FRESH_NATIVE_PHASES"
    orig=p4d7.run(workspace,source,engine_js,renderer,isolated)
    if (orig["experiment"]!=p4d7.EXPERIMENT or
        orig["native_scene_capture_total"]!=1387 or
        orig["safe_and_correct_samples"]!=21):
        raise ValueError("BLOCKED_P4D11_ISOLATED_NATIVE_DRIFT")
    samples_list=json.loads((isolated/"FIXED_ORIGINAL_SOURCE_SAMPLES.json").read_text("utf8"))
    rows=[json.loads(x) for x in (isolated/"NATIVE_PHASE_RESULTS_APPEND_ONLY.jsonl").read_text("utf8").splitlines() if x.strip()]
    if len(rows)!=1386 or len(samples_list)!=21:
        raise ValueError("BLOCKED_P4D11_ISOLATED_NOT_COMPLETE")
    samples={s["sample_id"]:s for s in samples_list}
    if len(samples)!=21:
        raise ValueError("BLOCKED_P4D11_DUPLICATE_SAMPLE_IDS")
    candidates=p4d8.eligible_rows(rows,set(samples))
    variants={x[0]:x for x in p4d7.VARIANTS}
    palette,_=p3b.read_engine_palette(engine_js)
    with tempfile.TemporaryDirectory(prefix="engine001-p4d11-original-") as tmp:
        fresh=Path(tmp)/"fresh_p3d"
        parent=p3d.run(source,engine_js,fresh)
        if (parent["experiment"]!=p3d.EXPERIMENT or
            parent["original_source_sha256"]!=p4d5.SOURCE_SHA or
            not parent["P3B_original_recomputed_in_current_run"] or
            parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D11_NOT_FRESH_SOURCE")
        idx={}
        for method in p4d7.METHODS:
            raw=np.asarray(Image.open(fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),np.uint8).copy()
            p4c0.validate_source(raw,palette,
                parent["all_results"][SOURCE]["selected_engine_indices"])
            idx[method]=raw
        x0,y0,x1,y1=CROP
        if not np.array_equal(idx[p4d7.METHODS[0]][y0:y1,x0:x1],
                              idx[p4d7.METHODS[1]][y0:y1,x0:x1]):
            raise ValueError("BLOCKED_P4D11_EF_SOURCES_DIFFER")
        index=idx[p4d7.METHODS[0]]
        if (p4d7.owner_samples(index)!=samples_list or
            int(p4d5.crop_target(index).sum())!=307 or
            not p4b4.source_critical_rois()[y0:y1,x0:x1].all()):
            raise ValueError("BLOCKED_P4D11_FROZEN_FACE_OR_SOURCE_DRIFT")
        orig_rgb=np.asarray(Image.open(fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"),np.uint8)
        results={}
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(240)
            for arm in ARMS:
                results[arm]=run_arm(driver,output/arm,arm,candidates,
                                     samples,variants,index,palette,orig_rgb)
    baseline=results[ARMS[0]]
    for key,value in BASELINE.items():
        if baseline[key]!=value:
            raise ValueError("BLOCKED_P4D11_STRICT_P4D8_PARITY_"+key)
    s2=results["SOFT_2_BACKING"]
    adapt=results["ADAPTIVE_RGB12_REPAIRABLE"]
    report={
        "experiment":EXPERIMENT,
        "technical_result":"REAL_EGRET_5_ARM_SOFT_AND_ADAPTIVE_CUMULATIVE",
        "original_source_sha256":p4d5.SOURCE_SHA,
        "fresh_original_P3D_B1R_not_G32_V44":True,
        "same_P4D7_21_samples_66_phases":True,
        "P4D7_remeasured_native_scene_count":orig["native_scene_capture_total"],
        "source_EF_original_index_crop_equal":True,
        "crop_xyxy":list(CROP),"target_nonwhite":307,
        "protected_face_full_crop":True,
        "pre_registered_arms":list(ARMS),
        "native_width":1,
        "hard_alpha_threshold":24,"logical_good_required_5_of_9":5,
        "soft_budgets_backing":{k:BUDGETS[k] for k in ARMS},
        "adaptive_visible_RGB_delta_max":RGB_MAX_DELTA,
        "adaptive_repair_sample_distance_max":REPAIR_DISTANCE,
        "P4D8_strict_parity":True,
        "results":results,
        "H1_soft2_improves_both":s2["fixed_sample_correct"]>16 and s2["source_owner_correct"]>17,
        "H2_adaptive_improves_both":adapt["fixed_sample_correct"]>16 and adapt["source_owner_correct"]>17,
        "H3_adaptive_at_least_soft2_coverage_with_less_risk":
            (adapt["source_owner_correct"]>=s2["source_owner_correct"] and
             adapt["accepted_protected_foreign_alpha24_touch_sum"]<=
             s2["accepted_protected_foreign_alpha24_touch_sum"]),
        "any_relaxed_arm_with_new_protected_foreign_not_quality_accepted":
            all(not results[x]["approved_protected0_gate_PASS"]
                for x in ARMS[1:] if results[x]["accepted_protected_foreign_alpha24_touch_sum"]>0),
        "native_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
        "renderer_git_blob":p4d5.p4d0.RENDERER_BLOB,
        "game_engine_git_blob":p3b.ENGINE_GIT_BLOB_SHA1,
        "production_promotion":False,
        "no_game_engine_or_estimator_or_executor_changes":True,
        "full_art_owner99_protected0_far3":"NOT_MEASURED",
        "E4_live":"NOT_RUN","E5_external":"NOT_RUN",
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
    print("P4D11_HYPOTHESES",report["H1_soft2_improves_both"],
          report["H2_adaptive_improves_both"],
          report["H3_adaptive_at_least_soft2_coverage_with_less_risk"],flush=True)
    return report


if __name__=="__main__":
    arg=argparse.ArgumentParser()
    arg.add_argument("--workspace",type=Path,required=True)
    arg.add_argument("--source",type=Path,required=True)
    arg.add_argument("--engine-js",type=Path,required=True)
    arg.add_argument("--renderer",type=Path,required=True)
    arg.add_argument("--output",type=Path,required=True)
    p=arg.parse_args()
    run(p.workspace,p.source,p.engine_js,p.renderer,p.output)
