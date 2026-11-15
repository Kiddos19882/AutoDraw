#!/usr/bin/env python3
"""V40 archived genuine Egret internal 3-logical-pixel color overlap audit.

No brush approximation, source geometry changes or game quota claims.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_native_color_boundary_audit_v38 import (
    ALPHAS, COLORS, SCENES, SOURCE_EXPERIMENT, SOURCE_SHA, load_native,
    original_labels, sha,
)
from run_engine001_native_warm_color_v34 import mae, warm_mask
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_visual_roi_palette_v28 import prepare_source

EXPERIMENT = "ENGINE001_V40_INTERNAL_COLOR_TOLERANCE_AUDIT"
LOGICAL_ALLOWANCE_PX = 3
BACKING_SCALE = 3
ALLOWANCE_NATIVE_PX = LOGICAL_ALLOWANCE_PX * BACKING_SCALE


def overlap_by_class(
    labels: np.ndarray, owner: int, painted: np.ndarray,
    allowance_native_px: int = ALLOWANCE_NATIVE_PX,
) -> dict:
    """Measure actual owner-color alpha in other original source class regions.

    Exact Euclidean distance comes from frozen target pixels, not a brush model.
    """
    if labels.shape != painted.shape or labels.ndim != 2:
        raise ValueError("V40 mismatching actual native masks")
    if labels.dtype.kind not in "iu" or painted.dtype != np.bool_:
        raise ValueError("V40 wrong label/alpha mask types")
    if owner not in COLORS or type(allowance_native_px) is not int or allowance_native_px < 0:
        raise ValueError("V40 invalid source owner or tolerance")
    own_target = labels == owner
    if not own_target.any():
        raise ValueError("V40 missing source class")
    distance = cv2.distanceTransform(
        (~own_target).astype(np.uint8),
        cv2.DIST_L2, cv2.DIST_MASK_PRECISE,
    )
    foreign = painted & np.isin(labels, COLORS) & ~own_target
    allowed = foreign & (distance <= allowance_native_px)
    excess = foreign & (distance > allowance_native_px)
    per_recipient = {}
    for recipient in COLORS:
        if recipient == owner:
            continue
        region = foreign & (labels == recipient)
        per_recipient[str(recipient)] = {
            "total_foreign_native_pixels": int(np.count_nonzero(region)),
            "within_3logical_px_native_pixels": int(
                np.count_nonzero(region & (distance <= allowance_native_px))
            ),
            "beyond_3logical_px_native_pixels": int(
                np.count_nonzero(region & (distance > allowance_native_px))
            ),
        }
    target_count = int(np.count_nonzero(own_target))
    return {
        "target_class_native_pixels": target_count,
        "correct_class_native_pixels": int(np.count_nonzero(painted & own_target)),
        "correct_class_recall": float(np.count_nonzero(painted & own_target) / target_count),
        "foreign_required_class_native_pixels": int(np.count_nonzero(foreign)),
        "foreign_overlap_allowed_within_3logical_px": int(np.count_nonzero(allowed)),
        "foreign_overlap_excess_beyond_3logical_px": int(np.count_nonzero(excess)),
        "max_foreign_source_distance_native_px": (
            float(distance[foreign].max()) if foreign.any() else 0.0
        ),
        "by_foreign_target_class": per_recipient,
    }


def audit(source: Path, archived: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("V40 refuse overwrite of evidence")
    labels = original_labels(source)  # verifies frozen SHA/palette/board geometry
    src, _ = prepare_source(source)
    report = json.loads((archived / "report.json").read_text(encoding="utf-8"))
    if (report.get("experiment") != SOURCE_EXPERIMENT
            or report.get("original_source_SHA256") != SOURCE_SHA
            or report.get("V35_B_control_RGBA_pixel_exact") is not True
            or report.get("same_native_alpha_all_variants") is not True):
        raise ValueError("V40 frozen Egret original report failed identity check")
    for name, digest in report["report_linked_SHA256"].items():
        if sha(archived / name) != digest:
            raise ValueError("V40 frozen Egret file hash mismatch: " + name)
    rgba = {}
    for scene in SCENES:
        variants = {key: load_native(archived, key, scene) for key in "ABC"}
        for key in "BC":
            if not np.array_equal(variants["A"][:, :, 3], variants[key][:, :, 3]):
                raise ValueError("V40 frozen A/B/C native alpha mismatch " + scene)
        rgba[scene] = variants["C"]

    required_foreground = np.isin(labels, COLORS)
    silhouette_distance = cv2.distanceTransform(
        (~required_foreground).astype(np.uint8),
        cv2.DIST_L2, cv2.DIST_MASK_PRECISE,
    )
    logical_roi = np.zeros(labels.shape, dtype=bool)
    logical_roi[:, 155 * BACKING_SCALE:305 * BACKING_SCALE] = True
    results = {}
    for alpha in ALPHAS:
        by_owner = {}
        painted_union = np.zeros(labels.shape, dtype=bool)
        for owner in COLORS:
            painted = rgba[f"color-{owner}"][:, :, 3] >= alpha
            painted_union |= painted
            metrics = overlap_by_class(labels, owner, painted)
            metrics["painted_source_near_white_native_pixels"] = int(
                np.count_nonzero(painted & ~required_foreground & logical_roi))
            metrics["painted_outside_artwork_ROI_native_pixels"] = int(
                np.count_nonzero(painted & ~logical_roi))
            by_owner[str(owner)] = metrics
        foreign_total = sum(r["foreign_required_class_native_pixels"] for r in by_owner.values())
        excess_total = sum(r["foreign_overlap_excess_beyond_3logical_px"] for r in by_owner.values())
        allowed_total = sum(r["foreign_overlap_allowed_within_3logical_px"] for r in by_owner.values())
        if foreign_total != allowed_total + excess_total:
            raise AssertionError("V40 internal classification incomplete")
        results[str(alpha)] = {
            "per_paint_owner_class": by_owner,
            "total_foreign_required_class_native_pixels": foreign_total,
            "allowed_internal_overlap_native_pixels": allowed_total,
            "excess_internal_overlap_native_pixels": excess_total,
            "internal_3logical_px_diagnostic_PASS": excess_total == 0,
            "union_foreground_recall": float(np.count_nonzero(
                painted_union & required_foreground) / np.count_nonzero(required_foreground)),
            "fill_painted_farther_than_3logical_px_from_whole_silhouette": int(
                np.count_nonzero(
                    painted_union & ~required_foreground &
                    (silhouette_distance > ALLOWANCE_NATIVE_PX))),
            "fill_painted_outside_artwork_ROI_native_pixels": int(
                np.count_nonzero(painted_union & ~logical_roi)),
        }

    actual_final = logical_crop(rgba["composite"])
    final_comparison = {
        "actual_final_native_composite_SHA256": sha(
            archived / "C" / "V37P2-C-composite.png"),
        "all_410_dark_contours_on_top": True,
        "full_source_RGB_MAE": mae(actual_final, src),
        "warm_source_RGB_MAE": mae(actual_final, src, warm_mask(src)),
        "visible_foreign_class_attribution_from_final_RGB": "NOT_DETERMINED",
    }
    record = {
        "experiment": EXPERIMENT,
        "status": "E3_ARCHIVED_NATIVE_ALPHA_DIAGNOSTIC_ONLY",
        "frozen_source_sha256": SOURCE_SHA,
        "frozen_archive_report_sha256": sha(archived / "report.json"),
        "input_native_run": 43747149144,
        "input_native_SHA": "04e506a3bf41b5d197a19bb20e36e8f445d79dec",
        "native_Egret_alpha_ABC_exact": True,
        "logical_pixel_tolerance": LOGICAL_ALLOWANCE_PX,
        "native_backing_scale": BACKING_SCALE,
        "native_distance_tolerance_pixels": ALLOWANCE_NATIVE_PX,
        "native_alpha_thresholds": list(ALPHAS),
        "measurements": results,
        "final_composite_color_diagnostic": final_comparison,
        "quality_accepted": False,
        "game_exact_CHALK": None,
        "not_tested": [
            "new placement", "new live game E4", "independent E5",
            "game quota", "production required-color coverage >=99%",
            "visible class ownership after contour occlusion",
        ],
        "versions": {
            "Python": platform.python_version(),
            "OpenCV": cv2.__version__,
            "numpy": np.__version__,
            "Pillow": Image.__version__,
        },
    }
    output.mkdir(parents=True)
    (output / "internal-color-overlap.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment": EXPERIMENT,
        "thresholds": {a: {
            "foreign": x["total_foreign_required_class_native_pixels"],
            "allowed": x["allowed_internal_overlap_native_pixels"],
            "excess": x["excess_internal_overlap_native_pixels"],
            "internal_tolerance_pass": x["internal_3logical_px_diagnostic_PASS"],
        } for a, x in results.items()},
        "final_RGB_MAE": final_comparison["full_source_RGB_MAE"],
    }, indent=2))
    return record


def main():
    ap = argparse.ArgumentParser()
    for name in ("source", "v37p2-archive", "output"):
        ap.add_argument("--" + name, type=Path, required=True)
    args = ap.parse_args()
    audit(args.source, args.v37p2_archive, args.output)


if __name__ == "__main__":
    main()
