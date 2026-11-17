#!/usr/bin/env python3
"""ENGINE-001 S2b EGRET-P1: genuine archived BoardPane brush on G source zones.

Isolated real WebGL/BoardPane RGBA, NOT full fill, game E4, or CHALK.
"""
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
from PIL import Image

from run_engine001_palette32_region_study import (
    read_source, read_palette, nearest32, sha,
)
from run_engine001_color32_s2_edge_protection import (
    strong_edges, protected_merge,
)
from run_engine001_complex_holdout_v5 import native_batch

EXP = "ENGINE001_COLOR32_S2B_EGRET_P1_NATIVE_ISOLATED"
WIDTHS = (2, 4, 6, 10)
ROI_X0 = 155
ROI_SHAPE = (240, 150)
BACKING_SHAPE = (720, 1380, 4)
MAX_COLORS = 4
INSET = 6.0
ALPHAS = (24, 128)


def select_interior_loops(g: np.ndarray, palette: np.ndarray) -> tuple[list[dict], dict]:
    if g.shape != ROI_SHAPE or g.dtype != np.uint8 or len(palette) != 32:
        raise ValueError("BLOCKED_S2B_G_GEOMETRY")
    colors, counts = np.unique(g, return_counts=True)
    ranked = sorted(zip(colors.tolist(), counts.tolist()),
                    key=lambda pair: (-pair[1], pair[0]))
    picked, reasons = [], {}
    for color_index, count in ranked:
        if color_index == 30:
            reasons[str(color_index)] = "EXCLUDED_WHITE_BACKGROUND"
            continue
        own = (g == color_index).astype(np.uint8)
        interior = (cv2.distanceTransform(
            own, cv2.DIST_L2, cv2.DIST_MASK_PRECISE) > INSET).astype(np.uint8)
        contours, _ = cv2.findContours(
            interior, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        accepted = None
        for contour in sorted(contours, key=lambda c: -cv2.contourArea(c)):
            if cv2.contourArea(contour) < 6:
                continue
            simple = cv2.approxPolyDP(contour, 0.75, True).reshape(-1, 2)
            if len(simple) < 3 or len(simple) + 1 > 128:
                continue
            closed = np.vstack((simple, simple[0]))
            if not np.all((closed[:, 0] >= 0) & (closed[:, 0] < 150)
                          & (closed[:, 1] >= 0) & (closed[:, 1] < 240)):
                continue
            path_ink = np.zeros(ROI_SHAPE, np.uint8)
            cv2.polylines(path_ink, [closed.astype(np.int32)], False, 255, 1)
            if np.any((path_ink > 0) & (own == 0)):
                continue
            accepted = closed
            break
        if accepted is None:
            reasons[str(color_index)] = "NO_SAFE_6PX_INSET_CLOSED_CONTOUR"
            continue
        rgb = palette[color_index]
        picked.append({
            "strokeId": f"icon-{len(picked)}",
            "colorIndex": int(color_index),
            "colorRgb": int((int(rgb[0]) << 16) | (int(rgb[1]) << 8) | int(rgb[2])),
            "width": WIDTHS[0],
            "points": [{"x": float(x + ROI_X0), "y": float(y)}
                       for x, y in accepted],
        })
        reasons[str(color_index)] = "SELECTED_NATIVE_PROBE"
        if len(picked) == MAX_COLORS:
            break
    if not picked:
        raise ValueError("BLOCKED_NOT_ENOUGH_SAFE_PROBES")
    if (sum(len(x["points"]) for x in picked) * len(WIDTHS) > 5900
            or len(picked) * len(WIDTHS) > 3000):
        raise ValueError("BLOCKED_RESOURCE_S2B_EGRET_P1")
    return picked, {"candidate_order": ranked, "eligibility": reasons,
                    "selected_colors": [s["colorIndex"] for s in picked],
                    "selected_count": len(picked),
                    "source_only_inset_logical_px": INSET,
                    "diagnostic_not_all_32_colors": True}


def native_metrics(images: dict, g: np.ndarray, strokes: list[dict]) -> dict:
    expected = {"composite"} | {f"color-{s['colorIndex']}" for s in strokes}
    if set(images) != expected:
        raise ValueError("BLOCKED_NATIVE_SCENE_SET")
    full = np.full((240, 460), 30, np.uint8)
    full[:, ROI_X0:ROI_X0 + 150] = g
    full3 = np.repeat(np.repeat(full, 3, axis=0), 3, axis=1)
    selected = {s["colorIndex"] for s in strokes}
    out = {}
    for alpha in ALPHAS:
        groups = {}
        for owner in sorted(selected):
            rgba = images[f"color-{owner}"]
            if rgba.shape != BACKING_SHAPE or rgba.dtype != np.uint8:
                raise ValueError("BLOCKED_NATIVE_BACKING_GEOMETRY")
            ink = rgba[:, :, 3] >= alpha
            own = full3 == owner
            dist = cv2.distanceTransform(
                (~own).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
            inside = int(np.count_nonzero(ink & own))
            target = int(np.count_nonzero(own))
            groups[str(owner)] = {
                "owner_target_backing_pixels": target,
                "native_alpha_ink_pixels": int(np.count_nonzero(ink)),
                "native_correct_owner_pixels": inside,
                "isolated_fraction_of_full_owner_NOT_full_fill_coverage": inside / target,
                "non_owner_native_pixels_any_distance": int(np.count_nonzero(ink & ~own)),
                "non_owner_beyond_3logical_px": int(np.count_nonzero(ink & (dist > 9))),
                "ink_outside_image_ROI": int(np.count_nonzero(
                    ink & np.logical_or(np.indices(ink.shape)[1] < ROI_X0*3,
                                        np.indices(ink.shape)[1] >= (ROI_X0+150)*3))),
            }
        out[str(alpha)] = groups
    return out


def run(workspace: Path, source: Path, palette_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_EXISTING_NATIVE_EVIDENCE")
    _, original = read_source(source)
    palette = read_palette(palette_path)
    b = nearest32(original, palette)
    strong, threshold = strong_edges(original)
    g, changes = protected_merge(original, b, palette, strong)
    probes, selection = select_interior_loops(g, palette)
    output.mkdir(parents=True)
    (output / "source-g-index.png").write_bytes(
        _png_bytes(Image.fromarray(g)))
    provenance = {
        "experiment": EXP,
        "source_sha256": sha(source),
        "palette_sha256": sha(palette_path),
        "g_index_map_sha256": hashlib.sha256(g.tobytes()).hexdigest(),
        "source_edge_threshold": threshold,
        "g_accepted_merges": changes,
        "selection": selection,
        "widths": list(WIDTHS),
        "strokes_base_paths": probes,
        "game_CHALK": None, "safe_to_execute": False,
    }
    (output / "probe-paths.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False, allow_nan=False)+"\n",
        encoding="utf-8")
    all_native, delta = {}, {}
    for width in WIDTHS:
        strokes = [{**s, "width": width} for s in probes]
        folder = output / f"native-width-{width}"
        folder.mkdir()
        frames, metadata, native_run = native_batch(
            workspace, f"S2B-EGRET-P1-W{width}", strokes, folder,
            renderer_method="renderComplexHoldoutColorProbe")
        metrics = native_metrics(frames, g, strokes)
        all_native[str(width)] = {
            "metrics": metrics, "metadata": metadata, "native_run": native_run,
            "strokes": len(strokes), "vertices_NOT_CHALK":
            sum(len(s["points"]) for s in strokes),
        }
        if width == 2:
            reference = metrics
        delta[str(width)] = {
            str(a): {key: {
                "additional_own_native_pixels_vs_w2_same_path":
                metrics[str(a)][key]["native_correct_owner_pixels"]
                - reference[str(a)][key]["native_correct_owner_pixels"],
                "beyond_3logical_px":
                metrics[str(a)][key]["non_owner_beyond_3logical_px"],
            } for key in metrics[str(a)]} for a in ALPHAS
        }
    hashed = {str(p.relative_to(output)).replace("\\", "/"): sha(p)
              for p in output.rglob("*") if p.is_file()}
    all_safe = all(v["non_owner_beyond_3logical_px"] == 0
                   for data in all_native.values()
                   for threshold_data in data["metrics"].values()
                   for v in threshold_data.values())
    report = {
        "experiment": EXP, "status": "REAL_EGRET_E3_ISOLATED_NOT_FULL_FILL",
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "actual_renderer": "archived BoardPane via renderComplexHoldoutColorProbe",
        "backend": "Firefox WebGL", "source_sha256": sha(source),
        "palette_sha256": sha(palette_path),
        "selected_G_colors": selection["selected_colors"],
        "source_probes": selection, "widths": list(WIDTHS),
        "native_width_evidence": all_native,
        "vs_width2": delta,
        "native_all_probes_beyond_3px_zero": all_safe,
        "full_owner_coverage_gate": "NOT_RUN",
        "V44B_frozen_410_detail_unchanged": True,
        "V44B_composite_overlay": "NOT_RUN",
        "source_S2b_CI_dependency": "UNKNOWN_UNTIL_VERIFIED",
        "E4_game": "NOT_RUN", "E5_independent": "NOT_RUN",
        "exact_game_CHALK": None, "production_accepted": False,
        "report_linked_SHA256": hashed,
        "versions": {"Python": platform.python_version(),
                     "numpy": np.__version__, "opencv": cv2.__version__,
                     "skimage": skimage.__version__},
    }
    (output / "report.json").write_text(json.dumps(
        report, indent=2, ensure_ascii=False, allow_nan=False)+"\n",
        encoding="utf-8")
    return report


def _png_bytes(image: Image.Image) -> bytes:
    from io import BytesIO
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def main():
    p = argparse.ArgumentParser()
    for name in ("workspace", "source", "palette", "output"):
        p.add_argument("--"+name, type=Path, required=True)
    a = p.parse_args()
    result = run(a.workspace, a.source, a.palette, a.output)
    print(json.dumps({
        "experiment": EXP,
        "native_widths": list(WIDTHS),
        "tested_colors": result["selected_G_colors"],
        "beyond_3px_all_zero": result["native_all_probes_beyond_3px_zero"],
        "full_fill": "NOT_RUN", "game_CHALK": None,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
