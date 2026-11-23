#!/usr/bin/env python3
"""ENGINE-001 S5-LANE-P2 real Egret normal multi-point joint samples (research)."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
from run_engine001_complex_holdout_v5 import read_webgl_result

EXPERIMENT = "ENGINE001_S5_LANE_P2_NORMAL_NATIVE_POLYLINE_JOINTS_V1"
PREREG = "ENGINE001_S5_LANE_P2_NATIVE_NORMAL_MULTI_VERTEX_JOINTS_PREREG_2026-11-23.md"
WIDTHS = tuple(range(1,11))
ANGLES = (45,90,135)
PHASES = ((.25,.375),(.5,.625))
SHAPES = ("turn3","serpentine5")
SHAPE = (720,1380,4)
CMD = "return window.AutoDrawGameRendererReference.renderP4A2BrushWidths1to10Probe(arguments[0]);"


def case_key(width, angle, phase_index, shape):
    if (width not in WIDTHS or angle not in ANGLES or
            type(phase_index) is not int or phase_index not in (0,1) or shape not in SHAPES):
        raise ValueError("BLOCKED_P2_UNREGISTERED_CASE")
    return f"W{width:02d}_A{angle:03d}_P{phase_index}_{shape}"


def make_points(width, angle, phase_index, shape):
    case_key(width,angle,phase_index,shape)
    directions = (0,angle) if shape=="turn3" else (0,angle,0,-angle)
    length=24 if shape=="turn3" else 20
    pts=[(0.,0.)]
    for direction in directions:
        rad=math.radians(direction)
        x,y=pts[-1]
        pts.append((x+length*math.cos(rad),y+length*math.sin(rad)))
    xs=[p[0] for p in pts]
    ys=[p[1] for p in pts]
    cx=(min(xs)+max(xs))/2
    cy=(min(ys)+max(ys))/2
    phase=PHASES[phase_index]
    result=[{"x":float(x-cx+230+phase[0]),
             "y":float(y-cy+120+phase[1])} for x,y in pts]
    if not all(15<=v["x"]<=445 and 15<=v["y"]<=225 for v in result):
        raise ValueError("BLOCKED_P2_PATH_OUTSIDE_BOARD")
    return result


def make_strokes(width, angle, phase_index, shape):
    points=make_points(width,angle,phase_index,shape)
    def native(points, idx):
        return {"strokeId":f"icon-{idx}","width":int(width),
                "colorIndex":1,"colorRgb":int(p4d3.COLOR),
                "points":[dict(p) for p in points]}
    continuous=[native(points,0)]
    separated=[native(points[i:i+2],i) for i in range(len(points)-1)]
    return continuous,separated,points


def metrics(poly, segments, points, width):
    if (poly.shape!=SHAPE or segments.shape!=SHAPE or
            poly.dtype!=np.uint8 or segments.dtype!=np.uint8):
        raise ValueError("BLOCKED_P2_NATIVE_RGBA")
    x_vals=[p["x"] for p in points]
    y_vals=[p["y"] for p in points]
    left=max(0,int(math.floor((min(x_vals)-width-5)*3)))
    right=min(1380,int(math.ceil((max(x_vals)+width+5)*3)))
    top=max(0,int(math.floor((min(y_vals)-width-5)*3)))
    bottom=min(720,int(math.ceil((max(y_vals)+width+5)*3)))
    if right<=left or bottom<=top:
        raise ValueError("BLOCKED_P2_BAD_ROI")
    p=poly[top:bottom,left:right,:]
    s=segments[top:bottom,left:right,:]
    yy,xx=np.indices(p.shape[:2])
    gx=(xx+left+.5)/3
    gy=(yy+top+.5)/3
    dist=np.full(p.shape[:2],np.inf,dtype=np.float64)
    for a,b in zip(points,points[1:]):
        dx=b["x"]-a["x"]
        dy=b["y"]-a["y"]
        sq=dx*dx+dy*dy
        if sq<1e-12:
            raise ValueError("BLOCKED_P2_ZERO_SEGMENT")
        t=np.clip(((gx-a["x"])*dx+(gy-a["y"])*dy)/sq,0,1)
        cur=np.hypot(gx-(a["x"]+t*dx),gy-(a["y"]+t*dy))
        np.minimum(dist,cur,out=dist)
    corner=np.zeros(p.shape[:2],bool)
    for v in points[1:-1]:
        corner |= np.hypot(gx-v["x"],gy-v["y"])<=width/2+4
    delta=np.any(p!=s,axis=2)
    result={
        "roi_backing_pixels":int(p.shape[0]*p.shape[1]),
        "rgba_different_backing_pixels":int(delta.sum()),
        "corner_rgba_different_backing_pixels":int((delta&corner).sum()),
        "corner_sample_backing_pixels":int(corner.sum()),
        "native_max_alpha_p":int(p[:,:,3].max()),
        "native_max_alpha_s":int(s[:,:,3].max())}
    for t in (24,128):
        a=p[:,:,3]>=t
        b=s[:,:,3]>=t
        outer=dist>width/2+3
        result[f"alpha{t}"]={
            "poly_ink_pixels":int(a.sum()),
            "separate_ink_pixels":int(b.sum()),
            "xor_ink_pixels":int(np.count_nonzero(a^b)),
            "corner_xor_ink_pixels":int(np.count_nonzero((a^b)&corner)),
            "poly_outside_overshoot3px":int(np.count_nonzero(a&outer)),
            "separate_outside_overshoot3px":int(np.count_nonzero(b&outer))}
    return result


def capture(driver, folder, stem, strokes):
    response=driver.execute_script(CMD,strokes)
    rgba,meta=read_webgl_result(response,folder,stem)
    if (rgba.shape!=SHAPE or meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer"
            or meta.get("mode")!="normal" or
            meta.get("schema")!="ENGINE001_B1R_P4A2_NATIVE_1_TO_10"
            or meta.get("strokeCount")!=len(strokes)):
        raise ValueError("BLOCKED_P2_NOT_REAL_EGRET_NORMAL")
    return rgba,meta


def run(workspace, engine, renderer, output):
    if output.exists():
        raise ValueError("BLOCKED_P2_OUTPUT_EXISTS")
    if p4b1.git_blob(engine.read_bytes())!=p4d3.ENGINE_GIT_BLOB:
        raise ValueError("BLOCKED_P2_ENGINE_PIN_DRIFT")
    if p4b1.git_blob(renderer.read_bytes())!=p4d3.RENDERER_GIT_BLOB:
        raise ValueError("BLOCKED_P2_RENDERER_PIN_DRIFT")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P2_MISSING_E0")
    output.mkdir(parents=True)
    rows=[]
    with p4b7.native_egret_session(workspace) as driver:
        driver.set_script_timeout(180)
        blank=driver.execute_script(CMD,[])
        rgba,meta=read_webgl_result(blank,output,"00_NATIVE_BLANK")
        if (rgba.shape!=SHAPE or meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL"
                or np.any(rgba[:,:,3])):
            raise ValueError("BLOCKED_P2_BLANK_NATIVE")
        with (output/"CASES_APPEND_ONLY.jsonl").open("a",encoding="utf8") as ledger:
            for width in WIDTHS:
                for angle in ANGLES:
                    for phase_index in range(2):
                        for shape in SHAPES:
                            key=case_key(width,angle,phase_index,shape)
                            folder=output/"cases"/f"W{width:02d}"
                            folder.mkdir(parents=True,exist_ok=True)
                            poly,sep,points=make_strokes(width,angle,phase_index,shape)
                            (folder/(key+"_PLAN.json")).write_text(
                                json.dumps({"experiment":EXPERIMENT,"id":key,
                                            "width":width,"angle":angle,
                                            "phase":PHASES[phase_index],"shape":shape,
                                            "points":points,"polyline":poly,
                                            "separated":sep},sort_keys=True)+"\n",encoding="utf8")
                            P,pm=capture(driver,folder,key+"_P",poly)
                            S,sm=capture(driver,folder,key+"_S",sep)
                            if not np.any(P[:,:,3]>=24) or not np.any(S[:,:,3]>=24):
                                raise ValueError("BLOCKED_P2_EMPTY_NATIVE_STROKE")
                            row={"id":key,"width":width,"turn_angle":angle,
                                 "phase":list(PHASES[phase_index]),"shape":shape,
                                 "native_sha256":{"P":pm["source_sha256"],
                                                  "S":sm["source_sha256"]},
                                 "metrics":metrics(P,S,points,width)}
                            ledger.write(json.dumps(row,sort_keys=True)+"\n")
                            ledger.flush()
                            rows.append(row)
                    print("S5_P2_PROGRESS",width,angle,len(rows),flush=True)
    if len(rows)!=120:
        raise ValueError("BLOCKED_P2_CASE_COUNT")
    members={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.rglob("*")) if p.is_file() and p.name!="report.json"}
    if len([n for n in members if n.endswith(".png")])!=241:
        raise ValueError("BLOCKED_P2_MISSING_RAW_PNG")
    report={
        "experiment":EXPERIMENT,"e0":PREREG,
        "evidence":"E3_OFFLINE_PINNED_EGRET",
        "technical_status":"PASS_COMPLETE_NATIVE_EVIDENCE",
        "game_engine_blob":p4d3.ENGINE_GIT_BLOB,
        "renderer_blob":p4d3.RENDERER_GIT_BLOB,
        "github_sha":os.environ.get("GITHUB_SHA","LOCAL"),
        "github_run_id":os.environ.get("GITHUB_RUN_ID","LOCAL"),
        "normal_smooth_false":True,
        "case_count":len(rows),"native_png_count":241,
        "cases":rows,"member_sha256":members,
        "E4_game":"NOT_RUN","exact_CHALK":"NOT_RUN",
        "production_promotion":False}
    (output/"report.json").write_text(
        json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("S5_P2_NATIVE_COMPLETED",len(rows),
          sum(r["metrics"]["alpha24"]["poly_outside_overshoot3px"] for r in rows),
          sum(r["metrics"]["alpha128"]["poly_outside_overshoot3px"] for r in rows),
          flush=True)
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--engine-js",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    run(a.workspace.resolve(),a.engine_js.resolve(),a.renderer.resolve(),
        a.output.resolve())


if __name__=="__main__":
    main()
