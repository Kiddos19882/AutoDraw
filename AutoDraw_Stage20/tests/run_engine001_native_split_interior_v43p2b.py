#!/usr/bin/env python3
"""ENGINE-001 V43P2b actual Egret: split thin dark edges + wide interior.

Source-only selection; native BoardPane/WebGL is the sole brush quality witness.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
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
from run_engine001_native_wide_interior_v43p2a import largest_dark_component

EXPERIMENT="ENGINE001_V43P2B_NATIVE_SPLIT_THIN_WIDE"
RULES={"A":(2,0.0,0),"B":(4,4.0,40),"C":(6,5.0,50)}


def longest_interior_run(stroke:dict, mask:np.ndarray, distance:np.ndarray,
                         threshold:float):
    if mask.shape!=(240,460) or distance.shape!=mask.shape:
        raise ValueError("V43P2b source interior shape changed")
    if (len(stroke["points"])!=2 or stroke["width"]!=2 or
        stroke["colorIndex"]!=7 or
        stroke["points"][0]["y"]!=stroke["points"][1]["y"]):
        raise ValueError("V43P2b source paint shape/owner invalid")
    p,q=stroke["points"]
    y=p["y"];x0=p["x"];x1=q["x"]
    if (not all(math.isfinite(v) for v in (x0,x1,y)) or
        y!=round(y) or not 155<=x0<=x1<305 or not 0<=y<240):
        raise ValueError("V43P2b noninteger row, invalid x or coordinate drift")
    y=int(y)
    left=math.ceil(x0+1)
    right=math.floor(x1-1)
    if left>right:
        return None
    best=None
    begin=None
    for x in range(left,right+2):
        eligible=(x<=right and bool(mask[y,x]) and distance[y,x]>=threshold)
        if eligible and begin is None:
            begin=x
        if not eligible and begin is not None:
            stop=x-1
            if best is None or stop-begin>best[1]-best[0]:
                best=(begin,stop)
            begin=None
    if best is None or best[1]-best[0]<8:
        return None
    if not (x0<best[0]<best[1]<x1):
        raise ValueError("V43P2b core not strictly within original line")
    return best


def split_plan(base:dict,mask:np.ndarray,distance:np.ndarray,
               width:int,radius:float,limit:int):
    if (width,radius,limit) not in RULES.values():
        raise ValueError("V43P2b candidate rule not preregistered")
    if (base.get("paint_strokes"),base.get("detail_strokes"),
        base.get("synthetic_vertices_NOT_CHALK"),len(base.get("strokes",[])))!=(
            1945,410,5682,2355):
        raise ValueError("V43P2b frozen plan counts drift")
    potentials=[]
    for idx,entry in enumerate(base["strokes"][:1945]):
        stroke=entry["stroke"]
        if (entry["layer"]!="paint" or stroke["width"]!=2 or
            len(stroke["points"])!=2):
            raise ValueError("V43P2b invalid frozen fill")
        if width==2 or stroke["colorIndex"]!=7:
            continue
        run=longest_interior_run(stroke,mask,distance,radius)
        if run is not None:
            index=int(stroke["strokeId"].removeprefix("icon-"))
            if stroke["strokeId"]!=f"icon-{index}":
                raise ValueError("V43P2b noncanonical source stroke ID")
            potentials.append((-(run[1]-run[0]),index,idx,run[0],run[1]))
    potentials.sort()
    if len(potentials)<limit:
        raise ValueError("V43P2b INSUFFICIENT_ELIGIBLE")
    chosen={p[2]:p for p in potentials[:limit]}
    strokes=[]
    selected=[]
    for idx,old in enumerate(base["strokes"][:1945]):
        if idx not in chosen:
            strokes.append(copy.deepcopy(old))
            continue
        row=old["stroke"]
        p,q=row["points"]
        _,source_index,_,start,end=chosen[idx]
        edges=(
            (row["strokeId"],2,copy.deepcopy(p),{"x":float(start),"y":p["y"]}),
            (f"icon-{500000+2*source_index}",width,
             {"x":float(start),"y":p["y"]},{"x":float(end),"y":q["y"]}),
            (f"icon-{500001+2*source_index}",2,
             {"x":float(end),"y":q["y"]},copy.deepcopy(q)),
        )
        for name,w,start_point,end_point in edges:
            item=copy.deepcopy(old)
            item["stroke"]["strokeId"]=name
            item["stroke"]["width"]=w
            item["stroke"]["points"]=[start_point,end_point]
            strokes.append(item)
        selected.append({
            "original_id":row["strokeId"],"source_index":source_index,
            "original_width":2,"new_core_width":width,
            "original_x": [float(p["x"]),float(q["x"])],
            "source_interior_core_x":[start,end],
            "core_length_logical_px":end-start,
            "synthetic_vertices_added":4,
        })
    original_detail=base["strokes"][1945:]
    if len(original_detail)!=410 or any(
        x["layer"]!="detail" or x["stroke"]["width"]!=1 or
        x["stroke"]["colorRgb"]!=0x31262B for x in original_detail):
        raise ValueError("V43P2b source dark contours changed")
    strokes.extend(copy.deepcopy(original_detail))
    expected=2355+2*limit
    vertices=5682+4*limit
    if (len(strokes)!=expected or
        sum(len(x["stroke"]["points"]) for x in strokes)!=vertices or
        expected>3000 or vertices>5900 or len(selected)!=limit or
        len({x["stroke"]["strokeId"] for x in strokes})!=expected or
        strokes[-410:]!=original_detail):
        raise ValueError("V43P2b native limit/outline/identity drift")
    return {
        **{k:copy.deepcopy(v) for k,v in base.items() if k!="strokes"},
        "paint_strokes":1945+2*limit,
        "detail_strokes":410,
        "synthetic_vertices_NOT_CHALK":vertices,
        "strokes":strokes,
    },selected


def main():
    p=argparse.ArgumentParser()
    for n in ("workspace","source","v37p2-archive","output"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V43P2b no overwrite frozen evidence")
    if sha(a.source)!=SOURCE_SHA:
        raise ValueError("V43P2b original source SHA drift")
    src,_=prepare_source(a.source)
    labels3=original_labels(a.source)
    mask,distance,component=largest_dark_component(labels3[::3,::3].copy())
    base=verified_input(a.v37p2_archive)
    variants,chosen={},{}
    for key,(width,radius,n) in RULES.items():
        variants[key],chosen[key]=split_plan(base,mask,distance,width,radius,n)
    out=a.output;out.mkdir(parents=True)
    (out/"split-plans.json").write_text(json.dumps({
        "experiment":EXPERIMENT,"rules":RULES,"dark_component":component,
        "plans":variants,"selected":chosen},ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8")
    native,roi_images,measurements={}, {}, {}
    warm=warm_mask(src)
    foreground=np.isin(labels3,(4,5,6,7))
    exterior_distance=cv2.distanceTransform(
        (~foreground).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    for k in "ABC":
        folder=out/k;folder.mkdir()
        layers,meta,_=native_batch(a.workspace,"V43P2b-"+k,
            native_strokes(variants[k]),folder,
            renderer_method="renderV43WideInteriorProbe")
        native[k]=layers
        crop=logical_crop(layers["composite"])
        crop.save(out/("V43P2b-"+k+"-roi.png"))
        roi_images[k]=crop
        result=native_metrics(layers,src,labels3,warm)
        tolerance={}
        for alpha in (24,128):
            by_color={str(c):overlap_by_class(
                labels3,c,layers[f"color-{c}"][:,:,3]>=alpha)
                for c in (4,5,6,7)}
            union=np.logical_or.reduce([
                layers[f"color-{c}"][:,:,3]>=alpha for c in (4,5,6,7)])
            tolerance[str(alpha)]={
                "internal_allowed":sum(r["foreign_overlap_allowed_within_3logical_px"]
                                       for r in by_color.values()),
                "internal_excess":sum(r["foreign_overlap_excess_beyond_3logical_px"]
                                      for r in by_color.values()),
                "external_excess":int(np.count_nonzero(
                    union&~foreground&(exterior_distance>9))),
            }
        result["internal_external_tolerance"]=tolerance
        result["strokes"]=len(variants[k]["strokes"])
        result["synthetic_vertices_NOT_CHALK"]=variants[k]["synthetic_vertices_NOT_CHALK"]
        result["selected_original_strokes"]=len(chosen[k])
        result["native_meta"]=meta
        measurements[k]=result
    replay=png_pixel_exact_replay(
        a.v37p2_archive/"C"/"V37P2-C-composite.png",
        out/"A"/"V43P2b-A-composite.png")
    if not replay["pixel_rgba_exact"]:
        raise ValueError("V43P2b exact source Egret A control drift")
    for k in "BC":
        if not np.array_equal(native["A"]["color-100"][:,:,3],
                              native[k]["color-100"][:,:,3]):
            raise ValueError("V43P2b dark410 contour footprint drift")
    sheet([src,roi_images["A"],roi_images["B"],roi_images["C"]],
          ["Original RGB","Unchanged V37-P2 C",
           "40 split cores width4","50 split cores width6"],
          out/"comparison-full.png")
    sheet([src,roi_images["A"],roi_images["B"],roi_images["C"]],
          ["Original","Baseline","Thin+width4","Thin+width6"],
          out/"comparison-faces.png",top=True)
    base24=measurements["A"]["native_class_metrics"]["24"]
    decisions={}
    for k in "BC":
        candidate=measurements[k]["native_class_metrics"]["24"]
        tests={
            "class7_native_own_recall_strict_gain":
                candidate["class_recall_and_overlap"]["7"]["correct_class_recall"]>
                base24["class_recall_and_overlap"]["7"]["correct_class_recall"],
            "classes4to6_native_own_recall_nonregression":all(
                candidate["class_recall_and_overlap"][str(c)]["correct_class_recall"]>=
                base24["class_recall_and_overlap"][str(c)]["correct_class_recall"]
                for c in (4,5,6)),
            "source_silhouette_recall_nonregression":
                candidate["union_source_foreground_recall"]>=
                base24["union_source_foreground_recall"],
            "native_internal_excess_nonregression_alpha24_128":all(
                measurements[k]["internal_external_tolerance"][str(a)]["internal_excess"]<=
                measurements["A"]["internal_external_tolerance"][str(a)]["internal_excess"]
                for a in (24,128)),
            "native_exterior_excess_nonregression_alpha24_128":all(
                measurements[k]["internal_external_tolerance"][str(a)]["external_excess"]<=
                measurements["A"]["internal_external_tolerance"][str(a)]["external_excess"]
                for a in (24,128)),
            "full_source_RGB_nonregression":
                measurements[k]["source_RGB_MAE"]<=measurements["A"]["source_RGB_MAE"],
            "warm_RGB_nonregression":
                measurements[k]["warm_RGB_MAE"]<=measurements["A"]["warm_RGB_MAE"],
        }
        decisions[k]={"checks":tests,"numeric_diagnostic_PASS":all(tests.values())}
    hashes={str(p.relative_to(out)).replace("\\","/"):sha(p)
            for p in out.rglob("*") if p.is_file()}
    record={
        "experiment":EXPERIMENT,"status":"ACTUAL_NATIVE_EGRET_E3_NOT_GAME",
        "source_SHA256":SOURCE_SHA,"component":component,
        "native_A_frozen_exact_RGBA":True,
        "all_original_410_dark_contours_alpha_exact":True,
        "variants":measurements,
        "predeclared_diagnostic_decisions":decisions,
        "artifact_SHA256":hashes,"production_accepted":False,"game_exact_CHALK":None,
        "not_tested":["full oriented/skeleton hybrid","resource savings","game E4",
            "E5","exact run-bound CHALK","production class coverage>=99%"],
        "versions":{"Python":platform.python_version(),"numpy":np.__version__,
                    "cv2":cv2.__version__}}
    (out/"report.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",
                                   encoding="utf-8")
    print(json.dumps({
        "selected":{k:len(chosen[k]) for k in "ABC"},
        "RGB":{k:measurements[k]["source_RGB_MAE"] for k in "ABC"},
        "decisions":decisions},indent=2))


if __name__=="__main__":main()
