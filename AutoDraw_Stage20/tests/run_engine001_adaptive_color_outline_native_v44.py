#!/usr/bin/env python3
"""V44 native BoardPane/Egret A/B/C for color-only full V35-B outlines.

The original V37-P2-C color fill and all 410 detail polylines remain frozen.
"""
from __future__ import annotations
import argparse
import json
import platform
from pathlib import Path

import numpy as np

from engine001_paint_then_detail_v35 import native_strokes
from engine001_adaptive_color_outline_v44 import adaptive_recolor
from run_engine001_full_outline_native_v37 import frozen_full_outline
from run_engine001_local_fill_color_native_v37p2 import recolor_paint
from run_engine001_native_warm_color_v34 import SOURCE_SHA, sha, mae, warm_mask, png_pixel_exact_replay
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source, quantize_case, sheet

EXP = "ENGINE001_ADAPTIVE_COLOR_OUTLINE_V44_P1"


def validate_v37p2_archive(folder):
    """Reject missing or altered frozen native baseline evidence before rendering."""
    report_path = folder / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (report.get("experiment") != "ENGINE001_LOCAL_FILL_COLOR_V37_P2"
            or report.get("original_source_SHA256") != SOURCE_SHA
            or not report.get("V35_B_control_RGBA_pixel_exact")
            or not report.get("same_native_alpha_all_variants")):
        raise ValueError("V44 invalid frozen V37-P2 native report")
    c = report.get("metrics", {}).get("C", {})
    if (c.get("complete_detail_strokes") != 410
            or c.get("synthetic_accepted_vertices_NOT_CHALK") != 5682
            or c.get("changed_fill_strokes") != 166):
        raise ValueError("V44 frozen V37-P2-C count/identity drift")
    checksums = report.get("report_linked_SHA256")
    baseline = "C/V37P2-C-composite.png"
    if not isinstance(checksums, dict) or baseline not in checksums:
        raise ValueError("V44 missing pinned baseline manifest entry")
    for name, digest in checksums.items():
        relative = Path(name)
        if (relative.is_absolute() or ".." in relative.parts
                or not isinstance(digest, str) or len(digest) != 64):
            raise ValueError("V44 unsafe archive manifest")
        path = folder / relative
        if not path.is_file() or sha(path) != digest:
            raise ValueError("V44 altered native V37-P2 archive: " + name)
    return folder / baseline


def main():
    ap = argparse.ArgumentParser()
    for name in ("workspace", "source", "v35-archive", "v37p2-archive", "output"):
        ap.add_argument("--" + name, required=True, type=Path)
    args = ap.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError("V44 refuse overwrite experiment evidence")
    if sha(args.source) != SOURCE_SHA:
        raise ValueError("V44 source SHA mismatch")
    src, canvas = prepare_source(args.source)
    labels, _, skipped = quantize_case(src, canvas, 8, False, True)
    if skipped != [0, 1, 2, 3]:
        raise ValueError("V44 source palette changed")
    warm = warm_mask(src)
    frozen_native_baseline = validate_v37p2_archive(args.v37p2_archive)
    v35 = frozen_full_outline(args.v35_archive)
    baseline, _, changed = recolor_paint(v35, src, labels, warm, "C")
    if changed != 166:
        raise ValueError("V44 V37-P2-C paint baseline mismatch")

    plans, journals = {}, {}
    for key in "ABC":
        plans[key], journals[key] = adaptive_recolor(baseline, src, key)
    out = args.output
    out.mkdir(parents=True)
    (out / "color-plans.json").write_text(json.dumps({
        "experiment": EXP, "baseline": "V37-P2-C",
        "outline_color_journal": journals, "plans": plans
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    native, crops, metrics = {}, {}, {}
    for key in "ABC":
        dest = out / key
        dest.mkdir()
        scenes, metadata, _ = native_batch(
            args.workspace, "V44-" + key, native_strokes(plans[key]), dest,
            renderer_method="renderV36SourceColoredContourProbe")
        native[key] = scenes
        im = logical_crop(scenes["composite"])
        crops[key] = im
        im.save(out / ("V44-" + key + "-roi.png"))
        rgb = [e["stroke"]["colorRgb"] for e in plans[key]["strokes"][1945:]]
        counts = {reason: sum(j["decision"] == reason for j in journals[key])
                  for reason in ("baseline", "source", "darkened", "unresolved", "missing_sides")}
        metrics[key] = {
            "full_RGB_MAE": mae(im, src),
            "warm_RGB_MAE": mae(im, src, warm),
            "contour_decisions": counts,
            "distinct_contour_RGB": len(set(rgb)),
            "contour_color_switches": sum(a != b for a, b in zip(rgb, rgb[1:])),
            "strokes": 2355,
            "detail_strokes": 410,
            "synthetic_vertices_NOT_CHALK": 5682,
            "native_composite_alpha24": int(np.count_nonzero(scenes["composite"][:, :, 3] >= 24)),
            "metadata": metadata,
        }
    replay = png_pixel_exact_replay(
        frozen_native_baseline, out / "A" / "V44-A-composite.png")
    if not replay["pixel_rgba_exact"]:
        raise ValueError("V44 native A differs from frozen V37-P2-C")
    for stem in ["composite", "color-100"] + [f"color-{n}" for n in (4, 5, 6, 7)]:
        if not (np.array_equal(native["A"][stem][:, :, 3], native["B"][stem][:, :, 3])
                and np.array_equal(native["A"][stem][:, :, 3], native["C"][stem][:, :, 3])):
            raise ValueError("V44 changed native alpha brush footprint " + stem)
    sheet([src, crops["A"], crops["B"], crops["C"]],
          ["Original", "V37-P2-C dark outline", "Source RGB contour", "Contrast-protected contour"],
          out / "comparison-full.png")
    sheet([src, crops["A"], crops["B"], crops["C"]],
          ["Original", "Dark baseline", "Source RGB", "Adaptive contrast"],
          out / "comparison-faces.png", top=True)
    hashes = {str(f.relative_to(out)).replace("\\", "/"): sha(f)
              for f in out.rglob("*") if f.is_file()}
    report = {
        "experiment": EXP, "status": "REAL_EGRET_E3_DIAGNOSTIC_NOT_GAME",
        "source_sha256": SOURCE_SHA, "control_V37P2C_RGBA_exact": True,
        "native_alpha_exact_all_variants": True,
        "metrics": metrics, "report_linked_SHA256": hashes,
        "color_diagnostic": {k: {
            "full_RGB_nonregression": metrics[k]["full_RGB_MAE"] <= metrics["A"]["full_RGB_MAE"],
            "warm_RGB_nonregression": metrics[k]["warm_RGB_MAE"] <= metrics["A"]["warm_RGB_MAE"],
        } for k in ("B", "C")},
        "quality_accepted": False, "exact_CHALK": None,
        "not_tested": ["live game E4", "independent E5", "per-color >=99% acceptance"],
        "versions": {"python": platform.python_version(), "numpy": np.__version__},
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
    print(json.dumps({"metrics": {k: {
        "full_RGB_MAE": metrics[k]["full_RGB_MAE"],
        "warm_RGB_MAE": metrics[k]["warm_RGB_MAE"],
        "contour_decisions": metrics[k]["contour_decisions"],
    } for k in "ABC"}, "diagnostic": report["color_diagnostic"]}, indent=2))


if __name__ == "__main__":
    main()
