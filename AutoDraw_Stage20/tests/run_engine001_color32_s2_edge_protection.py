#!/usr/bin/env python3
"""ENGINE-001 COLOR32-S2: source-only edge-protected region reduction. NO Egret/CHALK."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from skimage import color, filters, measure, segmentation

from run_engine001_palette32_region_study import (
    SOURCE_SHA, ROI_WH, nearest32, palette_lab, quality, read_palette,
    read_source, sha, tiny_region_merge, topology, thumbnail_sheet,
)

EXP = "ENGINE001_COLOR32_S2_EDGE_PROTECTION_SOURCE_ONLY"
AREA, EXTRA, PASSES = 8, 5.0, 2


def strong_edges(source: np.ndarray) -> tuple[np.ndarray, float]:
    gradient = filters.sobel(color.rgb2gray(source / 255.0))
    positive = gradient[gradient > 0]
    threshold = float(np.percentile(positive, 90)) if positive.size else float("inf")
    return gradient >= threshold, threshold


def protected_merge(source: np.ndarray, indices: np.ndarray, palette: np.ndarray,
                    protected: np.ndarray) -> tuple[np.ndarray, dict]:
    """Original E rules plus rejection of any touching protected source pixel."""
    if (indices.shape != ROI_WH[::-1] or source.shape != (*ROI_WH[::-1], 3)
            or protected.shape != indices.shape or protected.dtype != np.bool_
            or indices.dtype != np.uint8 or indices.max() >= len(palette)):
        raise ValueError("BLOCKED_INVALID_S2_INPUT")
    out = indices.copy()
    h, w = indices.shape
    lab = color.rgb2lab(source / 255.0)
    plab = palette_lab(palette)
    de = color.deltaE_ciede2000(lab[:, :, None, :], plab[None, None, :, :])
    stats = {"merged_per_pass": [], "edge_blocked_per_pass": []}
    for _ in range(PASSES):
        components = measure.label(out, connectivity=1, background=-1)
        regions = sorted(measure.regionprops(components), key=lambda r: (r.area, r.label))
        merged = blocked = 0
        for reg in regions:
            if reg.area > AREA:
                continue
            xy = reg.coords
            ys, xs = xy[:, 0], xy[:, 1]
            original = int(out[ys[0], xs[0]])
            # Must reject entire region to avoid cutting it into novel fragments.
            if np.any(protected[ys, xs]):
                blocked += 1
                continue
            member = components == reg.label
            contacts = Counter()
            for y, x in xy:
                for yy, xx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                    if 0 <= yy < h and 0 <= xx < w and not member[yy, xx]:
                        contacts[int(out[yy, xx])] += 1
            baseline = float(de[ys, xs, original].mean())
            scored = []
            for candidate, shared in contacts.items():
                if candidate == original:
                    continue
                delta = float(de[ys, xs, candidate].mean() - baseline)
                if delta <= EXTRA:
                    scored.append((delta, -shared, candidate))
            if scored:
                scored.sort()
                out[ys, xs] = scored[0][2]
                merged += 1
        stats["merged_per_pass"].append(merged)
        stats["edge_blocked_per_pass"].append(blocked)
        if not merged:
            break
    if np.any(out[protected] != indices[protected]):
        raise AssertionError("protected source pixels changed")
    return out, stats


def overlap(idx: np.ndarray, edges: np.ndarray) -> float:
    if not np.any(edges):
        raise ValueError("no source strong edges")
    bounds = segmentation.find_boundaries(idx, mode="outer")
    return float(np.count_nonzero(bounds & edges) / np.count_nonzero(edges) * 100)


def source_gate(b: dict, e: dict, g: dict) -> dict:
    lost = max(0.0, b["edge_overlap_percent"] - e["edge_overlap_percent"])
    restored = g["edge_overlap_percent"] - e["edge_overlap_percent"]
    reduction = 1 - g["components"]["all_4_connected_components"] / b["components"]["all_4_connected_components"]
    edge_pass = restored >= max(0.875, lost / 2)
    component_pass = reduction >= 0.25
    color_pass = g["quality"]["mean_delta_e00"] <= e["quality"]["mean_delta_e00"] + 0.1
    return {"edge_restored_pp": restored, "edge_loss_B_to_E_pp": lost,
            "component_reduction_vs_B": reduction,
            "edge_gate": edge_pass, "component_gate": component_pass,
            "color_gate": color_pass, "passed": bool(edge_pass and component_pass and color_pass)}


def run(source_path: Path, palette_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("refusing to overwrite S2 artifacts")
    _, source = read_source(source_path)
    palette = read_palette(palette_path)
    b = nearest32(source, palette)
    e, e_changes = tiny_region_merge(source, b, palette,
                                      max_area=AREA, max_extra_delta_e00=EXTRA, iterations=PASSES)
    edges, threshold = strong_edges(source)
    g, stats = protected_merge(source, b, palette, edges)
    variants = {}
    output.mkdir(parents=True)
    for name, idx in (("B_frozen_direct32", b), ("E_frozen_regularized32", e),
                      ("G_edge_protected32", g)):
        rgb = palette[idx]
        Image.fromarray(rgb, "RGB").save(output / (name + ".png"))
        Image.fromarray(idx, "L").save(output / (name + "_indices.png"))
        variants[name] = {"components": topology(idx), "quality": quality(source, rgb),
                          "edge_overlap_percent": overlap(idx, edges),
                          "changed_from_B_pixels": int(np.count_nonzero(idx != b)),
                          "used_palette_indices": [int(x) for x in np.unique(idx)]}
    Image.fromarray((edges.astype(np.uint8) * 255), "L").save(output / "source_edge_protection.png")
    thumbnail_sheet([source, palette[b], palette[e], palette[g]],
                    ["Source", "B direct32", "E frozen", "G edge protected"],
                    output / "comparison.png")
    gate = source_gate(variants["B_frozen_direct32"], variants["E_frozen_regularized32"],
                       variants["G_edge_protected32"])
    report = {
        "experiment": EXP,
        "status": "SOURCE_GATE_PASS_MODEL_ONLY" if gate["passed"] else "SOURCE_GATE_FAIL_MODEL_ONLY",
        "baseline_commit": "084a726294e5622fa0aa207408121fbfe17671fe",
        "source_sha256": SOURCE_SHA, "palette_sha256": sha(palette_path),
        "roi_wh": list(ROI_WH),
        "parameters": {"max_area": AREA, "max_extra_delta_e00": EXTRA,
                       "iterations": PASSES, "strong_edge_method": "sobel(rgb2gray(source/255))",
                       "strong_edge_percentile_positive": 90,
                       "component_connectivity": 4},
        "edge_threshold": threshold, "protected_pixels": int(edges.sum()),
        "frozen_E_merges_per_pass": e_changes, "G_merge_stats": stats,
        "variants": variants, "source_gate": gate,
        "actual_game_swatch_count": 32, "dither_used": False,
        "V44B_detail_410_untouched": True, "native_Egret_fill": "NOT_RUN",
        "E4_game": "NOT_RUN", "E5_independent": "NOT_RUN",
        "exact_CHALK": None, "production_accepted": False,
    }
    report["report_linked_SHA256"] = {p.name: sha(p) for p in sorted(output.glob("*.png"))}
    (output / "report.json").write_text(json.dumps(
        report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--palette", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.source, args.palette, args.output)
    print(json.dumps({"experiment": EXP, "status": result["status"],
                      "source_gate": result["source_gate"],
                      "variant_scores": {k: {"components": v["components"]["all_4_connected_components"],
                                            "edge_overlap_percent": v["edge_overlap_percent"],
                                            "delta_e00": v["quality"]["mean_delta_e00"]}
                                         for k, v in result["variants"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
