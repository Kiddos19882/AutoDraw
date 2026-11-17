#!/usr/bin/env python3
"""ENGINE-001 PAL32-REGION-V1: immutable source-only palette/region A..F trial.

NOT native Egret fill; never executed in Stage6, Monitor, Bridge or production.
Methods and post-pilot parameters: docs/ENGINE001_PAL32_REGION_V1_PROTOCOL_2026-11-17.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from skimage import color, measure, segmentation

EXP = "ENGINE001_PAL32_REGION_V1_SOURCE_ONLY"
SOURCE_SHA = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
PALETTE_BLOB = "461b5f3725b9b79888ad36e807b3cf4c9e445e98"
ROI_WH = (150, 240)
PARAMS = {
    "A_mediancut8": {"colors": 8, "dither": "NONE"},
    "B_direct32": {"metric": "CIEDE2000", "dither": "NONE"},
    "C_slic32": {"n_segments": 260, "compactness": 12.0, "sigma": 0.7},
    "D_slic32_merge": {"source": "C", "max_area": 41, "max_extra_delta_e00": 5.0, "iterations": 8},
    "E_regularized32": {"source": "B", "max_area": 8, "max_extra_delta_e00": 5.0, "iterations": 2},
    "F_fine_slic32": {"n_segments": 1600, "compactness": 8.0, "sigma": 0.3},
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_source(source: Path) -> tuple[Image.Image, np.ndarray]:
    if sha(source) != SOURCE_SHA:
        raise ValueError("BLOCKED_SOURCE_DRIFT: source SHA256")
    image = Image.open(source).convert("RGB").resize(ROI_WH, Image.Resampling.LANCZOS)
    return image, np.asarray(image, dtype=np.uint8)


def read_palette(palette_file: Path) -> np.ndarray:
    payload = json.loads(palette_file.read_text(encoding="utf-8"))
    colors = payload.get("colors")
    if not isinstance(colors, list) or len(colors) != 32:
        raise ValueError("BLOCKED_PALETTE_DRIFT: expected exactly 32 original game colors")
    out = []
    for item in colors:
        raw = item["rgb"]
        rgb = tuple(int(c) for c in raw)
        if (len(rgb) != 3 or any(x < 0 or x > 255 for x in rgb)
                or "#" + "".join(f"{x:02X}" for x in rgb) != item.get("hex", "").upper()):
            raise ValueError("BLOCKED_PALETTE_DRIFT: incompatible RGB and HEX")
        out.append(rgb)
    if len(set(out)) != 32:
        raise ValueError("BLOCKED_PALETTE_DRIFT: duplicate color")
    return np.asarray(out, dtype=np.uint8)


def palette_lab(palette: np.ndarray) -> np.ndarray:
    return color.rgb2lab(palette[np.newaxis, :, :] / 255.0)[0]


def nearest32(image: np.ndarray, palette: np.ndarray) -> np.ndarray:
    lab = color.rgb2lab(image / 255.0).reshape(-1, 3)
    plab = palette_lab(palette)
    idx = np.empty(lab.shape[0], dtype=np.uint8)
    for start in range(0, len(lab), 5000):
        de = color.deltaE_ciede2000(lab[start:start + 5000, None, :],
                                    plab[None, :, :])
        idx[start:start + 5000] = np.argmin(de, axis=1)
    return idx.reshape(image.shape[:2])


def slic32(image: np.ndarray, palette: np.ndarray, *, n_segments: int,
           compactness: float, sigma: float) -> tuple[np.ndarray, int]:
    segments = segmentation.slic(
        image, n_segments=n_segments, compactness=compactness, sigma=sigma,
        start_label=0, convert2lab=True, enforce_connectivity=True)
    lab = color.rgb2lab(image / 255.0)
    plab = palette_lab(palette)
    idx = np.empty(image.shape[:2], dtype=np.uint8)
    for segment_id in np.unique(segments):
        mask = segments == segment_id
        mean = lab[mask].mean(axis=0)
        # CIEDE2000 returns the full 32-value array; do NOT index [0] here.
        idx[mask] = np.argmin(color.deltaE_ciede2000(mean[None, :], plab))
    return idx, int(len(np.unique(segments)))


def tiny_region_merge(source: np.ndarray, index_map: np.ndarray, palette: np.ndarray,
                      *, max_area: int, max_extra_delta_e00: float,
                      iterations: int) -> tuple[np.ndarray, list[int]]:
    """4-connected tiny same-color region -> existing touching swatch only.

    Merging is allowed only if local original-image mean ΔE00 increases by
    <= configured amount. Own-color repaint is never a penalty here.
    """
    if (index_map.shape != ROI_WH[::-1] or index_map.dtype != np.uint8
            or max_area < 1 or iterations < 1 or max_extra_delta_e00 < 0):
        raise ValueError("invalid tiny-region merge configuration")
    out = index_map.copy()
    h, w = out.shape
    lab = color.rgb2lab(source / 255.0)
    plab = palette_lab(palette)
    de = color.deltaE_ciede2000(lab[:, :, None, :], plab[None, None, :, :])
    changed = []
    for _ in range(iterations):
        count = 0
        components = measure.label(out, connectivity=1, background=-1)
        regions = sorted(measure.regionprops(components), key=lambda r: (r.area, r.label))
        for reg in regions:
            if reg.area > max_area:
                continue
            xy = reg.coords
            ys, xs = xy[:, 0], xy[:, 1]
            original_index = int(out[ys[0], xs[0]])
            member = components == reg.label
            neighbor_contacts = Counter()
            for y, x in xy:
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < h and 0 <= xx < w and not member[yy, xx]:
                        neighbor_contacts[int(out[yy, xx])] += 1
            if not neighbor_contacts:
                continue
            baseline = float(de[ys, xs, original_index].mean())
            scored = []
            for candidate, shared_boundary in neighbor_contacts.items():
                if candidate == original_index:
                    continue
                extra = float(de[ys, xs, candidate].mean() - baseline)
                if extra <= max_extra_delta_e00:
                    scored.append((extra, -shared_boundary, candidate))
            if scored:
                scored.sort()
                out[ys, xs] = scored[0][2]
                count += 1
        changed.append(count)
        if count == 0:
            break
    return out, changed


def topology(idx: np.ndarray) -> dict:
    by = {}
    for pi in np.unique(idx):
        comp = measure.label(idx == pi, connectivity=1)
        areas = [int(p.area) for p in measure.regionprops(comp)]
        by[str(int(pi))] = {
            "pixels": int(np.count_nonzero(idx == pi)),
            "components": len(areas),
            "components_lt8": sum(s < 8 for s in areas),
            "components_lt16": sum(s < 16 for s in areas),
            "components_lt32": sum(s < 32 for s in areas),
        }
    return {
        "used_game_swatches_or_adaptive_colors": int(len(by)),
        "all_4_connected_components": sum(v["components"] for v in by.values()),
        "components_lt8": sum(v["components_lt8"] for v in by.values()),
        "components_lt16": sum(v["components_lt16"] for v in by.values()),
        "components_lt32": sum(v["components_lt32"] for v in by.values()),
        "by_palette_index": by,
    }


def quality(source: np.ndarray, mapped: np.ndarray) -> dict:
    de = color.deltaE_ciede2000(
        color.rgb2lab(source / 255.0), color.rgb2lab(mapped / 255.0))
    return {
        "mean_delta_e00": float(de.mean()),
        "p95_delta_e00": float(np.percentile(de, 95)),
        "max_delta_e00": float(de.max()),
        "rgb_mae": float(np.abs(
            source.astype(np.int16) - mapped.astype(np.int16)).mean()),
    }


def thumbnail_sheet(images: list[np.ndarray], labels: list[str], path: Path):
    scaling, pad, head = 3, 10, 28
    h, w = images[0].shape[:2]
    canvas = Image.new("RGB", ((w * scaling + pad) * len(images) + pad,
                               h * scaling + pad + head), "white")
    pen = ImageDraw.Draw(canvas)
    for i, (arr, label) in enumerate(zip(images, labels)):
        x = pad + i * (w * scaling + pad)
        pen.text((x, 7), label, fill="black")
        canvas.paste(Image.fromarray(arr, "RGB").resize(
            (w * scaling, h * scaling), Image.Resampling.NEAREST), (x, head))
    canvas.save(path)


def run(source_file: Path, palette_file: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("refusing overwrite of frozen PAL32 evidence")
    source_image, source = read_source(source_file)
    palette = read_palette(palette_file)
    a = source_image.quantize(
        colors=8, method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE)
    a_rgb = np.asarray(a.convert("RGB"), dtype=np.uint8)
    a_index = np.asarray(a, dtype=np.uint8)
    b_index = nearest32(source, palette)
    c_index, c_count = slic32(source, palette, **PARAMS["C_slic32"])
    d_params = PARAMS["D_slic32_merge"]
    d_index, d_changes = tiny_region_merge(
        source, c_index, palette, max_area=d_params["max_area"],
        max_extra_delta_e00=d_params["max_extra_delta_e00"],
        iterations=d_params["iterations"])
    e_params = PARAMS["E_regularized32"]
    e_index, e_changes = tiny_region_merge(
        source, b_index, palette, max_area=e_params["max_area"],
        max_extra_delta_e00=e_params["max_extra_delta_e00"],
        iterations=e_params["iterations"])
    f_index, f_count = slic32(source, palette, **PARAMS["F_fine_slic32"])
    variants = {
        "A_mediancut8": (a_rgb, a_index),
        "B_direct32": (palette[b_index], b_index),
        "C_slic32": (palette[c_index], c_index),
        "D_slic32_merge": (palette[d_index], d_index),
        "E_regularized32": (palette[e_index], e_index),
        "F_fine_slic32": (palette[f_index], f_index),
    }
    output.mkdir(parents=True)
    report = {
        "experiment": EXP,
        "status": "E2_SOURCE_ONLY_NOT_EGRET",
        "source_sha256": SOURCE_SHA,
        "palette_git_blob_sha": PALETTE_BLOB,
        "palette_file_sha256": sha(palette_file),
        "palette_hex_in_index_order": ["#" + "".join(
            f"{v:02X}" for v in row) for row in palette],
        "roi_wh": list(ROI_WH), "parameters": PARAMS,
        "source_slic_segments": {"C": c_count, "F": f_count},
        "adjacent_merges": {"D": d_changes, "E": e_changes},
        "variants": {},
        "dither_used": False,
        "comparison_of_components": "all colors, 4-connected, NOT 1838 Egret contour paths",
        "frozen_V44B_410_detail_untouched": True,
        "native_Egret_fill": "NOT_RUN",
        "E4_game": "NOT_RUN", "E5_independent": "NOT_RUN",
        "run_bound_exact_CHALK": None, "production_accepted": False,
    }
    for key, (rgb, idx) in variants.items():
        if key != "A_mediancut8" and not np.array_equal(rgb, palette[idx]):
            raise AssertionError("game palette mapping drift")
        if key != "A_mediancut8" and (idx.max() >= 32 or idx.min() < 0):
            raise AssertionError("game palette index drift")
        Image.fromarray(rgb, "RGB").save(output / f"{key}.png")
        Image.fromarray(idx, "L").save(output / f"{key}_indices.png")
        boundaries = segmentation.find_boundaries(idx, mode="outer")
        marked = rgb.copy()
        marked[boundaries] = 0
        Image.fromarray(marked, "RGB").save(output / f"{key}_boundaries.png")
        report["variants"][key] = {
            "quality": quality(source, rgb),
            "components": topology(idx),
            "used_palette_indices": sorted(int(i) for i in np.unique(idx)),
        }
    thumbnail_sheet([source] + [rgb for rgb, _ in variants.values()],
                    ["Original"] + list(variants.keys()), output / "comparison_all.png")
    thumbnail_sheet([source, variants["B_direct32"][0],
                     variants["E_regularized32"][0], variants["F_fine_slic32"][0]],
                    ["Original", "B direct32", "E regularized", "F fine SLIC"],
                    output / "comparison_detail.png")
    report["report_linked_SHA256"] = {
        p.name: sha(p) for p in sorted(output.glob("*.png"))
    }
    (output / "report.json").write_text(json.dumps(
        report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--palette", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.source, args.palette, args.output)
    print(json.dumps({
        "experiment": EXP, "status": report["status"],
        "metrics": {k: {
            "components": v["components"]["all_4_connected_components"],
            "colors_used": v["components"]["used_game_swatches_or_adaptive_colors"],
            "mean_delta_e00": round(v["quality"]["mean_delta_e00"], 4)}
            for k, v in report["variants"].items()},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
