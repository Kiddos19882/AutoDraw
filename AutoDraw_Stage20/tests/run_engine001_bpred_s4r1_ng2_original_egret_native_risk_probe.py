#!/usr/bin/env python3
"""NG2 research only: fixed source-known original E/F single-stroke true Egret risk.

Runs real Egret/BoardPane/WebGL via existing P4D13 and P4B7 harness; never
grants a brush-stroke permission, predicts game CHALK, or modifies production.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image

import engine001_bpred_s4r1_generic_source_maps as maps
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as p4d0
import run_engine001_b1r_p4d13_full_original_relaxed_finish as p4d13
import run_engine001_b1r_p4d18_physical_owner_edt_repair as p4d18

TASK = "ENGINE001_BPRED_S4R1_NG2_ORIGINAL_EF_TRUE_EGRET_RISK_V1"
E0 = "ENGINE001_BPRED001_S4R1_NG2_ORIGINAL_EF_NATIVE_SINGLE_STROKE_RISK_PREREG_2026-11-21.md"
E0_BLOB = "c9a5af70223c5eccbadb36e659c98d4ebdf2d186"
ARCHIVE_SHA = maps.SOURCE_KNOWN_EGRET_ARTIFACT_SHA256
WIDTHS = (1, 3)
POSITION_QUANTILES = (0, 1, 2, 3, 4)
METHODS = ("E_SOBEL90", "F_SOBEL90_LAB12")
ALPHA = 24
SCALE = 3
X0 = 155
EXPECTED_SCENES = 21


def choose_original_unknown_cells(contract: dict) -> list[tuple[int, int]]:
    """Five frozen row-major indices, no feedback/adaptation/ROI selection."""
    if (not isinstance(contract, dict) or
            contract.get("stroke_admission") !=
                "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION" or
            contract.get("scientific_s4") != "BLOCKED" or
            not isinstance(contract.get("candidate_interior"), np.ndarray) or
            not isinstance(contract.get("unknown"), np.ndarray)):
        raise ValueError("BLOCKED_NG2_NO_FAIL_CLOSED_SOURCE_CONTRACT")
    core = contract["candidate_interior"]
    unknown = contract["unknown"]
    if (core.dtype != bool or unknown.dtype != bool or
            core.ndim != 2 or unknown.shape != core.shape or
            np.any(core & ~unknown)):
        raise ValueError("BLOCKED_NG2_CORE_NOT_SOURCE_UNKNOWN")
    cells = np.argwhere(core)
    n = int(len(cells))
    if n < 5:
        raise ValueError("BLOCKED_NG2_INSUFFICIENT_RESEARCH_CELLS")
    positions = [0, n // 4, n // 2, (3 * n) // 4, n - 1]
    if len(set(positions)) != 5:
        raise ValueError("BLOCKED_NG2_NONINDEPENDENT_SOURCE_POSITIONS")
    return [(int(cells[i, 0]), int(cells[i, 1])) for i in positions]


def score_native_single(
    native: np.ndarray,
    source_index: np.ndarray,
    protected: np.ndarray,
    original_rgb_strong_contrast: np.ndarray,
    paint_owner: int,
    white_owner: int,
) -> dict[str, int]:
    """Actual native RGBA footprint, no model-painted pixels or approximations."""
    if (not isinstance(native, np.ndarray) or
            native.shape != (720, 1380, 4) or native.dtype != np.uint8 or
            not isinstance(source_index, np.ndarray) or
            source_index.shape != (240, 150) or
            source_index.dtype != np.uint8 or
            any(not isinstance(mask, np.ndarray) or
                mask.shape != source_index.shape or mask.dtype != bool
                for mask in (protected, original_rgb_strong_contrast)) or
            not isinstance(paint_owner, (int, np.integer)) or
            not isinstance(white_owner, (int, np.integer)) or
            not 0 <= int(paint_owner) < 128 or
            not 0 <= int(white_owner) < 128 or
            int(paint_owner) == int(white_owner)):
        raise ValueError("BLOCKED_NG2_NATIVE_SOURCE_OR_OWNER_SHAPE")
    crop = native[:, X0 * SCALE:(X0 + 150) * SCALE, :]
    ink = crop[:, :, 3] >= ALPHA
    physical = native[:, :, 3] >= ALPHA
    target = np.repeat(np.repeat(source_index, SCALE, 0), SCALE, 1)
    guard = np.repeat(np.repeat(protected, SCALE, 0), SCALE, 1)
    contour = np.repeat(np.repeat(original_rgb_strong_contrast, SCALE, 0), SCALE, 1)
    inside = int(np.count_nonzero(ink))
    total = int(np.count_nonzero(physical))
    return {
        "actual_ink_alpha24_total_backing": total,
        "inside_source_alpha24_backing": inside,
        "outside_source_alpha24_backing": total - inside,
        "painted_intended_owner_alpha24": int(np.count_nonzero(
            ink & (target == paint_owner))),
        "painted_other_nonwhite_owner_alpha24": int(np.count_nonzero(
            ink & (target != paint_owner) & (target != white_owner))),
        "painted_source_white_alpha24": int(np.count_nonzero(
            ink & (target == white_owner))),
        "painted_skc1_protected_alpha24": int(np.count_nonzero(ink & guard)),
        "painted_original_rgb_contour_alpha24": int(np.count_nonzero(ink & contour)),
    }


def _read_archive_image(z: ZipFile, name: str, mode: str) -> np.ndarray:
    with Image.open(io.BytesIO(z.read(name))) as im:
        if im.mode != mode or im.size != (150, 240):
            raise ValueError("BLOCKED_NG2_ORIGINAL_ARCHIVE_IMAGE_MODE " + name)
        return np.asarray(im).copy()


def verified_original_sources(archive_path: Path, engine_js: Path):
    """P4D18 immutable archive, exact game128 source owners, SKC1 fail-closed."""
    raw = archive_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA:
        raise ValueError("BLOCKED_NG2_ORIGINAL_P4D18_ARCHIVE_SHA")
    palette, engine = p3b.read_engine_palette(engine_js)
    with ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None:
            raise ValueError("BLOCKED_NG2_ORIGINAL_ZIP_CRC")
        report = json.loads(z.read("report.json"))
        if (report.get("experiment") != p4d18.EXPERIMENT or
                report.get("game_bundle_git_blob") != p4d18.GAME_BLOB or
                report.get("renderer_git_blob") != p4d18.RENDERER_BLOB or
                report.get("native_full_scenes") != 9 or
                report.get("blank_true_native_alpha0") is not True or
                len(report.get("members_sha256", {})) != 34):
            raise ValueError("BLOCKED_NG2_ORIGINAL_P4D18_REPORT_PROVENANCE")
        for name, sha in report["members_sha256"].items():
            if hashlib.sha256(z.read(name)).hexdigest() != sha:
                raise ValueError("BLOCKED_NG2_ORIGINAL_P4D18_MEMBER_SHA " + name)
        rgb = _read_archive_image(z, "ORIGINAL_RGB_LOGICAL.png", "RGB")
        rgba = np.concatenate((
            rgb, np.full((240, 150, 1), 255, dtype=np.uint8)), axis=2)
        result = {}
        for method in METHODS:
            index = _read_archive_image(z, method + "/SOURCE_OWNER_INDEX.png", "L")
            target = _read_archive_image(z, method + "/SOURCE_OWNER_RGB.png", "RGB")
            provenance = {
                "source_kind": "ORIGINAL_P4D18_EF_LOGICAL",
                "artifact_id": 14557770111, "archive_sha256": ARCHIVE_SHA,
                "method": method,
                "engine_git_blob_sha1": p4d18.GAME_BLOB,
                "renderer_git_blob_sha1": p4d18.RENDERER_BLOB,
                "archive_members_verified": True,
                "original_rgba_sha256": hashlib.sha256(rgba.tobytes()).hexdigest(),
                "owner_index_sha256": hashlib.sha256(index.tobytes()).hexdigest(),
                "owner_rgb_sha256": hashlib.sha256(target.tobytes()).hexdigest(),
                "game128_sha256": hashlib.sha256(palette.tobytes()).hexdigest(),
            }
            contract = maps.source_known_egret_protection_contract(
                rgba, index, target, palette, engine, provenance)
            if (contract["counts"]["candidate_interior"] not in (1919, 1921) or
                    contract["counts"]["candidate_interior"] !=
                    {"E_SOBEL90": 1919, "F_SOBEL90_LAB12": 1921}[method]):
                raise ValueError("BLOCKED_NG2_SKC1_BASELINE_DRIFT")
            result[method] = (index, contract, choose_original_unknown_cells(contract))
    return palette, result


def run(workspace: Path, archive: Path, engine_js: Path,
        renderer: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_NG2_OUTPUT_EXISTS")
    e0_raw = (workspace / "AutoDraw_Stage20" / "docs" / E0).read_bytes()
    e0_sha = maps.git_blob_sha1(e0_raw)
    if e0_sha != E0_BLOB:
        raise ValueError("BLOCKED_NG2_E0_DRIFT")
    if (p4b1.git_blob(renderer.read_bytes()) != p4d18.RENDERER_BLOB or
            p4b1.git_blob(engine_js.read_bytes()) != p4d18.GAME_BLOB):
        raise ValueError("BLOCKED_NG2_PINNED_RENDERER_OR_GAME")
    palette, method_data = verified_original_sources(archive, engine_js)
    output.mkdir(parents=True, exist_ok=False)
    samples = {}
    for method, (index, contract, cells) in method_data.items():
        samples[method] = [
            {"rank": i, "y": y, "x": x,
             "owner": int(index[y, x]), "widths": list(WIDTHS)}
            for i, (y, x) in enumerate(cells)
        ]
    scenes = []
    with p4d0.patched_test_renderer(renderer):
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(900)
            browser = {
                "browserName": driver.capabilities.get("browserName"),
                "browserVersion": driver.capabilities.get("browserVersion"),
                "platformName": driver.capabilities.get("platformName"),
            }
            if not str(browser["browserVersion"]).startswith("159."):
                raise ValueError("BLOCKED_NG2_WRONG_FIREFOX_BROWSER")
            blank, metadata = p4d13.render(driver, output, "NG2_TRUE_EGRET_BLANK", [])
            if np.any(blank[:, :, 3]):
                raise ValueError("BLOCKED_NG2_NONEMPTY_NATIVE_BLANK")
            blank_hash = metadata["source_sha256"]
            for method in METHODS:
                index, contract, cells = method_data[method]
                folder = output / method
                folder.mkdir()
                for rank, (y, x) in enumerate(cells):
                    owner = int(index[y, x])
                    if int(contract["protected"][y, x]) != 0:
                        raise ValueError("BLOCKED_NG2_PROBE_IN_PROTECTED")
                    for width in WIDTHS:
                        plan = p4d0._stroke(
                            owner, palette, float(x) - 0.025,
                            float(x) + 0.025, int(y), width=width)
                        stem = "NG2_C" + str(rank) + "_W" + str(width)
                        native, meta = p4d13.render(driver, folder, stem, [plan])
                        stats = score_native_single(
                            native, index, contract["protected"],
                            contract["original_rgb_strong_contrast"],
                            owner, 6)
                        scenes.append({
                            "method": method, "rank": rank, "source_x": x,
                            "source_y": y, "source_owner": owner,
                            "width": width, "native_png_sha256": meta["source_sha256"],
                            "stroke_preview_only": True,
                            "stroke_admission": "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION",
                            **stats,
                        })
                        print("NG2_TRUE_EGRET_NATIVE", method, rank, width,
                              json.dumps(stats, sort_keys=True), flush=True)
    if p4b1.git_blob(renderer.read_bytes()) != p4d18.RENDERER_BLOB:
        raise ValueError("BLOCKED_NG2_RENDERER_NOT_RESTORED")
    if len(scenes) != 20:
        raise ValueError("BLOCKED_NG2_SCENE_COUNT")
    summary = {
        "task": TASK, "frozen_e0_blob": E0_BLOB,
        "source_archive_sha256": ARCHIVE_SHA,
        "source_game_git_blob": p4d18.GAME_BLOB,
        "source_renderer_git_blob": p4d18.RENDERER_BLOB,
        "source_methods": list(METHODS), "widths": list(WIDTHS),
        "source_unknown_cells_fixed": {"E_SOBEL90": 1919, "F_SOBEL90_LAB12": 1921},
        "selected_unknown_samples": samples,
        "actual_original_egret_browser": browser,
        "actual_native_scene_count": EXPECTED_SCENES,
        "blank_native_png_sha256": blank_hash,
        "source_native_scene_count": len(scenes),
        "scenes": scenes,
        "total_foreign": sum(s["painted_other_nonwhite_owner_alpha24"] for s in scenes),
        "total_source_white": sum(s["painted_source_white_alpha24"] for s in scenes),
        "total_protected": sum(s["painted_skc1_protected_alpha24"] for s in scenes),
        "zero_stroke_admissions": True,
        "strict_S4": "BLOCKED",
        "native_paint_quality": "RESEARCH_DIAGNOSTIC_ONLY",
        "game_E4_E5_CHALK": "NOT_RUN",
        "heldout8_BLIND120_second50": "SEALED",
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
    }
    summary["raw_files_sha256"] = {
        str(f.relative_to(output)).replace("\\", "/"): hashlib.sha256(
            f.read_bytes()).hexdigest()
        for f in sorted(output.rglob("*")) if f.is_file()
    }
    (output / "report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.workspace, args.archive, args.engine,
                         args.renderer, args.output)["task"]))
