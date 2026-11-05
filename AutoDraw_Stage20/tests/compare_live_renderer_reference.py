#!/usr/bin/env python3
"""Compare a committed live board PNG with its accepted-point Egret WebGL replay.

This is an exploratory pixel audit. It reports metrics and diagnostic images but
does not apply an acceptance threshold or change any production planner defaults.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "preparation"))
from renderer_geometry import derive_live_board_screen_transform

import cv2
import numpy as np
from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.where(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]


def centroid(mask: np.ndarray) -> list[float] | None:
    ys, xs = np.where(mask)
    if not len(xs):
        return None
    return [float(xs.mean()), float(ys.mean())]


def shift_mask(mask: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """Translate a mask without wrapping; positive offsets move right/down."""
    shifted = np.zeros_like(mask, dtype=bool)
    source_y0 = max(0, -dy)
    source_y1 = min(mask.shape[0], mask.shape[0] - dy)
    source_x0 = max(0, -dx)
    source_x1 = min(mask.shape[1], mask.shape[1] - dx)
    target_y0 = max(0, dy)
    target_x0 = max(0, dx)
    target_y1 = target_y0 + (source_y1 - source_y0)
    target_x1 = target_x0 + (source_x1 - source_x0)
    shifted[target_y0:target_y1, target_x0:target_x1] = mask[source_y0:source_y1, source_x0:source_x1]
    return shifted


def mask_metrics(observed: np.ndarray, expected: np.ndarray) -> dict[str, Any]:
    observed = observed.astype(bool)
    expected = expected.astype(bool)
    tp = int(np.count_nonzero(observed & expected))
    fp = int(np.count_nonzero(observed & ~expected))
    fn = int(np.count_nonzero(~observed & expected))
    tn = int(np.count_nonzero(~observed & ~expected))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    union = tp + fp + fn
    return {
        "observed_pixels": int(np.count_nonzero(observed)),
        "expected_pixels": int(np.count_nonzero(expected)),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "symmetric_difference_pixels": fp + fn,
        "iou": tp / union if union else 1.0,
        "precision": precision,
        "recall": recall,
        "f1": (2 * precision * recall / (precision + recall)) if precision + recall else 0.0,
        "observed_bbox_xywh": bbox(observed),
        "expected_bbox_xywh": bbox(expected),
        "observed_centroid_xy": centroid(observed),
        "expected_centroid_xy": centroid(expected),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--blank", type=Path, required=True)
    parser.add_argument("--offline-png", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--geometry-audit", type=Path, default=None)
    parser.add_argument("--rgb-threshold", type=float, default=24.0)
    parser.add_argument("--alpha-thresholds", type=int, nargs="+", default=[1, 24, 64, 128, 192, 254])
    args = parser.parse_args()

    experiment_path = args.experiment_dir / "experiment.json"
    live_path = args.experiment_dir / "after_draw-board.png"
    for path in (experiment_path, live_path, args.blank, args.offline_png, args.manifest, args.plan):
        if not path.is_file():
            raise FileNotFoundError(path)

    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    summary = experiment.get("game_monitor_summary", {})
    run_id = summary.get("run_id")
    fixture = next((item for item in manifest.get("fixtures", []) if item.get("id") == "live-accepted-points"), None)
    if fixture is None:
        raise ValueError("Renderer manifest does not contain live-accepted-points fixture.")
    if fixture.get("sourceRunId") != run_id:
        raise ValueError(f"Run binding mismatch: experiment={run_id!r}, fixture={fixture.get('sourceRunId')!r}.")
    accepted_count = int(summary.get("chalk", {}).get("consumed_points", -1))
    if len(fixture.get("points", [])) != accepted_count:
        raise ValueError("Offline fixture point count does not match the exact live CHALK delta.")
    if fixture.get("mode") != "smooth" or float(fixture.get("lineWidth", 0)) != 10:
        raise ValueError("Unexpected renderer fixture mode/width; expected smooth / lineWidth 10.")

    transform = plan.get("generation", {}).get("screen_transform", {})
    roi = transform.get("screen_roi", {})
    sx = float(transform.get("scale_x", 0))
    sy = float(transform.get("scale_y", 0))
    board = transform.get("logical_board", {})
    if (int(roi.get("width", 0)), int(roi.get("height", 0))) != (674, 355):
        raise ValueError(f"Unexpected live ROI dimensions: {roi!r}")
    if (int(board.get("width", 0)), int(board.get("height", 0))) != (460, 240):
        raise ValueError(f"Unexpected logical board dimensions: {board!r}")

    blank = np.asarray(Image.open(args.blank).convert("RGB"), dtype=np.int16)
    live = np.asarray(Image.open(live_path).convert("RGB"), dtype=np.int16)
    offline = np.asarray(Image.open(args.offline_png).convert("RGBA"), dtype=np.uint8)
    if blank.shape != live.shape or live.shape[:2] != (355, 674):
        raise ValueError(f"Live/baseline dimensions mismatch: blank={blank.shape}, live={live.shape}.")
    if offline.shape[:2] != (720, 1380):
        raise ValueError(f"Unexpected offline WebGL image dimensions: {offline.shape}.")

    # The committed WebGL board image is 3 raster pixels per logical pixel.
    # Map its board-local origin to the live ROI origin using the frozen plan's
    # inclusive logical-bounds -> screen-pixel-centres transform.
    matrix = np.asarray([[sx / 3.0, 0.0, 0.0], [0.0, sy / 3.0, 0.0]], dtype=np.float32)
    warped_alpha = cv2.warpAffine(
        offline[:, :, 3], matrix, (674, 355),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
    )

    rgb_delta = live - blank
    observed = np.max(np.abs(rgb_delta), axis=2) > args.rgb_threshold
    results: dict[str, Any] = {}
    for alpha_threshold in args.alpha_thresholds:
        expected = warped_alpha > alpha_threshold
        results[str(alpha_threshold)] = mask_metrics(observed, expected)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(warped_alpha, mode="L").save(args.output_dir / "expected-alpha-warped.png")
    Image.fromarray((observed.astype(np.uint8) * 255), mode="L").save(args.output_dir / "observed-live-delta-mask.png")

    # Red = live-only, green = offline-only, yellow = overlap.
    expected_default = warped_alpha > 24
    overlay = np.zeros((355, 674, 3), dtype=np.uint8)
    overlay[observed & ~expected_default] = (255, 0, 0)
    overlay[~observed & expected_default] = (0, 255, 0)
    overlay[observed & expected_default] = (255, 255, 0)
    Image.fromarray(overlay, mode="RGB").save(args.output_dir / "live-offline-mask-overlay.png")

    # Diagnostic only: search a small translation window to distinguish a
    # coordinate-origin offset from a shape/footprint mismatch. The frozen
    # transform metrics above remain the primary, unshifted comparison.
    best_shift: tuple[float, int, int, dict[str, Any], np.ndarray] | None = None
    for dy in range(-5, 6):
        for dx in range(-5, 6):
            shifted = shift_mask(expected_default, dx, dy)
            metrics = mask_metrics(observed, shifted)
            candidate = (float(metrics["iou"]), dx, dy, metrics, shifted)
            if best_shift is None or (
                candidate[0], -(abs(dx) + abs(dy)), -abs(dy), -abs(dx)
            ) > (
                best_shift[0], -(abs(best_shift[1]) + abs(best_shift[2])),
                -abs(best_shift[2]), -abs(best_shift[1])
            ):
                best_shift = candidate
    assert best_shift is not None
    _, best_dx, best_dy, best_shift_metrics, shifted_expected = best_shift
    Image.fromarray((shifted_expected.astype(np.uint8) * 255), mode="L").save(
        args.output_dir / "expected-mask-best-translation.png"
    )
    shifted_overlay = np.zeros((355, 674, 3), dtype=np.uint8)
    shifted_overlay[observed & ~shifted_expected] = (255, 0, 0)
    shifted_overlay[~observed & shifted_expected] = (0, 255, 0)
    shifted_overlay[observed & shifted_expected] = (255, 255, 0)
    Image.fromarray(shifted_overlay, mode="RGB").save(
        args.output_dir / "live-offline-mask-overlay-best-translation.png"
    )

    report = {
        "status": "ANALYZED_EXPLORATORY_NO_ACCEPTANCE_THRESHOLD",
        "experiment_id": experiment.get("experiment_id"),
        "run_id": run_id,
        "session_id": summary.get("session_id"),
        "accepted_point_count": len(fixture.get("points", [])),
        "exact_chalk": summary.get("chalk", {}).get("consumed_points"),
        "renderer_fixture": {
            "id": fixture.get("id"),
            "mode": fixture.get("mode"),
            "line_width": fixture.get("lineWidth"),
            "manifest_schema_version": manifest.get("schemaVersion"),
        },
        "inputs": {
            str(path): {"sha256": sha256(path), "size_bytes": path.stat().st_size}
            for path in (experiment_path, live_path, args.blank, args.offline_png, args.manifest, args.plan)
        },
        "dimensions": {
            "live_roi": [674, 355],
            "offline_webgl": [1380, 720],
            "logical_board": [460, 240],
        },
        "transform": {
            "scale_x": sx,
            "scale_y": sy,
            "source_raster_scale": 3,
            "matrix_source_to_live": matrix.tolist(),
            "interpolation": "OpenCV INTER_LINEAR",
            "origin_mapping": "logical board origin to live ROI origin; frozen plan scale_x/scale_y",
        },
        "thresholds": {
            "observed_rgb_euclidean": args.rgb_threshold,
            "expected_alpha": args.alpha_thresholds,
        },
        "observed_live_delta": {
            "changed_pixels": int(np.count_nonzero(observed)),
            "bbox_xywh": bbox(observed),
            "centroid_xy": centroid(observed),
        },
        "comparisons": results,
        "best_translation_diagnostic": {
            "search_radius_px": 5,
            "expected_mask_translation_to_align_live": {"x": best_dx, "y": best_dy},
            "metrics_at_alpha_threshold_24": best_shift_metrics,
            "interpretation": "post-hoc alignment diagnostic only; does not replace the frozen transform or constitute acceptance",
        },
        "limitations": [
            "This is an exploratory raster comparison; no acceptance threshold is applied.",
            "Live image is differenced against the user-confirmed blank-board baseline.",
            "The offline WebGL alpha is resampled into the live ROI using the frozen plan transform.",
            "Any mismatch may include screen resampling, antialiasing, baseline drift, color management, or renderer differences.",
            "The manifest runtimeProfile references the 2026-11-04 renderer snapshot, not a same-run inspect() snapshot.",
        ],
    }
    (args.output_dir / "comparison-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    independent_summary = None
    if args.geometry_audit is not None:
        if not args.geometry_audit.is_file():
            raise FileNotFoundError(args.geometry_audit)
        geometry_evidence = json.loads(args.geometry_audit.read_text(encoding="utf-8"))
        monitor_path = args.experiment_dir / "monitor_report.json"
        monitor_report = json.loads(monitor_path.read_text(encoding="utf-8"))
        source_run = geometry_evidence.get("source_run", {})
        if source_run.get("run_id") != run_id or source_run.get("session_id") != summary.get("session_id"):
            raise ValueError("Independent geometry evidence is not bound to this exact run/session.")
        if monitor_report.get("run_id") != run_id or monitor_report.get("session_id") != summary.get("session_id"):
            raise ValueError("Monitor report run/session does not match the experiment manifest.")
        screen = geometry_evidence["screen"]
        inspect_input = {
            "provenance": geometry_evidence.get("provenance", {}),
            "screen": screen,
            "board": geometry_evidence["board"],
            "renderer": geometry_evidence["renderer"],
        }
        geometry = derive_live_board_screen_transform(
            monitor_report, inspect_input, roi, (int(screen["width"]), int(screen["height"]))
        )
        matrix_independent = np.asarray(geometry["matrix_source_raster_to_roi"], dtype=np.float32)
        alpha_independent = cv2.warpAffine(
            offline[:, :, 3], matrix_independent, (live.shape[1], live.shape[0]),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
        )
        independent_results = {
            str(threshold): mask_metrics(observed, alpha_independent > threshold)
            for threshold in args.alpha_thresholds
        }
        expected_independent = alpha_independent > 24
        overlay_independent = np.zeros((live.shape[0], live.shape[1], 3), dtype=np.uint8)
        overlay_independent[observed & ~expected_independent] = (255, 0, 0)
        overlay_independent[~observed & expected_independent] = (0, 255, 0)
        overlay_independent[observed & expected_independent] = (255, 255, 0)
        Image.fromarray(alpha_independent, mode="L").save(
            args.output_dir / "expected-alpha-independent-transform.png"
        )
        Image.fromarray(overlay_independent, mode="RGB").save(
            args.output_dir / "live-offline-mask-overlay-independent-transform.png"
        )
        independent_report = {
            "status": "ANALYZED_EXPLORATORY_NO_ACCEPTANCE_THRESHOLD",
            "experiment_id": experiment.get("experiment_id"),
            "run_id": run_id,
            "session_id": summary.get("session_id"),
            "inputs": {
                str(item): {"sha256": sha256(item), "size_bytes": item.stat().st_size}
                for item in (experiment_path, live_path, args.blank, args.offline_png, args.manifest,
                             args.plan, monitor_path, args.geometry_audit)
            },
            "transform": geometry,
            "thresholds": {"observed_rgb_euclidean": args.rgb_threshold, "expected_alpha": args.alpha_thresholds},
            "observed_live_delta": report["observed_live_delta"],
            "comparisons": independent_results,
            "limitations": [
                "No post-hoc translation or image registration is applied.",
                "Horizontal scale/origin are fitted from same-run Monitor screenX/boardX telemetry.",
                "Vertical scale comes from the user-provided inspect snapshot; this live run has no vertical pointer variation.",
                "The inspect snapshot has no run/session timestamp; same-screen provenance is user-attested.",
                "This is exploratory evidence and has no renderer acceptance threshold.",
            ],
        }
        (args.output_dir / "comparison-report-independent-transform.json").write_text(
            json.dumps(independent_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        independent_summary = {
            "iou_alpha_24": independent_results.get("24", {}).get("iou"),
            "precision_alpha_24": independent_results.get("24", {}).get("precision"),
            "recall_alpha_24": independent_results.get("24", {}).get("recall"),
            "symmetric_difference_alpha_24": independent_results.get("24", {}).get("symmetric_difference_pixels"),
            "report": str(args.output_dir / "comparison-report-independent-transform.json"),
        }
    print(json.dumps({
        "status": report["status"],
        "changed_live_pixels": report["observed_live_delta"]["changed_pixels"],
        "comparisons": {
            threshold: {
                "iou": metrics["iou"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "symmetric_difference_pixels": metrics["symmetric_difference_pixels"],
            }
            for threshold, metrics in results.items()
        },
        "best_translation_diagnostic": {
            "dx": best_dx,
            "dy": best_dy,
            "iou": best_shift_metrics["iou"],
            "symmetric_difference_pixels": best_shift_metrics["symmetric_difference_pixels"],
        },
        "report": str(args.output_dir / "comparison-report.json"),
        "independent_transform_comparison": independent_summary,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
