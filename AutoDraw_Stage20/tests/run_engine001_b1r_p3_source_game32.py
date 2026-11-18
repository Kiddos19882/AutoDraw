#!/usr/bin/env python3
"""B1-R-P3 original-only game swatch screening — no legacy G32 map or V44.

No native Egret/brush execution; unresolved guarded pixels are NOT drawable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

import cv2
import numpy as np
import scipy
import skimage
from PIL import Image, ImageDraw, ImageFont
from skimage import color

from run_engine001_b1r_p1_fullrgb_edge_aware import (
    FULL_SHAPE, SOURCE_SHA256, LOGICAL_WH, ROIS_FULL,
    check_source, full_features, filter_original, logical_rgb,
)
from run_engine001_b1r_p2_joint_region_outline import (
    digest, delta_metrics, fixed_original_edge_recall,
    slic_labels, source_region_medoids,
)
from run_engine001_b1r_p2b_residual_ink import ink_residual, logical_composite
from run_engine001_b1r_p2c_source_ink_palette import (
    VARIANTS as SOURCE_INK_BUDGETS,
    compress_source_ink, resample_discrete, unique_rgb,
)
from run_engine001_b1r_p2d_background_halo_guard import (
    GUARD_VARIANTS, source_bright_guard, apply_source_bright_guard,
    hair_dark_count,
)

EXPERIMENT = "ENGINE001_B1R_P3_ORIGINAL_SOURCE_32_GAME_SWATCH_V1"
PALETTE_BLOB_SHA1 = "461b5f3725b9b79888ad36e807b3cf4c9e445e98"
MAPPING_METHODS = ("N_NEAREST", "S_GUARDED")
PALETTE_COUNT = 32
WHITE_INDEX = 30
MAX_SOURCE_CHROMA_EXCESS = 12.0
MAX_HUE_DISTANCE = 45.0
MIN_HUE_CHROMA = 12.0
MAX_SOURCE_DELTA_E = 20.0
MAX_TARGET_DELTA_E = 20.0
MAX_ABSTAIN = 720
LOGICAL_SHAPE = (240, 150, 3)
INPUT_EXCLUDED_ARTIFACTS = (
    "G32 legacy pixel maps", "P4c1", "V44-B410", "M1",
    "P2B/P2C/P2D frozen PNG/NPY/JSON",
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_game_swatches(path: Path):
    data = path.read_bytes()
    if git_blob_sha(data) != PALETTE_BLOB_SHA1:
        raise ValueError("BLOCKED_P3_GAME_SWATCH_GIT_BLOB")
    obj = json.loads(data)
    if not isinstance(obj.get("colors"), list) or len(obj["colors"]) != PALETTE_COUNT:
        raise ValueError("BLOCKED_P3_GAME_PALETTE_SIZE")
    colors = []
    for e in obj["colors"]:
        if not isinstance(e, dict) or not isinstance(e.get("rgb"), list):
            raise ValueError("BLOCKED_P3_GAME_SWATCH_ENTRY")
        v = e["rgb"]
        if len(v) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in v):
            raise ValueError("BLOCKED_P3_GAME_SWATCH_VALUE")
        if e.get("hex", "").upper() != "#" + "".join(f"{c:02X}" for c in v):
            raise ValueError("BLOCKED_P3_GAME_SWATCH_RGB_HEX")
        colors.append(v)
    pal = np.asarray(colors, dtype=np.uint8)
    if unique_rgb(pal) != PALETTE_COUNT or not np.array_equal(
            pal[WHITE_INDEX], [255, 255, 255]):
        raise ValueError("BLOCKED_P3_GAME_SWATCH_DUPLICATE_OR_WHITE")
    return pal, obj["colors"], hashlib.sha256(data).hexdigest()


def rgb_lab(rgb: np.ndarray) -> np.ndarray:
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[-1] != 3 or a.dtype != np.uint8:
        raise ValueError("BLOCKED_P3_RGB_INPUT")
    return color.rgb2lab(a.astype(np.float64) / 255.0)


def game32_distance_tables(target: np.ndarray, source: np.ndarray,
                           swatches: np.ndarray):
    if (target.shape != source.shape or target.dtype != np.uint8 or
            source.dtype != np.uint8 or target.ndim != 3 or
            target.shape[-1] != 3 or swatches.shape != (32, 3) or
            swatches.dtype != np.uint8):
        raise ValueError("BLOCKED_P3_GAME32_DIMENSIONS")
    t_lab, s_lab = rgb_lab(target), rgb_lab(source)
    p_lab = rgb_lab(swatches.reshape(1, 32, 3))[0]
    target_de = np.stack([
        color.deltaE_ciede2000(t_lab, c[None, None, :])
        for c in p_lab], axis=-1)
    source_de = np.stack([
        color.deltaE_ciede2000(s_lab, c[None, None, :])
        for c in p_lab], axis=-1)
    source_chroma = np.linalg.norm(s_lab[..., 1:], axis=2)
    palette_chroma = np.linalg.norm(p_lab[:, 1:], axis=1)
    palette_hue = np.degrees(np.arctan2(p_lab[:, 2], p_lab[:, 1]))
    source_hue = np.degrees(np.arctan2(s_lab[..., 2], s_lab[..., 1]))
    hue_delta = np.abs(((source_hue[..., None] - palette_hue + 180) % 360) - 180)
    return {
        "target_de": target_de, "source_de": source_de,
        "source_chroma": source_chroma, "palette_chroma": palette_chroma,
        "hue_delta": hue_delta,
    }


def assign_game32(target: np.ndarray, source: np.ndarray,
                  swatches: np.ndarray, method: str):
    if method not in MAPPING_METHODS:
        raise ValueError("BLOCKED_P3_UNREGISTERED_METHOD")
    d = game32_distance_tables(target, source, swatches)
    if not np.array_equal(swatches[WHITE_INDEX], [255, 255, 255]):
        raise ValueError("BLOCKED_P3_MISSING_GAME_WHITE")
    near_white = np.min(source, axis=2) >= 245
    if method == "N_NEAREST":
        allowed = np.ones(d["target_de"].shape, dtype=bool)
    else:
        chroma_ok = (d["palette_chroma"][None, None, :] <=
                     d["source_chroma"][..., None] + MAX_SOURCE_CHROMA_EXCESS)
        hue_relevant = (
            (d["source_chroma"][..., None] >= MIN_HUE_CHROMA) &
            (d["palette_chroma"][None, None, :] >= MIN_HUE_CHROMA))
        hue_ok = (~hue_relevant) | (d["hue_delta"] <= MAX_HUE_DISTANCE)
        original_ok = d["source_de"] <= MAX_SOURCE_DELTA_E
        target_ok = d["target_de"] <= MAX_TARGET_DELTA_E
        allowed = chroma_ok & hue_ok & original_ok & target_ok
    # Independent of P2D source mapping and any frozen legacy assignment:
    allowed[near_white] = False
    allowed[near_white, WHITE_INDEX] = True
    scores = np.where(allowed, d["target_de"], np.inf)
    valid = np.any(allowed, axis=2)
    indexes = np.argmin(scores, axis=2).astype(np.int16)
    indexes[~valid] = -1
    if method == "N_NEAREST" and np.any(indexes < 0):
        raise AssertionError("BLOCKED_P3_NEAREST_UNRESOLVED")
    # All real assigned pixels are exact game RGB values; abstentions
    # are transparent, not a silently invented 33rd swatch.
    rgba = np.zeros((*target.shape[:2], 4), dtype=np.uint8)
    rgba[valid, :3] = swatches[indexes[valid]]
    rgba[valid, 3] = 255
    if not np.array_equal(rgba[valid, :3], swatches[indexes[valid]]):
        raise AssertionError("BLOCKED_P3_SOURCE_INDEX_RGB")
    preview = np.full_like(target, 255)
    preview[valid] = swatches[indexes[valid]]
    counters = {
        "rejected_chroma_pixels": 0,
        "rejected_hue_pixels": 0,
        "rejected_original_deltaE_pixels": 0,
        "rejected_target_deltaE_pixels": 0,
    }
    if method == "S_GUARDED":
        counters.update({
            "rejected_chroma_pixels": int(np.count_nonzero(
                (d["palette_chroma"][None,None,:] >
                 d["source_chroma"][...,None]+MAX_SOURCE_CHROMA_EXCESS).any(axis=2))),
            "rejected_hue_pixels": int(np.count_nonzero((
                (d["source_chroma"][...,None]>=MIN_HUE_CHROMA)&
                (d["palette_chroma"][None,None,:]>=MIN_HUE_CHROMA)&
                (d["hue_delta"]>MAX_HUE_DISTANCE)).any(axis=2))),
            "rejected_original_deltaE_pixels": int(np.count_nonzero(
                (d["source_de"]>MAX_SOURCE_DELTA_E).any(axis=2))),
            "rejected_target_deltaE_pixels": int(np.count_nonzero(
                (d["target_de"]>MAX_TARGET_DELTA_E).any(axis=2))),
        })
    return indexes, rgba, preview, {
        "unresolved_pixels": int(np.count_nonzero(~valid)),
        "assigned_pixels": int(np.count_nonzero(valid)),
        "game_indices_used": [int(i) for i in np.unique(indexes[valid])],
        "assigned_color_RGB_unique": (
            unique_rgb(swatches[indexes[valid]]) if np.any(valid) else 0
        ),
        "near_white_forced_game_white": int(np.count_nonzero(near_white)),
        "allowance_count_per_pixel_mean": float(allowed.sum(axis=2).mean()),
        "unresolved_is_not_drawable": True,
        "game_swatch_compliant": True,
        "reject_reason_counts_diagnostic_overlapping": counters,
    }


def palette_quality(original_logical: np.ndarray, target_logical: np.ndarray,
                    indexes: np.ndarray, swatches: np.ndarray,
                    preview: np.ndarray, mapping: str, assigned: dict):
    m, original_lab, out_lab = delta_metrics(original_logical, preview)
    source_chroma = np.linalg.norm(original_lab[..., 1:], axis=2)
    out_chroma = np.linalg.norm(out_lab[..., 1:], axis=2)
    extra = int(np.count_nonzero(out_chroma > source_chroma + MAX_SOURCE_CHROMA_EXCESS))
    edge = fixed_original_edge_recall(original_logical, preview)
    halo = hair_dark_count(original_logical, preview)
    valid = indexes >= 0
    palette_valid = bool(np.all(indexes[valid] < PALETTE_COUNT))
    exact_rgb = bool(np.array_equal(preview[valid], swatches[indexes[valid]]))
    all_assigned = assigned["assigned_pixels"] == 36000
    gates = {
        "all_resolved_indices_game_palette": palette_valid and exact_rgb,
        "new_palette_swatch_count_at_most32": len(assigned["game_indices_used"]) <=32,
        "near_white_source_not_false_dark_at_most20":
            halo["false_dark_logical_pixels"] <=20,
        "global_mean_deltaE00_at_most10": m["mean_deltaE00"] <=10.0,
        "global_p95_deltaE00_at_most30": m["p95_deltaE00"] <=30.0,
        "female_face_eye_deltaE00_at_most12":
            m["female_face_eyes_mean_deltaE00"]<=12.0,
        "male_face_eye_deltaE00_at_most12":
            m["male_face_eyes_mean_deltaE00"]<=12.0,
        "hands_deltaE00_at_most12": m["hands_mean_deltaE00"]<=12.0,
        "original_fixed_sobel90_edge_recall_at_least0p65": edge>=.65,
        "chroma_excess_at_most3600": extra<=3600,
        "unresolved_policy": (
            all_assigned if mapping=="N_NEAREST" else
            assigned["unresolved_pixels"] <=MAX_ABSTAIN
        ),
    }
    return {
        "source_deltaE00_vs_original_LANCZOS": m,
        "original_sobel90_1px_edge_recall": edge,
        "source_chroma_excess_pixels_plus12": extra,
        "bright_hair_false_dark_logical": halo,
        "metrics_on_white_background_for_unresolved_are_NOT_drawable": mapping=="S_GUARDED",
        "gates": gates,
        "status": ("SOURCE_SCREEN_PASS_VISUAL_PENDING" if all(gates.values())
                   else "SOURCE_GATE_FAIL"),
    }


def render_panel(named: list[tuple[str, np.ndarray]], path: Path,
                 crop: tuple[int, int, int, int] | None = None,
                 scale: int=3):
    swatches=[]
    for name, rgb in named:
        if rgb.shape != LOGICAL_SHAPE:
            raise ValueError("BLOCKED_P3_REVIEW_LOGICAL_SHAPE")
        if crop:
            x0,y0,x1,y1=crop
            rgb=rgb[y0:y1,x0:x1]
        swatches.append((name,rgb))
    widths=[rgb.shape[1]*scale for _,rgb in swatches]
    hh=max(rgb.shape[0]*scale for _,rgb in swatches)+32
    canvas=Image.new("RGB",(sum(widths),hh),(255,255,255))
    d=ImageDraw.Draw(canvas)
    try:
        font=ImageFont.truetype("DejaVuSans.ttf",15)
    except OSError:
        font=ImageFont.load_default()
    x=0
    for (name,rgb),w in zip(swatches,widths):
        d.text((x+4,8),name,fill=(0,0,0),font=font)
        canvas.paste(Image.fromarray(rgb).resize(
            (w,rgb.shape[0]*scale),Image.Resampling.NEAREST),(x,32))
        x+=w
    canvas.save(path)


def run(source: Path, palette_file: Path, destination: Path):
    if destination.exists():
        raise ValueError("BLOCKED_P3_OUTPUT_EXISTS")
    original=check_source(source)
    game, entries, palette_sha256=load_game_swatches(palette_file)
    features=full_features(original)
    source_filtered=filter_original(original,"A_SOFT",features["protected"])
    labels=slic_labels(source_filtered,"J_FINE")
    flat, region_ledger=source_region_medoids(original,labels)
    ink_mask, _, detail_full, detail_info=ink_residual(
        original,flat,features,"K_DETAIL")
    original_logical=logical_rgb(original)
    guards={}
    for method in GUARD_VARIANTS:
        guards[method],_=source_bright_guard(original,flat,ink_mask,method)
    destination.mkdir(parents=True)
    Image.fromarray(original_logical).save(destination/"ORIGINAL_RGB_LOGICAL.png")
    Image.fromarray(game.reshape(1,32,3).repeat(34,axis=0)
                    .repeat(16,axis=1)).save(destination/"ACTUAL_GAME_SWATCHES32.png")
    palettes={}
    for c in SOURCE_INK_BUDGETS:
        source_full,_,_=compress_source_ink(original,flat,ink_mask,c)
        for guard in GUARD_VARIANTS:
            full=apply_source_bright_guard(original,source_full,ink_mask,guards[guard])
            if unique_rgb(full)!=(347 if c=="C_096" else 443):
                raise ValueError("BLOCKED_P3_FROZEN_SOURCE_FULL_RGB_COUNT")
            source_nearest=resample_discrete(full)
            if hair_dark_count(original_logical,source_nearest)["false_dark_logical_pixels"]!=1:
                raise ValueError("BLOCKED_P3_FROZEN_P2D_HAIR_ROI")
            if int(np.count_nonzero(guards[guard]))!=(
                56 if guard=="D_BORDER" else 243):
                raise ValueError("BLOCKED_P3_FROZEN_P2D_SOURCE_GUARD")
            key=c+"_"+guard
            palettes[key]=source_nearest
            Image.fromarray(source_nearest).save(destination/(key+"_P2D_ACCEPTED_SOURCE_NEAREST.png"))
            Image.fromarray(logical_composite(full)).save(
                destination/(key+"_P2D_ACCEPTED_SOURCE_LANCZOS.png"))
    reports={}
    for key,target in palettes.items():
        reports[key]={}
        variants=[("ORIGINAL",original_logical),("P2D SOURCE",target)]
        for method in MAPPING_METHODS:
            indices,rgba,preview,summary=assign_game32(
                target,original_logical,game,method)
            quality=palette_quality(
                original_logical,target,indices,game,preview,method,summary)
            reports[key][method]={**summary,**quality}
            stem=key+"_"+method
            Image.fromarray(np.where(indices<0,255,indices).astype(np.uint8)).save(
                destination/(stem+"_GAME_INDEX_OR_UNRESOLVED255.png"))
            Image.fromarray(rgba).save(destination/(stem+"_ACTUAL_GAME_COLOR_RGBA.png"))
            Image.fromarray(preview).save(destination/(
                stem+"_GAME_PALETTE_PREVIEW_WHITE_UNRESOLVED.png"))
            Image.fromarray((indices<0).astype(np.uint8)*255).save(
                destination/(stem+"_UNRESOLVED_DIAGNOSTIC_MASK.png"))
            variants.append((method+(" (NOT DRAWABLE)" if summary["unresolved_pixels"] else ""),preview))
        render_panel(variants, destination/("REVIEW_"+key+"_FOUR_PANEL.png"))
        for roi in ("female_face_eyes","male_face_eyes","hands"):
            x0,y0,x1,y1=ROIS_FULL[roi]
            crop=(round(x0*.75),round(y0*.75),round(x1*.75),round(y1*.75))
            render_panel(variants,destination/("REVIEW_"+key+"_ROI_"+roi+".png"),
                         crop=crop,scale=5)
    (destination/"README_REVIEW_RU.txt").write_text(
        "ENGINE-001 B1-R-P3 — original RGB -> 32 original game swatches.\n"
        "В этом ZIP ЧЕТЫРЕ ранее визуально принятых source RGB P2D варианта\n"
        "и по ДВА pixelwise nearest32/guarded source-support варианта.\n"
        "Смотрите REVIEW_C_096_D_BORDER_FOUR_PANEL.png и аналогичные.\n"
        "N_NEAREST: реальная игровая палитра, pixelwise без старых карт.\n"
        "S_GUARDED: пиксели с недостатком исходной поддержки ПУСТЫЕ.\n"
        "Белый фон таких пикселей — НЕ игровая краска; если unresolved>0,\n"
        "S_GUARDED НЕ ГОТОВ К ОТРИСОВКЕ. Смотрите UNRESOLVED_MASK.\n"
        "NATIVE EGTRET, круглая кисть, CHALK E4/E5 НЕ ПРОВЕРЯЛИСЬ.\n"
        "Все показатели SOURCE, ни один не означает визуальную оценку пользователя.\n",
        encoding="utf8")
    hashes={
        p.name:digest(p.read_bytes()) for p in sorted(destination.iterdir())
        if p.is_file()
    }
    report={
        "experiment":EXPERIMENT,
        "original_png_sha256":SOURCE_SHA256,
        "actual_game_palette_git_blob_sha1":PALETTE_BLOB_SHA1,
        "actual_game_palette_sha256":palette_sha256,
        "game_palette_swatches":entries,
        "exact_game_palette32_unique_RGB":unique_rgb(game),
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "original_only_candidate_input":True,
        "old_G32_mapping_used":False,
        "V44_outline_used":False,
        "old_M1_mask_used":False,
        "frozen_P2B_P2C_P2D_artifact_consumed":False,
        "original_only_region_count":len(region_ledger),
        "original_source_K_DETAIL_ink_pixels":int(ink_mask.sum()),
        "original_source_ink_summary":detail_info,
        "P2D_guards_source_pixels":{k:int(v.sum()) for k,v in guards.items()},
        "source_original_visual_acceptance_P2D":"BOTH_GUARDS_ACCEPTED_FOUR_COMBINATIONS",
        "source_screen_results":reports,
        "manual_game32_visual_approval":"PENDING",
        "actual_native_Egret_brush":"NOT_RUN",
        "game_E4":"NOT_RUN",
        "independent_E5":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "production_promotion":False,
        "all_output_files_sha256":hashes,
        "versions":{
            "python":platform.python_version(),"numpy":np.__version__,
            "scipy":scipy.__version__,"scikit-image":skimage.__version__,
            "OpenCV":cv2.__version__,"Pillow":Image.__version__,
        },
    }
    (destination/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf8")
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--game-palette",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    report=run(a.source,a.game_palette,a.output)
    for name,m in report["source_screen_results"].items():
        for method,v in m.items():
            print(name,method,v["status"],
                  "assigned_game32",len(v["game_indices_used"]),
                  "UNRESOLVED",v["unresolved_pixels"],
                  "mean_original_DE00",round(v["source_deltaE00_vs_original_LANCZOS"]["mean_deltaE00"],4),
                  "p95",round(v["source_deltaE00_vs_original_LANCZOS"]["p95_deltaE00"],4),
                  "excess_chroma",v["source_chroma_excess_pixels_plus12"],
                  "failed",[k for k,pass_ in v["gates"].items() if not pass_])
    print("NATIVE_EGRET_GAME_E4_E5_EXACT_CHALK_NOT_RUN")
