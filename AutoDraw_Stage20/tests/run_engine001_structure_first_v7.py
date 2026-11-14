#!/usr/bin/env python3
"""ENGINE001_STRUCTURE_FIRST_V7: preregistered LINE-ONLY exploratory contour paths.

This intentionally does not implement full multi-color fills and cannot pass
recognizability, native renderer, or exact game CHALK gates.
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

EXPERIMENT = "ENGINE001_STRUCTURE_FIRST_V7"
MIN_ARC = 12.0
EPSILON = 0.65
MAX_POINTS = 128
MAX_STROKES = 400
MAX_VERTICES = 2500
WIDTH_PARAM = 2


def edge_mask(source: np.ndarray) -> np.ndarray:
    if source.dtype != np.uint8 or source.ndim != 3 or source.shape[2] != 3:
        raise ValueError("Expected RGB uint8 source crop")
    gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY)
    return cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0),
                     60, 120, L2gradient=True) != 0


def plan_line_only(source: np.ndarray, offset: tuple[int, int]) -> tuple[list[dict], dict, np.ndarray]:
    edges = edge_mask(source)
    contours, _ = cv2.findContours(edges.astype(np.uint8),
                                   cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    paths = []
    rejects = {"short_arc": 0, "short_or_degenerate_polyline": 0,
               "additional_split_segments": 0}
    total_length = 0.0
    for index, contour in enumerate(contours):
        if cv2.arcLength(contour, False) < MIN_ARC:
            rejects["short_arc"] += 1
            continue
        approx = cv2.approxPolyDP(contour, EPSILON, False).reshape(-1, 2)
        if len(approx) < 2 or cv2.arcLength(approx.reshape(-1, 1, 2), False) < MIN_ARC:
            rejects["short_or_degenerate_polyline"] += 1
            continue
        segments = [approx[s:min(s+MAX_POINTS, len(approx))]
                    for s in range(0, len(approx)-1, MAX_POINTS-1)]
        rejects["additional_split_segments"] += max(0, len(segments)-1)
        for segment in segments:
            if len(segment) < 2:
                continue
            length = float(np.linalg.norm(np.diff(segment.astype(float), axis=0), axis=1).sum())
            rgb = tuple(int(v) for v in np.median(
                source[segment[:, 1], segment[:, 0]], axis=0).round())
            pts = [{"x": float(x+offset[0]), "y": float(y+offset[1])}
                   for x, y in segment]
            paths.append({
                "strokeId": f"v7-edge-{len(paths)}",
                "width": WIDTH_PARAM,
                "points": pts, "colorRgb": rgb,
                "length_logical": length, "contour_index": index,
            })
            total_length += length
    vertices = sum(len(s["points"]) for s in paths)
    if len(paths) > MAX_STROKES or vertices > MAX_VERTICES:
        raise ValueError(f"V7 prereg quota exceeded: {len(paths)} strokes/{vertices} vertices")
    if any(len(s["points"]) < 2 or len(s["points"]) > MAX_POINTS for s in paths):
        raise ValueError("Invalid per-stroke point count")
    if any(not (offset[0] <= p["x"] < offset[0] + source.shape[1] and
                offset[1] <= p["y"] < offset[1] + source.shape[0])
           for st in paths for p in st["points"]):
        raise ValueError("Invalid stroke coordinate")
    summary = {
        "raw_contours": len(contours),
        "rejected_short_arc": rejects["short_arc"],
        "rejected_short_or_degenerate_polyline": rejects["short_or_degenerate_polyline"],
        "extra_split_segments": rejects["additional_split_segments"],
        "accepted_paths": len(paths), "accepted_vertices": vertices,
        "total_path_length_logical": total_length,
    }
    return paths, summary, edges


def preview_paths(source: np.ndarray, paths: list[dict],
                  offset: tuple[int, int], edges: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    rgb = np.full_like(source, 255)
    painted = np.zeros(edges.shape, dtype=np.uint8)
    for stroke in paths:
        pts = np.asarray([[round(p["x"]-offset[0]), round(p["y"]-offset[1])]
                          for p in stroke["points"]], dtype=np.int32)
        cv2.polylines(painted, [pts], False, 255, 2, cv2.LINE_AA)
        cv2.polylines(rgb, [pts], False, stroke["colorRgb"], 2, cv2.LINE_AA)
    mask = painted > 0
    close = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), dtype=np.uint8)).astype(bool)
    matched = int(np.count_nonzero(edges & close))
    target = int(np.count_nonzero(edges))
    stats = {
        "source_edge_pixels": target,
        "edge_pixels_within1px_of_preview": matched,
        "edge_coverage_proxy": matched / target if target else None,
        "preview_drawn_pixels": int(mask.sum()),
        "preview_pixels_not_on_exact_edge": int(np.count_nonzero(mask & ~edges)),
    }
    return rgb, painted, stats


def run(workspace: Path, output: Path) -> dict:
    labels, metadata, logical = source_palette(workspace)
    # source_palette() checks the original 97,308-byte Git blob fail-closed.
    x, y = metadata["paste_xy"]
    width, height = metadata["resized_size"]
    source = np.asarray(logical, dtype=np.uint8)[y:y+height, x:x+width]
    paths, plan_stats, edges = plan_line_only(source, (x, y))
    image, painted, preview_stats = preview_paths(source, paths, (x, y), edges)
    output.mkdir(parents=True, exist_ok=True)
    derived = {}
    for name, arr in [
        ("source.png", source),
        ("edges.png", edges.astype(np.uint8)*255),
        ("v7-line-only-proxy.png", image),
        ("v7-line-mask.png", painted),
    ]:
        dest = output/name
        Image.fromarray(arr).save(dest)
        derived[name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    (output/"paths.json").write_text(
        json.dumps(paths, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    report = {
        "experiment_id": EXPERIMENT,
        "status": "OFFLINE_EXPLORATORY_PATH_PREVIEW_NOT_NATIVE",
        "source": metadata,
        "statistics": {**plan_stats, **preview_stats},
        "derived_png_sha256": derived,
        "paths_sha256": hashlib.sha256((output/"paths.json").read_bytes()).hexdigest(),
        "quality": {
            "recognizability": "NOT_PASSED_BY_PREVIEW",
            "native_egret": "NOT_RUN",
            "exact_chalk": None,
        },
    }
    (output/"report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.workspace.resolve(), args.output_dir.resolve())
    print(json.dumps(report["statistics"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
