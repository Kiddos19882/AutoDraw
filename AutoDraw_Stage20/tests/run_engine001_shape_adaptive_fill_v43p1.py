#!/usr/bin/env python3
"""ENGINE-001 V43/P1: source-color connected-component shape study ONLY.

No strokes are generated, no brush footprint is approximated, and no
native/game coverage or CHALK claims are made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "preparation"))
from skeletonization import thin_binary_mask
from run_engine001_native_color_boundary_audit_v38 import original_labels, sha

SOURCE_SHA = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
EXP = "ENGINE001_SHAPE_ADAPTIVE_FILL_V43_P1"
REQUIRED = (4, 5, 6, 7)
WIDE_INSCRIBED_RADIUS = 4.0
ORIENTATION_RATIO = 2.0
ORIENTATION_MIN_AREA = 16
SKELETON_MAX_AREA = 3000


def analyze_component(component: np.ndarray, owner: int, number: int) -> dict:
    """Classify connected source pixels, never output paint commands."""
    if not isinstance(component, np.ndarray) or component.ndim != 2 or component.dtype != np.bool_:
        raise ValueError("V43 component must be a 2-D bool mask")
    if component.shape[0] == 0 or component.shape[1] == 0 or not np.any(component):
        raise ValueError("V43 empty component")
    if owner not in REQUIRED or type(number) is not int or number < 1:
        raise ValueError("V43 invalid palette owner or component ID")
    ys, xs = np.nonzero(component)
    area = len(xs)
    width = int(xs.max() - xs.min() + 1)
    height = int(ys.max() - ys.min() + 1)
    if area > 36000:
        raise ValueError("V43 component exceeds frozen image bound")
    coords = np.column_stack((xs, ys)).astype(np.float64)
    if area > 1:
        centered = coords - coords.mean(axis=0)
        covariance = centered.T @ centered / area
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        major, minor = float(max(eigenvalues[1], 0)), float(max(eigenvalues[0], 0))
        vector = eigenvectors[:, 1]
        angle = (math.degrees(math.atan2(float(vector[1]), float(vector[0]))) + 180) % 180
    else:
        major = minor = angle = 0.0
    ratio = (major / minor if minor > 1e-10 else
             float("inf") if major > 1e-10 else 1.0)
    # Pad the component so distance to image border counts as an actual edge.
    padded = np.pad(component.astype(np.uint8), 1)
    distance = cv2.distanceTransform(padded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    radius = float(distance.max())
    orientable = area >= ORIENTATION_MIN_AREA and ratio >= ORIENTATION_RATIO
    role = ("wide_interior_candidate" if radius >= WIDE_INSCRIBED_RADIUS else
            "thin_shape_candidate" if radius < WIDE_INSCRIBED_RADIUS else
            "mixed_or_small_candidate")
    skeleton = ("SKIPPED_RESOURCE_BOUND" if area > SKELETON_MAX_AREA else
                int(np.count_nonzero(thin_binary_mask(component))))
    return {
        "owner_color_index": owner,
        "component_id": number,
        "area_source_px": area,
        "source_bbox_xywh": [int(xs.min()), int(ys.min()), width, height],
        "principal_axis_angle_deg_mod180": round(angle, 6),
        "major_variance": round(major, 6),
        "minor_variance": round(minor, 6),
        "anisotropy_ratio": None if not math.isfinite(ratio) else round(ratio, 6),
        "oriented_sweep_candidate": bool(orientable),
        "maximum_inscribed_radius_source_px": round(radius, 6),
        "role": role,
        "skeleton_pixels_or_status": skeleton,
        "native_footprint_validated": False,
        "safe_to_execute": False,
    }


def analyze_index_map(indexes: np.ndarray) -> dict:
    if not isinstance(indexes, np.ndarray) or indexes.shape != (240, 150):
        raise ValueError("V43 source index shape must be frozen 240x150")
    if indexes.dtype.kind not in "iu":
        raise ValueError("V43 labels must be integers")
    if any(int(v) not in range(8) for v in np.unique(indexes)):
        raise ValueError("V43 original source palette indices changed")
    all_components = []
    summary = {}
    for owner in REQUIRED:
        color_mask = (indexes == owner).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(color_mask, connectivity=8)
        collected = []
        for local_id in range(1, n):
            x, y, w, h, area = map(int, stats[local_id])
            isolated = labels[y:y+h, x:x+w] == local_id
            record = analyze_component(isolated, owner, local_id)
            record["source_bbox_xywh"] = [x, y, w, h]
            if record["area_source_px"] != area:
                raise ValueError("V43 component pixel count inconsistent")
            collected.append(record)
            all_components.append(record)
        area_total = sum(r["area_source_px"] for r in collected)
        if area_total != int(np.count_nonzero(color_mask)):
            raise ValueError("V43 source-class component coverage inconsistent")
        roles = Counter(r["role"] for r in collected)
        summary[str(owner)] = {
            "source_class_pixels": area_total,
            "component_count": len(collected),
            "candidate_roles": dict(sorted(roles.items())),
            "oriented_component_count": sum(r["oriented_sweep_candidate"] for r in collected),
            "wide_component_area_source_pixels": sum(
                r["area_source_px"] for r in collected if r["role"] == "wide_interior_candidate"),
            "max_component_area_source_pixels": max(
                (r["area_source_px"] for r in collected), default=0),
        }
    if sum(s["source_class_pixels"] for s in summary.values()) != int(
            np.count_nonzero(np.isin(indexes, REQUIRED))):
        raise ValueError("V43 source-target color classes not fully accounted")
    return {"per_color": summary, "components": all_components,
            "target_source_pixels": int(np.count_nonzero(np.isin(indexes, REQUIRED)))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V43 no overwrite of evidence")
    if sha(a.source) != SOURCE_SHA:
        raise ValueError("V43 frozen original source SHA drift")
    # Exact existing source quantization; no reimplemented ROI/palette.
    indexes = original_labels(a.source)[::3, ::3][:, 155:305].copy()
    result = analyze_index_map(indexes)
    a.output.mkdir(parents=True, exist_ok=False)
    report = {
        "experiment": EXP,
        "evidence_level": "E2_MODEL_ONLY",
        "source_sha256": SOURCE_SHA,
        "source_labels_sha256": hashlib.sha256(
            indexes.tobytes()).hexdigest(),
        "roi_shape_hw": [240, 150],
        "source_label_method": "frozen MEDIANCUT8 LANCZOS original_labels reuse",
        "selection_thresholds": {
            "wide_inscribed_radius": WIDE_INSCRIBED_RADIUS,
            "oriented_variance_ratio": ORIENTATION_RATIO,
            "oriented_min_area": ORIENTATION_MIN_AREA,
            "skeleton_max_area": SKELETON_MAX_AREA,
        },
        **result,
        "all_410_V35B_final_outlines_must_be_preserved_in_P2": True,
        "allowed_internal_color_overlap_logical_px": 3,
        "synthetic_game_cost": None,
        "native_quality": "NOT_RUN",
        "game_exact_CHALK": None,
        "production_accepted": False,
        "not_tested": ["actual Egret variable-width fill",
                        "3px native internal/external overlap for generated strokes",
                        "source RGB MAE of generated strokes",
                        "game E4", "independent E5", "exact CHALK"],
        "versions": {"Python": platform.python_version(),
                     "numpy": np.__version__, "OpenCV": cv2.__version__},
    }
    output = a.output / "component-shape-analysis.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({
        "total_color_target_pixels": result["target_source_pixels"],
        "per_color": result["per_color"], "native_quality": "NOT_RUN",
    }, indent=2))


if __name__ == "__main__":
    main()
