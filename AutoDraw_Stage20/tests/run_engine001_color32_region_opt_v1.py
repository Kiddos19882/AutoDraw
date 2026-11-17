#!/usr/bin/env python3
"""ENGINE-001 COLOR32-V1: compare A=MEDIANCUT8, B=game32 CIEDE2000,
C=game32 SLIC, D=game32 SLIC + edge-aware small-region merging.

SOURCE-ONLY research. Never assume native BoardPane/Egret coverage or game CHALK.
All thresholds fixed in docs/ENGINE001_COLOR32_REGION_OPT_V1_PROTOCOL_2026-11-17.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from skimage.segmentation import slic

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "source" / "preparation"))
from palette_quantization import (  # noqa: E402
    delta_e_ciede2000, normalize_palette, quantize_image_to_palette, rgb_to_lab,
)

EXP = "ENGINE001_COLOR32_REGION_OPT_V1"
SOURCE_SHA = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
ROI = (150, 240)
SLIC_N_SEGMENTS = 350
SLIC_COMPACTNESS = 8
SLIC_SIGMA = 0
MERGE_MAX_PASSES = 3
MERGE_MAX_AREA = 16
MERGE_MAX_DE00 = 12.0
MERGE_MAX_RGB_P75 = 30.0
CANNY_LOW, CANNY_HIGH = 60, 120
FACE_HEIGHT = 125
LABEL_UNASSIGNED = -1


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_original(source: Path) -> Image.Image:
    if sha(source) != SOURCE_SHA:
        raise ValueError("BLOCKED_SOURCE_DRIFT exact original image SHA")
    with Image.open(source) as im:
        if im.size != (200, 320):
            raise ValueError("BLOCKED_SOURCE_DRIFT dimensions")
        return im.convert("RGB").resize(ROI, Image.Resampling.LANCZOS)


def load_game_palette(path: Path) -> tuple[list[dict], str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if len(raw.get("colors", [])) != 32:
        raise ValueError("BLOCKED_GAME_PALETTE_DRIFT expected exactly32")
    normalized = normalize_palette(raw["colors"])
    if len(normalized) != 32:
        raise ValueError("BLOCKED_GAME_PALETTE_DRIFT normalized count")
    for source, entry in zip(raw["colors"], normalized):
        if source["rgb"] != entry["rgb"]:
            raise ValueError("BLOCKED_GAME_PALETTE_DRIFT RGB altered")
    if "#FFFFFF" not in [c["hex"] for c in normalized]:
        raise ValueError("BLOCKED_GAME_PALETTE_DRIFT white absent")
    return normalized, sha(path)


def baseline_a(roi: Image.Image):
    q = roi.quantize(colors=8, method=Image.Quantize.MEDIANCUT,
                     dither=Image.Dither.NONE)
    raw = np.asarray(q, dtype=np.int32)
    ids = sorted(int(v) for v in np.unique(raw))
    if len(ids) != 8:
        raise ValueError("BLOCKED_BASELINE8 expected 8 labels")
    lookup = q.getpalette()
    colors = np.asarray([lookup[i*3:i*3+3] for i in ids], dtype=np.uint8)
    indexes = np.searchsorted(ids, raw).astype(np.int32)
    return indexes, colors


def nearest_game32(roi: Image.Image, palette: list[dict]) -> np.ndarray:
    result = quantize_image_to_palette(roi, palette)
    indexes = result.index_map
    if indexes.shape != (240, 150) or np.any(indexes < 0):
        raise ValueError("BLOCKED_GAME32 invalid quantization index map")
    return indexes.astype(np.int32)


def slic_game32(roi: Image.Image, palette: list[dict]):
    rgb = np.asarray(roi, dtype=np.uint8)
    superpixels = slic(rgb.astype(np.float32)/255.0,
                       n_segments=SLIC_N_SEGMENTS,
                       compactness=SLIC_COMPACTNESS,
                       sigma=SLIC_SIGMA,
                       start_label=0,
                       convert2lab=True,
                       enforce_connectivity=True,
                       channel_axis=-1)
    ids, inverse = np.unique(superpixels, return_inverse=True)
    if len(ids) < 2 or len(ids) > SLIC_N_SEGMENTS * 2:
        raise ValueError("BLOCKED_SLIC unexpected number of segments")
    flat = rgb.reshape(-1, 3).astype(np.float64)
    inverse = inverse.astype(np.int32, copy=False)
    sizes = np.bincount(inverse, minlength=len(ids))
    if np.any(sizes <= 0):
        raise ValueError("BLOCKED_SLIC empty superpixel")
    means = np.stack([np.bincount(inverse, weights=flat[:,c],
                                minlength=len(ids)) / sizes
                      for c in range(3)], axis=1)
    available = np.asarray([p["rgb"] for p in palette], dtype=np.uint8)
    d = delta_e_ciede2000(
        rgb_to_lab(means)[:,None,:], rgb_to_lab(available)[None,:,:])
    owner = np.argmin(d,axis=1).astype(np.int32)
    return owner[inverse].reshape(240,150).copy(), {
        "superpixels": int(len(ids)),
        "min_area": int(sizes.min()),
        "max_area": int(sizes.max()),
        "mean_area": float(np.mean(sizes)),
    }


def component_graph(indexes: np.ndarray, palette_size: int):
    """8-connected components per owner, including all tiny islands."""
    region = np.full(indexes.shape, -1, np.int32)
    owners, areas = [], []
    for color in range(palette_size):
        mask = (indexes == color).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        for k in range(1, n):
            region[labels == k] = len(owners)
            owners.append(color)
            areas.append(int(stats[k, cv2.CC_STAT_AREA]))
    if np.any(region < 0):
        raise ValueError("BLOCKED_COMPONENT missing source ownership")
    return region, np.asarray(owners, np.int32), np.asarray(areas, np.int32)


def boundary_neighbors(region: np.ndarray, y: int, x: int, owner: int,
                       source_rgb: np.ndarray):
    """8-neighbor RGB differences sampled strictly across component edges."""
    h,w = region.shape
    seen = []
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if dy == 0 and dx == 0:
                continue
            yy,xx = y+dy,x+dx
            if 0<=yy<h and 0<=xx<w and region[yy,xx]!=owner:
                seen.append((int(region[yy,xx]),
                    float(np.linalg.norm(source_rgb[y,x].astype(np.float64)-
                                         source_rgb[yy,xx].astype(np.float64)))))
    return seen


def merge_small_regions(indexes: np.ndarray, roi_rgb: np.ndarray,
                        palette: list[dict]):
    """Deterministic three-pass, fixed color-distance and source-edge guards."""
    if indexes.shape != (240,150) or roi_rgb.shape != (240,150,3):
        raise ValueError("BLOCKED_REGION geometry drift")
    palette_lab = rgb_to_lab(np.asarray([p["rgb"] for p in palette]))
    color_dist = delta_e_ciede2000(
        palette_lab[:,None,:], palette_lab[None,:,:])
    out = indexes.copy()
    runs = []
    for pass_id in range(MERGE_MAX_PASSES):
        reg, colors, areas = component_graph(out, len(palette))
        proposals = []
        rejected = Counter()
        for rid,area in enumerate(areas):
            if area > MERGE_MAX_AREA:
                continue
            coords = np.argwhere(reg==rid)
            neighbors = {}
            for y,x in coords:
                for other, delta in boundary_neighbors(reg,int(y),int(x),
                                                       rid,roi_rgb):
                    if other not in neighbors:
                        neighbors[other] = []
                    neighbors[other].append(delta)
            options = []
            for other, diffs in neighbors.items():
                target_color = int(colors[other])
                if target_color == int(colors[rid]):
                    # Same-color regions would be one component already.
                    continue
                de = float(color_dist[colors[rid],target_color])
                if de > MERGE_MAX_DE00:
                    rejected["color_delta_e_gt_12"] += 1
                    continue
                rgb_p75 = float(np.percentile(diffs,75))
                if rgb_p75 > MERGE_MAX_RGB_P75:
                    rejected["source_edge_p75_gt_30"] += 1
                    continue
                options.append((de,rgb_p75,-len(diffs),target_color))
            if options:
                best = min(options)
                proposals.append((rid,int(colors[rid]),int(best[3])))
            elif neighbors:
                rejected["no_allowed_neighbor"] += 1
            else:
                rejected["isolated_without_neighbor"] += 1
        # Simultaneous application keeps the original connected regions
        # independent of proposal ordering; provenance counts are exact.
        next_image = out.copy()
        changed_pixels = 0
        for rid,old_color,new_color in proposals:
            region_mask = reg==rid
            changed_pixels += int(region_mask.sum())
            next_image[region_mask] = new_color
        runs.append({
            "pass": pass_id+1,
            "small_regions_examined": int((areas <= MERGE_MAX_AREA).sum()),
            "regions_reassigned": len(proposals),
            "pixels_reassigned": changed_pixels,
            "rejected_neighbor_checks": dict(rejected),
        })
        out = next_image
        if not proposals:
            break
    return out, runs


def render(indexes, colors):
    if np.any(indexes < 0) or np.any(indexes >= len(colors)):
        raise ValueError("BLOCKED_RENDER invalid color index")
    return np.asarray(colors, np.uint8)[indexes]


def metrics(rgb: np.ndarray, indexes: np.ndarray,
            src_rgb: np.ndarray, colors: np.ndarray, source_edge: np.ndarray):
    rendered = render(indexes,colors)
    rgb_mae = float(np.abs(rendered.astype(np.float64) -
                            src_rgb.astype(np.float64)).mean())
    delta = delta_e_ciede2000(
        rgb_to_lab(src_rgb.astype(np.float64)),
        rgb_to_lab(rendered.astype(np.float64)))
    region,owners,areas = component_graph(indexes,len(colors))
    # Label discontinuity on all 4-neighbor horizontal/vertical edges.
    boundary = np.zeros(indexes.shape,np.uint8)
    xx=indexes[:,:-1]!=indexes[:,1:]
    yy=indexes[:-1,:]!=indexes[1:,:]
    boundary[:,:-1] |= xx.astype(np.uint8)
    boundary[:,1:] |= xx.astype(np.uint8)
    boundary[:-1,:] |= yy.astype(np.uint8)
    boundary[1:,:] |= yy.astype(np.uint8)
    # Edge adherence with a frozen 1-logical-pixel Chebyshev tolerance.
    near = cv2.dilate(boundary,np.ones((3,3),np.uint8))>0
    near_src = cv2.dilate(source_edge.astype(np.uint8),
                          np.ones((3,3),np.uint8))>0
    contours=sum(len(cv2.findContours(
        (indexes==color).astype(np.uint8),cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE)[0]) for color in np.unique(indexes))
    tiny = areas<=4
    return {
        "used_colors": int(len(np.unique(indexes))),
        "connected_regions_8":len(owners),
        "components_size_1_to_4":int(np.count_nonzero(tiny)),
        "pixels_in_components_1_to_4":int(areas[tiny].sum()),
        "component_area_median":float(np.median(areas)),
        "component_area_p95":float(np.percentile(areas,95)),
        "boundary_contours_including_holes":contours,
        "palette_boundary_pixels":int(np.count_nonzero(boundary)),
        "source_canny_edge_pixels":int(source_edge.sum()),
        "source_canny_edge_recall_within_1px":float(
            np.count_nonzero(source_edge & near)/max(1,int(source_edge.sum()))),
        "palette_boundary_pixels_outside_1px_source_edge":int(
            np.count_nonzero((boundary>0)&~near_src)),
        "RGB_MAE":rgb_mae,
        "mean_delta_E00":float(delta.mean()),
        "p95_delta_E00":float(np.percentile(delta,95)),
        "max_delta_E00":float(delta.max()),
    }


def make_comparison(original: np.ndarray, result: dict, output: Path):
    panels=[("Original",original)]
    panels.extend((k,result[k]["rgb"]) for k in ("A","B","C","D"))
    for filename,face in (("comparison-full.png",False),
                          ("comparison-faces.png",True)):
        h = FACE_HEIGHT if face else 240
        scale=3
        pad=14
        header=40
        w=150*scale
        tile_h=h*scale
        sheet=Image.new("RGB",(len(panels)*w+(len(panels)+1)*pad,
                               tile_h+header+pad*2),(235,238,243))
        draw=ImageDraw.Draw(sheet)
        for i,(title,img) in enumerate(panels):
            ox=pad+i*(w+pad)
            draw.text((ox+3,12),title,fill=(20,28,44))
            crop=Image.fromarray(img[:h],mode="RGB").resize(
                (w,tile_h),Image.Resampling.NEAREST)
            sheet.paste(crop,(ox,header))
        sheet.save(output/filename)


def run(source:Path,palette_file:Path,output:Path):
    if output.exists():
        raise ValueError("BLOCKED_EVIDENCE_OVERWRITE output already exists")
    roi = load_original(source)
    palette,palette_sha = load_game_palette(palette_file)
    src = np.asarray(roi,dtype=np.uint8)
    game_rgb=np.asarray([p["rgb"] for p in palette],dtype=np.uint8)
    a_indexes,a_rgb=baseline_a(roi)
    b_indexes=nearest_game32(roi,palette)
    c_indexes,slic_details=slic_game32(roi,palette)
    d_indexes,merge_details=merge_small_regions(c_indexes,src,palette)
    all_cases = {
        "A":(a_indexes,a_rgb,"MEDIANCUT8_source_ROI_no_dither"),
        "B":(b_indexes,game_rgb,"fixed_GAME32_CIEDE2000_no_dither"),
        "C":(c_indexes,game_rgb,"fixed_GAME32_SLIC350_CIEDE2000"),
        "D":(d_indexes,game_rgb,"fixed_GAME32_SLIC350_edge_guarded_merge"),
    }
    for label,(indexes,colors,_) in all_cases.items():
        if indexes.shape!=(240,150) or np.any(indexes<0) or np.any(indexes>=len(colors)):
            raise ValueError("BLOCKED_INDEX case "+label)
        if label!="A" and not np.all(np.isin(
                np.unique(render(indexes,colors).reshape(-1,3),axis=0).view(
                    "V3"),game_rgb.view("V3"))):
            raise ValueError("BLOCKED_GAME32 game RGB membership")
    edges=cv2.Canny(cv2.cvtColor(src,cv2.COLOR_RGB2GRAY),
                    CANNY_LOW,CANNY_HIGH)>0
    output.mkdir(parents=True)
    roi.save(output/"original-roi.png")
    data,visuals={},{}
    for name,(indexes,colors,method) in all_cases.items():
        image = render(indexes,colors)
        Image.fromarray(image,mode="RGB").save(output/(name+"-palette.png"))
        Image.fromarray(image[:FACE_HEIGHT],mode="RGB").resize(
            (600,500),Image.Resampling.NEAREST).save(
                output/(name+"-faces.png"))
        np.savez_compressed(output/(name+"-index-map.npz"),
                            index_map=indexes.astype(np.int16),
                            palette_rgb=colors)
        data[name] = {
            "method":method,
            "palette_rgb":[p.tolist() for p in colors],
            "metrics":metrics(image,indexes,src,colors,edges),
        }
        visuals[name]={"rgb":image}
    make_comparison(src,visuals,output)
    hashes={p.name:sha(p) for p in output.iterdir() if p.is_file()}
    report={
        "experiment":EXP,
        "source_sha256":SOURCE_SHA,
        "game32_palette_file":str(palette_file.relative_to(BASE)),
        "game32_palette_sha256":palette_sha,
        "game32_palette_color_count":32,
        "game32_palette_contains_true_black":any(
            p["hex"]=="#000000" for p in palette),
        "game32_palette_contains_white":any(
            p["hex"]=="#FFFFFF" for p in palette),
        "ROI_hw":[240,150],
        "methods":data,
        "SLIC_parameters":{"n_segments":SLIC_N_SEGMENTS,
                           "compactness":SLIC_COMPACTNESS,
                           "sigma":SLIC_SIGMA,
                           "enforce_connectivity":True},
        "SLIC_result":slic_details,
        "D_merge_parameters":{"passes":MERGE_MAX_PASSES,
            "max_component_area":MERGE_MAX_AREA,
            "max_palette_delta_e00":MERGE_MAX_DE00,
            "max_original_border_RGB_p75":MERGE_MAX_RGB_P75},
        "D_merge_diagnostics":merge_details,
        "source_edges":{"Canny_thresholds":[CANNY_LOW,CANNY_HIGH],
                        "boundary_adherence_radius_px":1},
        "whole_picture_Egret_E3":"NOT_RUN",
        "game_E4":"NOT_RUN",
        "independent_E5":"NOT_RUN",
        "exact_CHALK":None,
        "quality_accepted":False,
        "production_accepted":False,
        "report_linked_SHA256":hashes,
    }
    (output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({"experiment":EXP,"source_sha256":SOURCE_SHA,
        "case_metrics":{k:v["metrics"] for k,v in data.items()},
        "SLIC_result":slic_details,
        "D_merge_diagnostics":merge_details,
        "native_E3":"NOT_RUN"},ensure_ascii=False))
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--palette",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    run(a.source,a.palette,a.output)
