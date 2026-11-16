#!/usr/bin/env python3
"""ENGINE-001 V44-P1: source-aware, contrast-guarded RGB for frozen V35-B contours.

Color proposal only. It does not model native Egret footprints or game CHALK.
"""
from __future__ import annotations

import copy
import math
import numpy as np

from run_engine001_source_color_contour_native_v36 import DARK, medians_for_path

DETAIL_COUNT = 410
OFFSET = 2.0
MIN_CONTRAST = 2.5


def rgb_luminance(rgb):
    """WCAG-style relative luminance, purely a candidate selection heuristic."""
    if len(rgb) != 3 or any(not 0 <= int(x) <= 255 for x in rgb):
        raise ValueError("V44 invalid RGB")
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
              for v in (float(x) / 255 for x in rgb)]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    l1, l2 = sorted((rgb_luminance(a), rgb_luminance(b)))
    return (l2 + 0.05) / (l1 + 0.05)


def median_rgb(samples):
    a = np.asarray(samples, dtype=np.uint8)
    if a.ndim != 2 or a.shape[1] != 3 or not len(a):
        raise ValueError("V44 no valid RGB samples")
    return [int(np.sort(a[:, i])[(len(a) - 1) // 2]) for i in range(3)]


def side_backgrounds(original, points):
    """Two local sides using tangent of original polyline, no brush simulation."""
    arr = np.asarray(original.convert("RGB"), dtype=np.uint8)
    if arr.shape != (240, 150, 3):
        raise ValueError("V44 expected frozen source RGB ROI 150x240")
    sides = ([], [])
    for i, p in enumerate(points):
        if len(points) < 2:
            break
        prev, nex = points[max(0, i - 1)], points[min(len(points) - 1, i + 1)]
        dx = float(nex["x"]) - float(prev["x"])
        dy = float(nex["y"]) - float(prev["y"])
        norm = math.hypot(dx, dy)
        if not math.isfinite(norm) or norm < 1e-8:
            continue
        x, y = float(p["x"]), float(p["y"])
        for sign, dest in ((1, sides[0]), (-1, sides[1])):
            sx, sy = x - sign * OFFSET * dy / norm, y + sign * OFFSET * dx / norm
            if 155 <= sx < 305 and 0 <= sy < 240:
                ix, iy = max(0, min(149, round(sx - 155))), max(0, min(239, round(sy)))
                dest.append(arr[iy, ix].tolist())
    if not sides[0] or not sides[1]:
        return None
    return [median_rgb(samples) for samples in sides]


def contrast_guard(source_rgb, sides, minimum=MIN_CONTRAST):
    """Choose the lightest source-to-dark blend meeting both side contrasts."""
    if sides is None:
        return list(DARK), "missing_sides"
    if all(contrast(source_rgb, side) >= minimum for side in sides):
        return list(source_rgb), "source"
    # Deterministic fixed search, from original RGB toward V35-B color.
    for step in range(1, 101):
        t = step / 100.0
        trial = [int(round((1 - t) * source_rgb[i] + t * DARK[i])) for i in range(3)]
        if all(contrast(trial, side) >= minimum for side in sides):
            return trial, "darkened"
    return list(DARK), "unresolved"


def adaptive_recolor(base, original, variant):
    """A V35-B dark, B source median, C fixed-contrast source median.

    No geometry, width, order, stroke ID, or fill modifications allowed.
    """
    if variant not in ("A", "B", "C"):
        raise ValueError("V44 candidate must be A/B/C")
    result = copy.deepcopy(base)
    journal = []
    for original_entry, entry in zip(base["strokes"], result["strokes"]):
        if entry["layer"] != "detail":
            if entry != original_entry:
                raise ValueError("V44 altered fill")
            continue
        stroke = entry["stroke"]
        if stroke["width"] != 1 or stroke["colorRgb"] != 0x31262B:
            raise ValueError("V44 non-frozen detail")
        sampled = medians_for_path(original, stroke["points"])
        sides = side_backgrounds(original, stroke["points"])
        if variant == "A":
            used, reason = list(DARK), "baseline"
        elif variant == "B":
            used, reason = sampled, "source"
        else:
            used, reason = contrast_guard(sampled, sides)
        stroke["colorRgb"] = (used[0] << 16) | (used[1] << 8) | used[2]
        journal.append(dict(id=stroke["strokeId"], source_RGB=sampled,
                            sides_RGB=sides, assigned_RGB=used, decision=reason))
    if (len(base["strokes"]) != 2355 or len(result["strokes"]) != 2355
            or len(journal) != DETAIL_COUNT or base["synthetic_vertices_NOT_CHALK"] != 5682):
        raise ValueError("V44 frozen resource/count drift")
    for before, after in zip(base["strokes"], result["strokes"]):
        if before["layer"] != after["layer"]:
            raise ValueError("V44 layer order drift")
        if before["layer"] == "paint" and before != after:
            raise ValueError("V44 paint drift")
        if before["layer"] == "detail" and (
                {k: v for k, v in before["stroke"].items() if k != "colorRgb"}
                != {k: v for k, v in after["stroke"].items() if k != "colorRgb"}):
            raise ValueError("V44 contour geometry drift")
    return result, journal
