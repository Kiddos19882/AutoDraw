#!/usr/bin/env python3
"""Compare a committed live board PNG with its accepted-point Egret WebGL replay.

This is an exploratory pixel audit. It reports metrics and diagnostic images but
does not apply an acceptance threshold or change any production planner defaults.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "preparation"))
from renderer_geometry import (RendererGeometryError, build_same_run_geometry_audit_input, detect_board_bounds_from_screenshots, derive_live_board_screen_transform)
from renderer_acceptance import (
    EXPECTED_PAIRED_AXIS_SOURCES,
    evaluate_per_run_acceptance,
    validate_paired_capture,
    validate_renderer_comparison,
    validate_transform_geometry,
)

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




def _find_edge_executable() -> Path:
    candidates = [
        shutil.which("msedge"),
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise FileNotFoundError("Microsoft Edge is required for same-run CSS compositor replay.")


def _browser_composite_html(
    baseline_png: Path,
    offline_png: Path | None,
    screen_size: tuple[int, int],
    board_origin: dict[str, float],
    css_matrix: dict[str, float],
) -> str:
    width, height = screen_size
    baseline_uri = html.escape(baseline_png.resolve().as_uri(), quote=True)
    overlay = ""
    if offline_png is not None:
        overlay_uri = html.escape(offline_png.resolve().as_uri(), quote=True)
        left = float(board_origin["x"])
        top = float(board_origin["y"])
        a, b, c, d, tx, ty = (float(css_matrix[key]) for key in ("a", "b", "c", "d", "tx", "ty"))
        overlay = (
            f'<img id="board-overlay" alt="" src="{overlay_uri}" '
            f'style="left:{left:.12f}px;top:{top:.12f}px;'
            f'transform:matrix({a:.15g},{b:.15g},{c:.15g},{d:.15g},{tx:.15g},{ty:.15g});">'
        )
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<style>
html,body {{ margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden;background:#000; }}
img {{ position:absolute;display:block;margin:0;padding:0;border:0;max-width:none;max-height:none;object-fit:fill; }}
#baseline {{ left:0;top:0;width:{width}px;height:{height}px; }}
#board-overlay {{ width:1380px;height:720px;transform-origin:0 0;image-rendering:auto; }}
</style></head><body>
<img id="baseline" alt="" src="{baseline_uri}">
{overlay}
<script>
Promise.all(Array.from(document.images).map(image => image.decode()))
  .then(() => {{ document.documentElement.dataset.ready = "true"; }})
  .catch(error => {{ document.documentElement.dataset.error = String(error); }});
</script>
</body></html>"""


def render_browser_css_composite(
    baseline_png: Path,
    offline_png: Path,
    screen_size: tuple[int, int],
    board_origin: dict[str, float],
    css_matrix: dict[str, float],
    output_dir: Path,
) -> dict[str, Any]:
    """Composite the exact offline BoardPane raster using Edge's CSS compositor.

    The baseline capture is displayed 1:1. The offline PNG is then positioned at
    the same-run BoardPane screen origin and transformed by the inspected canvas
    CSS matrix. No image registration, translation search, or pixel-fit is used.
    """
    width, height = screen_size
    edge = _find_edge_executable()
    output_dir.mkdir(parents=True, exist_ok=True)
    browser_dir = output_dir / "browser-css-composite"
    browser_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "method": "edge_headless_css_compositor",
        "screen_size": {"width": width, "height": height},
        "board_origin_screen_px": board_origin,
        "css_matrix": css_matrix,
        "offline_png_natural_size": {"width": 1380, "height": 720},
        "device_scale_factor": 1,
        "post_hoc_registration": False,
    }

    def capture(name: str, overlay_png: Path | None) -> Path:
        html_path = browser_dir / f"{name}.html"
        screenshot_path = browser_dir / f"{name}.png"
        html_path.write_text(
            _browser_composite_html(baseline_png, overlay_png, screen_size, board_origin, css_matrix),
            encoding="utf-8",
        )
        profile = browser_dir / f"profile-{name}"
        command = [
            str(edge), "--headless", "--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--hide-scrollbars",
            "--force-device-scale-factor=1", f"--window-size={width},{height}",
            "--virtual-time-budget=2500", "--run-all-compositor-stages-before-draw",
            f"--user-data-dir={profile}", f"--screenshot={screenshot_path}", html_path.resolve().as_uri(),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=90, check=False)
        results.setdefault("browser_runs", {})[name] = {
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-4000:],
        }
        if completed.returncode != 0 or not screenshot_path.is_file():
            raise RuntimeError(
                f"Edge CSS compositor capture {name!r} failed; "
                f"returncode={completed.returncode}, stderr={completed.stderr[-2000:]}"
            )
        with Image.open(screenshot_path) as image:
            if image.size != (width, height):
                raise RuntimeError(
                    f"Edge CSS compositor returned {image.size}, expected {(width, height)}."
                )
        return screenshot_path

    base_capture = capture("baseline-only", None)
    composite_capture = capture("baseline-with-board", offline_png)
    with Image.open(base_capture) as image:
        base_rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    with Image.open(composite_capture) as image:
        composite_rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    with Image.open(baseline_png) as image:
        source_rgb = np.asarray(image.convert("RGB"), dtype=np.int16)
    roundtrip = np.max(np.abs(base_rgb - source_rgb), axis=2)
    results["baseline_round_trip"] = {
        "max_channel_error": int(roundtrip.max()),
        "pixels_over_1_channel_error": int(np.count_nonzero(roundtrip > 1)),
        "mean_absolute_channel_error": float(np.abs(base_rgb - source_rgb).mean()),
        "interpretation": "browser baseline capture compared with its exact source full-screen PNG",
    }
    composite_delta = np.max(np.abs(composite_rgb - base_rgb), axis=2)
    expected = composite_delta > 24
    Image.fromarray((expected.astype(np.uint8) * 255), mode="L").save(
        browser_dir / "expected-mask-browser-css.png"
    )
    Image.fromarray(composite_rgb.astype(np.uint8), mode="RGB").save(
        browser_dir / "baseline-with-board.png"
    )
    Image.fromarray(base_rgb.astype(np.uint8), mode="RGB").save(
        browser_dir / "baseline-browser-roundtrip.png"
    )
    results["expected_changed_pixels"] = int(np.count_nonzero(expected))
    results["expected_bbox_xywh"] = bbox(expected)
    results["outputs"] = {
        "html": str(browser_dir),
        "baseline": str(base_capture),
        "composite": str(composite_capture),
        "expected_mask": str(browser_dir / "expected-mask-browser-css.png"),
    }
    return {"expected_mask": expected, "diagnostics": results}



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--blank", type=Path, required=True)
    parser.add_argument("--offline-png", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--geometry-audit", type=Path, default=None)
    parser.add_argument("--same-run-geometry", action="store_true",
                        help="Build the geometry audit from this experiment and its exact Game Monitor run snapshot.")
    parser.add_argument("--rgb-threshold", type=float, default=24.0)
    parser.add_argument("--alpha-thresholds", type=int, nargs="+", default=[1, 24, 64, 128, 192, 254])
    args = parser.parse_args()
    if args.geometry_audit is not None and args.same_run_geometry:
        parser.error("--geometry-audit and --same-run-geometry are mutually exclusive.")

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
        "scenario_id": experiment.get("test_case"),
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
    formal_acceptance = None
    if args.geometry_audit is not None or args.same_run_geometry:
        monitor_path = args.experiment_dir / "monitor_report.json"
        monitor_report = json.loads(monitor_path.read_text(encoding="utf-8"))
        if args.same_run_geometry:
            screen_before_source = args.experiment_dir / "before_clear-screen.png"
            if not screen_before_source.is_file():
                raise FileNotFoundError(screen_before_source)
            with Image.open(screen_before_source) as screen_image:
                same_run_screen_size = screen_image.size
            geometry_evidence = build_same_run_geometry_audit_input(
                experiment, monitor_report, same_run_screen_size,
            )
            geometry_audit_path = args.output_dir / "screen_geometry_audit.json"
            args.output_dir.mkdir(parents=True, exist_ok=True)
            geometry_audit_path.write_text(
                json.dumps(geometry_evidence, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        else:
            if not args.geometry_audit.is_file():
                raise FileNotFoundError(args.geometry_audit)
            geometry_audit_path = args.geometry_audit
            geometry_evidence = json.loads(geometry_audit_path.read_text(encoding="utf-8"))
        source_run = geometry_evidence.get("source_run", {})
        if source_run.get("run_id") != run_id or source_run.get("session_id") != summary.get("session_id"):
            raise ValueError("Independent geometry evidence is not bound to this exact run/session.")
        if monitor_report.get("run_id") != run_id or monitor_report.get("session_id") != summary.get("session_id"):
            raise ValueError("Monitor report run/session does not match the experiment manifest.")
        screen = geometry_evidence["screen"]
        screen_before_path = args.experiment_dir / "before_clear-screen.png"
        screen_after_path = args.experiment_dir / "after_draw-screen.png"
        for screen_path in (screen_before_path, screen_after_path):
            if not screen_path.is_file():
                raise FileNotFoundError(screen_path)
        before_screen = np.asarray(Image.open(screen_before_path).convert("RGB"), dtype=np.uint8)
        after_screen = np.asarray(Image.open(screen_after_path).convert("RGB"), dtype=np.uint8)
        expected_screen_size = (int(screen["height"]), int(screen["width"]))
        if before_screen.shape[:2] != expected_screen_size or after_screen.shape[:2] != expected_screen_size:
            raise ValueError("Same-run full-screen captures do not match the inspect screen dimensions.")
        board_bounds_audit = detect_board_bounds_from_screenshots(
            before_screen, after_screen, roi,
        )
        inspect_input = {
            "provenance": geometry_evidence.get("provenance", {}),
            "screen": screen,
            "board": geometry_evidence["board"],
            "renderer": geometry_evidence["renderer"],
        }
        geometry = derive_live_board_screen_transform(
            monitor_report, inspect_input, roi, (int(screen["width"]), int(screen["height"])),
            screenshot_board_bounds=board_bounds_audit["bounds"],
        )
        scenario_id = experiment.get("test_case")
        expected_axis_sources = EXPECTED_PAIRED_AXIS_SOURCES.get(scenario_id)
        if expected_axis_sources is not None and geometry.get("axis_sources") != expected_axis_sources:
            raise RendererGeometryError(
                f"{scenario_id}: expected axis sources {expected_axis_sources}, "
                f"received {geometry.get('axis_sources')}."
            )
        monitor_fit_axes = [axis.upper() for axis, source in geometry["axis_sources"].items() if source == "same_run_monitor_fit"]
        screenshot_bounds_axes = [axis.upper() for axis, source in geometry["axis_sources"].items() if source == "same_run_full_screen_board_bounds"]
        inspect_fallback_axes = [axis.upper() for axis, source in geometry["axis_sources"].items() if source == "inspect_css_transform_unfitted_axis"]
        # Formal screen comparison uses the same-run CSS transform and Edge's
        # compositor. OpenCV affine resampling remains a separate diagnostic.
        matrix_independent = np.asarray(geometry["matrix_source_raster_to_roi"], dtype=np.float32)
        alpha_opencv = cv2.warpAffine(
            offline[:, :, 3], matrix_independent, (live.shape[1], live.shape[0]),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
        )
        opencv_independent_results = {}
        css_matrix = geometry_evidence["renderer"]["canvas"]["css_matrix"]
        browser_composite = render_browser_css_composite(
            screen_before_path,
            args.offline_png,
            (int(screen["width"]), int(screen["height"])),
            geometry["inspect_origin"],
            css_matrix,
            args.output_dir,
        )
        roi_x, roi_y = int(roi["x"]), int(roi["y"])
        roi_width, roi_height = int(roi["width"]), int(roi["height"])
        observed = (
            np.max(
                np.abs(
                    after_screen[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width].astype(np.int16)
                    - before_screen[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width].astype(np.int16)
                ),
                axis=2,
            ) > args.rgb_threshold
        )
        expected_independent = browser_composite["expected_mask"][
            roi_y:roi_y + roi_height, roi_x:roi_x + roi_width
        ]
        if expected_independent.shape != observed.shape:
            raise ValueError("Browser CSS compositor ROI dimensions differ from the live ROI.")
        opencv_independent_results = {
            str(threshold): mask_metrics(observed, alpha_opencv > threshold)
            for threshold in args.alpha_thresholds
        }
        if args.rgb_threshold != 24:
            raise ValueError("The formal browser-composited screen-delta threshold is fixed at RGB 24.")
        independent_results = {
            "24": mask_metrics(observed, expected_independent),
        }
        report["observed_live_delta"] = {
            "changed_pixels": int(np.count_nonzero(observed)),
            "bbox_xywh": bbox(observed),
            "centroid_xy": centroid(observed),
            "source": "same-run after_draw-screen.png minus before_clear-screen.png, cropped to the paired ROI",
        }
        Image.fromarray((expected_independent.astype(np.uint8) * 255), mode="L").save(
            args.output_dir / "expected-mask-browser-css.png"
        )
        Image.fromarray((alpha_opencv > 24).astype(np.uint8) * 255, mode="L").save(
            args.output_dir / "expected-alpha-opencv-diagnostic.png"
        )
        overlay_independent = np.zeros((live.shape[0], live.shape[1], 3), dtype=np.uint8)
        overlay_independent[observed & ~expected_independent] = (255, 0, 0)
        overlay_independent[~observed & expected_independent] = (0, 255, 0)
        overlay_independent[observed & expected_independent] = (255, 255, 0)
        Image.fromarray(overlay_independent, mode="RGB").save(
            args.output_dir / "live-offline-mask-overlay-independent-transform.png"
        )

        # Formal per-run gate applies only to the independent, unshifted transform.
        if "24" not in independent_results:
            raise ValueError("The fixed RGB screen-delta threshold must remain 24 for renderer acceptance.")
        capture_validation = validate_paired_capture(
            experiment, monitor_report, plan, fixture,
        )
        transform_validation = validate_transform_geometry(geometry, scenario_id)
        renderer_validation = validate_renderer_comparison(
            independent_results["24"], report["observed_live_delta"]["changed_pixels"],
            metric_suffix="screen_rgb_delta_24",
        )
        formal_acceptance = evaluate_per_run_acceptance(
            capture_validation, transform_validation, renderer_validation,
        )

        independent_report = {
            "status": formal_acceptance["status"],
            "experiment_id": experiment.get("experiment_id"),
            "scenario_id": scenario_id,
            "run_id": run_id,
            "session_id": summary.get("session_id"),
            "inputs": {
                str(item): {"sha256": sha256(item), "size_bytes": item.stat().st_size}
                for item in (experiment_path, live_path, args.blank, args.offline_png, args.manifest,
                             args.plan, monitor_path, geometry_audit_path, screen_before_path, screen_after_path)
            },
            "transform": geometry,
            "screen_compositing": {
                **browser_composite["diagnostics"],
                "formal_pixel_threshold_rgb": args.rgb_threshold,
                "opencv_inter_linear_diagnostic_metrics": opencv_independent_results,
            },
            "offline_renderer": {
                "logical_board_size": manifest.get("board"),
                "raster_scale": manifest.get("rasterScale"),
                "raster_png_size": {"width": int(offline.shape[1]), "height": int(offline.shape[0])},
                "manifest_runtime_profile_source": manifest.get("runtimeProfile", {}).get("source"),
                "runtime_profile_used_for_live_screen_transform": False,
            },
            "board_bounds_audit": board_bounds_audit,
            "thresholds": {
                "formal_screen_rgb_delta": args.rgb_threshold,
                "opencv_diagnostic_alpha": args.alpha_thresholds,
            },
            "observed_live_delta": report["observed_live_delta"],
            "comparisons": independent_results,
            "axis_coverage": geometry["axis_sources"],
            "formal_acceptance": formal_acceptance,
            "expected_axis_sources": expected_axis_sources,
            "limitations": [
                "No post-hoc translation or image registration is applied.",
                f"Same-run Monitor fit axes: {', '.join(monitor_fit_axes) if monitor_fit_axes else 'none'}.",
                f"Same-run screenshot BoardPane bounds axes: {', '.join(screenshot_bounds_axes) if screenshot_bounds_axes else 'none'}.",
                f"Inspect-only fallback axes: {', '.join(inspect_fallback_axes) if inspect_fallback_axes else 'none'}.",
                "Inspect geometry is an independent cross-check, not the source of same-run Monitor fits.",
                "This capture covers one trajectory and one screen configuration; it does not establish viewport/window/DPR generality or executor handoff.",
                "A per-run PASS is not series acceptance; three unique valid vertical and diagonal runs are still required.",
            ],
        }
        (args.output_dir / "comparison-report-independent-transform.json").write_text(
            json.dumps(independent_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        report["diagnostic_frozen_plan_comparison"] = {
            "status": report["status"],
            "transform": report["transform"],
            "comparisons": report["comparisons"],
            "purpose": "Diagnostic only; excluded from formal per-run acceptance.",
        }
        report["analysis_status"] = "FROZEN_PLAN_DIAGNOSTIC_ONLY"
        report["transform"] = geometry
        report["transform_source"] = "same_run_monitor_geometry_and_full_screen_board_bounds"
        report["comparisons"] = independent_results
        report["offline_renderer"] = independent_report["offline_renderer"]
        report["limitations"] = [
            "Frozen plan transform metrics are retained only in diagnostic_frozen_plan_comparison.",
            "Formal acceptance uses same-run inspected CSS matrix through Edge's CSS compositor over the exact before-draw full-screen capture; no post-hoc registration is applied.",
            "OpenCV INTER_LINEAR affine resampling is retained only as a diagnostic and is not the formal screen rasterization reference.",
            "The offline BoardPane uses the manifest logical board dimensions and raster scale; manifest runtimeProfile metadata is not used for live screen alignment.",
            "No post-hoc translation or image registration is applied to the formal comparison.",
            "A per-run PASS is not series acceptance; three unique valid vertical and diagonal runs are still required.",
        ]
        report["status"] = formal_acceptance["status"]
        report["formal_acceptance"] = formal_acceptance
        (args.output_dir / "comparison-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        independent_summary = {
            "status": formal_acceptance["status"],
            "failed_checks": {
                "capture": capture_validation["failed_checks"],
                "transform": transform_validation["failed_checks"],
                "renderer": renderer_validation["failed_checks"],
            },
            "iou_screen_rgb_delta_24": independent_results["24"]["iou"],
            "precision_screen_rgb_delta_24": independent_results["24"]["precision"],
            "recall_screen_rgb_delta_24": independent_results["24"]["recall"],
            "symmetric_difference_screen_rgb_delta_24": independent_results["24"]["symmetric_difference_pixels"],
            "screen_compositing_method": "edge_headless_css_compositor",
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
            for threshold, metrics in report["comparisons"].items()
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
    return 2 if formal_acceptance is not None and not formal_acceptance["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
