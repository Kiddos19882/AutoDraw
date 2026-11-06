#!/usr/bin/env python3
"""Diagnostic comparison of Stage-level Egret renders with same-run live screenshots.

This tool deliberately does not make a renderer acceptance decision. It uses the
exact CSS transform and canvas client origin captured by Game Monitor, and checks
that mapping against the independently derived board-to-screen transform.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

VARIANT_FILES = {
    "A": "stage-level-A-webgl-exact_fractional_backing_origin.png",
    "B": "stage-level-B-webgl-nearest_backing_pixel.png",
    "C": "stage-level-C-canvas2d-exact_fractional_backing_origin.png",
    "D": "stage-level-D-canvas2d-nearest_backing_pixel.png",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_css_matrix(value: str) -> dict[str, float]:
    match = re.fullmatch(r"\s*matrix\(([^)]+)\)\s*", value or "")
    if not match:
        raise ValueError(f"Unsupported or missing canvas CSS transform: {value!r}")
    parts = [float(item.strip()) for item in match.group(1).split(",")]
    if len(parts) != 6 or not all(np.isfinite(parts)):
        raise ValueError("Canvas CSS matrix must contain six finite values.")
    a, b, c, d, tx, ty = parts
    if abs(b) > 1e-9 or abs(c) > 1e-9:
        raise ValueError("Stage comparison currently requires an axis-aligned CSS transform.")
    if a <= 0 or d <= 0:
        raise ValueError("Canvas CSS scale must be positive.")
    return {"a": a, "b": b, "c": c, "d": d, "tx": tx, "ty": ty}


def derive_stage_canvas_origin(
    canvas_client_rect: dict[str, float],
    screen_offset_from_client: dict[str, float],
) -> dict[str, float]:
    values = [
        float(canvas_client_rect.get("left", float("nan"))),
        float(canvas_client_rect.get("top", float("nan"))),
        float(screen_offset_from_client.get("x", float("nan"))),
        float(screen_offset_from_client.get("y", float("nan"))),
    ]
    if not all(np.isfinite(values)):
        raise ValueError("Same-run canvas client origin or client-to-screen offset is incomplete.")
    return {"x": values[0] + values[2], "y": values[1] + values[3]}


def predict_board_screen_origin(
    stage_origin: dict[str, float],
    placement: dict[str, float],
    matrix: dict[str, float],
) -> dict[str, float]:
    x = float(placement["x"])
    y = float(placement["y"])
    return {
        "x": stage_origin["x"] + matrix["a"] * x + matrix["c"] * y + matrix["tx"],
        "y": stage_origin["y"] + matrix["b"] * x + matrix["d"] * y + matrix["ty"],
    }


def validate_board_origin_crosscheck(
    predicted: dict[str, float],
    independent: dict[str, float],
    tolerance_px: float = 1.0,
) -> dict[str, Any]:
    delta = {
        "x": predicted["x"] - float(independent["x"]),
        "y": predicted["y"] - float(independent["y"]),
    }
    passed = abs(delta["x"]) <= tolerance_px and abs(delta["y"]) <= tolerance_px
    if not passed:
        raise ValueError(
            "Run-bound canvas CSS transform does not agree with independent board-to-screen geometry: "
            f"delta={delta}, tolerance={tolerance_px}px."
        )
    return {"passed": True, "delta_px": delta, "tolerance_px": tolerance_px}


def mask_metrics(observed: np.ndarray, expected: np.ndarray) -> dict[str, Any]:
    observed = observed.astype(bool)
    expected = expected.astype(bool)
    if observed.shape != expected.shape:
        raise ValueError(f"Mask dimensions differ: observed={observed.shape}, expected={expected.shape}.")
    tp = int(np.count_nonzero(observed & expected))
    fp = int(np.count_nonzero(observed & ~expected))
    fn = int(np.count_nonzero(~observed & expected))
    union = tp + fp + fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "observed_pixels": int(np.count_nonzero(observed)),
        "expected_pixels": int(np.count_nonzero(expected)),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "symmetric_difference_pixels": fp + fn,
        "iou": tp / union if union else 1.0,
        "precision": precision,
        "recall": recall,
    }


def build_change_mask(candidate: np.ndarray, baseline: np.ndarray, threshold: float) -> np.ndarray:
    """Build an RGB-delta mask against one explicit baseline image."""
    candidate = np.asarray(candidate)
    baseline = np.asarray(baseline)
    if candidate.shape != baseline.shape or candidate.ndim != 3 or candidate.shape[2] != 3:
        raise ValueError(
            f"RGB candidate/baseline dimensions differ or are invalid: "
            f"candidate={candidate.shape}, baseline={baseline.shape}."
        )
    if not np.isfinite(float(threshold)) or threshold < 0:
        raise ValueError("RGB delta threshold must be finite and non-negative.")
    delta = np.max(
        np.abs(candidate.astype(np.int16) - baseline.astype(np.int16)),
        axis=2,
    )
    return delta > float(threshold)


def find_firefox() -> Path:
    candidates = [
        shutil.which("firefox"),
        Path(os.environ.get("ProgramFiles", "")) / "Mozilla Firefox/firefox.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Mozilla Firefox/firefox.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise FileNotFoundError("Firefox is required for same-browser Stage CSS compositing.")


def firefox_version(firefox: Path) -> str:
    result = subprocess.run([str(firefox), "--version"], capture_output=True, text=True, timeout=20, check=False)
    match = re.search(r"Firefox[ /]([0-9.]+)", result.stdout + " " + result.stderr)
    if result.returncode != 0 or not match:
        raise RuntimeError(f"Unable to determine Firefox version: {result.stdout} {result.stderr}")
    return match.group(1)


def build_html(
    baseline_png: Path,
    screen_size: tuple[int, int],
    stage_png: Path | None = None,
    stage_origin: dict[str, float] | None = None,
    matrix: dict[str, float] | None = None,
) -> str:
    width, height = screen_size
    baseline_uri = html.escape(baseline_png.resolve().as_uri(), quote=True)
    overlay = ""
    if stage_png is not None:
        if stage_origin is None or matrix is None:
            raise ValueError("Stage overlay requires a screen origin and CSS matrix.")
        with Image.open(stage_png) as image:
            stage_width, stage_height = image.size
        stage_uri = html.escape(stage_png.resolve().as_uri(), quote=True)
        left, top = stage_origin["x"], stage_origin["y"]
        a, b, c, d, tx, ty = (matrix[key] for key in ("a", "b", "c", "d", "tx", "ty"))
        overlay = f"""
<canvas id="stage-overlay" width="{stage_width}" height="{stage_height}"
 style="left:{left:.12f}px;top:{top:.12f}px;width:{stage_width}px;height:{stage_height}px;
 transform-origin:0 0;transform:matrix({a:.15g},{b:.15g},{c:.15g},{d:.15g},{tx:.15g},{ty:.15g});"></canvas>
<img id="stage-source" alt="" src="{stage_uri}" loading="eager" decoding="sync" style="display:none"
 onload="const canvas=document.getElementById('stage-overlay');const context=canvas.getContext('2d',{{alpha:true}});
 if(!context)throw new Error('Stage overlay Canvas2D context unavailable.');
 context.imageSmoothingEnabled=true;context.imageSmoothingQuality='high';
 context.drawImage(this,0,0,{stage_width},{stage_height});document.documentElement.dataset.stageReady='true';">
"""
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<style>
html,body {{ margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden;background:#000; }}
img {{ position:absolute;display:block;margin:0;padding:0;border:0;max-width:none;max-height:none; }}
#baseline {{ left:0;top:0;width:{width}px;height:{height}px; }}
#stage-overlay {{ position:absolute;display:block;image-rendering:auto; }}
</style></head><body>
<img id="baseline" alt="" src="{baseline_uri}">
{overlay}
</body></html>"""


def capture_firefox(
    firefox: Path,
    html_path: Path,
    screenshot_path: Path,
    profile_path: Path,
    screen_size: tuple[int, int],
) -> dict[str, Any]:
    width, height = screen_size
    profile_path.mkdir(parents=True, exist_ok=True)
    command = [
        str(firefox), "--headless", "--no-remote", "--profile", str(profile_path),
        "--window-size", f"{width},{height}", "--screenshot", str(screenshot_path),
        html_path.resolve().as_uri(),
    ]
    env = os.environ.copy()
    env["MOZ_HEADLESS"] = "1"
    result = subprocess.run(command, capture_output=True, text=True, timeout=90, check=False, env=env)
    if result.returncode != 0 or not screenshot_path.is_file():
        raise RuntimeError(
            f"Firefox screenshot failed: exit={result.returncode}, stderr={result.stderr[-3000:]}"
        )
    with Image.open(screenshot_path) as image:
        if image.size != screen_size:
            raise RuntimeError(f"Firefox screenshot size {image.size} differs from expected {screen_size}.")
    return {"returncode": result.returncode, "stdout_tail": result.stdout[-1000:], "stderr_tail": result.stderr[-2000:]}


def load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.int16)


def compare_stage_variants(
    orientation: str,
    stage_manifest_path: Path,
    stage_png_dir: Path,
    experiment_dir: Path,
    comparison_report_path: Path,
    output_dir: Path,
    variants: list[str],
) -> dict[str, Any]:
    manifest = json.loads(stage_manifest_path.read_text(encoding="utf-8-sig"))
    report = json.loads(comparison_report_path.read_text(encoding="utf-8-sig"))
    profile = manifest.get("runtimeProfile", {})
    fixtures = manifest.get("fixtures", [])
    if len(fixtures) != 1 or fixtures[0].get("id") != "live-accepted-points":
        raise ValueError("Stage manifest must contain exactly one live-accepted-points fixture.")
    fixture = fixtures[0]
    run_id = report.get("run_id")
    if not run_id or profile.get("sourceRunId") != run_id or fixture.get("sourceRunId") != run_id:
        raise ValueError("Stage manifest and independent screenshot report are not bound to the same run.")
    if manifest.get("stageLevelCompositor", {}).get("status") != "generated_four_offline_variants":
        raise ValueError("Stage manifest does not report all four generated compositor variants.")

    stage_variants = {item.get("id"): item for item in fixture.get("stageLevelCompositor", [])}
    if set(stage_variants) != {"A", "B", "C", "D"}:
        raise ValueError("Stage manifest does not contain the complete A-D variant set.")
    if not variants or any(value not in ("A", "B", "C", "D") for value in variants):
        raise ValueError("Requested variants must be a non-empty subset of A-D.")

    canvas_rect = profile.get("canvasClientRect") or {}
    offset = report.get("transform", {}).get("screen_offset_from_client") or {}
    stage_origin = derive_stage_canvas_origin(canvas_rect, offset)
    css_matrix = parse_css_matrix(profile.get("canvasCssTransform", ""))
    if profile.get("canvasCssTransformOrigin") not in ("0px 0px", "0px 0px 0px"):
        raise ValueError(f"Unsupported canvas transform origin: {profile.get('canvasCssTransformOrigin')!r}")

    screen_compositing = report.get("screen_compositing", {})
    screen_size = (
        int(screen_compositing.get("screen_size", {}).get("width", 0)),
        int(screen_compositing.get("screen_size", {}).get("height", 0)),
    )
    if min(screen_size) <= 0 or screen_size != (
        int(profile.get("screen", {}).get("width", 0)), int(profile.get("screen", {}).get("height", 0))
    ):
        raise ValueError("Stage profile and same-run screenshot dimensions do not match.")

    before_png = experiment_dir / "before_clear-screen.png"
    after_png = experiment_dir / "after_draw-screen.png"
    for path in (before_png, after_png):
        if not path.is_file():
            raise FileNotFoundError(path)
    before_rgb = load_rgb(before_png)
    after_rgb = load_rgb(after_png)
    if before_rgb.shape[:2] != (screen_size[1], screen_size[0]) or after_rgb.shape != before_rgb.shape:
        raise ValueError("Same-run full-screen screenshots do not match the Monitor screen dimensions.")

    bounds = report.get("board_bounds_audit", {}).get("bounds", {})
    bx, by, bw, bh = (int(bounds.get(key, 0)) for key in ("x", "y", "width", "height"))
    if bx < 0 or by < 0 or bw <= 0 or bh <= 0 or bx + bw > screen_size[0] or by + bh > screen_size[1]:
        raise ValueError(f"Invalid screenshot-derived BoardPane bounds: {bounds!r}")

    independent_origin = report.get("transform", {}).get("board_to_screen", {})
    if "origin_x" not in independent_origin or "origin_y" not in independent_origin:
        raise ValueError("Independent board-to-screen origin is missing from the comparison report.")
    threshold = float(report.get("thresholds", {}).get("formal_screen_rgb_delta", 24.0))
    # Compare live and expected masks against the exact same Firefox round-trip baseline.
    # Keep the raw-before mask as a sensitivity diagnostic for the <=1 RGB round-trip delta.
    observed_full = build_change_mask(after_rgb, baseline_rgb, threshold)
    observed_raw_baseline_full = build_change_mask(after_rgb, before_rgb, threshold)
    observed = observed_full[by:by + bh, bx:bx + bw]
    observed_raw_baseline = observed_raw_baseline_full[by:by + bh, bx:bx + bw]
    firefox = find_firefox()
    actual_version = firefox_version(firefox)
    expected_ua = screen_compositing.get("browser", {}).get("expected_user_agent", "")
    expected_match = re.search(r"Firefox/([0-9.]+)", expected_ua)
    if not expected_match or expected_match.group(1).split(".", 1)[0] != actual_version.split(".", 1)[0]:
        raise RuntimeError(
            f"Firefox major version mismatch: same-run={expected_ua!r}, current={actual_version!r}."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    browser_dir = output_dir / "firefox-stage-compositor"
    browser_dir.mkdir(parents=True, exist_ok=True)
    baseline_html = browser_dir / "baseline-only.html"
    baseline_capture = browser_dir / "baseline-only.png"
    baseline_html.write_text(build_html(before_png, screen_size), encoding="utf-8")
    baseline_run = capture_firefox(firefox, baseline_html, baseline_capture,
                                   browser_dir / "profile-baseline", screen_size)
    baseline_rgb = load_rgb(baseline_capture)
    roundtrip = np.max(np.abs(baseline_rgb - before_rgb), axis=2)
    if int(roundtrip.max()) > 1:
        raise RuntimeError("Firefox baseline round-trip differs from the original screenshot by more than one channel value.")

    result: dict[str, Any] = {
        "status": "DIAGNOSTIC_ONLY",
        "acceptance_decision_applied": False,
        "orientation": orientation,
        "run_id": run_id,
        "source_session_id": profile.get("sourceSessionId"),
        "source_experiment_id": profile.get("sourceExperimentId"),
        "browser": {"name": "Firefox", "version": actual_version, "expected_user_agent": expected_ua,
                    "major_version_match": True},
        "screen_size": {"width": screen_size[0], "height": screen_size[1]},
        "stage_origin_screen_px": stage_origin,
        "stage_css_matrix_from_same_run_monitor": css_matrix,
        "canvas_client_rect": canvas_rect,
        "screen_offset_from_client": offset,
        "independent_board_to_screen_origin": independent_origin,
        "board_bounds_screen_px": bounds,
        "board_origin_crosschecks": {},
        "threshold_rgb_delta": threshold,
        "post_hoc_alignment": False,
        "baseline_round_trip": {
            "max_channel_error": int(roundtrip.max()),
            "pixels_over_one": int(np.count_nonzero(roundtrip > 1)),
            "observed_mask_delta_pixels_vs_raw_before": int(
                np.count_nonzero(observed != observed_raw_baseline)
            ),
            "observed_mask_comparison": mask_metrics(observed, observed_raw_baseline),
        },
        "browser_runs": {"baseline-only": baseline_run},
        "variants": {},
        "source_hashes": {"before_screen": sha256(before_png), "after_screen": sha256(after_png),
                          "stage_manifest": sha256(stage_manifest_path)},
        "limitations": [
            "Diagnostic comparison only; existing formal PASS_PER_RUN gates are unchanged.",
            "No post-hoc translation, registration, or image fitting is applied.",
            "The CSS transform comes from the same-run Game Monitor snapshot; board-to-screen fit is an independent cross-check.",
        ],
    }

    for variant in variants:
        metadata = stage_variants[variant]
        if metadata.get("backend") != "WebGL":
            raise ValueError(f"Variant {variant} is not an Egret WebGL variant.")
        placement = metadata.get("placement", {})
        predicted_origin = predict_board_screen_origin(stage_origin, placement, css_matrix)
        crosscheck = validate_board_origin_crosscheck(
            predicted_origin,
            {"x": float(independent_origin["origin_x"]), "y": float(independent_origin["origin_y"])},
            tolerance_px=1.0,
        )
        stage_png = stage_png_dir / VARIANT_FILES[variant]
        if not stage_png.is_file():
            raise FileNotFoundError(stage_png)
        with Image.open(stage_png) as image:
            if image.size != (int(profile["canvasBackingWidth"]), int(profile["canvasBackingHeight"])):
                raise ValueError(f"Stage PNG size {image.size} differs from run-bound backing dimensions.")
        html_path = browser_dir / f"variant-{variant}.html"
        capture_path = browser_dir / f"variant-{variant}.png"
        html_path.write_text(build_html(before_png, screen_size, stage_png, stage_origin, css_matrix), encoding="utf-8")
        browser_run = capture_firefox(firefox, html_path, capture_path,
                                      browser_dir / f"profile-variant-{variant}", screen_size)
        composite_rgb = load_rgb(capture_path)
        expected_full = build_change_mask(composite_rgb, baseline_rgb, threshold)
        expected = expected_full[by:by + bh, bx:bx + bw]
        if not np.any(expected):
            raise RuntimeError(f"Variant {variant} produced an empty Stage overlay mask.")
        metrics = mask_metrics(observed, expected)
        Image.fromarray((observed.astype(np.uint8) * 255), mode="L").save(output_dir / "live-observed-mask.png")
        Image.fromarray((expected.astype(np.uint8) * 255), mode="L").save(output_dir / f"variant-{variant}-expected-mask.png")
        Image.fromarray(composite_rgb.astype(np.uint8), mode="RGB").save(output_dir / f"variant-{variant}-screen-composite.png")
        result["board_origin_crosschecks"][variant] = {"predicted_board_screen_origin": predicted_origin, **crosscheck}
        result["browser_runs"][f"variant-{variant}"] = browser_run
        result["variants"][variant] = {
            "backend": metadata["backend"],
            "placement": placement,
            "stage_png": str(stage_png),
            "stage_png_sha256": sha256(stage_png),
            "comparison_metrics": metrics,
            "expected_mask_pixels_outside_board_crop": int(np.count_nonzero(expected_full)) - int(np.count_nonzero(expected)),
        }

    report_path = output_dir / f"stage-level-{orientation}-comparison.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orientation", choices=("vertical", "diagonal"), required=True)
    parser.add_argument("--stage-manifest", type=Path, required=True)
    parser.add_argument("--stage-png-dir", type=Path, required=True)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--comparison-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--variants", nargs="+", choices=tuple(VARIANT_FILES), default=["A", "B"])
    args = parser.parse_args()
    result = compare_stage_variants(args.orientation, args.stage_manifest, args.stage_png_dir,
                                    args.experiment_dir, args.comparison_report, args.output_dir, args.variants)
    print(json.dumps({
        "status": result["status"],
        "orientation": result["orientation"],
        "run_id": result["run_id"],
        "stage_origin_screen_px": result["stage_origin_screen_px"],
        "variants": {key: value["comparison_metrics"] for key, value in result["variants"].items()},
        "report": str(args.output_dir / f"stage-level-{args.orientation}-comparison.json"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
