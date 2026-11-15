#!/usr/bin/env python3
"""ENGINE001_ANILINES_BRUSH1_PATHS_V17: opt-in source-bound offline research.

Not native Egret, not a fill planner, not a game CHALK estimate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from skimage.morphology import skeletonize

SOURCE_SHA = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
ANI_SHA = "2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b"
INK = (49, 38, 43)
NEIGHBORS = tuple((dx, dy) for dy in (-1, 0, 1)
                  for dx in (-1, 0, 1) if dx or dy)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def undirected(a, b):
    return (a, b) if a < b else (b, a)


def trace_graph(skeleton: np.ndarray):
    if skeleton.shape != (320, 200) or skeleton.dtype != np.dtype(bool):
        raise ValueError("Expected original 200x320 skeleton")
    pixels = {(int(x), int(y)) for y, x in np.argwhere(skeleton)}
    neighbors = {
        p: sorted((p[0] + dx, p[1] + dy) for dx, dy in NEIGHBORS
                  if (p[0] + dx, p[1] + dy) in pixels)
        for p in pixels
    }
    degrees = {p: len(adj) for p, adj in neighbors.items()}
    used = set()
    chains = []

    def walk(a, b):
        result = [a, b]
        used.add(undirected(a, b))
        prev, cur = a, b
        while degrees[cur] == 2:
            nxt = neighbors[cur][0] if neighbors[cur][1] == prev else neighbors[cur][1]
            edge = undirected(cur, nxt)
            if edge in used:
                break
            used.add(edge)
            result.append(nxt)
            prev, cur = cur, nxt
        return result

    for p in sorted(q for q in pixels if degrees[q] != 2):
        for q in neighbors[p]:
            if undirected(p, q) not in used:
                chains.append(walk(p, q))
    # Pure cycles have only degree-2 nodes; still need to trace every edge.
    for p in sorted(pixels):
        for q in neighbors[p]:
            if undirected(p, q) not in used:
                chains.append(walk(p, q))
    all_edges = {undirected(p, q) for p, adj in neighbors.items() for q in adj}
    if used != all_edges:
        raise ValueError("Some skeleton graph edges not visited")
    return chains, degrees, len(all_edges)


def length(points) -> float:
    if len(points) < 2:
        return 0.
    a = np.asarray(points, dtype=float)
    return float(np.linalg.norm(a[1:] - a[:-1], axis=1).sum())


def simplify(points, epsilon=0.6):
    if len(points) < 3:
        return list(points)
    a = np.asarray(points, dtype=float)
    start, end = a[0], a[-1]
    if np.allclose(start, end):
        distances = np.linalg.norm(a[1:-1] - start, axis=1)
    else:
        vector = end - start
        t = np.clip(((a[1:-1] - start) @ vector) / (vector @ vector), 0, 1)
        distances = np.linalg.norm(a[1:-1] - (start + np.outer(t, vector)), axis=1)
    if len(distances) == 0 or float(distances.max()) <= epsilon:
        return [points[0], points[-1]]
    index = int(np.argmax(distances)) + 1
    return simplify(points[:index+1], epsilon)[:-1] + simplify(points[index:], epsilon)


def run(source: Path, anilines: Path, output: Path):
    if sha(source) != SOURCE_SHA or source.stat().st_size != 97308:
        raise ValueError("Pinned original SHA/size mismatch")
    if sha(anilines) != ANI_SHA:
        raise ValueError("Pinned AniLines output SHA mismatch")
    with Image.open(source) as im:
        if im.size != (200, 320):
            raise ValueError("Wrong original dimensions")
        original = np.asarray(im.convert("RGB"))
    with Image.open(anilines) as im:
        if im.size != (200, 320):
            raise ValueError("Wrong AniLines dimensions")
        gray = np.asarray(im.convert("L"))
    mask = gray < 128
    skeleton = skeletonize(mask)
    chains, degrees, graph_edges = trace_graph(skeleton)

    strokes, rejected = [], 0
    splits = 0
    src_forecast = np.zeros((320, 200), dtype=np.uint8)
    total_length = 0.0
    for index, chain in enumerate(chains):
        if length(chain) < 4:
            rejected += 1
            continue
        simplified = simplify(chain, epsilon=0.6)
        if len(simplified) < 2:
            continue
        parts = [simplified[i:min(i+128, len(simplified))]
                 for i in range(0, len(simplified)-1, 127)]
        splits += max(0, len(parts)-1)
        for part in parts:
            if len(part) < 2:
                continue
            logical = [(x*.75+155, y*.75) for x, y in part]
            if any(not (np.isfinite(x) and np.isfinite(y)
                        and 155 <= x < 305 and 0 <= y < 240) for x, y in logical):
                raise ValueError("Out-of-bounds logical coordinate")
            path_length = length(part)
            total_length += path_length
            strokes.append({
                "stroke_id": f"v17-line-{len(strokes)}",
                "origin_chain": index, "brush_width_parameter": 1,
                "color_rgb": list(INK),
                "source_points": [[int(x), int(y)] for x, y in part],
                "logical_points": [[float(x), float(y)] for x, y in logical],
                "source_path_length": path_length,
            })
            cv2.polylines(src_forecast,
                          [np.asarray(part, dtype=np.int32).reshape(-1, 1, 2)],
                          False, 255, 1, cv2.LINE_8)

    vertices = sum(len(s["logical_points"]) for s in strokes)
    if len(strokes) > 4000 or vertices > 30000:
        raise ValueError("Predeclared V17 stroke/vertex quota exceeded")
    canvas = np.full((240, 460, 3), 255, dtype=np.uint8)
    overlap = np.zeros((240, 460), dtype=np.int32)
    for stroke in strokes:
        p = np.asarray([[round(x), round(y)] for x, y in stroke["logical_points"]],
                       dtype=np.int32).reshape(-1, 1, 2)
        if not 2 <= len(p) <= 128:
            raise ValueError("Invalid stroke point count")
        cv2.polylines(canvas, [p], False, INK, 1, cv2.LINE_8)
        m = np.zeros((240, 460), dtype=np.uint8)
        cv2.polylines(m, [p], False, 1, 1, cv2.LINE_8)
        overlap += m

    preview = canvas[:, 155:305]
    source_roi = np.asarray(Image.fromarray(original).resize(
        (150, 240), Image.Resampling.LANCZOS))
    overlay = source_roi.copy()
    preview_mask = np.any(preview != 255, axis=2)
    overlay[preview_mask] = preview[preview_mask]
    resized_ani = np.asarray(Image.fromarray(gray).resize(
        (150, 240), Image.Resampling.NEAREST))
    comparison = np.full((240, 450, 3), 255, dtype=np.uint8)
    comparison[:, :150] = source_roi
    comparison[:, 150:300] = np.repeat(resized_ani[:, :, None], 3, axis=2)
    comparison[:, 300:] = preview

    skel_near = cv2.dilate((src_forecast > 0).astype(np.uint8),
                          np.ones((3, 3), np.uint8)).astype(bool)
    ani_near = cv2.dilate(mask.astype(np.uint8),
                         np.ones((3, 3), np.uint8)).astype(bool)
    resized_lines = np.asarray(Image.fromarray(mask.astype(np.uint8)*255).resize(
        (150, 240), Image.Resampling.NEAREST)) > 0
    near_preview = cv2.dilate(preview_mask.astype(np.uint8),
                             np.ones((3, 3), np.uint8)).astype(bool)
    report = {
        "experiment": "ENGINE001_ANILINES_BRUSH1_PATHS_V17",
        "status": "OFFLINE_EXPLORATORY_NON_NATIVE",
        "source_sha256": SOURCE_SHA,
        "anilines_sha256": ANI_SHA,
        "metrics": {
            "binary_line_pixels": int(mask.sum()),
            "skeleton_pixels": int(skeleton.sum()),
            "graph_edges": graph_edges,
            "graph_branch_points_ge3": sum(v >= 3 for v in degrees.values()),
            "raw_chains": len(chains),
            "discarded_short_chains": rejected,
            "retained_chains": len(chains) - rejected,
            "additional_segments": splits,
            "stroke_paths": len(strokes),
            "synthetic_vertices": vertices,
            "source_polyline_length": total_length,
            "skeleton_pixels_supported_within_1_source_px": int((skeleton & skel_near).sum()),
            "skeleton_support_fraction": float((skeleton & skel_near).sum() / max(1, skeleton.sum())),
            "source_path_raster_foreign_line_pixels_exact": int(((src_forecast > 0) & ~mask).sum()),
            "source_path_raster_foreign_line_pixels_beyond1px": int(((src_forecast > 0) & ~ani_near).sum()),
            "logical_preview_colored_pixels": int(preview_mask.sum()),
            "logical_rounding_overpaint_pixels": int((overlap > 1).sum()),
            "logical_ani_nearest_line_pixels": int(resized_lines.sum()),
            "logical_ani_recall_within_1px_of_preview": float((resized_lines & near_preview).sum() / max(1, resized_lines.sum())),
        },
        "not_tested": ["native Egret brush1 support", "suit semantic precision",
                       "game exact CHALK", "fill geometry", "independent E5"],
    }
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refusing to overwrite evidence")
    output.mkdir(parents=True, exist_ok=True)
    images = {
        "source-pinned.png": original, "anilines-output.png": gray,
        "source-skeleton.png": (skeleton*255).astype(np.uint8),
        "source-path-raster.png": src_forecast,
        "logical-460x240-contours.png": canvas,
        "contour-roi-150x240.png": preview,
        "contour-overlay-source-roi.png": overlay,
        "source-anilines-v17-comparison.png": comparison,
    }
    report["images_sha256"] = {}
    for name, a in images.items():
        dest = output/name
        Image.fromarray(a).save(dest)
        report["images_sha256"][name] = sha(dest)
    (output/"strokes.json").write_text(
        json.dumps(strokes, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    report["strokes_json_sha256"] = sha(output/"strokes.json")
    (output/"report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--anilines", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args()
    print(json.dumps(run(a.source, a.anilines, a.output)["metrics"],
                     ensure_ascii=False, indent=2))
