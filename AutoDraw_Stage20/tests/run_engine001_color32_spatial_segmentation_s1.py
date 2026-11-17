#!/usr/bin/env python3
"""ENGINE-001 COLOR32-S1: frozen game32 spatial color A/B/C/D source-only.

No production modification, no synthetic swatches, no Egret or game claims.
All region merging constraints were registered before the first run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import skimage
from PIL import Image, ImageDraw
from skimage.segmentation import slic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "preparation"))
from palette_quantization import (
    normalize_palette, quantize_image_to_palette, rgb_to_lab,
    delta_e_ciede2000,
)

EXPERIMENT = "ENGINE001_COLOR32_S1_SPATIAL_SEGMENTATION"
SOURCE_SHA = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
ROI_SIZE = (150, 240)
SLIC_N_SEGMENTS = 400
SLIC_COMPACTNESS = 12
MERGE_MAX_DE00 = 8.0
MERGE_MAX_SHARED_GRADIENT = 0.08
CASES = ("A", "B", "C", "D")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_roi(path: Path) -> Image.Image:
    if not path.is_file() or sha(path) != SOURCE_SHA:
        raise ValueError("COLOR32 original frozen source SHA mismatch")
    with Image.open(path) as img:
        if img.size != (200, 320):
            raise ValueError("COLOR32 original image size drift")
        return img.convert("RGB").resize(ROI_SIZE, Image.Resampling.LANCZOS)


def load_game32(path: Path) -> list[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    colors = doc.get("colors")
    if not isinstance(colors, list) or len(colors) != 32:
        raise ValueError("COLOR32 actual game palette must contain exactly 32 swatches")
    normalized = normalize_palette(colors)
    if len(normalized) != 32 or len({tuple(v["rgb"]) for v in normalized}) != 32:
        raise ValueError("COLOR32 palette duplicates or wrong size")
    return normalized


def legacy_case(roi: Image.Image):
    q = roi.quantize(colors=8, method=Image.Quantize.MEDIANCUT,
                     dither=Image.Dither.NONE)
    indexes = np.asarray(q, dtype=np.int32).copy()
    lut = np.asarray(q.getpalette(), dtype=np.uint8).reshape(-1, 3)
    rgb = lut[indexes]
    return indexes, rgb, [lut[int(i)].tolist() for i in sorted(np.unique(indexes))]


def quantize_regions(medians: np.ndarray, palette):
    if medians.ndim != 2 or medians.shape[1] != 3:
        raise ValueError("COLOR32 invalid region representative shape")
    if not len(medians):
        raise ValueError("COLOR32 empty regions")
    # Apply the existing production-quality CIEDE2000 mapping, not new metric.
    row = Image.fromarray(medians[np.newaxis, :, :].astype(np.uint8), "RGB")
    result = quantize_image_to_palette(row, palette)
    return result.index_map.reshape(-1).astype(np.int32)


def region_medians(source: np.ndarray, regions: np.ndarray):
    if regions.shape != source.shape[:2] or np.min(regions) < 0:
        raise ValueError("COLOR32 region geometry mismatch")
    count = int(regions.max()) + 1
    out = np.zeros((count, 3), dtype=np.uint8)
    for i in range(count):
        vals = source[regions == i]
        if not len(vals):
            raise ValueError("COLOR32 non-contiguous or empty region ID")
        out[i] = np.median(vals, axis=0).astype(np.uint8)
    return out


def superpixels(source: np.ndarray):
    if source.shape != (240, 150, 3) or source.dtype != np.uint8:
        raise ValueError("COLOR32 SLIC source geometry")
    raw = slic(source.astype(np.float64) / 255.0,
               n_segments=SLIC_N_SEGMENTS,
               compactness=SLIC_COMPACTNESS, sigma=0,
               start_label=0, enforce_connectivity=True,
               convert2lab=True, channel_axis=-1)
    ids = np.unique(raw)
    # Re-label defensively; skimage is version-sensitive about sequential IDs.
    label = np.searchsorted(ids, raw).astype(np.int32)
    return label


def normalized_source_gradient(rgb: np.ndarray):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    # Central differences / 8 keep gradient on the original 0..1 scale.
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    return np.hypot(gx, gy)


def merge_adjacent_regions(regions: np.ndarray, original_rgb: np.ndarray):
    """Deterministic adjacent region union; strong source boundaries block.

    Neighboring cells are only merged if current source-region mean ΔE00≤8
    AND mean source Sobel gradient along their shared boundary≤.08.
    """
    if regions.shape != (240, 150) or original_rgb.shape != (240, 150, 3):
        raise ValueError("COLOR32 merge source geometry")
    n = int(regions.max()) + 1
    if not np.array_equal(np.unique(regions), np.arange(n)):
        raise ValueError("COLOR32 region ID gaps")
    lab = rgb_to_lab(original_rgb).reshape(-1, 3)
    flat = regions.ravel()
    counts = np.bincount(flat, minlength=n).astype(np.float64)
    if np.any(counts == 0):
        raise ValueError("COLOR32 empty superpixel")
    means = np.stack([
        np.bincount(flat, weights=lab[:, channel], minlength=n) / counts
        for channel in range(3)], axis=1)
    gradients = normalized_source_gradient(original_rgb)
    edge = {}  # (u,v): (gradient sum, number of touching pixel pairs)
    for left, right, signal in (
        (regions[:, :-1], regions[:, 1:],
         (gradients[:, :-1] + gradients[:, 1:]) / 2),
        (regions[:-1, :], regions[1:, :],
         (gradients[:-1, :] + gradients[1:, :]) / 2),
    ):
        valid = left != right
        aa = left[valid].astype(np.int32)
        bb = right[valid].astype(np.int32)
        gg = signal[valid].astype(np.float64)
        for u, v, g in zip(aa.tolist(), bb.tolist(), gg.tolist()):
            key = (min(u, v), max(u, v))
            old_sum, old_count = edge.get(key, (0.0, 0))
            edge[key] = (old_sum + g, old_count + 1)

    parent = list(range(n))
    active = set(range(n))
    accepted = 0
    # n<=400; rebuilding pair scores is deterministic and bounded, no random.
    while True:
        admissible = []
        for (u, v), (g_sum, g_count) in sorted(edge.items()):
            if u not in active or v not in active or not g_count:
                continue
            mean_boundary = g_sum / g_count
            if mean_boundary > MERGE_MAX_SHARED_GRADIENT:
                continue
            delta = float(delta_e_ciede2000(means[u], means[v]))
            if delta <= MERGE_MAX_DE00:
                admissible.append((delta, u, v))
        if not admissible:
            break
        _, u, v = min(admissible)
        # Stable root: minimum initial region ID survives.
        total = counts[u] + counts[v]
        means[u] = (means[u] * counts[u] + means[v] * counts[v]) / total
        counts[u] = total
        parent[v] = u
        active.remove(v)
        updated = {}
        for (a, b), (g, num) in edge.items():
            a = u if a == v else a
            b = u if b == v else b
            if a == b:
                continue
            pair = (min(a, b), max(a, b))
            old_g, old_n = updated.get(pair, (0.0, 0))
            updated[pair] = (old_g + g, old_n + num)
        edge = updated
        accepted += 1

    def representative(i):
        while parent[i] != i:
            i = parent[i]
        return i
    lookup = np.array([representative(i) for i in range(n)], dtype=np.int32)
    raw = lookup[regions]
    unique = np.unique(raw)
    merged = np.searchsorted(unique, raw).astype(np.int32)
    return merged, {
        "original_slic_superpixels": n,
        "merged_regions": len(unique),
        "accepted_merges": accepted,
        "max_delta_e00": MERGE_MAX_DE00,
        "max_shared_gradient_normalized": MERGE_MAX_SHARED_GRADIENT,
    }


def metrics(rgb: np.ndarray, labels: np.ndarray, source: np.ndarray):
    if rgb.shape != source.shape or labels.shape != source.shape[:2]:
        raise ValueError("COLOR32 metrics geometry drift")
    a = rgb.astype(np.float32)
    b = source.astype(np.float32)
    mae = float(np.abs(a-b).mean())
    # CIEDE00 for all 36k ROI pixels, no approximation.
    dist = delta_e_ciede2000(rgb_to_lab(rgb), rgb_to_lab(source))
    labels = labels.astype(np.int32)
    parts = []
    contour_count = 0
    for class_id in sorted(np.unique(labels).tolist()):
        mask = (labels == class_id).astype(np.uint8)
        _, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        parts.extend(int(x) for x in stats[1:, cv2.CC_STAT_AREA])
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST,
                                       cv2.CHAIN_APPROX_SIMPLE)
        contour_count += len(contours)
    transition = int(np.count_nonzero(labels[:, 1:] != labels[:, :-1]) +
                     np.count_nonzero(labels[1:, :] != labels[:-1, :]))
    grad_original = normalized_source_gradient(source)
    grad_rendered = normalized_source_gradient(rgb)
    hard_original = grad_original >= np.percentile(grad_original, 90)
    hard_rendered = grad_rendered >= np.percentile(grad_rendered, 90)
    return {
        "used_colors": len(np.unique(labels)),
        "RGB_MAE": float(round(mae, 6)),
        "deltaE00_mean": float(round(np.mean(dist), 6)),
        "deltaE00_p95": float(round(np.percentile(dist, 95), 6)),
        "connected_8_components": len(parts),
        "singleton_components": sum(x == 1 for x in parts),
        "components_area_at_most_4": sum(x <= 4 for x in parts),
        "pixels_inside_components_area_at_most_4": sum(x for x in parts if x <= 4),
        "contours_including_holes": contour_count,
        "4_neighbor_color_boundary_transitions": transition,
        "largest_connected_component_pixels": max(parts) if parts else 0,
        "top_decile_source_edge_overlap": float(round(
            np.count_nonzero(hard_original & hard_rendered) /
            max(1, np.count_nonzero(hard_original)), 6)),
        "white_like_enclosed_detail_is_not_automatically_removed": True,
    }


def run(image_path: Path, palette_path: Path, output: Path):
    if output.exists():
        raise ValueError("COLOR32 refuses overwrite of any earlier evidence")
    roi = source_roi(image_path)
    source = np.asarray(roi, dtype=np.uint8)
    palette = load_game32(palette_path)
    game_rgb = np.asarray([entry["rgb"] for entry in palette], dtype=np.uint8)
    data = {}
    a_idx, a_rgb, a_palette = legacy_case(roi)
    data["A"] = (a_idx, a_rgb)
    b = quantize_image_to_palette(roi, palette)
    data["B"] = (b.index_map.astype(np.int32), np.asarray(b.image, dtype=np.uint8))
    slic_map = superpixels(source)
    medians = region_medians(source, slic_map)
    label_slic = quantize_regions(medians, palette)
    c_labels = label_slic[slic_map]
    data["C"] = (c_labels, game_rgb[c_labels])
    merged, merge_meta = merge_adjacent_regions(slic_map, source)
    label_merged = quantize_regions(region_medians(source, merged), palette)
    d_labels = label_merged[merged]
    data["D"] = (d_labels, game_rgb[d_labels])

    output.mkdir(parents=True)
    pictures = []
    summary = {}
    for name in CASES:
        labels, rgb = data[name]
        if labels.shape != (240, 150) or rgb.shape != (240, 150, 3):
            raise ValueError("COLOR32 output shape drift")
        if name != "A" and not np.all(
                np.isin(rgb.reshape(-1, 3).view("V3"),
                        game_rgb.reshape(-1, 3).view("V3"))):
            raise ValueError("COLOR32 synthetic non-game RGB found")
        Image.fromarray(rgb).save(output / f"{name}-color-preview.png")
        summary[name] = metrics(rgb, labels, source)
        np.savez_compressed(output / f"{name}-labels.npz",
                            palette_index_map=labels,
                            palette_rgb=np.array(
                                a_palette if name == "A" else game_rgb,
                                dtype=np.uint8))
        pictures.append(Image.fromarray(rgb))

    def make_sheet(top_only=False):
        choices=[roi]+pictures
        if top_only:
            choices=[x.crop((0, 0, 150, 130)) for x in choices]
        scale=3; pad=14; heading=35
        w,h=choices[0].size
        canvas=Image.new("RGB",(len(choices)*(w*scale+pad)+pad,
                                  h*scale+heading+pad),"#e6e8ed")
        pen=ImageDraw.Draw(canvas)
        for n,(img,title) in enumerate(zip(choices,
                                           ("Original","A MEDIANCUT8",
                                            "B game32 ΔE00","C SLIC",
                                            "D region merge"))):
            x=pad+n*(w*scale+pad)
            pen.text((x+3, 10),title,fill="#191d25")
            canvas.paste(img.resize((w*scale,h*scale),Image.Resampling.NEAREST),
                         (x,heading))
        return canvas

    make_sheet().save(output / "comparison-full.png")
    make_sheet(True).save(output / "comparison-faces.png")
    roi.save(output / "original-source-roi.png")
    manifest = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    report = {
        "experiment": EXPERIMENT,
        "status": "E2_OFFLINE_SOURCE_ONLY_NOT_NATIVE",
        "source_sha256": SOURCE_SHA,
        "actual_game_palette_sha256": sha(palette_path),
        "actual_game_palette_count": 32,
        "palette": [{
            "index":p["index"],"rgb":p["rgb"],"hex":p["hex"]
        } for p in palette],
        "ROI_shape_hw": [240,150],
        "A_legacy_palette_actual_RGB": a_palette,
        "SLIC_parameters": {
            "n_segments": SLIC_N_SEGMENTS,
            "compactness": SLIC_COMPACTNESS,"sigma": 0,
            "enforce_connectivity":True,
        },
        "SLIC_actual_region_count":int(slic_map.max())+1,
        "D_merging":merge_meta,
        "metrics":summary,
        "previous_E3_1838_zone_contours_scope":
            "only legacy MEDIANCUT8 owners4..7, not all 8 color classes",
        "report_linked_SHA256": manifest,
        "true_Egret": "NOT_RUN","live_E4":"NOT_RUN",
        "game_exact_CHALK":None,"E5":"NOT_RUN",
        "production_accepted":False,
        "versions":{
            "Python":platform.python_version(),
            "Pillow":Image.__version__ if hasattr(Image,"__version__") else "unknown",
            "OpenCV":cv2.__version__,
            "NumPy":np.__version__,
            "scikit-image":skimage.__version__,
        },
    }
    (output / "report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({
        "experiment":EXPERIMENT, "SLIC_segments":report["SLIC_actual_region_count"],
        "merged":merge_meta, "metrics":summary,
        "source_only":True,
    },ensure_ascii=False))
    return report


def main():
    ap=argparse.ArgumentParser()
    for arg in ("source","palette","output"):
        ap.add_argument("--"+arg,required=True,type=Path)
    args=ap.parse_args()
    run(args.source,args.palette,args.output)


if __name__=="__main__":
    main()
