#!/usr/bin/env python3
"""B3 isolated contour ring width footprint via REAL Egret, not gameplay.

Fixed source-only selection from registered B3 contour generator. The archived
BoardPane renderer and existing native_batch are reused without JS edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import cv2
import numpy as np

from run_engine001_full_adaptive_fill_v43p4 import (
    COLORS, ROI_X0, SHAPE, SOURCE_SHA, sha,
)
from run_engine001_v43p4_b3_contour_source import (
    WIDTHS, contour_candidates, _safe_owner_footprint,
)
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_internal_color_tolerance_v40 import overlap_by_class

EXP = "ENGINE001_V43P4_B3_ISOLATED_CONTOUR_NATIVE_E3"
OWNER_RGB = {4:15921900, 5:14466476, 6:11174513, 7:5191999}
ALPHAS = (24,128)
MAX_PATHS = 16


def select_native_ring_probes(labels: np.ndarray):
    if labels.shape != SHAPE or labels.dtype.kind not in "iu":
        raise ValueError("B3 invalid pinned source labels")
    selected = []
    eligibility = {}
    for owner in COLORS:
        mask = labels == owner
        outside = cv2.distanceTransform(
            (~mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        for width in WIDTHS:
            key = f"{owner}/{width}"
            chosen = None
            for cand in contour_candidates(mask,width):
                if _safe_owner_footprint(cand["footprint"],mask,outside):
                    chosen = cand
                    break
            if chosen is None:
                eligibility[key] = "NO_ELIGIBLE_RING"
                continue
            eligibility[key] = "SOURCE_MODEL_ONLY_ELIGIBLE"
            selected.append({
                "strokeId":f"icon-{len(selected)}",
                "colorIndex":owner, "colorRgb":OWNER_RGB[owner],
                "width":width,
                "points":[{"x":float(x+ROI_X0),"y":float(y)}
                          for x,y in chosen["points"]],
            })
    if not selected or len(selected) > MAX_PATHS:
        raise ValueError("B3 isolated sample size invalid")
    ids={x["strokeId"] for x in selected}
    if (len(ids)!=len(selected) or
            sum(len(x["points"]) for x in selected)>5900 or
            any(len(x["points"])<2 or len(x["points"])>128 for x in selected)):
        raise ValueError("B3 probe violates frozen renderer resources")
    return selected, eligibility


def real_native_metrics(native: dict, backing_labels: np.ndarray,
                        probes: list[dict]):
    present = set(s["colorIndex"] for s in probes)
    if set(native)!=({"composite"}|{f"color-{k}" for k in present}):
        raise ValueError("B3 real Egret scene set mismatch")
    if backing_labels.shape!=(720,1380):
        raise ValueError("B3 native backing label geometry drift")
    silhouette = np.isin(backing_labels,COLORS)
    outside = cv2.distanceTransform(
        (~silhouette).astype(np.uint8),cv2.DIST_L2,
        cv2.DIST_MASK_PRECISE)
    result = {}
    for alpha in ALPHAS:
        per = {}
        for owner in COLORS:
            if owner not in present:
                per[str(owner)]={"status":"NO_ELIGIBLE_RING_FOR_ANY_WIDTH"}
                continue
            rgba = native[f"color-{owner}"]
            if rgba.shape!=(720,1380,4) or rgba.dtype!=np.uint8:
                raise ValueError("B3 native RGBA geometry mismatch")
            ink = rgba[:,:,3]>=alpha
            met = overlap_by_class(backing_labels,owner,ink)
            # Explicit parentheses important: NumPy bitwise precedence.
            met["native_exterior_beyond_3logical_px"] = int(
                np.count_nonzero(ink & (outside > 9)))
            met["isolated_nominal_widths"] = [x["width"] for x in probes
                                              if x["colorIndex"]==owner]
            per[str(owner)] = met
        result[str(alpha)] = per
    return result


def main():
    parser=argparse.ArgumentParser()
    for name in ("workspace","source","output"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError("B3 isolated native refuses evidence overwrite")
    if sha(args.source)!=SOURCE_SHA:
        raise ValueError("B3 original frozen source hash drift")
    backing = original_labels(args.source)
    labels = backing[::3,::3][:,ROI_X0:ROI_X0+SHAPE[1]].copy()
    probes,eligibility = select_native_ring_probes(labels)
    args.output.mkdir(parents=True)
    (args.output/"probe-paths.json").write_text(
        json.dumps({
            "experiment": EXP, "source_sha256":SOURCE_SHA,
            "source_labels_sha256":hashlib.sha256(labels.tobytes()).hexdigest(),
            "selection":"first eligible contour per owner4..7, width10/6/4/2",
            "same_color_overlap_penalty":0,
            "eligible_paths":eligibility,"strokes":probes,
            "game_exact_CHALK":None,"safe_to_execute":False,
        },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    native, metadata, run = native_batch(
        args.workspace,"B3-RINGS",probes,args.output,
        renderer_method="renderComplexHoldoutColorProbe")
    measured=real_native_metrics(native,backing,probes)
    hashes={str(p.relative_to(args.output)).replace("\\","/"):sha(p)
            for p in args.output.rglob("*") if p.is_file()}
    report={
        "experiment": EXP, "source_sha256":SOURCE_SHA,
        "mode":"E3_ISOLATED_ORIGINAL_EGRET_NOT_FULL_B3",
        "native_renderer":"renderComplexHoldoutColorProbe original BoardPane",
        "eligible_paths":eligibility,
        "sample_strokes":len(probes),
        "sample_vertices_NOT_CHALK":sum(len(x["points"]) for x in probes),
        "source_owner_overlap_penalty":0,
        "native_alpha24_128":measured,
        "native_metadata":metadata,"native_run":run,
        "report_linked_SHA256":hashes,
        "whole_picture_quality":"NOT_RUN",
        "E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
        "game_exact_CHALK":None,"production_accepted":False,
        "versions":{"Python":platform.python_version(),
                    "NumPy":np.__version__},
    }
    (args.output/"report.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({
        "sample_strokes":report["sample_strokes"],
        "sample_vertices_NOT_CHALK":report["sample_vertices_NOT_CHALK"],
        "native_owner_recall_sample_NOT_FULL_IMAGE":{
            a:{k: v.get("correct_class_recall")
               for k,v in rows.items()} for a,rows in measured.items()},
        "whole_picture_quality":"NOT_RUN"
    },ensure_ascii=False))


if __name__=="__main__":
    main()
