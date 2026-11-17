#!/usr/bin/env python3
"""ENGINE-001 P4c2: immutable P4c1 source plan -> real Egret all17 paint-only gate.

This is E3 archived BoardPane replay, NOT game E4, original410 detail integration
or exact CHALK. Never promote paint-only into full-image acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import io
import zipfile
from pathlib import Path

import numpy as np

from run_engine001_color32_p4c1_directional_micro import _frozen_base_paths_sha
from run_engine001_color32_s2b_egret_p1 import (
    FROZEN_PALETTE_GIT_BLOB, FROZEN_RENDERER_GIT_BLOB,
    git_blob_sha, native_metrics,
)
from run_engine001_color32_p4c0_all_owner_feasibility import (
    FROZEN_DETAILS, FROZEN_DETAIL_VERTICES, SOURCE_SHA, G_PNG_SHA,
)
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_palette32_region_study import sha

EXP = "ENGINE001_COLOR32_P4C2_FULL_17_OWNER_NATIVE"
FROZEN_SOURCE_PATHS_SHA = "f9e2d9a5e17ac2d7c098573e4c5df6852112489d12d3272207cb7b7a56c4a23c"
FROZEN_SOURCE_REPORT_SHA = "1badb1913369cbad690c1cfbdf04778a4e6fde126042d633f8548fc77d606873"
FROZEN_SOURCE_CI_SHA = "02303521af46bc0f5d60241592b861f73d03a253"
FROZEN_ZIP_SHA = "fac1fcf1ff6a43ac6e59da116b68b86e2238c2da13be0b167cf34f8241ac5eeb"
FROZEN_P4C0_PLAN_SHA = "b9ca97fde1b3ed205b8b69cd3c6dc3bf6ef6af7d52060a3b1e93a07a1b1f7901"
OWNERS = (4, 5, 6, 10, 11, 14, 15, 16, 17, 19, 20, 22, 23, 27, 28, 29, 31)
ALPHAS = (24, 128)
NATIVE_MIN_COVERAGE = .99
FROZEN_PAINT_PATHS = 1133
FROZEN_PAINT_VERTICES = 3485


def validate_frozen_paths(source_paths):
    if source_paths.get("safe_to_execute_game") is not False:
        raise ValueError("BLOCKED_P4C2_GAME_EXECUTION_FLAG")
    base = source_paths.get("original_P4c0_strokes", [])
    extra = source_paths.get("P4c1_additions", [])
    paths = base + extra
    if len(base) != 119 or len(extra) != 1014 or len(paths) != FROZEN_PAINT_PATHS:
        raise ValueError("BLOCKED_P4C2_FROZEN_PATH_COUNTS")
    vertices = sum(len(s.get("points", [])) for s in paths)
    if vertices != FROZEN_PAINT_VERTICES:
        raise ValueError("BLOCKED_P4C2_FROZEN_VERTEX_COUNT")
    ids = [s.get("strokeId") for s in paths]
    if (len(set(ids)) != len(ids) or
            any(not isinstance(i, str) or re.fullmatch(r"icon-[0-9]+", i) is None for i in ids)):
        raise ValueError("BLOCKED_P4C2_STROKE_IDS")
    if sorted({s.get("colorIndex") for s in paths}) != list(OWNERS):
        raise ValueError("BLOCKED_P4C2_OWNER_SET")
    if len(paths) + FROZEN_DETAILS > 3000 or vertices + FROZEN_DETAIL_VERTICES > 5900:
        raise ValueError("BLOCKED_P4C2_RESOURCE_CAP")
    if any(not 2 <= len(s["points"]) <= 128 for s in paths):
        raise ValueError("BLOCKED_P4C2_POINT_COUNT")
    return paths


def assess_native(native):
    """Pure, native-metric-only gate; no source OpenCV coverage shortcuts."""
    result = {}
    if set(native) != {str(x) for x in ALPHAS}:
        raise ValueError("BLOCKED_P4C2_NATIVE_ALPHA_SET")
    for alpha in ALPHAS:
        groups = native[str(alpha)]
        if set(groups) != {str(o) for o in OWNERS}:
            raise ValueError("BLOCKED_P4C2_NATIVE_OWNER_SET")
        per_owner = {}
        for owner in OWNERS:
            m = groups[str(owner)]
            total = int(m["owner_target_backing_pixels"])
            correct = int(m["native_correct_owner_pixels"])
            far = int(m["non_owner_beyond_3logical_px"])
            exterior = int(m["ink_outside_image_ROI"])
            ink = int(m["native_alpha_ink_pixels"])
            if total <= 0 or correct < 0 or correct > total or ink <= 0:
                raise ValueError("BLOCKED_P4C2_NATIVE_TARGET_OR_BLANK")
            if far < 0 or exterior < 0:
                raise ValueError("BLOCKED_P4C2_NATIVE_INVALID_LEAK")
            per_owner[str(owner)] = {
                "native_coverage_pct": 100. * correct / total,
                "coverage_ge_99": correct / total >= NATIVE_MIN_COVERAGE,
                "foreign_beyond3_logical_px": far,
                "outside_original_ROI": exterior,
                "foreign_any_distance": int(m["non_owner_native_pixels_any_distance"]),
                "safety_ok": far == 0 and exterior == 0,
            }
        result[str(alpha)] = per_owner
    quality = all(result["24"][str(o)]["coverage_ge_99"] for o in OWNERS)
    safe = all(result[str(a)][str(o)]["safety_ok"]
               for a in ALPHAS for o in OWNERS)
    return {
        "per_owner_by_alpha": result,
        "native_alpha24_all17_ge99": quality,
        "native_alpha24_128_all17_safety": safe,
        "native_paint_numeric_gate": quality and safe,
        "owners_below99_native_alpha24": [
            o for o in OWNERS if not result["24"][str(o)]["coverage_ge_99"]],
        "full_image_with_original_410_last": "NOT_RUN",
        "full_image_quality": "NOT_RUN",
    }


def load_frozen_archive(archive_path: Path):
    """Use exact historical source PNG and routes, never regenerate G on Windows."""
    if sha(archive_path) != FROZEN_ZIP_SHA:
        raise ValueError("BLOCKED_P4C2_FROZEN_ZIP_SHA")
    with zipfile.ZipFile(archive_path) as z:
        if z.testzip() is not None:
            raise ValueError("BLOCKED_P4C2_FROZEN_ZIP_CRC")
        expected = {"report.json", "source_paths.json", "original_G32_index.png",
                    "original_G32_RGB.png", "P4c0_SOURCE_MODEL_uncovered.png",
                    "P4c1_SOURCE_MODEL_uncovered.png"}
        if set(z.namelist()) != expected:
            raise ValueError("BLOCKED_P4C2_FROZEN_ZIP_MEMBERS")
        report_bytes = z.read("report.json")
        paths_bytes = z.read("source_paths.json")
        g_bytes = z.read("original_G32_index.png")
        if (hashlib.sha256(report_bytes).hexdigest() != FROZEN_SOURCE_REPORT_SHA or
                hashlib.sha256(paths_bytes).hexdigest() != FROZEN_SOURCE_PATHS_SHA or
                hashlib.sha256(g_bytes).hexdigest() != G_PNG_SHA):
            raise ValueError("BLOCKED_P4C2_FROZEN_FILE_SHA")
        report = json.loads(report_bytes)
        if (report.get("github_sha") != FROZEN_SOURCE_CI_SHA or
                str(report.get("github_run_id")) != "44098998634" or
                report.get("source_sha256") != SOURCE_SHA or
                report.get("game_palette_git_blob") != FROZEN_PALETTE_GIT_BLOB or
                report.get("status") != "SOURCE_INCREMENTAL_PASS_NATIVE_PENDING" or
                report.get("original_P4c0_strokes_SHA256") != FROZEN_P4C0_PLAN_SHA or
                report.get("original_G_index_png_SHA256") != G_PNG_SHA or
                report.get("original_owners") != list(OWNERS) or
                report.get("projected_total_strokes_with_frozen_V44B410_LAST") != 1543 or
                report.get("projected_total_vertices_with_frozen_V44B1792_NOT_CHALK") != 5277):
            raise ValueError("BLOCKED_P4C2_FROZEN_REPORT_IDENTITY")
        linked = report.get("source_file_sha256", {})
        if set(linked) != expected - {"report.json"}:
            raise ValueError("BLOCKED_P4C2_LINKED_FILE_SET")
        for filename, digest in linked.items():
            if hashlib.sha256(z.read(filename)).hexdigest() != digest:
                raise ValueError("BLOCKED_P4C2_LINKED_FILE_SHA")
        from PIL import Image
        with Image.open(io.BytesIO(g_bytes)) as image:
            if image.mode != "L" or image.size != (150, 240):
                raise ValueError("BLOCKED_P4C2_FROZEN_G_GEOMETRY")
            g = np.array(image, dtype=np.uint8, copy=True)
        data = json.loads(paths_bytes)
    if (data.get("frozen_P4c0_119_strokes_SHA256") != FROZEN_P4C0_PLAN_SHA or
            _frozen_base_paths_sha(data.get("original_P4c0_strokes", []))
            != FROZEN_P4C0_PLAN_SHA):
        raise ValueError("BLOCKED_P4C2_FROZEN_BASELINE")
    paths = validate_frozen_paths(data)
    if any(not np.any(g == owner) for owner in OWNERS):
        raise ValueError("BLOCKED_P4C2_FROZEN_OWNER_MASK")
    return g, paths


def run(workspace: Path, source: Path, palette: Path, output: Path,
        frozen_source_archive: Path):
    if output.exists():
        raise ValueError("BLOCKED_P4C2_IMMUTABLE_OUTPUT")
    renderer = workspace / "AutoDraw_Stage20/tests/game_renderer_reference.js"
    if (git_blob_sha(renderer) != FROZEN_RENDERER_GIT_BLOB or
            git_blob_sha(palette) != FROZEN_PALETTE_GIT_BLOB):
        raise ValueError("BLOCKED_P4C2_RENDERER_OR_PALETTE_DRIFT")
    if sha(source) != SOURCE_SHA:
        raise ValueError("BLOCKED_P4C2_SOURCE_DRIFT")
    g, paths = load_frozen_archive(frozen_source_archive)
    output.mkdir(parents=True)
    (output / "frozen-source-identity.json").write_text(json.dumps({
        "original_P4c1_source_paths_SHA256": FROZEN_SOURCE_PATHS_SHA,
        "original_P4c1_report_SHA256": FROZEN_SOURCE_REPORT_SHA,
        "original_P4c1_archive_SHA256": FROZEN_ZIP_SHA,
        "original_P4c1_CI_SHA": FROZEN_SOURCE_CI_SHA,
        "original_P4c1_CI_run_id": 44098998634,
        "source_sha256": sha(source),
        "palette_git_blob": FROZEN_PALETTE_GIT_BLOB,
        "renderer_git_blob": FROZEN_RENDERER_GIT_BLOB,
        "frozen_G32_index_png_SHA256": G_PNG_SHA,
        "frozen_paint_strokes": len(paths),
        "frozen_paint_vertices_NOT_CHALK": FROZEN_PAINT_VERTICES,
        "projected_strokes_with_410_details": len(paths) + FROZEN_DETAILS,
        "projected_vertices_with_1792_details_NOT_CHALK":
            FROZEN_PAINT_VERTICES + FROZEN_DETAIL_VERTICES,
        "windows_G_recomputation": "NOT_USED; original P4c1 archived pixels are authoritative",
        "safe_to_execute_game": False, "exact_CHALK": None,
    }, indent=2) + "\n", encoding="utf-8")
    folder = output / "P4c1-PAINT-ONLY"
    folder.mkdir()
    frames, metadata, manifest = native_batch(
        workspace, "P4c1-PAINT-ONLY", paths, folder,
        renderer_method="renderComplexHoldoutColorProbe")
    native = native_metrics(frames, g, paths)
    observed = assess_native(native)
    hashes = {str(f.relative_to(output)).replace("\\", "/"): sha(f)
              for f in output.rglob("*") if f.is_file()}
    report = {
        "experiment": EXP,
        "status": ("P4C2_NATIVE_PAINT_ONLY_PARTIAL" if observed[
            "native_paint_numeric_gate"] else "P4C2_NATIVE_PAINT_FAIL"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "source": "frozen original P4c1; model never accepted as native",
        "renderer": "archived actual BoardPane / Firefox WebGL",
        "native_paint_only": True,
        "original_410_V44B_LAST": "NOT_RENDERED_UNCHANGED",
        "native_observations": observed,
        "raw_native_metrics": native,
        "native_metadata": metadata,
        "native_manifest": manifest,
        "linked_file_SHA256": hashes,
        "versions": {"python": platform.python_version(),
                     "numpy": np.__version__},
        "game_E4": "NOT_RUN", "independent_E5": "NOT_RUN",
        "exact_CHALK": None, "production_accepted": False,
    }
    (output / "report.json").write_text(json.dumps(
        report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--palette", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--frozen-source-archive", type=Path, required=True)
    a = p.parse_args()
    r = run(a.workspace, a.source, a.palette, a.output, a.frozen_source_archive)
    print(json.dumps({
        "status": r["status"],
        "native_alpha24_below99": r["native_observations"]["owners_below99_native_alpha24"],
        "native_safety_all17": r["native_observations"]["native_alpha24_128_all17_safety"],
        "full_image_quality": "NOT_RUN",
        "exact_CHALK": None,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
