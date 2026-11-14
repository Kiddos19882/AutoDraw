#!/usr/bin/env python3
"""ENGINE001_COMPLEX_MULTICOLOR_HOLDOUT_V5 — preregistered unseen complex artwork.

Actual target = pinned repository PNG, aspect-fit onto logical 460x240,
quantized into 8 fixed MEDIANCUT indices; each non-background color mask
has its own V3, V4 and V5 plan and actual native WebGL alpha mask.
This is an imperfect palette proxy, never an exact original RGB quality gate.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from collections import Counter
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import threading

import cv2
import numpy as np
from PIL import Image, ImageDraw
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from run_engine001_adaptive_brush_v3 import plan_adaptive
from run_engine001_painted_frontier_v2 import permitted_halo, measure_halo
from run_engine001_two_icon_mask_probe import compare

EXP_ID = "ENGINE001_COMPLEX_MULTICOLOR_HOLDOUT_V5"
FROZEN_BLOB = "d3cd95b846f036a3f8acecf75d2a237e46dcf13a"
FROZEN_SIZE = 97308
SOURCE_REL = Path("AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png")
LOGICAL_SIZE = (460,240)
NATIVE_SIZE = (1380,720)
SCALE = 3
NUM_PALETTE = 8
ALPHA_MIN = 24
MAX_STROKES = 3000
MAX_VERTICES = 5900
UPGRADE = {2:2,4:6,8:10,15:15,30:30}
MAX_CLASS_CROSS_FRACTION = 0.05
HALO_NATIVE = 9.0


def fingerprint(blob: bytes) -> tuple[str,str]:
    return (hashlib.sha1(b"blob "+str(len(blob)).encode()+b"\0"+blob).hexdigest(),
            hashlib.sha256(blob).hexdigest())


def source_palette(workspace: Path) -> tuple[np.ndarray,dict,Image.Image]:
    path = workspace / SOURCE_REL
    raw=path.read_bytes()
    git_sha,sha256=fingerprint(raw)
    if git_sha!=FROZEN_BLOB or len(raw)!=FROZEN_SIZE:
        raise ValueError("Held-out PNG does not match original pinned repository Git blob")
    with Image.open(BytesIO(raw)) as im:
        original=im.convert("RGB")
        src_size=original.size
    ratio=min(LOGICAL_SIZE[0]/src_size[0],LOGICAL_SIZE[1]/src_size[1])
    resized=(max(1,round(src_size[0]*ratio)),max(1,round(src_size[1]*ratio)))
    xy=((LOGICAL_SIZE[0]-resized[0])//2,(LOGICAL_SIZE[1]-resized[1])//2)
    logical=Image.new("RGB",LOGICAL_SIZE,(255,255,255))
    logical.paste(original.resize(resized,Image.Resampling.LANCZOS),xy)
    paletted=logical.quantize(colors=NUM_PALETTE,
                              method=Image.Quantize.MEDIANCUT,
                              dither=Image.Dither.NONE)
    labels=np.asarray(paletted,dtype=np.uint8).copy()
    palette=paletted.getpalette()
    colors={int(k):tuple(int(palette[3*int(k)+j]) for j in range(3))
            for k in np.unique(labels)}
    corners=[int(labels[y,x]) for y,x in [
        (0,0),(0,LOGICAL_SIZE[0]-1),
        (LOGICAL_SIZE[1]-1,0),(LOGICAL_SIZE[1]-1,LOGICAL_SIZE[0]-1)
    ]]
    background=Counter(corners).most_common(1)[0][0]
    rgb=np.asarray(logical,dtype=np.int16)
    reconstructed=np.zeros_like(rgb)
    for k,color in colors.items():
        reconstructed[labels==k]=color
    mse=float(np.mean((rgb-reconstructed)**2))
    meta={
        "source_path":str(SOURCE_REL),
        "git_blob_sha":git_sha,
        "png_sha256":sha256,
        "png_bytes":len(raw),
        "original_size":list(src_size),"logical_size":list(LOGICAL_SIZE),
        "resized_size":list(resized),"paste_xy":list(xy),
        "resize":"aspect_contain_LANCZOS",
        "palette_method":"PIL_MEDIANCUT_colors8_no_dither",
        "background_index":background,
        "palette_rgb":{str(k):list(v) for k,v in colors.items()},
        "counts":{str(k):int(np.count_nonzero(labels==k)) for k in colors},
        "rgb_quantization_rmse":mse**0.5
    }
    return labels,meta,logical


def brush_mask(points:list[dict], size:int) -> np.ndarray:
    canvas=np.zeros((NATIVE_SIZE[1],NATIVE_SIZE[0]),dtype=np.uint8)
    xy=np.asarray([[round(p["x"]*SCALE),round(p["y"]*SCALE)]
                   for p in points],dtype=np.int32)
    cv2.polylines(canvas,[xy],False,255,size*SCALE,cv2.LINE_8)
    return canvas>0


def v5_selective(strokes:list[dict], own:np.ndarray, labels3:np.ndarray,
                 label:int) -> tuple[list[dict],dict]:
    exterior_distance=cv2.distanceTransform(
        (~own).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    out=[]
    decisions=[]
    for stroke in strokes:
        width=int(stroke["width"])
        proposed=UPGRADE[width]
        decision="UNCHANGED"
        if proposed!=width:
            old=brush_mask(stroke["points"],width)
            new=brush_mask(stroke["points"],proposed)
            addition=new&~old
            new_count=int(np.count_nonzero(addition))
            conflict=int(np.count_nonzero(addition&(labels3!=label)))
            far=int(np.count_nonzero(addition&(exterior_distance>HALO_NATIVE)))
            ratio=conflict/new_count if new_count else 0
            if far==0 and ratio<=MAX_CLASS_CROSS_FRACTION:
                width=proposed
                decision="UPGRADE"
            else:
                decision="RETAIN_SAFE_WIDTH"
            decisions.append({
                "strokeId":stroke["strokeId"],"from":stroke["width"],
                "to":width,"added_proxy_pixels":new_count,
                "conflicting_target_pixels":conflict,
                "conflict_fraction":ratio,
                "farther_than_3_logical_pixels":far,
                "decision":decision
            })
        out.append({**stroke,"width":width,
                    "points":[dict(p) for p in stroke["points"]]})
    return out,{"decisions":decisions,
                "upgraded":sum(d["decision"]=="UPGRADE" for d in decisions),
                "rejected":sum(d["decision"]=="RETAIN_SAFE_WIDTH" for d in decisions)}


def build_variants(labels:np.ndarray,palette:dict) -> tuple[dict,dict]:
    colors={int(k):tuple(c) for k,c in palette["palette_rgb"].items()}
    background=palette["background_index"]
    labels3=np.repeat(np.repeat(labels,SCALE,axis=0),SCALE,axis=1)
    variants={"V3":[],"V4":[],"V5":[]}
    decisions={}
    base_counts={}
    for label in sorted(colors):
        if label==background:
            continue
        own=labels==label
        rgb=colors[label]
        color_int=(rgb[0]<<16)|(rgb[1]<<8)|rgb[2]
        try:
            originals,planner,_=plan_adaptive(own)
        except ValueError as exc:
            if (str(exc) == "Native rendering quota exceeded"
                    and own.any()):
                # V3 raises the same exception for no candidate strokes.
                # Its planner caps <=428 strokes and <=1864 vertices, so
                # an individual color cannot actually exceed native limits.
                # Preserve the entire unpainted class as a holdout failure.
                originals=[]
                planner={"status":"NO_LONG_STROKES_FIT",
                         "target_logical_pixels":int(own.sum()),
                         "exception":str(exc)}
            else:
                raise
        # Every non-background class remains in the report even if unpaintable
        # under strict long-stroke geometry.
        for old in originals:
            if old["width"] not in UPGRADE:
                raise ValueError(f"Source planner size unexpected: {old['width']}")
        old_v5,decision=v5_selective(originals,labels3==label,labels3,label)
        decisions[str(label)]={"selector":decision,"source_plan":planner}
        base_counts[str(label)]={"target_native_pixels":int((labels3==label).sum()),
                                 "source_strokes":len(originals)}
        mapping={
            "V3":originals,
            "V4":[{**s,"width":UPGRADE[s["width"]]} for s in originals],
            "V5":old_v5
        }
        for name,source in mapping.items():
            for s in source:
                variants[name].append({
                    "strokeId":f"icon-{len(variants[name])}",
                    "width":int(s["width"]),
                    "colorRgb":color_int,
                    "colorIndex":int(label),
                    "points":[dict(p) for p in s["points"]]
                })
    for name,strokes in variants.items():
        if not strokes:
            raise ValueError("No paintable classes; this holdout cannot be measured")
        accepted=sum(len(s["points"]) for s in strokes)
        if len(strokes)>MAX_STROKES or accepted>MAX_VERTICES:
            raise ValueError(f"{name}: fail-closed source complexity {len(strokes)} strokes / {accepted} vertices")
        if any(len(s["points"])>128 or len(s["points"])<2 for s in strokes):
            raise ValueError("Native per-stroke 2..128 point limit exceeded")
    if len(variants["V3"])!=len(variants["V4"]) or len(variants["V3"])!=len(variants["V5"]):
        raise AssertionError("Variants must preserve source stroke count")
    for a,b,c in zip(variants["V3"],variants["V4"],variants["V5"]):
        if a["points"]!=b["points"] or a["points"]!=c["points"] or a["colorRgb"]!=b["colorRgb"] or a["colorRgb"]!=c["colorRgb"]:
            raise AssertionError("Color-aware variants must not modify original points/colors")
    return variants,{"per_color":base_counts,"candidate_decisions":decisions}


def read_webgl_result(response:dict,out:Path,stem:str) -> tuple[np.ndarray,dict]:
    url=response.pop("webglPngDataUrl")
    if not url.startswith("data:image/png;base64,"):
        raise ValueError("Native Egret did not return PNG")
    raw=base64.b64decode(url.partition(",")[2],validate=True)
    (out/f"{stem}.png").write_bytes(raw)
    with Image.open(BytesIO(raw)) as im:
        rgba=np.asarray(im.convert("RGBA")).copy()
    if rgba.shape!=(NATIVE_SIZE[1],NATIVE_SIZE[0],4):
        raise ValueError("Native output not 1380x720")
    meta={"source_sha256":hashlib.sha256(raw).hexdigest(),**response}
    return rgba,meta


def native_batch(workspace:Path,variant:str,strokes:list[dict],
                 output:Path) -> tuple[dict,dict,dict]:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):
            super().__init__(*a,directory=str(workspace),**kw)
        def log_message(self,*a):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    driver=None
    arrays={}
    info={}
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
        WebDriverWait(driver,90).until(
            lambda d:d.execute_script("return document.body.dataset.twoIconStatus")=="ready")
        groups={int(k):[s for s in strokes if s["colorIndex"]==k]
                for k in sorted({s["colorIndex"] for s in strokes})}
        # Render individual colors before composite for attribution.
        items=[(f"color-{k}",v) for k,v in groups.items()]+[("composite",strokes)]
        for stem,plan in items:
            result=driver.execute_script(
                "return window.AutoDrawGameRendererReference.renderComplexHoldoutColorProbe(arguments[0]);",
                plan)
            data,meta=read_webgl_result(result,output,f"{variant}-{stem}")
            arrays[stem]=data
            info[stem]=meta
    finally:
        if driver is not None:driver.quit()
        server.shutdown()
        server.server_close()
    return arrays,info,{"colors_rendered":sorted(groups),"variant":variant}


def classify_composite(pixels:np.ndarray,colors:dict,background:int) -> np.ndarray:
    palette_keys=np.asarray(sorted(colors),dtype=np.uint8)
    lut=np.asarray([colors[int(k)] for k in palette_keys],dtype=np.int16)
    alpha=pixels[:,:,3].astype(np.float32)/255
    # Some real Egret screenshots are premultiplied-alpha. RGB classification
    # is diagnostic only; isolated native alpha geometry is the primary gate.
    rgb=pixels[:,:,:3].astype(np.float32)*alpha[:,:,None]+255*(1-alpha[:,:,None])
    labels=np.empty(pixels.shape[:2],dtype=np.uint8)
    flat=rgb.reshape(-1,3)
    for start in range(0,len(flat),65536):
        chunk=flat[start:start+65536]
        dist=((chunk[:,None,:]-lut[None,:,:])**2).sum(axis=2)
        labels.flat[start:start+len(chunk)]=palette_keys[np.argmin(dist,axis=1)]
    return labels


def metrics(variants:dict,labels:np.ndarray,palette:dict,
            workspace:Path,out:Path)->dict:
    colors={int(k):tuple(c) for k,c in palette["palette_rgb"].items()}
    bg=int(palette["background_index"])
    labels3=np.repeat(np.repeat(labels,SCALE,axis=0),SCALE,axis=1)
    result={}
    for variant,strokes in variants.items():
        region=out/variant
        region.mkdir(exist_ok=True)
        rgba,scene,manifest=native_batch(workspace,variant,strokes,region)
        per_color={}
        union=np.zeros(labels3.shape,dtype=bool)
        for color in sorted(colors):
            if color==bg: continue
            plan=[s for s in strokes if s["colorIndex"]==color]
            target=labels3==color
            native=(rgba[f"color-{color}"][:,:,3]>=ALPHA_MIN) if plan else np.zeros_like(target)
            union|=native
            own=compare(target,native)
            halo=measure_halo(target,native)
            foreign=native&(labels3!=color)&(labels3!=bg)
            per_color[str(color)]={
                "strokes":len(plan),
                "synthetic_vertices_not_chalk":sum(len(s["points"]) for s in plan),
                "target_pixels":int(target.sum()),
                "native":own,"exterior":halo,
                "native_overlap_into_other_color_pixels":int(foreign.sum()),
                "diagnostic_quality_pass":bool(own["coverage"]>=.99 and halo["all_leakage_in_3logical_halo"])
            }
        foreground=labels3!=bg
        silhouette=compare(foreground,union)
        classified=classify_composite(rgba["composite"],colors,bg)
        accuracy=float(np.count_nonzero(classified[foreground]==labels3[foreground])/max(1,foreground.sum()))
        confused=Counter()
        for k in sorted(colors):
            if k==bg:continue
            for j in sorted(colors):
                if j==k:continue
                amount=int(np.count_nonzero((labels3==k)&(classified==j)))
                if amount:confused[f"{k}->{j}"]=amount
        sizes=[s["width"] for s in strokes]
        res={
            "strokes":len(strokes),
            "synthetic_vertices_not_chalk":sum(len(s["points"]) for s in strokes),
            "brush_switches":sum(a!=b for a,b in zip(sizes,sizes[1:])),
            "brush_widths":dict(Counter(str(s["width"]) for s in strokes)),
            "per_color":per_color,
            "silhouette":silhouette,
            "composited_nearest_palette_accuracy_foreground":accuracy,
            "composited_wrong_color_confusion":dict(confused),
            "native_scenes":scene,
            "manifest":manifest,
            "status":"PASS_OFFLINE_EACH_COLOR" if all(
                x["diagnostic_quality_pass"] for x in per_color.values()
            ) else "FAIL_OFFLINE_COLOR_GATE"
        }
        result[variant]=res
        Image.fromarray((classified.astype(np.uint8)),"L").save(region/f"{variant}-classified-index.png")
        composite=Image.fromarray(rgba["composite"],"RGBA")
        white=Image.new("RGBA",composite.size,(255,255,255,255))
        Image.alpha_composite(white,composite).convert("RGB").save(region/f"{variant}-over-white.png")
    return result


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,default=Path("."))
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    workspace=args.workspace.resolve()
    out=args.output_dir.resolve()
    out.mkdir(exist_ok=True,parents=True)
    labels,source,logical=source_palette(workspace)
    logical.save(out/"logical-color-original.png")
    palette_rgb=source["palette_rgb"]
    reconstructed=np.zeros((*labels.shape,3),dtype=np.uint8)
    for k,rgb in palette_rgb.items():
        reconstructed[labels==int(k)]=rgb
    Image.fromarray(reconstructed,"RGB").save(out/"quantized-target.png")
    Image.fromarray(labels,"L").save(out/"quantized-labels.png")
    variants,planning=build_variants(labels,source)
    for name,strokes in variants.items():
        (out/f"{name}-planned-strokes.json").write_text(
            json.dumps({"experiment_id":EXP_ID,"variant":name,"strokes":strokes},
                       ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"pre-render-planning.json").write_text(json.dumps(
        {"experiment_id":EXP_ID,"source":source,"planning":planning},
        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    observed=metrics(variants,labels,source,workspace,out)
    report={
        "experiment_id":EXP_ID,"preregistered_before_native":True,
        "source":source,
        "planning":planning,
        "observed":observed,
        "overall_status":"OFFLINE_HOLDOUT_MEASURED_NOT_GAME",
        "limitations":[
            "Palette 8-class MEDIANCUT is a deliberately coarse proxy for multicolor artwork",
            "The repo PNG Git blob, not the user-chat resized copy, is the frozen source",
            "Original full-resolution details are lost in aspect-preserving 460x240 scaling",
            "Nearest-palette composited RGB is diagnostic; exact stroke-class native alpha is separately measured",
            "No E4/live RGB8 audit, actual game CHALK or independent E5",
            "No gameplay executor or production preset changed"
        ]
    }
    (out/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for variant,s in observed.items():
        print(EXP_ID,variant,s["status"],
              "strokes",s["strokes"],"vertices",s["synthetic_vertices_not_chalk"],
              "silhouette_cov",s["silhouette"]["coverage"],
              "color_acc",s["composited_nearest_palette_accuracy_foreground"],
              flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
