#!/usr/bin/env python3
"""Two prospective CHROMA-AB1 source color tests, A/B x four DEV originals x2.

Full originals only. No prior derived art, no native Egret, no color gate changes.
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
import engine001_bpred_s4r1_chroma_ab1_color_tests as ab
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_reader

E0 = "ENGINE001_BPRED001_S4R1_CHROMA_AB1_TWO_COLOR_TESTS_PREREG_2026-11-22.md"
E0_BLOB = "dc11901d7502679e98f945637625a83320b5d67b"
ENGINE_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
SOURCES = (
    "testImages/wV6VeZI9S1Y.png",
    "data/generated_autodraw_plan/images_31_first/Sanrio_Characters_Hello_Kitty_Image026.webp",
    "data/generated_autodraw_plan/images_31_first/EZAL3k9ddfs.jpg",
    "data/generated_autodraw_plan/images_31_first/images (1).png",
)
MAIN_LIMITS = {SOURCES[0]: 5444, SOURCES[2]: 39894}
PAINT_LIMITS = {SOURCES[0]: 5283, SOURCES[2]: 38682}
RAW_KEYS = (
    "surface_id", "source_graph_id", "region_id", "region_parent_main",
    "region_color_index", "edge_component_id", "detail_id",
    "detail_parent_main", "detail_color_index", "paintable_id",
    "game_index", "baseline_index", "source_edge", "unknown",
    "adjacency", "original_strong_boundary_pairs",
    "original_strong_boundary_lengths",
)


def sha(data: bytes):
    return hashlib.sha256(data).hexdigest()


def picture_ids(ids: np.ndarray, alpha: np.ndarray):
    image = np.zeros((*ids.shape, 4), np.uint8)
    src = ids.astype(np.uint64)
    mask = src > 0
    image[mask, 0] = ((src[mask] * 73 + 49) % 230 + 14).astype(np.uint8)
    image[mask, 1] = ((src[mask] * 157 + 67) % 230 + 14).astype(np.uint8)
    image[mask, 2] = ((src[mask] * 191 + 89) % 230 + 14).astype(np.uint8)
    image[..., 3] = alpha
    return Image.fromarray(image, "RGBA")


def atlas(folder: Path, images: list[str]):
    headers = (
        "CURRENT original RGB",
        "Fresh nearest128 (metric baseline)",
        "Original main surfaces",
        "Unmerged original chroma graph",
        "True protected detail groups",
        "Actual 4-connected paintable",
        "Composed game128 (candidate)",
        "Original source strong edges",
    )
    canvas = Image.new("RGB", (340 * 8, 440), (245, 245, 245))
    ink = ImageDraw.Draw(canvas)
    for i, (name, title) in enumerate(zip(images, headers)):
        ink.text((i * 340 + 6, 7), title, fill=(25, 25, 25))
        with Image.open(folder / name) as opened:
            png = opened.convert("RGB")
            png.thumbnail((328, 384), Image.Resampling.LANCZOS)
        canvas.paste(png, (i * 340 + (340 - png.width) // 2, 32))
    canvas.save(folder / "00_SOURCE_ATLAS.png")


def run_one(root: Path, name: str, palette: np.ndarray,
            variant: str, i: int, output: Path):
    original_path = root / name
    raw = original_path.read_bytes()
    decoded = original_reader.decode_original(raw)
    rgba = decoded["rgba"]
    directory = output / ("%s_%02d_%s" % (variant, i, original_path.stem))
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original_path, directory / ("original" + original_path.suffix))
    begin = time.perf_counter()
    result = ab.build_chroma_ab1(rgba, palette, variant)
    first = time.perf_counter() - begin
    begin = time.perf_counter()
    replay = ab.build_chroma_ab1(rgba, palette, variant)
    second = time.perf_counter() - begin
    for key in RAW_KEYS + ("preview_rgba",):
        if not np.array_equal(result[key], replay[key]):
            raise RuntimeError("BLOCKED_CHROMA_AB1_NONDETERMINISTIC_" + variant + "_" + key)
    if result["counts"] != replay["counts"]:
        raise RuntimeError("BLOCKED_CHROMA_AB1_COUNT_NONDETERMINISTIC")
    metric = ab.evaluate_chroma_ab1(rgba, palette, result)
    opaque = rgba[..., 3] == 255
    nearest = rgba.copy()
    nearest[opaque, :3] = palette[result["baseline_index"][opaque]]
    edge_png = np.zeros_like(rgba)
    edge_png[..., 3] = rgba[..., 3]
    edge_png[result["source_edge"], :3] = (245, 55, 38)
    files = (
        "01_CURRENT_ORIGINAL.png",
        "02_FRESH_NEAREST128.png",
        "03_SOURCE_MAIN.png",
        "04_UNMERGED_SOURCE_CHROMA_GRAPH.png",
        "05_ORIGINAL_SOURCE_DETAIL.png",
        "06_ACTUAL_PAINTABLE.png",
        "07_GAME128_COLOR_PREVIEW.png",
        "08_ORIGINAL_STRONG_SOURCE_EDGES.png",
    )
    pictures = (
        Image.fromarray(rgba),
        Image.fromarray(nearest),
        picture_ids(result["surface_id"], rgba[..., 3]),
        picture_ids(result["region_id"], rgba[..., 3]),
        picture_ids(result["detail_id"], rgba[..., 3]),
        picture_ids(result["paintable_id"], rgba[..., 3]),
        Image.fromarray(result["preview_rgba"]),
        Image.fromarray(edge_png),
    )
    for f, image in zip(files, pictures):
        image.save(directory / f)
    atlas(directory, list(files))
    np.savez_compressed(directory / "09_ALL_ORIGINAL_SOURCE_ARRAYS.npz",
                        **{key: result[key] for key in RAW_KEYS})
    single_before = metric["baseline"]["singletons"]
    single_after = metric["candidate"]["singletons"]
    singleton_reduction = 100. * (single_before - single_after) / single_before if single_before else None
    baseline_rgb_mae = metric["baseline_rgb_mae"]
    candidate_rgb_mae = metric["candidate_rgb_mae"]
    ratio = candidate_rgb_mae / baseline_rgb_mae if baseline_rgb_mae > 1e-12 else None
    original_strong_fraction = metric["strong_source_contrast"]["retained_fraction"]
    strict_numeric = (
        singleton_reduction is not None and singleton_reduction >= 15.
        and ratio is not None and ratio <= 1.15
    )
    main_count = result["counts"]["main_surfaces"]
    paintable = result["counts"]["paintable_components"]
    main_gate = main_count < MAIN_LIMITS[name] if name in MAIN_LIMITS else None
    paint_gate = paintable < PAINT_LIMITS[name] if name in PAINT_LIMITS else None
    edge_gate = original_strong_fraction >= .75 if name in MAIN_LIMITS else None
    manifest = {
        "experiment": ab.VERSION, "test_variant": variant,
        "preregistered_modes": list(ab.VARIANTS), "e0_protocol": E0,
        "e0_git_blob_sha1": E0_BLOB, "engine_git_blob_sha1": ENGINE_BLOB,
        "input": name, "input_sha256": sha(raw),
        "input_git_blob_sha1": decoded["git_blob_sha1"],
        "input_size_wh": [decoded["width"], decoded["height"]],
        "input_mode": decoded["original_mode"],
        "exif_orientation": decoded["exif_orientation"],
        "game128_sha256": sha(palette.tobytes()),
        "source_frame": "full original RGB pixels, game NOT calibrated",
        "measurements": metric, "original_singleton_cut_percent": singleton_reduction,
        "rgb_mae_ratio_original_baseline": ratio,
        "strict_115_percent_numeric_gate": "PASS" if strict_numeric else "FAIL",
        "original_main_count": main_count,
        "strict_main_gate": main_gate,
        "real_paintable_count": paintable,
        "strict_real_paintable_gate": paint_gate,
        "true_original_strong_edges_retained": original_strong_fraction,
        "strict_75_percent_original_strong_edges_gate": edge_gate,
        "original_only": True, "legacy_artistic_input": False,
        "native_egret": "NOT_RUN", "game_chalk": "NOT_RUN",
        "formal_bpred_s4": "BLOCKED",
        "source_owner_status": result["source_owner_status"],
        "stroke_admission": result["stroke_admission"],
        "repeat_raw_identical": True,
        "source_to_logical": result["source_to_logical"],
        "detail_visual_review": "PENDING_ATLAS_REVIEW",
        "outputs_sha256": {},
    }
    for file in sorted(directory.iterdir()):
        if file.is_file():
            manifest["outputs_sha256"][file.name] = sha(file.read_bytes())
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")
    return result, manifest, {
        "test_variant": variant, "original": name,
        "source_graph_regions": result["counts"]["source_graph_regions"],
        "source_main_surfaces": main_count, "real_paintable_ids": paintable,
        "original_details": result["counts"]["detail_components"],
        "original_detail_pixels": result["counts"]["detail_pixels"],
        "rgb_mae": candidate_rgb_mae, "baseline_rgb_mae": baseline_rgb_mae,
        "mae_ratio": ratio, "singleton_reduction": singleton_reduction,
        "original_strong_fraction": original_strong_fraction,
        "strict_numeric_gate": manifest["strict_115_percent_numeric_gate"],
        "strict_main_gate": main_gate, "strict_paintable_gate": paint_gate,
        "strict_original_strong_edge_gate": edge_gate,
        "run_one_seconds": round(first, 3), "run_two_seconds": round(second, 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    colors, engine = palette_reader.read_engine_palette(
        root / "gameEngine/main.min_653f95bc.js"
    )
    if engine["engine_git_blob_sha1"] != ENGINE_BLOB or tuple(colors[6]) != (255, 255, 255):
        raise RuntimeError("BLOCKED_CHROMA_AB1_GAME128_UNPINNED")
    all_data = []
    for i, filename in enumerate(SOURCES):
        pair = {}
        for variant in ab.VARIANTS:
            data, manifest, short = run_one(root, filename, colors, variant, i, output)
            pair[variant] = data
            all_data.append(short)
        # Both experiments MUST share exactly the same freshly recomputed
        # original source geometry, independent of their game palette objective.
        for key in ("surface_id", "source_graph_id", "region_id",
                    "edge_component_id", "source_edge",
                    "original_strong_boundary_pairs",
                    "original_strong_boundary_lengths"):
            if not np.array_equal(pair["A"][key], pair["B"][key]):
                raise RuntimeError("BLOCKED_CHROMA_AB1_AB_DIFFERENT_SOURCE_" + key)
        side = Image.new("RGB", (1600, 425), (248, 248, 248))
        paint = ImageDraw.Draw(side)
        for j, (label, mode) in enumerate((
            ("Original", "A"), ("A game128", "A"),
            ("B game128", "B"), ("Fresh nearest128", "A")
        )):
            name = {
                "Original": "01_CURRENT_ORIGINAL.png",
                "A game128": "07_GAME128_COLOR_PREVIEW.png",
                "B game128": "07_GAME128_COLOR_PREVIEW.png",
                "Fresh nearest128": "02_FRESH_NEAREST128.png",
            }[label]
            folder = output / ("%s_%02d_%s" % (mode, i, Path(filename).stem))
            paint.text((j * 400 + 8, 8), label, fill=(25, 25, 25))
            with Image.open(folder / name) as opened:
                img = opened.convert("RGB")
                img.thumbnail((390, 380), Image.Resampling.LANCZOS)
            side.paste(img, (j * 400 + (400 - img.width) // 2, 29))
        side.save(output / ("00_AB_COMPARE_%02d.png" % i))
    variants = {}
    for variant in ab.VARIANTS:
        records = [x for x in all_data if x["test_variant"] == variant]
        count_numeric = sum(x["strict_numeric_gate"] == "PASS" for x in records)
        wv = records[0]
        original_gate = all(x["strict_original_strong_edge_gate"] is True
                            for x in records if x["strict_original_strong_edge_gate"] is not None)
        main_gate = all(x["strict_main_gate"] is True
                        for x in records if x["strict_main_gate"] is not None)
        paintable_gate = all(x["strict_paintable_gate"] is True
                            for x in records if x["strict_paintable_gate"] is not None)
        improvements = (
            wv["rgb_mae"] <= 5.813909 and
            original_gate and main_gate and paintable_gate
        )
        variants[variant] = {
            "source_original_count": 4, "two_runs_per_source": True,
            "strict_numeric_count": count_numeric,
            "strict_numeric_gate": "PASS" if count_numeric >= 2 else "FAIL",
            "strict_wv_115_percent_color_gate":
                "PASS" if wv["mae_ratio"] <= 1.15 else "FAIL",
            "strict_original_strong_edge_gate":
                "PASS" if original_gate else "FAIL",
            "strict_main_gate": "PASS" if main_gate else "FAIL",
            "strict_real_paintable_gate":
                "PASS" if paintable_gate else "FAIL",
            "meaningful_color_improvement_WITH_DETAIL_PENDING_VISUAL":
                improvements,
            "raw_metrics": records,
        }
    summary = {
        "experiment": ab.VERSION, "e0_blob_sha1": E0_BLOB,
        "tests": list(ab.VARIANTS),
        "original_only": True, "legacy_art_used": False,
        "game128_engine_git_blob_sha1": ENGINE_BLOB,
        "both_tests": variants,
        "original_source_count_per_test": 4,
        "total_original_source_executions": 16,
        "meaningful_color_improvement_if_visual_details_pass":
            any(variants[v]["meaningful_color_improvement_WITH_DETAIL_PENDING_VISUAL"]
                for v in ab.VARIANTS),
        "future_color_gate_decision": "PENDING_INDEPENDENT_VISUAL_AND_E2_REVIEW",
        "visual_gate": "PENDING_INDEPENDENT_REVIEW",
        "native_egret": "NOT_RUN", "exact_game_chalk": "NOT_RUN",
        "formal_s4": "BLOCKED",
    }
    (output / "00_CHROMA_AB1_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
