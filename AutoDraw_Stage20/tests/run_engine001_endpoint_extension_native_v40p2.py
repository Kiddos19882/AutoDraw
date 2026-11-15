#!/usr/bin/env python3
"""V40P2: native Egret endpoint extension, full 410 dark lines unchanged."""
from __future__ import annotations

import argparse
import copy
import json
import platform
from pathlib import Path

import cv2
import numpy as np

from engine001_paint_then_detail_v35 import native_strokes
from run_engine001_boundary_shift_native_v39 import verified_input, native_metrics
from run_engine001_internal_color_tolerance_v40 import overlap_by_class
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import (
    SOURCE_SHA, sha, warm_mask, png_pixel_exact_replay)
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source, sheet

EXPERIMENT="ENGINE001_V40P2_NATIVE_ENDPOINT_EXTENSION"
SCALE=3
ROI_LEFT=155.0
ROI_RIGHT=304.75
AMPLITUDES={"A":0.0, "B":0.25, "C":0.5}


def extend(base:dict,amount:float):
    if amount not in AMPLITUDES.values():
        raise ValueError("V40P2 unregistered extension amount")
    if (base.get("paint_strokes"),base.get("detail_strokes"),
            base.get("synthetic_vertices_NOT_CHALK")) != (1945,410,5682):
        raise ValueError("V40P2 frozen full-outline plan count drift")
    out=copy.deepcopy(base)
    changes=0
    for i,(previous,entry) in enumerate(zip(base["strokes"],out["strokes"])):
        s=entry["stroke"]
        if i>=1945:
            if previous!=entry or entry["layer"]!="detail":
                raise ValueError("V40P2 changed full dark contour")
            continue
        if entry["layer"]!="paint" or s["width"]!=2 or len(s["points"])!=2:
            raise ValueError("V40P2 invalid native width2 paint source")
        a,b=s["points"]
        x0,x1=a["x"],b["x"]
        if (a["y"]!=b["y"] or x0>x1 or
                not ROI_LEFT<=x0<=ROI_RIGHT or
                not ROI_LEFT<=x1<=ROI_RIGHT):
            raise ValueError("V40P2 non-horizontal or out-of-ROI fill")
        a["x"]=max(ROI_LEFT,x0-amount)
        b["x"]=min(ROI_RIGHT,x1+amount)
        if a["x"]>b["x"]:
            raise ValueError("V40P2 endpoint order reversed")
        if a["x"]!=x0 or b["x"]!=x1:
            changes+=1
        if ({k:v for k,v in previous["stroke"].items() if k!="points"} !=
            {k:v for k,v in s.items() if k!="points"}):
            raise ValueError("V40P2 color/width/id changed")
        for old,new in zip(previous["stroke"]["points"],s["points"]):
            if old["y"]!=new["y"] or abs(old["x"]-new["x"])>amount+1e-12:
                raise ValueError("V40P2 moved y or excessive x")
    if len(out["strokes"])!=2355 or sum(
            len(row["stroke"]["points"]) for row in out["strokes"])!=5682:
        raise ValueError("V40P2 accepted points/resources changed")
    return out,changes


def main():
    p=argparse.ArgumentParser()
    for name in ("workspace","source","v37p2-archive","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V40P2 preserve evidence, refuse overwrite")
    if sha(a.source)!=SOURCE_SHA:raise ValueError("V40P2 source SHA drift")
    original,_=prepare_source(a.source)
    labels=original_labels(a.source)
    baseline=verified_input(a.v37p2_archive)
    variants={};changed={}
    for name,amp in AMPLITUDES.items():
        variants[name],changed[name]=extend(baseline,amp)
    out=a.output;out.mkdir(parents=True)
    (out/"plans.json").write_text(json.dumps({
        "experiment":EXPERIMENT,"plans":variants,"endpoint_changed":changed},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    native={};crops={};metrics={}
    warm=warm_mask(original)
    foreground=np.isin(labels,(4,5,6,7))
    ext_distance=cv2.distanceTransform(
        (~foreground).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    for k in "ABC":
        sub=out/k;sub.mkdir()
        layers,meta,_=native_batch(a.workspace,"V40P2-"+k,
            native_strokes(variants[k]),sub,
            renderer_method="renderV36SourceColoredContourProbe")
        native[k]=layers
        crop=logical_crop(layers["composite"])
        crop.save(out/("V40P2-"+k+"-roi.png"))
        crops[k]=crop
        result=native_metrics(layers,original,labels,warm)
        overlaps={}
        for alpha in (24,128):
            per={}
            for color in (4,5,6,7):
                paint=layers[f"color-{color}"][:,:,3]>=alpha
                per[str(color)]=overlap_by_class(labels,color,paint)
            total=sum(s["foreign_overlap_excess_beyond_3logical_px"]
                      for s in per.values())
            allowed=sum(s["foreign_overlap_allowed_within_3logical_px"]
                        for s in per.values())
            painted_union=np.logical_or.reduce([
                layers[f"color-{color}"][:,:,3]>=alpha for color in (4,5,6,7)])
            overlaps[str(alpha)]={
                "by_color":per,
                "allowed_internal_native_pixels":allowed,
                "excess_internal_native_pixels":total,
                "external_beyond_3logical_px_native_pixels":int(np.count_nonzero(
                    painted_union&~foreground&(ext_distance>9)))
            }
        result["overlap_tolerance"]=overlaps
        result["changed_paint_strokes"]=changed[k]
        result["renderer_meta"]=meta
        metrics[k]=result
    control=png_pixel_exact_replay(
        a.v37p2_archive/"C"/"V37P2-C-composite.png",
        out/"A"/"V40P2-A-composite.png")
    for name in "BC":
        if not np.array_equal(native["A"]["color-100"][:,:,3],
                              native[name]["color-100"][:,:,3]):
            raise ValueError("V40P2 dark contour alpha changed")
    sheet([original,crops["A"],crops["B"],crops["C"]],
          ["Original","Frozen V37-P2-C","Horizontal +0.25 endpoints",
           "Horizontal +0.5 endpoints"],out/"comparison-full.png")
    sheet([original,crops["A"],crops["B"],crops["C"]],
          ["Original","Frozen outline","Endpoint 0.25","Endpoint 0.5"],
          out/"comparison-faces.png",top=True)
    validity={}
    for k in "BC":
        a24=metrics["A"]["native_class_metrics"]["24"]
        b24=metrics[k]["native_class_metrics"]["24"]
        av=[a24["class_recall_and_overlap"][str(c)]["correct_class_recall"]
            for c in (4,5,6,7)]
        bv=[b24["class_recall_and_overlap"][str(c)]["correct_class_recall"]
            for c in (4,5,6,7)]
        checks={
            "all_four_class_recall_nonregression":all(y>=x for x,y in zip(av,bv)),
            "one_class_strict_improvement":any(y>x for x,y in zip(av,bv)),
            "union_recall_nonregression":b24["union_source_foreground_recall"]>=
                a24["union_source_foreground_recall"],
            "internal_overpaint_excess_zero":
                metrics[k]["overlap_tolerance"]["24"]["excess_internal_native_pixels"]==0,
            "exterior_overpaint_nonregression":
                metrics[k]["overlap_tolerance"]["24"]["external_beyond_3logical_px_native_pixels"]<=
                metrics["A"]["overlap_tolerance"]["24"]["external_beyond_3logical_px_native_pixels"],
            "full_RGB_nonregression":metrics[k]["source_RGB_MAE"]<=metrics["A"]["source_RGB_MAE"],
            "warm_RGB_nonregression":metrics[k]["warm_RGB_MAE"]<=metrics["A"]["warm_RGB_MAE"]}
        validity[k]={"checks":checks,"predeclared_diagnostic_PASS":all(checks.values())}
    hashes={str(x.relative_to(out)).replace("\\","/"):sha(x)
            for x in out.rglob("*") if x.is_file()}
    report={
        "experiment":EXPERIMENT,"status":"E3_NATIVE_ACTUAL_EGRET_NOT_GAME",
        "source_sha256":SOURCE_SHA,
        "original_V37P2_C_control_RGBA_exact":control["pixel_rgba_exact"],
        "full_user_preferred_contours_alpha_identical":True,
        "strokes":2355,"synthetic_vertices_NOT_CHALK":5682,
        "endpoint_reallocated_strokes":changed,
        "measurements":metrics,
        "candidate_decisions":validity,
        "artifact_SHA256":hashes,
        "production_quality_accepted":False,
        "game_exact_CHALK":None,
        "not_tested":["live game E4","independent E5","game point quota",
                      "actual semantic coverage >=99%"],
        "versions":{"Python":platform.python_version(),"numpy":np.__version__,
                    "cv2":cv2.__version__}
    }
    (out/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"decisions":validity,
                      "RGB_MAE":{k:metrics[k]["source_RGB_MAE"] for k in "ABC"}},indent=2))

if __name__=="__main__":
    main()
