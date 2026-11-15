#!/usr/bin/env python3
"""ENGINE-001/V37-P2: source-local paint RGB, preserving all V35-B dark outlines.

Synthetic color samples select RGB only. Native Egret determines brush footprint.
"""
from __future__ import annotations
import argparse,copy,json,platform
from pathlib import Path
import numpy as np
from engine001_paint_then_detail_v35 import native_strokes
from run_engine001_full_outline_native_v37 import frozen_full_outline
from run_engine001_native_warm_color_v34 import (
    SOURCE_SHA,sha,mae,warm_mask,png_pixel_exact_replay)
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import (
    prepare_source,quantize_case,sheet)

EXP="ENGINE001_LOCAL_FILL_COLOR_V37_P2"
SAMPLES=(0.0,0.25,0.5,0.75,1.0)

def source_samples(stroke,source,labels,warm):
    """Five frozen scanline samples with class filter; no modeled brush claim."""
    points=stroke["points"]
    if (stroke["width"]!=2 or stroke["colorIndex"] not in (4,5,6,7)
        or len(points)!=2):
        raise ValueError("V37-P2 fill stroke is not frozen native width2 pair")
    arr=np.asarray(source.convert("RGB"),dtype=np.uint8)
    if arr.shape!=(240,150,3) or labels.shape!=(240,460) or warm.shape!=(240,150):
        raise ValueError("V37-P2 original source/quantized mask shape drift")
    p0,p1=points
    taken=[];warm_taken=[];coords=[]
    for t in SAMPLES:
        x=round((1-t)*p0["x"]+t*p1["x"])
        y=round((1-t)*p0["y"]+t*p1["y"])
        x=max(155,min(304,x));y=max(0,min(239,y))
        if labels[y,x]!=stroke["colorIndex"]:continue
        rgb=arr[y,x].tolist()
        taken.append(rgb);coords.append([x,y])
        if warm[y,x-155]:warm_taken.append(rgb)
    return taken,warm_taken,coords

def lower_median(rows):
    if not rows:raise ValueError("V37-P2 cannot median empty source samples")
    arr=np.asarray(rows,dtype=np.uint8)
    return [int(np.sort(arr[:,i])[(len(arr)-1)//2]) for i in range(3)]

def recolor_paint(base,source,labels,warm,variant):
    if variant not in ("A","B","C"):
        raise ValueError("V37-P2 unknown candidate")
    result=copy.deepcopy(base)
    journal=[];changed=0
    for entry in result["strokes"]:
        s=entry["stroke"]
        if entry["layer"]=="detail":
            continue
        if entry["layer"]!="paint":raise ValueError("V37-P2 invalid layer")
        owned,warm_owned,coords=source_samples(s,source,labels,warm)
        if variant=="B" and len(owned)>=3:
            used=lower_median(owned)
        elif variant=="C" and len(owned)>=3 and len(warm_owned)>=3:
            used=lower_median(warm_owned)
        else:
            used=[(s["colorRgb"]>>16)&255,(s["colorRgb"]>>8)&255,
                  s["colorRgb"]&255]
        old=s["colorRgb"]
        new=(used[0]<<16)|(used[1]<<8)|used[2]
        s["colorRgb"]=new
        changed+=int(new!=old)
        journal.append({"id":s["strokeId"],"class":s["colorIndex"],
            "original_RGB":old,"assigned_RGB":new,
            "owned_samples":len(owned),"warm_owned_samples":len(warm_owned),
            "source_coords":coords})
    if len(journal)!=1945 or result["detail_strokes"]!=410 or (
            result["synthetic_vertices_NOT_CHALK"]!=5682):
        raise ValueError("V37-P2 frozen color fill/detail count drift")
    for old,new in zip(base["strokes"],result["strokes"]):
        if old["layer"]!=new["layer"]:
            raise ValueError("V37-P2 changed layer order")
        if old["layer"]=="detail" and old!=new:
            raise ValueError("V37-P2 changed user-preferred V35-B dark contours")
        if old["layer"]=="paint" and (
            {k:v for k,v in old["stroke"].items() if k!="colorRgb"} !=
            {k:v for k,v in new["stroke"].items() if k!="colorRgb"}):
            raise ValueError("V37-P2 changed source paint geometry")
    return result,journal,changed

def main():
    ap=argparse.ArgumentParser()
    for n in ("workspace","source","v35-archive","output"):
        ap.add_argument("--"+n,type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V37-P2 refuse existing evidence dir")
    if sha(a.source)!=SOURCE_SHA:
        raise ValueError("V37-P2 original source SHA drift")
    source,canvas=prepare_source(a.source)
    labels,palette,skipped=quantize_case(source,canvas,8,False,True)
    if skipped!=[0,1,2,3]:
        raise ValueError("V37-P2 frozen source palette drift")
    warm=warm_mask(source)
    base=frozen_full_outline(a.v35_archive)
    variants={};journals={};counts={}
    for key in ("A","B","C"):
        variants[key],journals[key],counts[key]=recolor_paint(
            base,source,labels,warm,key)
    out=a.output;out.mkdir(parents=True)
    (out/"color-plans.json").write_text(json.dumps({
        "experiment":EXP,"recolored_fill_strokes":counts,
        "stroke_source_samples":journals,"plans":variants},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    raw={};crop={};metrics={}
    for key in ("A","B","C"):
        directory=out/key;directory.mkdir()
        scenes,meta,_=native_batch(
            a.workspace,"V37P2-"+key,native_strokes(variants[key]),directory,
            renderer_method="renderV36SourceColoredContourProbe")
        raw[key]=scenes
        image=logical_crop(scenes["composite"]);crop[key]=image
        image.save(out/("V37P2-"+key+"-roi.png"))
        rgb=[e["stroke"]["colorRgb"] for e in variants[key]["strokes"][:1945]]
        metrics[key]={
            "full_RGB_MAE":mae(image,source),
            "warm_RGB_MAE":mae(image,source,warm),
            "native_composite_alpha24_pixels":int(np.count_nonzero(
                scenes["composite"][:,:,3]>=24)),
            "native_composite_alpha128_pixels":int(np.count_nonzero(
                scenes["composite"][:,:,3]>=128)),
            "changed_fill_strokes":counts[key],
            "paint_distinct_RGB":len(set(rgb)),
            "paint_color_switches":sum(rgb[i]!=rgb[i-1] for i in range(1,len(rgb))),
            "synthetic_accepted_vertices_NOT_CHALK":5682,
            "complete_detail_strokes":410,
            "native_metadata":meta}
    replay=png_pixel_exact_replay(
        a.v35_archive/"B"/"V35-B-composite.png",
        out/"A"/"V37P2-A-composite.png")
    for stem in ["composite","color-100"]+[f"color-{n}" for n in (4,5,6,7)]:
        if not (np.array_equal(raw["A"][stem][:,:,3],raw["B"][stem][:,:,3])
                and np.array_equal(raw["A"][stem][:,:,3],raw["C"][stem][:,:,3])):
            raise ValueError("V37-P2 actual Egret alpha footprint changed "+stem)
    sheet([source,crop["A"],crop["B"],crop["C"]],
        ["Original RGB","V35-B unchanged A","Local source fill B","Warm-only fill C"],
        out/"comparison-full.png")
    sheet([source,crop["A"],crop["B"],crop["C"]],
        ["Original","V35-B dark lines","Local source fill","Warm fill only"],
        out/"comparison-faces.png",top=True)
    diagnostics={k:{
        "full_MAE_lower_than_A":metrics[k]["full_RGB_MAE"]<metrics["A"]["full_RGB_MAE"],
        "warm_MAE_lower_than_A":metrics[k]["warm_RGB_MAE"]<metrics["A"]["warm_RGB_MAE"]
        } for k in ("B","C")}
    hashes={str(p.relative_to(out)).replace("\\","/"):sha(p)
            for p in out.rglob("*") if p.is_file()}
    report={"experiment":EXP,"status":"EGRET_NATIVE_E3_NOT_GAME",
        "original_source_SHA256":SOURCE_SHA,
        "V35_B_control_RGBA_pixel_exact":replay["pixel_rgba_exact"],
        "same_native_alpha_all_variants":True,
        "warm_source_pixels":int(np.count_nonzero(warm)),
        "metrics":metrics,"color_diagnostic":diagnostics,
        "report_linked_SHA256":hashes,
        "quality_accepted":False,"exact_CHALK":None,
        "not_tested":["live E4","independent E5",
          "per-color>=99% acceptance","game quota safety margin"],
        "versions":{"python":platform.python_version(),"numpy":np.__version__}}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"changed":counts,"metrics":{
         k:{name:metrics[k][name] for name in (
         "full_RGB_MAE","warm_RGB_MAE","paint_color_switches")}
         for k in ("A","B","C")},"diagnostic":diagnostics},indent=2))

if __name__=="__main__":
    main()
