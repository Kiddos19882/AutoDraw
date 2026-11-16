#!/usr/bin/env python3
"""V43-P3a2 independent output: audit 4/6/10/20/30 source-only widths.

No native brush footprint and no original strokes replaced.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math

import numpy as np
from pathlib import Path

from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import SOURCE_SHA, sha
from run_engine001_native_wide_interior_v43p2a import largest_dark_component
from run_engine001_v43p3_oriented_source import (
    oriented_source_candidates, SUPPORTED_WIDTHS, MIN_SPAN, INTERIOR_MARGIN,
)

EXP = "ENGINE001_V43P3A2_BROAD_BRUSH_SOURCE_AUDIT"


def sample_source_segment(mask, distance, points, width):
    """Additional 0.25-logical-px centerline audit; still NOT native ink."""
    if (mask.shape != (240, 460) or distance.shape != mask.shape
            or width not in SUPPORTED_WIDTHS or len(points) != 2):
        raise ValueError("P3a2 invalid segment diagnostic input")
    p, q = points
    x0, y0 = float(p["x"]), float(p["y"])
    x1, y1 = float(q["x"]), float(q["y"])
    if not all(math.isfinite(v) for v in (x0,y0,x1,y1)):
        raise ValueError("P3a2 nonfinite source line")
    length = math.hypot(x1-x0,y1-y0)
    subdivisions = max(1, math.ceil(length*4))
    outside = near_border = 0
    for i in range(subdivisions+1):
        t=i/subdivisions
        x=int(round(x0+(x1-x0)*t))
        y=int(round(y0+(y1-y0)*t))
        if not (0<=x<460 and 0<=y<240) or not mask[y,x]:
            outside+=1
        elif float(distance[y,x]) < width/2.0 + INTERIOR_MARGIN:
            near_border+=1
    return {"centerline_samples":subdivisions+1,
            "source_owner_violations": outside,
            "interior_margin_violations":near_border,
            "proof_type":"SOURCE_CENTERLINE_ONLY_NOT_EGRET_FOOTPRINT"}


def source_width_audit(mask, distance):
    """Call existing candidate engine; change width variable only."""
    variants = {}
    for width in SUPPORTED_WIDTHS:
        candidate = oriented_source_candidates(mask, distance, width)
        if candidate["safe_to_execute"] is not False:
            raise ValueError("P3a2 source-only safety changed")
        # Append diagnostics; do NOT filter or alter frozen P3a route geometry.
        unsafe = 0
        for path in candidate["candidate_strokes"]:
            audit = sample_source_segment(mask, distance, path["points"], width)
            path["additional_source_centerline_audit"] = audit
            unsafe += bool(audit["source_owner_violations"]
                           or audit["interior_margin_violations"])
        candidate["source_centerline_flagged_paths"] = unsafe
        candidate["native_footprint_validated"] = False
        variants[str(width)] = candidate
    return variants


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    if sha(a.source) != SOURCE_SHA:
        raise ValueError("P3a2 source image SHA drift")
    if a.output.exists():
        raise ValueError("P3a2 no overwrite of outputs")
    labels = original_labels(a.source)[::3, ::3].copy()
    mask, distance, component = largest_dark_component(labels)
    if component["component_area"] != 5005:
        raise ValueError("P3a2 frozen component drift")
    candidates = source_width_audit(mask, distance)
    if list(map(int, candidates)) != list(SUPPORTED_WIDTHS):
        raise ValueError("P3a2 width audit drift")
    payload = {
        "experiment": EXP,
        "evidence_level": "E2_MODEL_ONLY",
        "source_sha256": SOURCE_SHA,
        "source_mask_sha256": hashlib.sha256(mask.tobytes()).hexdigest(),
        "component": component,
        "brush_width_candidates_logical": list(SUPPORTED_WIDTHS),
        "min_span_logical_px": MIN_SPAN,
        "interior_margin_logical_px": INTERIOR_MARGIN,
        "variants": candidates,
        "original_fill_routes_removed": 0,
        "original_V44B_outline_changed": False,
        "native_round_brush_footprint_validated": False,
        "native_coverage": None,
        "exact_CHALK": None,
        "safe_to_execute": False,
    }
    a.output.mkdir(parents=True)
    (a.output / "width-candidates.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    print(json.dumps({str(w): candidates[str(w)]["count"] for w in SUPPORTED_WIDTHS}))


if __name__ == "__main__":
    main()
