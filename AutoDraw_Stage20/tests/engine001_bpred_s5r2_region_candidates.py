#!/usr/bin/env python3
"""ENGINE-001 S5-R2: region-first MODEL_ONLY research, never executable.

Uses the existing swept_capsule_pixel_masks oracle and S4.6 provenance.
All points remain original-pixel centers. DEC-052: smooth=false always.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "preparation"))
from brush_footprint_geometry import swept_capsule_pixel_masks

VERSION = "ENGINE001_BPRED_S5R2_REGION_FIRST_MODEL_ONLY_V1"
DIRECTIONS = ((1., 0.), (0., 1.), (math.sqrt(.5), math.sqrt(.5)),
              (math.sqrt(.5), -math.sqrt(.5)))


class BlockedS5R2(ValueError):
    pass


def check(ok, name):
    if not ok:
        raise BlockedS5R2("BLOCKED_S5R2_" + name)


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _source_arrays(arrays):
    check(isinstance(arrays, dict), "ARRAYS")
    for key in ("game_index", "paintable_id", "original_rgba", "protected_original_dot"):
        check(isinstance(arrays.get(key), np.ndarray), "MISSING_" + key)
    game, ids, rgba, protected = (arrays[x] for x in
        ("game_index", "paintable_id", "original_rgba", "protected_original_dot"))
    check(game.ndim == 2 and ids.shape == protected.shape == game.shape and
          rgba.shape == (*game.shape, 4), "SHAPE")
    check(game.dtype == np.int16 and ids.dtype == np.int32 and
          rgba.dtype == np.uint8 and protected.dtype == np.bool_, "DTYPE")
    check(min(game.shape) > 0 and game.size <= 16_000_000, "SIZE")
    opaque = rgba[..., 3] == 255
    check(np.all((game[opaque] >= 0) & (game[opaque] < 128)) and
          np.all(game[~opaque] == -1) and np.all(ids[opaque] > 0) and
          np.all(ids[~opaque] == 0) and not np.any(protected[~opaque]),
          "SOURCE_INVARIANTS")
    if opaque.any():
        max_id = int(ids.max())
        check(max_id <= game.size, "UNBOUNDED_REGION_ID")
        lo = np.full(max_id + 1, 128, np.int16)
        hi = np.full(max_id + 1, -1, np.int16)
        np.minimum.at(lo, ids[opaque], game[opaque])
        np.maximum.at(hi, ids[opaque], game[opaque])
        sizes = np.bincount(ids[opaque], minlength=max_id + 1)
        check(np.all(lo[sizes > 0] == hi[sizes > 0]), "MIXED_REGION_SWATCH")
    return game, ids, rgba, protected, opaque


def _priority_seeds(ids, opaque, protected):
    """One source-aware interior maximum per region, with dot priority."""
    h, w = ids.shape
    max_id = int(ids.max())
    if not max_id:
        return [], 0
    border = np.zeros((h, w), dtype=bool)
    border[0] = True
    border[-1] = True
    border[:, 0] = True
    border[:, -1] = True
    different_h = ids[:, 1:] != ids[:, :-1]
    different_v = ids[1:, :] != ids[:-1, :]
    border[:, 1:] |= different_h
    border[:, :-1] |= different_h
    border[1:, :] |= different_v
    border[:-1, :] |= different_v
    border |= ~opaque
    clearance = ndimage.distance_transform_edt(~border)
    py, px = np.nonzero(opaque)
    labels = ids[py, px]
    counts = np.bincount(labels, minlength=max_id + 1)
    maximum = np.zeros(max_id + 1, dtype=np.float64)
    np.maximum.at(maximum, labels, clearance[py, px])
    candidate_pixels = opaque & (clearance >= maximum[ids] - 1e-9)
    cy, cx = np.nonzero(candidate_pixels)
    unique, first = np.unique(ids[cy, cx], return_index=True)
    locations = {int(region): (int(cx[pos]), int(cy[pos]))
                 for region, pos in zip(unique, first)}
    dy, dx = np.nonzero(protected)
    dot_regions, dot_first = np.unique(ids[dy, dx], return_index=True)
    dots = {int(region): (int(dx[pos]), int(dy[pos]))
            for region, pos in zip(dot_regions, dot_first)}
    ordered = sorted(locations, key=lambda region: (region not in dots,
                        -int(counts[region]), region))
    return [(region, locations[region], dots.get(region), int(counts[region]),
             float(maximum[region])) for region in ordered], int(protected.sum())


def build_region_candidates(arrays, *, max_strokes=200, max_trials=2000):
    check(isinstance(max_strokes, int) and not isinstance(max_strokes, bool)
          and 1 <= max_strokes <= 100000, "STROKE_LIMIT")
    check(isinstance(max_trials, int) and not isinstance(max_trials, bool)
          and 1 <= max_trials <= 2000000, "TRIAL_LIMIT")
    game, ids, rgba, protected, opaque = _source_arrays(arrays)
    h, w = game.shape
    seeds, dot_count = _priority_seeds(ids, opaque, protected)
    covered = np.zeros((h,w), dtype=bool)
    guaranteed = np.zeros((h,w), dtype=bool)
    proposals = []
    trials = 0
    visited = set()
    rejected = {"foreign_or_alpha_or_region": 0, "no_new_cells": 0}
    targeted_dot_count = 0

    def offer(region, start, brush, end):
        nonlocal trials
        if trials >= max_trials:
            return None
        trials += 1
        footprint = swept_capsule_pixel_masks((start,end),brush,1.,1.,w,h)
        potential = footprint["potential_cells"]
        if not potential or any(ids[y,x] != region or not opaque[y,x]
                                for x,y in potential):
            rejected["foreign_or_alpha_or_region"] += 1
            return None
        gained = sum(not covered[y,x] for x,y in potential)
        if not gained:
            rejected["no_new_cells"] += 1
            return None
        return (gained, len(footprint["guaranteed_cells"]), brush,
                math.hypot(end[0]-start[0],end[1]-start[1])), footprint

    def accept(region, color, start, end, brush, footprint):
        new_critical = sum(protected[y,x] and not covered[y,x]
                           for x,y in footprint["potential_cells"])
        for x,y in footprint["potential_cells"]:
            covered[y,x] = True
        for x,y in footprint["guaranteed_cells"]:
            guaranteed[y,x] = True
        proposals.append({"paintable_id":region, "color_index":color,
            "brush_value":brush, "points":[list(map(float,start)),list(map(float,end))],
            "drawing_mode":"normal", "smooth":False,
            "status":"MODEL_ONLY_NON_EXECUTABLE", "safe_to_execute":False,
            "modeled_protected_dots_newly_touched":int(new_critical)})

    for region, center, dot, area, clearance in seeds:
        if trials >= max_trials or len(proposals) >= max_strokes:
            break
        visited.add(region)
        color = int(game[center[1],center[0]])
        # Fragile source details receive an explicit width-1 candidate first.
        if dot and not covered[dot[1], dot[0]]:
            trial = offer(region, dot, 1, dot)
            targeted_dot_count += 1
            if trial is not None:
                accept(region, color, dot, dot, 1, trial[1])
            if trials >= max_trials or len(proposals) >= max_strokes:
                break
        # Clearance is a proposal heuristic; complete potential mask is gate.
        preferred = min(10, max(1, int(2 * max(0., clearance - .7))))
        widths = tuple(dict.fromkeys((preferred, max(1, preferred // 2), 1)))
        best = None
        for brush in widths:
            for dx,dy in DIRECTIONS:
                for length in (12.,6.,2.,0.):
                    if trials >= max_trials:
                        break
                    end = (center[0]+dx*length,center[1]+dy*length)
                    if not (0 <= end[0] < w and 0 <= end[1] < h):
                        continue
                    outcome = offer(region,center,brush,end)
                    if outcome is not None:
                        score,footprint = outcome
                        if best is None or score > best[0]:
                            best = (score,center,end,brush,footprint)
                if trials >= max_trials:
                    break
            if trials >= max_trials:
                break
        if best is not None and len(proposals) < max_strokes:
            _,start,end,brush,footprint = best
            accept(region,color,start,end,brush,footprint)

    remaining = int(np.count_nonzero(opaque & ~covered))
    result = {"schema":VERSION,"status":"PARTIAL" if remaining else "MODEL_ONLY",
        "source_shape":[h,w],"drawing_mode":"normal","smooth":False,
        "safe_to_execute":False,"admissible_for_gameplay":False,
        "source_owner_status":"MISSING","native_calibration":"UNVERIFIED",
        "coordinates":"ORIGINAL_PIXEL_CENTERS_NOT_EGRET",
        "visible_pixel_count":int(opaque.sum()),
        "potential_covered_pixel_count":int(np.count_nonzero(opaque & covered)),
        "guaranteed_covered_pixel_count":int(np.count_nonzero(opaque & guaranteed)),
        "uncovered_potential_pixel_count":remaining,
        "protected_original_dot_count":dot_count,
        "protected_dot_potential_covered":int(np.count_nonzero(protected & covered)),
        "protected_dot_regions_attempted":targeted_dot_count,
        "regions_total":len(seeds),"regions_visited":len(visited),
        "regions_not_visited":len(seeds)-len(visited),
        "stroke_count":len(proposals),"trials":trials,
        "rejected":rejected,"proposals":proposals}
    result["result_sha256"] = _sha(result)
    return result


def build_from_verified_s46(meta_bytes, raw_bytes, original_bytes, **kwargs):
    import engine001_bpred_s4r1_s46_source_contract as s46
    meta = s46.verify_quarantined(meta_bytes, raw_bytes, original_bytes)
    check(meta.get("source_original_only") is True and
          meta.get("admissible_for_gameplay") is False and
          meta.get("native_calibration") == "UNVERIFIED" and
          meta.get("source_owner_status") == "MISSING", "SOURCE_ADMISSION")
    with np.load(io.BytesIO(raw_bytes),allow_pickle=False) as z:
        arrays={k:z[k] for k in
                ("game_index","paintable_id","original_rgba","protected_original_dot")}
    result=build_region_candidates(arrays,**kwargs)
    result["input_sha256"]=meta["input_sha256"]
    result["source_packet_sha256"]=hashlib.sha256(meta_bytes).hexdigest()
    result["engine_git_blob_sha1"]=meta["engine_git_blob_sha1"]
    result["result_sha256"] = _sha({k:v for k,v in result.items()
                                    if k!="result_sha256"})
    return result
