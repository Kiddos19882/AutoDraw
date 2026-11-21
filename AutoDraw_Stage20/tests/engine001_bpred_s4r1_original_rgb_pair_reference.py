#!/usr/bin/env python3
"""S4R1 CR1 independent raw RGB pair reference, not human semantic ground truth.

Original full-resolution RGBA, 4-neighbor integer RGB difference. Independent
of source Sobel, Lab ΔE, SLIC, neural masks, game128 palette and brush. No
model/semantic/owner or painting acceptance follows from this diagnostic.
"""
from __future__ import annotations

import hashlib
import numpy as np

THRESHOLD = 32
VERSION = "ENGINE001_BPRED_S4R1_CR1_RAW_CONTRAST_REFERENCE_V1"
STROKE_FORBIDDEN = "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION"


def raw_contrast_endpoints(rgba: np.ndarray) -> np.ndarray:
    if (not isinstance(rgba, np.ndarray) or rgba.dtype != np.uint8
            or rgba.ndim != 3 or rgba.shape[-1] != 4
            or min(rgba.shape[:2]) < 1
            or rgba.shape[0] * rgba.shape[1] > 16_000_000):
        raise ValueError("BLOCKED_CR1_INVALID_ORIGINAL_RGBA")
    rgb = rgba[:, :, :3]
    opaque = rgba[:, :, 3] == 255
    edges = np.zeros(opaque.shape, dtype=bool)
    if rgba.shape[0] > 1:
        pair = (
            np.max(
                np.abs(rgb[:-1].astype(np.int16)-rgb[1:].astype(np.int16)),
                axis=2,
            ) >= THRESHOLD
        ) & opaque[:-1] & opaque[1:]
        edges[:-1] |= pair
        edges[1:] |= pair
    if rgba.shape[1] > 1:
        pair = (
            np.max(
                np.abs(rgb[:, :-1].astype(np.int16)-rgb[:, 1:].astype(np.int16)),
                axis=2,
            ) >= THRESHOLD
        ) & opaque[:, :-1] & opaque[:, 1:]
        edges[:, :-1] |= pair
        edges[:, 1:] |= pair
    return edges


def score_original_rgb_reference(
    rgba: np.ndarray, source_maps: dict, source_regions: dict,
) -> dict:
    reference = raw_contrast_endpoints(rgba)
    h, w = reference.shape
    if (not isinstance(source_maps, dict)
            or source_maps.get("owner_status") != "MISSING"
            or source_maps.get("stroke_admission") != STROKE_FORBIDDEN
            or source_maps.get("semantic_detail_status") !=
                "UNKNOWN_NO_VERIFIED_SEMANTIC_MODEL"
            or not isinstance(source_regions, dict)
            or source_regions.get("source_owner_status") != "MISSING"
            or source_regions.get("stroke_admission") != STROKE_FORBIDDEN
            or source_regions.get("source_rgba_sha256") !=
                hashlib.sha256(rgba.tobytes()).hexdigest()):
        raise ValueError("BLOCKED_CR1_ORIGINAL_SOURCE_REGION_PROVENANCE")
    for key, expected in (("source_rgb",rgba[:,:,:3]),
                          ("source_alpha",rgba[:,:,3])):
        actual=source_maps.get(key)
        if not isinstance(actual,np.ndarray) or not np.array_equal(actual,expected):
            raise ValueError("BLOCKED_CR1_ORIGINAL_RGB_ALPHA_MISMATCH")
    for mapping,key in ((source_maps,"protected"),
                        (source_maps,"unknown"),
                        (source_maps,"candidate_interior"),
                        (source_regions,"geometric_potential_core")):
        v=mapping.get(key)
        if (not isinstance(v,np.ndarray) or v.dtype!=bool
                or v.shape!=(h,w)):
            raise ValueError("BLOCKED_CR1_SOURCE_MASK_SHAPE")
    protected=source_maps["protected"]
    unknown=source_maps["unknown"]
    core=source_regions["geometric_potential_core"]
    if (not np.all(protected | unknown)
            or np.any(protected & unknown)
            or np.any(source_maps["candidate_interior"])
            or np.any(core & ~unknown)):
        raise ValueError("BLOCKED_CR1_SOURCE_UNKNOWN_NOT_ADMISSIBLE")
    ref_count=int(reference.sum())
    missed=reference & ~protected
    missed_count=int(missed.sum())
    protected_count=ref_count-missed_count
    core_overlap=int((reference & core).sum())
    if ref_count==0:
        state="NOT_APPLICABLE_NO_OPAQUE_RGB_CONTRAST_PAIRS"
    elif missed_count:
        state="SOURCE_CONTRAST_DIAGNOSTIC_FAIL_NOT_NATIVE_BRUSH_FAIL"
    else:
        state="PASS_RAW_RGB_CONTRAST_ONLY_NOT_SEMANTIC"
    return {
        "version":VERSION, "source_rgba_sha256":hashlib.sha256(rgba.tobytes()).hexdigest(),
        "threshold_max_abs_rgb_channel":THRESHOLD,
        "connectivity":"4_NEIGHBOR_BOTH_ENDPOINTS_OPAQUE",
        "status":state,
        "source_contrast_endpoints":ref_count,
        "source_contrast_protected_endpoints":protected_count,
        "source_contrast_unprotected_endpoints":missed_count,
        "source_contrast_unknown_endpoints":int((reference & unknown).sum()),
        "source_contrast_geometric_potential_core_overlap":core_overlap,
        "protected_fraction_on_raw_contrast_reference":(
            float(protected_count/ref_count) if ref_count else None),
        "original_opaque_pixels":int((rgba[:,:,3]==255).sum()),
        "source_game_owner_status":"MISSING",
        "critical_human_reference_status":"MISSING",
        "semantic_critical_recall":"NOT_READY_NO_INDEPENDENT_HUMAN_LABELS",
        "source_color_owner_accuracy":"UNKNOWN_NO_CANONICAL_OWNER_REFERENCE",
        "new_native_false_safe":"NOT_RUN",
        "stroke_admission":STROKE_FORBIDDEN,
        "reference_endpoints":reference,
        "reference_missed":missed,
    }
