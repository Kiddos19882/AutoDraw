#!/usr/bin/env python3
"""RAG2 four original DEV source-only visual review; no prior artwork as input."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np
from PIL import Image, ImageDraw

import engine001_bpred_s4r1_generic_source_maps as original_maps
import engine001_bpred_s4r1_rag2_split_guard as rag2
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_module

SOURCES = (
    "testImages/wV6VeZI9S1Y.png",
    "data/generated_autodraw_plan/images_31_first/Sanrio_Characters_Hello_Kitty_Image026.webp",
    "data/generated_autodraw_plan/images_31_first/EZAL3k9ddfs.jpg",
    "data/generated_autodraw_plan/images_31_first/images (1).png",
)
E0_FILE = "ENGINE001_BPRED001_S4R1_REGION_COLOR_RAG2_SPLIT_GUARD_PREREG_2026-11-22.md"
E0_BLOB = "c5e6564829b4ed641b31cba83da4a66c79caa5dd"
ENGINE_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def preview_regions(regions: np.ndarray, alpha: np.ndarray) -> Image.Image:
    rid = regions.astype(np.uint32)
    pixels = np.zeros((*rid.shape, 4), np.uint8)
    nonzero = rid != 0
    pixels[nonzero, 0] = (rid[nonzero] * 73 + 49) % 230 + 14
    pixels[nonzero, 1] = (rid[nonzero] * 157 + 67) % 230 + 14
    pixels[nonzero, 2] = (rid[nonzero] * 191 + 89) % 230 + 14
    pixels[:, :, 3] = alpha
    return Image.fromarray(pixels)


def atlas(images: list[Path], path: Path) -> None:
    head = ["Original full RGB", "New original nearest128 reference",
            "New SLIC-internal split IDs", "New RAG2 guarded game128 colors"]
    screen = Image.new("RGB", (350 * 4, 420), (245, 245, 245))
    draw = ImageDraw.Draw(screen)
    for i, (f, label) in enumerate(zip(images, head)):
        draw.text((i * 350 + 7, 6), label, fill=(30, 30, 30))
        im = Image.open(f).convert("RGB")
        im.thumbnail((334, 380), Image.Resampling.LANCZOS)
        screen.paste(im, (350 * i + (350 - im.width) // 2, 30))
    screen.save(path)


def process(root: Path, path: str, colors: np.ndarray, out: Path, index: int):
    source_path = root / path
    raw = source_path.read_bytes()
    src = original_maps.decode_original(raw)
    rgb = src["rgba"]
    directory = out / ("%02d_%s" % (index, source_path.stem))
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, directory / ("original" + source_path.suffix))
    start = time.perf_counter()
    data = rag2.build_rag2(rgb, colors)
    elapsed = time.perf_counter() - start
    summary = rag2.evaluate_rag2(rgb, colors, data)
    opaque = rgb[:, :, 3] == 255
    baseline = rgb.copy()
    baseline[opaque, :3] = colors[data["baseline_index"][opaque]]
    fns = [
        "01_ORIGINAL_RGB.png", "02_FRESH_NEAREST128.png",
        "03_RAG2_REGION_IDS.png", "04_RAG2_GAME128_COLORS.png"
    ]
    imgs = [
        Image.fromarray(rgb), Image.fromarray(baseline),
        preview_regions(data["region_ids"], rgb[:, :, 3]),
        Image.fromarray(data["preview_rgba"])
    ]
    for file, im in zip(fns, imgs):
        im.save(directory / file)
    edges = np.zeros(rgb.shape, np.uint8)
    edges[:, :, 3] = rgb[:, :, 3]
    edges[data["source_strong_edge"], :3] = (250, 55, 38)
    Image.fromarray(edges).save(directory / "05_ORIGINAL_STRONG_EDGES.png")
    atlas([directory / x for x in fns], directory / "00_REVIEW_4_PANELS.png")
    baseline_s = summary["baseline"]["singletons"]
    candidate_s = summary["candidate"]["singletons"]
    decrease = (100.0 * (baseline_s - candidate_s) / baseline_s
                if baseline_s else None)
    ratio = (summary["candidate_rgb_mae"] / summary["baseline_rgb_mae"]
             if summary["baseline_rgb_mae"] > 1e-9 else None)
    passed = (decrease is not None and decrease >= 15.0
              and ratio is not None and ratio <= 1.15)
    manifest = {
        "experiment": rag2.VERSION, "protocol": E0_FILE,
        "e0_git_blob_sha1": E0_BLOB, "source": path,
        "source_sha256": digest(raw),
        "source_git_blob_sha1": src["git_blob_sha1"],
        "source_size": [src["width"], src["height"]],
        "original_mode": src["original_mode"],
        "original_exif_orientation": src["exif_orientation"],
        "game128_sha256": digest(colors.tobytes()),
        "elapsed_seconds": round(elapsed, 3),
        "metrics": summary,
        "singleton_reduction_percent": decrease,
        "candidate_to_baseline_rgb_mae_ratio": ratio,
        "numeric_screen": "PASS_NUMERIC_ONLY" if passed else "FAIL_NUMERIC_ONLY",
        "original_only": True, "legacy_artistic_input": False,
        "not_native_egret": True,
        "source_owner_status": data["source_owner_status"],
        "stroke_admission": data["stroke_admission"],
        "visual_quality": "NOT_INDEPENDENTLY_VALIDATED",
        "output_files_sha256": {},
    }
    for file in sorted(directory.iterdir()):
        if file.is_file():
            manifest["output_files_sha256"][file.name] = digest(file.read_bytes())
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    palette, provenance = palette_module.read_engine_palette(
        root / "gameEngine/main.min_653f95bc.js")
    if provenance["engine_git_blob_sha1"] != ENGINE_BLOB:
        raise RuntimeError("BLOCKED_RAG2_UNPINNED_ENGINE")
    if tuple(palette[6]) != (255, 255, 255):
        raise RuntimeError("BLOCKED_RAG2_SWATCH_WHITE_MISMATCH")
    reports = [process(root, filename, palette, output, index)
               for index, filename in enumerate(SOURCES)]
    passed = sum(r["numeric_screen"] == "PASS_NUMERIC_ONLY" for r in reports)
    summary = {
        "experiment": rag2.VERSION,
        "e0_git_blob_sha1": E0_BLOB, "source_count": len(reports),
        "numeric_pass_count": passed,
        "numeric_verdict": "PROMISING_NUMERIC_ONLY" if passed >= 2
                           else "FAIL_FROZEN_NUMERIC_GATE",
        "e2_status": "TECHNICAL_NOT_A_SCIENTIFIC_GATE",
        "native_egret": "NOT_RUN",
        "formal_s4": "BLOCKED", "game_chalk": "NOT_RUN",
        "no_legacy_art": True,
        "source_paths": [r["source"] for r in reports],
    }
    (output / "00_RAG2_SUMMARY.json").write_text(json.dumps(
        summary, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
