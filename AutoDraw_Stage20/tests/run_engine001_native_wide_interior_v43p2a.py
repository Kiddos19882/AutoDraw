#!/usr/bin/env python3
"""ENGINE-001 V43-P2a native width2/4/6 interior feasibility, NOT production."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
from pathlib import Path

import cv2
import numpy as np

from engine001_paint_then_detail_v35 import native_strokes
from run_engine001_boundary_shift_native_v39 import verified_input, native_metrics
from run_engine001_internal_color_tolerance_v40 import overlap_by_class
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import SOURCE_SHA, sha, warm_mask, png_pixel_exact_replay
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source, sheet

EXPERIMENT = "ENGINE001_V43_P2A_NATIVE_WIDE_INTERIOR"
CLASS = 7
SAMPLES = (0, 0.25, 0.5, 0.75, 1.0)
CANDIDATES = {"A": (2, 0.0), "B": (4, 4.0), "C": (6, 5.0)}


def largest_dark_component(labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    if not isinstance(labels, np.ndarray) or labels.shape != (240, 460) or labels.dtype.kind not in "iu":
        raise ValueError("V43-P2a frozen source logical label shape/type changed")
    count, comp, stats, _ = cv2.connectedComponentsWithStats(
        (labels == CLASS).astype(np.uint8), connectivity=8)
    if count < 2:
        raise ValueError("V43-P2a no dark color source components")
    largest = sorted(range(1, count),
                     key=lambda i: (-int(stats[i, cv2.CC_STAT_AREA]), i))[0]
    area = int(stats[largest, cv2.CC_STAT_AREA])
    if area != 5005:
        raise ValueError("V43-P2a largest source dark component changed")
    mask = comp == largest
    distance = cv2.distanceTransform(
        np.pad(mask.astype(np.uint8), 1),
        cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
    return mask, distance, {"component_label": largest, "component_area": area,
                            "max_inscribed_radius_source_px": float(distance.max())}


def select_interior(base: dict, mask: np.ndarray, distance: np.ndarray,
                    native_width: int, min_radius: float) -> tuple[dict, list[dict]]:
    if ((native_width, min_radius) not in CANDIDATES.values()
        or mask.shape != (240, 460) or distance.shape != mask.shape):
        raise ValueError("V43-P2a unexpected native width, radius or source mask")
    if (base.get("paint_strokes"), base.get("detail_strokes"),
            base.get("synthetic_vertices_NOT_CHALK"), len(base.get("strokes", []))) != (
            1945, 410, 5682, 2355):
        raise ValueError("V43-P2a frozen user full outline plan counts changed")
    result = copy.deepcopy(base)
    audit = []
    for index, (old_entry, new_entry) in enumerate(zip(base["strokes"], result["strokes"])):
        old = old_entry["stroke"]
        s = new_entry["stroke"]
        if index >= 1945:
            if old_entry != new_entry or new_entry["layer"] != "detail":
                raise ValueError("V43-P2a user full dark contours changed")
            continue
        if (new_entry["layer"] != "paint" or old["width"] != 2
                or len(old["points"]) != 2 or
                old["points"][0]["y"] != old["points"][1]["y"]):
            raise ValueError("V43-P2a frozen horizontal fill width2 changed")
        selected = False
        radii = []
        if old["colorIndex"] == CLASS and native_width != 2:
            p, q = old["points"]
            y = round(p["y"])
            for t in SAMPLES:
                x = round((1-t)*p["x"] + t*q["x"])
                if not (0 <= y < 240 and 155 <= x <= 304):
                    raise ValueError("V43-P2a sample outside source ROI")
                radii.append(float(distance[y, x]))
            selected = all(mask[y, round((1-t)*p["x"] + t*q["x"])]
                           for t in SAMPLES) and all(r >= min_radius for r in radii)
        if selected:
            s["width"] = native_width
        if ({k:v for k,v in old.items() if k!="width"} !=
            {k:v for k,v in s.items() if k!="width"}):
            raise ValueError("V43-P2a modified paint geometry/color/ID")
        audit.append({"id": old["strokeId"], "source_color": old["colorIndex"],
                      "old_width": old["width"], "native_width": s["width"],
                      "selected": selected, "sampled_source_distances": radii})
    if (len(audit) != 1945 or len(result["strokes"]) != 2355
        or sum(len(x["stroke"]["points"]) for x in result["strokes"]) != 5682):
        raise ValueError("V43-P2a synthetic source resource count drift")
    return result, audit


def main() -> None:
    parser=argparse.ArgumentParser()
    for name in ("workspace","source","v37p2-archive","output"):
        parser.add_argument("--"+name, required=True, type=Path)
    a=parser.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V43-P2a refuse overwrite original evidence")
    if sha(a.source) != SOURCE_SHA:
        raise ValueError("V43-P2a source SHA drift")
    original,_=prepare_source(a.source)
    labels3=original_labels(a.source)
    mask,distance,component=largest_dark_component(labels3[::3, ::3].copy())
    base=verified_input(a.v37p2_archive)
    variants,audits={},{}
    for key,(width,radius) in CANDIDATES.items():
        variants[key],audits[key]=select_interior(base,mask,distance,width,radius)
    out=a.output
    out.mkdir(parents=True)
    (out/"width-candidates.json").write_text(json.dumps({
        "experiment":EXPERIMENT,"largest_dark_component":component,
        "candidate_native_width_and_source_radius":CANDIDATES,
        "selection":audits,"plans":variants},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    raw,crops,metrics={}, {}, {}
    warm=warm_mask(original)
    foreground=np.isin(labels3,(4,5,6,7))
    extent=cv2.distanceTransform((~foreground).astype(np.uint8),
                                  cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    for key in "ABC":
        directory=out/key
        directory.mkdir()
        native,meta,_=native_batch(
            a.workspace,"V43P2a-"+key,native_strokes(variants[key]),
            directory,renderer_method="renderV43WideInteriorProbe")
        raw[key]=native
        roi=logical_crop(native["composite"])
        crops[key]=roi
        roi.save(out/("V43P2a-"+key+"-roi.png"))
        measured=native_metrics(native,original,labels3,warm)
        per_threshold={}
        for alpha in (24,128):
            paint=np.logical_or.reduce([
                native[f"color-{c}"][:,:,3]>=alpha for c in (4,5,6,7)])
            per_color={str(c):overlap_by_class(
                labels3,c,native[f"color-{c}"][:,:,3]>=alpha) for c in (4,5,6,7)}
            per_threshold[str(alpha)]={
                "foreign_overlap_allowed_within_3logical_px":sum(
                    x["foreign_overlap_allowed_within_3logical_px"] for x in per_color.values()),
                "foreign_overlap_excess_beyond_3logical_px":sum(
                    x["foreign_overlap_excess_beyond_3logical_px"] for x in per_color.values()),
                "exterior_excess_beyond_3logical_px":int(np.count_nonzero(
                    paint & ~foreground & (extent>9))),
            }
        measured["overlap_and_exterior"]=per_threshold
        measured["paint_width_histogram"]={str(w):sum(
            x["stroke"]["width"]==w for x in variants[key]["strokes"][:1945])
            for w in (2,4,6)}
        measured["native_meta"]=meta
        metrics[key]=measured
    replay=png_pixel_exact_replay(
        a.v37p2_archive/"C"/"V37P2-C-composite.png",
        out/"A"/"V43P2a-A-composite.png")
    if not replay["pixel_rgba_exact"]:
        raise ValueError("V43-P2a original true Egret baseline changed")
    for key in "BC":
        if not np.array_equal(raw["A"]["color-100"][:,:,3],
                              raw[key]["color-100"][:,:,3]):
            raise ValueError("V43-P2a user 410 original dark contour alpha changed")
    sheet([original,crops["A"],crops["B"],crops["C"]],
          ["Original","Frozen width2","Native width4 deep dark",
           "Native width6 deeper dark"],out/"comparison-full.png")
    sheet([original,crops["A"],crops["B"],crops["C"]],
          ["Original","Baseline full outline","Width4 deep","Width6 deep"],
          out/"comparison-faces.png",top=True)
    baseline=metrics["A"]["native_class_metrics"]["24"]
    criteria={}
    for key in "BC":
        candidate=metrics[key]["native_class_metrics"]["24"]
        checks={
            "dark_class_own_recall_improves":
                candidate["class_recall_and_overlap"]["7"]["correct_class_recall"] >
                baseline["class_recall_and_overlap"]["7"]["correct_class_recall"],
            "other_classes_nonregress":all(
                candidate["class_recall_and_overlap"][str(c)]["correct_class_recall"] >=
                baseline["class_recall_and_overlap"][str(c)]["correct_class_recall"]
                for c in (4,5,6)),
            "source_silhouette_nonregress":candidate["union_source_foreground_recall"] >=
                                           baseline["union_source_foreground_recall"],
            "native_internal_excess_nonregress_alpha24_128":all(
                metrics[key]["overlap_and_exterior"][str(t)]["foreign_overlap_excess_beyond_3logical_px"] <=
                metrics["A"]["overlap_and_exterior"][str(t)]["foreign_overlap_excess_beyond_3logical_px"]
                for t in (24,128)),
            "native_exterior_nonregress_alpha24_128":all(
                metrics[key]["overlap_and_exterior"][str(t)]["exterior_excess_beyond_3logical_px"] <=
                metrics["A"]["overlap_and_exterior"][str(t)]["exterior_excess_beyond_3logical_px"]
                for t in (24,128)),
            "full_RGB_MAE_nonregress":metrics[key]["source_RGB_MAE"]<=metrics["A"]["source_RGB_MAE"],
            "warm_RGB_MAE_nonregress":metrics[key]["warm_RGB_MAE"]<=metrics["A"]["warm_RGB_MAE"],
        }
        criteria[key]={"checks":checks,"combined_numeric_diagnostic_PASS":all(checks.values())}
    hashes={str(p.relative_to(out)).replace("\\","/"):sha(p)
            for p in out.rglob("*") if p.is_file()}
    record={"experiment":EXPERIMENT,"status":"ACTUAL_NATIVE_EGRET_E3_NOT_GAME",
            "frozen_source_SHA256":SOURCE_SHA,
            "baseline_C_RGBA_exact":True,"all_410_original_contours_alpha_exact":True,
            "strokes":2355,"synthetic_vertices_NOT_CHALK":5682,
            "component":component,"metrics":metrics,"predeclared_decisions":criteria,
            "artifact_SHA256":hashes,"production_quality_accepted":False,
            "game_exact_CHALK":None,
            "not_tested":["full oriented/skeleton hybrid","game E4","independent E5",
                "per-color production>=99%","run-bound exact CHALK"],
            "versions":{"Python":platform.python_version(),"numpy":np.__version__,
                        "OpenCV":cv2.__version__}}
    (out/"report.json").write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",
                                   encoding="utf-8")
    print(json.dumps({"width_histograms":{k:metrics[k]["paint_width_histogram"] for k in "ABC"},
                      "decision":criteria},indent=2))


if __name__=="__main__":
    main()
