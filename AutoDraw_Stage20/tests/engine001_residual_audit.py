#!/usr/bin/env python3
"""ENGINE-001 fixed-pixel residual audit (offline E3; never changes acceptance)."""
from __future__ import annotations
import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image

FIGURES = ("c001-f001", "c001-f002", "c001-f003", "c002-f001", "c002-f002", "c002-f003")
RECOVERED = frozenset(("c001-f003", "c002-f002"))
RGB_THRESHOLD = 24  # Existing DEC-025, not fitted.
ALPHA_THRESHOLD = 24  # Existing native replay, not fitted.
EDGE_RADIUS = 2  # Diagnostic only, 4-connected fixed pixels.


def image_array(data: bytes, mode: str) -> np.ndarray:
    with Image.open(BytesIO(data)) as img:
        return np.asarray(img.convert(mode))


def masks(before: bytes, after: bytes, projected: bytes) -> tuple[np.ndarray, np.ndarray]:
    b = image_array(before, "RGB").astype(np.int16)
    a = image_array(after, "RGB").astype(np.int16)
    m = image_array(projected, "RGBA")
    if b.shape != a.shape or b.shape[:2] != m.shape[:2] or b.shape[:2] != (363, 694):
        raise ValueError("Only pinned 694x363 native-ROI images are supported")
    return np.max(np.abs(a - b), axis=2) > RGB_THRESHOLD, m[:, :, 3] >= ALPHA_THRESHOLD


def edge(mask: np.ndarray) -> np.ndarray:
    """4-connected boundary, with exterior treated as background."""
    p = np.pad(mask, 1, constant_values=False)
    h, w = mask.shape
    return ((mask != p[:h, 1:w+1]) | (mask != p[2:h+2, 1:w+1]) |
            (mask != p[1:h+1, :w]) | (mask != p[1:h+1, 2:w+2]))


def expand_4(mask: np.ndarray, steps: int) -> np.ndarray:
    result = mask.copy()
    for _ in range(steps):
        p = np.pad(result, 1, constant_values=False)
        h, w = result.shape
        result |= p[:h, 1:w+1] | p[2:h+2, 1:w+1] | p[1:h+1, :w] | p[1:h+1, 2:w+2]
    return result


def tiles(mask: np.ndarray) -> list[list[int]]:
    """No post-hoc region fitting: fixed regular 3x3 full-ROI partition."""
    ys = np.linspace(0, mask.shape[0], 4, dtype=int)
    xs = np.linspace(0, mask.shape[1], 4, dtype=int)
    return [[int(mask[ys[y]:ys[y+1], xs[x]:xs[x+1]].sum())
             for x in range(3)] for y in range(3)]


def residual(live: np.ndarray, model: np.ndarray) -> dict:
    if live.shape != model.shape or live.dtype != np.bool_ or model.dtype != np.bool_:
        raise ValueError("Incompatible binary masks")
    live_only, model_only = live & ~model, model & ~live
    mismatch = live_only | model_only
    near = expand_4(edge(live) | edge(model), EDGE_RADIUS) & mismatch
    far = mismatch & ~near
    return {
        "live_pixels": int(live.sum()), "model_pixels": int(model.sum()),
        "true_positive": int((live & model).sum()),
        "live_only": int(live_only.sum()), "model_only": int(model_only.sum()),
        "residual_total": int(mismatch.sum()), "near_boundary_2px": int(near.sum()),
        "far_from_boundary_2px": int(far.sum()),
        "live_only_tiles_3x3": tiles(live_only), "model_only_tiles_3x3": tiles(model_only),
        "far_tiles_3x3": tiles(far),
    }


def analyze(original: Path, recovered: Path) -> dict:
    files = ("game-before.png", "game-after.png", "egret-screen-projected.png",
             "native-stage-webgl.png")
    for label, root in (("original", original), ("recovered", recovered)):
        if not root.is_dir() or any(not (root / fig / name).is_file()
                                    for fig in FIGURES for name in (*files, "result.json")):
            raise ValueError(f"{label}: incomplete six-figure replay artifact")
    cases = []
    for fig in FIGURES:
        paths = (original / fig, recovered / fig)
        meta = [json.loads((p / "result.json").read_text(encoding="utf-8")) for p in paths]
        for k in ("figure", "monitor_sha", "run_id", "exact_chalk"):
            if meta[0].get(k) != meta[1].get(k):
                raise ValueError(f"{fig}: inconsistent {k}")
        n = 1 if fig in RECOVERED else 0
        if meta[0].get("figure") != fig or meta[0].get("recovered_coordinate_count") != 0 or meta[1].get("recovered_coordinate_count") != n:
            raise ValueError(f"{fig}: invalid quota provenance")
        png = [{name: (p / name).read_bytes() for name in files} for p in paths]
        if any(png[0][name] != png[1][name] for name in files[:2]):
            raise ValueError(f"{fig}: original live game screenshots differ")
        pair = [masks(x["game-before.png"], x["game-after.png"],
                      x["egret-screen-projected.png"]) for x in png]
        if not np.array_equal(pair[0][0], pair[1][0]):
            raise ValueError(f"{fig}: changed live mask")
        scores = [residual(*m) for m in pair]
        for score, m in zip(scores, meta):
            for k in ("true_positive", "live_only", "model_only"):
                if score[k] != m.get("comparison", {}).get(k):
                    raise ValueError(f"{fig}: replay comparison score mismatch {k}")
        stage = [image_array(x["native-stage-webgl.png"], "RGBA") for x in png]
        proj = [image_array(x["egret-screen-projected.png"], "RGBA") for x in png]
        stage_changed = int(np.count_nonzero(np.any(stage[0] != stage[1], axis=2)))
        projected_changed = int(np.count_nonzero(np.any(proj[0] != proj[1], axis=2)))
        if not n and (stage_changed or projected_changed):
            raise ValueError(f"{fig}: non-target control changed")
        cases.append({
            "figure": fig, "run_id": meta[0]["run_id"], "monitor_sha": meta[0]["monitor_sha"],
            "historical_exact_chalk": meta[0]["exact_chalk"],
            "quota_restored_points": n,
            "original": scores[0], "quota_recovered": scores[1],
            "delta_recovered_minus_original": {
                "residual_total": scores[1]["residual_total"] - scores[0]["residual_total"],
                "residual_far": scores[1]["far_from_boundary_2px"] - scores[0]["far_from_boundary_2px"],
                "live_only": scores[1]["live_only"] - scores[0]["live_only"],
                "model_only": scores[1]["model_only"] - scores[0]["model_only"],
                "alpha_mask_changed_pixels": int(np.count_nonzero(pair[0][1] ^ pair[1][1])),
                "stage_rgba_changed_pixels": stage_changed,
                "projected_rgba_changed_pixels": projected_changed,
            },
            "original_projected_sha256": hashlib.sha256(png[0]["egret-screen-projected.png"]).hexdigest(),
            "recovered_projected_sha256": hashlib.sha256(png[1]["egret-screen-projected.png"]).hexdigest(),
        })
    return {
        "schema": "ENGINE001_FIXED_RESIDUAL_AUDIT_V1",
        "status": "DIAGNOSTIC_ONLY_NO_PIXEL_ACCEPTANCE",
        "parameters": {
            "source_cases": list(FIGURES), "live_rgb_threshold": RGB_THRESHOLD,
            "model_alpha_threshold": ALPHA_THRESHOLD,
            "boundary": "4-connected union of live and model mask edges",
            "boundary_distance_pixels": EDGE_RADIUS,
            "partition": "fixed regular 3x3 ROI tiles",
            "posthoc_projection_or_threshold_fit": False,
        },
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-dir", required=True, type=Path)
    parser.add_argument("--recovered-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = analyze(args.original_dir, args.recovered_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in result["cases"]:
        print(item["figure"], "original residual", item["original"]["residual_total"],
              "far", item["original"]["far_from_boundary_2px"],
              "recovered residual", item["quota_recovered"]["residual_total"],
              "far", item["quota_recovered"]["far_from_boundary_2px"])


if __name__ == "__main__":
    main()
