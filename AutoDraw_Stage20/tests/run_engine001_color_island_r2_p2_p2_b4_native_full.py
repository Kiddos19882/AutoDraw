#!/usr/bin/env python3
"""B4 genuine archived Egret paint + 410 details LAST, original vs actual-game32 contour."""
from __future__ import annotations
import argparse,hashlib,io,json,os,platform,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from skimage.color import rgb2lab, deltaE_ciede2000
from run_engine001_color32_p4c2_full_native import (
    load_frozen_archive,OWNERS,assess_native,FROZEN_PAINT_PATHS,FROZEN_PAINT_VERTICES)
from run_engine001_color32_s2b_egret_p1 import native_metrics
from run_engine001_palette32_region_study import read_palette,read_source
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_color_island_r2_p2_p2_b1_p0_game32 import git_blob,valid_zip

EXP="ENGINE001_COLOR_ISLAND_R2_P2_P2_B4_NATIVE_FULL_COLOR_OUTLINE"
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
PALETTE_BLOB="461b5f3725b9b79888ad36e807b3cf4c9e445e98"
RENDERER_B4_BLOB="c6df789a22b6ae0d205829d5858afff99b1bb4c2"
P4C1_SHA="fac1fcf1ff6a43ac6e59da116b68b86e2238c2da13be0b167cf34f8241ac5eeb"
P4C2_SHA="edc15612da5660de0fd3e12c06bddfc4e0e6fec3dc6310d37c9abe46ec5344e7"
P4C2_CI_SHA="eae3061f11612fb48d39704aadd92b731d2ab1d8"
V44_SHA="43cb8e14a7e387b26772612ac06d1c7c6f176b8bd0c2d41e8945042fc80304a1"
V44_PLAN_SHA="9db4dda0661ea529547e91a09dcae38b27043dad57383fb483b945f0de08496a"
V44_DETAIL_PNG_SHA="0145975e4578bc86c1e4feb44d5ff93ecd486d576faf97626e1267a5c12b0275"
VARIANTS=("B4_A_ORIGINAL_DETAIL_RGB","B4_B_DETAIL_NEAREST32")
ROI=(465,0,915,720)

def sha(data):return hashlib.sha256(data).hexdigest()
def parse_rgb(color_int): return [(color_int>>16)&255,(color_int>>8)&255,color_int&255]
def to_int(rgb):return (int(rgb[0])<<16)|(int(rgb[1])<<8)|int(rgb[2])

def nearest_original_detail_palette(details,palette):
    if len(details)!=410 or palette.shape!=(32,3):raise ValueError("BLOCKED_B4_DETAIL_OR_PALETTE")
    original_colors=np.array([parse_rgb(s["colorRgb"]) for s in details],np.uint8)
    labs=rgb2lab(original_colors[None,:,:]/255.)[0]
    plabs=rgb2lab(palette[None,:,:]/255.)[0]
    de=deltaE_ciede2000(labs[:,None,:],plabs[None,:,:])
    indices=np.argmin(de,axis=1)
    changed=[]
    table=[]
    for i,(s,idx) in enumerate(zip(details,indices)):
        modified={**s,"colorRgb":to_int(palette[idx])}
        changed.append(modified)
        table.append({"strokeId":s["strokeId"],"original_RGB_int":int(s["colorRgb"]),
                      "game32_index":int(idx),"game32_RGB_int":int(modified["colorRgb"]),
                      "original_to_game32_deltaE00":float(de[i,idx])})
    return changed,table

def validate_detail(details):
    if len(details)!=410:raise ValueError("BLOCKED_B4_CONTOUR_COUNT")
    for i,d in enumerate(details):
        if (d.get("strokeId")!=f"detail-v18-B-{i}" or d.get("colorIndex")!=100 or
            d.get("width")!=1 or not isinstance(d.get("colorRgb"),int) or
            not 0<=d["colorRgb"]<=0xffffff or not 2<=len(d.get("points",[]))<=128):
            raise ValueError("BLOCKED_B4_CONTOUR_ID_OR_GEOMETRY")
        for p in d["points"]:
            if not (isinstance(p,dict) and 0<=p.get("x",-1)<460 and 0<=p.get("y",-1)<240):
                raise ValueError("BLOCKED_B4_CONTOUR_POINT")
    if sum(len(d["points"]) for d in details)!=1792:
        raise ValueError("BLOCKED_B4_CONTOUR_VERTICES")
    if len({d["colorRgb"] for d in details})!=395:
        raise ValueError("BLOCKED_B4_ORIGINAL_RGB_COUNT")

def immutable_inputs(source,palette_path,renderer_path,p4c1_zip,p4c2_zip,v44_zip):
    if sha(source.read_bytes())!=SOURCE_SHA:raise ValueError("BLOCKED_B4_SOURCE_SHA")
    if git_blob(palette_path.read_bytes())!=PALETTE_BLOB:
        raise ValueError("BLOCKED_B4_PALETTE_BLOB")
    if git_blob(renderer_path.read_bytes())!=RENDERER_B4_BLOB:
        raise ValueError("BLOCKED_B4_RENDERER_BLOB")
    palette=read_palette(palette_path)
    g,paint=load_frozen_archive(p4c1_zip)
    if len(paint)!=FROZEN_PAINT_PATHS or sum(len(s["points"]) for s in paint)!=FROZEN_PAINT_VERTICES:
        raise ValueError("BLOCKED_B4_PAINT_COUNT")
    for s in paint:
        if s["colorRgb"]!=to_int(palette[s["colorIndex"]]):
            raise ValueError("BLOCKED_B4_PAINT_RGB_OFF_PALETTE")
    with valid_zip(p4c2_zip,P4C2_SHA) as p:
        base=json.loads(p.read("report.json"))
        if (base.get("github_sha")!=P4C2_CI_SHA or
            str(base.get("github_run_id"))!="44139390005" or
            base.get("status")!="P4C2_NATIVE_PAINT_FAIL" or
            base["native_observations"]["native_alpha24_all17_ge99"] or
            len(base["native_observations"]["owners_below99_native_alpha24"])!=14 or
            base.get("original_410_V44B_LAST")!="NOT_RENDERED_UNCHANGED"):
            raise ValueError("BLOCKED_B4_FROZEN_P4C2_IDENTITY")
        original_ref={}
        for index in OWNERS:
            name=f"P4c1-PAINT-ONLY/P4c1-PAINT-ONLY-color-{index}.png"
            if sha(p.read(name))!=base["linked_file_SHA256"][name]:
                raise ValueError("BLOCKED_B4_P4C2_LINKED_SHA")
            original_ref[index]=np.asarray(Image.open(io.BytesIO(p.read(name))).convert("RGBA"))
    with valid_zip(v44_zip,V44_SHA) as v:
        if sha(v.read("color-plans.json"))!=V44_PLAN_SHA or sha(v.read("B/V44-B-color-100.png"))!=V44_DETAIL_PNG_SHA:
            raise ValueError("BLOCKED_B4_V44_PLAN_OR_DETAIL_SHA")
        plan=json.loads(v.read("color-plans.json"))
        if len(plan["plans"]["B"]["strokes"])!=2355:
            raise ValueError("BLOCKED_B4_V44_STROKES")
        originals=plan["plans"]["B"]["strokes"][-410:]
        if any(e.get("layer")!="detail" for e in originals):
            raise ValueError("BLOCKED_B4_CONTOUR_NOT_LAST")
        details=[e["stroke"] for e in originals]
        validate_detail(details)
    return g,paint,details,palette,base,original_ref

def assembled(paint,details):
    strokes=paint+details
    if (len(strokes)!=1543 or sum(len(s["points"]) for s in strokes)!=5277 or
        len({s["strokeId"] for s in strokes})!=1543):
        raise ValueError("BLOCKED_B4_RESOURCE_OR_IDS")
    if any(s["colorIndex"]==100 for s in paint) or any(s["colorIndex"]!=100 for s in details):
        raise ValueError("BLOCKED_B4_ORDER")
    return strokes

def _stats(source_rgb,real_native_frame):
    # Diagnostic only: only RGB from actual Egret composite on white backing.
    full=Image.fromarray(real_native_frame,"RGBA")
    white=Image.new("RGBA",full.size,(255,255,255,255))
    cropped=Image.alpha_composite(white,full).crop(ROI).convert("RGB")
    native=np.asarray(cropped.resize((150,240),Image.Resampling.BOX),np.uint8)
    de=deltaE_ciede2000(rgb2lab(source_rgb/255.),rgb2lab(native/255.))
    return cropped,{"mean_deltaE00_diagnostic":float(de.mean()),
                    "p95_deltaE00_diagnostic":float(np.percentile(de,95)),
                    "RGB_MAE_diagnostic":float(np.abs(source_rgb.astype(float)-native.astype(float)).mean())}

def _sheet(images,output):
    font=ImageFont.truetype("DejaVuSans.ttf",18)
    canvas=Image.new("RGB",(1800,768),"white")
    dr=ImageDraw.Draw(canvas)
    for i,(name,img) in enumerate(images.items()):
        x=i*450;canvas.paste(img,(x,48))
        dr.text((x+7,10),name,fill="black",font=font)
    canvas.save(output)

def run(workspace,source,palette_path,renderer_path,p4c1_zip,p4c2_zip,v44_zip,out):
    if out.exists():raise ValueError("BLOCKED_B4_NO_OVERWRITE")
    g,paint,original_details,palette,old_p4c2,old_owner_frames=immutable_inputs(
        source,palette_path,renderer_path,p4c1_zip,p4c2_zip,v44_zip)
    nearest_details,mapping=nearest_original_detail_palette(original_details,palette)
    # Freeze geometry and IDs: ONLY RGB allowed to change.
    for a,b in zip(original_details,nearest_details):
        if {k:v for k,v in a.items() if k!="colorRgb"}!={k:v for k,v in b.items() if k!="colorRgb"}:
            raise ValueError("BLOCKED_B4_DETAILS_GEOMETRY_CHANGED")
    out.mkdir(parents=True)
    (out/"detail_410_original_to_game32.json").write_text(
        json.dumps(mapping,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    _,original=read_source(source)
    if original.shape!=(240,150,3):raise ValueError("BLOCKED_B4_SOURCE_SIZE")
    game_rgb=palette[g]
    pictures={
        "Оригинал":Image.fromarray(original).resize((450,720),Image.Resampling.NEAREST),
        "G32 цель":Image.fromarray(game_rgb).resize((450,720),Image.Resampling.NEAREST)
    }
    reports={}
    for variant,detail in [(VARIANTS[0],original_details),(VARIANTS[1],nearest_details)]:
        folder=out/variant
        folder.mkdir()
        strokes=assembled(paint,detail)
        (folder/"frozen_complete_strokes.json").write_text(json.dumps(
            {"experiment":EXP,"variant":variant,"safe_to_execute_game":False,
             "strokes":strokes},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        rgba,meta,manifest=native_batch(workspace,variant,strokes,folder,
                                       renderer_method="renderB4FullGame32AndDetailProbe")
        required={f"color-{n}" for n in OWNERS}|{"color-100","composite"}
        if set(rgba)!=required:raise ValueError("BLOCKED_B4_NATIVE_COLORS_MISSING")
        if any(x.shape!=(720,1380,4) or x.dtype!=np.uint8 for x in rgba.values()):
            raise ValueError("BLOCKED_B4_NATIVE_BACKING_SHAPE")
        stable={int(i):bool(np.array_equal(rgba[f"color-{i}"][:,:,3],old_owner_frames[i][:,:,3]))
                for i in OWNERS}
        native=native_metrics(rgba,g,strokes)
        assessed=assess_native(native)
        scene,numeric=_stats(original,rgba["composite"])
        scene.save(out/(variant+"_native_real_ROI.png"))
        pictures[variant]=scene
        if variant==VARIANTS[0]:
            first_detail_alpha=rgba["color-100"][:,:,3].copy()
        else:
            detail_alpha_identical=bool(np.array_equal(first_detail_alpha,rgba["color-100"][:,:,3]))
        status=("E3_NATIVE_CAPTURE_PASS_QUALITY_FAIL" if
                not assessed["native_paint_numeric_gate"] or
                not all(stable.values()) else "E3_NATIVE_FULL_SCREEN_PASS_VISUAL_PENDING")
        reports[variant]={"status":status,"native_paint_gate":assessed,
                          "diagnostic_image_source_error":numeric,
                          "owner_native_alpha_pixel_identity_to_original_P4c2":stable,
                          "native_metadata":meta,"native_manifest":manifest,
                          "native_per_color_metrics":native,
                          "detail_geometry_preserved":True,
                          "all_full_native_strokes":len(strokes),
                          "all_synthetic_vertices_NOT_CHALK":sum(len(s["points"]) for s in strokes)}
    reports[VARIANTS[1]]["native_detail_alpha_pixel_identical_to_A"]=detail_alpha_identical
    _sheet(pictures,out/"B4_original_G32_native_A_B_comparison.png")
    errors=[x["original_to_game32_deltaE00"] for x in mapping]
    unique_src=len({x["original_RGB_int"] for x in mapping})
    unique_dst=len({x["game32_index"] for x in mapping})
    # no simulation-based fill correctness claims
    hashes={str(x.relative_to(out)).replace("\\","/"):sha(x.read_bytes())
            for x in sorted(out.rglob("*")) if x.is_file()}
    report={"experiment":EXP,"github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        "source_sha256":SOURCE_SHA,"renderer_b4_blob":RENDERER_B4_BLOB,
        "game32_palette_blob":PALETTE_BLOB,
        "p4c1_zip_sha256":P4C1_SHA,"p4c2_frozen_zip_sha256":P4C2_SHA,
        "v44_zip_sha256":V44_SHA,"original_detail_strokes":410,"original_contour_RGB_colors":unique_src,
        "game32_contour_used_palette_colors":unique_dst,
        "game32_contour_source_deltaE00_mean":float(np.mean(errors)),
        "game32_contour_source_deltaE00_p95":float(np.percentile(errors,95)),
        "source_G32_nonwhite_owners":list(OWNERS),"variants":reports,
        "full_native_paint_and_original_contour_rendered":True,
        "human_recognition":"PENDING","game_E4":"NOT_RUN","game_E5":"NOT_RUN",
        "real_game_CHALK":None,"production_accepted":False,
        "file_sha256":hashes,"versions":{"python":platform.python_version(),
                                          "numpy":np.__version__,"Pillow":Image.__version__}}
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for flag in ("workspace","source","palette","renderer","p4c1-archive","p4c2-archive","v44-archive","output"):
        p.add_argument("--"+flag,type=Path,required=True)
    a=p.parse_args()
    report=run(a.workspace,a.source,a.palette,a.renderer,a.p4c1_archive,a.p4c2_archive,a.v44_archive,a.output)
    print(json.dumps({"variants":{k:v["status"] for k,v in report["variants"].items()},
                      "detail_palette_used":report["game32_contour_used_palette_colors"],
                      "source_detail_RGB_colors":report["original_contour_RGB_colors"],
                      "real_game_CHALK":report["real_game_CHALK"]},ensure_ascii=False))
