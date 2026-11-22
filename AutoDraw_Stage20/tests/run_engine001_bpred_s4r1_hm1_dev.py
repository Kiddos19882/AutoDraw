#!/usr/bin/env python3
"""One frozen HM1 original-protected-atom E2: four complete originals twice.

NO prior derived images/labels/strokes used, never native Egret or game CHALK.
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
import engine001_bpred_s4r1_hm1_lowlight_hue_modes as hm1
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_reader

SOURCES = (
    "testImages/wV6VeZI9S1Y.png",
    "data/generated_autodraw_plan/images_31_first/Sanrio_Characters_Hello_Kitty_Image026.webp",
    "data/generated_autodraw_plan/images_31_first/EZAL3k9ddfs.jpg",
    "data/generated_autodraw_plan/images_31_first/images (1).png",
)
E0 = "ENGINE001_BPRED001_S4R1_HM1_LOWLIGHT_HUE_MODES_PREREG_2026-11-22.md"
E0_BLOB = "ee10dec2a1a22732e69e4aa5a3a0f42c63e4569f"
ENGINE_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
MAIN_LIMITS = {SOURCES[0]: 5444, SOURCES[2]: 39894}
PAINTABLE_LIMITS = {SOURCES[0]: 5283, SOURCES[2]: 38682}
RAW_KEYS = (
    "original_graph_id", "surface_id", "protected_source_atom_id",
    "original_hue_mode", "source_mode_region_id",
    "source_region_parent_main", "region_hue_mode",
    "region_supported_dark_hue", "region_color_index",
    "protected_original_dot", "strong_original_region_pair", "strong_original_region_length",
    "paintable_id", "game_index", "baseline_index",
    "source_edge", "unknown", "adjacency",
)


def sha256(raw: bytes):
    return hashlib.sha256(raw).hexdigest()


def id_picture(label: np.ndarray, alpha: np.ndarray):
    rgb = np.zeros((*label.shape, 4), np.uint8)
    data = label.astype(np.uint64)
    active = label > 0
    rgb[active, 0] = ((data[active] * 73 + 49) % 230 + 14).astype(np.uint8)
    rgb[active, 1] = ((data[active] * 157 + 67) % 230 + 14).astype(np.uint8)
    rgb[active, 2] = ((data[active] * 191 + 89) % 230 + 14).astype(np.uint8)
    rgb[..., 3] = alpha
    return Image.fromarray(rgb, "RGBA")


def review_atlas(folder: Path, names: list[str]):
    labels = (
        "Current original RGB",
        "Fresh nearest128 - evaluation",
        "Original chromatic source graph",
        "Original hue modes/owners before swatches",
        "Original high-contrast protected dots",
        "Actual 4connected paintable by main+swatch",
        "HM1 original-source regional game128",
        "Original true strong edge mask",
    )
    out = Image.new("RGB", (340 * len(labels), 430), (245, 245, 245))
    ink = ImageDraw.Draw(out)
    for i, (name, label) in enumerate(zip(names, labels)):
        ink.text((i * 340 + 7, 7), label, fill=(28, 28, 28))
        with Image.open(folder / name) as f:
            image = f.convert("RGB")
            image.thumbnail((326, 387), Image.Resampling.LANCZOS)
        out.paste(image, (i * 340 + (340 - image.width) // 2, 30))
    out.save(folder / "00_HM1_SOURCE_ATLAS.png")


def run_one(root: Path, relative: str, colors: np.ndarray, dest: Path, index: int):
    original_file = root / relative
    raw = original_file.read_bytes()
    decoded = original_reader.decode_original(raw)
    rgba = decoded["rgba"]
    folder = dest / ("%02d_%s" % (index, original_file.stem))
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original_file, folder / ("original" + original_file.suffix))

    started = time.perf_counter()
    data = hm1.build_hm1(rgba, colors)
    first_seconds = time.perf_counter() - started
    started = time.perf_counter()
    again = hm1.build_hm1(rgba, colors)
    replay_seconds = time.perf_counter() - started
    for key in RAW_KEYS + ("preview_rgba",):
        if not np.array_equal(data[key], again[key]):
            raise RuntimeError("BLOCKED_HM1_SOURCE_NONDETERMINISTIC_" + key)
    if data["counts"] != again["counts"]:
        raise RuntimeError("BLOCKED_HM1_NONDETERMINISTIC_COUNT")

    metric = hm1.evaluate_hm1(rgba, colors, data)
    opaque = rgba[..., 3] == 255
    nearest = rgba.copy()
    nearest[opaque, :3] = colors[data["baseline_index"][opaque]]
    anchor = rgba.copy()
    anchor[data["protected_original_dot"], :3] = (255, 55, 0)
    true_source_edge = np.zeros_like(rgba)
    true_source_edge[..., 3] = rgba[..., 3]
    true_source_edge[data["source_edge"], :3] = (245, 55, 38)

    files = (
        "01_CURRENT_ORIGINAL_RGB.png",
        "02_FRESH_NEAREST128_BASELINE.png",
        "03_ORIGINAL_CHROMA_GRAPH.png",
        "04_NEW_SOURCE_DETAIL_ATOMS.png",
        "05_PROTECTED_ORIGINAL_ANCHOR_PIXELS.png",
        "06_ACTUAL_PAINTABLE.png",
        "07_HM1_COMPOSED_GAME128.png",
        "08_ORIGINAL_STRONG_EDGE_PIXELS.png",
    )
    images = (
        Image.fromarray(rgba),
        Image.fromarray(nearest),
        id_picture(data["original_graph_id"], rgba[..., 3]),
        id_picture(data["source_mode_region_id"], rgba[..., 3]),
        Image.fromarray(anchor),
        id_picture(data["paintable_id"], rgba[..., 3]),
        Image.fromarray(data["preview_rgba"]),
        Image.fromarray(true_source_edge),
    )
    for name, image in zip(files, images):
        image.save(folder / name)
    review_atlas(folder, list(files))
    np.savez_compressed(folder / "09_HM1_CURRENT_ORIGINAL_SOURCE_ARRAYS.npz",
                        **{key: data[key] for key in RAW_KEYS})

    base = metric["baseline"]
    candidate = metric["candidate"]
    reduction = 100 * (base["singletons"] - candidate["singletons"]) / base["singletons"] if base["singletons"] else None
    original_mae = metric["baseline_rgb_mae"]
    output_mae = metric["candidate_rgb_mae"]
    ratio = output_mae / original_mae if original_mae > 1e-12 else None
    numeric_125 = (reduction is not None and reduction >= 15.
                   and ratio is not None and ratio <= 1.25)
    numeric_115 = (reduction is not None and reduction >= 15.
                   and ratio is not None and ratio <= 1.15)
    main = data["counts"]["main_surfaces"]
    paintable = data["counts"]["paintable_components"]
    main_gate = main < MAIN_LIMITS[relative] if relative in MAIN_LIMITS else None
    paint_gate = paintable < PAINTABLE_LIMITS[relative] if relative in PAINTABLE_LIMITS else None
    edge_retained = metric["strong_source_contrast"]["retained_fraction"]
    edge_gate = edge_retained >= .75 if relative in MAIN_LIMITS else None
    manifest = {
        "version": data["version"], "e0": E0, "e0_git_blob_sha1": E0_BLOB,
        "game_engine_git_blob_sha1": ENGINE_BLOB,
        "source_path": relative, "source_sha256": sha256(raw),
        "source_git_blob_sha1": decoded["git_blob_sha1"],
        "original_source_size_wh": [decoded["width"], decoded["height"]],
        "exif_orientation": decoded["exif_orientation"],
        "source_original_mode": decoded["original_mode"],
        "game128_sha256": sha256(colors.tobytes()),
        "source_frame": "source original pixel edges, game calibration UNKNOWN",
        "raw_metrics": metric,
        "singletons_cut_percent": reduction,
        "source_rgb_mae_ratio_nearest128": ratio,
        "engineering_numeric_125": "PASS" if numeric_125 else "FAIL",
        "historical_original_scientific_115": "PASS" if numeric_115 else "FAIL",
        "actual_main_count": main,
        "actual_main_gate": main_gate,
        "actual_paintable_count": paintable,
        "actual_paintable_gate": paint_gate,
        "true_original_strong_edges_retained": edge_retained,
        "true_original_75_percent_strong_gate": edge_gate,
        "source_original_only": True,
        "legacy_artistic_input": False,
        "original_atom_one_swatch": True,
        "no_postcolor_detail_overlay": True,
        "two_clean_original_builds_identical": True,
        "source_owner_status": data["source_owner_status"],
        "stroke_admission": data["stroke_admission"],
        "source_to_logical": data["source_to_logical"],
        "native_egret": "NOT_RUN", "formal_s4": "BLOCKED",
        "game_chalk": "NOT_RUN", "visual_source_review": "PENDING_SOURCE_ATLAS",
        "outputs_sha256": {},
    }
    for f in sorted(folder.iterdir()):
        if f.is_file():
            manifest["outputs_sha256"][f.name] = sha256(f.read_bytes())
    (folder / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False),
        encoding="utf-8")
    return manifest, {
        "source": relative,
        "first_seconds": round(first_seconds, 3),
        "repeat_seconds": round(replay_seconds, 3),
        "original_source_graph_regions": int(data["counts"]["original_chroma_graph"]),
        "protected_source_points": int(data["counts"]["source_protected_original_points"]),
        "original_source_mode_regions": int(data["counts"]["source_final_regions"]),
        "main_count": main, "true_paintable_count": paintable,
        "source_RGB_MAE": output_mae, "fresh_nearest128_RGB_MAE": original_mae,
        "mae_ratio": ratio, "singletons_cut_percent": reduction,
        "source_strong_retained": edge_retained,
        "engineering_numeric_125": manifest["engineering_numeric_125"],
        "historical_scientific_numeric_115": manifest["historical_original_scientific_115"],
        "main_gate": main_gate, "paintable_gate": paint_gate,
        "source_strong_edge_gate": edge_gate,
    }


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args.add_argument("--output", type=Path, required=True)
    opt = args.parse_args()
    root, out = opt.root.resolve(), opt.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    colors, provenance = palette_reader.read_engine_palette(
        root / "gameEngine/main.min_653f95bc.js")
    if provenance["engine_git_blob_sha1"] != ENGINE_BLOB or tuple(colors[6]) != (255, 255, 255):
        raise RuntimeError("BLOCKED_HM1_GAME128_ENGINE_UNPINNED")
    result = [run_one(root, path, colors, out, i)
              for i, path in enumerate(SOURCES)]
    manifest, metrics = zip(*result)
    n125 = sum(m["engineering_numeric_125"] == "PASS" for m in manifest)
    n115 = sum(m["historical_original_scientific_115"] == "PASS" for m in manifest)
    wv125 = metrics[0]["mae_ratio"] <= 1.25
    wv115 = metrics[0]["mae_ratio"] <= 1.15
    real = all(m["paintable_gate"] is True for m in metrics
               if m["paintable_gate"] is not None)
    mains = all(m["main_gate"] is True for m in metrics
                if m["main_gate"] is not None)
    edge = all(m["source_strong_edge_gate"] is True for m in metrics
               if m["source_strong_edge_gate"] is not None)
    summary = {
        "version": hm1.VERSION,
        "e0_git_blob_sha1": E0_BLOB,
        "genuine_game_engine_git_blob_sha1": ENGINE_BLOB,
        "originals": list(SOURCES), "source_original_count": 4,
        "builds_per_source": 2,
        "engineering_numeric_125_count": n125,
        "engineering_numeric_125_gate": "PASS" if n125 >= 2 else "FAIL",
        "engineering_mandatory_wv_125": "PASS" if wv125 else "FAIL",
        "historical_strict_115_count": n115,
        "historical_strict_115_gate": "PASS" if n115 >= 2 else "FAIL",
        "historical_mandatory_wv_115": "PASS" if wv115 else "FAIL",
        "true_real_paintable_gate": "PASS" if real else "FAIL",
        "true_original_main_gate": "PASS" if mains else "FAIL",
        "true_original_strong_edge_gate": "PASS" if edge else "FAIL",
        "source_original_only": True, "no_old_derived_art": True,
        "no_aftercolor_detail_overlay": True,
        "native_egret": "NOT_RUN", "formal_s4": "BLOCKED",
        "exact_game_chalk": "NOT_RUN",
        "visual_quality": "PENDING_INDEPENDENT_ATLAS_REVIEW",
        "overall_engineering_source_acceptance": "PENDING_VISUAL_AND_RAW_REVIEW",
        "source_metrics": list(metrics),
    }
    (out / "00_HM1_SUMMARY.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(json.dumps(summary, sort_keys=True, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
