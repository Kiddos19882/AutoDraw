#!/usr/bin/env python3
"""AWEAK2 one fixed, automatic source-Lab multiscale edge proposal.

Research-only automatic pixel-array warnings. Human A only evaluates risk,
never modifies the generated map. Neither output nor core permits any stroke.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import ndimage
from skimage import color, filters

from engine001_bpred_s4r1_generic_source_maps import (
    decode_original, generic_source_maps, original_source_region_uncertainty, git_blob_sha1,
)
from engine001_bpred_s4r1_semref1_human_review_validation import (
    SELECTED, FORBIDDEN, validated_review,
)
from run_engine001_bpred_s4r1_semref1_aqa1_uploaded_a_intake import (
    REL_A, INPUT_SHA, audit as audit_aqa1,
)
from run_engine001_bpred_s4r1_aweak1_original_region_hint_diagnostic import (
    E0_BLOB_WEAK, E0_PATH_WEAK, score_human_mark_proxies,
)
from run_engine001_bpred_s4r1_corpus_integrity import REL_CORPUS

E0_PATH = "AutoDraw_Stage20/docs/ENGINE001_BPRED001_S4R1_AWEAK2_AUTOMATIC_MULTISCALE_LAB_EDGE_PROPOSAL_PREREG_2026-11-21.md"
E0_BLOB = "80a410cb5feb45dec3f7b36b0499e71120c8c512"
VERSION = "ENGINE001_BPRED_S4R1_AWEAK2_ONE_CANDIDATE_MULTISCALE_LAB_V1"
SIGMAS = (1.0,3.0)
PERCENTILE = 90.0
NUMERICAL_ZERO_EPS = 1e-9


def ratio(a: int, b: int) -> float | None:
    return float(a/b) if b else None


def source_multiscale_lab_proposal(rgba: np.ndarray, source: dict, regions: dict) -> dict:
    """Compute only a separate proposed protected trial, never alter source."""
    if (not isinstance(rgba,np.ndarray) or rgba.dtype != np.uint8
            or rgba.ndim != 3 or rgba.shape[-1] != 4
            or not np.all(rgba[:,:,3]==255)
            or source.get("owner_status") != "MISSING"
            or regions.get("source_owner_status") != "MISSING"
            or source.get("stroke_admission") != FORBIDDEN
            or regions.get("stroke_admission") != FORBIDDEN
            or not np.array_equal(source.get("source_rgb"),rgba[:,:,:3])
            or not np.array_equal(source.get("source_alpha"),rgba[:,:,3])
            or regions.get("source_rgba_sha256") != hashlib.sha256(rgba.tobytes()).hexdigest()
            or not isinstance(source.get("protected"),np.ndarray)
            or not isinstance(source.get("unknown"),np.ndarray)
            or not isinstance(regions.get("geometric_potential_core"),np.ndarray)):
        raise ValueError("BLOCKED_AWEAK2_SOURCE_PROVENANCE_OR_OWNER")
    baseline=source["protected"]
    unknown=source["unknown"]
    core=regions["geometric_potential_core"]
    h,w=rgba.shape[:2]
    if (any(m.shape!=(h,w) or m.dtype!=bool for m in (baseline,unknown,core))
            or not np.all(baseline|unknown) or np.any(baseline & unknown)
            or np.any(core & ~unknown)
            or np.any(source["candidate_interior"])):
        raise ValueError("BLOCKED_AWEAK2_SOURCE_UNKNOWN_OR_CORE_GATE")
    before_sha=hashlib.sha256(rgba.tobytes()).hexdigest()
    lab=color.rgb2lab(rgba[:,:,:3].astype(np.float64)/255.0)
    edges=np.zeros((h,w),dtype=bool)
    scale_info=[]
    for sigma in SIGMAS:
        sm=ndimage.gaussian_filter(lab,sigma=(sigma,sigma,0),mode="reflect")
        mags=np.zeros((h,w),dtype=np.float64)
        for channel in range(3):
            gx=filters.sobel(sm[:,:,channel])
            mags+=gx*gx
        np.sqrt(mags,out=mags)
        mags=np.where(mags<=NUMERICAL_ZERO_EPS,0.0,mags)
        positive=mags[mags>0]
        if len(positive):
            threshold=float(np.percentile(positive,PERCENTILE))
            edge=mags>=threshold
        else:
            threshold=None
            edge=np.zeros((h,w),dtype=bool)
        edges|=edge
        scale_info.append({
            "sigma_source_pixels":sigma,
            "threshold_positive_magnitude_p90":threshold,
            "source_edge_pixels":int(np.count_nonzero(edge)),
        })
    warning=ndimage.binary_dilation(edges,iterations=1)
    protected_trial=baseline|warning
    core_trial=core & ~warning
    added=protected_trial & ~baseline
    if (not np.all(protected_trial|~protected_trial)
            or not np.all(protected_trial[baseline])
            or np.any(core_trial & ~core)
            or np.any(core_trial & protected_trial)
            or hashlib.sha256(rgba.tobytes()).hexdigest()!=before_sha):
        raise ValueError("BLOCKED_AWEAK2_PROPOSAL_INVARIANT")
    return {
        "version":VERSION,
        "warning":warning,
        "protected_trial":protected_trial,
        "core_trial":core_trial,
        "added":added,
        "source_rgba_sha256":before_sha,
        "scales":scale_info,
        "source_owner_status":"MISSING",
        "human_mask_used_to_generate":False,
        "stroke_admission":FORBIDDEN,
        "baseline_protected_pixels":int(np.count_nonzero(baseline)),
        "newly_protected_trial_pixels":int(np.count_nonzero(added)),
        "old_potential_core_pixels":int(np.count_nonzero(core)),
        "new_potential_core_pixels":int(np.count_nonzero(core_trial)),
        "source_pixels":h*w,
    }


def compare_with_approx_marks(a: np.ndarray, source: dict, regions: dict, trial: dict) -> dict:
    """Use A only for descriptive after-the-fact scoring, not algorithm selection."""
    old=score_human_mark_proxies(
        a,source["protected"],source["unknown"],regions["geometric_potential_core"],
        regions["region_ids"],
    )
    proposed=score_human_mark_proxies(
        a,trial["protected_trial"],~trial["protected_trial"],trial["core_trial"],
        regions["region_ids"],
    )
    m_old=old["source_label_counts"]
    m_new=proposed["source_label_counts"]
    if m_old != m_new or trial["human_mask_used_to_generate"]:
        raise ValueError("BLOCKED_AWEAK2_HUMAN_MARK_NOT_READONLY")
    k=m_old["K_critical_or_boundary"]
    i=m_old["human_visual_interior"]
    rmetrics={}
    for radius in ("0","2","5"):
        older=old["K_sensitivity_source_only"][radius]["K_near_protected"]
        newer=proposed["K_sensitivity_source_only"][radius]["K_near_protected"]
        if newer<older:
            raise ValueError("BLOCKED_AWEAK2_NONMONOTONIC_PROTECTED_TRIAL")
        rmetrics[radius]={
            "baseline_K_near":older,"trial_K_near":newer,
            "newly_near_K":newer-older,
            "baseline_K_fraction":ratio(older,k),
            "trial_K_fraction":ratio(newer,k),
            "K_fraction_gain":ratio(newer-older,k),
        }
    i_old=old["I_human_visual_interior"]
    i_new=proposed["I_human_visual_interior"]
    k_oldcore=old["K_exact_core_conflict_proxy"]
    k_newcore=proposed["K_exact_core_conflict_proxy"]
    if k_newcore>k_oldcore:
        raise ValueError("BLOCKED_AWEAK2_NONMONOTONIC_CORE_TRIAL")
    interior_added=int(np.count_nonzero(
        np.all(a == [0,255,0],axis=2) & trial["added"]
    ))
    return {
        "K_count_approx_critical_or_boundary":k,
        "I_count_human_visual_interior":i,
        "K_near_source_protected_radii":rmetrics,
        "K_exact_old_potential_core_risk_proxy":k_oldcore,
        "K_exact_trial_potential_core_risk_proxy":k_newcore,
        "K_potential_core_reduced_by_trial_proxy":k_oldcore-k_newcore,
        "I_newly_marked_protected_by_trial":interior_added,
        "I_newly_protected_fraction":ratio(interior_added,i),
        "I_old_potential_core":i_old["raw_in_potential_core_NOT_safe"],
        "I_trial_potential_core":i_new["raw_in_potential_core_NOT_safe"],
        "I_old_core_retained_fraction":ratio(
            i_new["raw_in_potential_core_NOT_safe"],
            i_old["raw_in_potential_core_NOT_safe"],
        ),
        "I_eroded2_old_potential_core":i_old["eroded2_in_potential_core_NOT_safe"],
        "I_eroded2_trial_potential_core":i_new["eroded2_in_potential_core_NOT_safe"],
        "I_eroded2_old_core_retained_fraction":ratio(
            i_new["eroded2_in_potential_core_NOT_safe"],
            i_old["eroded2_in_potential_core_NOT_safe"],
        ),
        "old_total_source_potential_core":trial["old_potential_core_pixels"],
        "trial_total_source_potential_core":trial["new_potential_core_pixels"],
        "total_source_core_retained_fraction":ratio(
            trial["new_potential_core_pixels"],trial["old_potential_core_pixels"],
        ),
        "old_source_protected":trial["baseline_protected_pixels"],
        "extra_source_protection_trial":trial["newly_protected_trial_pixels"],
        "extra_source_protection_fraction_all_pixels":ratio(
            trial["newly_protected_trial_pixels"],trial["source_pixels"],
        ),
        "human_rgb_pixel_exact_ground_truth":False,
        "game128_owner_is_known":False,
        "stroke_admission":FORBIDDEN,
    }


def run(root: Path) -> dict:
    for name,expected in ((E0_PATH,E0_BLOB),(E0_PATH_WEAK,E0_BLOB_WEAK)):
        if git_blob_sha1((root/name).read_bytes())!=expected:
            raise ValueError("BLOCKED_AWEAK2_FROZEN_E0_CHANGED "+name)
    valid=audit_aqa1(root)
    if (valid["pairs_a_checked"]!=4 or valid["pairs_b_checked"]!=0
            or valid["technical_status"]!="PASS_A_ONLY_SOURCE_AND_LABEL_INTEGRITY"):
        raise ValueError("BLOCKED_AWEAK2_EXISTING_AQA1_GATE")
    items=[]
    combined={}
    summable=("K_count_approx_critical_or_boundary","I_count_human_visual_interior",
              "I_newly_marked_protected_by_trial","I_old_potential_core",
              "I_trial_potential_core","old_total_source_potential_core",
              "trial_total_source_potential_core","old_source_protected",
              "extra_source_protection_trial","old_source_protected")
    for name in SELECTED:
        raw=(root/REL_CORPUS/name).read_bytes()
        original=decode_original(raw)
        key=hashlib.sha256(name.encode()).hexdigest()[:12]
        labels=(root/REL_A/(key+"_a.png")).read_bytes()
        meta=json.loads((root/REL_A/(key+"_a.json")).read_text(encoding="utf8"))
        reviewer,a=validated_review(original,labels,meta)
        base=generic_source_maps(original["rgba"])
        regions=original_source_region_uncertainty(original["rgba"],base)
        proposal=source_multiscale_lab_proposal(original["rgba"],base,regions)
        compare=compare_with_approx_marks(a,base,regions,proposal)
        for field in set(summable):
            combined[field]=combined.get(field,0)+compare[field]
        for r in ("0","2","5"):
            v=compare["K_near_source_protected_radii"][r]
            for k in ("baseline_K_near","trial_K_near","newly_near_K"):
                ck="r"+r+"_"+k
                combined[ck]=combined.get(ck,0)+v[k]
        combined["pixels"]=combined.get("pixels",0)+proposal["source_pixels"]
        items.append({
            "file":name, "role":"DEV",
            "source_git_blob_sha1":original["git_blob_sha1"],
            "source_raw_sha256":original["sha256"],
            "A_png_sha256":meta["labels_png_sha256"],
            "source_hw":[original["height"],original["width"]],
            "proposal_scales":proposal["scales"],
            "proposal_human_mask_used_to_generate":False,
            "source_only_comparison":compare,
        })
    k=combined["K_count_approx_critical_or_boundary"]
    for r in ("0","2","5"):
        combined["r"+r+"_K_fraction_gain"]=ratio(combined["r"+r+"_newly_near_K"],k)
        combined["r"+r+"_baseline_K_near_fraction"]=ratio(combined["r"+r+"_baseline_K_near"],k)
        combined["r"+r+"_trial_K_near_fraction"]=ratio(combined["r"+r+"_trial_K_near"],k)
    combined["I_old_potential_core_retained_fraction"]=ratio(
        combined["I_trial_potential_core"],combined["I_old_potential_core"])
    combined["total_source_old_core_retained_fraction"]=ratio(
        combined["trial_total_source_potential_core"],combined["old_total_source_potential_core"])
    combined["extra_source_protection_fraction_all_pixels"]=ratio(
        combined["extra_source_protection_trial"],combined["pixels"])
    return {
        "version":VERSION,"frozen_E0_git_blob":E0_BLOB,
        "baseline_code_SHA":"a74c95e97c294323f43dd4b9029c865f25befcef",
        "input_A_git_commit":INPUT_SHA,
        "four_DEV_real_A_approximations":len(items),
        "single_candidate_scales_source_px":[1.0,3.0],
        "human_marks_only_evaluation_not_generator":True,
        "trial_protected_not_production":True,
        "exact_game_owner":"MISSING",
        "original_RGB_mutated":False,
        "quality_gates_modified":False,
        "technical_status":"E2_SOURCE_ONLY_CANDIDATE_COMPARISON",
        "science_status":"EXPLORATORY_NO_INDEPENDENT_SEMANTIC_OR_NATIVE_GT",
        "strict_S4":"BLOCKED",
        "stroke_admission":FORBIDDEN,
        "native_E3":"NOT_RUN","game_E4":"NOT_RUN",
        "independent_E5":"NOT_RUN","exact_CHALK":None,
        "heldout_outputs":0,
        "aggregate_four_DEV":combined,
        "per_original":items,
    }


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True,type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    obj=run(args.root)
    payload=json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    if args.out:args.out.write_text(payload,encoding="utf8")
    print(payload)
