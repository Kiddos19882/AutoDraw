#!/usr/bin/env python3
"""ENGINE001_TWO_ICON_ADAPTIVE_BRUSH_V3: frozen geometric mixed-brush research.

Candidate widths represent Egret BoardPane.setRadius arguments, NOT validated
diameters, nor an inferred CHALK rate. Three-logical-pixel exterior and
interior-boundary sensitivity does not replace >=99% frozen-target coverage.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
from io import BytesIO
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import threading

import cv2
import numpy as np
from PIL import Image
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from run_engine001_two_icon_mask_probe import (
    WIDTH, HEIGHT, ALPHA_THRESHOLD, composite_mask, compare
)
from run_engine001_predictive_contour_probe import (
    SCALE, contour_candidates, stroke_length
)
from run_engine001_painted_frontier_v2 import measure_halo, permitted_halo

EXPERIMENT = "ENGINE001_TWO_ICON_ADAPTIVE_BRUSH_V3"
WIDTHS = (30,15,8,4,2)
MIN_GAIN=48
MAX_HORIZONTAL=420
MAX_OUTLINES=8
HALO=3.0
TARGET_SHAPE=(HEIGHT*SCALE,WIDTH*SCALE)


def variable_footprint(stroke:dict) -> np.ndarray:
    points=stroke["points"]
    if stroke["width"] not in WIDTHS or len(points)<2:
        raise ValueError("Unsupported mixed-brush stroke")
    coords=np.array([[round(p["x"]*SCALE),round(p["y"]*SCALE)]
                     for p in points],dtype=np.int32)
    raster=np.zeros(TARGET_SHAPE,dtype=np.uint8)
    cv2.polylines(raster,[coords],False,255,
                  stroke["width"]*SCALE,cv2.LINE_8)
    return raster!=0


def _safe_spans(mask:np.ndarray, width:int, y:int) -> list[tuple[int,int]]:
    inward=cv2.distanceTransform(mask.astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    return _spans_in_distance(inward,width,y)


def _spans_in_distance(inward:np.ndarray, width:int, y:int) -> list[tuple[int,int]]:
    row=np.pad(inward[y]>=width/2.0,(1,1),constant_values=False).astype(np.int8)
    starts=np.flatnonzero(np.diff(row)==1)
    stops=np.flatnonzero(np.diff(row)==-1)
    return [(int(x),int(z)) for x,z in zip(starts,stops)
            if z-x>=max(12,width)]


def plan_adaptive(mask:np.ndarray) -> tuple[list[dict],dict,dict[str,np.ndarray]]:
    if mask.shape!=(HEIGHT,WIDTH) or mask.dtype!=np.dtype(bool) or not mask.any():
        raise ValueError("V3 requires a nonempty pinned 460x240 binary source mask")
    target=np.repeat(np.repeat(mask,SCALE,axis=0),SCALE,axis=1)
    allowed,_=permitted_halo(target)
    inward=cv2.distanceTransform(mask.astype(np.uint8),
                                 cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    current=np.zeros(TARGET_SHAPE,dtype=bool)
    strokes=[]
    decisions=[]
    # Long boundary contours FIRST; both external shapes and internal holes
    # are discoverable via the frozen target-mask contour extractor.
    outline_candidates=contour_candidates(mask)
    outline_candidates.sort(key=lambda x:(-x["length"],x["source_contour"]))
    for candidate in outline_candidates:
        if len(strokes)>=MAX_OUTLINES:
            break
        if len(candidate["points"])>128:
            decisions.append({"type":"outline","decision":"REJECT_TOO_MANY_VERTICES"})
            continue
        outline={"strokeId":f"icon-{len(strokes)}","width":2,
                 "points":candidate["points"]}
        raster=variable_footprint(outline)
        gain=int(np.count_nonzero(target&raster&~current))
        far=int(np.count_nonzero(raster&~allowed))
        accept=gain>=MIN_GAIN and far==0
        decisions.append({"type":"outline","length":round(candidate["length"],3),
                          "gain":gain,"far":far,"decision":"ACCEPT" if accept else "REJECT"})
        if accept:
            strokes.append(outline)
            current|=raster
    outline_count=len(strokes)
    # Brush widths descending; each continuous source-run becomes one long
    # horizontal stroke. Completely redundant rows are ignored.
    count_by_width={str(w):0 for w in WIDTHS}
    for width in WIDTHS:
        step=max(2,int(0.75*width))
        for y in range(0,HEIGHT,step):
            for x0,x1 in _spans_in_distance(inward,width,y):
                if len(strokes)-outline_count>=MAX_HORIZONTAL:
                    break
                points=[{"x":float(x0)+0.5,"y":float(y)+0.5},
                        {"x":float(x1-1)+0.5,"y":float(y)+0.5}]
                candidate={"strokeId":f"icon-{len(strokes)}","width":width,"points":points}
                raster=variable_footprint(candidate)
                pixels=int(np.count_nonzero(raster))
                gain=int(np.count_nonzero(raster&target&~current))
                far=int(np.count_nonzero(raster&~allowed))
                overlap=int(np.count_nonzero(raster&current))
                overlap_fraction=overlap/pixels if pixels else 1.0
                accept=gain>=MIN_GAIN and far==0 and overlap_fraction<=0.90
                decisions.append({
                    "type":"horizontal","width":width,"y":y,"run":[x0,x1],
                    "gain":gain,"far":far,
                    "overlap_fraction":round(overlap_fraction,5),
                    "decision":"ACCEPT" if accept else "REJECT"
                })
                if accept:
                    strokes.append(candidate)
                    current|=raster
                    count_by_width[str(width)]+=1
            if len(strokes)-outline_count>=MAX_HORIZONTAL:
                break
    verts=sum(len(s["points"]) for s in strokes)
    if not strokes or len(strokes)>3000 or verts>5900:
        raise ValueError("Native rendering quota exceeded")
    widths=[s["width"] for s in strokes]
    notes={
        "algorithm":"outer_and_inner_contours_first_then_adaptive_safe_horizontal_centrelines",
        "outline_strokes":outline_count,
        "horizontal_strokes":len(strokes)-outline_count,
        "total_strokes":len(strokes),
        "synthetic_vertices_not_chalk":verts,
        "widths_used":sorted(set(widths),reverse=True),
        "horizontal_count_by_width":count_by_width,
        "size_switches":sum(a!=b for a,b in zip(widths,widths[1:])),
        "total_path_length_logical":sum(stroke_length(s) for s in strokes),
        "candidate_decisions":decisions,
        "preview_comparison":compare(target,current),
        "preview_halo":measure_halo(target,current),
        "frozen_parameters":{
            "widths":list(WIDTHS),"preview_nominal_diameter_multiplier":SCALE,
            "inward_safe_distance_parameter_divisor":2,
            "horizontal_stride_ratio":0.75,"min_run_length":"max(12,width)",
            "min_new_native_pixels":MIN_GAIN,"max_horizontals":MAX_HORIZONTAL,
            "max_outline_strokes":MAX_OUTLINES,
            "max_overlap_fraction":0.90,"exterior_halo_logical":HALO
        }
    }
    return strokes,notes,{"target":target,"proxy_predicted_coverage":current}


def native_render(strokes:list[dict],workspace:Path) -> dict:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):
            super().__init__(*a,directory=str(workspace),**kw)
        def log_message(self,*a): pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    th=threading.Thread(target=server.serve_forever,daemon=True)
    th.start()
    driver=None
    try:
        opts=Options()
        opts.add_argument("-headless")
        opts.set_preference("webgl.disabled",False)
        opts.set_preference("webgl.force-enabled",True)
        opts.set_preference("webgl.disable-fail-if-major-performance-caveat",True)
        driver=webdriver.Firefox(options=opts)
        driver.set_page_load_timeout(180)
        driver.get(f"http://127.0.0.1:{server.server_port}/"
                   "AutoDraw_Stage20/tests/game_renderer_reference.html?twoicons=home-envelope")
        WebDriverWait(driver,90).until(lambda d:
            d.execute_script("return document.body.dataset.twoIconStatus")=="ready")
        return driver.execute_script(
            "return window.AutoDrawGameRendererReference.renderTwoIconAdaptiveBrushProbe(arguments[0]);",
            strokes)
    finally:
        if driver is not None: driver.quit()
        server.shutdown()
        server.server_close()


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",type=Path,default=Path("."))
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args()
    out=args.output_dir.resolve()
    out.mkdir(parents=True,exist_ok=True)
    logical,sources=composite_mask(args.workspace.resolve())
    strokes,meta,previews=plan_adaptive(logical)
    for name,mask in previews.items():
        Image.fromarray(mask.astype(np.uint8)*255,"L").save(out/(name+".png"))
    (out/"adaptive-brush-strokes.json").write_text(json.dumps({
        "experiment":EXPERIMENT,"strokes":strokes
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    native=native_render(strokes,args.workspace.resolve())
    url=native.pop("webglPngDataUrl")
    if not url.startswith("data:image/png;base64,"):
        raise ValueError("Actual native WebGL did not return PNG")
    raw=base64.b64decode(url.partition(",")[2],validate=True)
    (out/"adaptive-brush-native-egret.png").write_bytes(raw)
    with Image.open(BytesIO(raw)) as im:
        rgba=np.asarray(im.convert("RGBA"))
    if rgba.shape!=(*TARGET_SHAPE,4): raise ValueError("Unexpected native raster size")
    painted=rgba[:,:,3]>=ALPHA_THRESHOLD
    target=previews["target"]
    metrics=compare(target,painted)
    ext=measure_halo(target,painted)
    inside_dist=cv2.distanceTransform(target.astype(np.uint8),
                                      cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    missing=target&~painted
    inside_far=int(np.count_nonzero(missing & (inside_dist>HALO*SCALE)))
    viz=np.full((*TARGET_SHAPE,3),255,dtype=np.uint8)
    viz[target&painted]=(44,145,76)
    viz[missing]=(230,80,70)
    viz[painted&~target]=(65,95,205)
    Image.fromarray(viz,"RGB").save(out/"adaptive-brush-overlay.png")
    passed=metrics["coverage"]>=.99 and ext["all_leakage_in_3logical_halo"]
    report={
        "schema":EXPERIMENT,"status":"OFFLINE_GEOMETRIC_PASS_NOT_GAME" if passed
                                             else "OFFLINE_QUALITY_FAIL",
        "source":sources,"renderer":native,"normal_mode":True,"scale":SCALE,
        "alpha_threshold":ALPHA_THRESHOLD,
        "native_png_sha256":hashlib.sha256(raw).hexdigest(),
        "metrics":metrics,"external_tolerance":ext,
        "internal_boundary_diagnostic":{
            "missed_pixels_inside_3_logical_px":int(np.count_nonzero(
                missing&(inside_dist<=HALO*SCALE))),
            "missed_pixels_deeper_than_3_logical_px":inside_far,
            "note":"Boundary-localized missing pixels are NOT silently accepted; coverage >=99% remains"
        },
        "planning":meta,"quality":{
            "coverage_min":.99,"max_external_distance_logical":3.0,
            "result":"PASS_OFFLINE_ONLY" if passed else "FAIL"
        },
        "controls":{
            "horizontal_only":{"coverage":0.9210937202482958,"strokes":380},
            "target_contour_v1":{"coverage":0.9272884217474644,"strokes":381},
            "painted_frontier_v2":{"coverage":0.9647422471025807,"strokes":403,
                                   "synthetic_vertices":1943}
        },
        "limitations":[
            "No real game, run-bound screen RGB, E4, E5, or exact CHALK",
            "setRadius is a native API parameter, not automatically a physical brush diameter",
            "cv2 LINE_8 width model is an explicit approximate preview",
            "Exterior and interior 3 logical pixel tolerance is a diagnostic boundary band",
            "No production changes or retrospective threshold fitting"
        ]
    }
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",
                                    encoding="utf-8")
    print(EXPERIMENT,report["status"],"coverage",metrics["coverage"],
          "IoU",metrics["iou"],"outside",ext["leaked_native_pixels"],
          "farOutside",ext["farther_than_3logical_native_pixels"],
          "missingDeepInside",inside_far,"strokes",len(strokes),
          "vertices",meta["synthetic_vertices_not_chalk"],flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
