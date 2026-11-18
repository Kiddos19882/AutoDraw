#!/usr/bin/env python3
"""B1-R-P4C0: original-only E/F full multicolor native Egret diagnostic, not production."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import native_batch, read_webgl_result

EXPERIMENT = "ENGINE001_B1R_P4C0_FULL_MULTICOLOR_EGRET_PREVIEW_V1"
PREREG = "ENGINE001_B1R_P4C0_FULL_SOURCE_MULTICOLOR_NATIVE_PREVIEW_PREREG_2026-11-18.md"
SOURCE = "C_192_D_COMPONENT24"
METHODS = p3d.MASKS
RENDERER_BLOB = "76d950e0a8911888a9df3b675b866519ecf7bba4"
P4B1_BLOB = "b95aa361cf2ec94d5fa28e7309bd3e4af15eca93"
ORIGINAL_SHA = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
WHITE = 6
MAX_STROKES = 3000
MAX_VERTICES = 5900
PAINT_STROKES_CAP = 2600
PAINT_VERTICES_CAP = 5200
ALPHA = 24
SIZE = (240, 150)
BACKING = (720, 1380, 4)
X0 = 155
SCALE = 3


def validate_source(index: np.ndarray, palette: np.ndarray, selected: list):
    if (index.shape != SIZE or index.dtype != np.uint8 or
            palette.shape != (128, 3) or palette.dtype != np.uint8 or
            len(set(int(x) for x in selected)) != 32 or
            WHITE not in selected or
            not set(int(v) for v in np.unique(index)).issubset(set(selected))):
        raise ValueError("BLOCKED_P4C0_WRONG_ORIGINAL_PALETTE_OR_INDEX")


def allocate_limits(counts: dict[int, int], total: int = PAINT_STROKES_CAP) -> dict[int, int]:
    """Stable weighted fair-share with no owner completely dropped by rounding."""
    if not counts or any(type(k) is not int or type(v) is not int or v <= 0
                         for k, v in counts.items()) or total < len(counts):
        raise ValueError("BLOCKED_P4C0_INVALID_BUDGET_INPUT")
    keys = sorted(counts)
    limits = {key: 1 for key in keys}
    weight = {key: float(counts[key]) ** 0.60 for key in keys}
    # Recalculate fair-share priorities; cap each original P4B1 owner at 250.
    left = total - len(keys)
    while left:
        options = [k for k in keys if limits[k] < p4b1.MAX_STROKES]
        if not options:
            break
        key = max(options, key=lambda k: (weight[k] / (limits[k] + 1), -k))
        limits[key] += 1
        left -= 1
    assert sum(limits.values()) <= total
    return limits


def renumber(strokes: list[dict]) -> list[dict]:
    result = []
    for s in strokes:
        result.append({k: s[k] for k in ("strokeId", "width", "colorIndex", "colorRgb", "points")})
        result[-1]["strokeId"] = "icon-%d" % (len(result)-1)
    return result


def source_micro(owner: int, game: np.ndarray, pixel_yx: tuple[int, int]):
    y, x = pixel_yx
    rgb = game[owner]
    return {"strokeId": "icon-0", "colorIndex": owner,
            "colorRgb": (int(rgb[0]) << 16) | (int(rgb[1]) << 8) | int(rgb[2]),
            "width": 1, "points": [{"x": float(X0+x)+.125, "y": float(y)},
                                    {"x": float(X0+x)+.375, "y": float(y)}]}


def color_plan(index: np.ndarray, game: np.ndarray):
    unique = sorted(int(i) for i in np.unique(index) if int(i) != WHITE)
    if not unique:
        raise ValueError("BLOCKED_P4C0_NO_NONWHITE_COLORS")
    masks = {i: index == i for i in unique}
    limits = allocate_limits({i: int(m.sum()) for i, m in masks.items()})
    plans, details = {}, {}
    for i in unique:
        mask = masks[i]
        planned, model = p4b1.plan_component(mask, mask, i, game, "A_ORIENTED")
        if not planned:
            y, x = (int(v) for v in np.argwhere(mask)[0])
            planned = [source_micro(i, game, (y, x))]
        plans[i] = planned
        details[i] = {"source_owner_pixels": int(mask.sum()),
                      "model_original_strokes": len(planned),
                      "model": model,
                      "budget_quota": limits[i]}
        print("P4C0_PLAN_COLOR", i, "area", int(mask.sum()),
              "model_strokes", len(planned), flush=True)
    # Color order is deterministic; major regions first so the later small details
    # can cover them in the composite, while owner validation remains per-color.
    order = sorted(unique, key=lambda i: (-int(masks[i].sum()), i))
    selected = [s for i in order for s in plans[i][:limits[i]]]
    if sum(len(s["points"]) for s in selected) > PAINT_VERTICES_CAP:
        selected = selected[:PAINT_VERTICES_CAP // 2]
    selected = renumber(selected)
    by_owner = {i: sum(s["colorIndex"] == i for s in selected) for i in unique}
    for i in unique:
        details[i].update({"actual_selected_strokes": by_owner[i],
                           "truncated_by_global_preview_budget": by_owner[i] < len(plans[i])})
    if (not selected or len(selected) > PAINT_STROKES_CAP or
            sum(len(s["points"]) for s in selected) > PAINT_VERTICES_CAP or
            any(not 1 <= s["width"] <= 10 for s in selected)):
        raise ValueError("BLOCKED_P4C0_COLOR_BUDGET")
    return selected, details


def source_joint_outline(index: np.ndarray, original: np.ndarray, game: np.ndarray):
    """Fresh contours from CURRENT indexed colors and original-source gradients."""
    if index.shape != SIZE or original.shape != (240, 150, 3):
        raise ValueError("BLOCKED_P4C0_OUTLINE_SOURCE")
    edge = np.zeros(SIZE, np.uint8)
    neq_h = index[:, :-1] != index[:, 1:]
    neq_v = index[:-1, :] != index[1:, :]
    edge[:, :-1] |= neq_h
    edge[:, 1:] |= neq_h
    edge[:-1, :] |= neq_v
    edge[1:, :] |= neq_v
    source_gray = cv2.cvtColor(original, cv2.COLOR_RGB2GRAY)
    strong = cv2.Canny(source_gray, 55, 130) > 0
    near_seam = cv2.dilate(edge, np.ones((3, 3), np.uint8), iterations=1) > 0
    face_hands = np.zeros(SIZE, np.bool_)
    for name in ("female_face_eyes", "male_face_eyes", "hands"):
        x0, y0, x1, y1 = p3b.roi_logical(name)
        face_hands[y0:y1, x0:x1] = True
    mask = ((edge > 0) & strong) | (strong & near_seam) | (strong & face_hands)
    # No V44, G32 or unrelated feature source ever enters this process.
    contours, _ = cv2.findContours(mask.astype(np.uint8),
                                    cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    result = []
    darkest = int(min(sorted(set(int(v) for v in np.unique(index)) - {WHITE}),
                      key=lambda i: (int(game[i].sum()), i)))
    color = game[darkest]
    rgb = (int(color[0]) << 16) | (int(color[1]) << 8) | int(color[2])
    for c in sorted(contours, key=lambda c: (-cv2.arcLength(c, False),
                                               cv2.boundingRect(c)[1],
                                               cv2.boundingRect(c)[0])):
        path = cv2.approxPolyDP(c, .42, False).reshape(-1, 2).tolist()
        if len(path) < 2:
            continue
        for start in range(0, len(path)-1, 127):
            points = path[start:start+128]
            if len(points) < 2:
                continue
            result.append({"strokeId":"icon-0", "colorIndex": darkest,
                           "colorRgb": rgb, "width": 1,
                           "points": [{"x": float(x+X0), "y": float(y)} for x,y in points]})
    if not result:
        raise ValueError("BLOCKED_P4C0_NEW_SOURCE_OUTLINE_EMPTY")
    return result, mask, darkest


def preview_native(rgba: np.ndarray) -> Image.Image:
    if rgba.shape != BACKING or rgba.dtype != np.uint8:
        raise ValueError("BLOCKED_P4C0_NOT_REAL_NATIVE_RGBA")
    roi = Image.fromarray(rgba, "RGBA").crop((X0*SCALE, 0, (X0+150)*SCALE, 240*SCALE))
    return Image.alpha_composite(Image.new("RGBA", roi.size, "white"), roi).convert("RGB")


def native_mask_metrics(native_by_owner: dict, index: np.ndarray):
    """Native pixel comparison per swatch; masks exactly same backing coordinate space."""
    missing = np.zeros((720, 450), np.uint8)
    foreign = np.zeros((720, 450), np.uint8)
    protected = p4b4.source_critical_rois()
    counts = {}
    for i in sorted(int(k) for k in native_by_owner):
        image = native_by_owner[i]
        if image.shape != BACKING or image.dtype != np.uint8:
            raise ValueError("BLOCKED_P4C0_SWATCH_NOT_NATIVE")
        ink = image[:, X0*SCALE:(X0+150)*SCALE, 3] >= ALPHA
        target = np.repeat(np.repeat(index == i, SCALE, 0), SCALE, 1)
        protected_other = np.repeat(
            np.repeat(protected & (index != i), SCALE, 0), SCALE, 1)
        far = cv2.distanceTransform((~target).astype(np.uint8),
                                    cv2.DIST_L2, cv2.DIST_MASK_PRECISE) > 3*SCALE
        missed = target & ~ink
        leaked = ink & ~target
        missing[missed] = 255
        foreign[leaked] = 255
        total = int(target.sum())
        counts[str(i)] = {"owner_backing_pixels": total,
                          "covered_backing_pixels": int((target & ink).sum()),
                          "owner_coverage_alpha24": float((target & ink).sum()/total),
                          "owner_missing_backing_pixels": int(missed.sum()),
                          "foreign_backing_pixels": int(leaked.sum()),
                          "foreign_beyond3logical_backing_pixels": int((leaked & far).sum()),
                          "protected_foreign_backing_pixels": int((ink & protected_other).sum()),
                          "quality_frozen_gates": bool(
                              (target & ink).sum()/total >= .99 and
                              not (leaked & far).any() and
                              not (ink & protected_other).any())}
    return missing, foreign, counts


def review_canvas(original: np.ndarray, reference: np.ndarray,
                  paint: Image.Image, outlined: Image.Image,
                  missing: np.ndarray, foreign: np.ndarray):
    parts = [
        ("ORIGINAL RGB", Image.fromarray(original).resize((450,720),Image.Resampling.NEAREST)),
        ("SOURCE GAME32 E/F", Image.fromarray(reference).resize((450,720),Image.Resampling.NEAREST)),
        ("EGRET PAINT ONLY", paint),
        ("EGRET PAINT + NEW OUTLINE", outlined),
    ]
    sheet = Image.new("RGB",(4*450,762),(248,248,248))
    draw = ImageDraw.Draw(sheet)
    for k,(label,img) in enumerate(parts):
        sheet.paste(img,(k*450,42))
        draw.text((k*450+8,13), label, fill=(16,16,16))
    return sheet


def run(workspace: Path, source: Path, engine_js: Path, renderer: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P4C0_OUTPUT_ALREADY_EXISTS")
    check_source(source)
    if p4b1.git_blob(renderer.read_bytes()) != RENDERER_BLOB:
        raise ValueError("BLOCKED_P4C0_RENDERER_DRIFT")
    if p4b1.git_blob(Path(p4b1.__file__).read_bytes()) != P4B1_BLOB:
        raise ValueError("BLOCKED_P4C0_PARENT_PLANNER_DRIFT")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4C0_MISSING_PREREG")
    game, provenance = p3b.read_engine_palette(engine_js)
    output.mkdir(parents=True)
    findings = {}
    with tempfile.TemporaryDirectory(prefix="engine001-p4c0-original-") as tmp:
        fresh = Path(tmp)/"P3D_CURRENT_SOURCE"
        parent = p3d.run(source, engine_js, fresh)
        if (parent["experiment"] != p3d.EXPERIMENT or
                parent["original_source_sha256"] != ORIGINAL_SHA or
                not parent["P3B_original_recomputed_in_current_run"] or
                parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4C0_P3D_SOURCE")
        original = np.asarray(Image.open(fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"),np.uint8)
        Image.fromarray(original).save(output/"ORIGINAL_RGB_LOGICAL.png")
        for method in METHODS:
            key = SOURCE+"_"+method
            folder = output/method
            folder.mkdir()
            source_index = np.asarray(Image.open(fresh/(key+"_ENGINE_INDICES.png")),np.uint8).copy()
            selected = parent["all_results"][SOURCE]["selected_engine_indices"]
            validate_source(source_index, game, selected)
            item = parent["all_results"][SOURCE]["methods"][method]
            if item["status"] != "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED":
                raise ValueError("BLOCKED_P4C0_REJECTED_EF_SOURCE")
            reference = game[source_index]
            Image.fromarray(source_index).save(folder/"SOURCE_ENGINE_INDICES.png")
            Image.fromarray(reference).save(folder/"SOURCE_GAME32_RGB.png")
            paint, plan = color_plan(source_index, game)
            contours, mask, black_index = source_joint_outline(source_index, original, game)
            # The current source's selected darkest swatch is a real original palette color.
            if black_index not in selected:
                raise ValueError("BLOCKED_P4C0_OUTLINE_NOT_SOURCE_SWATCH")
            room_strokes = MAX_STROKES-len(paint)
            room_vertices = MAX_VERTICES-sum(len(s["points"]) for s in paint)
            actual_contours = []
            for s in contours:
                if len(actual_contours) >= room_strokes or len(s["points"]) > room_vertices:
                    continue
                actual_contours.append(s)
                room_vertices -= len(s["points"])
            final = renumber(paint + actual_contours)
            if (not actual_contours or len(final) > MAX_STROKES or
                    sum(len(s["points"]) for s in final) > MAX_VERTICES or
                    any(not 1<=s["width"]<=10 for s in final)):
                raise ValueError("BLOCKED_P4C0_NATIVE_BUDGET_OR_OUTLINE")
            (folder/"PLAN_PAINT_ONLY.json").write_text(
                json.dumps(paint,ensure_ascii=False,allow_nan=False)+"\n","utf8")
            (folder/"PLAN_PAINT_OUTLINE.json").write_text(
                json.dumps(final,ensure_ascii=False,allow_nan=False)+"\n","utf8")
            Image.fromarray(mask.astype(np.uint8)*255).save(folder/"NEW_ORIGINAL_SOURCE_OUTLINE_MASK.png")
            native_dir = folder/"NATIVE_COLOR_BY_COLOR"
            native_dir.mkdir()
            images, metas, manifest = native_batch(
                workspace,"P4C0-"+method+"-PAINT",paint,native_dir,
                renderer_method="renderP4A2BrushWidths1to10Probe")
            observed = set(manifest["colors_rendered"])
            expected = set(int(v) for v in np.unique(source_index))-{WHITE}
            if (observed != expected or set(images)!={*(f"color-{v}" for v in expected), "composite", "blank"} or
                    any(a.shape!=BACKING for a in images.values()) or
                    metas["composite"].get("renderer") !=
                    "real Egret 5.4.1 BoardPane/WebGLRenderer" or
                    metas["composite"].get("schema") !=
                    "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
                    np.any(images["blank"][:,:,3])):
                raise ValueError("BLOCKED_P4C0_NATIVE_PAINT_OR_BLANK")
            paint_native = images["composite"]
            paint_preview = preview_native(paint_native)
            paint_preview.save(folder/"REAL_EGRET_PAINT_ONLY.png")
            # A separate true native full-plan replay, with freshly generated
            # RGB+indexed-source contour appended after all painted colors.
            with p4b7.native_egret_session(workspace) as driver:
                actual = driver.execute_script(
                    "return window.AutoDrawGameRendererReference.renderP4A2BrushWidths1to10Probe(arguments[0]);",
                    final)
                overlay_native, overlay_meta = read_webgl_result(
                    actual, folder,"P4C0-"+method+"-NATIVE_PAINT_AND_OUTLINE")
                empty = driver.execute_script(
                    "return window.AutoDrawGameRendererReference.renderP4A2BrushWidths1to10Probe([]);")
                blank_again, blank_meta = read_webgl_result(
                    empty, folder,"P4C0-"+method+"-NEW_OUTLINE_BLANK")
                if (overlay_meta.get("renderer") !=
                        "real Egret 5.4.1 BoardPane/WebGLRenderer" or
                        overlay_meta.get("schema") !=
                        "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
                        blank_meta.get("schema") != "ENGINE001_B1R_P4A2_BLANK_WEBGL" or
                        np.any(blank_again[:,:,3])):
                    raise ValueError("BLOCKED_P4C0_OUTLINE_NOT_NATIVE_EGRET")
            outlined = preview_native(overlay_native)
            outlined.save(folder/"REAL_EGRET_PAINT_AND_NEW_OUTLINE.png")
            by_owner = {i:images["color-"+str(i)] for i in sorted(expected)}
            missing, foreign, metrics = native_mask_metrics(by_owner, source_index)
            Image.fromarray(missing).save(folder/"REAL_EGRET_MISSING_ALPHA24.png")
            Image.fromarray(foreign).save(folder/"REAL_EGRET_FOREIGN_ALPHA24.png")
            sheet = review_canvas(original,reference,paint_preview,outlined,missing,foreign)
            sheet.save(folder/"REVIEW_ORIGINAL_SOURCE_EGRET_COMPARE.png")
            total = sum(v["owner_backing_pixels"] for v in metrics.values())
            covered = sum(v["covered_backing_pixels"] for v in metrics.values())
            findings[method] = {
                "source_key": SOURCE, "native_renderer": overlay_meta["renderer"],
                "source_palette_size": len(selected),
                "nonwhite_colors_in_source": len(expected),
                "nonwhite_colors_actually_native_rendered": len(observed),
                "white_background_no_paint_required": True,
                "global_paint_strokes": len(paint),
                "global_outline_strokes": len(actual_contours),
                "total_real_Egret_strokes_NOT_CHALK": len(final),
                "total_synthetic_vertices_NOT_CHALK": sum(len(s["points"]) for s in final),
                "skipped_original_outline_strokes_due_renderer_budget":
                    len(contours)-len(actual_contours),
                "source_original_derived_outline_only": True,
                "source_owner_plan": plan,
                "per_owner_native_alpha24": metrics,
                "overall_owner_weighted_native_coverage": float(covered/total),
                "all_frozen_99_0protected_3logical_gates":
                    all(x["quality_frozen_gates"] for x in metrics.values()),
                "game_E4":"NOT_RUN", "independent_E5":"NOT_RUN",
                "exact_run_bound_CHALK":None, "production_promotion":False,
            }
            (folder/"METHOD_REPORT.json").write_text(
                json.dumps(findings[method],ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
            print("P4C0_NATIVE_RESULT",method,"colors",len(observed),"owner",
                  round(100*covered/total,3),"quality",
                  findings[method]["all_frozen_99_0protected_3logical_gates"],
                  "paint",len(paint),"outline",len(actual_contours),flush=True)
    members = {str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
               for p in sorted(output.rglob("*")) if p.is_file()}
    report = {
        "experiment":EXPERIMENT, "result":"DIAGNOSTIC_FULL_NATIVE_EF_AVAILABLE",
        "prereg":PREREG, "original_sha256":ORIGINAL_SHA,
        "renderer_git_blob": RENDERER_BLOB,
        "p4b1_planner_git_blob":P4B1_BLOB,
        "source_current_run_P3D":True,
        "source_C192_D_COMPONENT24_EF_only":True,
        "G32_V44_old_as_candidate":False,
        "methods":findings,
        "overall_paint_quality_pass":all(x["all_frozen_99_0protected_3logical_gates"]
                                          for x in findings.values()),
        "production_promotion":False, "game_E4":"NOT_RUN","E5":"NOT_RUN",
        "exact_CHALK":None, "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "members_sha256":members,
    }
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    (output/"README_REVIEW_RU.txt").write_text(
        "P4C0: ДИАГНОСТИКА полного исходного изображения. Два метода E/F.\n"
        "REAL_EGRET_PAINT_ONLY.png и REAL_EGRET_PAINT_AND_NEW_OUTLINE.png — "
        "оба настоящие Egret BoardPane/WebGL. Контур только из RGB и E/F source.\n"
        "REAL_EGRET_MISSING_ALPHA24.png / FOREIGN_ALPHA24.png основаны на "
        "нативных отдельных цветовых рендерах, не на Pillow proxy.\n"
        "Белый цвет #6 — белый холст; 32 цвета допустимы в исходной палитре, "
        "live выбор этих цветов E4 не проверен.\n"
        "Это не принятая заливка, CHALK не измерен, production не изменен.\n","utf8")
    print("P4C0_EF_COMPLETE",list(findings),flush=True)
    return report


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--engine-js",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    run(args.workspace,args.source,args.engine_js,args.renderer,args.output)
