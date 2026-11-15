#!/usr/bin/env python3
"""ENGINE-001 V37-P1: user-preferred complete V35-B outline, native color A/B/C.

Only 410 detail stroke colors change. All paths/width/order/source fill frozen.
Real archived BoardPane/Egret WebGL, no game E4 or exact CHALK.
"""
from __future__ import annotations
import argparse,copy,json,platform
from pathlib import Path
import numpy as np
from engine001_paint_then_detail_v35 import native_strokes
from run_engine001_source_color_contour_native_v36 import (
    DARK, medians_for_path, frozen_v35)
from run_engine001_native_warm_color_v34 import (
    SOURCE_SHA,sha,mae,warm_mask,png_pixel_exact_replay)
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source,sheet

EXPERIMENT="ENGINE001_FULL_OUTLINE_V37_P1"
DETAIL_COUNT=410
STROKES=2355
VERTICES=5682

def frozen_full_outline(v35:Path):
    # Existing V36 verifier checks all V35 report-linked source SHA files.
    frozen_v35(v35)
    plans=json.loads((v35/"plans.json").read_text(encoding="utf-8"))
    base=plans["B"]
    if (base["paint_strokes"],base["detail_strokes"],
            base["synthetic_vertices_NOT_CHALK"])!=(1945,DETAIL_COUNT,VERTICES):
        raise ValueError("V37-P1 frozen V35-B complete outline count changed")
    if len(base["strokes"])!=STROKES or [e["layer"] for e in base["strokes"]] != (
            ["paint"]*1945+["detail"]*DETAIL_COUNT):
        raise ValueError("V37-P1 frozen V35-B layer order/count changed")
    if any(s["stroke"]["width"]!=1 or
           s["stroke"]["colorRgb"]!=0x31262B or
           not s["stroke"]["strokeId"].startswith("detail-v18-B-")
           for s in base["strokes"][1945:]):
        raise ValueError("V37-P1 user-preferred V35-B detail identity drift")
    if any(s["stroke"]["width"]!=2 or
           s["stroke"]["colorIndex"] not in (4,5,6,7)
           for s in base["strokes"][:1945]):
        raise ValueError("V37-P1 native fill drift")
    return base

def full_recolor(base,original,variant):
    if variant not in ("A","B","C"):
        raise ValueError("V37-P1 candidate must be A, B or C")
    result=copy.deepcopy(base)
    candidates=[]
    for entry in result["strokes"]:
        if entry["layer"]!="detail":continue
        s=entry["stroke"]
        sampled=medians_for_path(original,s["points"])
        rgb=(list(DARK) if variant=="A" else sampled if variant=="B"
             else [(DARK[i]+sampled[i]+1)//2 for i in range(3)])
        s["colorRgb"]=(rgb[0]<<16)|(rgb[1]<<8)|rgb[2]
        candidates.append({"id":s["strokeId"],"original_median_RGB":sampled,
                           "assigned_RGB":rgb})
    if len(candidates)!=DETAIL_COUNT or len(result["strokes"])!=STROKES:
        raise ValueError("V37-P1 missing complete contour geometry")
    for x,y in zip(base["strokes"],result["strokes"]):
        if x["layer"]!=y["layer"]:
            raise ValueError("V37-P1 layer order drift")
        if x["layer"]=="paint" and x!=y:
            raise ValueError("V37-P1 frozen fill modified")
        if x["layer"]=="detail" and (
            {k:v for k,v in x["stroke"].items() if k!="colorRgb"} !=
            {k:v for k,v in y["stroke"].items() if k!="colorRgb"}):
            raise ValueError("V37-P1 detail geometry modified")
    return result,candidates

def main():
    ap=argparse.ArgumentParser()
    for n in ("workspace","source","v35-archive","output"):
        ap.add_argument("--"+n,required=True,type=Path)
    a=ap.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V37-P1 evidence directory must be empty")
    if sha(a.source)!=SOURCE_SHA:
        raise ValueError("V37-P1 original source hash drift")
    source,_=prepare_source(a.source)
    base=frozen_full_outline(a.v35_archive)
    candidates={};plans={}
    for k in ("A","B","C"):
        plans[k],candidates[k]=full_recolor(base,source,k)
    out=a.output;out.mkdir(parents=True)
    (out/"color-plans.json").write_text(json.dumps({
        "experiment":EXPERIMENT,"variants":candidates,"plans":plans},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    native={};crop={};metrics={}
    warm=warm_mask(source)
    for key in ("A","B","C"):
        sub=out/key;sub.mkdir()
        layers,metadata,_=native_batch(a.workspace,"V37-"+key,
            native_strokes(plans[key]),sub,
            renderer_method="renderV36SourceColoredContourProbe")
        native[key]=layers
        img=logical_crop(layers["composite"]);crop[key]=img
        img.save(out/("V37-"+key+"-roi.png"))
        details=plans[key]["strokes"][1945:]
        rgb=[s["stroke"]["colorRgb"] for s in details]
        metrics[key]={
            "full_RGB_MAE":mae(img,source),
            "warm_RGB_MAE":mae(img,source,warm),
            "native_alpha24_composite":int(np.count_nonzero(
                layers["composite"][:,:,3]>=24)),
            "native_alpha128_composite":int(np.count_nonzero(
                layers["composite"][:,:,3]>=128)),
            "total_strokes":STROKES,"detail_strokes":DETAIL_COUNT,
            "synthetic_accepted_vertices_NOT_CHALK":VERTICES,
            "distinct_contour_RGB":len(set(rgb)),
            "detail_color_switches":sum(rgb[i]!=rgb[i-1] for i in range(1,len(rgb))),
            "native_metadata":metadata}
    replay=png_pixel_exact_replay(
        a.v35_archive/"B"/"V35-B-composite.png",
        out/"A"/"V37-A-composite.png")
    for stem in ["composite","color-100"]+[f"color-{n}" for n in (4,5,6,7)]:
        if not (np.array_equal(native["A"][stem][:,:,3],native["B"][stem][:,:,3])
                and np.array_equal(native["A"][stem][:,:,3],native["C"][stem][:,:,3])):
            raise ValueError("V37-P1 actual Egret native alpha mismatch "+stem)
    sheet([source,crop["A"],crop["B"],crop["C"]],
        ["Original RGB","V35-B original full outline","V37 source-color full outline",
         "V37 half-tint full outline"],out/"comparison-full.png")
    sheet([source,crop["A"],crop["B"],crop["C"]],
        ["Original RGB","V35-B full dark","V37 source-color","V37 half-tint"],
        out/"comparison-faces.png",top=True)
    diag={k:{"full_MAE_lower_than_A":metrics[k]["full_RGB_MAE"]<
             metrics["A"]["full_RGB_MAE"],
             "warm_MAE_lower_than_A":metrics[k]["warm_RGB_MAE"]<
             metrics["A"]["warm_RGB_MAE"]}
           for k in ("B","C")}
    checksums={str(p.relative_to(out)).replace("\\","/"):sha(p)
               for p in out.rglob("*") if p.is_file()}
    report={"experiment":EXPERIMENT,"status":"REAL_EGRET_E3_DIAGNOSTIC_NOT_GAME",
            "source_sha256":SOURCE_SHA,
            "baseline":"CI43742747278 artifact14173635779 V35-B",
            "control_V35B_RGBA_exact":replay["pixel_rgba_exact"],
            "native_alpha_exact_all_variants":True,
            "warm_source_pixels":int(warm.sum()),"metrics":metrics,
            "color_only_diagnostic":diag,"artifact_sha256":checksums,
            "quality_accepted":False,"exact_CHALK":None,
            "not_tested":["real game E4","independent E5",
                          "per-color native >=99% full quality"],
            "versions":{"Python":platform.python_version(),"numpy":np.__version__}}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"metrics":{k:{x:v[x] for x in (
        "full_RGB_MAE","warm_RGB_MAE","distinct_contour_RGB",
        "detail_color_switches")} for k,v in metrics.items()},
        "diagnostic":diag},indent=2))

if __name__=="__main__":
    main()
