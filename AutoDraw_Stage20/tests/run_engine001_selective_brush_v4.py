#!/usr/bin/env python3
"""ENGINE001_TWO_ICON_SELECTIVE_BRUSH_V4 frozen selective mixed-width experiment.

V3 original JSON geometry is cryptographically checked before changing ANY
width. V4 only changes width4->6 and width8->10 in EXISTING long strokes;
all short/other strokes and every point/point count remain unchanged.
Offline WebGL rendering is not a game CHALK measurement or formal E4/E5.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_two_icon_mask_probe import (
    ALPHA_THRESHOLD, HEIGHT, WIDTH, compare, composite_mask
)
from run_engine001_adaptive_brush_v3 import native_render, plan_adaptive
from run_engine001_painted_frontier_v2 import permitted_halo, measure_halo

ID = "ENGINE001_TWO_ICON_SELECTIVE_BRUSH_V4"
V3_STROKES_SHA256 = "68b478d289c3eaa99493bb120bd6dcee7efc40944d4720844e74663837ec9594"
EXPECTED_V3_METRICS = {
    "target_pixels":157554, "covered_target_pixels":153880,
    "uncovered_target_pixels":3674, "outside_target_pixels":6974
}
SCALE=3
FIXED_SIZE_UPGRADE={2:2, 4:6, 8:10}
FROZEN_STROKE_COUNT=323
FROZEN_POINT_COUNT=674


def canonical_sha256(strokes: list[dict]) -> str:
    return hashlib.sha256(json.dumps(
        strokes,sort_keys=True,separators=(",",":")
    ).encode("utf-8")).hexdigest()


def select_widths(v3: list[dict]) -> list[dict]:
    if canonical_sha256(v3) != V3_STROKES_SHA256:
        raise ValueError("Refusing V4: regenerated V3 stroke plan is not frozen source plan")
    if len(v3)!=FROZEN_STROKE_COUNT or sum(len(s["points"]) for s in v3)!=FROZEN_POINT_COUNT:
        raise ValueError("Refusing V4: V3 stroke/point count drift")
    v4=[]
    for stroke in v3:
        w=stroke["width"]
        if w not in FIXED_SIZE_UPGRADE:
            raise ValueError(f"Unexpected source width {w}")
        item={"strokeId":stroke["strokeId"],
              "width":FIXED_SIZE_UPGRADE[w],
              "points":[dict(point) for point in stroke["points"]]}
        v4.append(item)
    for old,new in zip(v3,v4):
        if old["points"]!=new["points"] or old["strokeId"]!=new["strokeId"]:
            raise AssertionError("V4 must keep every point and stroke unchanged")
    return v4


def predictor(strokes:list[dict]) -> np.ndarray:
    canvas=np.zeros((HEIGHT*SCALE,WIDTH*SCALE),dtype=np.uint8)
    for stroke in strokes:
        xy=np.array([[round(p["x"]*SCALE), round(p["y"]*SCALE)]
                     for p in stroke["points"]],dtype=np.int32)
        cv2.polylines(canvas,[xy],False,255,
                      stroke["width"]*SCALE,cv2.LINE_8)
    return canvas>=1


def parse_native(strokes:list[dict], workspace:Path, output:Path, name:str) -> tuple[np.ndarray,dict,str]:
    result=native_render(strokes,workspace)
    png_url=result.pop("webglPngDataUrl")
    if not png_url.startswith("data:image/png;base64,"):
        raise ValueError(f"{name}: missing real WebGL PNG")
    raw=base64.b64decode(png_url.partition(",")[2],validate=True)
    (output/f"{name}-actual-egret.png").write_bytes(raw)
    with Image.open(BytesIO(raw)) as im:
        rgba=np.asarray(im.convert("RGBA"))
    if rgba.shape!=(HEIGHT*SCALE,WIDTH*SCALE,4):
        raise ValueError(f"{name}: unexpected output size")
    return rgba[:,:,3]>=ALPHA_THRESHOLD,result,hashlib.sha256(raw).hexdigest()


def interior_band(target:np.ndarray,painted:np.ndarray) -> dict:
    inward=cv2.distanceTransform(target.astype(np.uint8),
                                 cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    missing=target&~painted
    far=missing&(inward>9.0+1e-6)
    return {
        "missing_total_native_px":int(missing.sum()),
        "missing_within_3_logical_px":int((missing&~far).sum()),
        "missing_farther_than_3_logical_px":int(far.sum()),
        "note":"No interior missing is excused from >=99% coverage"
    }


def make_overlay(target:np.ndarray,painted:np.ndarray,path:Path) -> None:
    image=np.full((*target.shape,3),255,dtype=np.uint8)
    image[target&painted]=(44,145,76)
    image[target&~painted]=(230,80,70)
    image[~target&painted]=(65,95,205)
    Image.fromarray(image,"RGB").save(path)


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",type=Path,default=Path("."))
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args()
    out=args.output_dir.resolve()
    out.mkdir(parents=True,exist_ok=True)
    workspace=args.workspace.resolve()
    logical,sources=composite_mask(workspace)
    target=np.repeat(np.repeat(logical,SCALE,axis=0),SCALE,axis=1)
    original,v3_planning,_=plan_adaptive(logical)
    candidate=select_widths(original)
    if candidate == original:
        raise AssertionError("Selective experiment must change one existing brush width")
    (out/"v3-source-strokes.json").write_text(json.dumps(
        {"id":"ENGINE001_TWO_ICON_ADAPTIVE_BRUSH_V3","strokes":original},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"v4-strokes.json").write_text(json.dumps(
        {"id":ID,"strokes":candidate},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    Image.fromarray(target.astype(np.uint8)*255,"L").save(out/"target.png")
    proxy={}
    for name,plan in [("v3",original),("v4",candidate)]:
        mask=predictor(plan)
        Image.fromarray(mask.astype(np.uint8)*255,"L").save(out/f"{name}-forecast.png")
        proxy[name]={
            "pixel_metrics":compare(target,mask),
            "exterior":measure_halo(target,mask),
            "interior":interior_band(target,mask)
        }
    v3_actual,v3_renderer,v3_sha=parse_native(original,workspace,out,"v3-control")
    v3_metrics=compare(target,v3_actual)
    for field,expected in EXPECTED_V3_METRICS.items():
        if v3_metrics[field]!=expected:
            raise ValueError(f"Control native Egret drift: {field} {v3_metrics[field]} vs {expected}")
    v4_actual,v4_renderer,v4_sha=parse_native(candidate,workspace,out,"v4-experiment")
    v4_metrics=compare(target,v4_actual)
    make_overlay(target,v3_actual,out/"v3-control-overlay.png")
    make_overlay(target,v4_actual,out/"v4-overlay.png")
    exterior=measure_halo(target,v4_actual)
    quality=v4_metrics["coverage"]>=0.99 and exterior["all_leakage_in_3logical_halo"]
    old_widths=[s["width"] for s in original]
    new_widths=[s["width"] for s in candidate]
    resource={
        "v3_strokes":len(original),
        "v4_strokes":len(candidate),
        "v3_vertices_not_chalk":sum(len(s["points"]) for s in original),
        "v4_vertices_not_chalk":sum(len(s["points"]) for s in candidate),
        "v3_brush_size_switches":sum(a!=b for a,b in zip(old_widths,old_widths[1:])),
        "v4_brush_size_switches":sum(a!=b for a,b in zip(new_widths,new_widths[1:])),
        "v3_width_counts":{str(w):old_widths.count(w) for w in sorted(set(old_widths))},
        "v4_width_counts":{str(w):new_widths.count(w) for w in sorted(set(new_widths))},
        "preserved_all_points_and_order":True,
        "v3_plan_sha256":canonical_sha256(original),
        "v4_plan_sha256":canonical_sha256(candidate),
    }
    if resource["v4_strokes"]!=FROZEN_STROKE_COUNT or resource["v4_vertices_not_chalk"]!=FROZEN_POINT_COUNT:
        raise ValueError("V4 must not introduce more synthetic strokes or vertices")
    if resource["v4_brush_size_switches"]>3:
        raise ValueError("V4 must not increase brush size switches")
    report={
        "schema":ID,
        "status":"OFFLINE_GEOMETRIC_PASS_NOT_GAME" if quality else "OFFLINE_QUALITY_FAIL",
        "preregistered_protocol":"TASKS.md / ENGINE001_TWO_ICON_SELECTIVE_BRUSH_V4",
        "source":sources,
        "source_V3_plan_sha256":V3_STROKES_SHA256,
        "transformation":"ONLY brush width4->6 and width8->10; width2 preserved",
        "mode":"normal","native_scale":SCALE,"native_alpha_threshold":ALPHA_THRESHOLD,
        "frozen_quality":{"coverage_min":0.99,"max_exterior_logical_px":3.0,
                          "allow_internal_boundary_diagnostic_logical_px":3.0},
        "proxy_forecast_before_native":proxy,
        "native_control_V3":{
            "metrics":v3_metrics,"exterior":measure_halo(target,v3_actual),
            "interior":interior_band(target,v3_actual),
            "native_png_sha256":v3_sha,"renderer":v3_renderer
        },
        "native_V4":{
            "metrics":v4_metrics,"exterior":exterior,
            "interior":interior_band(target,v4_actual),
            "native_png_sha256":v4_sha,"renderer":v4_renderer
        },
        "resource":resource,
        "native_v4_quality":"PASS_OFFLINE_ONLY" if quality else "FAIL",
        "limitations":[
            "Offline WebGL mask alpha24; does not implement run-bound DEC-030 RGB8 game quality",
            "Approximate OpenCV preview computed on V3 source geometry is not native fidelity",
            "No accepted in-game CHALK; synthetic vertices/brush width do not predict exact quota",
            "No isolated short corrective lines or geometry tuning after V4 native result",
            "Multi-color clipping, E4, E5 and independent holdout untested",
            "3-logical-pixel interior band is separate from strict >=99% source mask coverage"
        ]
    }
    (out/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(ID,report["status"],
          "V3",v3_metrics["coverage"],
          "V4",v4_metrics["coverage"],
          "V4 iou",v4_metrics["iou"],
          "V4 far",exterior["farther_than_3logical_native_pixels"],
          "strokes",resource["v4_strokes"],
          "vertices",resource["v4_vertices_not_chalk"],flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
