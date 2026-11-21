#!/usr/bin/env python3
"""RAG1 original-only DEV visual review and frozen numerical research report.

NO historic maps, strokes, user annotations or blind inputs. No game stroke
execution is claimed. S4 region/color maps are not a native Egret painting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

import engine001_bpred_s4r1_generic_source_maps as original_maps
import engine001_bpred_s4r1_rag1_region_color as rag1
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_module

SOURCES = (
    "testImages/wV6VeZI9S1Y.png",
    "data/generated_autodraw_plan/images_31_first/Sanrio_Characters_Hello_Kitty_Image026.webp",
    "data/generated_autodraw_plan/images_31_first/EZAL3k9ddfs.jpg",
    "data/generated_autodraw_plan/images_31_first/images (1).png",
)
E0_FILE = "ENGINE001_BPRED001_S4R1_REGION_COLOR_RAG1_PREREG_2026-11-22.md"
E0_GIT_BLOB = "97692d0c20bdfabfc81016cbbc34cd7d84af4cbe"
PINNED_ENGINE_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def colored_regions(region_map: np.ndarray, alpha: np.ndarray) -> Image.Image:
    r = region_map.astype(np.uint32)
    colored = np.zeros((*r.shape, 4), np.uint8)
    valid = r > 0
    colored[valid, 0] = (r[valid] * 73 + 49) % 230 + 14
    colored[valid, 1] = (r[valid] * 157 + 67) % 230 + 14
    colored[valid, 2] = (r[valid] * 191 + 89) % 230 + 14
    colored[:, :, 3] = alpha
    return Image.fromarray(colored, mode="RGBA")


def save_review(paths: list[Path], output: Path) -> None:
    images = [Image.open(p).convert("RGB") for p in paths]
    cell_w, cell_h = 350, 420
    canvas = Image.new("RGB", (cell_w * 4, cell_h), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    headers = ("Original RGB", "Original pixel-nearest128", "New region IDs", "New RAG1 game128 colors")
    for i, (img, title) in enumerate(zip(images, headers)):
        draw.text((i * cell_w + 9, 6), title, fill=(10, 10, 10))
        img.thumbnail((cell_w - 16, cell_h - 40), Image.Resampling.LANCZOS)
        canvas.paste(img, (i * cell_w + (cell_w - img.width) // 2, 30))
    canvas.save(output)


def one_original(root: Path, source_rel: str, game: np.ndarray,
                 out: Path, index: int) -> dict:
    source_file = root / source_rel
    raw = source_file.read_bytes()
    origin = original_maps.decode_original(raw)
    rgba = origin["rgba"]
    folder = out / f"{index:02d}_{Path(source_rel).stem}"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_file, folder / ("original" + source_file.suffix))
    t0 = time.perf_counter()
    result = rag1.build_rag1(rgba, game)
    seconds = time.perf_counter() - t0
    metrics = rag1.evaluate_rag1(rgba, game, result)
    baseline = rgba.copy()
    valid = baseline[:, :, 3] == 255
    baseline[valid, :3] = game[result["baseline_index"][valid]]
    images = (
        Image.fromarray(rgba).convert("RGBA"),
        Image.fromarray(baseline).convert("RGBA"),
        colored_regions(result["region_ids"], rgba[:, :, 3]),
        Image.fromarray(result["preview_rgba"]).convert("RGBA"),
    )
    names = ("01_ORIGINAL.png", "02_ORIGINAL_NEAREST128_BASELINE.png",
             "03_RAG1_REGION_IDS.png", "04_RAG1_GAME128_COLORS.png")
    for name, image in zip(names, images):
        image.save(folder / name)
    edge = np.zeros((*rgba.shape[:2], 4), np.uint8)
    edge[:, :, 3] = rgba[:, :, 3]
    edge[result["source_strong_edge"], :3] = (255, 50, 40)
    Image.fromarray(edge).save(folder / "05_ORIGINAL_STRONG_EDGES.png")
    save_review([folder / x for x in names], folder / "00_REVIEW_4_PANELS.png")
    before, after = metrics["baseline"], metrics["candidate"]
    reduction = (100.0 * (before["singletons"] - after["singletons"]) /
                 before["singletons"]) if before["singletons"] else None
    ratio = (metrics["candidate_rgb_mae"] / metrics["baseline_rgb_mae"]
             if metrics["baseline_rgb_mae"] > 1e-9 else None)
    screening = bool(
        reduction is not None and reduction >= 15.0
        and ratio is not None and ratio <= 1.15)
    manifest = {
        "experiment": rag1.VERSION, "e0_filename": E0_FILE,
        "e0_git_blob_sha1": E0_GIT_BLOB,
        "source_path": source_rel, "original_sha256": sha256(raw),
        "original_git_blob_sha1": origin["git_blob_sha1"],
        "original_wh": [origin["width"], origin["height"]],
        "original_mode": origin["original_mode"],
        "original_exif_orientation": origin["exif_orientation"],
        "game128_sha256": sha256(game.tobytes()),
        "source_only_not_native": True,
        "old_artistic_input": False,
        "processing_seconds": round(seconds, 3),
        "metrics": metrics,
        "singleton_reduction_percent": reduction,
        "candidate_to_baseline_rgb_mae": ratio,
        "numeric_screen_15_percent": screening,
        "semantic_detail_verdict": "UNKNOWN_PENDING_VISUAL_REVIEW",
        "stroke_admission": result["stroke_admission"],
        "output_files_sha256": {},
    }
    for p in sorted(folder.iterdir()):
        if p.is_file():
            manifest["output_files_sha256"][p.name] = sha256(p.read_bytes())
    (folder / "manifest.json").write_text(json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    game, palette_prov = palette_module.read_engine_palette(
        root / "gameEngine/main.min_653f95bc.js")
    if palette_prov["engine_git_blob_sha1"] != PINNED_ENGINE_BLOB:
        raise RuntimeError("BLOCKED_RAG1_UNPINNED_ENGINE")
    if not np.array_equal(game[6], (255, 255, 255)):
        raise RuntimeError("BLOCKED_RAG1_GAME128_PALETTE")
    reports = [one_original(root, s, game, out, i)
               for i, s in enumerate(SOURCES)]
    numeric_pass = sum(x["numeric_screen_15_percent"] for x in reports)
    summary = {
        "experiment": rag1.VERSION, "e0_git_blob_sha1": E0_GIT_BLOB,
        "source_count": len(SOURCES), "numeric_sources_pass": numeric_pass,
        "numeric_screen": "MEETS_PRESPEC_NUMERIC_ONLY"
        if numeric_pass >= 2 else "FAIL_PRESPEC_NUMERIC_SCREEN",
        "visual_quality": "NOT_VALIDATED",
        "independent_s4_gate": "BLOCKED",
        "native_egret": "NOT_RUN_SOURCE_ONLY",
        "game_chalk": "NOT_RUN",
        "all_fresh": True,
        "sources": [x["source_path"] for x in reports],
    }
    (out / "00_RAG1_RESEARCH_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
