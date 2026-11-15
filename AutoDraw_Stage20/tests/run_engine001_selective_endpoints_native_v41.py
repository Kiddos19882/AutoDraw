#!/usr/bin/env python3
"""V41 native real-Egret-alpha selected horizontal endpoint extension, NOT game."""
from __future__ import annotations

import argparse
import copy
import json
import platform
from pathlib import Path

import cv2
import numpy as np

from engine001_paint_then_detail_v35 import native_strokes
from run_engine001_boundary_shift_native_v39 import verified_input, native_metrics
from run_engine001_internal_color_tolerance_v40 import overlap_by_class
from run_engine001_native_color_boundary_audit_v38 import (
    COLORS, load_native, original_labels,
)
from run_engine001_native_warm_color_v34 import (
    SOURCE_SHA, sha, warm_mask, png_pixel_exact_replay,
)
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source, sheet

EXPERIMENT = "ENGINE001_V41_SELECTIVE_EGRET_ALPHA_ENDPOINT"
AMPLITUDES = {"A": 0.0, "B": 0.25, "C": 0.5}


def selected_plan(base: dict, labels3: np.ndarray, archived_alpha: dict,
                  extension: float) -> tuple[dict, list[dict]]:
    if extension not in AMPLITUDES.values():
        raise ValueError("V41 unregistered extension")
    if (base.get("paint_strokes"), base.get("detail_strokes"),
            base.get("synthetic_vertices_NOT_CHALK"),
            len(base.get("strokes", []))) != (1945, 410, 5682, 2355):
        raise ValueError("V41 frozen full-outline identity drift")
    if labels3.shape != (720, 1380):
        raise ValueError("V41 source labels native shape drift")
    if set(archived_alpha) != set(COLORS) or any(
            a.shape != (720, 1380) or a.dtype != np.uint8
            for a in archived_alpha.values()):
        raise ValueError("V41 native Egret source alpha invalid")
    out = copy.deepcopy(base)
    decisions = []
    for i, (before, now) in enumerate(zip(base["strokes"], out["strokes"])):
        if i >= 1945:
            if before != now or now["layer"] != "detail":
                raise ValueError("V41 modified user-preferred 410 contours")
            continue
        old, stroke = before["stroke"], now["stroke"]
        if (now["layer"] != "paint" or old["width"] != 2
                or old["colorIndex"] not in COLORS or len(old["points"]) != 2
                or old["points"][0]["y"] != old["points"][1]["y"]
                or old["points"][0]["x"] > old["points"][1]["x"]):
            raise ValueError("V41 invalid original fill pair")
        for side, sign, j in (("start", -1, 0), ("end", 1, 1)):
            point = old["points"][j]
            x, y = float(point["x"]), float(point["y"])
            probe_x = x + sign * (1.0 + extension)
            valid = (155 <= x <= 304.75 and 155 <= probe_x <= 304.75
                     and 0 <= y < 240)
            native_x = max(0, min(1379, round(probe_x * 3)))
            native_y = max(0, min(719, round(y * 3)))
            source_x = max(155, min(304, round(probe_x)))
            source_y = max(0, min(239, round(y)))
            own = bool(valid and labels3[source_y * 3, source_x * 3]
                       == old["colorIndex"])
            alpha = int(archived_alpha[old["colorIndex"]][native_y, native_x]) if valid else None
            selected = bool(valid and own and alpha is not None and alpha < 24)
            # A is guaranteed no-op, even if an endpoint has source-edge support.
            dx = sign * extension if selected and extension else 0.0
            moved = max(155.0, min(304.75, x + dx)) if dx else x
            stroke["points"][j]["x"] = moved
            decisions.append({
                "id": old["strokeId"], "side": side, "source_color": old["colorIndex"],
                "probe_x": probe_x, "probe_y": y, "probe_source_owner": (
                    int(labels3[source_y * 3, source_x * 3]) if valid else None),
                "frozen_Egret_alpha": alpha, "eligible": selected,
                "applied_dx": moved - x,
            })
        if (stroke["points"][0]["x"] > stroke["points"][1]["x"] or
                any(stroke["points"][j]["y"] != old["points"][j]["y"]
                    for j in (0, 1))):
            raise ValueError("V41 endpoints reordered or y moved")
        if ({k: v for k, v in old.items() if k != "points"} !=
                {k: v for k, v in stroke.items() if k != "points"}):
            raise ValueError("V41 altered paint attributes")
    if (len(decisions) != 3890 or len(out["strokes"]) != 2355 or
            sum(len(item["stroke"]["points"]) for item in out["strokes"]) != 5682):
        raise ValueError("V41 synthetic accepted points changed")
    return out, decisions


def main():
    parser = argparse.ArgumentParser()
    for item in ("workspace", "source", "v37p2-archive", "output"):
        parser.add_argument("--" + item, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("V41 refuse to overwrite frozen evidence")
    if sha(args.source) != SOURCE_SHA:
        raise ValueError("V41 original image SHA drift")
    src, _ = prepare_source(args.source)
    labels = original_labels(args.source)
    base = verified_input(args.v37p2_archive)
    frozen = {c: load_native(args.v37p2_archive, "C", f"color-{c}")[:, :, 3]
              for c in COLORS}
    variants, selections = {}, {}
    for key, amplitude in AMPLITUDES.items():
        variants[key], selections[key] = selected_plan(base, labels, frozen, amplitude)
    out = args.output
    out.mkdir(parents=True)
    (out / "candidate-plans.json").write_text(json.dumps({
        "experiment": EXPERIMENT, "plans": variants, "decisions": selections
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    warm = warm_mask(src)
    foreground = np.isin(labels, COLORS)
    distance = cv2.distanceTransform(
        (~foreground).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    metrics, native, crops = {}, {}, {}
    for key in "ABC":
        directory = out / key
        directory.mkdir()
        rgba, meta, _ = native_batch(
            args.workspace, "V41-" + key, native_strokes(variants[key]),
            directory, renderer_method="renderV36SourceColoredContourProbe")
        native[key] = rgba
        crop = logical_crop(rgba["composite"])
        crops[key] = crop
        crop.save(out / ("V41-" + key + "-roi.png"))
        row = native_metrics(rgba, src, labels, warm)
        over = {}
        for alpha in (24, 128):
            foreign = {}
            union = np.zeros(labels.shape, dtype=bool)
            for color in COLORS:
                painted = rgba[f"color-{color}"][:, :, 3] >= alpha
                union |= painted
                foreign[str(color)] = overlap_by_class(labels, color, painted)
            over[str(alpha)] = {
                "internal_allowed_native_pixels": sum(
                    x["foreign_overlap_allowed_within_3logical_px"]
                    for x in foreign.values()),
                "internal_excess_native_pixels": sum(
                    x["foreign_overlap_excess_beyond_3logical_px"]
                    for x in foreign.values()),
                "exterior_excess_native_pixels": int(np.count_nonzero(
                    union & ~foreground & (distance > 9))),
                "per_color": foreign,
            }
        row["internal_and_external_tolerance"] = over
        row["eligible_endpoints"] = sum(x["eligible"] for x in selections[key])
        row["changed_endpoints"] = sum(abs(x["applied_dx"]) > 0 for x in selections[key])
        row["changed_fill_strokes"] = len(set(
            x["id"] for x in selections[key] if abs(x["applied_dx"]) > 0))
        row["renderer_metadata"] = meta
        metrics[key] = row

    replay = png_pixel_exact_replay(
        args.v37p2_archive / "C" / "V37P2-C-composite.png",
        out / "A" / "V41-A-composite.png")
    if not replay["pixel_rgba_exact"]:
        raise ValueError("V41 native original baseline RGBA changed")
    for key in "BC":
        if not np.array_equal(native["A"]["color-100"][:, :, 3],
                              native[key]["color-100"][:, :, 3]):
            raise ValueError("V41 all 410 dark outlines changed")
    sheet([src, crops["A"], crops["B"], crops["C"]],
          ["Original", "Frozen V37-P2 C", "V41 0.25 selective",
           "V41 0.5 selective"], out / "comparison-full.png")
    sheet([src, crops["A"], crops["B"], crops["C"]],
          ["Original", "Frozen full contour", "Selected 0.25",
           "Selected 0.5"], out / "comparison-faces.png", top=True)

    decisions = {}
    base_alpha24 = metrics["A"]["native_class_metrics"]["24"]
    for key in "BC":
        comparison = metrics[key]["native_class_metrics"]["24"]
        reference = [base_alpha24["class_recall_and_overlap"][str(c)]["correct_class_recall"]
                     for c in COLORS]
        candidate = [comparison["class_recall_and_overlap"][str(c)]["correct_class_recall"]
                     for c in COLORS]
        checks = {
            "all_class_recall_nonregression": all(b >= a for a, b in zip(reference, candidate)),
            "one_class_strict_gain": any(b > a for a, b in zip(reference, candidate)),
            "silhouette_recall_nonregression": (
                comparison["union_source_foreground_recall"] >=
                base_alpha24["union_source_foreground_recall"]),
            "internal_3px_excess_zero_alpha24_and128": all(
                metrics[key]["internal_and_external_tolerance"][str(alpha)]
                ["internal_excess_native_pixels"] == 0 for alpha in (24, 128)),
            "external_3px_nonregression_alpha24_and128": all(
                metrics[key]["internal_and_external_tolerance"][str(alpha)]
                ["exterior_excess_native_pixels"] <=
                metrics["A"]["internal_and_external_tolerance"][str(alpha)]
                ["exterior_excess_native_pixels"] for alpha in (24, 128)),
            "full_RGB_MAE_nonregression": (
                metrics[key]["source_RGB_MAE"] <= metrics["A"]["source_RGB_MAE"]),
            "warm_RGB_MAE_nonregression": (
                metrics[key]["warm_RGB_MAE"] <= metrics["A"]["warm_RGB_MAE"]),
        }
        decisions[key] = {"checks": checks, "numeric_diagnostic_PASS": all(checks.values())}
    hashes = {str(p.relative_to(out)).replace("\\", "/"): sha(p)
              for p in out.rglob("*") if p.is_file()}
    report = {
        "experiment": EXPERIMENT,
        "status": "E3_TRUE_EGRET_NOT_GAME",
        "original_source_sha256": SOURCE_SHA,
        "V37P2_C_control_pixel_exact": True,
        "full_410_dark_contour_alpha_exact": True,
        "strokes": 2355,
        "synthetic_vertices_NOT_CHALK": 5682,
        "measurement": metrics,
        "predeclared_decisions": decisions,
        "artifacts_SHA256": hashes,
        "production_quality_accepted": False,
        "exact_game_CHALK": None,
        "not_tested": ["live E4", "independent E5", "exact CHALK",
                       "game quota", "semantic each-color>=99%"],
        "versions": {"Python": platform.python_version(),
                     "numpy": np.__version__, "cv2": cv2.__version__},
    }
    (out / "report.json").write_text(json.dumps(
        report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "changed_endpoints": {k: metrics[k]["changed_endpoints"] for k in "ABC"},
        "RGB_MAE": {k: metrics[k]["source_RGB_MAE"] for k in "ABC"},
        "quality_numeric": decisions,
    }, indent=2))


if __name__ == "__main__":
    main()
