#!/usr/bin/env python3
"""ENGINE-001 S5-R1: bounded MODEL_ONLY proposals, not executor strokes.

Consumes an already independently verified S4.6 source contract's arrays.
All positions are source-pixel centers, NOT calibrated Egret coordinates.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import sys

import numpy as np

# Reuse the existing source/preparation footprint oracle; do not reproduce it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "preparation"))
from brush_footprint_geometry import swept_capsule_pixel_masks

VERSION = "ENGINE001_S5R1_MODEL_ONLY_V1"
DIRECTIONS = ((1., 0.), (0., 1.), (2 ** -0.5, 2 ** -0.5),
              (2 ** -0.5, -2 ** -0.5))


class BlockedS5(ValueError):
    pass


def _block(ok: bool, reason: str) -> None:
    if not ok:
        raise BlockedS5("BLOCKED_S5R1_" + reason)


def build_candidates(arrays: dict, *, max_strokes: int = 1000,
                     max_seed_trials: int = 5000, directions=DIRECTIONS) -> dict:
    """Make bounded, non-executable original-pixel proposals.

    Selection is exploratory: potential footprint is an upper-bound model;
    guarantee under-approximation is reported separately.
    """
    _block(isinstance(max_strokes, int) and not isinstance(max_strokes, bool)
           and 1 <= max_strokes <= 100000, "STROKE_BUDGET")
    _block(isinstance(max_seed_trials, int) and not isinstance(max_seed_trials, bool)
           and 1 <= max_seed_trials <= 2000000, "TRIAL_BUDGET")
    _block(isinstance(arrays, dict), "ARRAYS")
    for key in ("game_index", "paintable_id", "original_rgba", "protected_original_dot"):
        _block(key in arrays and isinstance(arrays[key], np.ndarray), "ARRAY_" + key)
    game, regions, rgba, protected = (arrays[key] for key in
        ("game_index", "paintable_id", "original_rgba", "protected_original_dot"))
    _block(game.ndim == regions.ndim == protected.ndim == 2, "DIMENSIONS")
    h, w = game.shape
    _block(h > 0 and w > 0 and regions.shape == protected.shape == (h, w)
           and rgba.shape == (h, w, 4), "SHAPE")
    _block(game.dtype == np.int16 and regions.dtype == np.int32
           and rgba.dtype == np.uint8 and protected.dtype == np.bool_, "DTYPE")
    opaque = rgba[:, :, 3] == 255
    _block(np.all((game[opaque] >= 0) & (game[opaque] < 128))
           and np.all(game[~opaque] == -1)
           and np.all(regions[opaque] > 0)
           and np.all(regions[~opaque] == 0)
           and not np.any(protected[~opaque]), "SOURCE_MAP")
    _block(isinstance(directions, (tuple, list)) and len(directions) > 0, "DIRECTIONS")
    unit_directions = []
    for direction in directions:
        _block(isinstance(direction, (tuple, list)) and len(direction) == 2,
               "DIRECTION_PAIR")
        try:
            dx, dy = float(direction[0]), float(direction[1])
        except (TypeError, ValueError):
            raise BlockedS5("BLOCKED_S5R1_DIRECTION_VALUE") from None
        norm = math.hypot(dx, dy)
        _block(math.isfinite(norm) and norm > 0, "DIRECTION_FINITE")
        unit_directions.append((dx / norm, dy / norm))
    # Stable y/x traversal; sampling budget is bounded and disclosed.
    covered_potential = np.zeros((h, w), dtype=bool)
    covered_guaranteed = np.zeros((h, w), dtype=bool)
    proposals = []
    trials = 0
    rejects = {"foreign_or_alpha_or_region": 0, "no_gain": 0}
    finished = False
    for y, x in zip(*np.nonzero(opaque)):
        if finished:
            break
        y, x = int(y), int(x)
        if covered_potential[y, x]:
            continue
        color, region = int(game[y, x]), int(regions[y, x])
        best = None
        # Longest candidates first for each width; width and gain dominate count.
        for width in range(10, 0, -1):
            for length in (12., 6., 2., 0.):
                for dx, dy in unit_directions:
                    if trials >= max_seed_trials:
                        finished = True
                        break
                    trials += 1
                    end_x, end_y = x + dx * length, y + dy * length
                    if not (0 <= end_x < w and 0 <= end_y < h):
                        continue
                    footprint = swept_capsule_pixel_masks(
                        ((float(x), float(y)), (end_x, end_y)), width,
                        1., 1., w, h)
                    potential = footprint["potential_cells"]
                    if not potential:
                        continue
                    if any(game[py, px] != color or regions[py, px] != region
                           or not opaque[py, px] for px, py in potential):
                        rejects["foreign_or_alpha_or_region"] += 1
                        continue
                    new_cells = [(px, py) for px, py in potential
                                 if not covered_potential[py, px]]
                    if not new_cells:
                        rejects["no_gain"] += 1
                        continue
                    score = (len(new_cells), width, length)
                    if best is None or score > best[0]:
                        best = (score, (end_x, end_y), footprint, width)
                if finished:
                    break
            if finished:
                break
        if best is None:
            continue
        _, end, footprint, width = best
        for px, py in footprint["potential_cells"]:
            covered_potential[py, px] = True
        for px, py in footprint["guaranteed_cells"]:
            covered_guaranteed[py, px] = True
        proposals.append({
            "color_index": color, "paintable_id": region, "brush_value": width,
            "points": [[float(x), float(y)], [float(end[0]), float(end[1])]],
            "safe_to_execute": False, "status": "MODEL_ONLY_NON_EXECUTABLE",
            "modeled_new_upper_bound_cells": best[0][0],
        })
        if len(proposals) >= max_strokes:
            finished = True
    visible = int(opaque.sum())
    output = {
        "schema": VERSION, "status": "PARTIAL" if finished else "MODEL_ONLY",
        "safe_to_execute": False, "admissible_for_gameplay": False,
        "source_owner_status": "MISSING", "native_calibration": "UNVERIFIED",
        "coordinates": "ORIGINAL_PIXEL_CENTERS_NOT_EGRET",
        "source_shape": [h, w],
        "trials": trials, "stroke_count": len(proposals),
        "visible_pixel_count": visible,
        "potential_covered_pixel_count": int(np.count_nonzero(covered_potential & opaque)),
        "guaranteed_covered_pixel_count": int(np.count_nonzero(covered_guaranteed & opaque)),
        "uncovered_potential_pixel_count": int(np.count_nonzero(opaque & ~covered_potential)),
        "rejected": rejects, "proposals": proposals,
    }
    output["result_sha256"] = hashlib.sha256(json.dumps(
        output, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    return output


def build_from_verified_s46(meta_bytes: bytes, raw_bytes: bytes,
                            original_bytes: bytes, **kwargs) -> dict:
    """Only provenance-bound S4.6 can enter the integrated S5 research path."""
    import engine001_bpred_s4r1_s46_source_contract as s46
    meta = s46.verify_quarantined(meta_bytes, raw_bytes, original_bytes)
    _block(meta.get("source_original_only") is True
           and meta.get("admissible_for_gameplay") is False
           and meta.get("source_owner_status") == "MISSING"
           and meta.get("native_calibration") == "UNVERIFIED",
           "S46_STATUS")
    with np.load(io.BytesIO(raw_bytes), allow_pickle=False) as src:
        arrays = {k: src[k] for k in
                  ("game_index", "paintable_id", "original_rgba",
                   "protected_original_dot")}
    result = build_candidates(arrays, **kwargs)
    result["input_sha256"] = meta["input_sha256"]
    result["engine_git_blob_sha1"] = meta["engine_git_blob_sha1"]
    result["s46_packet_sha256"] = hashlib.sha256(meta_bytes).hexdigest()
    result["s46_raw_sha256"] = meta["raw_npz_sha256"]
    result["result_sha256"] = hashlib.sha256(json.dumps(
        {k: v for k, v in result.items() if k != "result_sha256"},
        sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()
    return result
