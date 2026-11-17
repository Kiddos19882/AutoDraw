#!/usr/bin/env python3
"""ENGINE-001 COLOR32-S2b-P4a: frozen G vs edge-locked component H, source E1/E2 ONLY.

No native brush, game run or CHALK; do not promote this into production.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import os
import platform
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage import color, measure

from run_engine001_color32_s2_edge_protection import (
    strong_edges, protected_merge, s1_rgb_gradient_overlap,
)
from run_engine001_palette32_region_study import (
    read_source, read_palette, nearest32, quality, topology, sha, palette_lab,
)
from run_engine001_color32_s2b_egret_p1 import (
    git_blob_sha, FROZEN_PALETTE_GIT_BLOB,
)

EXP = "ENGINE001_COLOR32_S2B_P4A_COMPONENT_ISLAND_SOURCE_ONLY"
FROZEN_G_INDEX_PNG_SHA256 = "b8dcd5f00d2c39c81997aaae084eaae19a776454e6fd6466209839288c1e5637"
ORIGINAL_SOURCE_SHA256 = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
MAX_COMPONENT_AREA = 24
MAX_EXTRA_DELTA_E00 = 2.0
MIN_SHARED_BOUNDARY_CONTACTS = 2
MAX_CHANGED_PIXELS = 360
MAX_MEAN_DELTA_E00_INCREASE = 0.10
MAX_RGB_EDGE_DROP_PP = 0.25
WHITE_OWNER = 30
ROI_SHAPE = (240, 150)


def _png_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def components_for(indices: np.ndarray, *, connectivity: int = 1) -> dict:
    totals = {}
    all_components = 0
    for owner in sorted(int(x) for x in np.unique(indices)):
        _, _, stats, _ = cv2.connectedComponentsWithStats(
            (indices == owner).astype(np.uint8),
            connectivity=4 if connectivity == 1 else 8,
        )
        areas = stats[1:, cv2.CC_STAT_AREA]
        counts = {str(limit):int(np.count_nonzero(areas <= limit))
                  for limit in (1, 2, 3, 8, 24)}
        totals[str(owner)] = {
            "components":len(areas),
            "pixels":int(areas.sum()),
            "tiny_components_leq_area":counts,
            "tiny_area_leq_24":int(areas[areas <= 24].sum()),
            "largest_component_pixels":int(areas.max()) if len(areas) else 0,
        }
        all_components += len(areas)
    return {"all_components":int(all_components),
            "per_game32_owner":totals, "connectivity":4 if connectivity == 1 else 8}


def component_aware_h(source: np.ndarray, g: np.ndarray, palette: np.ndarray,
                      protected: np.ndarray) -> tuple[np.ndarray, dict]:
    """One fixed pass over ORIGINAL G component geometry; never split components."""
    if (not isinstance(source,np.ndarray) or source.shape != (*ROI_SHAPE,3)
            or source.dtype != np.uint8 or not isinstance(g,np.ndarray)
            or g.shape != ROI_SHAPE or g.dtype != np.uint8
            or not isinstance(palette,np.ndarray) or palette.shape != (32,3)
            or palette.dtype != np.uint8
            or not isinstance(protected,np.ndarray) or protected.shape != ROI_SHAPE
            or protected.dtype != np.bool_ or int(g.max()) >= 32):
        raise ValueError("BLOCKED_P4A_SOURCE_GEOMETRY_OR_PALETTE")

    original_components = measure.label(g, connectivity=1, background=-1)
    regions = sorted(measure.regionprops(original_components),
                     key=lambda reg:(reg.area,reg.label))
    lab = color.rgb2lab(source / 255.0)
    plab = palette_lab(palette)
    de = color.deltaE_ciede2000(
        lab[:,:,None,:], plab[None,None,:,:])
    h = g.copy()
    accepted = []
    candidate_count = 0
    blocked_protected = 0
    blocked_color = 0
    blocked_contact = 0
    for reg in regions:
        if not 1 <= reg.area <= MAX_COMPONENT_AREA:
            continue
        ys,xs=reg.coords[:,0],reg.coords[:,1]
        owner=int(g[ys[0],xs[0]])
        if owner == WHITE_OWNER:
            continue
        candidate_count += 1
        if np.any(protected[ys,xs]):
            blocked_protected += 1
            continue
        touches=Counter()
        for y,x in reg.coords:
            for yy,xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if (0 <= yy < ROI_SHAPE[0] and
                        0 <= xx < ROI_SHAPE[1] and
                        original_components[yy,xx] != reg.label):
                    touches[int(g[yy,xx])] += 1
        if not any(c != owner and c != WHITE_OWNER and count >= MIN_SHARED_BOUNDARY_CONTACTS
                   for c,count in touches.items()):
            blocked_contact += 1
            continue
        base=de[ys,xs,owner]
        scores=[]
        for neighbor,shared in touches.items():
            if (neighbor == owner or neighbor == WHITE_OWNER or
                    shared < MIN_SHARED_BOUNDARY_CONTACTS):
                continue
            extra=float(np.mean(de[ys,xs,neighbor] - base))
            if extra <= MAX_EXTRA_DELTA_E00:
                scores.append((extra,-shared,neighbor))
        if not scores:
            blocked_color += 1
            continue
        extra,neg_shared,replacement=min(scores)
        h[ys,xs]=replacement
        accepted.append({
            "original_component_id":int(reg.label),
            "area_original_pixels":int(reg.area),
            "from_palette_index":owner,
            "to_palette_index":int(replacement),
            "mean_additional_delta_E00":float(extra),
            "shared_original_G_border_contacts":int(-neg_shared),
            "original_bbox_y0x0y1x1":[int(v) for v in reg.bbox],
        })
    if (np.any(h[protected] != g[protected]) or
            np.any(h[g==WHITE_OWNER] != WHITE_OWNER)):
        raise AssertionError("P4a protected or white color changed")
    modified=int(np.count_nonzero(h!=g))
    if modified != sum(item["area_original_pixels"] for item in accepted):
        raise AssertionError("P4a original-component whole-cell identity drift")
    return h, {
        "input_component_candidates_area_leq24_nonwhite":candidate_count,
        "blocked_if_any_protected_pixel":blocked_protected,
        "blocked_not_enough_original_border_contacts":blocked_contact,
        "blocked_no_eligible_delta_E00":blocked_color,
        "accepted_component_count":len(accepted),
        "changed_pixel_count":modified,
        "accepted_original_components":accepted,
        "full_Original_G_component_only":True,
        "no_white_to_from_reassignment":True,
        "one_pass":True,
        "same_color_overpaint_irrelevant_source_only":True,
    }


def source_checks(source:np.ndarray, g:np.ndarray, h:np.ndarray,
                  palette:np.ndarray, protected:np.ndarray) -> dict:
    gc=components_for(g)
    hc=components_for(h)
    g_error=float(quality(source,palette[g])["mean_delta_e00"])
    h_error=float(quality(source,palette[h])["mean_delta_e00"])
    g_edge=s1_rgb_gradient_overlap(source,palette[g])
    h_edge=s1_rgb_gradient_overlap(source,palette[h])
    changed=int(np.count_nonzero(g!=h))
    values = {
        "original_G_index_immutable":True,
        "protected_pixels_unchanged":bool(np.array_equal(g[protected],h[protected])),
        "white_pixel_unmodified":bool(np.all(h[g==WHITE_OWNER]==WHITE_OWNER)),
        "only_original_game32_swatch_indices":bool(
            np.all(np.isin(np.unique(h),np.unique(g))) and int(h.max())<32),
        "changed_pixels_from_1_to_360":bool(0<changed<=MAX_CHANGED_PIXELS),
        "4_connected_components_decreased_by_one_or_more":bool(
            hc["all_components"]<gc["all_components"]),
        "source_mean_delta_E00_within_G_plus_0_10":bool(
            h_error<=g_error+MAX_MEAN_DELTA_E00_INCREASE),
        "historic_S1_RGB_edge_overlap_within_G_minus_0_25pp":bool(
            h_edge>=g_edge-MAX_RGB_EDGE_DROP_PP),
    }
    return {
        "checks":values,"passed":all(values.values()),
        "changed_pixels":changed,
        "source_mean_deltaE00_G":g_error,"source_mean_deltaE00_H":h_error,
        "RGB_S1_overlap_pct_G":g_edge,"RGB_S1_overlap_pct_H":h_edge,
        "G_all_4_connected":gc["all_components"],
        "H_all_4_connected":hc["all_components"],
        "G_components":gc, "H_components":hc,
        "original_owner31_8connected_G":components_for(g,connectivity=2)["per_game32_owner"].get("31"),
        "original_owner29_8connected_G":components_for(g,connectivity=2)["per_game32_owner"].get("29"),
        "native_BoardPane":"NOT_RUN",
        "recognizability":"PENDING_VISUAL",
        "full_original_V44B410_overlay":"NOT_RUN",
        "E4_E5_game":"NOT_RUN","CHALK":None,
    }


def run(source_path:Path,palette_path:Path,output:Path):
    if output.exists():
        raise ValueError("BLOCKED_P4A_OUTPUT_ALREADY_EXISTS")
    if (sha(source_path) != ORIGINAL_SOURCE_SHA256 or
            git_blob_sha(palette_path) != FROZEN_PALETTE_GIT_BLOB):
        raise ValueError("BLOCKED_P4A_ORIGINAL_SOURCE_OR_PALETTE_DRIFT")
    _,source=read_source(source_path)
    palette=read_palette(palette_path)
    b=nearest32(source,palette)
    protected,threshold=strong_edges(source)
    g,original_g_stats=protected_merge(source,b,palette,protected)
    if hashlib.sha256(_png_bytes(g)).hexdigest()!=FROZEN_G_INDEX_PNG_SHA256:
        raise ValueError("BLOCKED_P4A_FROZEN_G_SOURCE_INDEX_DRIFT")
    h,model=component_aware_h(source,g,palette,protected)
    checks=source_checks(source,g,h,palette,protected)
    output.mkdir(parents=True)
    files={
        "original_source.png":source,
        "G_frozen_game32_RGB.png":palette[g],
        "G_frozen_game32_indices.png":g,
        "H_component_aware_game32_RGB.png":palette[h],
        "H_component_aware_game32_indices.png":h,
        "protected_source_edges.png":(protected.astype(np.uint8)*255),
        "changed_H_vs_G.png":((h!=g).astype(np.uint8)*255),
    }
    for name,array in files.items():
        Image.fromarray(array).save(output/name)
    # Contact sheet: exact side-by-side label-free pixels to avoid overlays
    # obscuring face/hair contours. Visual judgments remain manual.
    canvas=Image.new("RGB",(150*3,240),"white")
    for i,im in enumerate((source,palette[g],palette[h])):
        canvas.paste(Image.fromarray(im,"RGB"),(i*150,0))
    canvas.resize((1350,720),Image.Resampling.NEAREST).save(
        output/"side_by_side_original_G_H.png")
    hashes={p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    report={
        "experiment":EXP,
        "status":"SOURCE_GATE_PASS_VISUAL_PENDING" if checks["passed"] else "SOURCE_GATE_FAIL",
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "original_source_sha256":sha(source_path),
        "original_game32_palette_git_blob":FROZEN_PALETTE_GIT_BLOB,
        "original_G_index_png_SHA256":FROZEN_G_INDEX_PNG_SHA256,
        "frozen_G_prior_S2b_run_id":44003045004,
        "frozen_G_S2b_original_report_SHA256":
            "db975bff8b15f9ee54eded6e186cc7eb9279cb6b22df13f6db76351d4daaf25a",
        "original_G_source_settings":{"AREA":8,"EXTRA_deltaE00":5.0,"PASSES":2,
                                      "protected_sobel_percentile":90},
        "settings":{
            "component_connectivity":4,"min_area":1,"max_area":MAX_COMPONENT_AREA,
            "max_extra_delta_E00":MAX_EXTRA_DELTA_E00,
            "min_shared_original_border_contacts":MIN_SHARED_BOUNDARY_CONTACTS,
            "disallow_white_reassign":True,"max_modified_pixels":MAX_CHANGED_PIXELS,
            "max_mean_deltaE00_increase":MAX_MEAN_DELTA_E00_INCREASE,
            "max_S1_RGB_edge_drop_pp":MAX_RGB_EDGE_DROP_PP,
            "one_pass_original_G_only":True,
        },
        "protected_source_edge_threshold":threshold,
        "original_G_merge_stats":original_g_stats,
        "P4a_merges":model,
        "P4a_source_checks":checks,
        "visual_review":"PENDING",
        "source_only":True,
        "native_Egret":"NOT_RUN","full_image_quality":"NOT_RUN",
        "original_V44B_410_last":"NOT_RENDERED_UNMODIFIED",
        "E4_game":"NOT_RUN","E5":"NOT_RUN","exact_CHALK":None,
        "production_accepted":False,
        "file_sha256":hashes,
        "versions":{"python":platform.python_version(),
                    "numpy":np.__version__,"cv2":cv2.__version__},
    }
    (output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--palette",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=run(args.source,args.palette,args.output)
    print(json.dumps({
        "experiment":EXP,"status":result["status"],
        "changed_pixels":result["P4a_merges"]["changed_pixel_count"],
        "accepted_components":result["P4a_merges"]["accepted_component_count"],
        "checks":result["P4a_source_checks"]["checks"],
        "visual_review":result["visual_review"],
        "full_image_quality":result["full_image_quality"],
        "exact_CHALK":result["exact_CHALK"],
    },ensure_ascii=False))


if __name__=="__main__":
    main()
