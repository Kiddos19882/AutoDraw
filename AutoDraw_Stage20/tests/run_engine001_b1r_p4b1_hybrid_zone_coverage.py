#!/usr/bin/env python3
"""ENGINE-001 B1-R-P4B1: original-only oriented vs contour-hybrid zone coverage.

All model footprints are proposal/ranking ONLY. Actual E3 coverage/leakage
comes exclusively from game_renderer_reference.js Egret BoardPane native RGBA.
No G32/P4c1/V44 old color/contour as inputs, no game E4 or exact CHALK.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import native_batch

EXPERIMENT = "ENGINE001_B1R_P4B1_HYBRID_OWNER_COVERAGE_V1"
RENDERER_BLOB = "76d950e0a8911888a9df3b675b866519ecf7bba4"
SOURCE_KEYS = ("C_096_D_BORDER", "C_096_D_COMPONENT24",
               "C_192_D_BORDER", "C_192_D_COMPONENT24")
NATIVE_SOURCE_KEY = "C_192_D_COMPONENT24"
METHODS = ("E_SOBEL90", "F_SOBEL90_LAB12")
STRATEGIES = ("A_ORIENTED", "B_CONTOUR_HYBRID")
WIDTHS = tuple(range(10, 0, -1))
DIRECTIONS = {"HORIZONTAL": (1, 0), "DIAG_DOWN": (1, 1),
              "VERTICAL": (0, 1), "DIAG_UP": (-1, 1)}
CENTER_MARGIN = 0.3
TRACK_SPACING_FACTOR = 0.8
RING_STEP_FACTOR = 0.7
MAX_STROKES = 250
MAX_VERTICES = 500
MAX_POINTS_PER_STROKE = 128
MIN_COMPONENT_SIZE = 256
LOGICAL_SHAPE = (240, 150)
BOARD_SHAPE = (240, 460)
BACKING_SHAPE = (720, 1380, 4)
ROI_X0 = 155
BACKING_SCALE = 3
ALPHA_GATES = (24, 128)
LEAKAGE_MAX_LOGICAL = 3.0
NATIVE_COMPONENT_COVERAGE_GATE = .99


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _valid_index(index: np.ndarray, selected: np.ndarray):
    if (not isinstance(index, np.ndarray) or index.shape != LOGICAL_SHAPE or
            index.dtype != np.uint8 or
            selected.shape != (32,) or
            not np.issubdtype(selected.dtype, np.integer) or
            len(set(int(x) for x in selected)) != 32 or
            np.any(selected < 0) or np.any(selected >= 128) or
            int(p3b.ENGINE_WHITE_INDEX) not in selected or
            not set(np.unique(index)).issubset(set(selected))):
        raise ValueError("BLOCKED_P4B1_INDEX_OR_PALETTE")


def choose_common_source_owner(e: np.ndarray, f: np.ndarray,
                               selected: np.ndarray):
    """Largest current-run 4-connected E/F intersection; stable tie-breaks."""
    _valid_index(e, selected)
    _valid_index(f, selected)
    possibilities = []
    for owner in sorted(set(int(v) for v in selected)):
        if owner == int(p3b.ENGINE_WHITE_INDEX):
            continue
        both = ((e == owner) & (f == owner)).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(
            both, connectivity=4)
        for part in range(1, n):
            area = int(stats[part, cv2.CC_STAT_AREA])
            if area < MIN_COMPONENT_SIZE:
                continue
            y, x = np.argwhere(labels == part)[0]
            possibilities.append((-area, owner, int(y), int(x)))
    if not possibilities:
        raise ValueError("BLOCKED_P4B1_NO_COMMON_NONWHITE_REGION")
    neg_area, owner, ay, ax = min(possibilities)
    areas = {}
    masks = {}
    for name, index in zip(METHODS, (e, f)):
        n, labels, stats, _ = cv2.connectedComponentsWithStats(
            (index == owner).astype(np.uint8), connectivity=4)
        label = int(labels[ay, ax])
        if label == 0:
            raise ValueError("BLOCKED_P4B1_NO_SOURCE_OWNER_AT_COMMON_ANCHOR")
        mask = labels == label
        areas[name] = int(stats[label, cv2.CC_STAT_AREA])
        masks[name] = mask
    return {
        "engine_index": owner, "common_intersection_pixels": -neg_area,
        "anchor_yx": [ay, ax], "component_area_E_F": areas
    }, masks


def _model_candidate(points: list[tuple[float, float]], width: int,
                     component: np.ndarray, full_owner: np.ndarray,
                     outside: np.ndarray, kind: str, direction: str):
    """MODEL_ONLY footprint for candidate gain/safety; NEVER native evidence."""
    if (not 1 <= width <= 10 or len(points) < 2 or
            len(points) > MAX_POINTS_PER_STROKE):
        return None
    coordinates = np.rint(np.asarray(points, dtype=np.float64)).astype(np.int32)
    if (np.any(coordinates[:, 0] < 0) or
            np.any(coordinates[:, 0] >= 150) or
            np.any(coordinates[:, 1] < 0) or
            np.any(coordinates[:, 1] >= 240)):
        return None
    left = max(0, int(coordinates[:, 0].min()) - width - 2)
    right = min(150, int(coordinates[:, 0].max()) + width + 3)
    top = max(0, int(coordinates[:, 1].min()) - width - 2)
    bottom = min(240, int(coordinates[:, 1].max()) + width + 3)
    xy = coordinates.copy()
    xy[:, 0] -= left
    xy[:, 1] -= top
    brush = np.zeros((bottom-top, right-left), dtype=np.uint8)
    cv2.polylines(brush, [xy.reshape(-1, 1, 2)], False, 255,
                  thickness=width, lineType=cv2.LINE_8)
    ys, xs = np.where(brush != 0)
    yy, xx = ys+top, xs+left
    if len(xx) == 0:
        return None
    if np.any((~full_owner[yy, xx]) & (outside[yy, xx] > LEAKAGE_MAX_LOGICAL)):
        return None
    owner_pixels = component[yy, xx]
    flat = np.unique((yy[owner_pixels]*150 + xx[owner_pixels]).astype(np.int32))
    if not len(flat):
        return None
    return {
        "points": points, "width": int(width), "kind": kind,
        "direction": direction, "owner_flat": flat,
        "vertices": len(points), "model_ink_pixels": int(len(xx)),
        "model_nonowner_any": int(np.count_nonzero(~full_owner[yy, xx])),
    }


def _source_centerline(points: list[tuple[float, float]],
                       component: np.ndarray) -> bool:
    pts = np.rint(np.asarray(points)).astype(np.int32)
    line = np.zeros(LOGICAL_SHAPE, np.uint8)
    cv2.polylines(line, [pts.reshape(-1, 1, 2)], False, 255, 1, cv2.LINE_8)
    return bool(line.any()) and bool(np.all(component[line != 0]))


def _candidate_oriented(component: np.ndarray, full_owner: np.ndarray,
                        outside: np.ndarray, width: int):
    padded = np.pad(component.astype(np.uint8), 1)
    distance = cv2.distanceTransform(
        padded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
    centers = distance >= (width/2 + CENTER_MARGIN)
    coords = np.argwhere(centers)
    spacing = max(1, int(round(width * TRACK_SPACING_FACTOR)))
    options = []
    for name, (dx, dy) in DIRECTIONS.items():
        lines = defaultdict(list)
        for y, x in coords:
            x, y = int(x), int(y)
            lateral = dy*x - dx*y
            if lateral % spacing == 0:
                lines[lateral].append((x, y))
        for lateral in sorted(lines):
            ordered = sorted(lines[lateral],
                             key=lambda p: (dx*p[0]+dy*p[1], p[1], p[0]))
            run = []
            for xy in ordered:
                if run and (xy[0]-run[-1][0], xy[1]-run[-1][1]) != (dx, dy):
                    if len(run) >= 2:
                        points = [tuple(map(float, (run[0][0], run[0][1]))),
                                  tuple(map(float, (run[-1][0], run[-1][1])))]
                        if _source_centerline(points, component):
                            c = _model_candidate(points, width, component,
                                                 full_owner, outside,
                                                 "oriented", name)
                            if c:
                                options.append(c)
                    run = []
                run.append(xy)
            if len(run) >= 2:
                points = [(float(run[0][0]), float(run[0][1])),
                          (float(run[-1][0]), float(run[-1][1]))]
                if _source_centerline(points, component):
                    c = _model_candidate(points, width, component,
                                         full_owner, outside, "oriented", name)
                    if c:
                        options.append(c)
    return options


def _candidate_rings(component: np.ndarray, full_owner: np.ndarray,
                     outside: np.ndarray, width: int):
    dt = cv2.distanceTransform(
        np.pad(component.astype(np.uint8), 1),
        cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
    level, step = width/2+ CENTER_MARGIN, max(1.0, width * RING_STEP_FACTOR)
    output = []
    while level <= float(dt.max(initial=0)) + 1e-9:
        region = (dt >= level).astype(np.uint8)
        contours, _ = cv2.findContours(region, cv2.RETR_LIST,
                                       cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=lambda c: (
            cv2.boundingRect(c)[1], cv2.boundingRect(c)[0],
            cv2.boundingRect(c)[2], cv2.boundingRect(c)[3]))
        for contour in contours:
            if len(contour) == 0:
                continue
            simplified = cv2.approxPolyDP(
                contour, max(.35, width*.07), True).reshape(-1, 2)
            points = [tuple(map(float, p)) for p in simplified.tolist()]
            if len(points) == 1:
                x, y = points[0]
                paths = [[(x + .125, y), (x + .375, y)]]
            elif len(points) == 2:
                paths = [points]
            else:
                closed = points + [points[0]]
                paths = [closed[i:i+MAX_POINTS_PER_STROKE]
                         for i in range(0, len(closed)-1,
                                        MAX_POINTS_PER_STROKE-1)]
            for part in paths:
                if len(part) < 2 or not _source_centerline(part, component):
                    continue
                c = _model_candidate(part, width, component, full_owner,
                                     outside, "contour_ring", "RING")
                if c:
                    output.append(c)
        level += step
    return output


def plan_component(component: np.ndarray, full_owner: np.ndarray, owner: int,
                   game128: np.ndarray, strategy: str):
    if (component.shape != LOGICAL_SHAPE or component.dtype != np.bool_ or
            full_owner.shape != LOGICAL_SHAPE or full_owner.dtype != np.bool_ or
            not np.any(component) or np.any(component & ~full_owner) or
            game128.shape != (128, 3) or game128.dtype != np.uint8 or
            not 0 <= owner < 128 or
            strategy not in STRATEGIES):
        raise ValueError("BLOCKED_P4B1_PLAN_INPUT")
    outside = cv2.distanceTransform(
        (~full_owner).astype(np.uint8), cv2.DIST_L2,
        cv2.DIST_MASK_PRECISE)
    uncovered = component.copy().reshape(-1)
    source_area = int(component.sum())
    strokes = []
    vertices = 0
    counts = Counter()
    candidates_count = 0
    truncated = False
    for width in WIDTHS:
        if strategy == "B_CONTOUR_HYBRID" and width >= 3:
            candidates = _candidate_rings(component, full_owner, outside, width)
        else:
            candidates = _candidate_oriented(component, full_owner, outside,
                                             width)
        candidates_count += len(candidates)
        # Per-stage immutable candidates, each dynamically rescored on uncovered.
        heap = []
        for i, candidate in enumerate(candidates):
            gain = int(np.count_nonzero(uncovered[candidate["owner_flat"]]))
            if gain:
                heapq.heappush(heap, (-gain/candidate["vertices"], -gain,
                                      candidate["vertices"], i, gain))
        while heap:
            _, _, _, idx, previous = heapq.heappop(heap)
            item = candidates[idx]
            gain = int(np.count_nonzero(uncovered[item["owner_flat"]]))
            if gain != previous:
                if gain:
                    heapq.heappush(heap, (-gain/item["vertices"], -gain,
                                          item["vertices"], idx, gain))
                continue
            if not gain:
                continue
            if len(strokes) >= MAX_STROKES or vertices+item["vertices"] > MAX_VERTICES:
                truncated = True
                # Do not skip large ring and search smaller ones to cheat the
                # fixed budget/ordering; preserve the first budget blocker.
                break
            rgb = game128[int(owner)]
            stroke = {
                "strokeId": "icon-%d" % len(strokes),
                "width": int(width), "colorIndex": int(owner),
                "colorRgb": (int(rgb[0]) << 16) | (int(rgb[1]) << 8) |
                            int(rgb[2]),
                "points": [{"x": float(x)+ROI_X0, "y": float(y)}
                           for x, y in item["points"]],
                "route_kind": item["kind"],
                "orientation": item["direction"],
                "model_new_owner_pixels_NOT_NATIVE": gain,
            }
            strokes.append(stroke)
            uncovered[item["owner_flat"]] = False
            vertices += item["vertices"]
            counts[str(width)] += 1
        if truncated:
            break
    if len(strokes) > MAX_STROKES or vertices > MAX_VERTICES:
        raise AssertionError("BLOCKED_P4B1_RESOURCE_CONSTRAINT")
    return strokes, {
        "strategy": strategy, "owner_engine_index": int(owner),
        "source_component_logical_pixels": source_area,
        "model_remaining_pixels_NOT_NATIVE": int(uncovered.sum()),
        "model_coverage_NOT_NATIVE": 1 - float(uncovered.sum())/source_area,
        "strokes_count": len(strokes),
        "synthetic_vertices_NOT_CHALK": vertices,
        "fixed_stroke_cap": MAX_STROKES,
        "fixed_vertex_cap": MAX_VERTICES,
        "budget_limited": truncated,
        "candidate_count_MODEL_ONLY": candidates_count,
        "width_histogram": {str(w): counts[str(w)] for w in WIDTHS},
        "P3D_source_owner_unchanged": True,
    }


def _board_backing(mask: np.ndarray):
    if mask.shape != LOGICAL_SHAPE or mask.dtype != np.bool_:
        raise ValueError("BLOCKED_P4B1_WRONG_LOGICAL_MASK")
    board = np.zeros(BOARD_SHAPE, dtype=bool)
    board[:, ROI_X0:ROI_X0+150] = mask
    return np.repeat(np.repeat(board, BACKING_SCALE, axis=0),
                     BACKING_SCALE, axis=1)


def native_metrics(rgba: np.ndarray, blank: np.ndarray,
                   component: np.ndarray, full_owner: np.ndarray):
    if (rgba.shape != BACKING_SHAPE or rgba.dtype != np.uint8 or
            blank.shape != BACKING_SHAPE or blank.dtype != np.uint8):
        raise ValueError("BLOCKED_P4B1_NATIVE_RGBA_SHAPE")
    target = _board_backing(component)
    whole = _board_backing(full_owner)
    if not target.any() or not whole.any():
        raise ValueError("BLOCKED_P4B1_EMPTY_NATIVE_OWNER")
    outside = cv2.distanceTransform(
        (~whole).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    result = {}
    for alpha in ALPHA_GATES:
        ink = rgba[:, :, 3] >= alpha
        owner = ink & target
        far = ink & ~whole & (outside > LEAKAGE_MAX_LOGICAL * BACKING_SCALE)
        result[str(alpha)] = {
            "native_nonzero_ink_backing_pixels": int(ink.sum()),
            "native_selected_component_owner_backing_pixels": int(owner.sum()),
            "native_selected_component_total_backing_pixels": int(target.sum()),
            "native_component_coverage": float(owner.sum()/target.sum()),
            "native_full_color_nonowner_backing_pixels": int((ink & ~whole).sum()),
            "native_beyond3logicalpx_other_color_pixels": int(far.sum()),
        }
    return result, int(np.count_nonzero(blank[:, :, 3]))


def preview_plan(component: np.ndarray, strokes: list[dict], output: Path):
    # Source/model visualization explicitly NOT actual Egret footprint.
    image = np.zeros((240, 150, 3), np.uint8)
    image[:] = (239, 239, 239)
    image[component] = (172, 187, 190)
    for s in strokes:
        pts = np.asarray([[int(round(p["x"]-ROI_X0)),
                           int(round(p["y"]))] for p in s["points"]],
                         dtype=np.int32)
        width = s["width"]
        color = (42, int(180-10*width), int(40+18*width))
        cv2.polylines(image, [pts.reshape(-1, 1, 2)], False,
                      color, 1, cv2.LINE_8)
    im = Image.fromarray(image).resize((450, 720), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (450, 766), "white")
    canvas.paste(im, (0, 46))
    ImageDraw.Draw(canvas).text(
        (8, 9), "SOURCE MODEL ONLY - not actual native Egret coverage",
        fill=(0, 0, 0))
    canvas.save(output)


def run(workspace: Path, source: Path, engine_js: Path, renderer: Path,
        output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P4B1_OUTPUT_EXISTS")
    check_source(source)
    engine, _ = p3b.read_engine_palette(engine_js)
    if git_blob(renderer.read_bytes()) != RENDERER_BLOB:
        raise ValueError("BLOCKED_P4B1_RENDERER_BLOB")
    output.mkdir(parents=True)
    all_results = {}
    with tempfile.TemporaryDirectory(prefix="engine001-p4b1-original-") as tmp:
        from_source = Path(tmp) / "p3d_fresh"
        base = p3d.run(source, engine_js, from_source)
        if (base["experiment"] != p3d.EXPERIMENT or
                base["original_source_sha256"] != p3b.SOURCE_SHA or
                base["read_frozen_ZIP_as_source"] or
                base["legacy_G32_V44_M1_used_as_source"] or
                not base["P3B_original_recomputed_in_current_run"] or
                set(base["all_results"]) != set(SOURCE_KEYS)):
            raise ValueError("BLOCKED_P4B1_ORIGINAL_SOURCE_PROVENANCE")
        for key in SOURCE_KEYS:
            for method in METHODS:
                item = base["all_results"][key]["methods"][method]
                if item["status"] != (
                        "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED"):
                    raise ValueError("BLOCKED_P4B1_REJECTED_P3D_SOURCE")
        shutil.copyfile(from_source/"00_ORIGINAL_RGB_LOGICAL.png",
                        output/"SOURCE_ORIGINAL_LOGICAL_RGB.png")
        for key in SOURCE_KEYS:
            indices = {}
            palette = np.asarray(base["all_results"][key]["selected_engine_indices"],
                                 dtype=np.int16)
            for method in METHODS:
                name = key+"_"+method+"_ENGINE_INDICES.png"
                idx = np.asarray(Image.open(from_source/name), np.uint8).copy()
                _valid_index(idx, palette)
                indices[method] = idx
            info, components = choose_common_source_owner(
                indices[METHODS[0]], indices[METHODS[1]], palette)
            owner = info["engine_index"]
            all_results[key] = {"source_common_owner": info, "methods": {}}
            for method in METHODS:
                component = components[method]
                full_owner = (indices[method] == owner)
                prefix = key+"_"+method
                if key == NATIVE_SOURCE_KEY:
                    Image.fromarray(indices[method]).save(
                        output/(prefix+"_SOURCE_ENGINE_INDICES.png"))
                    Image.fromarray(engine[indices[method]]).save(
                        output/(prefix+"_SOURCE_RGB.png"))
                    Image.fromarray(component.astype(np.uint8)*255).save(
                        output/(prefix+"_SELECTED_COMPONENT_MASK.png"))
                pl = {}
                for strategy in STRATEGIES:
                    strokes, diag = plan_component(component, full_owner,
                                                    owner, engine, strategy)
                    stem = prefix+"_"+strategy
                    if key == NATIVE_SOURCE_KEY:
                        preview_plan(component, strokes,
                                     output/("MODEL_"+stem+"_PREVIEW.png"))
                        (output/("PATHS_"+stem+".json")).write_text(
                            json.dumps(strokes, ensure_ascii=False, indent=2,
                                       allow_nan=False)+"\n", encoding="utf8")
                    pl[strategy] = {
                        "model": diag, "native": None, "native_status": "NOT_RUN"
                    }
                all_results[key]["methods"][method] = pl
        native_keys = all_results[NATIVE_SOURCE_KEY]["methods"]
        native_owner = all_results[NATIVE_SOURCE_KEY]["source_common_owner"]["engine_index"]
        for method in METHODS:
            index = np.asarray(Image.open(
                from_source/(NATIVE_SOURCE_KEY+"_"+method+"_ENGINE_INDICES.png")),
                np.uint8).copy()
            full_owner = index == native_owner
            # Same source component anchor; recomputed from original-only E/F.
            _, comps = choose_common_source_owner(
                np.asarray(Image.open(from_source/(
                    NATIVE_SOURCE_KEY+"_"+METHODS[0]+"_ENGINE_INDICES.png")),
                    np.uint8).copy(),
                np.asarray(Image.open(from_source/(
                    NATIVE_SOURCE_KEY+"_"+METHODS[1]+"_ENGINE_INDICES.png")),
                    np.uint8).copy(),
                np.asarray(base["all_results"][NATIVE_SOURCE_KEY]
                           ["selected_engine_indices"], np.int16))
            component = comps[method]
            for strategy in STRATEGIES:
                stem = NATIVE_SOURCE_KEY+"_"+method+"_"+strategy
                paths = json.loads((output/("PATHS_"+stem+".json")).read_text(
                    encoding="utf8"))
                if not paths:
                    raise ValueError("BLOCKED_P4B1_EMPTY_PAINTABLE_COMPONENT")
                # Keep diagnostics outside executable stroke schema.
                strokes = [{
                    k: s[k] for k in ("strokeId", "width", "colorIndex",
                                    "colorRgb", "points")
                } for s in paths]
                scene = output/("NATIVE_"+method+"_"+strategy)
                scene.mkdir()
                native, meta, manifest = native_batch(
                    workspace, "P4B1-"+method+"-"+strategy,
                    strokes, scene,
                    renderer_method="renderP4A2BrushWidths1to10Probe")
                keys = {"composite", "blank", "color-"+str(native_owner)}
                if (set(native) != keys or set(meta) != keys or
                        meta["composite"].get("schema") !=
                        "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
                        meta["composite"].get("renderer") !=
                        "real Egret 5.4.1 BoardPane/WebGLRenderer" or
                        manifest["colors_rendered"] != [native_owner]):
                    raise ValueError("BLOCKED_P4B1_WRONG_GAME_RENDERER")
                if any(a.shape != BACKING_SHAPE or a.dtype != np.uint8
                       for a in native.values()):
                    raise ValueError("BLOCKED_P4B1_NATIVE_WRONG_RGBA")
                metrics, blank_count = native_metrics(
                    native["color-"+str(native_owner)], native["blank"],
                    component, full_owner)
                alpha24 = metrics["24"]
                good = bool(
                    alpha24["native_nonzero_ink_backing_pixels"] > 0 and
                    alpha24["native_component_coverage"] >=
                    NATIVE_COMPONENT_COVERAGE_GATE and
                    alpha24["native_beyond3logicalpx_other_color_pixels"] == 0 and
                    blank_count == 0)
                model = native_keys[method][strategy]["model"]
                native_keys[method][strategy].update({
                    "native_status": "NATIVE_COMPONENT_PASS" if good else
                        ("BUDGET_LIMITED" if model["budget_limited"] else
                         "NATIVE_COMPONENT_QUALITY_FAIL"),
                    "native": {
                        "alpha_masks": metrics,
                        "native_blank_nonzero_alpha_pixels": blank_count,
                        "real_Egret_BoardPane_renderer": True,
                        "native_source_color_index": native_owner,
                        "native_selected_RGB": "#%02X%02X%02X" %
                            tuple(int(a) for a in engine[native_owner]),
                        "scene_diagnostics": meta["composite"].get("sceneDiagnostics"),
                    }
                })
                print("P4B1_NATIVE", method, strategy,
                      native_keys[method][strategy]["native_status"],
                      "coverage", round(alpha24["native_component_coverage"], 5),
                      "far_leakage",
                      alpha24["native_beyond3logicalpx_other_color_pixels"],
                      "strokes", model["strokes_count"],
                      "vertices", model["synthetic_vertices_NOT_CHALK"],
                      flush=True)
    native_count = sum(
        all_results[NATIVE_SOURCE_KEY]["methods"][m][s]["native"] is not None
        for m in METHODS for s in STRATEGIES)
    if native_count != 4:
        raise AssertionError("BLOCKED_P4B1_NATIVE_4_SCENES_MISSING")
    all_pass = all(
        all_results[NATIVE_SOURCE_KEY]["methods"][m][s]["native_status"] ==
        "NATIVE_COMPONENT_PASS" for m in METHODS for s in STRATEGIES)
    hashes = {
        str(p.relative_to(output)).replace("\\", "/"): digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    (output/"README_REVIEW_RU.txt").write_text(
        "ENGINE001 P4B1: original-only, C192 D_COMPONENT24 real Egret/BoardPane\n"
        "A_ORIENTED — прямые линии 0/45/90/135 с адаптивными размерами 10..1.\n"
        "B_CONTOUR_HYBRID — внутренние кольца 10..3, остаток линиями 2/1.\n"
        "SOURCE_*/MODEL_* — лишь исходные карты/предложения, НЕ итог Egret.\n"
        "NATIVE_*/*-composite.png и *-color-*.png — настоящий архивный Egret.\n"
        "Оценка coverage относится только к самой большой общей цветовой области,\n"
        "а не ко всей картинке и не к 32 игровым цветам.\n"
        "Порог 99% и утечка больше 3 логических пикселей фиксированы до запуска.\n"
        "CHALK E4 E5 не измерялись; old G32 V44 history only.\n",
        encoding="utf8")
    hashes["README_REVIEW_RU.txt"] = digest(
        (output/"README_REVIEW_RU.txt").read_bytes())
    report = {
        "experiment": EXPERIMENT,
        "prereg_id": EXPERIMENT,
        "result": "NATIVE_COMPONENT_ALL_4_PASS" if all_pass else
            "NATIVE_COMPONENT_QUALITY_NOT_ALL_PASS",
        "native_4_scenes_captured": True,
        "source_SHA256": p3b.SOURCE_SHA,
        "engine_git_blob_SHA1": p3b.ENGINE_GIT_BLOB_SHA1,
        "renderer_git_blob_SHA1": RENDERER_BLOB,
        "P3D_original_only_recomputed": True,
        "P3D_all8_source_quality_pass": True,
        "P3D_E_F_user_visual_approval": "BOTH_ACCEPTED_DEC038",
        "source_keys": list(SOURCE_KEYS), "methods": list(METHODS),
        "strategy_names": list(STRATEGIES), "widths": list(WIDTHS),
        "native_source_key": NATIVE_SOURCE_KEY,
        "component_selection": "largest_common_4connected_EF_nonwhite",
        "model_footprints_do_NOT_validate_native_coverage": True,
        "legacy_G32_P4c1_V44_as_input": False,
        "original_P3D_frozen_ZIP_as_input": False,
        "actual_game_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN",
        "exact_run_bound_CHALK": None,
        "production_promotion": False,
        "source_results": all_results,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "file_sha256": hashes,
    }
    (output/"report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2,
                   allow_nan=False)+"\n", encoding="utf8")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True, type=Path)
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--engine-js", required=True, type=Path)
    ap.add_argument("--renderer", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    try:
        result = run(args.workspace, args.source, args.engine_js,
                     args.renderer, args.output)
    except Exception as error:
        if not args.output.exists():
            args.output.mkdir(parents=True)
        (args.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({
                "experiment": EXPERIMENT, "status": "BLOCKED",
                "error_type": type(error).__name__,
                "reason": str(error), "github_sha": os.getenv("GITHUB_SHA"),
                "github_run_id": os.getenv("GITHUB_RUN_ID"),
                "native_quality_not_established": True,
                "exact_CHALK": None,
            }, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
        raise
    for key, obj in result["source_results"].items():
        for method, choices in obj["methods"].items():
            for name, item in choices.items():
                print("P4B1_MODEL", key, method, name,
                      "MODEL_ONLY_COVERAGE",
                      round(item["model"]["model_coverage_NOT_NATIVE"], 5),
                      "strokes", item["model"]["strokes_count"],
                      "budget", item["model"]["budget_limited"])
    print("P4B1_RESULT",result["result"],
          "four real source-native Egret scenes; exact CHALK NOT_RUN")
