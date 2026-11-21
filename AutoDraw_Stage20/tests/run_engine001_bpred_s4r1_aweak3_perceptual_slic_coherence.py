#!/usr/bin/env python3
"""One AWEAK3 research-only original RGB perceptual-SLIC boundary coherence trial.

Output is a purely hypothetical geometric region diagnostic, never actual
source game128 owner or native brush stroke admission. User hand labels are
consulted only after the automatic proposal is already built.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import ndimage
from skimage import color

from engine001_bpred_s4r1_generic_source_maps import (
    DELTA_E_STRONG, decode_original, generic_source_maps, git_blob_sha1,
    original_source_region_uncertainty,
)
from engine001_bpred_s4r1_semref1_human_review_validation import (
    CODES, E0_BLOB, E0_PATH as SEMREF_E0, FORBIDDEN, SELECTED,
    validated_review,
)
from run_engine001_bpred_s4r1_aweak1_original_region_hint_diagnostic import (
    E0_BLOB_WEAK, E0_PATH_WEAK,
)
from run_engine001_bpred_s4r1_aweak2_multiscale_lab_source_proposal import (
    E0_BLOB as E0_BLOB2, E0_PATH as E0_PATH2,
)
from run_engine001_bpred_s4r1_semref1_aqa1_uploaded_a_intake import (
    INPUT_SHA, REL_A, audit as audit_aqa1,
)
from run_engine001_bpred_s4r1_corpus_integrity import REL_CORPUS

E0_PATH3 = (
    "AutoDraw_Stage20/docs/"
    "ENGINE001_BPRED001_S4R1_AWEAK3_PERCEPTUAL_SLIC_COHERENCE_PREREG_2026-11-21.md"
)
E0_BLOB3 = "0d899b80415967315f1a87219428a4a867af2adf"
VERSION = "ENGINE001_BPRED_S4R1_AWEAK3_ONE_PERCEPTUAL_SLIC_V1"


def frac(a: int, n: int) -> float | None:
    return float(a/n) if n else None


def coherence_trial(rgba: np.ndarray, source: dict, regions: dict) -> dict:
    """Discard ONLY visually weak SLIC-only boundaries, leave original protection.

    Pair Lab comparison is between actual-original P2 region medoids, never
    between arbitrary PNG pixel RGB values or 128-game owner colors.
    """
    if (not isinstance(rgba, np.ndarray) or rgba.dtype != np.uint8
            or rgba.ndim != 3 or rgba.shape[2] != 4
            or not np.all(rgba[:, :, 3] == 255)
            or source.get("owner_status") != "MISSING"
            or regions.get("source_owner_status") != "MISSING"
            or source.get("stroke_admission") != FORBIDDEN
            or regions.get("stroke_admission") != FORBIDDEN
            or not np.array_equal(source.get("source_rgb"), rgba[:, :, :3])
            or not np.array_equal(source.get("source_alpha"), rgba[:, :, 3])
            or regions.get("source_rgba_sha256") != hashlib.sha256(rgba.tobytes()).hexdigest()):
        raise ValueError("BLOCKED_AWEAK3_INVALID_ORIGINAL_PROVENANCE")
    h, w = rgba.shape[:2]
    protected = source.get("protected")
    unknown = source.get("unknown")
    exact_white = source.get("exact_white_evidence")
    source_edge = source.get("source_edge")
    labels = regions.get("region_ids")
    old_region_border = regions.get("region_boundary")
    region_disagree = regions.get("region_color_uncertain")
    old_warning = regions.get("source_region_warning")
    old_core = regions.get("geometric_potential_core")
    masks = (protected,unknown,exact_white,source_edge,old_region_border,
             region_disagree,old_warning,old_core)
    if (any(not isinstance(m, np.ndarray) or m.shape != (h,w) or m.dtype != bool
            for m in masks)
            or not isinstance(labels,np.ndarray) or labels.shape != (h,w)
            or not np.issubdtype(labels.dtype,np.integer)
            or labels.min() < 1
            or np.any(protected & unknown)
            or not np.all(protected | unknown)
            or np.any(source["candidate_interior"])
            or np.any(old_core & ~unknown)
            or not isinstance(regions.get("representatives"),list)):
        raise ValueError("BLOCKED_AWEAK3_SOURCE_UNKNOWN_OR_REGION_MAP")

    maxid = int(labels.max())
    representatives = regions["representatives"]
    if len(representatives) != maxid or maxid > 2048:
        raise ValueError("BLOCKED_AWEAK3_MEDOID_ID_COUNT")
    medoid_rgb = np.empty((maxid+1,3),np.uint8)
    medoid_rgb[0,:]=0
    for i, representative in enumerate(representatives, start=1):
        if (representative.get("region_id") != i
                or len(representative.get("source_rgb",[])) != 3):
            raise ValueError("BLOCKED_AWEAK3_REGION_MEDOID_INVALID")
        rgb = np.asarray(representative["source_rgb"],dtype=np.int64)
        if np.any(rgb<0) or np.any(rgb>255):
            raise ValueError("BLOCKED_AWEAK3_REGION_MEDOID_RANGE")
        medoid_rgb[i] = rgb.astype(np.uint8)

    # Vectorize only 4-neighbor boundary pairs; compute each unique pair's
    # source-medoid Delta E once. No human masks enter this calculation.
    base=maxid+1
    pair_arrays=[]
    rebuilt_border = np.zeros((h,w),bool)
    for axis in (0,1):
        if rgba.shape[axis] < 2:
            continue
        first, second = ((labels[:-1],labels[1:]) if axis==0
                         else (labels[:,:-1],labels[:,1:]))
        changed = first != second
        if axis==0:
            rebuilt_border[:-1] |= changed
            rebuilt_border[1:] |= changed
        else:
            rebuilt_border[:,:-1] |= changed
            rebuilt_border[:,1:] |= changed
        codes = np.minimum(first[changed],second[changed]).astype(np.int64)*base + (
            np.maximum(first[changed],second[changed]).astype(np.int64))
        pair_arrays.append(codes)
    if not np.array_equal(rebuilt_border,old_region_border):
        raise ValueError("BLOCKED_AWEAK3_P2_SOURCE_BORDER_MISMATCH")
    if not np.array_equal((source_edge | old_region_border | region_disagree),old_warning):
        raise ValueError("BLOCKED_AWEAK3_P2_REGION_WARNING_MISMATCH")
    old_band=ndimage.binary_dilation(old_warning,iterations=1)
    if not np.array_equal(old_core,~protected & ~old_band & ~exact_white):
        raise ValueError("BLOCKED_AWEAK3_P2_GEOMETRIC_CORE_MISMATCH")
    if pair_arrays:
        unique_pairs=np.unique(np.concatenate(pair_arrays))
    else:
        unique_pairs=np.empty(0,dtype=np.int64)
    left=unique_pairs // base
    right=unique_pairs % base
    if unique_pairs.size:
        medoid_lab=color.rgb2lab(medoid_rgb[1:].astype(np.float64).reshape(1,-1,3)/255.0).reshape(-1,3)
        pair_delta=color.deltaE_ciede2000(medoid_lab[left-1],medoid_lab[right-1])
        if not np.all(np.isfinite(pair_delta)):
            raise ValueError("BLOCKED_AWEAK3_NONFINITE_PERCEPTUAL_DELTA")
        strong=pair_delta >= DELTA_E_STRONG
    else:
        strong=np.empty(0,bool)
    strong_border=np.zeros((h,w),bool)
    for axis,codes in enumerate(pair_arrays):
        if not len(codes):
            continue
        first, second = ((labels[:-1],labels[1:]) if axis==0
                         else (labels[:,:-1],labels[:,1:]))
        changed=first!=second
        pair_idx=np.searchsorted(unique_pairs,codes)
        if np.any(pair_idx>=len(unique_pairs)) or np.any(unique_pairs[pair_idx]!=codes):
            raise ValueError("BLOCKED_AWEAK3_REGION_PAIR_LOOKUP")
        strong_mask=np.zeros(changed.shape,bool)
        strong_mask[changed]=strong[pair_idx]
        if axis==0:
            strong_border[:-1] |= strong_mask
            strong_border[1:] |= strong_mask
        else:
            strong_border[:,:-1] |= strong_mask
            strong_border[:,1:] |= strong_mask
    retained_warning=source_edge | region_disagree | strong_border
    band=ndimage.binary_dilation(retained_warning,iterations=1)
    trial_core=~protected & ~band & ~exact_white
    added=trial_core & ~old_core
    if (np.any(old_core & ~trial_core) or np.any(trial_core & protected)
            or np.any(trial_core & ~unknown)
            or np.any(trial_core & source_edge)
            or np.any(trial_core & region_disagree)
            or np.any(strong_border & ~old_region_border)):
        raise ValueError("BLOCKED_AWEAK3_TRIAL_CORE_INVARIANT")
    return {
        "version":VERSION,
        "trial_core":trial_core,
        "newly_unexcluded_core":added,
        "strong_border":strong_border,
        "source_rgba_sha256":hashlib.sha256(rgba.tobytes()).hexdigest(),
        "region_pair_count":int(unique_pairs.size),
        "weak_region_pair_count":int(np.count_nonzero(~strong)),
        "strong_region_pair_count":int(np.count_nonzero(strong)),
        "original_slic_border_pixels":int(np.count_nonzero(old_region_border)),
        "strong_border_pixels":int(np.count_nonzero(strong_border)),
        "existing_source_protected_pixels":int(np.count_nonzero(protected)),
        "original_slic_core_pixels":int(np.count_nonzero(old_core)),
        "trial_core_pixels":int(np.count_nonzero(trial_core)),
        "newly_unexcluded_core_pixels":int(np.count_nonzero(added)),
        "total_source_pixels":h*w,
        "human_mark_input_to_generator":False,
        "owner_status":"MISSING",
        "stroke_admission":FORBIDDEN,
    }


def compare_weak_mark_tradeoff(labels_a: np.ndarray, regions: dict, trial: dict) -> dict:
    """Human marks are imperfect hints to evaluate tradeoffs, never pixel truth."""
    if not isinstance(labels_a,np.ndarray) or labels_a.ndim!=3 or labels_a.shape[2]!=3 or labels_a.dtype!=np.uint8:
        raise ValueError("BLOCKED_AWEAK3_INVALID_A_REVIEW_RGB")
    old=regions["geometric_potential_core"]
    new=trial["trial_core"]
    if old.shape!=labels_a.shape[:2] or trial["human_mark_input_to_generator"]:
        raise ValueError("BLOCKED_AWEAK3_A_LABELS_IN_GENERATOR")
    marked=[np.all(labels_a==col,axis=2) for col in CODES]
    if not np.all(np.logical_or.reduce(marked)):
        raise ValueError("BLOCKED_AWEAK3_INVALID_A_REVIEW_CODE")
    K=marked[1] | marked[2]
    I=marked[3]
    nK=int(np.count_nonzero(K))
    nI=int(np.count_nonzero(I))
    if nK == 0 or nI == 0:
        raise ValueError("BLOCKED_AWEAK3_NO_HUMAN_VISUAL_SUPPORT")
    Iinner=ndimage.binary_erosion(I,structure=np.ones((5,5),bool))
    new_border=ndimage.binary_dilation(new,iterations=2)
    old_border=ndimage.binary_dilation(old,iterations=2)
    stats={
        "K_visual_marked_pixels":nK,
        "I_visual_marked_pixels":nI,
        "I_eroded2_visual_pixels":int(np.count_nonzero(Iinner)),
        "K_old_core_overlap_proxy":int(np.count_nonzero(K & old)),
        "K_trial_core_overlap_proxy":int(np.count_nonzero(K & new)),
        "K_newly_in_core_warning":int(np.count_nonzero(K & trial["newly_unexcluded_core"])),
        "K_old_within2_of_core_proxy":int(np.count_nonzero(K & old_border)),
        "K_trial_within2_of_core_proxy":int(np.count_nonzero(K & new_border)),
        "I_old_core_overlap_proxy":int(np.count_nonzero(I & old)),
        "I_trial_core_overlap_proxy":int(np.count_nonzero(I & new)),
        "I_newly_in_core_proxy":int(np.count_nonzero(I & trial["newly_unexcluded_core"])),
        "I_eroded2_old_core_overlap_proxy":int(np.count_nonzero(Iinner & old)),
        "I_eroded2_trial_core_overlap_proxy":int(np.count_nonzero(Iinner & new)),
        "total_old_core":trial["original_slic_core_pixels"],
        "total_trial_core":trial["trial_core_pixels"],
        "newly_hypothetical_core":trial["newly_unexcluded_core_pixels"],
    }
    stats["I_relative_old_core_gain"]=frac(stats["I_newly_in_core_proxy"],stats["I_old_core_overlap_proxy"])
    stats["K_new_core_warning_fraction_of_K"]=frac(stats["K_newly_in_core_warning"],nK)
    stats["I_eroded2_relative_gain"]=frac(
        stats["I_eroded2_trial_core_overlap_proxy"]-stats["I_eroded2_old_core_overlap_proxy"],
        stats["I_eroded2_old_core_overlap_proxy"])
    stats["K_new_near2_core_warning_fraction_of_K"]=frac(
        stats["K_trial_within2_of_core_proxy"]-stats["K_old_within2_of_core_proxy"],nK)
    stats["source_owner_accuracy"]="UNKNOWN"
    stats["human_rgb_equality_assumed"]=False
    stats["stroke_admission"]=FORBIDDEN
    return stats


def run(root: Path) -> dict:
    for p,expected in ((E0_PATH3,E0_BLOB3),(E0_PATH_WEAK,E0_BLOB_WEAK),
                       (E0_PATH2,E0_BLOB2),(SEMREF_E0,E0_BLOB)):
        if git_blob_sha1((root/p).read_bytes())!=expected:
            raise ValueError("BLOCKED_AWEAK3_FROZEN_E0_DRIFT "+p)
    aqa=audit_aqa1(root)
    if (aqa["pairs_a_checked"]!=4 or aqa["pairs_b_checked"]!=0
            or aqa["technical_status"]!="PASS_A_ONLY_SOURCE_AND_LABEL_INTEGRITY"):
        raise ValueError("BLOCKED_AWEAK3_ACTUAL_A_PROVENANCE")
    reports=[]
    pooled={}
    count_keys=("K_visual_marked_pixels","I_visual_marked_pixels",
                "K_old_core_overlap_proxy","K_trial_core_overlap_proxy",
                "K_newly_in_core_warning","K_old_within2_of_core_proxy",
                "K_trial_within2_of_core_proxy","I_old_core_overlap_proxy",
                "I_trial_core_overlap_proxy","I_newly_in_core_proxy",
                "I_eroded2_old_core_overlap_proxy","I_eroded2_trial_core_overlap_proxy",
                "total_old_core","total_trial_core","newly_hypothetical_core")
    for name in SELECTED:
        original=decode_original((root/REL_CORPUS/name).read_bytes())
        source=generic_source_maps(original["rgba"])
        region=original_source_region_uncertainty(original["rgba"],source)
        candidate=coherence_trial(original["rgba"],source,region)
        key=hashlib.sha256(name.encode()).hexdigest()[:12]
        png=(root/REL_A/(key+"_a.png")).read_bytes()
        meta=json.loads((root/REL_A/(key+"_a.json")).read_text(encoding="utf-8"))
        _,A=validated_review(original,png,meta)
        scores=compare_weak_mark_tradeoff(A,region,candidate)
        for count in count_keys:
            pooled[count]=pooled.get(count,0)+scores[count]
        for count in ("region_pair_count","weak_region_pair_count","strong_region_pair_count",
                      "original_slic_border_pixels","strong_border_pixels","existing_source_protected_pixels",
                      "total_source_pixels"):
            pooled[count]=pooled.get(count,0)+candidate[count]
        reports.append({
            "file":name,"source_role":"DEV","source_hw":[original["height"],original["width"]],
            "source_git_blob_sha1":original["git_blob_sha1"],
            "source_sha256":original["sha256"],
            "A_png_sha256":meta["labels_png_sha256"],
            "region_slic_version":region["version"],
            "candidate_automatic":{
                k:v for k,v in candidate.items()
                if not isinstance(v,np.ndarray)
            },
            "human_weak_visual_evaluation":scores,
        })
    pooled["K_new_core_warning_fraction_of_K"]=frac(
        pooled["K_newly_in_core_warning"],pooled["K_visual_marked_pixels"])
    pooled["I_relative_old_core_gain"]=frac(
        pooled["I_newly_in_core_proxy"],pooled["I_old_core_overlap_proxy"])
    pooled["I_eroded2_relative_gain"]=frac(
        pooled["I_eroded2_trial_core_overlap_proxy"]-pooled["I_eroded2_old_core_overlap_proxy"],
        pooled["I_eroded2_old_core_overlap_proxy"])
    pooled["K_new_near2_core_warning_fraction_of_K"]=frac(
        pooled["K_trial_within2_of_core_proxy"]-pooled["K_old_within2_of_core_proxy"],
        pooled["K_visual_marked_pixels"])
    pooled["total_core_relative_gain"]=frac(
        pooled["newly_hypothetical_core"],pooled["total_old_core"])
    return {
        "version":VERSION,"frozen_AWEAK3_E0_blob":E0_BLOB3,
        "baseline_HEAD":"5b8638bda7298140a4aba0a59c32cd5ec48e4dd5",
        "real_original_A_input_commit":INPUT_SHA,
        "tested_DEV_count":len(reports),"holdout_used":0,
        "human_annotations_for_scoring_only":True,"per_image_RGB_exact_equality_required":False,
        "trial_core_is_safe":False,"old_protection_unmodified":True,
        "strict_S4":"BLOCKED","stroke_admission":FORBIDDEN,
        "source_owner":"MISSING","technical_status":"E2_SOURCE_ONLY_RESEARCH",
        "native_E3":"NOT_RUN","game_E4":"NOT_RUN","independent_E5":"NOT_RUN",
        "exact_CHALK":None,"S5_S6":"NOT_RUN",
        "pooled_four_DEV":pooled,"per_original":reports,
    }


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--root",required=True,type=Path)
    cli.add_argument("--output",type=Path)
    args=cli.parse_args()
    result=run(args.root)
    output=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    if args.output:args.output.write_text(output,encoding="utf8")
    print(output)
