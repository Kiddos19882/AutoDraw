#!/usr/bin/env python3
"""ENGINE-001 COLOR32-S2b, RGB-gradient source gate only; no Egret/CHALK."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

import cv2
import numpy as np
import skimage
import PIL
from PIL import Image

from run_engine001_palette32_region_study import (
    nearest32, quality, read_palette, read_source, sha, tiny_region_merge,
    thumbnail_sheet, topology,
)
from run_engine001_color32_s2_edge_protection import (
    protected_merge, s1_rgb_gradient_overlap, strong_edges, overlap,
)

EXP = "ENGINE001_COLOR32_S2B_RGB_EDGE_SOURCE_ONLY"
SOURCE_GATE_MIN_RECOVERY_PP = 0.875
MIN_COMPONENT_REDUCTION = 0.35
MAX_COLOR_DELTA_ABOVE_E = 0.1


def assess(b: dict, e: dict, g: dict, protected_unchanged: bool) -> dict:
    loss = max(0.0, b["rgb_gradient_overlap_percent"] - e["rgb_gradient_overlap_percent"])
    recovery = g["rgb_gradient_overlap_percent"] - e["rgb_gradient_overlap_percent"]
    reduction = (1.0 - g["components"]["all_4_connected_components"]
                 / b["components"]["all_4_connected_components"])
    checks = {
        "rgb_edge_recovery": bool(recovery >= max(SOURCE_GATE_MIN_RECOVERY_PP, 0.5 * loss)),
        "component_reduction": bool(reduction >= MIN_COMPONENT_REDUCTION),
        "color_error": bool(g["quality"]["mean_delta_e00"]
                            <= e["quality"]["mean_delta_e00"] + MAX_COLOR_DELTA_ABOVE_E),
        "protected_pixels_unchanged": bool(protected_unchanged),
    }
    return {
        "rgb_edge_B_to_E_loss_pp": loss,
        "rgb_edge_G_recovery_pp": recovery,
        "component_reduction_fraction_vs_B": reduction,
        "checks": checks,
        "passed": all(checks.values()),
    }


def run(source_path: Path, palette_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_OUTPUT_EXISTS: frozen results must not be overwritten")
    _, source = read_source(source_path)
    palette = read_palette(palette_path)
    b = nearest32(source, palette)
    e, e_merges = tiny_region_merge(
        source, b, palette, max_area=8, max_extra_delta_e00=5.0, iterations=2)
    mask, threshold = strong_edges(source)
    g, g_merges = protected_merge(source, b, palette, mask)
    if not np.array_equal(g[mask], b[mask]):
        raise AssertionError("S2b protected mask mutated")
    output.mkdir(parents=True)
    variants = {}
    for name, index in (("B_direct32", b), ("E_regularized32", e),
                        ("G_edge_protected32", g)):
        rgb = palette[index]
        Image.fromarray(rgb).save(output / (name + ".png"))
        Image.fromarray(index).save(output / (name + "_indices.png"))
        variants[name] = {
            "quality": quality(source, rgb),
            "components": topology(index),
            "rgb_gradient_overlap_percent": s1_rgb_gradient_overlap(source, rgb),
            "s2_index_boundary_overlap_diagnostic_percent": overlap(index, mask),
            "changed_vs_B": int(np.count_nonzero(index != b)),
            "palette_indices": [int(x) for x in np.unique(index)],
        }
        if not np.array_equal(rgb, palette[index]) or int(index.max()) >= 32:
            raise AssertionError("S2b non-game palette color")
    Image.fromarray((mask * 255).astype(np.uint8)).save(output / "protected_source_edges.png")
    thumbnail_sheet([source, palette[b], palette[e], palette[g]],
                    ["Original", "B control", "E control", "G edge protected"],
                    output / "comparison.png")
    gate = assess(variants["B_direct32"], variants["E_regularized32"],
                  variants["G_edge_protected32"], bool(np.array_equal(g[mask], b[mask])))
    report = {
        "experiment": EXP,
        "github_sha": os.environ.get("GITHUB_SHA") or None,
        "github_run_id": os.environ.get("GITHUB_RUN_ID") or None,
        "versions": {"Python": platform.python_version(), "numpy": np.__version__, "Pillow": PIL.__version__, "scikit_image": skimage.__version__, "OpenCV": cv2.__version__},
        "status": "SOURCE_GATE_PASS_VISUAL_PENDING" if gate["passed"] else "SOURCE_GATE_FAIL",
        "input_source_sha256": sha(source_path),
        "input_palette_sha256": sha(palette_path),
        "roi_wh": [150, 240],
        "settings": {
            "game_colors": 32, "max_area": 8, "extra_delta_e00": 5.0,
            "merge_passes": 2, "protected_sobel_positive_percentile": 90,
            "s1_rgb_edge_percentile": 90, "component_connectivity": 4,
            "min_rgb_recovery_pp": SOURCE_GATE_MIN_RECOVERY_PP,
            "min_component_reduction": MIN_COMPONENT_REDUCTION,
            "max_color_delta_above_E": MAX_COLOR_DELTA_ABOVE_E,
        },
        "protected_pixel_count": int(mask.sum()),
        "strong_edge_threshold": threshold,
        "original_E_accepted_merge_counts": e_merges,
        "G_merge_stats": g_merges,
        "variants": variants, "source_gate": gate,
        "visual_review": "PENDING",
        "native_Egret_fill": "NOT_RUN", "E4_game": "NOT_RUN",
        "E5_independent": "NOT_RUN", "exact_CHALK": None,
        "V44B_410_contours_preserved": True,
        "production_accepted": False,
    }
    report["file_sha256"] = {p.name: sha(p) for p in sorted(output.glob("*.png"))}
    (output / "report.json").write_text(json.dumps(
        report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--palette", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = run(args.source, args.palette, args.output)
    print(json.dumps({
        "status": report["status"],
        "source_gate": report["source_gate"],
        "metrics": {name: {
            "components": v["components"]["all_4_connected_components"],
            "rgb_gradient_overlap_percent": v["rgb_gradient_overlap_percent"],
            "delta_e00": v["quality"]["mean_delta_e00"]
        } for name, v in report["variants"].items()}
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
