#!/usr/bin/env python3
"""FC1: one original -> newly computed maps -> new brush plan -> real Egret.

RESEARCH_ONLY. Previous E/F/G32/V44/P4D artistic outputs are NOT inputs.
The imported legacy modules supply only the fixed game swatch parser and real
Egret transport; no archived region, stroke, reference or repair is loaded.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw

import engine001_bpred_s4r1_generic_source_maps as source_maps
import run_engine001_b1r_p3b_engine128_adaptive32 as game_palette
import run_engine001_b1r_p4b7_native_stroke_attribution as native_transport
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as native_caps
import run_engine001_b1r_p4d13_full_original_relaxed_finish as native_render


TASK = "ENGINE001_BPRED_S4R1_FC1_FRESH_FULL_CHAIN_NATIVE_V1"
E0 = "ENGINE001_BPRED001_S4R1_FC1_FRESH_CHAIN_EGRET_PREREG_2026-11-21.md"
E0_GIT_BLOB = "e026b0ef82f04ecb979e5366d5c582162c60052a"
EXPECTED_ORIGINAL_SHA256 = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
GAME_GIT_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
RENDERER_GIT_BLOB = "76d950e0a8911888a9df3b675b866519ecf7bba4"
LOGICAL_WH = (150, 240)
X0 = 155
SCALE = 3
WHITE = 6
ALPHA_GATE = 24
WIDTH_PHASES = (10, 7, 5, 3, 1)
ALLOWED_ARTISTIC_INPUTS = ("original_bytes", "current_game128_palette")


def fresh_logical_source(original_raw: bytes) -> tuple[np.ndarray, dict]:
    decoded = source_maps.decode_original(original_raw)
    if (decoded["sha256"] != EXPECTED_ORIGINAL_SHA256
            or (decoded["width"], decoded["height"]) != (200, 320)):
        raise ValueError("BLOCKED_FC1_NOT_PINNED_KNOWN_DEV_ORIGINAL")
    rgba = decoded["rgba"]
    if np.any(rgba[:, :, 3] != 255):
        raise ValueError("BLOCKED_FC1_ALPHA_NOT_SUPPORTED_IN_FIRST_DEV")
    logical = np.asarray(
        Image.fromarray(rgba).resize(LOGICAL_WH, Image.Resampling.LANCZOS)
    ).copy()
    if logical.shape != (240, 150, 4) or not np.all(logical[:, :, 3] == 255):
        raise ValueError("BLOCKED_FC1_LOGICAL_SOURCE")
    return logical, decoded


def fresh_owner_and_edges(logical: np.ndarray, game: np.ndarray,
                          provenance: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    """Only this original's freshly normalized RGBA is fed to source analysis."""
    with io.BytesIO() as buffer:
        Image.fromarray(logical).save(buffer, format="PNG")
        raw_logical = buffer.getvalue()
    suggestion = source_maps.provisional_game128_owner_maps(
        raw_logical, game, provenance)
    owners = suggestion["provisional_owner_index"]
    if (owners.shape != (240, 150) or np.any(owners < 0)
            or np.any(owners > 127)
            or suggestion["source_owner_status"] != "MISSING"):
        raise ValueError("BLOCKED_FC1_UNVERIFIED_FRESH_OWNER_PROPOSAL")
    rgb_evidence = source_maps.generic_source_maps(logical)
    edges = (suggestion["provisional_owner_edge"] |
             rgb_evidence["source_edge"])
    if not np.any(edges):
        raise ValueError("BLOCKED_FC1_SOURCE_EDGES_EMPTY")
    meta = {
        "logical_png_sha256": hashlib.sha256(raw_logical).hexdigest(),
        "fresh_owner_proposal_version": suggestion["version"],
        "source_analysis_version": rgb_evidence["version"],
        "owner_proposal_status": suggestion["proposal_status"],
        "source_owner_status": suggestion["source_owner_status"],
        "unique_game128_colors": suggestion["counts"]["unique_proposed_game_colors"],
        "mean_lab_nearest_distance": suggestion["lab_nearest_distance_mean"],
        "source_edge_cells": rgb_evidence["counts"]["source_edges"],
        "provisional_owner_edge_cells": suggestion["counts"]["proposed_owner_edges"],
        "fresh_only": True,
    }
    return owners.astype(np.uint8), edges, meta


def make_stroke(owner: int, palette: np.ndarray, width: int,
                a: tuple[float, float], b: tuple[float, float]) -> dict:
    if not 1 <= width <= 10 or owner < 0 or owner > 127:
        raise ValueError("BLOCKED_FC1_STROKE_ARGUMENT")
    if not all(np.isfinite(v) for v in (*a, *b)):
        raise ValueError("BLOCKED_FC1_NONFINITE_COORDINATES")
    if not all(155 <= p[0] <= 305 and 0 <= p[1] <= 240 for p in (a, b)):
        raise ValueError("BLOCKED_FC1_OUTSIDE_NATIVE_ROI")
    r, g, bl = (int(v) for v in palette[owner])
    return {
        "strokeId": "icon-0",
        "colorIndex": int(owner),
        "colorRgb": (r << 16) | (g << 8) | bl,
        "width": int(width),
        "points": [{"x": float(a[0]), "y": float(a[1])},
                   {"x": float(b[0]), "y": float(b[1])}],
    }


def runs(mask_line: np.ndarray):
    row = np.asarray(mask_line, dtype=bool)
    if row.ndim != 1:
        raise ValueError("BLOCKED_FC1_BAD_RUN_AXIS")
    edges = np.flatnonzero(np.diff(np.r_[False, row, False].astype(np.int8)))
    return [(int(x), int(y) - 1) for x, y in zip(edges[::2], edges[1::2])]


def new_adaptive_fill(owners: np.ndarray, palette: np.ndarray) -> tuple[list[dict], dict]:
    """Fresh distance-aware multiwidth geometric planner; no legacy strokes.

    OpenCV line coverage is a MODEL_ONLY residual selection heuristic.
    Coverage and holes are evaluated using actual Egret RGBA later.
    """
    if (owners.shape != (240, 150) or owners.dtype != np.uint8
            or palette.shape != (128, 3) or palette.dtype != np.uint8):
        raise ValueError("BLOCKED_FC1_OWNER_SHAPE")
    nonwhite = [(int(v), int(np.count_nonzero(owners == v)))
                for v in np.unique(owners) if int(v) != WHITE]
    nonwhite.sort(key=lambda pair: (-pair[1], pair[0]))
    strokes: list[dict] = []
    per_owner = {}
    for owner, total in nonwhite:
        target = (owners == owner).astype(np.uint8)
        distances = cv2.distanceTransform(target, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        model_covered = np.zeros(target.shape, dtype=np.uint8)
        count_by_width = Counter()
        for width in WIDTH_PHASES:
            # Alternate horizontal and vertical to paint thin oriented regions.
            axes = ("row", "col") if width % 2 else ("col", "row")
            radius = width / 2.0 + (0.15 if width > 1 else 0.0)
            center_ok = distances >= radius if width > 1 else target.astype(bool)
            stride = max(1, width - 1)
            for axis in axes:
                bound = 240 if axis == "row" else 150
                offset = min(width // 2, bound - 1) if width > 1 else 0
                for pos in range(offset, bound, stride):
                    remaining = (target > 0) & (model_covered == 0) & center_ok
                    line = remaining[pos, :] if axis == "row" else remaining[:, pos]
                    for start, end in runs(line):
                        if width > 1 and end - start + 1 < max(2, width // 2):
                            continue
                        if axis == "row":
                            stroke = make_stroke(
                                owner, palette, width,
                                (X0 + start + 0.125, float(pos)),
                                (X0 + end + 0.375, float(pos)))
                            p0, p1 = (start, pos), (end, pos)
                        else:
                            stroke = make_stroke(
                                owner, palette, width,
                                (float(X0 + pos), start + 0.125),
                                (float(X0 + pos), end + 0.375))
                            p0, p1 = (pos, start), (pos, end)
                        strokes.append(stroke)
                        count_by_width[width] += 1
                        cv2.line(model_covered, p0, p1, 255,
                                 thickness=width, lineType=cv2.LINE_8)
        remaining = int(np.count_nonzero((target > 0) & (model_covered == 0)))
        per_owner[str(owner)] = {
            "source_pixels": total,
            "strokes": sum(count_by_width.values()),
            "widths": dict(sorted(count_by_width.items())),
            "model_only_remaining_cells": remaining,
        }
    return renumber(strokes), per_owner


def new_source_outline(logical: np.ndarray, owners: np.ndarray,
                       palette: np.ndarray) -> tuple[list[dict], np.ndarray]:
    """No historic contours or face/hand ROIs; edges only from this RGB+owner."""
    if logical.shape != (240, 150, 4) or owners.shape != (240, 150):
        raise ValueError("BLOCKED_FC1_OUTLINE_SHAPE")
    gray = cv2.cvtColor(logical[:, :, :3], cv2.COLOR_RGB2GRAY)
    rgb_edges = cv2.Canny(gray, 70, 140) > 0
    adjacency = np.zeros(owners.shape, dtype=np.uint8)
    neq = owners[:, :-1] != owners[:, 1:]
    adjacency[:, :-1] |= neq
    adjacency[:, 1:] |= neq
    neq = owners[:-1] != owners[1:]
    adjacency[:-1, :] |= neq
    adjacency[1:, :] |= neq
    near = cv2.dilate(adjacency, np.ones((3, 3), np.uint8)) > 0
    outline_mask = (rgb_edges & near).astype(np.uint8)
    present = sorted(int(v) for v in np.unique(owners) if int(v) != WHITE)
    if not present:
        return [], outline_mask
    darkest = min(present, key=lambda i: (int(palette[i].sum()), i))
    contours, _ = cv2.findContours(
        outline_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    result = []
    contours = sorted(contours, key=lambda c: (
        -cv2.arcLength(c, False), cv2.boundingRect(c)[1], cv2.boundingRect(c)[0]))
    for contour in contours:
        if cv2.arcLength(contour, False) < 3:
            continue
        coords = cv2.approxPolyDP(contour, 0.45, False).reshape(-1, 2)
        for begin in range(0, max(0, len(coords) - 1), 127):
            piece = coords[begin:begin + 128]
            if len(piece) < 2:
                continue
            pts = [{"x": float(X0 + x), "y": float(y)} for x, y in piece]
            stroke = make_stroke(
                darkest, palette, 1,
                (pts[0]["x"], pts[0]["y"]), (pts[-1]["x"], pts[-1]["y"]))
            stroke["points"] = pts
            result.append(stroke)
    return renumber(result), outline_mask


def renumber(strokes: list[dict]) -> list[dict]:
    return [{**s, "strokeId": "icon-%d" % i} for i, s in enumerate(strokes)]


def native_missing_cells(native: np.ndarray, owners: np.ndarray) -> np.ndarray:
    if (native.shape != (720, 1380, 4) or native.dtype != np.uint8
            or owners.shape != (240, 150)):
        raise ValueError("BLOCKED_FC1_NATIVE_MISSING_SHAPE")
    roi = native[:, X0 * SCALE:(X0 + 150) * SCALE]
    physical_ink = roi[:, :, 3] >= ALPHA_GATE
    counts = physical_ink.reshape(240, SCALE, 150, SCALE).sum(axis=(1, 3))
    return (owners != WHITE) & (counts == 0)


def new_native_feedback_repair(missing: np.ndarray, owners: np.ndarray,
                               palette: np.ndarray) -> list[dict]:
    if missing.shape != (240, 150) or owners.shape != missing.shape:
        raise ValueError("BLOCKED_FC1_FEEDBACK_SHAPE")
    repair = []
    for y in range(240):
        for start, end in runs(missing[y]):
            x = start
            while x <= end:
                owner = int(owners[y, x])
                finish = x
                while finish < end and owners[y, finish + 1] == owner:
                    finish += 1
                if owner != WHITE:
                    repair.append(make_stroke(
                        owner, palette, 1,
                        (X0 + x + 0.125, float(y)),
                        (X0 + finish + 0.375, float(y))))
                x = finish + 1
    return renumber(repair)


def native_paint_rgb(native: np.ndarray) -> Image.Image:
    if native.shape != (720, 1380, 4):
        raise ValueError("BLOCKED_FC1_NOT_REAL_BOARD_SHAPE")
    roi = Image.fromarray(
        native[:, X0 * SCALE:(X0 + 150) * SCALE], "RGBA")
    return Image.alpha_composite(Image.new("RGBA", roi.size, "white"), roi).convert("RGB")


def native_diagnostics(native: np.ndarray, owners: np.ndarray,
                       palette: np.ndarray, original_logical: np.ndarray) -> dict:
    ink = native[:, X0*SCALE:(X0+150)*SCALE, 3] >= ALPHA_GATE
    has = ink.reshape(240, SCALE, 150, SCALE).any(axis=(1, 3))
    target = owners != WHITE
    final_logical = np.asarray(native_paint_rgb(native).resize(
        LOGICAL_WH, Image.Resampling.BOX), dtype=np.uint8)
    quant = palette[owners]
    return {
        "target_nonwhite_cells": int(target.sum()),
        "any_native_ink_target_cells": int(np.count_nonzero(has & target)),
        "no_native_ink_target_cells": int(np.count_nonzero(~has & target)),
        "source_white_cells_with_native_ink": int(np.count_nonzero(has & (owners == WHITE))),
        "native_preview_vs_current_game128_mean_abs_rgb": round(
            float(np.mean(np.abs(final_logical.astype(np.int16) -
                                 quant.astype(np.int16)))), 4),
        "native_preview_vs_original_RGB_mean_abs_rgb": round(
            float(np.mean(np.abs(final_logical.astype(np.int16) -
                                 original_logical[:, :, :3].astype(np.int16)))), 4),
        "native_preview_rgb_comparison_is_diagnostic_not_accepted": True,
    }


def save_review(output: Path, original: np.ndarray, owners: np.ndarray,
                palette: np.ndarray, native_fill: np.ndarray,
                native_final: np.ndarray, edges: np.ndarray) -> None:
    rgb = Image.fromarray(original[:, :, :3])
    Image.fromarray(palette[owners]).save(output / "02_FRESH_GAME128_TARGET.png")
    Image.fromarray(owners, "L").save(output / "03_FRESH_OWNER_INDEX.png")
    Image.fromarray((edges.astype(np.uint8) * 255), "L").save(
        output / "04_FRESH_SOURCE_EDGES.png")
    fill = native_paint_rgb(native_fill)
    final = native_paint_rgb(native_final)
    fill.save(output / "05_ACTUAL_EGRET_FILL.png")
    final.save(output / "06_ACTUAL_EGRET_FINAL.png")
    images = [
        rgb.resize((450, 720), Image.Resampling.NEAREST),
        Image.fromarray(palette[owners]).resize((450, 720), Image.Resampling.NEAREST),
        fill, final,
    ]
    sheet = Image.new("RGB", (1800, 768), "white")
    drawer = ImageDraw.Draw(sheet)
    for i, (name, pic) in enumerate(zip(
            ("ORIGINAL RGB", "FRESH GAME128 TARGET",
             "REAL EGRET FILL", "REAL EGRET FINAL"), images)):
        sheet.paste(pic, (i * 450, 48))
        drawer.text((i * 450 + 8, 12), name, fill=(10, 10, 10))
    sheet.save(output / "00_VISUAL_REVIEW_FRESH_CHAIN.png")


def run(workspace: Path, source: Path, engine: Path, renderer: Path,
        output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_FC1_OUTPUT_EXISTS")
    frozen = subprocess.check_output(
        ["git", "show", "HEAD:AutoDraw_Stage20/docs/" + E0], cwd=workspace)
    if source_maps.git_blob_sha1(frozen) != E0_GIT_BLOB:
        raise ValueError("BLOCKED_FC1_FROZEN_E0_DRIFT")
    raw = source.read_bytes()
    logical, origin = fresh_logical_source(raw)
    if (game_palette.git_blob_sha(engine.read_bytes()) != GAME_GIT_BLOB
            or game_palette.git_blob_sha(renderer.read_bytes()) != RENDERER_GIT_BLOB):
        raise ValueError("BLOCKED_FC1_NATIVE_INFRA_PROVENANCE")
    game, provenance = game_palette.read_engine_palette(engine)
    owners, edges, meta = fresh_owner_and_edges(logical, game, provenance)
    fill, owner_plan = new_adaptive_fill(owners, game)
    outline, outline_mask = new_source_outline(logical, owners, game)
    if not fill:
        raise ValueError("BLOCKED_FC1_EMPTY_FRESH_PLAN")
    output.mkdir(parents=True, exist_ok=False)
    (output / "01_FRESH_LOGICAL_ORIGINAL.png").write_bytes(
        _encode_png(logical))
    (output / "07_FRESH_CONTOUR_MASK.png").write_bytes(
        _encode_png(outline_mask.astype(np.uint8) * 255))
    (output / "FILL_PLAN_FROM_ORIGINAL.json").write_text(
        json.dumps(fill, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf8")
    (output / "OUTLINE_PLAN_FROM_ORIGINAL.json").write_text(
        json.dumps(outline, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf8")
    with native_caps.patched_test_renderer(renderer):
        with native_transport.native_egret_session(workspace) as driver:
            driver.set_script_timeout(900)
            browser = {
                "name": driver.capabilities.get("browserName"),
                "version": driver.capabilities.get("browserVersion"),
            }
            if not str(browser["version"]).startswith("159."):
                raise ValueError("BLOCKED_FC1_WRONG_FIREFOX")
            blank, blank_info = native_render.render(
                driver, output, "FC1_BLANK", [])
            if np.any(blank[:, :, 3]):
                raise ValueError("BLOCKED_FC1_NOT_BLANK_NATIVE")
            painted, fill_info = native_render.render(
                driver, output, "FC1_ALL_FRESH_FILL", fill)
            missing = native_missing_cells(painted, owners)
            repair = new_native_feedback_repair(missing, owners, game)
            final_plan = renumber(fill + repair + outline)
            (output / "FULL_FRESH_CHAIN_STROKES.json").write_text(
                json.dumps(final_plan, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf8")
            final_rgba, final_info = native_render.render(
                driver, output, "FC1_FINAL_FRESH_CHAIN", final_plan)
    if game_palette.git_blob_sha(renderer.read_bytes()) != RENDERER_GIT_BLOB:
        raise ValueError("BLOCKED_FC1_NATIVE_RENDERER_NOT_RESTORED")
    save_review(output, logical, owners, game, painted, final_rgba, edges)
    width_stats = dict(sorted(Counter(
        str(s["width"]) for s in final_plan).items()))
    report = {
        "task": TASK,
        "frozen_e0_git_blob": E0_GIT_BLOB,
        "run_input_provenance": {
            "original_path": source.as_posix(),
            "original_sha256": hashlib.sha256(raw).hexdigest(),
            "original_git_blob_sha1": origin["git_blob_sha1"],
            "original_full_wh": [origin["width"], origin["height"]],
            "working_wh": list(LOGICAL_WH),
            "game_git_blob": GAME_GIT_BLOB,
            "renderer_git_blob": RENDERER_GIT_BLOB,
            "palette_sha256": hashlib.sha256(game.tobytes()).hexdigest(),
            "only_current_image_as_artistic_source": True,
            "old_e_f_g32_v44_p4d_artistic_data_used": False,
            "allowed_artistic_inputs": list(ALLOWED_ARTISTIC_INPUTS),
            "source_generated_in_same_run": True,
            "legacy_modules_used_for_infrastructure_only": True,
        },
        "fresh_map": meta,
        "native_browser": browser,
        "native_scenes": ["blank", "current_run_fill", "current_run_fill_repair_outline"],
        "native_blank_sha256": blank_info["source_sha256"],
        "native_fill_sha256": fill_info["source_sha256"],
        "native_final_sha256": final_info["source_sha256"],
        "native_blank_alpha0": True,
        "source_only_owner_diagnostic": "PROVISIONAL_LAB_NEAREST_NOT_SOURCE_OWNER",
        "plan": {
            "fill_strokes": len(fill),
            "fresh_feedback_width1_repair_strokes": len(repair),
            "source_derived_outline_strokes": len(outline),
            "final_strokes": len(final_plan),
            "width_counts": width_stats,
            "owners": owner_plan,
            "model_footprint_used_only_for_candidate_planning": True,
        },
        "fill_diagnostics": native_diagnostics(painted, owners, game, logical),
        "final_diagnostics": native_diagnostics(final_rgba, owners, game, logical),
        "status": "RESEARCH_ONLY_VISUAL_REVIEW_REQUIRED",
        "strict_S4": "BLOCKED",
        "formal_S5_S6": "NOT_RUN",
        "game_E4_E5_CHALK": "NOT_RUN",
        "heldout8_BLIND120_second50": "SEALED",
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
    }
    report["raw_files_sha256"] = {
        str(path.relative_to(output)).replace("\\", "/"):
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.rglob("*")) if path.is_file()
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf8")
    return report


def _encode_png(data: np.ndarray) -> bytes:
    bio = io.BytesIO()
    Image.fromarray(data).save(bio, format="PNG")
    return bio.getvalue()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.workspace, arguments.source,
                         arguments.engine, arguments.renderer,
                         arguments.output), ensure_ascii=False, indent=2))
