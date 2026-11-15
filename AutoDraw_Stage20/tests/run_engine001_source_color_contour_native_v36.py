#!/usr/bin/env python3
"""V36 source-aware contour RGB, frozen V35 C geometry, native Egret A/B/C."""
from __future__ import annotations
import argparse,copy,hashlib,json,platform
from pathlib import Path
import numpy as np
from PIL import Image
from engine001_paint_then_detail_v35 import native_strokes
from run_engine001_native_warm_color_v34 import SOURCE_SHA,sha,mae,warm_mask,png_pixel_exact_replay
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source,sheet

EXPERIMENT="ENGINE001_SOURCE_COLOR_CONTOUR_V36"
V35_ZIP_SHA="350892e45a1941072e0dc3b590d348ea817d0ee8f7daf004915e683a3368f170"
DARK=(49,38,43)

def medians_for_path(original:Image.Image, points:list[dict]):
    arr=np.asarray(original.convert("RGB"),dtype=np.uint8)
    if arr.shape!=(240,150,3) or not points:
        raise ValueError("V36 original ROI shape or detail points invalid")
    values=[]
    for p in points:
        x,y=float(p["x"]),float(p["y"])
        if not np.isfinite(x) or not np.isfinite(y) or not (155<=x<305 and 0<=y<240):
            raise ValueError("V36 detail sample outside source ROI")
        ix=max(0,min(149,round(x-155)))
        iy=max(0,min(239,round(y)))
        values.append(arr[iy,ix])
    values=np.asarray(values,dtype=np.uint8)
    return [int(np.sort(values[:,channel])[(len(values)-1)//2]) for channel in range(3)]

def recolor(base:dict, source:Image.Image, variant:str):
    if variant not in ("A","B","C"):raise ValueError("V36 invalid candidate")
    candidate=copy.deepcopy(base)
    details=[]
    for record in candidate["strokes"]:
        s=record["stroke"]
        if record["layer"]=="paint":
            continue
        if record["layer"]!="detail" or s["width"]!=1 or s["colorRgb"]!=0x31262B:
            raise ValueError("V36 frozen V18-B detail identity changed")
        local=medians_for_path(source,s["points"])
        if variant=="B":new=local
        elif variant=="C":new=[(DARK[i]+local[i]+1)//2 for i in range(3)]
        else:new=list(DARK)
        s["colorRgb"]=new[0]*65536+new[1]*256+new[2]
        details.append({"sourceId":s["strokeId"],"source_median_rgb":local,
                        "used_rgb":new})
    if len(details)!=297 or candidate["synthetic_vertices_NOT_CHALK"]!=5269:
        raise ValueError("V36 count/vertex drift")
    if any(x["stroke"]!=y["stroke"] for x,y in zip(base["strokes"],candidate["strokes"])
           if x["layer"]=="paint"):
        raise ValueError("V36 fill stroke mutation")
    if any({k:v for k,v in x["stroke"].items() if k!="colorRgb"}!=
           {k:v for k,v in y["stroke"].items() if k!="colorRgb"}
           for x,y in zip(base["strokes"],candidate["strokes"])):
        raise ValueError("V36 mutated frozen detail route")
    return candidate,details

def frozen_v35(folder:Path):
    report=json.loads((folder/"report.json").read_text(encoding="utf-8"))
    if report["experiment"]!="ENGINE001_PAINT_THEN_DETAIL_V35_NATIVE_PILOT_2" or (
         report["variants"]["C"]["strokes"],report["variants"]["C"]["synthetic_vertices_NOT_CHALK"])!=(2242,5269):
        raise ValueError("V36 original V35 native baseline identity drift")
    if not report["native_A_replay_V34R_pixel_exact"]:
        raise ValueError("V36 V35-RGB native control invalid")
    for name,digest in report["artifacts_sha256"].items():
        if sha(folder/name)!=digest:raise ValueError("V36 original V35 file SHA drift")
    plans=json.loads((folder/"plans.json").read_text(encoding="utf-8"))
    base=plans["C"]
    if base["paint_strokes"]!=1945 or base["detail_strokes"]!=297:
        raise ValueError("V36 original two-layer plan changed")
    return base

def main():
    p=argparse.ArgumentParser()
    for name in ("workspace","source","v35-archive","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V36 no-overwrite evidence")
    if sha(a.source)!=SOURCE_SHA:raise ValueError("V36 source SHA drift")
    original,_=prepare_source(a.source)
    baseline=frozen_v35(a.v35_archive)
    variants={};color_sources={}
    for v in ("A","B","C"):
        variants[v],color_sources[v]=recolor(baseline,original,v)
    out=a.output;out.mkdir(parents=True)
    (out/"detail-color-plans.json").write_text(json.dumps({
        "experiment":EXPERIMENT,"detail_RGB_by_variant":color_sources,
        "plans":variants},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    native={};crop={};metadata={}
    for v in ("A","B","C"):
        directory=out/v;directory.mkdir()
        rgba,scenes,manifest=native_batch(
            a.workspace,"V36-"+v,native_strokes(variants[v]),directory,
            renderer_method="renderV36SourceColoredContourProbe")
        native[v]=rgba
        image=logical_crop(rgba["composite"])
        image.save(out/("V36-"+v+"-roi.png"))
        crop[v]=image
        metadata[v]=scenes
    replay=png_pixel_exact_replay(
        a.v35_archive/"C"/"V35-C-composite.png",
        out/"A"/"V36-A-composite.png")
    for stem in ["composite","color-100"]+[f"color-{c}" for c in (4,5,6,7)]:
        if not (np.array_equal(native["A"][stem][:,:,3],native["B"][stem][:,:,3])
            and np.array_equal(native["A"][stem][:,:,3],native["C"][stem][:,:,3])):
            raise ValueError("V36 native A/B/C alpha footprint changed "+stem)
    sheet([original,crop["A"],crop["B"],crop["C"]],
          ["Original source","V35 selected dark A","V36 original sampled B","V36 half-tint C"],
          out/"comparison-full.png")
    sheet([original,crop["A"],crop["B"],crop["C"]],
          ["Original","V35 dark contours","Source colored","Half tint"],
          out/"comparison-faces.png",top=True)
    warm=warm_mask(original)
    metrics={k:{"source_RGB_MAE":mae(crop[k],original),
                "warm_RGB_MAE":mae(crop[k],original,warm),
                "detail_strokes":297,
                "synthetic_vertices_NOT_CHALK":5269,
                "native_composite_alpha24_pixels":int(np.count_nonzero(
                    native[k]["composite"][:,:,3]>=24))}
             for k in ("A","B","C")}
    checks={key:{ "full_improved":metrics[key]["source_RGB_MAE"]<metrics["A"]["source_RGB_MAE"],
                  "warm_improved":metrics[key]["warm_RGB_MAE"]<metrics["A"]["warm_RGB_MAE"]}
            for key in ("B","C")}
    hashes={str(p.relative_to(out)).replace("\\","/"):sha(p)
            for p in out.rglob("*") if p.is_file()}
    report={"experiment":EXPERIMENT,"status":"REAL_ARCHIVED_EGRET_E3_NOT_LIVE",
            "source_sha":SOURCE_SHA,"v35_reference":"CI43742747278 artifact14173635779",
            "v35_control_pixel_exact":replay["pixel_rgba_exact"],
            "same_native_alpha_all_variants":True,
            "warm_source_pixel_count":int(warm.sum()),
            "metrics":metrics,"candidate_diagnostic":checks,
            "native_scenes":metadata,"artifact_sha256":hashes,
            "quality_accepted":False,"game_exact_CHALK":None,
            "not_tested":["live E4","independent E5","game exact CHALK",
                "per-color native >=99% acceptance"],
            "versions":{"Python":platform.python_version(),"numpy":np.__version__}}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"metrics":metrics,"candidate":checks},indent=2))

if __name__=="__main__":main()
