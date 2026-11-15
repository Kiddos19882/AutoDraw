#!/usr/bin/env python3
"""ENGINE-001/V39: shift existing native paint y by ±0.25/0.5, retain 410 lines.

Source-neighborhood proposals are NOT brush footprints; only true Egret output
is used for measurements. Independent prereg in docs/ENGINE001_BOUNDARY_SHIFT_V39_PROTOCOL_2026-11-16.md.
"""
from __future__ import annotations
import argparse,copy,json,platform
from pathlib import Path
import cv2,numpy as np
from engine001_paint_then_detail_v35 import native_strokes
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import (
    SOURCE_SHA,sha,mae,warm_mask,png_pixel_exact_replay)
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source,quantize_case,sheet

EXPERIMENT="ENGINE001_BOUNDARY_SHIFT_V39"
SAMPLES=(0,0.25,0.5,0.75,1.0)
SCENES=("composite","color-4","color-5","color-6","color-7","color-100")

def verified_input(folder:Path)->dict:
    report=json.loads((folder/"report.json").read_text(encoding="utf-8"))
    if (report.get("experiment")!="ENGINE001_LOCAL_FILL_COLOR_V37_P2"
        or report.get("original_source_SHA256")!=SOURCE_SHA
        or report.get("V35_B_control_RGBA_pixel_exact") is not True
        or report.get("same_native_alpha_all_variants") is not True):
        raise ValueError("V39 frozen V37-P2 report identity invalid")
    for file,hash_ in report["report_linked_SHA256"].items():
        if sha(folder/file)!=hash_:
            raise ValueError("V39 frozen source input checksum drift: "+file)
    base=json.loads((folder/"color-plans.json").read_text(encoding="utf-8"))["plans"]["C"]
    if (base["paint_strokes"],base["detail_strokes"],
        base["synthetic_vertices_NOT_CHALK"],len(base["strokes"]))!=(1945,410,5682,2355):
        raise ValueError("V39 frozen V37-P2-C path count drift")
    if any(e["layer"]!="paint" or e["stroke"]["width"]!=2 or
           e["stroke"]["colorIndex"] not in (4,5,6,7) or
           len(e["stroke"]["points"])!=2 for e in base["strokes"][:1945]):
        raise ValueError("V39 frozen source fill identity invalid")
    if any(e["layer"]!="detail" or e["stroke"]["width"]!=1 or
           e["stroke"]["colorRgb"]!=0x31262B for e in base["strokes"][1945:]):
        raise ValueError("V39 all 410 full dark contours must be unchanged")
    return base

def decide_shift(stroke:dict,labels:np.ndarray)->int:
    """Only original 8-class logical labels determine the shift direction."""
    if labels.shape!=(240,460):
        raise ValueError("V39 source label shape drift")
    points=stroke["points"]
    if len(points)!=2 or stroke["width"]!=2 or stroke["colorIndex"] not in (4,5,6,7):
        raise ValueError("V39 nonfrozen paint stroke")
    y0,y1=points[0]["y"],points[1]["y"]
    if y0!=y1 or y0!=round(y0):
        raise ValueError("V39 original paint row must be integer and horizontal")
    y=int(y0)
    if not 1<=y<=238:
        return 0
    x0,x1=points[0]["x"],points[1]["x"]
    if x0>x1 or not (155<=x0<305 and 155<=x1<305):
        raise ValueError("V39 paint stroke exceeds original ROI")
    xs=[max(155,min(304,round((1-t)*x0+t*x1))) for t in SAMPLES]
    own=stroke["colorIndex"]
    top=sum(int(labels[y-1,x]==own) for x in xs)
    bottom=sum(int(labels[y+1,x]==own) for x in xs)
    return 1 if bottom-top>=2 else -1 if top-bottom>=2 else 0

def displaced(base:dict,labels:np.ndarray,amplitude:float):
    if amplitude not in (0,0.25,0.5):
        raise ValueError("V39 invalid preregistered y-shift")
    result=copy.deepcopy(base);shifts=[]
    for before,entry in zip(base["strokes"],result["strokes"]):
        if entry["layer"]=="detail":
            if before!=entry:raise ValueError("V39 detail changed")
            continue
        source=before["stroke"];s=entry["stroke"]
        direction=decide_shift(source,labels)
        delta=amplitude*direction
        if delta:
            for point in s["points"]:
                point["y"]+=delta
                if not 0<=point["y"]<240:
                    raise ValueError("V39 paint moved outside native board")
        shifts.append({"id":source["strokeId"],"dir":direction,"dy":delta})
        if any(old["x"]!=new["x"] or new["y"]-old["y"]!=delta for old,new in
            zip(source["points"],s["points"])):
            raise ValueError("V39 changed paint x or accepted point layout")
        if ({k:v for k,v in source.items() if k!="points"} !=
            {k:v for k,v in s.items() if k!="points"}):
            raise ValueError("V39 changed paint metadata/RGB/width")
    if len(shifts)!=1945 or result["synthetic_vertices_NOT_CHALK"]!=5682:
        raise ValueError("V39 synthetic resource count drift")
    return result,shifts

def native_metrics(native:dict,source,labels3:np.ndarray,warm):
    foreground=np.isin(labels3,(4,5,6,7))
    outside_dist=cv2.distanceTransform((~foreground).astype(np.uint8),
                                       cv2.DIST_L2,3)
    class_rows={}
    metrics={}
    for a in (24,128):
        union=np.zeros_like(foreground,dtype=bool)
        classes={}
        for c in (4,5,6,7):
            target=(labels3==c)
            paint=(native[f"color-{c}"][:,:,3]>=a)
            union|=paint
            classes[str(c)]={
                "correct_class_recall":float(np.count_nonzero(target&paint)/np.count_nonzero(target)),
                "correct_class_pixels":int(np.count_nonzero(target&paint)),
                "foreign_required_class_pixels":int(np.count_nonzero(
                    paint&foreground&~target))}
        correct=foreground&union
        metrics[str(a)]={
            "class_recall_and_overlap":classes,
            "union_source_foreground_recall":float(np.count_nonzero(correct)/np.count_nonzero(foreground)),
            "fill_only_precision":float(np.count_nonzero(correct)/max(1,np.count_nonzero(union))),
            "painted_more_than_3_logical_px_from_source_foreground":int(np.count_nonzero(
                union&~foreground&(outside_dist>9))),
            "fill_native_alpha_pixels":int(np.count_nonzero(union))}
    roi=logical_crop(native["composite"])
    return {"source_RGB_MAE":mae(roi,source),
            "warm_RGB_MAE":mae(roi,source,warm),
            "native_class_metrics":metrics}

def main():
    a=argparse.ArgumentParser()
    for key in ("workspace","source","v37p2-archive","output"):
        a.add_argument("--"+key,required=True,type=Path)
    args=a.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("V39 no overwrite previous evidence")
    if sha(args.source)!=SOURCE_SHA:raise ValueError("V39 original SHA drift")
    source,canvas=prepare_source(args.source)
    labels,_,skipped=quantize_case(source,canvas,8,False,True)
    if skipped!=[0,1,2,3]:
        raise ValueError("V39 original source label/skip drift")
    labels3=original_labels(args.source)
    frozen=verified_input(args.v37p2_archive)
    variants={};displacements={}
    for k,amplitude in (("A",0),("B",0.25),("C",0.5)):
        variants[k],displacements[k]=displaced(frozen,labels,amplitude)
    if [x["dir"] for x in displacements["B"]]!=[x["dir"] for x in displacements["C"]]:
        raise ValueError("V39 shift support varies between candidates")
    out=args.output;out.mkdir(parents=True)
    (out/"candidate-plans.json").write_text(json.dumps({
        "experiment":EXPERIMENT,"plans":variants,
        "displacements":displacements},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    raw={};crops={};metrics={}
    warm=warm_mask(source)
    for k in ("A","B","C"):
        target=out/k;target.mkdir()
        rgba,meta,_=native_batch(args.workspace,"V39-"+k,
            native_strokes(variants[k]),target,
            renderer_method="renderV36SourceColoredContourProbe")
        raw[k]=rgba
        crop=logical_crop(rgba["composite"]);crops[k]=crop
        crop.save(out/("V39-"+k+"-roi.png"))
        metrics[k]=native_metrics(rgba,source,labels3,warm)
        metrics[k]["modified_fill_strokes"]=sum(bool(z["dy"]) for z in displacements[k])
        metrics[k]["native_scenes"]=meta
    baseline=png_pixel_exact_replay(
        args.v37p2_archive/"C"/"V37P2-C-composite.png",
        out/"A"/"V39-A-composite.png")
    if not baseline["pixel_rgba_exact"]:
        raise ValueError("V39 frozen actual native control changed")
    if not (np.array_equal(raw["A"]["color-100"][:,:,3],raw["B"]["color-100"][:,:,3])
            and np.array_equal(raw["A"]["color-100"][:,:,3],raw["C"]["color-100"][:,:,3])):
        raise ValueError("V39 user-preferred 410 dark Egret contours alpha changed")
    sheet([source,crops["A"],crops["B"],crops["C"]],
        ["Original source","V37-P2 C unchanged A","V39 shift 0.25 B",
         "V39 shift 0.5 C"],out/"comparison-full.png")
    sheet([source,crops["A"],crops["B"],crops["C"]],
        ["Original","Frozen full outline","Shift 0.25","Shift 0.5"],
        out/"comparison-faces.png",top=True)
    decisions={}
    a24=metrics["A"]["native_class_metrics"]["24"]
    for k in ("B","C"):
        b24=metrics[k]["native_class_metrics"]["24"]
        prev=[a24["class_recall_and_overlap"][str(c)]["correct_class_recall"]
              for c in (4,5,6,7)]
        next_=[b24["class_recall_and_overlap"][str(c)]["correct_class_recall"]
               for c in (4,5,6,7)]
        decisions[k]={
            "all_class_recall_nonregression":all(b>=a for a,b in zip(prev,next_)),
            "at_least_one_class_strict_improvement":any(b>a for a,b in zip(prev,next_)),
            "foreground_recall_nonregression":b24["union_source_foreground_recall"]>=
                 a24["union_source_foreground_recall"],
            "no_additional_exterior_beyond_3logical_px":
                 b24["painted_more_than_3_logical_px_from_source_foreground"]<=
                 a24["painted_more_than_3_logical_px_from_source_foreground"],
            "full_RGB_MAE_nonregression":metrics[k]["source_RGB_MAE"]<=metrics["A"]["source_RGB_MAE"],
            "warm_RGB_MAE_nonregression":metrics[k]["warm_RGB_MAE"]<=metrics["A"]["warm_RGB_MAE"]}
    hashes={str(p.relative_to(out)).replace("\\","/"):sha(p)
            for p in out.rglob("*") if p.is_file()}
    report={"experiment":EXPERIMENT,"status":"NATIVE_EGRET_NOT_GAME",
        "source_SHA256":SOURCE_SHA,
        "V37P2_C_control_pixel_exact":True,
        "dark_contour_alpha_pixel_exact_all":True,
        "strokes":2355,"synthetic_vertices_NOT_CHALK":5682,
        "measured":metrics,"preregistered_diagnostics":decisions,
        "artifact_SHA256":hashes,"quality_accepted":False,
        "exact_game_CHALK":None,"not_tested":["real live E4","independent E5",
                           "production per-color >=99% acceptance"],
        "versions":{"Python":platform.python_version(),"numpy":np.__version__,
                    "OpenCV":cv2.__version__}}
    (out/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"result":decisions,
        "MAE":{k:(metrics[k]["source_RGB_MAE"],metrics[k]["warm_RGB_MAE"])
               for k in "ABC"}},indent=2))

if __name__=="__main__":
    main()
