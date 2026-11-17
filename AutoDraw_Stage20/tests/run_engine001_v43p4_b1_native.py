#!/usr/bin/env python3
"""V43-P4/B1 first independent native Egret A/B1, keeping frozen B0 as evidence.

B1 native output is not a game run. Never overwrite A, B0 or source archives.
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
from PIL import Image

from run_engine001_v43p4_b1_source import (
    EXPERIMENT as SOURCE_EXPERIMENT, b1_source_plan,
)
from run_engine001_v43p4_native_ab import (
    SOURCE_SHA, SCENES, ALPHAS, FROZEN_DETAILS,
    verified_v44, per_owner_native,
)
from run_engine001_full_adaptive_fill_v43p4 import (
    COLORS, MAX_STROKES, MAX_VERTICES, sha,
)
from run_engine001_boundary_shift_native_v39 import native_metrics
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import warm_mask, png_pixel_exact_replay
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source, sheet
from run_engine001_native_v29_brush2_v33 import logical_crop

EXPERIMENT = "ENGINE001_V43P4_B1_OWNER_CONSTRAINED_NATIVE_E3"
FROZEN_B0_RUN = 43983619222
FROZEN_B0_REPORT_SHA256 = "5e1b62ae38ca15fc55efac7edb1d2d8ce393c237e4d96f8221427c5c7a90dd3a"


def verified_b0(folder: Path):
    p = folder / "report.json"
    if not p.is_file() or sha(p) != FROZEN_B0_REPORT_SHA256:
        raise ValueError("BLOCKED_B0_DRIFT frozen B0 report SHA")
    r = json.loads(p.read_text(encoding="utf-8"))
    if (r.get("experiment") != "ENGINE001_V43P4_FULL_ADAPTIVE_FILL_B0_NATIVE_E3"
            or r.get("source_SHA256") != SOURCE_SHA
            or r.get("frozen_native_A_V44B_pixel_exact") is not True
            or r.get("b0", {}).get("original_paint_retained") != 0
            or r.get("b0", {}).get("V44B_410_detail_exact") is not True
            or r.get("quality_status") != "NUMERIC_FAIL"
            or r.get("b0", {}).get("paint_count") != 955):
        raise ValueError("BLOCKED_B0_DRIFT frozen B0 metadata")
    hashes = r.get("report_linked_SHA256")
    if not isinstance(hashes, dict) or len(hashes) != 17:
        raise ValueError("BLOCKED_B0_DRIFT manifest count")
    for name, digest in hashes.items():
        path = Path(name)
        if (path.is_absolute() or ".." in path.parts
                or not (folder / path).is_file()
                or sha(folder / path) != digest):
            raise ValueError("BLOCKED_B0_DRIFT manifest entry " + name)
    return r


def assemble_b1(source: dict, v44: dict) -> tuple[list, dict]:
    if (source.get("experiment") != SOURCE_EXPERIMENT
            or source.get("candidate") != "B1_SOURCE_ONLY"
            or source.get("safe_to_execute") is not False
            or source.get("original_A_paint_retained") != 0
            or source.get("original_B0_paint_retained") != 0
            or source.get("paint_count") != len(source.get("paint", []))):
        raise ValueError("B1 invalid registered source-only plan")
    entries = v44.get("strokes")
    if not isinstance(entries, list) or len(entries) != 2355:
        raise ValueError("B1 frozen A plan invalid")
    rgb_modes = {}
    for owner in COLORS:
        counts = Counter(e["stroke"]["colorRgb"] for e in entries[:1945]
                         if e["layer"] == "paint" and
                            e["stroke"]["colorIndex"] == owner)
        if not counts:
            raise ValueError("B1 owner lacks frozen A paint RGB")
        rgb_modes[owner] = min(counts, key=lambda rgb: (-counts[rgb], rgb))
    paint = []
    for entry in source["paint"]:
        s = copy.deepcopy(entry)
        owner = s.get("colorIndex")
        if (owner not in COLORS or s.get("width") not in (10, 6, 4, 2)
                or not s.get("strokeId", "").startswith(f"p4-b1-{owner}-")
                or not s["strokeId"][-5:].isdigit()
                or len(s["points"]) != 2):
            raise ValueError("B1 invalid owner/width/ID/vertices")
        s["colorRgb"] = rgb_modes[owner]
        paint.append(s)
    detail = [copy.deepcopy(x["stroke"]) for x in entries[1945:]]
    if (len(detail) != FROZEN_DETAILS or any(
            x["layer"] != "detail" for x in entries[1945:]) or
            detail != [e["stroke"] for e in entries[1945:]]):
        raise ValueError("B1 frozen colored V44-B detail drift")
    strokes = paint + detail
    vertices = sum(len(s["points"]) for s in strokes)
    if (len(strokes) > MAX_STROKES or vertices > MAX_VERTICES
            or len({x["strokeId"] for x in strokes}) != len(strokes)
            or len(strokes) != source["projected_total_strokes"]
            or vertices != source["projected_synthetic_vertices_NOT_CHALK"]):
        raise ValueError("BLOCKED_RESOURCE B1 native assembly")
    if any(s["strokeId"].startswith("icon-") or s["strokeId"].startswith("p4-b0-")
           for s in paint):
        raise ValueError("B1 retained old A/B0 paint")
    return strokes, {
        "new_paint_strokes": len(paint),
        "details_unchanged": len(detail),
        "vertices_NOT_CHALK": vertices,
        "original_A_paint_retained": 0,
        "original_B0_paint_retained": 0,
        "V44B_410_detail_exact_last": True,
        "frozen_A_mode_RGB_by_owner": {str(k):v for k,v in rgb_modes.items()},
    }


def main():
    ap = argparse.ArgumentParser()
    for name in ("workspace", "source", "v44-archive", "b0-archive", "output"):
        ap.add_argument("--" + name, type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError("B1 refuses overwrite of existing evidence")
    if sha(args.source) != SOURCE_SHA:
        raise ValueError("B1 original source SHA mismatch")
    frozen, native_a_png, frozen_v44_hashes = verified_v44(args.v44_archive)
    b0_report = verified_b0(args.b0_archive)
    original, _ = prepare_source(args.source)
    labels = original_labels(args.source)
    source = b1_source_plan(labels[::3, ::3][:, 155:305].copy())
    source["source_sha256"] = SOURCE_SHA
    source["source_labels_sha256"] = hashlib.sha256(
        labels[::3, ::3][:, 155:305].tobytes()).hexdigest()
    strokes, preflight = assemble_b1(source, frozen)
    output = args.output
    output.mkdir(parents=True)
    (output / "candidate-b1-native.json").write_text(
        json.dumps({"experiment": EXPERIMENT, "source": source,
                    "b1_preflight": preflight, "strokes": strokes},
                   ensure_ascii=False, indent=2, allow_nan=False)+"\n",
        encoding="utf-8")
    captures, measured, crops = {}, {}, {}
    warm = warm_mask(original)
    for variant in ("A", "B1"):
        folder = output / variant
        folder.mkdir()
        native = ([copy.deepcopy(e["stroke"]) for e in frozen["strokes"]]
                  if variant == "A" else strokes)
        renderer = ("renderV36SourceColoredContourProbe" if variant == "A"
                    else "renderV43P4B1OwnerConstrainedProbe")
        captures[variant], metadata, _ = native_batch(
            args.workspace, "V43P4B1-" + variant, native, folder,
            renderer_method=renderer)
        if set(captures[variant]) != set(SCENES):
            raise ValueError("B1 expected native scene set changed")
        if variant == "A":
            replay = png_pixel_exact_replay(
                native_a_png, folder / "V43P4B1-A-composite.png")
            if not replay["pixel_rgba_exact"]:
                raise ValueError("BLOCKED_BASELINE_DRIFT B1 A vs V44-B")
        measured[variant] = {
            **native_metrics(captures[variant], original, labels, warm),
            "native_owner_overlap": per_owner_native(captures[variant], labels),
            "metadata": metadata,
        }
        crops[variant] = logical_crop(captures[variant]["composite"])
        crops[variant].save(output / f"V43P4B1-{variant}-roi.png")
    with Image.open(args.b0_archive / "V43P4-B0-roi.png") as src:
        b0_crop = src.convert("RGB").copy()
    sheet([original, crops["A"], b0_crop, crops["B1"]],
          ["Original", "Frozen V44-B", "Frozen native B0 FAIL",
           "First B1 native"], output / "comparison-full.png")
    sheet([original, crops["A"], b0_crop, crops["B1"]],
          ["Original", "V44-B", "B0", "B1"],
          output / "comparison-faces.png", top=True)
    quality = {}
    for alpha in ALPHAS:
        per = measured["B1"]["native_owner_overlap"][str(alpha)]
        quality[str(alpha)] = {
            "all_class_recall_at_least_99pct": all(
                per[str(owner)]["correct_class_recall"] >= .99 for owner in COLORS),
            "foreign_more_than_3logical_px_zero": all(
                per[str(owner)]["foreign_overlap_excess_beyond_3logical_px"] == 0
                for owner in COLORS),
            "exterior_more_than_3logical_px_zero":
                measured["B1"]["native_class_metrics"][str(alpha)][
                    "painted_more_than_3_logical_px_from_source_foreground"] == 0,
        }
    quality["full_RGB_MAE_nonregression_vs_A"] = (
        measured["B1"]["source_RGB_MAE"] <= measured["A"]["source_RGB_MAE"])
    quality["warm_RGB_MAE_nonregression_vs_A"] = (
        measured["B1"]["warm_RGB_MAE"] <= measured["A"]["warm_RGB_MAE"])
    quality["provisional_numeric_pass_not_visual"] = all(
        v for row in quality.values() for v in (
            row.values() if isinstance(row, dict) else (row,)))
    b0 = b0_report["measurements"]["B0"]
    relative = {
        "B0_RGB_MAE": b0["source_RGB_MAE"],
        "B0_warm_MAE": b0["warm_RGB_MAE"],
        "B1_RGB_MAE": measured["B1"]["source_RGB_MAE"],
        "B1_warm_MAE": measured["B1"]["warm_RGB_MAE"],
        "B0_foreign_pixels_alpha24": {
            str(k): b0["native_owner_overlap"]["24"][str(k)][
                "foreign_required_class_native_pixels"] for k in COLORS},
        "B1_foreign_pixels_alpha24": {
            str(k): measured["B1"]["native_owner_overlap"]["24"][str(k)][
                "foreign_required_class_native_pixels"] for k in COLORS},
    }
    hashes = {str(f.relative_to(output)).replace("\\", "/"): sha(f)
              for f in output.rglob("*") if f.is_file()}
    report = {
        "experiment": EXPERIMENT,
        "status": "REAL_EGRET_E3_NOT_GAME",
        "source_sha256": SOURCE_SHA,
        "baseline_A_pixel_exact": True,
        "frozen_B0_report_sha256": FROZEN_B0_REPORT_SHA256,
        "frozen_B0_run": FROZEN_B0_RUN,
        "frozen_V44B_checksums": frozen_v44_hashes,
        "preflight": preflight,
        "measurements": measured, "quality": quality,
        "relative_to_immutable_B0": relative,
        "quality_accepted": False,
        "numeric_status": ("PASS_DIAGNOSTIC_NOT_VISUAL" if
            quality["provisional_numeric_pass_not_visual"] else
            "NUMERIC_FAIL"),
        "report_linked_SHA256": hashes,
        "E4": "NOT_RUN", "E5": "NOT_RUN",
        "game_exact_CHALK": None, "production_accepted": False,
        "versions": {"Python": platform.python_version(),
                     "NumPy": np.__version__},
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2,
                   allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"native_numeric": report["numeric_status"],
                      "preflight": preflight, "quality": quality,
                      "vs_B0": relative}, ensure_ascii=False))


if __name__ == "__main__":
    main()
