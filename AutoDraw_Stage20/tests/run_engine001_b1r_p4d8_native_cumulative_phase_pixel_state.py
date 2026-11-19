#!/usr/bin/env python3
"""P4D8: true Egret cumulative 0/1 owner-safe phase composition (research only).

Re-measure P4D7 21*66 genuine native isolated cases unchanged, then
evaluate the resulting safe phase candidates as whole-board cumulative
Egret scenes. Never translate an already-rendered footprint.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d5_pixel_state_native_feedback as p4d5
import run_engine001_b1r_p4d7_native_width1_phase_feasibility as p4d7
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D8_NATIVE_CUMULATIVE_PHASE_OWNER_PIXEL_V1"
PREREG="ENGINE001_B1R_P4D8_NATIVE_CUMULATIVE_PHASE_PIXEL_STATE_PREREG_2026-11-19.md"
SOURCE=p4d7.SOURCE
CROP=p4d7.CROP
METHODS=p4d7.METHODS
WHITE=p4d7.WHITE
ALPHA=p4d7.ALPHA
BOARD_SHAPE=p4d5.BOARD_SHAPE
SCALE=p4d5.SCALE
EXPECTED_SAMPLES=21
EXPECTED_ISOLATED=21*66


def rank_candidate(row:dict)->tuple:
    """Deterministic tie-break; isolated native measurements, not a model."""
    m=row["measured"]
    return (-int(m["native_other_correct_logical_in_crop"]),
            int(m["native_alpha1_genuine_foreign_backing"]),
            str(row["sample_id"]),str(row["variant"]))


def eligible_rows(rows:list[dict],sample_ids:set[str])->list[dict]:
    """Only source-bound P4D7 native actually safe and correct cases."""
    accepted=[]
    for row in rows:
        if row["sample_id"] not in sample_ids:
            raise ValueError("BLOCKED_P4D8_UNKNOWN_SAMPLE")
        if row["variant"] not in {v[0] for v in p4d7.VARIANTS}:
            raise ValueError("BLOCKED_P4D8_UNREGISTERED_PHASE")
        if row["width"]!=1:
            raise ValueError("BLOCKED_P4D8_NOT_WIDTH1")
        if row["measured"]["phase_feasible"]:
            if (not row["measured"]["native_exact_sample_cell_correct_5of9"] or
                row["measured"]["native_alpha24_genuine_foreign_backing"]!=0):
                raise ValueError("BLOCKED_P4D8_INCONSISTENT_SINGLE_NATIVE")
            accepted.append(row)
    return sorted(accepted,key=rank_candidate)


def trial_metrics(before:np.ndarray,after:np.ndarray,
                  index:np.ndarray,palette:np.ndarray,
                  current_state:np.ndarray,sample:dict)->dict:
    """Full native RGBA delta and freshly measured state, no alpha union model."""
    if (before.shape!=BOARD_SHAPE or after.shape!=BOARD_SHAPE or
        before.dtype!=np.uint8 or after.dtype!=np.uint8 or
        index.shape!=(240,150) or palette.shape!=(128,3) or
        current_state.shape!=index.shape):
        raise ValueError("BLOCKED_P4D8_NATIVE_OR_SOURCE_FORMAT")
    owner=int(sample["owner"])
    if int(index[sample["y"],sample["x"]])!=owner or owner==WHITE:
        raise ValueError("BLOCKED_P4D8_UNMATCHED_SOURCE_OWNER")
    target=p4d5.crop_target(index)
    after_state=p4d5.actual_state(after,index,palette)
    gain=int((target & ~current_state & after_state).sum())
    lost=int((target & current_state & ~after_state).sum())
    source_owner_full=p4d7.full_backing_source_mask(index==owner)
    source_white_full=p4d7.full_backing_source_mask(index==WHITE)
    changed=np.any(before!=after,axis=2)
    new_ink=after[:,:,3]>=ALPHA
    foreign_delta=changed & new_ink & ~source_owner_full
    low_alpha_foreign_delta=changed & (after[:,:,3]>0) & ~source_owner_full
    all_white=new_ink & source_white_full
    sample_was_correct=bool(current_state[sample["y"],sample["x"]])
    sample_now_correct=bool(after_state[sample["y"],sample["x"]])
    accepted=bool(not sample_was_correct and sample_now_correct and
                  gain>0 and lost==0 and not foreign_delta.any()
                  and not all_white.any())
    return {
        "native_new_correct_0_to_1":gain,
        "native_lost_correct_1_to_0":lost,
        "net_correct_delta":gain-lost,
        "target_sample_before":sample_was_correct,
        "target_sample_after":sample_now_correct,
        "native_changed_foreign_alpha24_backing":int(foreign_delta.sum()),
        "native_changed_foreign_alpha1_backing":int(low_alpha_foreign_delta.sum()),
        "native_original_white_alpha24_backing":int(all_white.sum()),
        "total_correct_after":int(after_state.sum()),
        "accepted":accepted,
    }


def compare_native(original:np.ndarray,index:np.ndarray,
                   palette:np.ndarray,native:np.ndarray,
                   state:np.ndarray,output:Path)->None:
    x0,y0,x1,y1=CROP
    original_card=Image.fromarray(original[y0:y1,x0:x1]).resize(
        (288,288),Image.Resampling.NEAREST)
    palette_card=Image.fromarray(palette[index[y0:y1,x0:x1]]).resize(
        (288,288),Image.Resampling.NEAREST)
    observed=p4d5.real_composite_rgb(native)
    native_card=Image.fromarray(
        observed[y0*SCALE:y1*SCALE,
                 (p4d5.X0+x0)*SCALE:(p4d5.X0+x1)*SCALE]).resize(
                     (288,288),Image.Resampling.NEAREST)
    crop_state=state[y0:y1,x0:x1]
    crop_target=p4d5.crop_target(index)[y0:y1,x0:x1]
    diagnostic=np.full((24,24,3),255,np.uint8)
    diagnostic[crop_target]=(205,76,76)  # not correct
    diagnostic[crop_state]=(49,148,92)   # correct
    state_card=Image.fromarray(diagnostic).resize(
        (288,288),Image.Resampling.NEAREST)
    panel=Image.new("RGB",(1152,312),"white")
    drawer=ImageDraw.Draw(panel)
    for i,(label,card) in enumerate((
        ("ORIGINAL RGB",original_card),("ORIGINAL B1-R OWNER COLORS",palette_card),
        ("ACTUAL CUMULATIVE EGRET",native_card),("ACTUAL 0/1: GREEN CORRECT",state_card)
    )):
        panel.paste(card,(i*288,24))
        drawer.text((i*288+6,5),label,fill=(0,0,0))
    panel.save(output/"P4D8_ACTUAL_NATIVE_ROI_COMPARISON.png")


def run(workspace:Path,source:Path,engine_js:Path,
        renderer:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D8_EVIDENCE_EXISTS")
    check_source(source)
    if (p4d5.p4b1.git_blob(renderer.read_bytes())!=p4d5.p4d0.RENDERER_BLOB or
        p4d5.p4b1.git_blob(engine_js.read_bytes())!=p3b.ENGINE_GIT_BLOB_SHA1):
        raise ValueError("BLOCKED_P4D8_EGRET_OR_PALETTE_DRIFT")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
        raise ValueError("BLOCKED_P4D8_NOT_PREREGISTERED")
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D8: повторно нативно измеренные P4D7 фазы, затем каждый trial это "
        "ПОЛНАЯ реальная Egret BoardPane сцена. Состояния 0/1 из настоящего "
        "composite, no new source-foreign alpha24, no original-white alpha24, "
        "no 1->0, сохраняются неуспешные попытки. Только 21 фиксированный "
        "sample женского лица; не full image/E4/CHALK/production.\n","utf8")
    # The previous protocol and renderer are reused without rewriting P4D7.
    isolated_dir=output/"P4D7_FRESH_NATIVE_ISOLATED"
    isolated=p4d7.run(workspace,source,engine_js,renderer,isolated_dir)
    if (isolated["experiment"]!=p4d7.EXPERIMENT or
        isolated["native_scene_capture_total"]!=EXPECTED_ISOLATED+1 or
        isolated["samples"]!=EXPECTED_SAMPLES or
        isolated["safe_and_correct_samples"]!=EXPECTED_SAMPLES or
        not isolated["original_EF_frozen_ROI_index_exact_identical"]):
        raise ValueError("BLOCKED_P4D8_REMEASURED_P4D7_DRIFT")
    rows=[json.loads(line) for line in
          (isolated_dir/"NATIVE_PHASE_RESULTS_APPEND_ONLY.jsonl").read_text(
              "utf8").splitlines() if line.strip()]
    samples=json.loads((isolated_dir/"FIXED_ORIGINAL_SOURCE_SAMPLES.json").read_text("utf8"))
    if (len(rows)!=EXPECTED_ISOLATED or len(samples)!=EXPECTED_SAMPLES or
        {r["sample_id"] for r in samples}!={r["sample_id"] for r in rows}):
        raise ValueError("BLOCKED_P4D8_ISOLATED_EVIDENCE_INCOMPLETE")
    sample_map={s["sample_id"]:s for s in samples}
    valid=eligible_rows(rows,set(sample_map))
    if not valid:
        raise ValueError("BLOCKED_P4D8_NO_SAFE_ISOLATED_STROKES")
    variants={variant[0]:variant for variant in p4d7.VARIANTS}
    palette,_=p3b.read_engine_palette(engine_js)
    with tempfile.TemporaryDirectory(prefix="engine001-p4d8-original-") as tmp:
        fresh=Path(tmp)/"fresh_p3d"
        parent=p3d.run(source,engine_js,fresh)
        if (parent["experiment"]!=p3d.EXPERIMENT or
            parent["original_source_sha256"]!=p4d5.SOURCE_SHA or
            not parent["P3B_original_recomputed_in_current_run"] or
            parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D8_NOT_ORIGINAL_B1R_SOURCE")
        index={}
        for method in METHODS:
            ix=np.asarray(Image.open(
                fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),np.uint8).copy()
            selection=parent["all_results"][SOURCE]["selected_engine_indices"]
            p4c0.validate_source(ix,palette,selection)
            index[method]=ix
        x0,y0,x1,y1=CROP
        if not np.array_equal(index[METHODS[0]][y0:y1,x0:x1],
                              index[METHODS[1]][y0:y1,x0:x1]):
            raise ValueError("BLOCKED_P4D8_EF_ROI_NOT_IDENTICAL")
        original=np.asarray(Image.open(
            fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"),np.uint8)
        target_index=index[METHODS[0]]
        if (int(p4d5.crop_target(target_index).sum())!=307 or
            len({int(target_index[s["y"],s["x"]]) for s in samples})!=20):
            raise ValueError("BLOCKED_P4D8_TARGET_SOURCE_DRIFT")
        if p4d7.owner_samples(target_index)!=samples:
            raise ValueError("BLOCKED_P4D8_SAMPLE_SELECTION_DRIFT")
        trial_dir=output/"REAL_EGRET_CUMULATIVE_TRIALS"
        trial_dir.mkdir()
        state=np.zeros((240,150),bool)
        accepted=[]
        strokes=[]
        events=[]
        used=set()
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(240)
            current,blank_meta=p4d5._native(
                driver,output,"REAL_EGRET_CUMULATIVE_BLANK",[])
            if np.any(current[:,:,3]) or state.any():
                raise ValueError("BLOCKED_P4D8_BLANK_NONZERO")
            ledger=output/"NATIVE_CUMULATIVE_TRIALS_APPEND_ONLY.jsonl"
            with ledger.open("a",encoding="utf8") as stream:
                while True:
                    possibilities=[
                        row for row in valid
                        if (row["sample_id"],row["variant"]) not in used and
                        not state[sample_map[row["sample_id"]]["y"],
                                  sample_map[row["sample_id"]]["x"]]
                    ]
                    if not possibilities:
                        break
                    row=possibilities[0]  # valid already sorted
                    sample=sample_map[row["sample_id"]]
                    key=(row["sample_id"],row["variant"])
                    used.add(key)
                    stroke=p4d7.phase_stroke(sample,variants[row["variant"]],palette)
                    if (stroke["colorIndex"]!=int(row["colorIndex"]) or
                        stroke["points"]!=row["points"] or stroke["width"]!=1):
                        raise ValueError("BLOCKED_P4D8_ISOLATED_STROKE_PROVENANCE")
                    i=len(events)+1
                    trial,meta=p4d5._native(driver,trial_dir,
                        f"TRIAL_{i:04d}_{sample['sample_id']}_{row['variant']}",
                        strokes+[stroke])
                    measured=trial_metrics(
                        current,trial,target_index,palette,state,sample)
                    event={
                        "trial":i,"sample_id":row["sample_id"],"variant":row["variant"],
                        "colorIndex":stroke["colorIndex"],"colorRgb":stroke["colorRgb"],
                        "stroke_points_exact":stroke["points"],"width":1,
                        "isolated_native_sha256":row["native_png_sha256"],
                        "real_cumulative_native_sha256":meta["source_sha256"],
                        "same_real_renderer":meta["renderer"],
                        **measured,
                    }
                    if measured["accepted"]:
                        accepted.append(event)
                        strokes.append(stroke)
                        current=trial
                        state=p4d5.actual_state(current,target_index,palette)
                    events.append(event)
                    stream.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+"\n")
                    stream.flush()
                    if i%5==0:
                        print("P4D8_CUMULATIVE_TRIALS",i,"accepted",len(accepted),
                              "correct",int(state.sum()),flush=True)
            replay,meta=p4d5._native(
                driver,output,"REAL_EGRET_FINAL_REPLAY",strokes)
            if not np.array_equal(current,replay):
                raise ValueError("BLOCKED_P4D8_FINAL_NATIVE_REPLAY_DIFFERS")
        if any((ev["native_lost_correct_1_to_0"] or
                ev["native_changed_foreign_alpha24_backing"] or
                ev["native_original_white_alpha24_backing"])
               for ev in accepted):
            raise ValueError("BLOCKED_P4D8_ACCEPTED_SOURCE_DAMAGE")
        final_score=p4d5.roi_metrics(current,target_index,palette)
        final_sample_hits=sum(bool(state[s["y"],s["x"]]) for s in samples)
        compare_native(original,target_index,palette,current,state,output)
        result={
            "experiment":EXPERIMENT,
            "technical_result":"REAL_EGRET_P4D7_ISOLATED_PLUS_P4D8_CUMULATIVE",
            "original_source_sha256":p4d5.SOURCE_SHA,
            "fresh_original_B1R_P3D":True,
            "P4D7_fresh_native_isolated_experiment":isolated["experiment"],
            "P4D7_fresh_native_isolated_scene_count":EXPECTED_ISOLATED+1,
            "P4D7_fresh_safe_sample_count":isolated["safe_and_correct_samples"],
            "selected_source":SOURCE,"method":METHODS[0],
            "original_EF_source_crop_duplicate":True,"crop_xyxy":list(CROP),
            "fixed_samples":EXPECTED_SAMPLES,"target_nonwhite":307,
            "isolated_total_variants":len(rows),"isolated_safe_variants":len(valid),
            "real_native_cumulative_trial_count":len(events),
            "real_native_cumulative_accepted":len(accepted),
            "real_native_cumulative_rejected":len(events)-len(accepted),
            "final_accepted_sample_correct_out_of_21":final_sample_hits,
            "final_owner_correct_out_of_307":int(final_score["correct_logical_native_5_of_9"]),
            "final_remaining_source_zeros":int(final_score["remaining_zero_logical"]),
            "P4D5_historical_native_baseline_correct_out_of_307":10,
            "P4D6_historical_native_baseline_correct_out_of_307":1,
            "H1_more_covered_than_P4D5_with_protected_safety":
                int(final_score["correct_logical_native_5_of_9"])>10,
            "H2_all_21_fixed_samples_correct":final_sample_hits==21,
            "accepted_real_native_all_foreign_alpha24_change_zero":
                all(ev["native_changed_foreign_alpha24_backing"]==0
                    for ev in accepted),
            "accepted_no_1_to_0":all(ev["native_lost_correct_1_to_0"]==0
                                    for ev in accepted),
            "accepted_original_white_native_alpha24_zero":
                all(ev["native_original_white_alpha24_backing"]==0
                    for ev in accepted),
            "final_native_replay_rgba_exact":True,
            "final_source_white_alpha24_backing":
                final_score["white_target_ink_alpha24_backing"],
            "final_crop_outside_ink_alpha24_backing":
                final_score["any_ink_outside_crop_alpha24_backing"],
            "final_score":final_score,
            "real_native_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
            "game_bundle_git_blob":p3b.ENGINE_GIT_BLOB_SHA1,
            "renderer_git_blob":p4d5.p4d0.RENDERER_BLOB,
            "no_production_or_global_dark_contour":True,
            "full_art_owners99_protected0_far3":"NOT_MEASURED",
            "E4_live":"NOT_RUN","E5_independent":"NOT_RUN",
            "exact_run_bound_CHALK":None,"production_promotion":False,
            "github_sha":os.getenv("GITHUB_SHA"),
            "github_run_id":os.getenv("GITHUB_RUN_ID"),
        }
        result["members_sha256"]={
            str(path.relative_to(output)).replace("\\","/"):digest(path.read_bytes())
            for path in sorted(output.rglob("*")) if path.is_file()
        }
        (output/"report.json").write_text(json.dumps(
            result,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
        print("P4D8_NATIVE_CUMULATIVE_FINAL",final_sample_hits,"of21 samples",
              int(state.sum()),"of307 source pixels","accepted",len(accepted),
              "attempts",len(events),"H1",result["H1_more_covered_than_P4D5_with_protected_safety"],
              "H2",result["H2_all_21_fixed_samples_correct"],flush=True)
        return result


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--workspace",type=Path,required=True)
    cli.add_argument("--source",type=Path,required=True)
    cli.add_argument("--engine-js",type=Path,required=True)
    cli.add_argument("--renderer",type=Path,required=True)
    cli.add_argument("--output",type=Path,required=True)
    args=cli.parse_args()
    run(args.workspace,args.source,args.engine_js,args.renderer,args.output)
