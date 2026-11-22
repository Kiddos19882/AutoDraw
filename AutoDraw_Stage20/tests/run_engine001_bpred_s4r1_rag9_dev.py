#!/usr/bin/env python3
"""One frozen RAG9 E0 candidate; four full originals x2, source E2 only.

Recomputes ALL maps from original bytes; never reads RAG1-RAG8 art as an input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np
from PIL import Image, ImageDraw

import engine001_bpred_s4r1_generic_source_maps as original_reader
import engine001_bpred_s4r1_rag9_hard_edge_chroma as rag9
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_reader

SOURCES = (
    "testImages/wV6VeZI9S1Y.png",
    "data/generated_autodraw_plan/images_31_first/Sanrio_Characters_Hello_Kitty_Image026.webp",
    "data/generated_autodraw_plan/images_31_first/EZAL3k9ddfs.jpg",
    "data/generated_autodraw_plan/images_31_first/images (1).png",
)
E0_FILE = "ENGINE001_BPRED001_S4R1_REGION_COLOR_RAG9_HARD_EDGE_CHROMA_PROPAGATION_PREREG_2026-11-22.md"
E0_BLOB = "5bd38c425f599747e3d8319edf20973782e9bb74"
ENGINE_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
MAIN_LIMIT = {SOURCES[0]: 5444, SOURCES[2]: 39894}
PAINTABLE_LIMIT = {SOURCES[0]: 5283, SOURCES[2]: 38682}
RAW_KEYS = (
    "surface_id", "barrier_atom_id", "atom_source_bin",
    "atom_source_owner", "patch_id", "patch_parent_surface_id",
    "patch_source_mode", "patch_color_index", "paintable_id",
    "game_index", "baseline_index", "barrier_h", "barrier_v",
    "source_edge", "unknown", "adjacency",
)


def sha(raw: bytes):
    return hashlib.sha256(raw).hexdigest()


def pseudo_label(labels: np.ndarray, alpha: np.ndarray):
    out = np.zeros((*labels.shape, 4), np.uint8)
    vals = labels.astype(np.uint64)
    mask = vals > 0
    out[mask, 0] = ((vals[mask] * 73 + 49) % 230 + 14).astype(np.uint8)
    out[mask, 1] = ((vals[mask] * 157 + 67) % 230 + 14).astype(np.uint8)
    out[mask, 2] = ((vals[mask] * 191 + 89) % 230 + 14).astype(np.uint8)
    out[:, :, 3] = alpha
    return Image.fromarray(out, "RGBA")


def make_atlas(directory: Path, names: list[str]):
    headers = ("Original RGB", "Hard source edge atoms", "Source chroma mode groups",
               "Geodesic source color regions", "Actual 4-connected paintable",
               "RAG9 genuine game128", "True original strong boundaries",
               "Fresh nearest128 (evaluation only)")
    canvas = Image.new("RGB", (340 * 8, 430), (245, 245, 245))
    pen = ImageDraw.Draw(canvas)
    for i, (filename, header) in enumerate(zip(names, headers)):
        pen.text((340 * i + 5, 5), header, fill=(30, 30, 30))
        with Image.open(directory / filename) as opened:
            picture = opened.convert("RGB")
            picture.thumbnail((328, 387), Image.Resampling.LANCZOS)
        canvas.paste(picture, (340 * i + (340 - picture.width) // 2, 30))
    canvas.save(directory / "00_REVIEW_ATLAS.png")


def run_source(root: Path, source_path: str, palette: np.ndarray,
               output: Path, index: int):
    filename = root / source_path
    raw = filename.read_bytes()
    original = original_reader.decode_original(raw)
    rgba = original["rgba"]
    sub = output / ("%02d_%s" % (index, filename.stem))
    sub.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(filename, sub / ("original" + filename.suffix))
    begin = time.perf_counter()
    result = rag9.build_rag9(rgba, palette)
    first_seconds = time.perf_counter() - begin
    begin = time.perf_counter()
    replay = rag9.build_rag9(rgba, palette)
    replay_seconds = time.perf_counter() - begin
    for key in RAW_KEYS + ("preview_rgba",):
        if not np.array_equal(result[key], replay[key]):
            raise RuntimeError("BLOCKED_RAG9_NONDETERMINISTIC_" + key)
    if result["counts"] != replay["counts"]:
        raise RuntimeError("BLOCKED_RAG9_NONDETERMINISTIC_COUNTS")
    metric = rag9.evaluate_rag9(rgba, palette, result)
    opaque = rgba[:, :, 3] == 255
    fresh_nearest = rgba.copy()
    fresh_nearest[opaque, :3] = palette[result["baseline_index"][opaque]]
    edge = np.zeros_like(rgba)
    edge[..., 3] = rgba[..., 3]
    edge[result["source_edge"], :3] = (250, 50, 35)
    # "source color mode" is diagnostic mode ID, never a palette target input.
    colors_by_mode = np.zeros_like(result["patch_id"], np.int64)
    colors_by_mode[opaque] = result["patch_source_mode"][result["patch_id"][opaque]]
    files = [
        "01_ORIGINAL_RGB.png", "02_HARD_SOURCE_EDGE_ATOMS.png",
        "03_SOURCE_CHROMATIC_MODES.png", "04_FINAL_SOURCE_REGIONS.png",
        "05_ACTUAL_PAINTABLE.png", "06_RAG9_GAME128.png",
        "07_TRUE_ORIGINAL_STRONG_EDGES.png", "08_NEAREST128_BASELINE.png",
    ]
    pictures = [
        Image.fromarray(rgba),
        pseudo_label(result["barrier_atom_id"], rgba[..., 3]),
        pseudo_label(colors_by_mode, rgba[..., 3]),
        pseudo_label(result["patch_id"], rgba[..., 3]),
        pseudo_label(result["paintable_id"], rgba[..., 3]),
        Image.fromarray(result["preview_rgba"]),
        Image.fromarray(edge),
        Image.fromarray(fresh_nearest),
    ]
    for file, picture in zip(files, pictures):
        picture.save(sub / file)
    make_atlas(sub, files)
    np.savez_compressed(sub / "09_RAG9_FULL_SOURCE_LAYERS.npz",
                        **{key: result[key] for key in RAW_KEYS})
    before = metric["baseline"]["singletons"]
    after = metric["candidate"]["singletons"]
    reduction = 100. * (before - after) / before if before else None
    baseline_mae = metric["baseline_rgb_mae"]
    ratio = metric["candidate_rgb_mae"] / baseline_mae if baseline_mae > 1e-12 else None
    numeric = reduction is not None and reduction >= 15.0 and ratio is not None and ratio <= 1.15
    main_count = result["counts"]["main_surfaces"]
    real_paint = result["counts"]["paintable_components"]
    main_pass = main_count < MAIN_LIMIT[source_path] if source_path in MAIN_LIMIT else None
    paint_pass = real_paint < PAINTABLE_LIMIT[source_path] if source_path in PAINTABLE_LIMIT else None
    retained = metric["strong_source_contrast"]["retained_fraction"]
    contrast_pass = retained >= .75 if source_path in MAIN_LIMIT else None
    manifest = {
        "experiment": rag9.VERSION, "protocol": E0_FILE,
        "e0_git_blob_sha1": E0_BLOB,
        "engine_git_blob_sha1": ENGINE_BLOB,
        "source": source_path, "source_sha256": sha(raw),
        "source_git_blob_sha1": original["git_blob_sha1"],
        "source_size_wh": [original["width"], original["height"]],
        "exif_orientation": original["exif_orientation"],
        "original_mode": original["original_mode"],
        "game128_sha256": sha(palette.tobytes()),
        "source_pixel_frame": "full original RGB, NOT calibrated to game",
        "metric": metric, "singleton_reduction_percent": reduction,
        "candidate_to_nearest128_rgb_mae_ratio": ratio,
        "numeric_gate": "PASS" if numeric else "FAIL",
        "main_count": main_count, "main_gate": main_pass,
        "real_paintable_count": real_paint, "paintable_gate": paint_pass,
        "original_strong_edge_contrast": retained, "contrast_gate": contrast_pass,
        "source_to_logical": result["source_to_logical"],
        "original_only": True, "legacy_derived_art_used": False,
        "source_owner_status": result["source_owner_status"],
        "stroke_admission": result["stroke_admission"],
        "two_clean_runs_array_identical": True,
        "native_egret": "NOT_RUN", "formal_bpred_s4": "BLOCKED",
        "visual_review": "PENDING_ARTIFACT_INSPECTION",
        "output_files_sha256": {},
    }
    for item in sorted(sub.iterdir()):
        if item.is_file():
            manifest["output_files_sha256"][item.name] = sha(item.read_bytes())
    (sub / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    summary = {
        "source": source_path, "numeric_screen": manifest["numeric_gate"],
        "main_gate": main_pass, "real_paintable_gate": paint_pass,
        "original_strong_edge_gate": contrast_pass,
        "mae_ratio": ratio, "edge_retained": retained,
        "singleton_reduction": reduction,
        "main_surfaces": main_count, "paintable": real_paint,
        "source_atoms": result["counts"]["atoms"],
        "source_regions": result["counts"]["patches"],
        "first_seconds": round(first_seconds, 3),
        "replay_seconds": round(replay_seconds, 3),
    }
    return manifest, summary


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    colors, provenance = palette_reader.read_engine_palette(
        root / "gameEngine/main.min_653f95bc.js")
    if provenance["engine_git_blob_sha1"] != ENGINE_BLOB or tuple(colors[6]) != (255, 255, 255):
        raise RuntimeError("BLOCKED_RAG9_GAME128_UNPINNED")
    all_results = [run_source(root, filename, colors, output, i)
                   for i, filename in enumerate(SOURCES)]
    manifests, timing = zip(*all_results)
    n = sum(m["numeric_gate"] == "PASS" for m in manifests)
    wv = manifests[0]["candidate_to_nearest128_rgb_mae_ratio"] <= 1.15
    main_ok = all(m["main_gate"] for m in manifests if m["main_gate"] is not None)
    paint_ok = all(m["paintable_gate"] for m in manifests if m["paintable_gate"] is not None)
    strong_ok = all(m["contrast_gate"] for m in manifests if m["contrast_gate"] is not None)
    summary = {
        "experiment": rag9.VERSION, "e0_git_blob_sha1": E0_BLOB,
        "source_count": len(manifests), "source_paths": list(SOURCES),
        "numeric_pass_count": n, "numeric_gate": "PASS" if n >= 2 else "FAIL",
        "mandatory_wv_rgb_mae": "PASS" if wv else "FAIL",
        "main_gate": "PASS" if main_ok else "FAIL",
        "real_paintable_gate": "PASS" if paint_ok else "FAIL",
        "strong_original_edge_gate": "PASS" if strong_ok else "FAIL",
        "quality_acceptance": "PENDING_INDEPENDENT_VISUAL_AND_RAW_REVIEW",
        "original_only": True, "no_legacy_derived_art": True,
        "native_egret": "NOT_RUN", "formal_bpred_s4": "BLOCKED",
        "exact_game_chalk": "NOT_RUN", "per_source": list(timing),
    }
    (output / "00_RAG9_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
