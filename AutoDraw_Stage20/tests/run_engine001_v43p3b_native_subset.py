#!/usr/bin/env python3
"""ENGINE-001 V43-P3b/P0: native old-stroke subset feasibility, never delete routes.

Pinned P3a3 grouped actual Egret class7 PNG is the candidate footprint.
Each eligible original width2 stroke is replayed ALONE on actual Egret WebGL.
No whole-image composite, CHALK or execution-ready plan is produced.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_boundary_shift_native_v39 import verified_input
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import SOURCE_SHA, sha
from run_engine001_native_wide_interior_v43p2a import largest_dark_component

EXP = "ENGINE001_V43P3B_P0_NATIVE_OLD_STROKE_SUBSET"
P3A3_EXP = "ENGINE001_V43P3A3_NATIVE_ORIENTED_FOOTPRINT"
WIDTHS = (4, 6, 10)
ALPHAS = (24, 128)
MAX_SAMPLE_PER_WIDTH = 12
P3A3_ARTIFACT_ZIP_SHA256 = "4565925cead78a67a993a0b4629a457d9f3d6f5bcea230a1baa91e33b817faa6"


def load_p3a3(folder: Path, source_sha: str):
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    if (report.get("experiment") != P3A3_EXP or
            report.get("source_sha256") != source_sha or
            list(report.get("per_width", {})) != ["4","6","10","20","30"] or
            report.get("source_fill_paths_replaced") != 0 or
            report.get("V44B_410_outlines_modified") is not False or
            report.get("game_exact_CHALK") is not None):
        raise ValueError("P3b P3a3 frozen native report mismatch")
    hashes = report.get("report_linked_SHA256")
    if not isinstance(hashes, dict) or len(hashes) != 6:
        raise ValueError("P3b native P3a3 manifest count drift")
    for name, digest in hashes.items():
        relative = Path(name)
        if (relative.is_absolute() or ".." in relative.parts or
                len(digest) != 64 or not (folder / relative).is_file() or
                sha(folder / relative) != digest):
            raise ValueError("P3b P3a3 archive SHA invalid: " + name)
    masks = {}
    for width in WIDTHS:
        row = report["per_width"][str(width)]
        if (row.get("status") != "NATIVE_CAPTURED" or
                row.get("selected_paths") != 3 or
                len(row.get("selected_strokes", [])) != 3):
            raise ValueError("P3b P3a3 width native identity changed")
        for threshold in ALPHAS:
            m = row["native_metrics"][str(threshold)]
            if (m["native_foreign_required_color_more_than_3logical_px"] != 0 or
                    m["native_exterior_silhouette_more_than_3logical_px"] != 0):
                raise ValueError("P3b unsafe archived native candidate")
        p = folder / str(width) / f"V43P3a3-w{width}-color-7.png"
        with Image.open(p) as im:
            image = np.asarray(im.convert("RGBA")).copy()
        if image.shape != (720, 1380, 4):
            raise ValueError("P3b non-Egret candidate raster size")
        masks[width] = image[:, :, 3]
    return report, masks


def select_old_strokes(base: dict, component: np.ndarray,
                       native_candidate_alpha: np.ndarray):
    """Bounded whole-span source prefilter, NOT an actual footprint test."""
    if (component.shape != (240, 460) or component.dtype != np.bool_ or
            native_candidate_alpha.shape != (720, 1380)):
        raise ValueError("P3b invalid original source/native geometry")
    yy, xx = np.nonzero(native_candidate_alpha >= 24)
    if not len(xx):
        return [], {"status": "NO_CANDIDATE_INK", "eligible_total": 0}
    xmin, xmax, ymin, ymax = int(xx.min() // 3), int(xx.max() // 3), int(yy.min() // 3), int(yy.max() // 3)
    eligible = []
    for entry in base["strokes"][:1945]:
        s = entry["stroke"]
        if s["colorIndex"] != 7:
            continue
        a, b = s["points"]
        if s["width"] != 2 or a["y"] != b["y"]:
            raise ValueError("P3b original dark paint changed")
        x0,x1,y = a["x"],b["x"],a["y"]
        if not (155 <= x0 <= x1 < 305 and y == round(y) and 0 <= y < 240):
            raise ValueError("P3b original dark coordinates invalid")
        if not (xmin <= x0 <= x1 <= xmax and ymin <= y <= ymax):
            continue
        iy = int(y)
        if np.any(component[iy, int(x0):int(x1)+1]):
            eligible.append(s)
    return eligible[:MAX_SAMPLE_PER_WIDTH], {
        "status": "BOUNDED_SOURCE_SELECTION", "eligible_total": len(eligible),
        "sampled": min(len(eligible), MAX_SAMPLE_PER_WIDTH),
        "unsampled_eligible": max(0, len(eligible)-MAX_SAMPLE_PER_WIDTH),
        "native_ink_logical_bbox_inclusive": [xmin,ymin,xmax,ymax],
    }


def subset_result(old_alpha: np.ndarray, candidate_alpha: np.ndarray,
                  original_owner: np.ndarray):
    if (old_alpha.shape != (720,1380) or
            candidate_alpha.shape != old_alpha.shape or
            original_owner.shape != (240,460)):
        raise ValueError("P3b native subset raster shape drift")
    owned = np.repeat(np.repeat(original_owner == 7, 3, axis=0), 3, axis=1)
    result = {}
    for t in ALPHAS:
        old_ink = old_alpha >= t
        replacement = candidate_alpha >= t
        required = old_ink & owned
        uncovered = required & ~replacement
        result[str(t)] = {
            "old_native_ink_backing_pixels": int(old_ink.sum()),
            "old_own_class_ink_pixels": int(required.sum()),
            "old_foreign_class_or_background_ink_pixels": int((old_ink&~owned).sum()),
            "own_class_pixels_not_replaced": int(uncovered.sum()),
            "source_owner_subset": bool(required.any() and not uncovered.any()),
        }
    return {"alpha_thresholds": result,
            "potential_replacement_ONLY": all(
                result[str(t)]["source_owner_subset"] for t in ALPHAS)}


def main():
    p=argparse.ArgumentParser()
    for name in ("workspace","source","v37p2-archive","p3a3-archive","output"):
        p.add_argument("--"+name,required=True,type=Path)
    args=p.parse_args()
    if sha(args.source)!=SOURCE_SHA:
        raise ValueError("P3b source SHA drift")
    if args.output.exists():
        raise ValueError("P3b refuse overwrite of evidence")
    base=verified_input(args.v37p2_archive)
    p3a3, candidate_masks=load_p3a3(args.p3a3_archive,SOURCE_SHA)
    owner=original_labels(args.source)[::3,::3].copy()
    component,_,meta=largest_dark_component(owner)
    if meta["component_area"]!=5005:
        raise ValueError("P3b pinned source component drift")
    args.output.mkdir(parents=True)
    records={}
    total_captures=0
    for width in WIDTHS:
        native_alpha=candidate_masks[width]
        selected,selection=select_old_strokes(base,component,native_alpha)
        details=[]
        for i,old in enumerate(selected):
            folder=args.output/str(width)/f"old-{i:02d}"
            folder.mkdir(parents=True)
            native,_,_=native_batch(args.workspace,f"V43P3b-w{width}-old-{i:02d}",
                [old],folder,renderer_method="renderComplexHoldoutColorProbe")
            if not np.array_equal(native["color-7"][:,:,3],native["composite"][:,:,3]):
                raise ValueError("P3b old isolated Egret alpha differs from composite")
            result=subset_result(native["color-7"][:,:,3],native_alpha,owner)
            result.update({"original_stroke_id":old["strokeId"],
                           "original_points":old["points"],
                           "source_color_index":old["colorIndex"],
                           "original_width":old["width"]})
            details.append(result)
            total_captures+=1
        replaceable=[x["original_stroke_id"] for x in details
                     if x["potential_replacement_ONLY"]]
        counts={"candidate_new_oriented_paths":3,
                "old_whole_strokes_potentially_removable_in_SAMPLE":len(replaceable),
                "potential_net_stroke_savings_SAMPLE_ONLY":len(replaceable)-3,
                "potential_net_synthetic_vertices_savings_SAMPLE_ONLY":2*(len(replaceable)-3)}
        records[str(width)]={"selection":selection,"old_stroke_evidence":details,
                             "potential_replacement_ids_SAMPLE_ONLY":replaceable,
                             "resource_proxy_SAMPLE_ONLY":counts,
                             "status": ("NO_SAMPLE" if not selected else
                                        "POTENTIAL_SAVINGS_SAMPLE_ONLY" if len(replaceable)>3
                                        else "NO_NET_SAVINGS_SAMPLE")}
    if total_captures == 0:
        raise ValueError("P3b NO_NATIVE_OLD_STROKE_SAMPLE")
    hashes={str(file.relative_to(args.output)).replace("\\","/"):sha(file)
            for file in args.output.rglob("*") if file.is_file()}
    report={"experiment":EXP,"status":"NATIVE_OLD_STROKE_SAMPLE_DIAGNOSTIC",
            "source_sha256":SOURCE_SHA,
            "p3a3_artifact_id":14224453656,
            "p3a3_original_zip_sha256":P3A3_ARTIFACT_ZIP_SHA256,
            "p3a3_manifest_sha256":p3a3["report_linked_SHA256"],
            "v37p2_baseline":"verified_input V37-P2-C",
            "largest_source_class7_component":meta,
            "native_single_old_strokes_rendered":total_captures,
            "per_width":records,"report_linked_SHA256":hashes,
            "source_original_paint_strokes_deleted":0,
            "new_oriented_strokes_added_to_full_plan":0,
            "original_V44B_410_detail_modified":False,
            "whole_image_RGB_and_visual":"NOT_RUN",
            "game_exact_CHALK":None,"game_E4":"NOT_RUN",
            "production_accepted":False}
    (args.output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps({w:{"sampled":len(v["old_stroke_evidence"]),
                          "potential_removable":len(v["potential_replacement_ids_SAMPLE_ONLY"]),
                          "status":v["status"]}
                      for w,v in records.items()},indent=2))


if __name__=="__main__":
    main()
