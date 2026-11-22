#!/usr/bin/env python3
"""CTR1 source S4.4 four full ORIGINAL x2; raw unit cracks, no native drawing."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import time

import numpy as np
from PIL import Image, ImageDraw

import engine001_bpred_s4r1_generic_source_maps as source_io
import engine001_bpred_s4r1_dg1_source_detail_atoms as provisional
import engine001_bpred_s4r1_ctr1_source_contour as ctr
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_io

E0_FILE = "ENGINE001_BPRED001_S4R1_CTR1_SOURCE_CONTOUR_PREREG_2026-11-22.md"
E0_BLOB = "5d0da0694ce0333e9d477fb2fb964329a06763eb"
ENGINE_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
SOURCES = (
    "testImages/wV6VeZI9S1Y.png",
    "data/generated_autodraw_plan/images_31_first/Sanrio_Characters_Hello_Kitty_Image026.webp",
    "data/generated_autodraw_plan/images_31_first/EZAL3k9ddfs.jpg",
    "data/generated_autodraw_plan/images_31_first/images (1).png",
)
RAW_KEYS = (
    "source_atom_id", "surface_id", "protected_original_dot",
    "game_index", "paintable_id", "baseline_index",
    "source_edge", "source_original_alpha",
    "contour_segments", "contour_source_lab", "preview_rgba"
)
PAINT_LIMITS = {SOURCES[0]: 5283, SOURCES[2]: 38682}
MAIN_LIMITS = {SOURCES[0]: 5444, SOURCES[2]: 39894}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def region_image(ids: np.ndarray, alpha: np.ndarray):
    img=np.zeros((*ids.shape,4),np.uint8)
    present=ids>0
    source=ids.astype(np.uint64)
    img[present,0]=((source[present]*73+49)%230+14).astype(np.uint8)
    img[present,1]=((source[present]*157+67)%230+14).astype(np.uint8)
    img[present,2]=((source[present]*191+89)%230+14).astype(np.uint8)
    img[...,3]=alpha
    return Image.fromarray(img,"RGBA")


def contour_debug_overlay(original: np.ndarray, data: dict) -> Image.Image:
    """NOT strokes or gameplay! Categorical visibility of unit source cracks."""
    h,w=original.shape[:2]
    scaled=Image.fromarray(original,"RGBA").convert("RGB").resize(
        (w*2,h*2),Image.Resampling.NEAREST)
    pen=ImageDraw.Draw(scaled)
    # These diagnostic colors are NOT intended game swatches or stroke colors.
    type_colors={1:(0,195,190),2:(252,34,178),3:(255,131,29)}
    for x0,y0,x1,y1,_,_,_,_,kind,_ in data["contour_segments"]:
        pen.line([(int(x0)*2,int(y0)*2),(int(x1)*2,int(y1)*2)],
                 fill=type_colors[int(kind)],width=1)
    return scaled


def atlas_images(folder: Path):
    names=[
        ("01_CURRENT_ORIGINAL.png","Original full RGB alpha"),
        ("02_PROVISIONAL_DG1_GAME128.png","Provisional DG1 game128: COLOR FAIL"),
        ("03_DG1_SOURCE_REGION_ID.png","DG1 source atom ids from current original"),
        ("04_CTR1_SOURCE_CONTOUR_DEBUG.png","Source cracks debug colors; NOT game ink"),
        ("05_TRUE_PAINTABLE_SOURCE_ID.png","Actual 4connected paintable"),
        ("06_PROTECTED_SOURCE_DOT.png","Original protected 1px source detail"),
    ]
    panel_w=380;panel_h=520
    out=Image.new("RGB",(3*panel_w,2*panel_h),(245,245,245))
    draw=ImageDraw.Draw(out)
    for i,(name,label) in enumerate(names):
        x=(i%3)*panel_w
        y=(i//3)*panel_h
        draw.text((x+8,y+9),label,fill=(30,30,30))
        with Image.open(folder/name) as img:
            frame=img.convert("RGB")
            frame.thumbnail((panel_w-18,panel_h-45),Image.Resampling.LANCZOS)
        out.paste(frame,(x+(panel_w-frame.width)//2,y+30))
    out.save(folder/"00_CTR1_SOURCE_ATLAS.png")


def do_original(root:Path,relative:str,game128:np.ndarray,out:Path,index:int):
    input_path=root/relative
    original_bytes=input_path.read_bytes()
    decoded=source_io.decode_original(original_bytes)
    original=decoded["rgba"]
    folder=out/("%02d_%s"%(index,input_path.stem))
    folder.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(input_path,folder/("original"+input_path.suffix))
    start=time.perf_counter()
    data=ctr.build_ctr1(original,game128)
    first=time.perf_counter()-start
    start=time.perf_counter()
    again=ctr.build_ctr1(original,game128)
    repeat=time.perf_counter()-start
    for key in RAW_KEYS:
        if not np.array_equal(data[key],again[key]):
            raise ValueError("BLOCKED_CTR1_ORIGINAL_REPLAY_DIFFERENT_"+key)
    if data["contour_summary"]!=again["contour_summary"] or data["counts"]!=again["counts"]:
        raise ValueError("BLOCKED_CTR1_SOURCE_COUNT_REPLAY")
    opaque=original[...,3]==255
    original_preview=Image.fromarray(original,"RGBA")
    protected=original.copy()
    protected[data["protected_original_dot"],:3]=[255,75,0]
    stored={
        "01_CURRENT_ORIGINAL.png":original_preview,
        "02_PROVISIONAL_DG1_GAME128.png":Image.fromarray(data["preview_rgba"],"RGBA"),
        "03_DG1_SOURCE_REGION_ID.png":region_image(data["source_atom_id"],original[...,3]),
        "04_CTR1_SOURCE_CONTOUR_DEBUG.png":contour_debug_overlay(original,data),
        "05_TRUE_PAINTABLE_SOURCE_ID.png":region_image(data["paintable_id"],original[...,3]),
        "06_PROTECTED_SOURCE_DOT.png":Image.fromarray(protected,"RGBA"),
    }
    for name,image in stored.items():
        image.save(folder/name)
    atlas_images(folder)
    np.savez_compressed(folder/"07_CTR1_ORIGINAL_RAW_SOURCE_SEGMENTS.npz",
                        **{key:data[key] for key in RAW_KEYS})
    source_data={
        "preview_rgba":data["preview_rgba"],
        "paintable_id":data["paintable_id"],
        "game_index":data["game_index"],
        "baseline_index":data["baseline_index"],
        "surface_id":data["surface_id"],
        "source_edge":data["source_edge"],
    }
    source_metric=provisional.evaluate_dg1(original,game128,source_data)
    rgb_error=source_metric["candidate_rgb_mae"]
    rgb_control=source_metric["baseline_rgb_mae"]
    ratio=rgb_error/rgb_control if rgb_control>0 else None
    strong=source_metric["strong_source_contrast"]["retained_fraction"]
    region_n=data["counts"]["main_surfaces"]
    paint_n=data["counts"]["paintable_components"]
    summary=data["contour_summary"]
    metric={
        "source":relative,"dimensions_wh":[int(decoded["width"]),int(decoded["height"])],
        "decode_git_blob_sha1":decoded["git_blob_sha1"],
        "source_sha256":digest(original_bytes),
        "original_rgb_nearest128_mae":rgb_control,
        "provisional_DG1_rgb_mae":rgb_error,
        "provisional_DG1_rgb_ratio":ratio,
        "provisional_DG1_color_125_gate":"PASS" if ratio is not None and ratio<=1.25 else "FAIL",
        "original_true_strong_game128_retained_fraction":strong,
        "original_strong_game128_gate":strong>=.75 if relative in MAIN_LIMITS else None,
        "original_main":region_n,"original_main_gate":region_n<MAIN_LIMITS[relative] if relative in MAIN_LIMITS else None,
        "real_paintable":paint_n,"real_paintable_gate":paint_n<PAINT_LIMITS[relative] if relative in PAINT_LIMITS else None,
        "provisional_DG1_atoms":int(data["counts"]["source_atoms"]),
        "source_segments":summary,
        "first_build_sec":round(first,3),"repeat_build_sec":round(repeat,3),
    }
    manifest={
        "version":ctr.VERSION,"task":"ENGINE-001 S4.4 CTR1 RESEARCH_ONLY",
        "e0_git_blob_sha1":E0_BLOB,"engine_git_blob_sha1":ENGINE_BLOB,
        "game128_sha256":digest(game128.tobytes()),
        "source_path":relative,"source_sha256":digest(original_bytes),
        "decoded_git_blob_sha1":decoded["git_blob_sha1"],
        "original_mode":decoded["original_mode"],
        "exif_orientation":decoded["exif_orientation"],
        "source_original_only":True,
        "old_candidate_artistic_input":False,
        "current_original_regenerated_DG1":True,
        "source_owner_status":data["source_owner_status"],
        "stroke_admission":data["stroke_admission"],
        "source_to_logical":data["source_to_logical"],
        "contour_source_frame":"integer original source pixel corners, NOT brush",
        "game_chalk":"NOT_RUN","native_Egret":"NOT_RUN","formal_BPREDS4":"BLOCKED",
        "provisional_source_quality":data["provisional_source_quality"],
        "two_builds_raw_bitwise_equal":True,
        "source_metric":metric,
        "review":"SOURCE_ONLY_PENDING_INDEPENDENT_VISUAL",
        "outputs_sha256":{},
    }
    for f in sorted(folder.iterdir()):
        if f.is_file():
            manifest["outputs_sha256"][f.name]=digest(f.read_bytes())
    (folder/"manifest.json").write_text(
        json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False),encoding="utf-8")
    return metric


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output",type=Path,required=True)
    options=parser.parse_args()
    root=options.root.resolve()
    out=options.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    game128,provenance=palette_io.read_engine_palette(root/"gameEngine/main.min_653f95bc.js")
    if provenance["engine_git_blob_sha1"]!=ENGINE_BLOB:
        raise ValueError("BLOCKED_CTR1_GENUINE_ENGINE128_SHA")
    sources=[do_original(root,p,game128,out,i) for i,p in enumerate(SOURCES)]
    aggregate={
        "version":ctr.VERSION,"e0_git_blob_sha1":E0_BLOB,
        "engine_git_blob_sha1":ENGINE_BLOB,"full_original_count":len(SOURCES),
        "repeat_clean_builds_per_original":2,
        "source_original_only":True,"old_artistic_inputs":False,
        "provisional_color_source_acceptance":"FAIL_NOT_PROMOTED",
        "source_contour_geometry_research_review":"PENDING_VISUAL",
        "formal_BPREDS4":"BLOCKED","native":"NOT_RUN","exact_game_chalk":"NOT_RUN",
        "source_metrics":sources,
    }
    (out/"00_CTR1_SUMMARY.json").write_text(
        json.dumps(aggregate,sort_keys=True,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(aggregate,sort_keys=True,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
