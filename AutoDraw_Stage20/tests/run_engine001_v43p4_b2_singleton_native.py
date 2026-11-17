#!/usr/bin/env python3
"""V43-P4 B2: isolate real Egret 0.25 logical-px singleton micro-strokes.

No full B2 planner, no Stage6, no game CHALK.
"""
from __future__ import annotations
import argparse, hashlib, json, math, platform
from pathlib import Path
import cv2
import numpy as np
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import SOURCE_SHA, sha
from run_engine001_complex_holdout_v5 import native_batch

EXP="ENGINE001_V43P4_B2_NATIVE_SINGLETON_MICRO_STROKE_PROBE"
OWNERS=(4,5,6,7)
WIDTHS=(2,4)
OWNER_RGB={4:15921900,5:14466476,6:11174513,7:5191999}
ALPHAS=(24,128)
NATIVE=(720,1380)

def select_singletons(logical):
    if (not isinstance(logical,np.ndarray) or logical.shape!=(240,460)
            or logical.dtype.kind not in "iu" or
            np.any((logical < -1)|(logical > 7))):
        raise ValueError("B2 source label shape/type invalid")
    picked=[]
    for owner in OWNERS:
        count,components,stats,_=cv2.connectedComponentsWithStats(
            (logical==owner).astype(np.uint8),connectivity=8)
        positions=sorted((int(stats[i,cv2.CC_STAT_TOP]),
                          int(stats[i,cv2.CC_STAT_LEFT]))
                         for i in range(1,count)
                         if stats[i,cv2.CC_STAT_AREA]==1)
        owner_count=0
        for y,x in positions:
            if not (156<=x<=303 and 1<=y<=238):
                continue
            if any(math.hypot(x-s["x"],y-s["y"])<15 for s in picked):
                continue
            picked.append({"id":f"singleton-{owner}-{owner_count}",
                           "owner":owner,"x":x,"y":y,
                           "direction":"horizontal" if len(picked)%2==0
                           else "vertical"})
            owner_count+=1
            if owner_count==3:break
        if owner_count!=3:raise ValueError("BLOCKED_SAMPLE B2 insufficient owner singleton")
    if len(picked)!=12:raise ValueError("B2 wrong sample count")
    return picked

def make_strokes(samples,width):
    if width not in WIDTHS or len(samples)!=12:
        raise ValueError("B2 unsupported width/sample count")
    strokes=[]
    for i,s in enumerate(samples):
        x,y=s["x"],s["y"]
        if s["direction"]=="horizontal":
            points=[{"x":x+.125,"y":y},{"x":x+.375,"y":y}]
        elif s["direction"]=="vertical":
            points=[{"x":x,"y":y+.125},{"x":x,"y":y+.375}]
        else:raise ValueError("B2 direction drift")
        strokes.append({"strokeId":f"icon-{i}","colorIndex":s["owner"],
                        "colorRgb":OWNER_RGB[s["owner"]],"width":width,
                        "points":points})
    if any(math.hypot(p["points"][1]["x"]-p["points"][0]["x"],
                      p["points"][1]["y"]-p["points"][0]["y"])!=.25
           for p in strokes):
        raise ValueError("B2 fractional length drift")
    return strokes

def native_metrics(native,labels3,samples):
    if labels3.shape!=NATIVE or len(samples)!=12 or set(native)!={
            "composite","color-4","color-5","color-6","color-7"}:
        raise ValueError("B2 wrong native scene/label identity")
    if any(a.shape!=(*NATIVE,4) or a.dtype!=np.uint8
           for a in native.values()):
        raise ValueError("B2 actual native RGBA shape invalid")
    foreground=np.isin(labels3,OWNERS)
    exterior_dist=cv2.distanceTransform(
        (~foreground).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    data={}
    for alpha in ALPHAS:
        by_owner={}
        for owner in OWNERS:
            ink=native[f"color-{owner}"][:,:,3]>=alpha
            own=labels3==owner
            dist=cv2.distanceTransform(
                (~own).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
            foreign=ink&foreground&~own
            samples_data=[]
            for s in samples:
                if s["owner"]!=owner:continue
                x,y=s["x"],s["y"]
                tile=ink[3*y:3*y+3,3*x:3*x+3]
                if tile.shape!=(3,3):raise ValueError("B2 tile outside backing")
                samples_data.append({"id":s["id"],"pixels":int(tile.sum()),
                                     "hit":bool(tile.any())})
            by_owner[str(owner)]={
                "samples":samples_data,
                "samples_hit":sum(x["hit"] for x in samples_data),
                "fraction_of_target_3x3_pixels_hit":
                     sum(x["pixels"] for x in samples_data)/(9*len(samples_data)),
                "source_owner_ink_pixels":int((ink&own).sum()),
                "foreign_required_pixels":int(foreign.sum()),
                "foreign_beyond_3logicalpx":int((foreign&(dist>9)).sum()),
                "outside_silhouette_beyond_3logicalpx":int(
                    (ink&~foreground&(exterior_dist>9)).sum()),
                "all_native_alpha_positive_pixels":int(ink.sum()),
            }
        data[str(alpha)]=by_owner
    return data

def main():
    p=argparse.ArgumentParser()
    for n in ("workspace","source","output"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError("B2 refuse overwrite")
    if sha(a.source)!=SOURCE_SHA:raise ValueError("B2 frozen source SHA mismatch")
    labels3=original_labels(a.source)
    logical=labels3[::3,::3].copy()
    samples=select_singletons(logical)
    a.output.mkdir(parents=True)
    (a.output/"selection.json").write_text(json.dumps({
        "experiment":EXP,"source_sha256":SOURCE_SHA,
        "logical_labels_sha256":hashlib.sha256(logical.tobytes()).hexdigest(),
        "samples":samples,"widths":list(WIDTHS),
        "micro_segment_length_logical_px":.25,
        "min_sample_spacing_logical_px":15,
        "frozen_owner_RGB":{str(k):v for k,v in OWNER_RGB.items()},
        "safe_to_execute":False,"exact_CHALK":None},
        ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    results={}
    for width in WIDTHS:
        target=a.output/f"width-{width}"
        target.mkdir()
        paths=make_strokes(samples,width)
        images,meta,_=native_batch(a.workspace,f"V43P4B2-w{width}",
            paths,target,renderer_method="renderComplexHoldoutColorProbe")
        if not images["composite"][:,:,3].any():
            raise ValueError("B2 actual Egret no ink")
        results[str(width)]={
            "stroke_count":len(paths),"synthetic_vertices_NOT_CHALK":24,
            "paths":paths,"metadata":meta,
            "alpha24_128_native":native_metrics(images,labels3,samples),
        }
    checks={str(f.relative_to(a.output)).replace("\\","/"):sha(f)
            for f in a.output.rglob("*") if f.is_file()}
    report={"experiment":EXP,"status":"E3_REAL_EGRET_ISOLATED_NOT_B2_FULL",
            "source_sha256":SOURCE_SHA,"samples":samples,
            "results":results,"report_linked_SHA256":checks,
            "full_B2_quality":"NOT_RUN","E4":"NOT_RUN",
            "E5":"NOT_RUN","game_CHALK":None,
            "production_accepted":False,
            "versions":{"Python":platform.python_version(),
                        "numpy":np.__version__,"cv2":cv2.__version__}}
    (a.output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({w:{k:{c:{"hit":v["samples_hit"],
       "foreign":v["foreign_required_pixels"],
       "foreign_over3":v["foreign_beyond_3logicalpx"]}
       for c,v in by.items()}
       for k,by in result["alpha24_128_native"].items()}
       for w,result in results.items()},ensure_ascii=False))

if __name__=="__main__":
    main()
