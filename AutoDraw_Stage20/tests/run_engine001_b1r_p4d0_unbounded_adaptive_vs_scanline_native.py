#!/usr/bin/env python3
"""P4D0: full original B1-R E/F, unlimited-stroke adaptive vs row-major scanline in genuine Egret.

No G32/V44 candidate, no CHALK, no production renderer mutation. The archived
test renderer is changed ONLY inside a scoped runtime experiment, then restored.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_complex_holdout_v5 import read_webgl_result

EXPERIMENT = "ENGINE001_B1R_P4D0_UNBOUNDED_ADAPTIVE_VS_SCANLINE_EGRET_V1"
PREREG = "ENGINE001_B1R_P4D0_UNBOUNDED_ADAPTIVE_VS_SCANLINE_NATIVE_PREREG_2026-11-18.md"
RENDERER_BLOB = "76d950e0a8911888a9df3b675b866519ecf7bba4"
SOURCE_SHA = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
METHODS = ("E_SOBEL90", "F_SOBEL90_LAB12")
ARMS = ("ADAPTIVE_UNBOUNDED", "FIRST_SCANLINE")
WHITE = 6
X0 = 155
SCALE = 3
NATIVE_SHAPE = (720, 1380, 4)
ALPHA = 24
SOURCE = "C_192_D_COMPONENT24"


def _stroke(owner: int, game: np.ndarray, x0: float, x1: float, y: int,
            width: int = 2) -> dict:
    rgb = game[owner]
    color = (int(rgb[0]) << 16) | (int(rgb[1]) << 8) | int(rgb[2])
    return {"strokeId": "icon-0", "colorIndex": int(owner),
            "colorRgb": color, "width": width,
            "points": [{"x": float(X0 + x0), "y": float(y)},
                       {"x": float(X0 + x1), "y": float(y)}]}


def first_scanline(index: np.ndarray, game: np.ndarray) -> list[dict]:
    """Simple exact row-major runs; no component sorting or synthetic caps."""
    if (index.shape != (240, 150) or index.dtype != np.uint8 or
            game.shape != (128, 3) or game.dtype != np.uint8):
        raise ValueError("BLOCKED_P4D0_SCANLINE_SHAPE")
    plan = []
    for y in range(240):
        x = 0
        while x < 150:
            owner = int(index[y, x])
            start = x
            while x + 1 < 150 and index[y, x + 1] == owner:
                x += 1
            if owner != WHITE:
                plan.append(_stroke(owner, game, start + .125, x + .375, y))
            x += 1
    return p4c0.renumber(plan)


@contextmanager
def unlimited_owner_planner():
    """Reuse frozen P4B1 algorithm, change only local globals during this call."""
    before = (p4b1.MAX_STROKES, p4b1.MAX_VERTICES)
    p4b1.MAX_STROKES = float("inf")
    p4b1.MAX_VERTICES = float("inf")
    try:
        yield
    finally:
        p4b1.MAX_STROKES, p4b1.MAX_VERTICES = before


def _model_missing(index: np.ndarray, owner: int, strokes: list[dict]):
    """Only a candidate-search heuristic, NEVER native game coverage evidence."""
    target = index == owner
    footprint = np.zeros(target.shape, np.uint8)
    for s in strokes:
        xy = np.array([[int(round(p["x"] - X0)), int(round(p["y"]))]
                       for p in s["points"]], np.int32).reshape(-1, 1, 2)
        cv2.polylines(footprint, [xy], False, 255,
                      thickness=int(s["width"]), lineType=cv2.LINE_8)
    return target & (footprint == 0)


def adaptive_unbounded(index: np.ndarray, game: np.ndarray):
    """All original P4B1 owner strokes, then model-gap source-only width1 repair.

    MODEL mask selects where to TRY real strokes. Native scoring is separate.
    """
    present = sorted(int(i) for i in np.unique(index) if i != WHITE)
    plan = []
    per_color = {}
    for owner in sorted(present, key=lambda c: (-int(np.sum(index == c)), c)):
        mask = (index == owner)
        with unlimited_owner_planner():
            base, model = p4b1.plan_component(mask, mask, owner, game, "A_ORIENTED")
        missed = _model_missing(index, owner, base)
        repairs = []
        for y in range(240):
            x = 0
            while x < 150:
                if not missed[y, x]:
                    x += 1
                    continue
                start = x
                while x + 1 < 150 and missed[y, x + 1]:
                    x += 1
                repairs.append(_stroke(owner, game, start + .125, x + .375, y, width=1))
                x += 1
        plan.extend(base)
        plan.extend(repairs)
        per_color[str(owner)] = {
            "source_owner_logical": int(mask.sum()),
            "original_unlimited_P4B1_strokes": len(base),
            "model_only_repair_strokes": len(repairs),
            "model_only_missing_logical": int(missed.sum()),
            "native_coverage_NOT_RUN": True,
        }
        print("P4D0_ADAPTIVE_COLOR", owner, "strokes", len(base),
              "repair", len(repairs), "source", int(mask.sum()), flush=True)
    return p4c0.renumber(plan), per_color


def patch_renderer_in_memory(js: str) -> str:
    """Exact, narrowly scoped test-time bypass of old *test* caps only."""
    def section(source, start, end, replaces):
        a = source.index(start)
        b = source.index(end, a)
        piece = source[a:b]
        for old, new in replaces:
            if piece.count(old) != 1:
                raise ValueError("BLOCKED_P4D0_RENDERER_PATCH_ANCHOR")
            piece = piece.replace(old, new)
        return source[:a] + piece + source[b:]
    # BoardPane constructor's second arg is a synthetic point quota, not CHALK.
    js = section(js, "function makeTemporalBoard(",
                 "\n  function renderTemporalStudy()", [(
        "const board = new BoardPane(false, 6000);",
        "const board = new BoardPane(false, Math.max(6000, " +
        "strokes.reduce((n,s)=>n+s.points.length,0) + 64));")])
    js = section(js, "function renderComplexHoldoutColorProbe(",
                 "\n  // ENGINE-001 V35", [(
        "strokes.length < 1 || strokes.length > 3000",
        "strokes.length < 1"), (
        'if (count > 5900) throw new Error("V5 point budget exceeded.");',
        "/* P4D0 test only: no aggregate synthetic point ceiling. */")])
    return js


@contextmanager
def patched_test_renderer(renderer: Path):
    """Never mutate Git's archived test source persistently. Restore on exceptions."""
    original = renderer.read_bytes()
    if p4b1.git_blob(original) != RENDERER_BLOB:
        raise ValueError("BLOCKED_P4D0_FROZEN_RENDERER_SHA")
    modified = patch_renderer_in_memory(original.decode("utf8")).encode("utf8")
    if modified == original or b"Math.max(6000" not in modified:
        raise AssertionError("BLOCKED_P4D0_NO_TEST_RENDERER_PATCH")
    try:
        renderer.write_bytes(modified)
        yield {"original_renderer_git_blob": RENDERER_BLOB,
               "test_only_renderer_sha256": digest(modified),
               "modified_archived_test_renderer_in_memory_during_run": True,
               "board_quota_dynamic": True, "render_composite_stroke_cap": None,
               "render_composite_vertex_cap": None}
    finally:
        renderer.write_bytes(original)
        if renderer.read_bytes() != original:
            raise AssertionError("BLOCKED_P4D0_RENDERER_RESTORE")


def _native_stats(pixels: np.ndarray, index: np.ndarray, game: np.ndarray) -> dict:
    """Composite-only native scoring; NOT per-owner alpha or foreign attribution."""
    if pixels.shape != NATIVE_SHAPE or pixels.dtype != np.uint8:
        raise ValueError("BLOCKED_P4D0_NATIVE_RGBA")
    rgba = pixels[:, X0*SCALE:(X0+150)*SCALE]
    ink = rgba[:, :, 3] >= ALPHA
    target = np.repeat(np.repeat(index != WHITE, SCALE, 0), SCALE, 1)
    expected = np.repeat(np.repeat(game[index], SCALE, 0), SCALE, 1)
    # Rendered composite, against white background; not a per-owner attribution.
    preview = np.asarray(p4c0.preview_native(pixels), np.uint8)
    diff = np.max(np.abs(preview.astype(np.int16) - expected.astype(np.int16)), axis=2)
    return {
        "native_nonwhite_any_ink_coverage_alpha24":
            float((ink & target).sum() / target.sum()),
        "native_missing_any_ink_backing_px": int((target & ~ink).sum()),
        "native_ink_on_white_background_backing_px": int((ink & ~target).sum()),
        "native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite":
            float(((diff <= 32) & target).sum()/target.sum()),
        "source_nonwhite_target_backing_px": int(target.sum()),
        "native_any_ink_backing_px": int(ink.sum()),
        "per_owner_same_color_quality_gates": "NOT_MEASURED_COMPOSITE_ONLY",
    }


def _native_error_masks(pixels: np.ndarray, index: np.ndarray, game: np.ndarray,
                        folder: Path):
    rgba = pixels[:, X0*SCALE:(X0+150)*SCALE]
    target = np.repeat(np.repeat(index != WHITE, SCALE, 0), SCALE, 1)
    ink = rgba[:, :, 3] >= ALPHA
    expected = np.repeat(np.repeat(game[index], SCALE, 0), SCALE, 1)
    real = np.asarray(p4c0.preview_native(pixels), np.uint8)
    colorwrong = target & (np.max(np.abs(
        real.astype(np.int16)-expected.astype(np.int16)), axis=2) > 32)
    for name, arr in (
            ("MISSING_ANY_INK_ALPHA24.png", target & ~ink),
            ("INK_ON_TARGET_WHITE_ALPHA24.png", ink & ~target),
            ("COMPOSITE_RGB_DELTA_GT32.png", colorwrong)):
        Image.fromarray((arr.astype(np.uint8)*255)).save(folder/name)
    # Red missing over original source indexed RGB for immediate human review.
    base = expected.copy()
    red = target & ~ink
    base[red] = (245, 30, 35)
    Image.fromarray(base).save(folder/"MISSING_RED_ON_SOURCE_GAME32.png")


def _visual_review(original: np.ndarray, palette_rgb: np.ndarray, renders: dict,
                   output: Path, label: str):
    if any(k not in renders for k in ARMS):
        return
    pieces = [
        ("ORIGINAL", Image.fromarray(original).resize((450,720),Image.Resampling.NEAREST)),
        ("SOURCE GAME32", Image.fromarray(palette_rgb).resize((450,720),Image.Resampling.NEAREST)),
        ("ADAPTIVE NO TOTAL CAPS", renders[ARMS[0]]),
        ("TOP DOWN LEFT RIGHT", renders[ARMS[1]]),
    ]
    sheet = Image.new("RGB",(1800,760),"white")
    draw = ImageDraw.Draw(sheet)
    for k,(text,img) in enumerate(pieces):
        sheet.paste(img,(450*k,40))
        draw.text((450*k+8,14), text, fill=(0,0,0))
    sheet.save(output/("SIDE_BY_SIDE_"+label+".png"))


def _plan_summary(plan: list[dict]) -> dict:
    total_points = sum(len(s["points"]) for s in plan)
    return {"strokes": len(plan), "synthetic_vertices_NOT_CHALK": total_points,
            "colors": sorted(set(int(s["colorIndex"]) for s in plan)),
            "widths": sorted(set(int(s["width"]) for s in plan)),
            "history_unbounded_p4b1": True,
            "fixed_250_500_or_3000_5900_not_applied": True}


def run(workspace: Path, source: Path, engine_js: Path,
        renderer: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P4D0_OUTPUT_EXISTS")
    check_source(source)
    if p4b1.git_blob(renderer.read_bytes()) != RENDERER_BLOB:
        raise ValueError("BLOCKED_P4D0_PINNED_EGRET")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4D0_MISSING_PRE_REGISTERED_SCOPE")
    game, _ = p3b.read_engine_palette(engine_js)
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D0 diagnostic: unchanged original B1-R E/F game32 source.\n"
        "ADAPTIVE_UNBOUNDED vs row-major FIRST_SCANLINE fixed width2.\n"
        "No total stroke limits in opt-in native test replay; original game quota NOT overridden in production.\n"
        "Only actual Egret 5.4.1 BoardPane/WebGL saved as native PNG.\n"
        "Composite any-ink score and RGB mismatch are NOT owner-specific protected safety PASS.\n"
        "Exact game CHALK, E4/E5: NOT_RUN. G32/V44 not used.\n","utf8")
    all_results = {}
    with tempfile.TemporaryDirectory(prefix="engine001-p4d0-original-") as temp:
        fresh = Path(temp)/"fresh_p3d"
        parent = p3d.run(source, engine_js, fresh)
        if (parent["experiment"] != p3d.EXPERIMENT or
                parent["original_source_sha256"] != SOURCE_SHA or
                not parent["P3B_original_recomputed_in_current_run"] or
                parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D0_NOT_FRESH_ORIGINAL_SOURCE")
        original = np.asarray(Image.open(fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"), np.uint8)
        Image.fromarray(original).save(output/"ORIGINAL_RGB_LOGICAL.png")
        jobs = []
        for method in METHODS:
            folder = output/method
            folder.mkdir()
            source_index = np.asarray(Image.open(
                fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")), np.uint8).copy()
            selected = parent["all_results"][SOURCE]["selected_engine_indices"]
            p4c0.validate_source(source_index, game, selected)
            if parent["all_results"][SOURCE]["methods"][method]["status"] != (
                    "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED"):
                raise ValueError("BLOCKED_P4D0_ORIGINAL_SOURCE_STATUS")
            Image.fromarray(source_index).save(folder/"SOURCE_ENGINE_INDICES.png")
            reference = game[source_index]
            Image.fromarray(reference).save(folder/"SOURCE_GAME32_RGB.png")
            contour, mask, contour_owner = p4c0.source_joint_outline(source_index,original,game)
            Image.fromarray(mask.astype(np.uint8)*255).save(folder/"NEW_ORIGINAL_SOURCE_CONTOUR.png")
            paint_adaptive, diag = adaptive_unbounded(source_index, game)
            paint_raster = first_scanline(source_index, game)
            fulls = {ARMS[0]: paint_adaptive, ARMS[1]: paint_raster}
            method_result = {"source_key":SOURCE, "selected_engine_swatches":len(selected),
                             "nonwhite_native_colors_to_paint":len(set(np.unique(source_index))-{WHITE}),
                             "original_source_only":True, "no_G32_V44_inputs":True,
                             "full_contour_strokes":len(contour),
                             "arms":{}, "adaptive_per_color_MODEL_ONLY":diag}
            for arm, paint in fulls.items():
                native = folder/arm
                native.mkdir()
                combined = p4c0.renumber(paint+contour)
                for name, data in (("PAINT_ONLY",paint),("PAINT_AND_CONTOUR",combined)):
                    (native/(name+"_FULL_PLAN.json")).write_text(
                        json.dumps(data, ensure_ascii=False, allow_nan=False)+"\n","utf8")
                method_result["arms"][arm] = {
                    "paint":_plan_summary(paint), "full":_plan_summary(combined),
                    "native_status":"NOT_RUN", "real_native_snapshots":{}}
                jobs.append((method,arm,paint,combined,source_index,reference))
                print("P4D0_SAVED_FULL_PLANS",method,arm,"paint",len(paint),
                      "vertices",sum(len(s["points"]) for s in paint),
                      "outline",len(contour),flush=True)
            all_results[method] = method_result

        # This scoped change is only to existing archived *test fixture* JS.
        # After the with block the byte-identical frozen renderer is restored.
        renderer_audit = None
        with patched_test_renderer(renderer) as audit:
            renderer_audit = dict(audit)
            with p4b7.native_egret_session(workspace) as driver:
                driver.set_script_timeout(900)
                for method,arm,paint,full,index,reference in jobs:
                    native_dir = output/method/arm
                    result = all_results[method]["arms"][arm]
                    captures = {}
                    for stage, strokes in (("PAINT_ONLY",paint),
                                           ("PAINT_AND_CONTOUR",full)):
                        try:
                            response = driver.execute_script(
                                "return window.AutoDrawGameRendererReference."+
                                "renderP4A2BrushWidths1to10Probe(arguments[0]);", strokes)
                            rgba, metadata = read_webgl_result(
                                response,native_dir,stage+"_REAL_NATIVE_BOARD")
                            if (metadata.get("schema") !=
                                "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
                                    metadata.get("renderer") !=
                                    "real Egret 5.4.1 BoardPane/WebGLRenderer" or
                                    rgba.shape != NATIVE_SHAPE):
                                raise ValueError("BLOCKED_P4D0_NOT_REAL_EGRET")
                            img = p4c0.preview_native(rgba)
                            img.save(native_dir/(stage+"_REAL_EGRET_CROP.png"))
                            metrics = _native_stats(rgba,index,game)
                            if stage == "PAINT_ONLY":
                                _native_error_masks(rgba,index,game,native_dir)
                            result["real_native_snapshots"][stage] = {
                                "metadata": {k:v for k,v in metadata.items()
                                             if k != "glInfo"},
                                "native_composite": metrics,
                                "raw_native_png":stage+"_REAL_NATIVE_BOARD.png",
                                "rendered_successfully": True}
                            captures[stage] = img
                            print("P4D0_TRUE_EGRET",method,arm,stage,
                                  "inkcov",round(metrics[
                                      "native_nonwhite_any_ink_coverage_alpha24"],6),
                                  "rgbmatch",round(metrics[
                                      "native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"],6),
                                  flush=True)
                        except Exception as exc:
                            result["real_native_snapshots"][stage] = {
                                "rendered_successfully": False,
                                "error_type":type(exc).__name__,
                                "message":str(exc)[:500]}
                            print("P4D0_NATIVE_BLOCKED",method,arm,stage,
                                  type(exc).__name__,str(exc)[:250],flush=True)
                            # Browser/renderer may be unhealthy; preserve the
                            # full plan, original and negative status, never trim.
                            break
                    result["native_status"] = ("COMPLETE" if len(captures)==2
                                                else "PARTIAL_OR_BLOCKED")
                # Independent native zero-input control, even when all scenes FAIL.
                blank_data=driver.execute_script(
                    "return window.AutoDrawGameRendererReference."+
                    "renderP4A2BrushWidths1to10Probe([]);")
                blank,blank_meta=read_webgl_result(
                    blank_data,output,"REAL_EGRET_BLANK")
                if blank.shape!=NATIVE_SHAPE or np.any(blank[:,:,3]) or (
                    blank_meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL"):
                    raise ValueError("BLOCKED_P4D0_BLANK_NOT_EMPTY_OR_NATIVE")
        if renderer.read_bytes() != (workspace/"AutoDraw_Stage20"/"tests"/
                                     "game_renderer_reference.js").read_bytes():
            raise ValueError("BLOCKED_P4D0_RENDERER_RESTORATION_INCONSISTENT")
        if p4b1.git_blob(renderer.read_bytes()) != RENDERER_BLOB:
            raise ValueError("BLOCKED_P4D0_FROZEN_RENDERER_NOT_RESTORED")

        # Compare PAINT_ONLY and PAINT_AND_CONTOUR without inventing any image.
        for method in METHODS:
            folder = output/method
            src = np.asarray(Image.open(folder/"SOURCE_GAME32_RGB.png"),np.uint8)
            for stage in ("PAINT_ONLY","PAINT_AND_CONTOUR"):
                available = {}
                for arm in ARMS:
                    path = folder/arm/(stage+"_REAL_EGRET_CROP.png")
                    if path.exists():
                        available[arm] = Image.open(path).convert("RGB")
                _visual_review(original,src,available,folder,stage)
    completed = sum(
        all_results[m]["arms"][a]["native_status"]=="COMPLETE"
        for m in METHODS for a in ARMS)
    final = {
        "experiment":EXPERIMENT,"result":(
            "ALL_FOUR_UNBOUNDED_EGRET_FULL_RENDERS_COMPLETED"
            if completed==4 else "PARTIAL_OR_BLOCKED_UNBOUNDED_EGRET"),
        "source_original_SHA256":SOURCE_SHA,
        "source_original_recomputed_same_run":True,
        "source_key":SOURCE,"methods":all_results,
        "native_arms_full_2stage":completed,
        "native_arms_requested":4,
        "temporary_test_renderer":renderer_audit,
        "production_promotion":False, "E4_game_runtime":"NOT_RUN",
        "E5_independent":"NOT_RUN","exact_run_bound_CHALK":None,
        "native_single_source_original_only":True,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    hashes = {str(f.relative_to(output)).replace("\\","/"):digest(f.read_bytes())
              for f in sorted(output.rglob("*")) if f.is_file()}
    final["members_sha256"]=hashes
    (output/"report.json").write_text(
        json.dumps(final,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    print("P4D0_RESULT",final["result"],"completed",completed,flush=True)
    return final


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--engine-js",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    x=p.parse_args()
    run(x.workspace,x.source,x.engine_js,x.renderer,x.output)
