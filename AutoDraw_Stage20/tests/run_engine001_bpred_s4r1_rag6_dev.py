#!/usr/bin/env python3
"""One frozen RAG6 candidate, exactly four original-only DEV source E2 runs.

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
import engine001_bpred_s4r1_rag6_edge_topology as rag6
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_reader


SOURCES = (
    "testImages/wV6VeZI9S1Y.png",
    "data/generated_autodraw_plan/images_31_first/Sanrio_Characters_Hello_Kitty_Image026.webp",
    "data/generated_autodraw_plan/images_31_first/EZAL3k9ddfs.jpg",
    "data/generated_autodraw_plan/images_31_first/images (1).png",
)
E0_FILE = "ENGINE001_BPRED001_S4R1_REGION_COLOR_RAG6_EDGE_TOPOLOGY_PREREG_2026-11-22.md"
E0_BLOB = "c384734adcc2615a4ac0d43e81603399c122990f"
ENGINE_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
COMPLEX_MAIN_LIMITS = {SOURCES[0]: 5444, SOURCES[2]: 39894}
COMPLEX_PAINTABLE_LIMITS = {SOURCES[0]: 5283, SOURCES[2]: 38682}
RAW_KEYS = (
    "surface_id", "edge_component_id", "patch_id", "patch_parent_surface_id", "patch_color_index",
    "detail_id", "detail_parent_surface_id", "detail_color_index",
    "paintable_id", "game_index", "baseline_index", "source_edge",
    "unknown", "adjacency",
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
    headers = ("Original RGB", "Main source surfaces", "Edge graph source patches",
               "Original edge topology", "Protected actual details",
               "Actual paintable IDs", "RAG6 composed game128", "Original strong edges")
    screen = Image.new("RGB", (340 * len(names), 430), (245, 245, 245))
    draw = ImageDraw.Draw(screen)
    for i, (name, header) in enumerate(zip(names, headers)):
        draw.text((i * 340 + 6, 7), header, fill=(25, 25, 25))
        with Image.open(directory / name) as opened:
            picture = opened.convert("RGB")
            picture.thumbnail((328, 384), Image.Resampling.LANCZOS)
        screen.paste(picture, (340 * i + (340 - picture.width) // 2, 30))
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
    result = rag6.build_rag6(rgba, colors)
    primary_seconds = time.perf_counter() - start
    start = time.perf_counter()
    replay = rag6.build_rag6(rgba, colors)
    replay_seconds = time.perf_counter() - start
    # All raw array data must be byte-identical on two clean original runs.
    for key in RAW_KEYS + ("preview_rgba",):
        if not np.array_equal(result[key], replay[key]):
            raise RuntimeError("BLOCKED_RAG6_NONDETERMINISTIC_" + key)
    if result["counts"] != replay["counts"]:
        raise RuntimeError("BLOCKED_RAG6_NONDETERMINISTIC_COUNTS")

    metric = rag6.evaluate_rag6(rgba, colors, result)
    opaque = rgba[:, :, 3] == 255
    nearest = rgba.copy()
    nearest[opaque, :3] = colors[result["baseline_index"][opaque]]
    edge_png = np.zeros_like(rgba)
    edge_png[:, :, 3] = rgba[:, :, 3]
    edge_png[result["source_edge"], :3] = (245, 55, 38)
    files = (
        "01_ORIGINAL_RGB.png", "02_FRESH_NEAREST128.png",
        "03_MAIN_SURFACES.png", "04_SOURCE_EDGE_GRAPH_PATCHES.png",
        "05_SOURCE_EDGE_TOPOLOGY_IDS.png", "06_PROTECTED_EDGE_DETAILS.png",
        "07_ACTUAL_PAINTABLE_REGIONS.png", "08_RAG6_GAME128_COMPOSED.png",
        "09_SOURCE_STRONG_EDGES.png",
    )
    pictures = (
        Image.fromarray(rgba), Image.fromarray(nearest),
        id_picture(result["surface_id"], rgba[:, :, 3]),
        id_picture(result["patch_id"], rgba[:, :, 3]),
        id_picture(result["edge_component_id"], rgba[:, :, 3]),
        id_picture(result["detail_id"], rgba[:, :, 3]),
        id_picture(result["paintable_id"], rgba[:, :, 3]),
        Image.fromarray(result["preview_rgba"]), Image.fromarray(edge_png),
    )
    for name, picture in zip(files, pictures):
        picture.save(directory / name)
    atlas(directory, [files[i] for i in (0, 2, 3, 4, 5, 6, 7, 8)])
    np.savez_compressed(directory / "10_RAG6_SOURCE_LAYERS.npz",
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
    paintable_count = int(result["counts"]["paintable_components"])
    paintable_limit = COMPLEX_PAINTABLE_LIMITS.get(relative)
    paintable_gate = paintable_count < paintable_limit if paintable_limit else None
    edge_fraction = metric["strong_source_contrast"]["retained_fraction"]
    edge_gate = edge_fraction >= 0.75 if relative in COMPLEX_MAIN_LIMITS else None
    manifest = {
        "experiment": rag6.VERSION, "protocol": E0_FILE,
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
        "complex_paintable_limit_exclusive": paintable_limit,
        "complex_paintable_pass": paintable_gate,
        "source_edge_retention_at_least_75_percent": edge_gate,
        "source_to_logical": result["source_to_logical"],
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
        "complex_paintable_gate": paintable_gate,
        "complex_strong_source_edge_gate": edge_gate,
        "source_edge_retained_fraction": metric["strong_source_contrast"]["retained_fraction"],
        "main_surfaces": main_count,
        "source_graph_components": int(result["counts"]["graph_regions"]),
        "source_edge_graph_patches": int(result["counts"]["patches"]),
        "original_edge_component_count": int(result["counts"]["edge_components"]),
        "paintable_components": paintable_count,
        "protected_detail_components": int(result["counts"]["detail_components"]),
        "protected_detail_pixels": int(result["counts"]["detail_pixels"]),
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
        raise RuntimeError("BLOCKED_RAG6_UNPINNED_ENGINE")
    if tuple(colors[6]) != (255, 255, 255):
        raise RuntimeError("BLOCKED_RAG6_GAME_WHITE_MISMATCH")
    results = [single(root, source, colors, output, i)
               for i, source in enumerate(SOURCES)]
    manifests, timings = zip(*results)
    numeric_pass = sum(m["numeric_screen"] == "PASS_NUMERIC_ONLY" for m in manifests)
    detail_all = all(m["metrics"]["counts"]["detail_pixels"] > 0 for m in manifests)
    complex_pass = all(m["complex_main_surface_count_pass"] is True
                       for m in manifests if m["complex_main_surface_limit_exclusive"])
    paintable_pass = all(m["complex_paintable_pass"] is True
                         for m in manifests if m["complex_paintable_limit_exclusive"])
    edge_pass = all(m["source_edge_retention_at_least_75_percent"] is True
                    for m in manifests if m["complex_paintable_limit_exclusive"])
    summary = {
        "experiment": rag6.VERSION,
        "e0_git_blob_sha1": E0_BLOB,
        "source_count": len(manifests),
        "source_paths": list(SOURCES),
        "numeric_pass_count": numeric_pass,
        "numeric_gate": "PASS" if numeric_pass >= 2 else "FAIL",
        "wV_rgb_mae_gate": "PASS" if manifests[0]["candidate_to_baseline_rgb_mae_ratio"] <= 1.15 else "FAIL",
        "complex_main_surface_gate": "PASS" if complex_pass else "FAIL",
        "complex_paintable_gate": "PASS" if paintable_pass else "FAIL",
        "complex_strong_source_edge_gate": "PASS" if edge_pass else "FAIL",
        "detail_nonempty_all_dev": detail_all,
        "source_patch_total": sum(m["metrics"]["counts"]["patches"] for m in manifests),
        "paintable_components_total": sum(m["metrics"]["counts"]["paintable_components"] for m in manifests),
        "e2_status": "SOURCE_ONLY_NOT_GAME",
        "visual_quality": "PENDING_ARTIFACT_REVIEW",
        "research_acceptance": "PENDING_VISUAL_AND_SYNTHETIC_REVIEW",
        "native_egret": "NOT_RUN", "formal_s4": "BLOCKED",
        "game_chalk": "NOT_RUN", "no_legacy_art": True,
        "runtime": list(timings),
    }
    (output / "00_RAG6_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
