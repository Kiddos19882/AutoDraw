#!/usr/bin/env python3
"""ENGINE-001 P4b: original Egret V44-B detail-only over SOURCE bitmap G/H.

This is a HYBRID VISUAL CONTROL, not native brush coverage or game CHALK.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
import os
import platform
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

EXP = "ENGINE001_COLOR32_S2B_P4B_V44B_HYBRID_VISUAL_ONLY"
P4A_RUN = 44015038442
V44_RUN = 43813812976
P4A_ZIP_SHA = "d02ec009f2b0cba026a4d6ef23e25021bab6e77174f15b2ee8ab655bae3f552b"
V44_ZIP_SHA = "43cb8e14a7e387b26772612ac06d1c7c6f176b8bd0c2d41e8945042fc80304a1"
P4A_REPORT_SHA = "5548a540173ca9afbea5b237df919d7030c8f32fa8294eb0c354938cf87dca85"
V44_REPORT_SHA = "c729a81eb1c84cc0778b1f316f1a0e039c447d83ec147002484bb6c4212ff428"
V44_PLAN_SHA = "9db4dda0661ea529547e91a09dcae38b27043dad57383fb483b945f0de08496a"
V44_DETAILS_SHA = "0145975e4578bc86c1e4feb44d5ff93ecd486d576faf97626e1267a5c12b0275"
P4A_G_SHA = "da8017729cb4d53d5cd3a9e5325a1aeb214e85985136c1088dff8269f32329ff"
P4A_H_SHA = "9d650a0ade0301c27d11a77ea8284336a6bcad9e7ef65e55595ba3494622e8cf"
V44_CI_SHA = "0a58bf36fa9cc3f72803563d4617622987812498"
P4A_CI_SHA = "6f4b4b9e64872591257bbf67731eb2bbb0d8eccd"

BACKING_SIZE=(1380,720)
ROI_BOX=(465,0,915,720)
ROI_WH=(150,240)


def _sha_bytes(b:bytes)->str:
    return sha256(b).hexdigest()


def _read_zip_archive(path:Path, expected_sha:str,
                      expected_report_sha:str, run_id:int,
                      expected_git_sha:str, manifest_name:str):
    if not path.is_file() or _sha_bytes(path.read_bytes()) != expected_sha:
        raise ValueError("BLOCKED_P4B_ARCHIVE_SHA_DRIFT")
    archive=ZipFile(path)
    if archive.testzip() is not None:
        raise ValueError("BLOCKED_P4B_ZIP_CRC")
    report_bytes=archive.read("report.json")
    if _sha_bytes(report_bytes) != expected_report_sha:
        raise ValueError("BLOCKED_P4B_REPORT_SHA_DRIFT")
    report=json.loads(report_bytes)
    if run_id==P4A_RUN:
        if (report.get("experiment") !=
                "ENGINE001_COLOR32_S2B_P4A_COMPONENT_ISLAND_SOURCE_ONLY" or
                report.get("github_sha") != expected_git_sha or
                str(report.get("github_run_id")) != str(run_id) or
                report.get("status") != "SOURCE_GATE_PASS_VISUAL_PENDING"):
            raise ValueError("BLOCKED_P4B_P4A_RUN_PROVENANCE")
    else:
        if (report.get("experiment") !=
                "ENGINE001_ADAPTIVE_COLOR_OUTLINE_V44_P1" or
                not report.get("native_alpha_exact_all_variants")):
            raise ValueError("BLOCKED_P4B_V44_ARCHIVE_PROVENANCE")
    linked=report.get(manifest_name)
    if not isinstance(linked,dict) or not linked:
        raise ValueError("BLOCKED_P4B_ARCHIVE_MANIFEST")
    for name,expected in linked.items():
        if (name.startswith("/") or ".." in Path(name).parts or
                _sha_bytes(archive.read(name))!=expected):
            raise ValueError("BLOCKED_P4B_ORIGINAL_ARTIFACT_FILE_SHA")
    return archive,report


def validate_original_detail_plan(plan:dict):
    if (plan.get("experiment") != "ENGINE001_ADAPTIVE_COLOR_OUTLINE_V44_P1" or
            plan.get("baseline") != "V37-P2-C" or
            not isinstance(plan.get("plans"),dict)):
        raise ValueError("BLOCKED_P4B_V44_PLAN_SCHEMA")
    source=plan["plans"]["B"]["strokes"]
    if len(source)!=2355:
        raise ValueError("BLOCKED_P4B_ORIGINAL_V44_STROKE_COUNT")
    if any(x["layer"]!="paint" for x in source[:-410]):
        raise ValueError("BLOCKED_P4B_ORIGINAL_FILL_ORDER")
    entries=source[-410:]
    if any(x["layer"]!="detail" for x in entries):
        raise ValueError("BLOCKED_P4B_ORIGINAL_CONTOUR_LAST")
    details=[e["stroke"] for e in entries]
    ids=[s["strokeId"] for s in details]
    if (ids!=[f"detail-v18-B-{i}" for i in range(410)] or
            any(s.get("width")!=1 or s.get("colorIndex")!=100 or
                not isinstance(s.get("colorRgb"),int) or
                not 0<=s["colorRgb"]<=0xffffff or
                not 2<=len(s["points"])<=128 for s in details) or
            sum(len(s["points"]) for s in details)!=1792):
        raise ValueError("BLOCKED_P4B_ORIGINAL_410_DETAIL_IDENTITY")
    if any(e["stroke"].get("colorIndex")==100 for e in source[:-410]):
        raise ValueError("BLOCKED_P4B_COLOR_100_CONTAINS_PAINT")
    return {
        "original_contours_LAST":410,
        "native_width":1,
        "detail_vertices_NOT_CHALK":1792,
        "original_color_index_100_only_contains_details":True,
        "distinct_original_source_contour_RGB":len({s["colorRgb"] for s in details}),
        "geometry_color_order_unmodified":True,
    }


def _opaque_source_backing(roi:Image.Image)->Image.Image:
    if roi.size!=ROI_WH or roi.mode!="RGB":
        raise ValueError("BLOCKED_P4B_SOURCE_ROI_OR_RGB")
    full=Image.new("RGBA",BACKING_SIZE,(255,255,255,255))
    backing=roi.resize((450,720),Image.Resampling.NEAREST).convert("RGBA")
    full.paste(backing,ROI_BOX[:2])
    return full


def compose(original_roi:Image.Image,detail_rgba:Image.Image):
    if detail_rgba.mode!="RGBA" or detail_rgba.size!=BACKING_SIZE:
        raise ValueError("BLOCKED_P4B_NATIVE_CONTOUR_BACKING")
    raw=_opaque_source_backing(original_roi)
    overlay=Image.alpha_composite(raw,detail_rgba)
    return raw,overlay


def run(p4a_archive:Path,v44_archive:Path,output:Path):
    if output.exists():
        raise ValueError("BLOCKED_P4B_OUTPUT_ALREADY_EXISTS")
    pa,ap=_read_zip_archive(p4a_archive,P4A_ZIP_SHA,P4A_REPORT_SHA,
                            P4A_RUN,P4A_CI_SHA,"file_sha256")
    va,vp=_read_zip_archive(v44_archive,V44_ZIP_SHA,V44_REPORT_SHA,
                            V44_RUN,V44_CI_SHA,"report_linked_SHA256")
    try:
        if (ap["original_G_index_png_SHA256"] !=
                "b8dcd5f00d2c39c81997aaae084eaae19a776454e6fd6466209839288c1e5637" or
                ap["P4a_merges"]["changed_pixel_count"]!=67 or
                not ap["P4a_source_checks"]["passed"]):
            raise ValueError("BLOCKED_P4B_G_H_TARGET_DRIFT")
        if (_sha_bytes(pa.read("G_frozen_game32_RGB.png"))!=P4A_G_SHA or
                _sha_bytes(pa.read("H_component_aware_game32_RGB.png"))!=P4A_H_SHA or
                _sha_bytes(va.read("color-plans.json"))!=V44_PLAN_SHA or
                _sha_bytes(va.read("B/V44-B-color-100.png"))!=V44_DETAILS_SHA):
            raise ValueError("BLOCKED_P4B_FROZEN_PREVIEW_INPUT_DRIFT")
        original_plan=json.loads(va.read("color-plans.json"))
        detail_info=validate_original_detail_plan(original_plan)
        contour_png=va.read("B/V44-B-color-100.png")
        detail=Image.open(BytesIO(contour_png)).convert("RGBA")
        if detail.size!=BACKING_SIZE:
            raise ValueError("BLOCKED_P4B_BACKING_SCALE")
        alpha=np.asarray(detail)[:,:,3]
        roi=(slice(0,BACKING_SIZE[1]),slice(ROI_BOX[0],ROI_BOX[2]))
        if alpha.shape != (720,1380):
            raise ValueError("BLOCKED_P4B_ALPHA_SHAPE")
        backgrounds={
            "original":Image.open(BytesIO(pa.read("original_source.png"))).convert("RGB"),
            "G":Image.open(BytesIO(pa.read("G_frozen_game32_RGB.png"))).convert("RGB"),
            "H":Image.open(BytesIO(pa.read("H_component_aware_game32_RGB.png"))).convert("RGB"),
        }
        output.mkdir(parents=True)
        (output/"original_V44B_native_detail_only.png").write_bytes(contour_png)
        screens={}
        for label,img in backgrounds.items():
            base,over=compose(img,detail)
            screens[label]=(base,over)
            base.save(output/f"{label}_without_V44B_hybrid.png")
            over.save(output/f"{label}_with_original_V44B_hybrid.png")
        ref=np.asarray(screens["original"][0].convert("RGB"),dtype=np.int16)
        diagnostics={}
        for label,(base,over) in screens.items():
            variants={}
            for key,im in (("without",base),("with",over)):
                arr=np.asarray(im.convert("RGB"),dtype=np.int16)
                original_roi=ref[roi]
                variants[key]={
                    "source_backing_RGBA_full_size":list(im.size),
                    "MAE_against_original_source_BACKING_RGB_DIAGNOSTIC_ONLY":
                        float(np.abs(arr[roi]-original_roi).mean()),
                }
            diagnostics[label]=variants
        names=["original","G","G","H","H"]
        with_outline=[False,False,True,False,True]
        pane=Image.new("RGB",(5*450,760),(255,255,255))
        draw=ImageDraw.Draw(pane)
        try:
            font=ImageFont.truetype("DejaVuSans.ttf",16)
        except OSError:
            font=ImageFont.load_default()
        captions=[
            "Original source","Game32 G source raster",
            "G + original Egret V44-B","Game32 H source raster",
            "H + original Egret V44-B"
        ]
        for i,(name,use_outline) in enumerate(zip(names,with_outline)):
            frame=screens[name][int(use_outline)].convert("RGB")
            pane.paste(frame.crop(ROI_BOX),(i*450,40))
            draw.text((i*450+5,12),captions[i],fill=(0,0,0),font=font)
        pane.save(output/"original_G_H_with_without_Egret_V44B_hybrid_comparison.png")
        files={f.name:_sha_bytes(f.read_bytes()) for f in sorted(output.iterdir())
               if f.is_file()}
        report={
            "experiment":EXP,
            "status":"HYBRID_INTEGRITY_PASS_VISUAL_PENDING",
            "github_sha":os.environ.get("GITHUB_SHA"),
            "github_run_id":os.environ.get("GITHUB_RUN_ID"),
            "original_P4a_run":P4A_RUN,
            "original_V44_B_E3_run":V44_RUN,
            "original_P4a_ZIP_SHA256":P4A_ZIP_SHA,
            "original_V44_ZIP_SHA256":V44_ZIP_SHA,
            "original_G_source_original_index_png_SHA256":ap["original_G_index_png_SHA256"],
            "original_V44_B_original_detail_RGBA_SHA256":V44_DETAILS_SHA,
            "original_V44_B_color_plans_SHA256":V44_PLAN_SHA,
            "original_410_detail_identity":detail_info,
            "original_native_detail_alpha24_pixels":int(np.count_nonzero(alpha>=24)),
            "original_native_detail_alpha128_pixels":int(np.count_nonzero(alpha>=128)),
            "original_native_detail_alpha24_pixels_outside_150x240_ROI":
                int(np.count_nonzero(alpha>=24) -
                    np.count_nonzero(alpha[roi]>=24)),
            "backing_geometry":{"game_logical_wh":[460,240],
                                "source_ROI_logical_x0":155,
                                "ROI_logical_wh":[150,240],
                                "png_backing_wh":list(BACKING_SIZE),
                                "source_scale_factor":3},
            "bitmap_background_is_source_only_NOT_native_brush":True,
            "outline_alpha_is_original_boardpane_webgl_E3":True,
            "color_compositing_Pillow_NOT_original_Egret":True,
            "human_visual_review":"PENDING",
            "full_native_color_fill":"NOT_RUN",
            "per_owner_99pct_real_Egret":"NOT_RUN",
            "game_E4":"NOT_RUN","E5":"NOT_RUN",
            "exact_game_CHALK":None,
            "production_accepted":False,
            "diagnostic_source_RGB_error":diagnostics,
            "file_sha256":files,
            "versions":{"python":platform.python_version(),
                        "Pillow":Image.__version__,
                        "numpy":np.__version__},
        }
        (output/"report.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
            encoding="utf-8")
        return report
    finally:
        pa.close()
        va.close()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--p4a-archive",type=Path,required=True)
    ap.add_argument("--v44-archive",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    r=run(a.p4a_archive,a.v44_archive,a.output)
    print(json.dumps({
        "status":r["status"],
        "true_Egret_original_410_contours":r["original_410_detail_identity"],
        "hybrid_rgb_diagnostic":r["diagnostic_source_RGB_error"],
        "native_fill":"NOT_RUN","exact_CHALK":None,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
