#!/usr/bin/env python3
"""AWEAK1: frozen human-A source-mark approximations vs existing math source maps.

Research-only. No RGB exact ground truth, no owner or native stroke permission.
A-only markers are approximate human points/brush areas, not pixel-accurate GT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import ndimage

from engine001_bpred_s4r1_generic_source_maps import (
    decode_original, generic_source_maps, original_source_region_uncertainty,
    git_blob_sha1,
)
from engine001_bpred_s4r1_semref1_human_review_validation import (
    CODES, E0_BLOB, E0_PATH, SELECTED, FORBIDDEN, validated_review,
)
from run_engine001_bpred_s4r1_semref1_aqa1_uploaded_a_intake import (
    AQA1_E0, AQA1_E0_BLOB, REL_A, INPUT_SHA, audit as audit_aqa1,
)
from run_engine001_bpred_s4r1_corpus_integrity import REL_CORPUS

E0_PATH_WEAK = (
    "AutoDraw_Stage20/docs/"
    "ENGINE001_BPRED001_S4R1_AWEAK1_SINGLE_HUMAN_REGIONAL_DIAGNOSTIC_PREREG_2026-11-21.md"
)
E0_BLOB_WEAK = "a6ceeceb6095b2b23224ce8c412a44818302066c"
VERSION = "ENGINE001_BPRED_S4R1_AWEAK1_APPROX_SOURCE_REGIONS_V1"
RADII = (0, 2, 5)
EROSION_SOURCE_PX = 2  # square footprint Chebyshev 2, not logical board size


def ratio(num: int, den: int) -> float | None:
    return float(num / den) if den else None


def score_human_mark_proxies(
    a: np.ndarray, protected: np.ndarray, unknown: np.ndarray,
    potential_core: np.ndarray, region_ids: np.ndarray,
) -> dict:
    """No source RGB equality checks; marks remain approximate.

    K = human hand-marked critical or color-boundary pixels.
    I = hand-marked perceived coherent interior, NOT owner-accurate color.
    """
    if (not isinstance(a, np.ndarray) or a.ndim != 3 or a.shape[2] != 3
            or a.dtype != np.uint8):
        raise ValueError("BLOCKED_AWEAK1_INVALID_HUMAN_RGB_LABEL")
    h, w = a.shape[:2]
    masks = (protected, unknown, potential_core)
    if (any(not isinstance(m, np.ndarray) or m.dtype != bool or m.shape != (h,w)
            for m in masks)
            or not isinstance(region_ids, np.ndarray)
            or region_ids.shape != (h,w)
            or not np.issubdtype(region_ids.dtype, np.integer)
            or int(region_ids.min()) < 1
            or not np.all(protected | unknown)
            or np.any(protected & unknown)
            or np.any(potential_core & ~unknown)):
        raise ValueError("BLOCKED_AWEAK1_SOURCE_MAP_OR_UNCERTAINTY_CONTRACT")
    classes = [np.all(a == col, axis=2) for col in CODES]
    if not np.all(np.logical_or.reduce(classes)):
        raise ValueError("BLOCKED_AWEAK1_INVALID_SOURCE_MARK_RGB_CLASS")
    k = classes[1] | classes[2]
    interior = classes[3]
    ambiguous_or_unreviewed = classes[0] | classes[4]
    n_k = int(np.count_nonzero(k))
    n_i = int(np.count_nonzero(interior))
    if not n_k or not n_i:
        raise ValueError("BLOCKED_AWEAK1_REQUIRED_MARK_TYPES_ABSENT")
    near = {}
    for radius in RADII:
        if radius == 0:
            protected_near = protected
        else:
            protected_near = ndimage.maximum_filter(
                protected.astype(np.uint8), size=(2*radius+1),
                mode="constant", cval=0,
            ).astype(bool)
        supported = int(np.count_nonzero(k & protected_near))
        near[str(radius)] = {
            "source_radius_px": radius,
            "K_near_protected": supported,
            "K_not_near_protected": n_k-supported,
            "K_near_protected_fraction": ratio(supported,n_k),
        }
    if any(near[str(a)]["K_near_protected"] > near[str(b)]["K_near_protected"]
           for a,b in zip(RADII,RADII[1:])):
        raise ValueError("BLOCKED_AWEAK1_PROXIMITY_NONMONOTONIC")

    # Square erosion: conservative center subset, with no claim manual brush
    # footprint corresponds to the physical game's brush footprint.
    inner = ndimage.binary_erosion(
        interior, structure=np.ones((2*EROSION_SOURCE_PX+1,)*2,bool),
        border_value=0,
    )
    inner_count = int(np.count_nonzero(inner))
    inner_protected = int(np.count_nonzero(inner & protected))
    inner_core = int(np.count_nonzero(inner & potential_core))

    def touched(mask):
        return np.unique(region_ids[mask]).astype(int)

    touched_k = touched(k)
    touched_i = touched(interior)
    common = np.intersect1d(touched_k,touched_i)
    all_core_ids = region_ids[potential_core]
    by_region = np.bincount(all_core_ids, minlength=int(region_ids.max())+1)
    core_touch_k = by_region[touched_k]
    return {
        "human_marks_are_exact_rgb_gt": False,
        "source_label_counts": {
            "critical": int(np.count_nonzero(classes[1])),
            "human_color_boundary": int(np.count_nonzero(classes[2])),
            "human_visual_interior": n_i,
            "unreviewed": int(np.count_nonzero(classes[0])),
            "ambiguous": int(np.count_nonzero(classes[4])),
            "K_critical_or_boundary": n_k,
            "unknown_human_unreviewed_or_ambiguous": int(np.count_nonzero(ambiguous_or_unreviewed)),
        },
        "source_global": {
            "pixels": h*w,
            "protected": int(np.count_nonzero(protected)),
            "unknown": int(np.count_nonzero(unknown)),
            "potential_core_NOT_safe": int(np.count_nonzero(potential_core)),
        },
        "K_sensitivity_source_only": near,
        "K_exact_core_conflict_proxy": int(np.count_nonzero(k & potential_core)),
        "K_core_conflict_proxy_fraction": ratio(int(np.count_nonzero(k & potential_core)),n_k),
        "I_human_visual_interior": {
            "raw_count": n_i,
            "raw_in_protected": int(np.count_nonzero(interior & protected)),
            "raw_in_unknown": int(np.count_nonzero(interior & unknown)),
            "raw_in_potential_core_NOT_safe": int(np.count_nonzero(interior & potential_core)),
            "raw_in_core_fraction": ratio(int(np.count_nonzero(interior & potential_core)),n_i),
            "eroded2_square_count": inner_count,
            "eroded2_in_protected": inner_protected,
            "eroded2_in_potential_core_NOT_safe": inner_core,
            "eroded2_in_core_fraction": ratio(inner_core,inner_count),
            "eroded2_status": (
                "SOURCE_ONLY_NONZERO_SUPPORT" if inner_count
                else "NOT_APPLICABLE_NO_ERODED_INTERIOR"
            ),
        },
        "SLIC_region_touch_approximation": {
            "total_regions": int(np.unique(region_ids).size),
            "regions_touched_by_K": int(len(touched_k)),
            "regions_touched_by_I": int(len(touched_i)),
            "regions_touched_by_both_K_and_I": int(len(common)),
            "K_touched_regions_with_any_hypothetical_core": int(np.count_nonzero(core_touch_k)),
            "potential_core_pixels_in_K_touched_regions_NOT_error_rate": int(np.sum(core_touch_k)),
        },
        "status": "DESCRIPTIVE_A_ONLY_NO_INDEPENDENT_SEMANTIC_GROUND_TRUTH",
        "stroke_admission": FORBIDDEN,
        "strict_s4": "BLOCKED",
    }


def audit(root: Path) -> dict:
    for doc, expected in ((E0_PATH_WEAK,E0_BLOB_WEAK),
                          (AQA1_E0,AQA1_E0_BLOB),(E0_PATH,E0_BLOB)):
        if git_blob_sha1((root/doc).read_bytes()) != expected:
            raise ValueError("BLOCKED_AWEAK1_FROZEN_PROTOCOL_DRIFT " + doc)
    aqa = audit_aqa1(root)  # exactly 8/8 raw label Git SHA and 4 original SHAs
    if (aqa["technical_status"] != "PASS_A_ONLY_SOURCE_AND_LABEL_INTEGRITY"
            or aqa["science_status"] != "BLOCKED_MISSING_SECOND_INDEPENDENT_REVIEWER"
            or aqa["pairs_a_checked"] != 4 or aqa["pairs_b_checked"] != 0):
        raise ValueError("BLOCKED_AWEAK1_ORIGINAL_SOURCE_INTAKE_NOT_PASS")

    records, combined = [], {}
    for original_name in SELECTED:
        key=hashlib.sha256(original_name.encode()).hexdigest()[:12]
        raw=(root/REL_CORPUS/original_name).read_bytes()
        src=decode_original(raw)
        png=(root/REL_A/(key+"_a.png")).read_bytes()
        sidecar=json.loads((root/REL_A/(key+"_a.json")).read_text(encoding="utf8"))
        reviewer, a=validated_review(src,png,sidecar)
        source=generic_source_maps(src["rgba"])
        regions=original_source_region_uncertainty(src["rgba"],source)
        if (source["owner_status"] != "MISSING"
                or regions["source_owner_status"] != "MISSING"
                or np.any(source["candidate_interior"])
                or regions["source_rgba_sha256"] != hashlib.sha256(src["rgba"].tobytes()).hexdigest()
                or source["stroke_admission"] != FORBIDDEN
                or regions["stroke_admission"] != FORBIDDEN
                or not np.array_equal(src["rgba"][:,:,:3],source["source_rgb"])
                or not np.array_equal(src["rgba"][:,:,3],source["source_alpha"])):
            raise ValueError("BLOCKED_AWEAK1_EXISTING_SOURCE_CONTRACT")
        metrics=score_human_mark_proxies(
            a,source["protected"],source["unknown"],
            regions["geometric_potential_core"],regions["region_ids"],
        )
        records.append({
            "original_file":original_name,
            "source_size_hw":[src["height"],src["width"]],
            "source_git_blob_sha1":src["git_blob_sha1"],
            "source_raw_sha256":src["sha256"],
            "source_rgba_sha256":regions["source_rgba_sha256"],
            "A_labels_png_sha256":sidecar["labels_png_sha256"],
            "A_reviewer_id_supplied": bool(reviewer),
            "math_map_version":source["version"],
            "source_region_version":regions["version"],
            "metrics":metrics,
        })
        # Pooled raw counts and rates; per-image rates never averaged naively.
        sc=metrics["source_label_counts"]
        for name in ("critical","human_color_boundary","human_visual_interior",
                     "unreviewed","ambiguous","K_critical_or_boundary"):
            combined[name]=combined.get(name,0)+sc[name]
        for rr in RADII:
            keyr="K_near_protected_r"+str(rr)
            combined[keyr]=combined.get(keyr,0)+metrics["K_sensitivity_source_only"][str(rr)]["K_near_protected"]
        for keyc,val in (
            ("K_exact_core_conflict_proxy",metrics["K_exact_core_conflict_proxy"]),
            ("I_raw_core",metrics["I_human_visual_interior"]["raw_in_potential_core_NOT_safe"]),
            ("I_eroded2_pixels",metrics["I_human_visual_interior"]["eroded2_square_count"]),
            ("I_eroded2_core",metrics["I_human_visual_interior"]["eroded2_in_potential_core_NOT_safe"]),
            ("source_protected",metrics["source_global"]["protected"]),
            ("source_unknown",metrics["source_global"]["unknown"]),
            ("source_potential_core",metrics["source_global"]["potential_core_NOT_safe"]),
            ("source_pixels",metrics["source_global"]["pixels"]),
        ):
            combined[keyc]=combined.get(keyc,0)+val
    k_all=combined["K_critical_or_boundary"]
    i_all=combined["human_visual_interior"]
    combined["K_near_protected_fraction_by_source_radii"]={
        str(rr):ratio(combined["K_near_protected_r"+str(rr)],k_all) for rr in RADII
    }
    combined["K_exact_core_conflict_proxy_fraction"]=ratio(combined["K_exact_core_conflict_proxy"],k_all)
    combined["I_raw_core_fraction"]=ratio(combined["I_raw_core"],i_all)
    combined["I_eroded2_core_fraction"]=ratio(combined["I_eroded2_core"],combined["I_eroded2_pixels"])
    return {
        "version":VERSION,"input_commit":INPUT_SHA,"frozen_AWEAK1_E0_git_blob":E0_BLOB_WEAK,
        "original_SEMREF1_E0_git_blob":E0_BLOB,
        "tested_frozen_A_only_sources":4,"second_reviewers_required_for_this_descriptive_step":False,
        "AQA1_technical_intake":"PASS_AT_SAME_INPUT_SOURCE",
        "evidence_level":"E2_SOURCE_ONLY_DESCRIPTIVE",
        "source_pixel_radii_sensitivity":[0,2,5],
        "human_rgb_equality_assumption":False,
        "human_marks_pixel_exact_ground_truth":False,
        "scored_as_auto_quality_pass":False,
        "science_status":"PARTIAL_EXPLORATORY_SOURCE_ONLY_NEITHER_SEMANTIC_NOR_NATIVE",
        "strict_two_reviewer_SEMREF1":"BLOCKED_NO_B_LABELS_UNCHANGED",
        "strict_S4":"BLOCKED", "stroke_admission":FORBIDDEN,
        "source_owner_ground_truth":"MISSING",
        "native_E3":"NOT_RUN","game_E4":"NOT_RUN","independent_E5":"NOT_RUN",
        "exact_game_CHALK":None, "heldout_outputs":0,
        "original_or_human_input_modified":False,
        "pooled_four_DEV_counts":combined, "per_original":records,
    }


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    result=audit(args.root)
    output=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n"
    if args.out:
        args.out.write_text(output,encoding="utf8")
    print(output)
