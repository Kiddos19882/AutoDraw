#!/usr/bin/env python3
"""ENGINE001_NATIVE_ENDPOINT_V1: native Egret vs OpenCV in *board-local* space.

This analysis deliberately rejects mapping historical FILL-001 PNG to the
Egret output: the frozen multi-stroke run has no run-bound renderer geometry.
Comparisons to the planner and to observed brush positions remain offline
and cannot determine actual screen leakage or accepted FILL-001 quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

VARIANTS = ("game-smooth", "smooth-drawlast", "normal")
ROWS = (5, 15, 16)
THRESHOLDS = (1, 64, 128, 254)
WIDTH, HEIGHT, SCALE = 1380, 720, 3
MONITOR_REL = ("AutoDraw_Stage20/data/results/brush_behavior_tests/"
               "game_monitor_bridge/bb261898-8296-41f5-a333-eb0b81016410/"
               "game-monitor-run-20261104T040548835772Z-6a17a297.json")
PLAN_REL = ("AutoDraw_Stage20/data/results/brush_behavior_tests/fill001/plans/"
            "fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1.json")
EXPECTED_MONITOR_BLOB = "8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24"
EXPECTED_PLAN_BLOB = "ab54d5a322a642ba6a89a6c77111e4cfadf93232"


def require_git_blob(workspace: Path, relative: str, expected: str) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD:" + relative],
        cwd=workspace, capture_output=True, text=True, check=True,
    ).stdout.strip()
    if result != expected:
        raise ValueError(f"Pinned input changed: {relative}, Git blob {result}")


def png_rgba(path: Path) -> tuple[np.ndarray, str]:
    raw = path.read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG magic: " + str(path))
    with Image.open(path) as img:
        if img.size != (WIDTH, HEIGHT):
            raise ValueError(f"Unexpected engine raster size {img.size}: {path.name}")
        rgba = np.array(img.convert("RGBA"), dtype=np.uint8)
    if not np.any(rgba[:, :, 3]):
        raise ValueError("Empty renderer PNG: " + path.name)
    return rgba, hashlib.sha256(raw).hexdigest()


def cv2_capsule(first: tuple[float, float], last: tuple[float, float]) -> np.ndarray:
    """OpenCV LINE_8 30-backing-px stroke with round ends, *not* Egret emulation."""
    canvas = np.zeros((HEIGHT, WIDTH), dtype=np.uint8)
    a = tuple(round(float(v) * SCALE) for v in first)
    b = tuple(round(float(v) * SCALE) for v in last)
    cv2.line(canvas, a, b, color=1, thickness=30, lineType=cv2.LINE_8)
    cv2.circle(canvas, a, 15, color=1, thickness=-1, lineType=cv2.LINE_8)
    cv2.circle(canvas, b, 15, color=1, thickness=-1, lineType=cv2.LINE_8)
    return canvas.astype(bool)


def agreement(reference: np.ndarray, candidate: np.ndarray) -> dict:
    if reference.shape != candidate.shape:
        raise ValueError("Cannot compare geometry at mismatched resolution")
    joint = int(np.count_nonzero(reference & candidate))
    only_reference = int(np.count_nonzero(reference & ~candidate))
    only_candidate = int(np.count_nonzero(~reference & candidate))
    union = joint + only_reference + only_candidate
    return {
        "common_pixels": joint,
        "reference_only_pixels": only_reference,
        "candidate_only_pixels": only_candidate,
        "xor_pixels": only_reference + only_candidate,
        "iou": round(joint / union, 9) if union else None,
    }


def bounds(mask: np.ndarray, logical_y: float) -> dict:
    center = round(float(logical_y) * SCALE)
    band = mask[max(0, center - 2): min(HEIGHT, center + 3)]
    ys, xs = np.nonzero(band)
    return {
        "left_backing_x": int(xs.min()) if len(xs) else None,
        "right_backing_x": int(xs.max()) if len(xs) else None,
        "band_covered_pixels": int(len(xs)),
    }


def accepted_by_stroke(run: dict) -> list:
    strokes = []
    last = None
    for sample in run["accepted_points"]:
        sid = sample["stroke_id"]
        if sid != last:
            if any(s["id"] == sid for s in strokes):
                raise ValueError("Interleaved accepted stroke IDs")
            strokes.append({"id": sid, "points": []})
            last = sid
        strokes[-1]["points"].append((float(sample["x"]), float(sample["y"])))
    if len(strokes) != 27 or sum(len(s["points"]) for s in strokes) != 1260:
        raise ValueError("Frozen 27-stroke/1260-point evidence was not reproduced")
    return strokes


def overlay(base: np.ndarray, extended: np.ndarray, row: int, logical_y: float) -> Image.Image:
    center = round(float(logical_y) * SCALE)
    # Restricted to the right end; values indicate mask categories, not source colors.
    y0, y1 = max(0, center - 24), min(HEIGHT, center + 25)
    x0, x1 = 1070, 1240
    a = base[y0:y1, x0:x1]
    b = extended[y0:y1, x0:x1]
    rgb = np.zeros((y1 - y0, x1 - x0, 3), dtype=np.uint8)
    rgb[a & b] = (160, 160, 160)
    rgb[b & ~a] = (36, 196, 92)
    rgb[a & ~b] = (242, 140, 52)
    return Image.fromarray(rgb, "RGB")


def analyze(workspace: Path, reference_dir: Path, output_dir: Path) -> dict:
    require_git_blob(workspace, MONITOR_REL, EXPECTED_MONITOR_BLOB)
    require_git_blob(workspace, PLAN_REL, EXPECTED_PLAN_BLOB)
    run = json.loads((workspace / MONITOR_REL).read_text("utf-8"))
    plan = json.loads((workspace / PLAN_REL).read_text("utf-8"))
    summary = json.loads((reference_dir / "engine001-native-endpoint-v1.json").read_text("utf-8-sig"))
    if (summary.get("experimentId") != "ENGINE001_NATIVE_ENDPOINT_V1"
            or summary.get("screenProjection") != "UNCALIBRATED"
            or summary.get("runId") != run.get("run_id")
            or summary.get("sessionId") != run.get("session_id")
            or summary.get("exactHistoricalChalk") != 1260
            or summary.get("isolatedRows") != list(ROWS)
            or summary.get("strokeCount") != 27
            or summary.get("acceptedCount") != 1260):
        raise ValueError("Native endpoint manifest does not match frozen source")
    if len(plan["strokes"]) != 27:
        raise ValueError("27-stroke frozen plan required")
    accepted = accepted_by_stroke(run)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_hashes = {}
    scans = {}
    for p in reference_dir.glob("engine001-endpoint-*.png"):
        if p.name.startswith("engine001-endpoint-outline5-"):
            continue  # Versioned separate contour study, not original 15 PNG.
        if p.name in image_hashes:
            raise ValueError("Duplicate PNG filename")
        rgba, digest = png_rgba(p)
        image_hashes[p.name] = digest
    if len(image_hashes) != 15:
        raise ValueError(f"Expected exactly 15 native engine PNG, found {len(image_hashes)}")
    def load(name: str) -> np.ndarray:
        if name not in image_hashes:
            raise ValueError("Missing named endpoint PNG " + name)
        rgba, digest = png_rgba(reference_dir / name)
        if digest != image_hashes[name]:
            raise ValueError("Endpoint PNG changed during analysis")
        return rgba[:, :, 3]

    aggregates = {}
    for variant in VARIANTS:
        a = load(f"engine001-endpoint-{variant}-all-canvas2d.png")
        b = load(f"engine001-endpoint-{variant}-all-webgl.png")
        aggregate_variants = {}
        for threshold in THRESHOLDS:
            aggregate_variants[str(threshold)] = agreement(a >= threshold, b >= threshold)
        aggregates[variant] = {"backend_comparison_by_alpha": aggregate_variants}

    for row in ROWS:
        s = accepted[row - 1]
        pts = s["points"]
        intended = plan["strokes"][row - 1]["points"]
        if (intended[0]["x"], intended[-1]["x"]) != (75, 385):
            raise ValueError("Non-identical plan start/end in selected row")
        if not all(abs(pt[1] - pts[0][1]) < 1e-7 for pt in pts):
            raise ValueError("Non-horizontal accepted samples in selected row")
        last, penultimate = pts[-1], pts[-2]
        midpoint = ((last[0] + penultimate[0]) / 2, last[1])
        variants = {variant: load(f"engine001-endpoint-{variant}-row{row}-webgl.png")
                    for variant in VARIANTS}
        v_metrics = {}
        for variant in VARIANTS:
            terminal = midpoint if variant == "game-smooth" else last
            cvmask = cv2_capsule(pts[0], terminal)
            stats = {}
            for threshold in THRESHOLDS:
                native = variants[variant] >= threshold
                stats[str(threshold)] = {
                    "native_vs_open_cv_capsule": agreement(native, cvmask),
                    "native_bounds": bounds(native, last[1]),
                    "open_cv_bounds": bounds(cvmask, last[1]),
                }
            v_metrics[variant] = stats
        comparisons = {}
        for threshold in THRESHOLDS:
            original = variants["game-smooth"] >= threshold
            final = variants["smooth-drawlast"] >= threshold
            normal = variants["normal"] >= threshold
            comparisons[str(threshold)] = {
                "game_smooth_vs_smooth_drawlast": agreement(original, final),
                "game_smooth_vs_normal": agreement(original, normal),
                "forced_smooth_vs_normal": agreement(final, normal),
                "added_by_forcing_last": int(np.count_nonzero(final & ~original)),
                "removed_by_forcing_last": int(np.count_nonzero(original & ~final)),
                "forced_last_right_edge_delta_backing_px": (
                    bounds(final, last[1])["right_backing_x"] -
                    bounds(original, last[1])["right_backing_x"]
                ),
            }
        overlay(variants["game-smooth"] >= 128,
                variants["smooth-drawlast"] >= 128, row, last[1]).save(
                    output_dir / f"row-{row}-forced-endpoint-overlay.png")
        scans[str(row)] = {
            "plan_row": row,
            "planned_xy": [intended[0], intended[-1]],
            "accepted_first_xy": pts[0],
            "accepted_penultimate_xy": penultimate,
            "accepted_last_xy": last,
            "smooth_terminal_xy": midpoint,
            "variant_metrics_by_alpha": v_metrics,
            "native_comparisons_by_alpha": comparisons,
        }

    # Large multi-stroke aggregates are intentionally reported separately:
    # tightly spaced horizontal strokes can conceal per-row endpoint changes.
    aggregate_differences = {}
    for threshold in THRESHOLDS:
        a = load("engine001-endpoint-game-smooth-all-webgl.png") >= threshold
        b = load("engine001-endpoint-smooth-drawlast-all-webgl.png") >= threshold
        c = load("engine001-endpoint-normal-all-webgl.png") >= threshold
        aggregate_differences[str(threshold)] = {
            "game_vs_forced": agreement(a, b),
            "game_vs_normal": agreement(a, c),
            "forced_vs_normal": agreement(b, c),
        }
    result = {
        "experiment_id": "ENGINE001_NATIVE_ENDPOINT_BOARD_LOCAL_ANALYSIS_V1",
        "status": "COMPLETE_OFFLINE_NATIVE_BOARD_LOCAL_MEASUREMENT",
        "run_id": summary["runId"], "session_id": summary["sessionId"],
        "source_code_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=workspace,
            capture_output=True, text=True, check=True).stdout.strip(),
        "input_monitor_blob_sha": EXPECTED_MONITOR_BLOB,
        "input_plan_blob_sha": EXPECTED_PLAN_BLOB,
        "screen_mapping_status": "UNCALIBRATED",
        "cross_run_screen_overlay_status": "BLOCKED_NO_SAME_RUN_GEOMETRY",
        "actual_fill001_png_quality": "UNCHANGED_REJECTED_COVERAGE_98.430600_LEAKAGE_11",
        "pixel_canvas": [WIDTH, HEIGHT],
        "native_webgl_png_sha256": image_hashes,
        "comparison_basis": "Same 27 accepted strokes; same native Egret BoardPane; same 3x backing raster; changed only endpoint behavior. OpenCV is independently rasterized LINE_8 capsule in same board-local pixel space.",
        "limitations": [
            "Per-stroke game smooth option not captured, so smooth is a research assumption",
            "OpenCV capsule is a geometric comparator, not an exact Egret antialiased renderer",
            "No historical same-run screen mapping from board to saved FILL-001 PNG",
            "No Egret ENTER_FRAME or DOM replay; no new gameplay or CHALK measurement",
            "Cannot directly attribute 1116 actual missed ROI pixels to this board-local simulation",
        ],
        "per_row": scans,
        "aggregate_backend_agreement": aggregates,
        "aggregate_native_differences": aggregate_differences,
    }
    (output_dir / "analysis.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.workspace.resolve(), args.reference_dir.resolve(),
                     args.output_dir.resolve())
    for row, data in result["per_row"].items():
        vals = data["native_comparisons_by_alpha"]["128"]
        print(f"ENGINE-001 row {row}: forced-endpoint added={vals['added_by_forcing_last']}, "
              f"removed={vals['removed_by_forcing_last']}, "
              f"right-bound-shift={vals['forced_last_right_edge_delta_backing_px']} backing px")
    print("ENGINE-001 board-local actual Egret vs OpenCV finished; screen UNCALIBRATED.")


if __name__ == "__main__":
    main()
