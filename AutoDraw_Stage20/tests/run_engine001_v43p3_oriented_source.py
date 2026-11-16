#!/usr/bin/env python3
"""V43-P3a source-only oriented width4/6 candidate geometry, NEVER executor-ready.

Reuses V43-P1 source mask interpretation and P2a largest dark component.
No brush footprint, no original paint routes removed and NO CHALK inference.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np

from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import SOURCE_SHA, sha
from run_engine001_native_wide_interior_v43p2a import largest_dark_component
from run_engine001_shape_adaptive_fill_v43p1 import analyze_component

EXP = "ENGINE001_V43P3_ORIENTED_REPLACEMENT_P3A_MODEL_ONLY"
WIDTHS = (4, 6)
MIN_SPAN = 8
INTERIOR_MARGIN = 1.0


def oriented_source_candidates(mask, distance, width):
    """Deterministic PCA-oriented interior line candidates; no native-ink claims."""
    if (not isinstance(mask, np.ndarray) or mask.shape != (240, 460)
            or mask.dtype != np.bool_ or not np.any(mask)
            or not isinstance(distance, np.ndarray) or distance.shape != mask.shape
            or not np.issubdtype(distance.dtype, np.floating)
            or not np.isfinite(distance).all()
            or (distance < 0).any()):
        raise ValueError("V43P3 invalid source mask/distance")
    if width not in WIDTHS:
        raise ValueError("V43P3 unsupported candidate width")
    ys, xs = np.nonzero(mask)
    coords = np.column_stack((xs, ys)).astype(np.float64)
    center = coords.mean(axis=0)
    centered = coords - center
    cov = centered.T @ centered / len(coords)
    vals, vectors = np.linalg.eigh(cov)
    axis = vectors[:, 1]
    # Canonical sign is positive X (or positive Y for truly vertical).
    if axis[0] < -1e-12 or (abs(axis[0]) <= 1e-12 and axis[1] < 0):
        axis = -axis
    normal = np.array([-axis[1], axis[0]])
    projected_major = centered @ axis
    projected_minor = centered @ normal
    minor_min, minor_max = float(projected_minor.min()), float(projected_minor.max())
    major_min, major_max = float(projected_major.min()), float(projected_major.max())
    # Width-sized lanes and 1-pixel samples; no collision with contour geometry.
    lanes = np.arange(minor_min + width / 2.0, minor_max, float(width))
    lines = []
    for lane_id, lateral in enumerate(lanes):
        running = []
        def flush():
            if len(running) < MIN_SPAN + 1:
                return
            a, b = running[0], running[-1]
            if math.hypot(b[0]-a[0], b[1]-a[1]) < MIN_SPAN:
                return
            lines.append({"lane": lane_id, "width": width,
                          "points": [{"x": float(a[0]), "y": float(a[1])},
                                     {"x": float(b[0]), "y": float(b[1])}],
                          "sampled_centers": len(running),
                          "safe_to_execute": False})
        last = None
        for along in np.arange(math.floor(major_min), math.ceil(major_max)+1, 1.0):
            point = center + along * axis + lateral * normal
            x, y = int(round(point[0])), int(round(point[1]))
            good = (0 <= x < 460 and 0 <= y < 240 and bool(mask[y,x])
                    and float(distance[y,x]) >= width/2.0 + INTERIOR_MARGIN)
            if not good:
                flush()
                running = []
                last = None
            elif (x,y) != last:
                running.append((x,y))
                last = (x,y)
        flush()
    return {"width": width, "axis_xy": [float(axis[0]),float(axis[1])],
            "axis_angle_deg_mod180": float(math.degrees(math.atan2(axis[1],axis[0]))%180),
            "candidate_strokes": lines, "count": len(lines),
            "safe_to_execute": False,
            "evidence": "SOURCE_GEOMETRY_ONLY_NOT_NATIVE_BRUSH"}


def main():
    p=argparse.ArgumentParser()
    for name in ("source", "output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    if sha(a.source)!=SOURCE_SHA:
        raise ValueError("V43P3 original source SHA drift")
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V43P3 reject overwrite")
    labels = original_labels(a.source)[::3,::3].copy()
    mask, distance, component=largest_dark_component(labels)
    if component.get("component_area") != 5005:
        raise ValueError("V43P3 pinned largest dark source component drift")
    geom=analyze_component(mask,7,1)
    results={str(w):oriented_source_candidates(mask,distance,w) for w in WIDTHS}
    payload={"experiment":EXP,"source_sha256":SOURCE_SHA,
             "source_mask_sha256":hashlib.sha256(mask.tobytes()).hexdigest(),
             "target_color_index":7,"component":component,
             "component_shape":geom,"candidate_widths":list(WIDTHS),
             "min_span_logical_px":MIN_SPAN,"interior_margin":INTERIOR_MARGIN,
             "variants":results,"original_fill_routes_removed":0,
             "native_coverage":None,"exact_CHALK":None,
             "production_accepted":False,"safe_to_execute":False}
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/"oriented-candidates.json").write_text(
        json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({w:results[str(w)]["count"] for w in WIDTHS}))


if __name__=="__main__":
    main()
