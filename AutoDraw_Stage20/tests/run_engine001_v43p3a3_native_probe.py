#!/usr/bin/env python3
"""V43-P3a3 isolated native BoardPane width4/6/10/20/30; NOT fill replacement."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import SOURCE_SHA, sha
from run_engine001_native_wide_interior_v43p2a import largest_dark_component
from run_engine001_v43p3a2_width_audit import source_width_audit
from run_engine001_v43p3_oriented_source import SUPPORTED_WIDTHS

EXP="ENGINE001_V43P3A3_NATIVE_ORIENTED_FOOTPRINT"
ALPHA_THRESHOLDS=(24,128)
MAX_PROBES=3
COLOR=0x31262B


def make_probe_strokes(candidates, width):
    if width not in SUPPORTED_WIDTHS or candidates.get("width")!=width:
        raise ValueError("P3a3 source candidate width drift")
    choices=candidates["candidate_strokes"][:MAX_PROBES]
    if any(x["width"]!=width or len(x["points"])!=2 or
           x.get("safe_to_execute") is not False for x in choices):
        raise ValueError("P3a3 invalid frozen source path")
    return [{"strokeId":f"icon-{i}", "colorIndex":7,
             "colorRgb":COLOR,"width":width,
             "points":[dict(p) for p in old["points"]]}
            for i,old in enumerate(choices)]


def native_footprint_metrics(alpha, owner, component):
    if (alpha.shape!=(720,1380) or owner.shape!=(240,460)
            or component.shape!=owner.shape or component.dtype!=np.bool_):
        raise ValueError("P3a3 invalid native/mask raster scale")
    original_foreign=(owner!=7)
    outside_component=~component
    # Distance to nearest component pixel; 9 native px == 3 logical px.
    outside_distance=cv2.distanceTransform(
        np.repeat(np.repeat(outside_component.astype(np.uint8),3,axis=0),3,axis=1),
        cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    owned=np.repeat(np.repeat(owner==7,3,axis=0),3,axis=1)
    inside=np.repeat(np.repeat(component,3,axis=0),3,axis=1)
    results={}
    for threshold in ALPHA_THRESHOLDS:
        painted=alpha>=threshold
        results[str(threshold)]={
            "native_backing_ink_pixels":int(painted.sum()),
            "native_ink_inside_owner7":int((painted&owned).sum()),
            "native_ink_inside_largest_component":int((painted&inside).sum()),
            "native_ink_over_other_source_classes":int((painted &
                np.repeat(np.repeat(original_foreign,3,axis=0),3,axis=1)).sum()),
            "native_ink_outside_component_more_than_3logical_px":int(
                (painted & (outside_distance>9)).sum()),
            "largest_component_native_coverage_DIAGNOSTIC_ONLY":float(
                (painted & inside).sum()/max(int(inside.sum()),1)),
        }
    return results


def main():
    p=argparse.ArgumentParser()
    for name in ("workspace","source","output"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    if sha(a.source)!=SOURCE_SHA:
        raise ValueError("P3a3 source SHA mismatch")
    if a.output.exists():
        raise ValueError("P3a3 no overwrite")
    owner=original_labels(a.source)[::3,::3].copy()
    component,distance,meta=largest_dark_component(owner)
    if meta["component_area"]!=5005:
        raise ValueError("P3a3 source class7 component drift")
    proposals=source_width_audit(component,distance)
    output=a.output
    output.mkdir(parents=True)
    details={}
    for width in SUPPORTED_WIDTHS:
        strokes=make_probe_strokes(proposals[str(width)],width)
        report={"candidate_count_total":proposals[str(width)]["count"],
                "selected_paths":len(strokes),
                "selected_strokes":strokes,
                "synthetic_vertices_NOT_CHALK":2*len(strokes),
                "native_coverage":"NOT_RUN" if not strokes else "PENDING"}
        if not strokes:
            report["status"]="NO_ELIGIBLE_PATHS"
        else:
            folder=output/str(width)
            folder.mkdir()
            rgba, metadata,_=native_batch(a.workspace,f"V43P3a3-w{width}",
                strokes,folder,renderer_method="renderV43P3PaintBrushProbe")
            image=rgba["composite"]
            report["status"]="NATIVE_CAPTURED"
            report["native_metrics"]=native_footprint_metrics(
                image[:,:,3],owner,component)
            report["renderer_metadata"]=metadata
            report["native_alpha_color7_matches_composite"]=bool(
                np.array_equal(rgba["color-7"][:,:,3],image[:,:,3]))
            if not report["native_alpha_color7_matches_composite"]:
                raise ValueError("P3a3 isolated class alpha mismatch")
        details[str(width)]=report
    hashes={str(p.relative_to(output)).replace("\\","/"):sha(p)
            for p in output.rglob("*") if p.is_file()}
    summary={"experiment":EXP,"source_sha256":SOURCE_SHA,
             "class7_component":meta,"native_renderer":"archived Egret BoardPane WebGL",
             "source_candidate_provenance":"V43-P3a2",
             "widths":list(SUPPORTED_WIDTHS),"per_width":details,
             "report_linked_SHA256":hashes,"quality_accepted":False,
             "full_color_V44B_comparison":"NOT_RUN",
             "source_fill_paths_replaced":0,"V44B_410_outlines_modified":False,
             "game_exact_CHALK":None,"game_E4":"NOT_RUN","independent_E5":"NOT_RUN"}
    (output/"report.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:{"status":v["status"],"paths":v["selected_paths"]}
                      for k,v in details.items()},indent=2))


if __name__=="__main__":
    main()
