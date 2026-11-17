#!/usr/bin/env python3
"""ENGINE-001 color region boundaries: real Egret BoardPane diagnostic, no fill.

Outline ALL connected source regions/holes of owner classes 4..7 using
source MEDIANCUT8 labels, then render actual 2px Egret brush strokes.
The colored diagnostic palette makes pale original region boundaries visible.
This is NOT the frozen V44-B 410-detail contours nor a production fill plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import SOURCE_SHA, sha
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_v43p4_native_ab import verified_v44

EXPERIMENT = "ENGINE001_V43P4_COLOR_ZONE_BOUNDARIES_NATIVE_E3"
COLORS = (4, 5, 6, 7)
SHAPE = (240, 150)
ROI_X0 = 155
WIDTH = 2
EPSILON = 1.25  # Fixed source contour simplification, logical px
MAX_STROKES = 3000
MAX_VERTICES = 5900
MAX_PATH_VERTICES = 128
# Display-only contrasting owner colors, NOT frozen V44 fill RGB.
DIAGNOSTIC_RGB = {4: 0xCA3F3F, 5: 0xE28B00,
                  6: 0x188A84, 7: 0x4259CA}


def plan_zone_boundaries(labels: np.ndarray) -> tuple[list[dict], dict]:
    if (not isinstance(labels, np.ndarray) or labels.shape != SHAPE or
            labels.dtype.kind not in "iu" or np.any(labels < 0) or
            np.any(labels > 7)):
        raise ValueError("zone-boundary source labels drift")
    strokes = []
    per = {}
    for owner in COLORS:
        mask = (labels == owner).astype(np.uint8)
        if not mask.any():
            raise ValueError("required owner is absent")
        contours, hierarchy = cv2.findContours(
            mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ValueError("source color contour extraction failed")
        singletons, line_segments, closed = 0, 0, 0
        # Keep every contour, including holes and 1-pixel components.
        for raw in contours:
            approx = cv2.approxPolyDP(raw, EPSILON, True)
            points = [(float(p[0][0]), float(p[0][1]))
                      for p in approx]
            if len(points) == 1:
                x, y = points[0]
                # Nonzero-length nominal 2px Egret trace on a singleton.
                points = [(x + .125, y), (x + .375, y)]
                singletons += 1
            elif len(points) == 2:
                line_segments += 1
            else:
                points = points + [points[0]]
                closed += 1
            if len(points) < 2 or len(points) > MAX_PATH_VERTICES:
                raise ValueError("BLOCKED_GEOMETRY: contour path length")
            if any(x < 0 or x >= SHAPE[1] or y < 0 or y >= SHAPE[0]
                   for x, y in points):
                raise ValueError("BLOCKED_GEOMETRY: out-of-bounds zone point")
            strokes.append({
                "strokeId": f"icon-{len(strokes)}",
                "colorIndex": owner,
                "colorRgb": DIAGNOSTIC_RGB[owner],
                "width": WIDTH,
                "points": [{"x": x + ROI_X0, "y": y} for x, y in points],
            })
        per[str(owner)] = {
            "target_source_pixels": int(np.count_nonzero(mask)),
            "source_contours_including_holes": len(contours),
            "single_point_islands_or_contours": singletons,
            "two_point_segments": line_segments,
            "closed_boundary_paths": closed,
            "diagnostic_RGB": DIAGNOSTIC_RGB[owner],
        }
    vertices = sum(len(stroke["points"]) for stroke in strokes)
    if len(strokes) > MAX_STROKES or vertices > MAX_VERTICES:
        raise ValueError(
            f"BLOCKED_RESOURCE: {len(strokes)} contour paths, {vertices} vertices")
    if len({s["strokeId"] for s in strokes}) != len(strokes):
        raise ValueError("duplicate Egret stroke ID")
    return strokes, {
        "source_roi_shape_hw": list(SHAPE),
        "color_classes": list(COLORS),
        "contour_epsilon_logical_px": EPSILON,
        "native_nominal_brush_width": WIDTH,
        "total_paths": len(strokes),
        "total_synthetic_vertices_NOT_CHALK": vertices,
        "per_owner": per,
        "all_source_contours_included": True,
        "original_paint_or_V44_detail_strokes_reused": 0,
        "purpose": "diagnostic color-zone edge map, not fill or 410 detail contours",
    }


def composite_white(rgba: np.ndarray) -> Image.Image:
    if rgba.shape != (720, 1380, 4):
        raise ValueError("Egret backing changed from 1380x720 RGBA")
    background = Image.new("RGBA", (1380, 720), (255, 255, 255, 255))
    return Image.alpha_composite(
        background, Image.fromarray(rgba, mode="RGBA"))


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("workspace", "source", "v44-archive", "output"):
        ap.add_argument("--" + name, required=True, type=Path)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError("refusing overwrite of zone-boundary evidence")
    if sha(args.source) != SOURCE_SHA:
        raise ValueError("frozen source SHA drift")
    original = original_labels(args.source)
    labels = original[::3, ::3][:, ROI_X0:ROI_X0+SHAPE[1]].copy()
    strokes, geometry = plan_zone_boundaries(labels)
    # Source-only preflight done before creating any native evidence.
    _, contour_png, _ = verified_v44(args.v44_archive)
    v44_detail_png = args.v44_archive / "B" / "V44-B-color-100.png"
    if not v44_detail_png.is_file():
        raise ValueError("frozen Egret V44-B contour-only PNG absent")
    args.output.mkdir(parents=True)
    (args.output / "zone-plan.json").write_text(json.dumps({
        "experiment": EXPERIMENT,
        "source_sha256": SOURCE_SHA,
        "source_labels_sha256": hashlib.sha256(labels.tobytes()).hexdigest(),
        "geometry": geometry,
        "native_strokes": strokes,
        "safe_to_execute": False,
        "production_accepted": False,
        "exact_CHALK": None,
    }, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (args.output / "native").mkdir()
    native, metadata, _ = native_batch(
        args.workspace, "ZONE-BOUNDARIES", strokes,
        args.output / "native", renderer_method="renderComplexHoldoutColorProbe")
    if set(native) != {"composite", "color-4", "color-5", "color-6", "color-7"}:
        raise ValueError("missing real Egret region scenes")
    zone_rgba = native["composite"]
    zone_only = composite_white(zone_rgba)
    zone_only.save(args.output / "egret-zones-only-full.png")
    zone_only.resize((460, 240), Image.Resampling.LANCZOS).crop(
        (155, 0, 305, 240)).resize((600, 960), Image.Resampling.NEAREST).save(
        args.output / "egret-zones-only-600x960.png")
    with Image.open(v44_detail_png) as im:
        detail = im.convert("RGBA")
    if detail.size != (1380, 720):
        raise ValueError("frozen Egret V44 detail backing drift")
    # Both layers originate from actual Egret PNGs; only this preview merge
    # happens in Pillow, it does NOT repaint source paths.
    layered = Image.alpha_composite(
        Image.alpha_composite(
            Image.new("RGBA", (1380,720), (255,255,255,255)), detail),
        Image.fromarray(zone_rgba, mode="RGBA"))
    layered.save(args.output / "egret-zone-boundaries-and-v44-outline-full.png")
    layered.resize((460,240), Image.Resampling.LANCZOS).crop(
        (155,0,305,240)).resize((600,960), Image.Resampling.NEAREST).save(
        args.output / "egret-zones-and-v44-outline-600x960.png")
    checksums = {str(p.relative_to(args.output)).replace("\\","/"):sha(p)
                 for p in args.output.rglob("*") if p.is_file()}
    report = {
        "experiment": EXPERIMENT,
        "status": "REAL_EGRET_E3_COLOR_ZONE_CONTOUR_DIAGNOSTIC",
        "source_sha256": SOURCE_SHA,
        "native_renderer": "renderComplexHoldoutColorProbe",
        "native_Egret": "BoardPane/WebGLRenderer",
        "zones": geometry, "native_metadata": metadata,
        "frozen_V44_contour_overlay_file_sha256": sha(v44_detail_png),
        "overlay_compositing": "Pillow combines two separately real-Egret-rendered RGBA layers",
        "no_color_fill": True,
        "all_zone_source_contours_included": True,
        "original_410_V44B_detail_strokes_unmodified": True,
        "render_is_not_gameplay": True, "game_E4": "NOT_RUN",
        "exact_game_CHALK": None, "production_accepted": False,
        "report_linked_SHA256": checksums,
        "versions": {"python": platform.python_version(),
                     "numpy": np.__version__},
    }
    (args.output / "report.json").write_text(json.dumps(
        report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "contours": geometry["total_paths"],
        "vertices_NOT_CHALK": geometry["total_synthetic_vertices_NOT_CHALK"],
        "preview": "egret-zones-only-600x960.png",
        "overlay": "egret-zones-and-v44-outline-600x960.png",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
