#!/usr/bin/env python3
"""ENGINE001_DUPLICATE_FRAMES_V1: independent native Egret RGBA/alpha PNG audit.

No same-run screen or ENTER_FRAME timeline exists for archived FILL-001.
This script does not invent it, alter CHALK or project to the screenshot ROI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from analyze_engine001_endpoint_reference import (
    EXPECTED_MONITOR_BLOB,
    MONITOR_REL,
    THRESHOLDS,
    WIDTH,
    HEIGHT,
    png_rgba,
    require_git_blob,
)

COUNTS = (0, 1, 3)
PATHS = (70, 97, 151)
RUN = "6a17a297-ea14-4527-9527-bfd8de3bd335"
SESSION = "bb261898-8296-41f5-a333-eb0b81016410"


def rgba_compare(a: np.ndarray, b: np.ndarray) -> dict:
    if a.shape != b.shape or a.shape != (HEIGHT, WIDTH, 4):
        raise ValueError("Mismatched native renderer RGBA dimensions")
    absdiff = np.abs(a.astype(np.int16) - b.astype(np.int16))
    different = np.any(absdiff != 0, axis=2)
    result = {
        "different_rgba_pixels": int(np.count_nonzero(different)),
        "max_channel_difference": int(absdiff.max()),
        "mean_differing_channel_difference": (
            round(float(absdiff[absdiff != 0].mean()), 9)
            if np.any(absdiff) else 0.0
        ),
    }
    by_alpha = {}
    for threshold in THRESHOLDS:
        x, y = a[:, :, 3] >= threshold, b[:, :, 3] >= threshold
        by_alpha[str(threshold)] = {
            "newly_covered_backing_pixels": int(np.count_nonzero(y & ~x)),
            "removed_backing_pixels": int(np.count_nonzero(x & ~y)),
            "changed_mask_pixels": int(np.count_nonzero(x != y)),
            "reference_covered_backing_pixels": int(np.count_nonzero(x)),
            "candidate_covered_backing_pixels": int(np.count_nonzero(y)),
        }
    result["by_alpha_threshold"] = by_alpha
    return result


def analyze(workspace: Path, reference_dir: Path, output_dir: Path) -> dict:
    require_git_blob(workspace, MONITOR_REL, EXPECTED_MONITOR_BLOB)
    run = json.loads((workspace / MONITOR_REL).read_text("utf-8"))
    manifest = json.loads(
        (reference_dir / "engine001-duplicate-frames-v1.json").read_text("utf-8-sig"))
    older = json.loads(
        (reference_dir / "engine001-temporal-accepted-only-v1.json").read_text("utf-8-sig"))
    if (manifest.get("experimentId") != "ENGINE001_DUPLICATE_FRAMES_V1"
            or manifest.get("status") != "COMPLETE_OFFLINE_NATIVE_FRAME_EXPERIMENT"
            or manifest.get("runId") != run.get("run_id") or manifest["runId"] != RUN
            or manifest.get("sessionId") != run.get("session_id")
            or manifest["sessionId"] != SESSION
            or manifest.get("historicalExactChalk") != 1260
            or manifest.get("acceptedPoints") != 1260
            or manifest.get("strokeCount") != 27
            or manifest.get("screenProjection") != "UNCALIBRATED"
            or manifest.get("monitorInputBlobSha") != EXPECTED_MONITOR_BLOB
            or manifest.get("extraFrameCounts") != list(COUNTS)
            or manifest.get("pngCount") != 6
            or older.get("experimentId") != "ENGINE001_TEMPORAL_ACCEPTED_ONLY_V1"
            or older.get("runId") != RUN or older.get("sessionId") != SESSION
            or older.get("exactHistoricalChalk") != 1260):
        raise ValueError("Duplicate-frame input or original temporal source differs")
    if len(manifest.get("samples", [])) != 3 or len(manifest.get("comparisons", [])) != 3:
        raise ValueError("Expected exactly three native frame cases")
    for index, count in enumerate(COUNTS):
        s = manifest["samples"][index]
        if (s["extraStationaryFramesPerStroke"] != count
                or s["totalSyntheticFrameCallbacks"] != count * 27
                or s["acceptedPoints"] != 1260
                or s["duplicatePointRejections"] != count * 27
                or s["extraFrameRedrawCalls"] != count * 27
                or s["graphicsPathCount"] != PATHS[index]):
            raise ValueError("Native extra frame count / Graphics path guard failure")
    imgs = {}
    hashes = {}
    for count in COUNTS:
        for backend in ("canvas2d", "webgl"):
            name = f"engine001-frames-frames{count}-{backend}.png"
            rgba, digest = png_rgba(reference_dir / name)
            imgs[count, backend] = rgba
            hashes[name] = digest
    for backend in ("canvas2d", "webgl"):
        # The explicit 0-frame replay MUST match the already independently
        # validated accepted-only temporal CI PNG, not just its own manifest.
        name = f"engine001-temporal-incremental-{backend}.png"
        old, digest = png_rgba(reference_dir / name)
        hashes[name] = digest
        if not np.array_equal(old, imgs[0, backend]):
            raise ValueError("Duplicate-frame 0-case disagrees with pinned temporal baseline")
    comparisons = {}
    for count in COUNTS:
        comparisons[str(count)] = {
            "extraStationaryFramesPerStroke": count,
            "against_zero_canvas2d": rgba_compare(imgs[0, "canvas2d"], imgs[count, "canvas2d"]),
            "against_zero_webgl": rgba_compare(imgs[0, "webgl"], imgs[count, "webgl"]),
            "same_case_canvas2d_vs_webgl": rgba_compare(
                imgs[count, "canvas2d"], imgs[count, "webgl"]),
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    # One visual comparison image at the most sensitive alpha threshold.
    old = imgs[0, "webgl"][:, :, 3] >= 128
    new = imgs[3, "webgl"][:, :, 3] >= 128
    rgb = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    rgb[old & new] = (170, 170, 170)
    rgb[new & ~old] = (30, 200, 96)
    rgb[old & ~new] = (235, 139, 46)
    Image.fromarray(rgb, "RGB").save(output_dir / "frames0-vs-frames3-webgl-alpha128.png")
    result = {
        "schema_version": 1,
        "experiment_id": "ENGINE001_DUPLICATE_FRAMES_INDEPENDENT_PNG_V1",
        "status": "COMPLETE_OFFLINE_NATIVE_FRAME_RASTER_AUDIT",
        "run_id": RUN, "session_id": SESSION,
        "historical_exact_chalk": 1260, "new_game_chalk": "NOT_MEASURED",
        "historical_monitor_blob_sha": EXPECTED_MONITOR_BLOB,
        "screen_projection": "UNCALIBRATED",
        "synthetic_extra_frames_per_stroke": list(COUNTS),
        "graphics_paths": list(PATHS),
        "png_sha256": hashes,
        "native_rgba_comparisons": comparisons,
        "limitations": [
            "No actual frame timestamps or distribution of repeated inputs in FILL-001",
            "Only final-point duplicate frame callbacks were modeled",
            "No intermediate live screen render, no same-run Stage/CSS/desktop geometry",
            "No newly accepted points were permitted and no new CHALK measured",
        ],
    }
    (output_dir / "analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for count in COUNTS:
        v = comparisons[str(count)]["against_zero_webgl"]
        print(f"ENGINE-001 repeated-final frame={count}: "
              f"WebGL RGBA differs={v['different_rgba_pixels']} "
              f"alpha128 differs={v['by_alpha_threshold']['128']['changed_mask_pixels']}")
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--workspace", type=Path, required=True)
    cli.add_argument("--reference-dir", type=Path, required=True)
    cli.add_argument("--output-dir", type=Path, required=True)
    args = cli.parse_args()
    analyze(args.workspace.resolve(), args.reference_dir.resolve(), args.output_dir.resolve())
