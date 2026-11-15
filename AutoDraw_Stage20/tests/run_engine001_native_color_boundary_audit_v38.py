#!/usr/bin/env python3
"""ENGINE-001 V38: immutable true-Egret native color-boundary coverage audit.

This reads archived V37-P2 PNG alpha, never approximates a game brush.
"""
from __future__ import annotations
import argparse, hashlib, io, json, platform
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
EXPERIMENT="ENGINE001_NATIVE_COLOR_BOUNDARY_AUDIT_V38"
SOURCE_EXPERIMENT="ENGINE001_LOCAL_FILL_COLOR_V37_P2"
COLORS=(4,5,6,7)
ALPHAS=(24,128)
SCENES=("composite","color-4","color-5","color-6","color-7","color-100")
NATIVE_SHAPE=(720,1380,4)

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_native(directory:Path,variant:str,scene:str)->np.ndarray:
    name=f"V37P2-{variant}-{scene}.png"
    with Image.open(directory/variant/name) as img:
        rgba=np.asarray(img.convert("RGBA")).copy()
    if rgba.shape!=NATIVE_SHAPE:
        raise ValueError("V38 native PNG shape changed: "+name)
    return rgba

def original_labels(path:Path)->np.ndarray:
    if sha(path)!=SOURCE_SHA:
        raise ValueError("V38 source SHA drift")
    with Image.open(path) as img:
        if img.size!=(200,320):
            raise ValueError("V38 source size changed")
        roi=img.convert("RGB").resize((150,240),Image.Resampling.LANCZOS)
    quant=roi.quantize(colors=8,method=Image.Quantize.MEDIANCUT,
                       dither=Image.Dither.NONE)
    palette=quant.getpalette()
    if [palette[i*3:i*3+3] for i in range(8)]!=[
        [255,255,255],[255,254,255],[255,255,253],[252,254,250],
        [245,245,240],[225,201,180],[159,122,112],[74,49,55]]:
        raise ValueError("V38 MEDIANCUT palette changed")
    raw=np.asarray(quant,dtype=np.int16)
    board=np.full((240,460),-1,np.int16)
    board[:,155:305]=raw
    return np.repeat(np.repeat(board,3,0),3,1)

def components(missing:np.ndarray)->dict:
    if missing.dtype!=np.bool_:
        raise ValueError("V38 missing mask must be bool")
    total,labels,stats,centroids=cv2.connectedComponentsWithStats(
        missing.astype(np.uint8),connectivity=8)
    sizes=np.asarray(stats[1:,cv2.CC_STAT_AREA],dtype=np.int64)
    top_indices=sorted(range(len(sizes)),key=lambda i:(-int(sizes[i]),i))[:10]
    return {
        "count":int(total-1),
        "areas_ge_9_native_px":int(np.count_nonzero(sizes>=9)),
        "areas_ge_36_native_px":int(np.count_nonzero(sizes>=36)),
        "areas_ge_144_native_px":int(np.count_nonzero(sizes>=144)),
        "top_largest":[{"area_native_px":int(sizes[i]),
                        "logical_x":float(centroids[i+1][0]/3),
                        "logical_y":float(centroids[i+1][1]/3)}
                       for i in top_indices]
    }

def class_metrics(target:np.ndarray,painted:np.ndarray,
                  foreground:np.ndarray,roi:np.ndarray)->dict:
    if (target.dtype!=np.bool_ or painted.dtype!=np.bool_ or
            target.shape!=painted.shape or target.shape!=foreground.shape):
        raise ValueError("V38 incompatible native masks")
    target_n=int(target.sum())
    if target_n==0:raise ValueError("V38 empty required source class")
    correct=target & painted
    missed=target & ~painted
    distance=cv2.distanceTransform(target.astype(np.uint8),
                                    cv2.DIST_L2,3)
    interior=distance>=3.0
    return {
        "target_native_pixels":target_n,
        "painted_target_native_pixels":int(correct.sum()),
        "native_recall":float(correct.sum()/target_n),
        "missed_target_native_pixels":int(missed.sum()),
        "missed_class_interior_distance_ge_3_native_px":int(
            np.count_nonzero(missed & interior)),
        "target_class_interior_distance_ge_3_native_px":int(
            np.count_nonzero(interior)),
        "foreign_required_class_painted_native_pixels":int(
            np.count_nonzero(painted & foreground & ~target)),
        "skipped_near_white_painted_native_pixels":int(
            np.count_nonzero(painted & ~foreground & roi)),
        "outside_logical_artwork_ROI_native_pixels":int(
            np.count_nonzero(painted & ~roi)),
        "missed_components":components(missed),
    }

def audit(source:Path, archive:Path, out:Path)->dict:
    if out.exists() and any(out.iterdir()):
        raise ValueError("V38 cannot overwrite evidence")
    native_labels=original_labels(source)
    report=json.loads((archive/"report.json").read_text(encoding="utf-8"))
    if report.get("experiment")!=SOURCE_EXPERIMENT or (
        report.get("original_source_SHA256")!=SOURCE_SHA or
        report.get("V35_B_control_RGBA_pixel_exact") is not True or
        report.get("same_native_alpha_all_variants") is not True):
        raise ValueError("V38 source V37-P2 report identity invalid")
    for name,digest in report["report_linked_SHA256"].items():
        if sha(archive/name)!=digest:
            raise ValueError("V38 report-linked input checksum drift: "+name)
    native={}
    for scene in SCENES:
        images={v:load_native(archive,v,scene) for v in "ABC"}
        if not (np.array_equal(images["A"][:,:,3],images["B"][:,:,3])
                and np.array_equal(images["A"][:,:,3],images["C"][:,:,3])):
            raise ValueError("V38 actual native A/B/C alpha differs: "+scene)
        native[scene]=images["C"][:,:,3]
    foreground=np.isin(native_labels,COLORS)
    roi=np.zeros(foreground.shape,dtype=bool);roi[:,155*3:305*3]=True
    source_boundary_distance=cv2.distanceTransform(
        (~foreground).astype(np.uint8),cv2.DIST_L2,3)
    measurements={}
    for alpha in ALPHAS:
        union=np.zeros_like(foreground,dtype=bool)
        by_class={}
        for c in COLORS:
            target=native_labels==c
            painted=native[f"color-{c}"]>=alpha
            union|=painted
            by_class[str(c)]=class_metrics(target,painted,foreground,roi)
        correct=foreground&union
        missed=foreground&~union
        outside=union&~foreground
        far=outside&(source_boundary_distance>9.0)
        measurements[str(alpha)]={
            "per_source_class":by_class,
            "foreground_target_native_pixels":int(foreground.sum()),
            "foreground_correct_native_pixels":int(correct.sum()),
            "foreground_recall":float(correct.sum()/foreground.sum()),
            "fill_only_precision":float(correct.sum()/max(1,int(union.sum()))),
            "foreground_missed_native_pixels":int(missed.sum()),
            "foreground_missed_components":components(missed),
            "painted_outside_source_quantized_foreground_native_pixels":int(outside.sum()),
            "painted_more_than_3_logical_px_from_source_foreground_native_pixels":int(
                far.sum()),
            "painted_outside_original_artwork_ROI_native_pixels":int(
                np.count_nonzero(union&~roi)),
            "composite_with_details_native_alpha_pixels":int(
                np.count_nonzero(native["composite"]>=alpha))
        }
    out.mkdir(parents=True)
    data={
        "experiment":EXPERIMENT,
        "scope":"E2 archived native PNG analysis only; NO new Egret brush render",
        "original_source_SHA256":SOURCE_SHA,
        "input_report_SHA256":sha(archive/"report.json"),
        "frozen_native_run":"43747149144",
        "frozen_native_commit":"04e506a3bf41b5d197a19bb20e36e8f445d79dec",
        "native_alpha_A_B_C_pixel_identical":True,
        "source_preprocessing":"Pillow LANCZOS150x240 MEDIANCUT8 no dither, 3x native",
        "native_footprint_source":"Archived actual Egret BoardPane PNG alpha",
        "alpha_threshold_measurements":measurements,
        "not_tested":["new brush quality","new placement","game exact CHALK",
                      "E4 live","independent E5","99% required per-color acceptance"],
        "versions":{"Python":platform.python_version(),"numpy":np.__version__,
                    "OpenCV":cv2.__version__,"Pillow":Image.__version__}
    }
    (out/"audit.json").write_text(json.dumps(
        data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return data

def main():
    p=argparse.ArgumentParser()
    for name in ("source","v37p2-archive","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    data=audit(a.source,a.v37p2_archive,a.output)
    compact={k:{"classes":{n:{"recall":v["native_recall"],
         "missed":v["missed_target_native_pixels"],
         "interior_missed":v["missed_class_interior_distance_ge_3_native_px"]}
         for n,v in m["per_source_class"].items()},
        "foreground_recall":m["foreground_recall"],
        "distant_exterior":m[
            "painted_more_than_3_logical_px_from_source_foreground_native_pixels"]}
        for k,m in data["alpha_threshold_measurements"].items()}
    print(json.dumps(compact,indent=2))

if __name__=="__main__":
    main()
