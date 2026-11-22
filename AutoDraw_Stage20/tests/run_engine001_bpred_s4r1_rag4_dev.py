#!/usr/bin/env python3
"""One frozen RAG4 candidate, exactly four original-only DEV source E2 runs.

No RAG1/RAG2/FC1 artwork, labels, strokes, reports or cached maps as input.
The manifest is deterministic; wall-clock runtime lives in the run summary.
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

import engine001_bpred_s4r1_generic_source_maps as originals
import engine001_bpred_s4r1_rag4_hierarchy as rag4
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_reader


SOURCES = (
    "testImages/wV6VeZI9S1Y.png",
    "data/generated_autodraw_plan/images_31_first/Sanrio_Characters_Hello_Kitty_Image026.webp",
    "data/generated_autodraw_plan/images_31_first/EZAL3k9ddfs.jpg",
    "data/generated_autodraw_plan/images_31_first/images (1).png",
)
E0_FILE = "ENGINE001_BPRED001_S4R1_REGION_COLOR_RAG4_COHERENT_DETAIL_PREREG_2026-11-22.md"
E0_BLOB = "34add17b33edd54cdefeb551d781cc987433ba23"
ENGINE_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
COMPLEX_MAIN_LIMITS = {SOURCES[0]: 5444, SOURCES[2]: 39894}
RAW_KEYS = (
    "surface_id", "color_segment_id", "detail_id", "surface_color_index", "surface_color_table",
    "detail_parent_surface_id", "detail_color_index", "game_index",
    "baseline_index", "source_edge", "unknown", "adjacency",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def id_picture(labels: np.ndarray, alpha: np.ndarray) -> Image.Image:
    out = np.zeros((*labels.shape, 4), dtype=np.uint8)
    ids = labels.astype(np.uint64)
    active = labels > 0
    out[active, 0] = ((ids[active] * 73 + 49) % 230 + 14).astype(np.uint8)
    out[active, 1] = ((ids[active] * 157 + 67) % 230 + 14).astype(np.uint8)
    out[active, 2] = ((ids[active] * 191 + 89) % 230 + 14).astype(np.uint8)
    out[:, :, 3] = alpha
    return Image.fromarray(out, "RGBA")


def atlas(directory: Path, names: list[str]):
    headers = ("Original RGB", "Main source-connected surfaces", "Protected detail IDs",
               "RAG4 composed game128", "Original strong source edges")
    screen = Image.new("RGB", (340 * len(names), 430), (245, 245, 245))
    draw = ImageDraw.Draw(screen)
    for i, (name, header) in enumerate(zip(names, headers)):
        draw.text((i * 340 + 6, 7), header, fill=(25, 25, 25))
        with Image.open(directory / name) as opened:
            image = opened.convert("RGB")
            image.thumbnail((328, 384), Image.Resampling.LANCZOS)
        screen.paste(image, (340 * i + (340 - image.width) // 2, 30))
    screen.save(directory / "00_REVIEW_ATLAS.png")


def single(root: Path, relative: str, colors: np.ndarray, out: Path, i: int):
    file = root / relative
    raw = file.read_bytes()
    source = originals.decode_original(raw)
    rgba = source["rgba"]
    directory = out / ("%02d_%s" % (i, file.stem))
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(file, directory / ("original" + file.suffix))

    start = time.perf_counter()
    result = rag4.build_rag4(rgba, colors)
    primary_seconds = time.perf_counter() - start
    start = time.perf_counter()
    replay = rag4.build_rag4(rgba, colors)
    replay_seconds = time.perf_counter() - start
    # All raw array data must be byte-identical on two clean original runs.
    for key in RAW_KEYS + ("preview_rgba",):
        if not np.array_equal(result[key], replay[key]):
            raise RuntimeError("BLOCKED_RAG4_NONDETERMINISTIC_" + key)
    if result["counts"] != replay["counts"]:
        raise RuntimeError("BLOCKED_RAG4_NONDETERMINISTIC_COUNTS")

    metric = rag4.evaluate_rag4(rgba, colors, result)
    opaque = rgba[:, :, 3] == 255
    nearest = rgba.copy()
    nearest[opaque, :3] = colors[result["baseline_index"][opaque]]
    edge_png = np.zeros_like(rgba)
    edge_png[:, :, 3] = rgba[:, :, 3]
    edge_png[result["source_edge"], :3] = (245, 55, 38)
    files = (
        "01_ORIGINAL_RGB.png", "02_FRESH_NEAREST128.png",
        "03_MAIN_SURFACES.png", "04_COHERENT_COLOR_DETAIL_IDS.png",
        "05_RAG4_GAME128_COMPOSED.png", "06_SOURCE_STRONG_EDGES.png"
    )
    pictures = (
        Image.fromarray(rgba), Image.fromarray(nearest),
        id_picture(result["surface_id"], rgba[:, :, 3]),
        id_picture(result["detail_id"], rgba[:, :, 3]),
        Image.fromarray(result["preview_rgba"]), Image.fromarray(edge_png)
    )
    for name, picture in zip(files, pictures):
        picture.save(directory / name)
    atlas(directory, [files[i] for i in (0, 2, 3, 4, 5)])
    np.savez_compressed(directory / "07_RAG4_SOURCE_LAYERS.npz",
                        **{key: result[key] for key in RAW_KEYS})
    before = metric["baseline"]["singletons"]
    after = metric["candidate"]["singletons"]
    reduction = (100.0 * (before - after) / before if before else None)
    base_mae = metric["baseline_rgb_mae"]
    mae_ratio = metric["candidate_rgb_mae"] / base_mae if base_mae > 1e-12 else None
    numeric = (reduction is not None and reduction >= 15.0
               and mae_ratio is not None and mae_ratio <= 1.15)
    main_count = int(result["counts"]["main_surfaces"])
    main_limit = COMPLEX_MAIN_LIMITS.get(relative)
    main_gate = main_count < main_limit if main_limit else None
    manifest = {
        "experiment": rag4.VERSION, "protocol": E0_FILE,
        "e0_git_blob_sha1": E0_BLOB, "source": relative,
        "source_sha256": sha256(raw),
        "source_git_blob_sha1": source["git_blob_sha1"],
        "source_size_wh": [source["width"], source["height"]],
        "original_mode": source["original_mode"],
        "exif_orientation": source["exif_orientation"],
        "game128_sha256": sha256(colors.tobytes()),
        "coordinate_frame": "source-pixel-edges; no game calibration",
        "metrics": metric,
        "singleton_reduction_percent": reduction,
        "candidate_to_baseline_rgb_mae_ratio": mae_ratio,
        "numeric_screen": "PASS_NUMERIC_ONLY" if numeric else "FAIL_NUMERIC_ONLY",
        "complex_main_surface_limit_exclusive": main_limit,
        "complex_main_surface_count_pass": main_gate,
        "two_clean_runs_array_identical": True,
        "original_only": True, "legacy_artistic_input": False,
        "source_owner_status": result["source_owner_status"],
        "stroke_admission": result["stroke_admission"],
        "native_egret": "NOT_RUN", "formal_s4": "BLOCKED",
        "visual_review": "PENDING_ARTIFACT_REVIEW",
        "output_files_sha256": {},
    }
    for f in sorted(directory.iterdir()):
        if f.is_file():
            manifest["output_files_sha256"][f.name] = sha256(f.read_bytes())
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8")
    return manifest, {
        "source": relative, "primary_seconds": round(primary_seconds, 3),
        "replay_seconds": round(replay_seconds, 3),
        "numeric_screen": manifest["numeric_screen"],
        "complex_main_gate": main_gate,
        "source_edge_retained_fraction": metric["strong_source_contrast"]["retained_fraction"],
        "main_surfaces": main_count,
        "color_segments": metric["counts"]["final_color_segments"],
        "recolored_color_segments": metric["counts"]["recolored_color_segments"],
        "detail_segments": metric["counts"]["detail_segments"],
        "detail_pixels": metric["counts"]["detail_pixels"],
        "original_sha256": manifest["source_sha256"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    colors, provenance = palette_reader.read_engine_palette(
        root / "gameEngine/main.min_653f95bc.js")
    if provenance["engine_git_blob_sha1"] != ENGINE_BLOB:
        raise RuntimeError("BLOCKED_RAG4_UNPINNED_ENGINE")
    if tuple(colors[6]) != (255, 255, 255):
        raise RuntimeError("BLOCKED_RAG4_GAME_WHITE_MISMATCH")
    results = [single(root, source, colors, output, i)
               for i, source in enumerate(SOURCES)]
    manifests, timings = zip(*results)
    numeric_pass = sum(m["numeric_screen"] == "PASS_NUMERIC_ONLY" for m in manifests)
    detail_all = all(m["metrics"]["counts"]["detail_segments"] > 0 for m in manifests)
    complex_pass = all(m["complex_main_surface_count_pass"] is True
                       for m in manifests if m["complex_main_surface_limit_exclusive"])
    summary = {
        "experiment": rag4.VERSION,
        "e0_git_blob_sha1": E0_BLOB,
        "source_count": len(manifests),
        "source_paths": list(SOURCES),
        "numeric_pass_count": numeric_pass,
        "numeric_gate": "PASS" if numeric_pass >= 2 else "FAIL",
        "complex_main_surface_gate": "PASS" if complex_pass else "FAIL",
        "detail_nonempty_all_dev": detail_all,
        "color_subregion_total": sum(m["metrics"]["counts"]["final_color_segments"] for m in manifests),
        "e2_status": "SOURCE_ONLY_NOT_GAME",
        "visual_quality": "PENDING_ARTIFACT_REVIEW",
        "research_acceptance": "PENDING_VISUAL_AND_SYNTHETIC_REVIEW",
        "native_egret": "NOT_RUN", "formal_s4": "BLOCKED",
        "game_chalk": "NOT_RUN", "no_legacy_art": True,
        "runtime": list(timings),
    }
    (output / "00_RAG4_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
