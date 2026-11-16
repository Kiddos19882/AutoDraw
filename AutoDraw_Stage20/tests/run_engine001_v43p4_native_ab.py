#!/usr/bin/env python3
"""V43-P4.2 first full native A/B0 Egret comparison (NOT gameplay/CHALK).

Frozen V44-B remains pixel-exact control. Original 1945 paint paths are never
included in B0. This is opt-in research and never invokes the Stage6 executor.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
from collections import Counter
from pathlib import Path

import numpy as np

from engine001_paint_then_detail_v35 import native_strokes
from run_engine001_boundary_shift_native_v39 import native_metrics
from run_engine001_full_adaptive_fill_v43p4 import (
    COLORS, FROZEN_DETAILS, MAX_STROKES, MAX_VERTICES, SOURCE_SHA,
    source_plan, sha,
)
from run_engine001_internal_color_tolerance_v40 import overlap_by_class
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import (
    warm_mask, png_pixel_exact_replay,
)
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source, sheet
from run_engine001_native_v29_brush2_v33 import logical_crop

EXPERIMENT = "ENGINE001_V43P4_FULL_ADAPTIVE_FILL_B0_NATIVE_E3"
V44_EXPERIMENT = "ENGINE001_ADAPTIVE_COLOR_OUTLINE_V44_P1"
SOURCE_V44_RUN = 43813812976
SCENES = ("composite", "color-4", "color-5", "color-6", "color-7", "color-100")
ALPHAS = (24, 128)


def verified_v44(folder: Path):
    """Verify manifest, source identity, frozen B detail and original A PNG."""
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    if (report.get("experiment") != V44_EXPERIMENT
            or report.get("source_sha256") != SOURCE_SHA
            or report.get("control_V37P2C_RGBA_exact") is not True
            or report.get("native_alpha_exact_all_variants") is not True):
        raise ValueError("BLOCKED_BASELINE_DRIFT V44 metadata")
    checksums = report.get("report_linked_SHA256")
    if not isinstance(checksums, dict) or not checksums:
        raise ValueError("BLOCKED_BASELINE_DRIFT missing V44 checksums")
    for name, digest in checksums.items():
        rel = Path(name)
        if (rel.is_absolute() or ".." in rel.parts or len(str(digest)) != 64
                or not (folder / rel).is_file() or sha(folder / rel) != digest):
            raise ValueError("BLOCKED_BASELINE_DRIFT V44 file SHA: " + name)
    filename = folder / "B" / "V44-B-composite.png"
    if not filename.is_file():
        raise ValueError("BLOCKED_BASELINE_DRIFT missing V44-B native PNG")
    payload = json.loads((folder / "color-plans.json").read_text(encoding="utf-8"))
    if payload.get("experiment") != V44_EXPERIMENT:
        raise ValueError("BLOCKED_BASELINE_DRIFT V44 plan experiment")
    base = payload["plans"]["B"]
    entries = base.get("strokes")
    if (not isinstance(entries, list) or len(entries) != 2355
            or base.get("paint_strokes") != 1945
            or base.get("detail_strokes") != FROZEN_DETAILS
            or base.get("synthetic_vertices_NOT_CHALK") != 5682):
        raise ValueError("BLOCKED_BASELINE_DRIFT V44 counts")
    if any(e["layer"] != "paint" or
           e["stroke"]["width"] != 2 or
           e["stroke"]["colorIndex"] not in COLORS or
           not e["stroke"]["strokeId"].startswith("icon-")
           for e in entries[:1945]):
        raise ValueError("BLOCKED_BASELINE_DRIFT V44 original paint")
    details = entries[1945:]
    if (any(e["layer"] != "detail" or
            e["stroke"]["width"] != 1 or
            not e["stroke"]["strokeId"].startswith("detail-v18-B-")
            for e in details)
            or len({e["stroke"]["strokeId"] for e in entries}) != len(entries)):
        raise ValueError("BLOCKED_BASELINE_DRIFT V44 contours/IDs")
    if sum(len(e["stroke"]["points"]) for e in details) != 1792:
        raise ValueError("BLOCKED_BASELINE_DRIFT frozen detail vertices")
    return base, filename, checksums


def assemble_b0(source_candidate: dict, v44_base: dict) -> tuple[list, dict]:
    """New paint + byte-structurally unchanged V44-B colored contour strokes."""
    if (source_candidate.get("safe_to_execute") is not False
            or source_candidate.get("original_paint_retained") != 0
            or source_candidate.get("candidate") != "B0_SOURCE_ONLY"):
        raise ValueError("P4 invalid source-only candidate")
    entries = v44_base["strokes"]
    if len(entries) != 2355 or source_candidate["paint_strokes"] != len(
            source_candidate["paint"]):
        raise ValueError("P4 frozen or model count drift")
    colors = {}
    counts = {}
    for owner in COLORS:
        rgb = Counter(e["stroke"]["colorRgb"] for e in entries[:1945]
                      if e["stroke"]["colorIndex"] == owner)
        if not rgb:
            raise ValueError("P4 missing frozen RGB for owner")
        colors[owner] = min(rgb, key=lambda value: (-rgb[value], value))
        counts[str(owner)] = {
            "frozen_selected_rgb": colors[owner],
            "source_mode_frequency": rgb[colors[owner]],
            "source_strokes": sum(rgb.values()),
        }
    paint = []
    for candidate in source_candidate["paint"]:
        s = copy.deepcopy(candidate)
        owner = s["colorIndex"]
        if (owner not in COLORS or s["width"] not in (10, 6, 4, 2)
                or not s["strokeId"].startswith(f"p4-b0-{owner}-")
                or len(s["points"]) != 2):
            raise ValueError("P4 unexpected B0 paint")
        s["colorRgb"] = colors[owner]
        paint.append(s)
    detail = [copy.deepcopy(e["stroke"]) for e in entries[1945:]]
    if detail != [e["stroke"] for e in entries[1945:]]:
        raise ValueError("P4 frozen colored detail modified")
    strokes = paint + detail
    total_vertices = sum(len(s["points"]) for s in strokes)
    if (len(strokes) > MAX_STROKES or total_vertices > MAX_VERTICES
            or len(detail) != FROZEN_DETAILS
            or len({s["strokeId"] for s in strokes}) != len(strokes)
            or total_vertices != source_candidate[
                "synthetic_vertices_with_frozen_detail_NOT_CHALK"]):
        raise ValueError("BLOCKED_RESOURCE P4 B0 native preflight")
    if any(s["strokeId"].startswith("icon-") for s in paint):
        raise ValueError("P4 original paint was retained")
    return strokes, {
        "paint_count": len(paint),
        "detail_count": len(detail),
        "synthetic_vertices_NOT_CHALK": total_vertices,
        "original_paint_retained": 0,
        "V44B_410_detail_exact": True,
        "detail_after_paint": True,
        "frozen_paint_RGB_owner_mode": counts,
    }


def per_owner_native(native, labels):
    metrics = {}
    for alpha in ALPHAS:
        metrics[str(alpha)] = {
            str(owner): overlap_by_class(
                labels, owner, native[f"color-{owner}"][:, :, 3] >= alpha)
            for owner in COLORS
        }
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    for name in ("workspace", "source", "v44-archive", "output"):
        ap.add_argument("--" + name, required=True, type=Path)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError("P4 refuses overwrite of native evidence")
    if sha(args.source) != SOURCE_SHA:
        raise ValueError("P4 frozen source SHA mismatch")
    frozen, frozen_png, frozen_hashes = verified_v44(args.v44_archive)
    original, _ = prepare_source(args.source)
    labels3 = original_labels(args.source)
    model = source_plan(labels3[::3, ::3][:, 155:305].copy())
    b0, preflight = assemble_b0(model, frozen)
    # Preserve all preflight data even on a native quality failure.
    output = args.output
    output.mkdir(parents=True)
    (output / "candidate-plans.json").write_text(
        json.dumps({"experiment": EXPERIMENT, "source": model,
                    "b0_preflight": preflight, "b0_native_strokes": b0},
                   ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    images, results, crops = {}, {}, {}
    warm = warm_mask(original)
    for variant in ("A", "B0"):
        target = output / variant
        target.mkdir()
        candidate = native_strokes(frozen) if variant == "A" else b0
        renderer = ("renderV36SourceColoredContourProbe" if variant == "A"
                    else "renderV43P4FullAdaptiveProbe")
        images[variant], meta, _ = native_batch(
            args.workspace, "V43P4-" + variant, candidate, target,
            renderer_method=renderer)
        if set(images[variant]) != set(SCENES):
            raise ValueError("P4 native scene set drift")
        metrics = native_metrics(images[variant], original, labels3, warm)
        results[variant] = {
            **metrics, "native_owner_overlap": per_owner_native(images[variant], labels3),
            "native_renderer_metadata": meta,
        }
        crops[variant] = logical_crop(images[variant]["composite"])
        if variant == "A":
            replay = png_pixel_exact_replay(
                frozen_png, output / "A" / "V43P4-A-composite.png")
            if not replay["pixel_rgba_exact"]:
                raise ValueError("BLOCKED_BASELINE_DRIFT P4 native A is not V44-B")
    for variant in ("A", "B0"):
        crops[variant].save(output / f"V43P4-{variant}-roi.png")
    sheet([original, crops["A"], crops["B0"]],
          ["Original", "Frozen native V44-B", "First full P4 B0"],
          output / "comparison-full.png")
    sheet([original, crops["A"], crops["B0"]],
          ["Original", "Frozen native V44-B", "P4 B0 native"],
          output / "comparison-faces.png", top=True)
    quality = {}
    for alpha in ALPHAS:
        rows = results["B0"]["native_owner_overlap"][str(alpha)]
        quality[str(alpha)] = {
            "all_class_recall_at_least_99pct": all(
                rows[str(i)]["correct_class_recall"] >= 0.99 for i in COLORS),
            "foreign_more_than_3logical_px_zero": all(
                rows[str(i)]["foreign_overlap_excess_beyond_3logical_px"] == 0
                for i in COLORS),
            "exterior_more_than_3logical_px_zero":
                results["B0"]["native_class_metrics"][str(alpha)][
                    "painted_more_than_3_logical_px_from_source_foreground"] == 0,
        }
    quality["full_RGB_MAE_nonregression"] = (
        results["B0"]["source_RGB_MAE"] <= results["A"]["source_RGB_MAE"])
    quality["warm_RGB_MAE_nonregression"] = (
        results["B0"]["warm_RGB_MAE"] <= results["A"]["warm_RGB_MAE"])
    quality["native_quality_provisional_numeric_only"] = all(
        v for row in quality.values() for v in
        (row.values() if isinstance(row, dict) else [row]))
    hashes = {str(p.relative_to(output)).replace("\\", "/"): sha(p)
              for p in output.rglob("*") if p.is_file()}
    report = {
        "experiment": EXPERIMENT,
        "status": "NATIVE_EGRET_E3_NOT_LIVE_GAME",
        "source_SHA256": SOURCE_SHA, "frozen_V44_run_id": SOURCE_V44_RUN,
        "frozen_V44_report_SHA256": frozen_hashes,
        "frozen_native_A_V44B_pixel_exact": True,
        "b0": preflight, "measurements": results, "quality_gates": quality,
        "quality_accepted": False,
        "quality_status": "PENDING_USER_VISUAL_AND_E5" if
            quality["native_quality_provisional_numeric_only"] else "NUMERIC_FAIL",
        "native_alpha_thresholds": list(ALPHAS),
        "report_linked_SHA256": hashes,
        "game_exact_CHALK": None, "E4": "NOT_RUN", "E5": "NOT_RUN",
        "production_accepted": False,
        "versions": {"Python": platform.python_version(),
                     "numpy": np.__version__},
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2,
                   allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"native_quality": report["quality_status"],
                      "strokes": len(b0), "preflight": preflight,
                      "quality": quality}, ensure_ascii=False))


if __name__ == "__main__":
    main()
