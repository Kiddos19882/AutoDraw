#!/usr/bin/env python3
"""P4D1: only the order of original B1-R P4D0 fill/outline strokes changes.

Both baseline and interleaved are replayed through the same real archived
Egret 5.4.1 BoardPane/WebGL; no production/game/CHALK modification.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as p4d0
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import read_webgl_result

EXPERIMENT = "ENGINE001_B1R_P4D1_INTERLEAVED_SOURCE_OUTLINE_EGRET_V1"
PREREG = "ENGINE001_B1R_P4D1_INTERLEAVED_FILL_CONTOUR_NATIVE_PREREG_2026-11-19.md"
SOURCE = p4d0.SOURCE
SOURCE_SHA = p4d0.SOURCE_SHA
METHODS = p4d0.METHODS
ARMS = p4d0.ARMS
STAGES = ("BASELINE_FILL_THEN_CONTOUR", "INTERLEAVED_LOCAL")
P4D0_PARENT_BLOB = "cf4f0b0b8a1fef5879067f41901f2806758e81bd"
RENDERER_BLOB = p4d0.RENDERER_BLOB
CANONICAL_FIELDS = ("width", "colorIndex", "colorRgb", "points")


def signature(s: dict) -> str:
    return json.dumps({name:s[name] for name in CANONICAL_FIELDS},
                      sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(",", ":"))


def center(s: dict) -> tuple[float, float]:
    p = s["points"]
    if len(p) < 2 or len(p) > 128:
        raise ValueError("BLOCKED_P4D1_BAD_STROKE_POINT_COUNT")
    points = np.array([[float(a["x"]), float(a["y"])] for a in p], np.float64)
    if (not np.isfinite(points).all() or np.any(points[:, 0] < 0) or
            np.any(points[:, 0] >= 460) or np.any(points[:, 1] < 0) or
            np.any(points[:, 1] >= 240)):
        raise ValueError("BLOCKED_P4D1_BAD_STROKE_COORDINATE")
    return (float(points[:, 0].mean()), float(points[:, 1].mean()))


def interleave_nearest_fill(paint: list[dict], contour: list[dict]):
    """Preserve every stroke and paint sequence; insert outline before nearest fill.

    Euclidean nearest mean of ORIGINAL native board control points.
    Deterministic tie: earliest paint index; same-slot outline source order.
    """
    if not paint or not contour:
        raise ValueError("BLOCKED_P4D1_EMPTY_PAINT_OR_CONTOUR")
    xy = np.asarray([center(s) for s in paint], np.float64)
    insertion = [[] for _ in paint]
    anchors = []
    for j, stroke in enumerate(contour):
        x, y = center(stroke)
        squared = np.square(xy[:, 0]-x) + np.square(xy[:, 1]-y)
        nearest = int(np.argmin(squared))
        insertion[nearest].append((j, stroke))
        anchors.append(nearest)
    source = []
    kinds = []
    for i, fill in enumerate(paint):
        for _, outline in insertion[i]:
            source.append(outline)
            kinds.append("contour")
        source.append(fill)
        kinds.append("paint")
    result = p4c0.renumber(source)
    if (len(result) != len(paint)+len(contour) or
            [signature(s) for s, k in zip(result, kinds) if k == "paint"] !=
            [signature(s) for s in paint] or
            Counter(signature(s) for s in result) !=
            Counter(signature(s) for s in paint+contour)):
        raise ValueError("BLOCKED_P4D1_STROKE_IDENTITY_OR_PAINT_ORDER")
    transitions = sum(a != b for a, b in zip(kinds, kinds[1:]))
    if (kinds[-1] != "paint" or transitions < 2 or
            len(set(anchors)) < 2 and len(paint) >= 4 and len(contour) >= 2):
        raise ValueError("BLOCKED_P4D1_NO_MEANINGFUL_INTERLEAVING")
    trace = {
        "stroke_counts_identical": True,
        "source_paint_order_identical": True,
        "only_order_changed": True,
        "paint_strokes": len(paint),
        "contour_strokes": len(contour),
        "unique_paint_anchor_slots": len(set(anchors)),
        "first_paint_anchor": min(anchors),
        "last_paint_anchor": max(anchors),
        "contour_paint_transitions": transitions,
        "pre_paint_contours": len(anchors),
        "anchor_method": "nearest Euclidean mean of original stroke points",
        "paint_order": "same exact P4D0 per-arm sequence",
        "all_strokes_retained": True,
    }
    return result, trace


def write_review(folder: Path, original: np.ndarray, source: np.ndarray,
                 baseline: Image.Image, interleaved: Image.Image):
    items = [
        ("ORIGINAL RGB", Image.fromarray(original).resize((450,720),Image.Resampling.NEAREST)),
        ("SOURCE B1-R E/F", Image.fromarray(source).resize((450,720),Image.Resampling.NEAREST)),
        ("EGRET FILL THEN OUTLINE", baseline),
        ("EGRET INTERLEAVED", interleaved),
    ]
    out = Image.new("RGB", (1800, 770), (250,250,250))
    draw = ImageDraw.Draw(out)
    for i, (title, img) in enumerate(items):
        out.paste(img, (i*450, 45))
        draw.text((i*450+9, 18), title, fill=(20,20,20))
    out.save(folder/"COMPARE_SOURCE_BASELINE_INTERLEAVED.png")


def run(workspace: Path, source: Path, engine_js: Path,
        renderer: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P4D1_OUTPUT_EXISTS")
    check_source(source)
    if p4b1.git_blob(renderer.read_bytes()) != RENDERER_BLOB:
        raise ValueError("BLOCKED_P4D1_RENDERER_DRIFT")
    if p4b1.git_blob(Path(p4d0.__file__).read_bytes()) != P4D0_PARENT_BLOB:
        raise ValueError("BLOCKED_P4D1_P4D0_PARENT_DRIFT")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4D1_NO_PREREG")
    game, _ = p3b.read_engine_palette(engine_js)
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "ENGINE-001 B1-R P4D1: настоящие native Egret 5.4.1 WebGL PNG.\n"
        "Сравниваются ОДНИ И ТЕ ЖЕ strokes/colors/width/points: сначала заливка и затем весь контур "
        "против попеременных местных штрихов контура и заливки.\n"
        "На каждую карту E/F и два способа заливки имеются по две full-stage картинки.\n"
        "Чистые значения составного покрытия/цвета не заменяют per-owner safety.\n"
        "NOT_PRODUCTION. E4/E5/точный CHALK: NOT_RUN.\n", "utf8")

    results = {}
    work = []
    with tempfile.TemporaryDirectory(prefix="engine001-p4d1-original-") as tmp:
        fresh = Path(tmp)/"fresh_p3d"
        parent = p3d.run(source, engine_js, fresh)
        if (parent["experiment"] != p3d.EXPERIMENT or
                parent["original_source_sha256"] != SOURCE_SHA or
                not parent["P3B_original_recomputed_in_current_run"] or
                parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D1_NOT_ORIGINAL_RECOMPUTED")
        original = np.asarray(Image.open(fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"), np.uint8)
        Image.fromarray(original).save(output/"ORIGINAL_RGB_LOGICAL.png")

        for method in METHODS:
            sub = output/method
            sub.mkdir()
            index = np.asarray(Image.open(fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),
                               dtype=np.uint8).copy()
            selected = parent["all_results"][SOURCE]["selected_engine_indices"]
            p4c0.validate_source(index, game, selected)
            if (parent["all_results"][SOURCE]["methods"][method]["status"] !=
                    "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED"):
                raise ValueError("BLOCKED_P4D1_SOURCE_NOT_APPROVED")
            Image.fromarray(index).save(sub/"SOURCE_ENGINE_INDICES.png")
            rgb = game[index]
            Image.fromarray(rgb).save(sub/"SOURCE_GAME32_RGB.png")
            contour, mask, _ = p4c0.source_joint_outline(index, original, game)
            Image.fromarray(mask.astype(np.uint8)*255).save(sub/"NEW_SOURCE_CONTOUR_MASK.png")
            if len(contour) != 358:
                # Fail-closed against changes from the previously accepted P4D0 geometry.
                raise ValueError("BLOCKED_P4D1_ORIGINAL_CONTOUR_GEOMETRY_DRIFT")
            adaptive, model = p4d0.adaptive_unbounded(index, game)
            scanline = p4d0.first_scanline(index, game)
            results[method] = {
                "source": SOURCE, "source_palette_size": len(selected),
                "original_source_only": True, "legacy_G32_V44_as_inputs": False,
                "contour_strokes":len(contour),
                "arms":{},
                "adaptive_model_only": model,
            }
            for arm, paint in zip(ARMS, (adaptive, scanline)):
                folder = sub/arm
                folder.mkdir()
                base = p4c0.renumber(paint+contour)
                mixed, ordering = interleave_nearest_fill(paint, contour)
                if (Counter(signature(s) for s in base) !=
                        Counter(signature(s) for s in mixed) or
                        all(signature(x)==signature(y) for x,y in zip(base, mixed))):
                    raise ValueError("BLOCKED_P4D1_NOT_CONTROLLED_REORDER")
                stages = {STAGES[0]:base, STAGES[1]:mixed}
                for tag, plan in stages.items():
                    (folder/(tag+"_PLAN.json")).write_text(
                        json.dumps(plan,ensure_ascii=False,allow_nan=False)+"\n","utf8")
                results[method]["arms"][arm] = {
                    "paint_strokes":len(paint),
                    "contour_strokes":len(contour),
                    "total_strokes":len(base),
                    "total_synthetic_vertices_NOT_CHALK":sum(len(s["points"]) for s in base),
                    "same_exact_stroke_multiset":True,
                    "ordering":ordering, "stages":{},
                    "numeric_candidate": "NOT_MEASURED",
                    "color_owner_quality": "NOT_MEASURED_COMPOSITE_ONLY",
                }
                work.append((method, arm, index, stages))
                print("P4D1_READY",method,arm,"paint",len(paint),
                      "contour",len(contour), "transitions",
                      ordering["contour_paint_transitions"],flush=True)

        runtime_renderer = {}
        with p4d0.patched_test_renderer(renderer) as audit:
            runtime_renderer = dict(audit)
            with p4b7.native_egret_session(workspace) as driver:
                driver.set_script_timeout(900)
                for method, arm, index, stages in work:
                    folder = output/method/arm
                    result = results[method]["arms"][arm]
                    previews = {}
                    native_arrays = {}
                    for stage, strokes in stages.items():
                        response = driver.execute_script(
                            "return window.AutoDrawGameRendererReference."
                            "renderP4A2BrushWidths1to10Probe(arguments[0]);",
                            strokes)
                        native, meta = read_webgl_result(
                            response,folder,stage+"_REAL_EGRET_NATIVE")
                        if (native.shape != p4d0.NATIVE_SHAPE or
                                meta.get("schema") !=
                                "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
                                meta.get("renderer") !=
                                "real Egret 5.4.1 BoardPane/WebGLRenderer" or
                                meta.get("strokeCount") != len(strokes) or
                                meta.get("syntheticAcceptedVerticesNotChalk") !=
                                sum(len(s["points"]) for s in strokes)):
                            raise ValueError("BLOCKED_P4D1_NOT_NATIVE_EGRET_OR_STROKES")
                        preview = p4c0.preview_native(native)
                        preview.save(folder/(stage+"_REAL_EGRET_CROP.png"))
                        p4d0._native_error_masks(native,index,game,folder/stage
                                                 if False else folder)
                        # Write truly stage-specific diagnostics without a second
                        # rendering. Existing P4D0 exporter writes fixed filenames.
                        for name in ("MISSING_ANY_INK_ALPHA24.png",
                                     "INK_ON_TARGET_WHITE_ALPHA24.png",
                                     "COMPOSITE_RGB_DELTA_GT32.png",
                                     "MISSING_RED_ON_SOURCE_GAME32.png"):
                            f = folder/name
                            f.rename(folder/(stage+"_"+name))
                        m = p4d0._native_stats(native,index,game)
                        result["stages"][stage] = {
                            "real_native":True,
                            "renderer":meta["renderer"],"schema":meta["schema"],
                            "accepted_stroke_count":meta["strokeCount"],
                            "accepted_vertices_NOT_CHALK":
                                meta["syntheticAcceptedVerticesNotChalk"],
                            "PNG_sha256":meta["source_sha256"],
                            "native_composite":m,
                        }
                        native_arrays[stage] = native
                        previews[stage] = preview
                        print("P4D1_EGRET",method,arm,stage,
                              "rgb",round(m[
                                "native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"],5),
                              "whiteink",m["native_ink_on_white_background_backing_px"],
                              flush=True)
                    a = result["stages"][STAGES[0]]["native_composite"]
                    z = result["stages"][STAGES[1]]["native_composite"]
                    improvement = (z[
                        "native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"] >
                        a["native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"]
                        and z["native_ink_on_white_background_backing_px"] <=
                        a["native_ink_on_white_background_backing_px"])
                    result["numeric_candidate"] = (
                        "COMPOSITE_NUMERIC_CANDIDATE_VISUAL_PENDING"
                        if improvement else "NO_COMPOSITE_NUMERIC_IMPROVEMENT")
                    result["change_from_baseline"] = {
                        "rgb_within32_nonwhite_delta":
                            z["native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"] -
                            a["native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"],
                        "white_background_ink_backing_delta":
                            z["native_ink_on_white_background_backing_px"] -
                            a["native_ink_on_white_background_backing_px"],
                        "changed_backing_RGBA_pixels":
                            int(np.any(native_arrays[STAGES[0]] !=
                                       native_arrays[STAGES[1]],axis=2).sum()),
                    }
                    write_review(folder,original,game[index],
                                 previews[STAGES[0]],previews[STAGES[1]])
                blank_result = driver.execute_script(
                    "return window.AutoDrawGameRendererReference."
                    "renderP4A2BrushWidths1to10Probe([]);")
                blank, blank_meta = read_webgl_result(
                    blank_result,output,"REAL_EGRET_BLANK")
                if (blank.shape != p4d0.NATIVE_SHAPE or
                        np.any(blank[:,:,3]) or
                        blank_meta.get("schema") !=
                        "ENGINE001_B1R_P4A2_BLANK_WEBGL"):
                    raise ValueError("BLOCKED_P4D1_NOT_NATIVE_BLANK")
        if p4b1.git_blob(renderer.read_bytes()) != RENDERER_BLOB:
            raise ValueError("BLOCKED_P4D1_RENDERER_NOT_RESTORED")

    summary = {
        "experiment":EXPERIMENT,
        "result":"E3_TRUE_NATIVE_EF_INTERLEAVED_VS_BASELINE_COMPLETE",
        "original_sha256":SOURCE_SHA,"source_original_recomputed_same_run":True,
        "source_key":SOURCE,"methods":results,"native_scenes_rendered":8,
        "blank_native_zero":True,"source_is_original_RGB_p3d":True,
        "renderer_test_only_dynamic_quota":runtime_renderer,
        "production_promotion":False,"E4_live":"NOT_RUN",
        "E5_independent_live":"NOT_RUN","exact_run_bound_CHALK":None,
        "frozen_99_0protected_3logical":"NOT_MEASURED_COMPOSITE_ONLY",
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    members = {str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
               for p in sorted(output.rglob("*")) if p.is_file()}
    summary["members_sha256"]=members
    (output/"report.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    print("P4D1_NATIVE_COMPLETE 8_SCENES",flush=True)
    return summary


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--engine-js",type=Path,required=True)
    parser.add_argument("--renderer",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    opts=parser.parse_args()
    run(opts.workspace,opts.source,opts.engine_js,opts.renderer,opts.output)
