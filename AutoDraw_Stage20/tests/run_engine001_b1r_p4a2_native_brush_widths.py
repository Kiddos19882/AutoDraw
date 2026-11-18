#!/usr/bin/env python3
"""B1-R P4A2: all 1..10 real archived Egret/BoardPane brush widths.

ONLY original-sourced P3D E/F, no historical G32/V44 candidate inputs.
Actual native alpha in Firefox WebGL, NOT game E4 or exact CHALK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import native_batch

EXPERIMENT = "ENGINE001_B1R_P4A2_NATIVE_BRUSH_WIDTHS_1_TO_10_V1"
RENDERER_PARENT_BLOB = "c6df789a22b6ae0d205829d5858afff99b1bb4c2"
RENDERER_OPTIN_BLOB = "76d950e0a8911888a9df3b675b866519ecf7bba4"
SOURCE_KEY = "C_192_D_COMPONENT24"
METHODS = ("E_SOBEL90", "F_SOBEL90_LAB12")
WIDTHS = tuple(range(1, 11))
DIRECTIONS = {
    "HORIZONTAL": (7, 0),
    "DIAGONAL": (5, 5),
}
INSET_SOURCE_LOGICAL = 4.0
ALPHAS = (24, 128)
LOGICAL = (240, 150)
BOARD_SHAPE = (240, 460)
BACKING_SHAPE = (720, 1380, 4)
ROI_X0 = 155
BACKING_SCALE = 3
MAX_NONOWNER_DISTANCE_LOGICAL = 3.0


def git_blob(data: bytes):
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _eligible_anchors(centers: np.ndarray, dx: int, dy: int) -> np.ndarray:
    if centers.shape != LOGICAL or centers.dtype != np.bool_:
        raise ValueError("BLOCKED_P4A2_UNSAFE_SOURCE_CENTERS")
    longest = max(abs(dx), abs(dy))
    rows, cols = 240 - dy, 150 - dx
    ok = np.ones((rows, cols), dtype=bool)
    for step in range(longest + 1):
        ystep = int(round(step * dy / longest))
        xstep = int(round(step * dx / longest))
        ok &= centers[ystep:ystep + rows, xstep:xstep + cols]
    return np.argwhere(ok)


def choose_two_source_paths(e: np.ndarray, f: np.ndarray,
                            selected32: np.ndarray, game128: np.ndarray):
    """Pick distinct engine swatches with common E/F deep source centers."""
    if (e.shape != LOGICAL or f.shape != LOGICAL or
            e.dtype != np.uint8 or f.dtype != np.uint8 or
            selected32.shape != (32,) or
            len(set(int(v) for v in selected32)) != 32 or
            not np.issubdtype(selected32.dtype, np.integer) or
            game128.shape != (128, 3) or game128.dtype != np.uint8 or
            p3b.ENGINE_WHITE_INDEX not in selected32 or
            np.any(selected32 < 0) or np.any(selected32 >= 128) or
            not set(np.unique(e)).issubset(set(selected32)) or
            not set(np.unique(f)).issubset(set(selected32))):
        raise ValueError("BLOCKED_P4A2_SOURCE_MAP_OR_PALETTE")
    candidates = {}
    for idx in sorted(set(int(v) for v in selected32)):
        if idx == p3b.ENGINE_WHITE_INDEX:
            continue
        common = (e == idx) & (f == idx)
        if not common.any():
            continue
        distance = cv2.distanceTransform(
            np.pad(common.astype(np.uint8), 1),
            cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )[1:-1, 1:-1]
        centers = distance >= INSET_SOURCE_LOGICAL
        for orientation, (dx, dy) in DIRECTIONS.items():
            anchors = _eligible_anchors(centers, dx, dy)
            if len(anchors):
                candidates[(orientation, idx)] = (
                    len(anchors), (int(anchors[0, 0]), int(anchors[0, 1]))
                )
    selected = {}
    used = set()
    for orientation in DIRECTIONS:
        options = sorted(
            (
                (-count, idx, anchor)
                for (direction, idx), (count, anchor) in candidates.items()
                if direction == orientation and idx not in used
            ),
            key=lambda row: (row[0], row[1], row[2][0], row[2][1])
        )
        if not options:
            raise ValueError("BLOCKED_P4A2_NO_DISTINCT_SOURCE_ORIENTED_REGION")
        neg_count, idx, (y, x) = options[0]
        dx, dy = DIRECTIONS[orientation]
        used.add(idx)
        selected[orientation] = {
            "orientation": orientation,
            "engine128_index": idx,
            "engine_rgb_int": (int(game128[idx, 0]) << 16) |
                              (int(game128[idx, 1]) << 8) |
                              int(game128[idx, 2]),
            "engine_hex": "#%02X%02X%02X" % tuple(int(v) for v in game128[idx]),
            "source_anchor_yx": [y, x],
            "eligible_anchors_same_color_E_and_F": -neg_count,
            "minimum_source_common_distance_logical": INSET_SOURCE_LOGICAL,
            "two_source_points_xy": [[x, y], [x + dx, y + dy]],
            "two_board_logical_points_xy": [
                [x + ROI_X0, y], [x + ROI_X0 + dx, y + dy]
            ],
        }
    if len(used) != 2:
        raise AssertionError("BLOCKED_P4A2_ORIENTATION_COLOR_DUPLICATION")
    return selected


def make_native_strokes(paths: dict, width: int):
    if type(width) is not int or width not in WIDTHS or set(paths) != set(DIRECTIONS):
        raise ValueError("BLOCKED_P4A2_WIDTH_OR_ORIENTATION")
    strokes = []
    for i, orientation in enumerate(DIRECTIONS):
        item = paths[orientation]
        pts = item["two_board_logical_points_xy"]
        if (not isinstance(pts, list) or len(pts) != 2 or
                any(len(pt) != 2 or
                    not 155 <= pt[0] < 305 or not 0 <= pt[1] < 240
                    for pt in pts)):
            raise ValueError("BLOCKED_P4A2_UNSAFE_LOGICAL_POINTS")
        strokes.append({
            "strokeId": "icon-%d" % i,
            "width": width, "colorIndex": item["engine128_index"],
            "colorRgb": item["engine_rgb_int"],
            "points": [{"x": float(x), "y": float(y)} for x, y in pts],
        })
    if (strokes[0]["colorIndex"] == strokes[1]["colorIndex"] or
            sum(len(s["points"]) for s in strokes) != 4):
        raise ValueError("BLOCKED_P4A2_STROKE_OVERLAP_OR_BUDGET")
    return strokes


def _owner_backing(index: np.ndarray, owner: int):
    if index.shape != LOGICAL or index.dtype != np.uint8:
        raise ValueError("BLOCKED_P4A2_INDEX_SHAPE")
    board = np.zeros(BOARD_SHAPE, dtype=bool)
    board[:, ROI_X0:ROI_X0 + 150] = index == owner
    return np.repeat(np.repeat(board, BACKING_SCALE, axis=0), BACKING_SCALE, axis=1)


def geometry_metrics(native: np.ndarray, target: np.ndarray, distance: np.ndarray):
    if (native.shape != BACKING_SHAPE or native.dtype != np.uint8 or
            target.shape != BACKING_SHAPE[:2] or target.dtype != np.bool_ or
            distance.shape != target.shape or not np.issubdtype(distance.dtype, np.floating)):
        raise ValueError("BLOCKED_P4A2_NATIVE_OR_TARGET_SHAPE")
    result = {}
    for alpha in ALPHAS:
        ink = native[:, :, 3] >= alpha
        nonowner = ink & ~target
        far = nonowner & (distance > MAX_NONOWNER_DISTANCE_LOGICAL * BACKING_SCALE)
        owner_count = int(np.count_nonzero(target))
        native_owner = int(np.count_nonzero(ink & target))
        result[str(alpha)] = {
            "native_ink_backing_pixels": int(np.count_nonzero(ink)),
            "native_correct_owner_backing_pixels": native_owner,
            "target_owner_total_backing_pixels": owner_count,
            "pilot_fraction_of_full_owner_NOT_full_coverage":
                native_owner / owner_count if owner_count else None,
            "native_nonowner_any_distance": int(np.count_nonzero(nonowner)),
            "native_nonowner_beyond3logicalpx": int(np.count_nonzero(far)),
            "native_alpha_nonzero": bool(np.any(ink)),
        }
    return result


def run(workspace: Path, source_path: Path, engine_js_path: Path,
        renderer_path: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P4A2_OUTPUT_EXISTS")
    check_source(source_path)
    game128, _ = p3b.read_engine_palette(engine_js_path)
    renderer_raw = renderer_path.read_bytes()
    if git_blob(renderer_raw) != RENDERER_OPTIN_BLOB:
        raise ValueError("BLOCKED_P4A2_UNPINNED_OPTIN_EGRET_RENDERER")
    renderer_text = renderer_raw.decode("utf8")
    if ("renderP4A2BrushWidths1to10Probe" not in renderer_text or
            "function renderComplexHoldoutColorProbe" not in renderer_text):
        raise ValueError("BLOCKED_P4A2_INVALID_RENDERER_PATH")
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="engine001-p4a2-source-only-") as d:
        parent_output = Path(d) / "p3d_current_run"
        parent = p3d.run(source_path, engine_js_path, parent_output)
        if (parent["experiment"] != p3d.EXPERIMENT or
                parent["original_source_sha256"] != p3b.SOURCE_SHA or
                parent["P3B_original_recomputed_in_current_run"] is not True or
                parent["read_frozen_ZIP_as_source"] or
                parent["legacy_G32_V44_M1_used_as_source"] or
                set(parent["all_results"][SOURCE_KEY]["methods"]) != set(METHODS) or
                not all(item["status"] ==
                        "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED"
                        for item in parent["all_results"][SOURCE_KEY]["methods"].values())):
            raise ValueError("BLOCKED_P4A2_PARENT_P3D_SOURCE_QUALITY")
        selected = np.asarray(
            parent["all_results"][SOURCE_KEY]["selected_engine_indices"],
            dtype=np.int16)
        maps = {}
        for method in METHODS:
            name = SOURCE_KEY + "_" + method + "_ENGINE_INDICES.png"
            maps[method] = np.asarray(
                Image.open(parent_output / name), dtype=np.uint8).copy()
            shutil.copyfile(parent_output / name,
                            output / ("SOURCE_" + method + "_ENGINE_INDICES.png"))
            shutil.copyfile(parent_output / (SOURCE_KEY + "_" + method + "_RGB.png"),
                            output / ("SOURCE_" + method + "_RGB.png"))
        shutil.copyfile(parent_output / "00_ORIGINAL_RGB_LOGICAL.png",
                        output / "SOURCE_00_ORIGINAL_RGB_LOGICAL.png")
        paths = choose_two_source_paths(
            maps[METHODS[0]], maps[METHODS[1]], selected, game128)
        (output / "source_proposal_paths.json").write_text(
            json.dumps({
                "source": SOURCE_KEY, "accepted_P3D_methods": METHODS,
                "original_only_path_selection": True,
                "legacy_G32_V44_as_input": False,
                "paths": paths, "widths": WIDTHS,
                "orientations": list(DIRECTIONS),
                "source_inset_MODEL_ONLY": INSET_SOURCE_LOGICAL,
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        distance_cache = {}
        for method in METHODS:
            for orientation in DIRECTIONS:
                owner = paths[orientation]["engine128_index"]
                target = _owner_backing(maps[method], owner)
                if not target.any():
                    raise ValueError("BLOCKED_P4A2_OWNER_TARGET_EMPTY")
                dmap = cv2.distanceTransform(
                    (~target).astype(np.uint8), cv2.DIST_L2,
                    cv2.DIST_MASK_PRECISE)
                distance_cache[(method, orientation)] = (target, dmap)
        all_widths = {}
        for width in WIDTHS:
            strokes = make_native_strokes(paths, width)
            scene_path = output / ("native-width-%02d" % width)
            scene_path.mkdir()
            native, meta, manifest = native_batch(
                workspace, "P4A2-W%02d" % width, strokes, scene_path,
                renderer_method="renderP4A2BrushWidths1to10Probe")
            expect = {"blank", "composite"} | {
                "color-" + str(paths[o]["engine128_index"]) for o in DIRECTIONS}
            if (set(native) != expect or set(meta) != expect or
                    manifest["colors_rendered"] !=
                    sorted(paths[o]["engine128_index"] for o in DIRECTIONS) or
                    meta["composite"].get("schema") !=
                    "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
                    meta["blank"].get("schema") !=
                    "ENGINE001_B1R_P4A2_BLANK_WEBGL" or
                    meta["composite"].get("renderer") !=
                    "real Egret 5.4.1 BoardPane/WebGLRenderer" or
                    meta["composite"].get("usedWidths") != [width] or
                    meta["composite"].get("syntheticAcceptedVerticesNotChalk") != 4):
                raise ValueError("BLOCKED_P4A2_NATIVE_EGRET_SCHEMA")
            if any(a.shape != BACKING_SHAPE or a.dtype != np.uint8
                   for a in native.values()):
                raise ValueError("BLOCKED_P4A2_NATIVE_RGBA_BACKING")
            blank_pixel_count = int(np.count_nonzero(native["blank"][:, :, 3]))
            comparisons = {}
            for method in METHODS:
                colors = {}
                for orientation in DIRECTIONS:
                    owner = paths[orientation]["engine128_index"]
                    scene = native["color-%d" % owner]
                    target, distance = distance_cache[(method, orientation)]
                    metrics = geometry_metrics(scene, target, distance)
                    native_quality_ok = bool(
                        metrics["24"]["native_alpha_nonzero"] and
                        metrics["24"]["native_nonowner_beyond3logicalpx"] == 0 and
                        blank_pixel_count == 0)
                    colors[orientation] = {
                        "engine128_index": owner,
                        "actual_native_rgba": True,
                        "native_quality_pass_at_alpha24": native_quality_ok,
                        "alpha_metrics": metrics,
                    }
                comparisons[method] = colors
            all_widths[str(width)] = {
                "native_renderer_method": "renderP4A2BrushWidths1to10Probe",
                "native_blank_control_nonzero_alpha_pixels": blank_pixel_count,
                "native_renderer_glInfo": meta["composite"].get("glInfo"),
                "native_scene_diagnostics": meta["composite"].get("sceneDiagnostics"),
                "synthetic_vertices_NOT_CHALK": 4,
                "strokes": strokes,
                "methods": comparisons,
            }
            print("P4A2_NATIVE_WIDTH", width,
                  "E_PASS", [comparisons[METHODS[0]][o]["native_quality_pass_at_alpha24"]
                             for o in DIRECTIONS],
                  "F_PASS", [comparisons[METHODS[1]][o]["native_quality_pass_at_alpha24"]
                             for o in DIRECTIONS],
                  "blank_alpha_nonzero", blank_pixel_count, flush=True)
    comparisons = [
        all_widths[str(w)]["methods"][m][o]["native_quality_pass_at_alpha24"]
        for w in WIDTHS for m in METHODS for o in DIRECTIONS
    ]
    if len(comparisons) != 40 or any(str(w) not in all_widths for w in WIDTHS):
        raise AssertionError("BLOCKED_P4A2_MISSING_WIDTH_OR_TEST_COMPARISONS")
    status = ("PASS_ALL_10_NATIVE_ISOLATED_3PX" if all(comparisons) else
              "NATIVE_ISOLATED_PARTIAL_QUALITY_FAIL")
    (output / "README_REVIEW_RU.txt").write_text(
        "ENGINE-001 / B1-R-P4A2: реальные следы Egret/BoardPane для "
        "каждой ширины 1..10.\n"
        "SOURCE_*_RGB.png — принятые E/F цветовые карты (из исходного RGB).\n"
        "native-width-XX/P4A2-WXX-color-*.png — отдельно каждый цвет "
        "настоящей кистью.\n"
        "native-width-XX/P4A2-WXX-blank.png — пустой BoardPane/WebGL контроль.\n"
        "native-width-XX/P4A2-WXX-composite.png — две ориентации вместе.\n"
        "source_proposal_paths.json — одни и те же два штриха для всех 10 кистей.\n"
        "Отрицательные leakage/zero-ink результаты сохраняются, "
        "пороги не подстраиваются.\n"
        "E3 архивный Egret НЕ E4 в игре; точный CHALK не измерен.\n",
        encoding="utf8",
    )
    hashes = {
        str(p.relative_to(output)).replace("\\", "/"): digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    report = {
        "experiment": EXPERIMENT,
        "prereg": "ENGINE001_B1R_P4A2_NATIVE_BRUSH_WIDTHS_1_TO_10_V1",
        "status": status,
        "widths": list(WIDTHS),
        "all_10_widths_have_actual_native_Egret_RGBA": True,
        "all_40_native_source_EF_direction_comparisons": len(comparisons),
        "all_40_quality_gate_pass": all(comparisons),
        "source_SHA256": p3b.SOURCE_SHA,
        "engine_blob_sha1": p3b.ENGINE_GIT_BLOB_SHA1,
        "renderer_parent_git_blob_sha1": RENDERER_PARENT_BLOB,
        "renderer_optin_git_blob_sha1": RENDERER_OPTIN_BLOB,
        "original_only_source": SOURCE_KEY,
        "P3D_methods_user_approved": list(METHODS),
        "P3D_all_four_source_variants_still_allowed": True,
        "game128_palette_work_deferred_user_reported_selectable": True,
        "source_P3D_recomputed_original_only": True,
        "legacy_G32_V44_P4c1_inputs_used": False,
        "P3D_frozen_archive_used_as_input": False,
        "actual_native_renderer": "real Egret 5.4.1 BoardPane/WebGLRenderer",
        "native_backend_E3": "archived Firefox WebGL",
        "actual_game_runtime_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN",
        "exact_run_bound_CHALK": None,
        "production_promotion": False,
        "probe_paths": paths,
        "all_widths": all_widths,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "file_sha256": hashes,
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--engine-js", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.workspace, args.source, args.engine_js,
                 args.renderer, args.output)
    print("P4A2_NATIVE_E3_OFFLINE_COMPLETE", result["status"],
          "widths", result["widths"],
          "native_EF_orientation_comparisons",
          result["all_40_native_source_EF_direction_comparisons"])
    print("P4A2_NO_LIVE_E4_NO_EXACT_CHALK_NOT_PRODUCTION")
