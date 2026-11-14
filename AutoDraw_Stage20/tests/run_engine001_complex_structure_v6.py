#!/usr/bin/env python3
"""ENGINE001_COMPLEX_STRUCTURE_V6: preregistered read-only structure diagnostics.

Exploratory edge metrics only. No drawing plan, game CHALK or recognition PASS.
Protocol: docs/ENGINE001_COMPLEX_STRUCTURE_V6_PROTOCOL_2026-11-14.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_complex_holdout_v5 import source_palette

EXPERIMENT = "ENGINE001_COMPLEX_STRUCTURE_V6"
SOURCE_SHA256 = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
EDGE_LOW = 60
EDGE_HIGH = 120
EDGE_TOLERANCE_PX = 1
MIN_COMPONENT_PX = 12
COMPONENT_RETAIN_FRACTION = 0.5


def extract_edges(rgb: np.ndarray) -> np.ndarray:
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("Expected uint8 RGB array")
    grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(grey, (3, 3), 0)
    return cv2.Canny(blurred, EDGE_LOW, EDGE_HIGH, L2gradient=True) != 0


def compare_edges(source_edges: np.ndarray, palette_edges: np.ndarray) -> dict:
    if (source_edges.shape != palette_edges.shape or
            source_edges.ndim != 2 or
            source_edges.dtype != np.dtype(bool) or
            palette_edges.dtype != np.dtype(bool)):
        raise ValueError("Expected matching two-dimensional bool edge masks")
    near_palette = cv2.dilate(
        palette_edges.astype(np.uint8), np.ones((3, 3), dtype=np.uint8)
    ).astype(bool)
    preserved = source_edges & near_palette
    num, components, stats, _ = cv2.connectedComponentsWithStats(
        source_edges.astype(np.uint8), connectivity=8
    )
    eligible = []
    for label in range(1, num):
        count = int(stats[label, cv2.CC_STAT_AREA])
        if count < MIN_COMPONENT_PX:
            continue
        retained = int(np.count_nonzero(preserved & (components == label)))
        eligible.append({
            "pixels": count,
            "matched_pixels": retained,
            "fraction": retained / count,
            "retained": retained / count >= COMPONENT_RETAIN_FRACTION
        })
    n = int(np.count_nonzero(source_edges))
    m = int(np.count_nonzero(preserved))
    return {
        "source_edge_pixels": n,
        "palette_edge_pixels": int(np.count_nonzero(palette_edges)),
        "source_edges_matched_within_1px": m,
        "source_edge_recall_within_1px": m / n if n else None,
        "missing_source_edge_pixels": n - m,
        "eligible_source_components_ge12": len(eligible),
        "components_retained_ge50pct": sum(x["retained"] for x in eligible),
        "components_lost_ge50pct": sum(not x["retained"] for x in eligible),
        "component_details": eligible
    }


def reconstruct_palette(labels: np.ndarray, palette: dict) -> np.ndarray:
    colors = {int(k): np.asarray(v, dtype=np.uint8)
              for k, v in palette["palette_rgb"].items()}
    if labels.ndim != 2:
        raise ValueError("Labels must be 2D")
    if set(np.unique(labels).tolist()) != set(colors):
        raise ValueError("Palette color mapping mismatch")
    out = np.zeros((*labels.shape, 3), dtype=np.uint8)
    for key, rgb in colors.items():
        out[labels == key] = rgb
    return out


def roi_bounds(metadata: dict, canvas_shape: tuple[int, int]) -> tuple[slice, slice]:
    x, y = map(int, metadata["paste_xy"])
    width, height = map(int, metadata["resized_size"])
    if min(x, y) < 0 or min(width, height) <= 0:
        raise ValueError("Invalid source ROI")
    if x + width > canvas_shape[1] or y + height > canvas_shape[0]:
        raise ValueError("ROI outside logical canvas")
    return slice(y, y + height), slice(x, x + width)


def write_png(out: Path, filename: str, data: np.ndarray) -> str:
    image = Image.fromarray(data)
    path = out / filename
    image.save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(workspace: Path, output: Path) -> dict:
    labels, metadata, logical = source_palette(workspace)
    if metadata["png_sha256"] != SOURCE_SHA256:
        raise ValueError("Source SHA256 mismatch")
    rgb = np.asarray(logical, dtype=np.uint8)
    reconstructed = reconstruct_palette(labels, metadata)
    ys, xs = roi_bounds(metadata, labels.shape)
    original_crop = rgb[ys, xs]
    palette_crop = reconstructed[ys, xs]
    if original_crop.size == 0 or original_crop.shape != palette_crop.shape:
        raise ValueError("Invalid crop")
    original_edges = extract_edges(original_crop)
    palette_edges = extract_edges(palette_crop)
    metrics = compare_edges(original_edges, palette_edges)
    palette_neighbor = cv2.dilate(
        palette_edges.astype(np.uint8), np.ones((3, 3), dtype=np.uint8)
    ).astype(bool)
    missing = original_edges & ~palette_neighbor
    output.mkdir(exist_ok=True, parents=True)
    sha = {}
    for name, data in [
        ("source-logical-roi.png", original_crop),
        ("v5-palette-logical-roi.png", palette_crop),
        ("source-edges.png", original_edges.astype(np.uint8) * 255),
        ("v5-palette-edges.png", palette_edges.astype(np.uint8) * 255),
        ("missing-v5-edges.png", missing.astype(np.uint8) * 255),
    ]:
        sha[name] = write_png(output, name, data)
    report = {
        "experiment_id": EXPERIMENT,
        "status": "DIAGNOSTIC_COMPLETE_NOT_RECOGNITION_PASS",
        "protocol": "docs/ENGINE001_COMPLEX_STRUCTURE_V6_PROTOCOL_2026-11-14.md",
        "baseline": "frozen V5 eight-color MEDIANCUT geometry",
        "source": metadata,
        "roi": {
            "width": original_crop.shape[1],
            "height": original_crop.shape[0],
            "paste_xy": metadata["paste_xy"],
        },
        "parameters": {
            "canny_low": EDGE_LOW, "canny_high": EDGE_HIGH,
            "gaussian_kernel": [3, 3], "l2gradient": True,
            "match_tolerance_logical_px": EDGE_TOLERANCE_PX,
            "min_component_pixels": MIN_COMPONENT_PX,
            "component_retain_fraction": COMPONENT_RETAIN_FRACTION,
        },
        "metrics": metrics,
        "derived_png_sha256": sha,
        "quality": {
            "v5_user_visual_judgment": "FAIL_UNRECOGNIZABLE",
            "v6_recognition": "NOT_TESTED",
            "game_chalk_exact": None,
            "native_egret_v6": "NOT_RUN",
        },
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=Path("."))
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    report = run(args.workspace.resolve(), args.output_dir.resolve())
    print(json.dumps({
        "experiment_id": report["experiment_id"],
        "status": report["status"],
        "source_sha256": report["source"]["png_sha256"],
        "roi": report["roi"],
        "metrics": {k: v for k, v in report["metrics"].items()
                    if k != "component_details"},
        "derived_png_sha256": report["derived_png_sha256"]
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
