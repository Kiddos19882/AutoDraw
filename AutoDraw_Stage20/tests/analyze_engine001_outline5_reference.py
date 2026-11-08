#!/usr/bin/env python3
"""ENGINE001_NATIVE_ENDPOINT_OUTLINE5_V1: compare native Egret outline to OpenCV.

The fixed extra contour is a closed 5-LOGICAL-px native Painter stroke along
the 3-logical-px inset of the pinned rectangle target. This is NOT a 5px
dilation, not an adjustment of all scanline brush widths, and not a measured
live FILL-001 contour. Board raster is 3x logical size; no screen mapping.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from analyze_engine001_endpoint_reference import (
    EXPECTED_MONITOR_BLOB,
    EXPECTED_PLAN_BLOB,
    HEIGHT,
    MONITOR_REL,
    PLAN_REL,
    ROWS,
    SCALE,
    THRESHOLDS,
    VARIANTS,
    WIDTH,
    agreement,
    bounds,
    png_rgba,
    require_git_blob,
)


def _metrics(mask: np.ndarray, target: np.ndarray) -> dict:
    covered = int(np.count_nonzero(mask & target))
    outside = int(np.count_nonzero(mask & ~target))
    area = int(np.count_nonzero(target))
    return {
        "target_pixels_board_backing": area,
        "covered_target_pixels": covered,
        "uncovered_target_pixels": area - covered,
        "leakage_pixels": outside,
        "coverage_fraction": round(covered / area, 9),
        "hypothetical_board_quality_pass": covered / area >= 0.99 and outside == 0,
    }


def _open_cv_round_capped_contour(pts: list[list[int]]) -> np.ndarray:
    # Independent binary 3x OpenCV reference with 15 backing-px thickness.
    canvas = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        start = (int(a[0]) * SCALE, int(a[1]) * SCALE)
        end = (int(b[0]) * SCALE, int(b[1]) * SCALE)
        cv2.line(canvas, start, end, color=1, thickness=5 * SCALE, lineType=cv2.LINE_8)
        cv2.circle(canvas, start, 8, color=1, thickness=-1, lineType=cv2.LINE_8)
        cv2.circle(canvas, end, 8, color=1, thickness=-1, lineType=cv2.LINE_8)
    return canvas.astype(bool)


def _diff_image(target: np.ndarray, old: np.ndarray, new: np.ndarray) -> Image.Image:
    rgb = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    rgb[target] = (52, 52, 52)
    rgb[target & old] = (174, 174, 174)
    rgb[~target & old] = (187, 67, 195)
    rgb[target & new & ~old] = (38, 202, 95)
    rgb[~target & new & ~old] = (244, 146, 57)
    rgb[target & ~new] = (215, 51, 60)
    return Image.fromarray(rgb, "RGB")


def analyze(workspace: Path, reference_dir: Path, output_dir: Path) -> dict:
    root = workspace / "AutoDraw_Stage20" / "source" / "preparation"
    sys.path.insert(0, str(root))
    from chalk_fill_experiment import (
        FILL001_EXPECTED_MASK_SHA256,
        build_fill_target_mask,
        fill_target_mask_sha256,
    )
    from chalk_fill_strategy_comparison import _contour_stroke
    require_git_blob(workspace, MONITOR_REL, EXPECTED_MONITOR_BLOB)
    require_git_blob(workspace, PLAN_REL, EXPECTED_PLAN_BLOB)
    original = json.loads(
        (reference_dir / "engine001-native-endpoint-v1.json").read_text("utf-8-sig"))
    augmented = json.loads(
        (reference_dir / "engine001-native-endpoint-outline5-v1.json").read_text("utf-8-sig"))
    if (original.get("experimentId") != "ENGINE001_NATIVE_ENDPOINT_V1"
            or augmented.get("experimentId") != "ENGINE001_NATIVE_ENDPOINT_OUTLINE5_V1"
            or augmented.get("status") != "COMPLETE_OFFLINE_NATIVE_ENGINE_MEASUREMENT"
            or original.get("runId") != augmented.get("runId")
            or original.get("sessionId") != augmented.get("sessionId")
            or original.get("monitorInputBlobSha") != EXPECTED_MONITOR_BLOB
            or augmented.get("monitorInputBlobSha") != EXPECTED_MONITOR_BLOB
            or original.get("strokeCount") != augmented.get("strokeCount") != 27
            or augmented.get("strokeCount") != 27
            or original.get("acceptedCount") != 1260
            or augmented.get("acceptedCount") != 1260
            or augmented.get("exactHistoricalChalk") != 1260
            or original.get("screenProjection") != "UNCALIBRATED"
            or augmented.get("screenProjection") != "UNCALIBRATED"
            or augmented.get("isolatedRows") != list(ROWS)
            or original.get("isolatedRows") != list(ROWS)
            or augmented.get("aggregate", {}).get("smooth-drawlast", {}).get(
                "nativePainterPatchedCalls") != 54):
        raise ValueError("Native endpoint/outline paired provenance is incomplete")

    frozen = build_fill_target_mask("rectangle")
    if fill_target_mask_sha256("rectangle", frozen) != FILL001_EXPECTED_MASK_SHA256["rectangle"]:
        raise ValueError("Frozen rectangle target SHA is invalid")
    expected = _contour_stroke(frozen, 3, 5)
    expected_pts = [list(p) for p in expected["points"]]
    o = augmented.get("outline5")
    if (not isinstance(o, dict)
            or o.get("widthLogical") != 5
            or o.get("insetLogical") != 3
            or o.get("mode") != "native_normal_closed_contour"
            or o.get("vertexCount") != len(expected_pts)
            or o.get("appendedPointCount") != len(expected_pts) + 1
            or o.get("additionalChalk") != "NOT_MEASURED"
            or o.get("points") != expected_pts):
        raise ValueError("Native outline vertices do not match pinned OpenCV eroded mask")
    if len(expected_pts) != 64:
        raise ValueError("Expected original fixed rectangle contour of 64 vertices")
    target = np.repeat(np.repeat(frozen, SCALE, axis=0), SCALE, axis=1)
    if target.shape != (HEIGHT, WIDTH) or int(np.count_nonzero(frozen)) != 44653:
        raise ValueError("Target board shape or reference area changed")
    reference_outline = _open_cv_round_capped_contour(expected_pts)
    if not np.any(reference_outline):
        raise ValueError("OpenCV outline reference is empty")

    expected_pngs = []
    for prefix in ("engine001-endpoint-", "engine001-endpoint-outline5-"):
        for mode in VARIANTS:
            for backend in ("canvas2d", "webgl"):
                expected_pngs.append(f"{prefix}{mode}-all-{backend}.png")
            for row in ROWS:
                expected_pngs.append(f"{prefix}{mode}-row{row}-webgl.png")
    png_hashes = {}
    png_alpha = {}
    for path_name in expected_pngs:
        rgba, digest = png_rgba(reference_dir / path_name)
        png_hashes[path_name] = digest
        png_alpha[path_name] = rgba[:, :, 3]
    if len(png_hashes) != 30:
        raise ValueError("Expected exactly 30 named baseline/outline renderer PNG")

    by_threshold = {}
    output_dir.mkdir(parents=True, exist_ok=True)
    for threshold in THRESHOLDS:
        per_variant = {}
        native_masks = {}
        for variant in VARIANTS:
            old = png_alpha[f"engine001-endpoint-{variant}-all-webgl.png"] >= threshold
            new = png_alpha[f"engine001-endpoint-outline5-{variant}-all-webgl.png"] >= threshold
            native_masks[variant] = new
            old_2d = png_alpha[f"engine001-endpoint-{variant}-all-canvas2d.png"] >= threshold
            new_2d = png_alpha[f"engine001-endpoint-outline5-{variant}-all-canvas2d.png"] >= threshold
            added = new & ~old
            removed = old & ~new
            missing_before = target & ~old
            missed_recovered = int(np.count_nonzero(added & missing_before))
            new_leakage = int(np.count_nonzero(added & ~target))
            old_leakage = int(np.count_nonzero(old & ~target))
            hypothetical_model_add = old | reference_outline
            per_variant[variant] = {
                "original_board_target_metrics": _metrics(old, target),
                "plus_native_5px_outline_board_target_metrics": _metrics(new, target),
                "added_backing_pixels": int(np.count_nonzero(added)),
                "removed_backing_pixels": int(np.count_nonzero(removed)),
                "recovered_missing_board_backing_target_pixels": missed_recovered,
                "new_leakage_backing_pixels": new_leakage,
                "old_leakage_backing_pixels": old_leakage,
                "additive_union_new_leakage_check": old_leakage + new_leakage,
                "original_vs_contoured_native_webgl": agreement(old, new),
                "original_egret_canvas2d_vs_webgl": agreement(old_2d, old),
                "contoured_egret_canvas2d_vs_webgl": agreement(new_2d, new),
                "native_contoured_vs_opencv_added_contour": agreement(new, hypothetical_model_add),
                "native_added_pixels_vs_opencv_added_pixels": agreement(
                    added, reference_outline & ~old),
            }
            if threshold == 128:
                _diff_image(target, old, new).save(
                    output_dir / f"{variant}-added-native-outline5-vs-target-3x.png")
        by_threshold[str(threshold)] = {
            "per_variant": per_variant,
            "native_contoured_game_vs_forced_smooth": agreement(
                native_masks["game-smooth"], native_masks["smooth-drawlast"]),
            "native_contoured_forced_smooth_vs_normal": agreement(
                native_masks["smooth-drawlast"], native_masks["normal"]),
        }

    per_stroke = {}
    for row in ROWS:
        per_variant = {}
        for variant in VARIANTS:
            a = png_alpha[f"engine001-endpoint-{variant}-row{row}-webgl.png"]
            b = png_alpha[f"engine001-endpoint-outline5-{variant}-row{row}-webgl.png"]
            measured = {}
            for threshold in THRESHOLDS:
                prev, outlined = a >= threshold, b >= threshold
                # A perimeter contour may cover the original endpoint and obscure
                # its measurement. Keep both old and new bounds explicitly.
                run_y = float(original["individual"][list(ROWS).index(row)]["lastAccepted"]["y"])
                x0 = bounds(prev, run_y)
                x1 = bounds(outlined, run_y)
                measured[str(threshold)] = {
                    "original_edge": x0, "outlined_edge": x1,
                    "added": int(np.count_nonzero(outlined & ~prev)),
                    "removed": int(np.count_nonzero(prev & ~outlined)),
                    "contour_occluded_endpoint": x1["right_backing_x"] != x0["right_backing_x"],
                }
            per_variant[variant] = measured
        per_stroke[str(row)] = per_variant

    result = {
        "schemaVersion": 1,
        "experimentId": "ENGINE001_NATIVE_ENDPOINT_OUTLINE5_OPENCV_V1",
        "status": "COMPLETE_OFFLINE_BOARD_LOCAL_COMPARISON",
        "sourceRunId": original["runId"], "sourceSessionId": original["sessionId"],
        "historicalChalkUnchanged": 1260, "additionalOutlineChalk": "NOT_MEASURED",
        "inputGitBlobs": {"monitor": EXPECTED_MONITOR_BLOB,
                          "plan": EXPECTED_PLAN_BLOB,
                          "frozenTarget": FILL001_EXPECTED_MASK_SHA256["rectangle"]},
        "geometry": {
            "outlineWidthLogical": 5, "contourInsetLogical": 3,
            "contourVertexCount": len(expected_pts), "closed": True,
            "nativePainterMode": "normal_for_all_variants",
            "outlineConstruction": "OpenCV elliptical erosion of frozen target plus connected CHAIN_APPROX_SIMPLE contour",
            "logicalBoard": [460, 240], "backingCanvas": [WIDTH, HEIGHT],
            "targetRaster": "nearest_neighbour_3x_repetition_of_frozen_logical_mask",
            "opencVComparator": "LINE_8 round-capped segments 15 backing px width, cap circle radius 8",
            "screenTransform": "UNAVAILABLE_NOT_APPLIED",
        },
        "frozenSourcePngCount": 30,
        "pngSha256": png_hashes,
        "byAlphaThreshold": by_threshold,
        "isolatedRows": per_stroke,
        "actualFill001": {
            "status": "UNCHANGED_REJECTED",
            "liveCoverage": 0.984306, "liveLeakagePixels": 11,
            "screenUncoveredPixels": 1116,
            "screenRightMisses": 499,
            "screenMappingValid": False,
            "comparisonToHistoricalScreenResidual": "BLOCKED_NO_SAME_RUN_GEOMETRY",
        },
        "interpretation": [
            "Board-local model only; no FILL-001 live PNG projection",
            "Chosen contour width 5 is stroke thickness, inset 3 is centerline displacement",
            "Historical accepted points remain fixed; added native contour is a hypothetical extra stroke",
            "Model coverage/leakage is not live quality acceptance",
            "Contour can occlude isolated stroke-end bounds; compare old/new carefully",
            "Native original per-stroke smooth mode is an unproven research assumption",
        ],
    }
    (output_dir / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for v in VARIANTS:
        k = by_threshold["128"]["per_variant"][v]
        print(f"ENGINE-001 outline5 {v}: added={k['added_backing_pixels']} "
              f"recovered-board-target={k['recovered_missing_board_backing_target_pixels']} "
              f"new-leak={k['new_leakage_backing_pixels']} "
              f"coverage={k['plus_native_5px_outline_board_target_metrics']['coverage_fraction']}")
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True, type=Path)
    p.add_argument("--reference-dir", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    analyze(args.workspace.resolve(), args.reference_dir.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()
