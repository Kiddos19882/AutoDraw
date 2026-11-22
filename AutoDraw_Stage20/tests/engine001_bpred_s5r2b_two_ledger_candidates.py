#!/usr/bin/env python3
"""ENGINE-001 S5-R2b frozen-E0 research-only broad/detail two-ledger planner.

Never generates executable Egret coordinates; all geometry is original pixels.
DEC-052: all plans/strokes are normal, smooth=False.
"""
from __future__ import annotations

import hashlib
import io
import json
import math

import numpy as np

import engine001_bpred_s5r2_region_candidates as previous

VERSION = "ENGINE001_BPRED_S5R2B_TWO_LEDGER_MODEL_ONLY_V1"
BROAD_TRIALS = 1400
BROAD_STROKES = 80
DETAIL_TRIALS = 600
DETAIL_STROKES = 120
DIRECTIONS = ((1., 0.), (0., 1.), (.7071067811865476, .7071067811865476),
              (.7071067811865476, -.7071067811865476))


class BlockedS5R2b(ValueError):
    pass


def require(test, reason):
    if not test:
        raise BlockedS5R2b("BLOCKED_S5R2B_" + reason)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def build_candidates(arrays, *, max_trials=2000, max_strokes=200):
    """One frozen 1400/80 broad and 600/120 detail schedule at standard budget.

    Lower caps are supported only for negative/unit tests and are not valid
    comparative DEV feasibility claims.
    """
    require(type(max_trials) is int and 1 <= max_trials <= 2000, "TRIALS")
    require(type(max_strokes) is int and 1 <= max_strokes <= 200, "STROKES")
    try:
        game, ids, rgba, protected, opaque = previous._source_arrays(arrays)
    except previous.BlockedS5R2 as exc:
        raise BlockedS5R2b(str(exc)) from exc
    h, w = game.shape
    original_regions = np.unique(ids[opaque])
    region_count = int(len(original_regions))
    covered = np.zeros((h, w), dtype=bool)
    guaranteed = np.zeros((h, w), dtype=bool)
    proposals = []
    trials = {"broad": 0, "detail": 0}
    accepted = {"broad": 0, "detail": 0}
    rejects = {"foreign_alpha_region": 0, "no_gain": 0, "empty": 0,
               "preflight_region": 0}
    visited = set()
    broad_visited = set()
    dot_attempted = 0
    touched_regions = set()
    trial_budget = {"broad": min(BROAD_TRIALS, max_trials),
                    "detail": min(DETAIL_TRIALS, max(0, max_trials-BROAD_TRIALS))}
    stroke_budget = {"broad": min(BROAD_STROKES, max_strokes),
                     "detail": min(DETAIL_STROKES, max(0, max_strokes-BROAD_STROKES))}

    # Reuse the established S5-R2 source-derived EDT/region seeds;
    # reverse its dot-first sorting for broad-fill prioritization.
    seeds, protected_total = previous._priority_seeds(ids, opaque, protected)
    broad = sorted((s for s in seeds if s[4] >= 1.0 and s[3] >= 6),
                   key=lambda s: (-s[3], -s[4], s[0]))
    broad_ids = set(s[0] for s in broad)
    # Approximate source-region preflight only. Exact ideal capsule check
    # remains mandatory and is the only source-safety acceptance gate.
    def offer(phase, region, start, end, brush):
        if trials[phase] >= trial_budget[phase]:
            return None
        points = max(2, int(math.ceil(math.dist(start, end)*2.0))+1)
        for t in np.linspace(0., 1., points):
            x = int(round(start[0] + (end[0]-start[0])*float(t)))
            y = int(round(start[1] + (end[1]-start[1])*float(t)))
            if x < 0 or y < 0 or x >= w or y >= h or ids[y, x] != region:
                rejects["preflight_region"] += 1
                return None
        trials[phase] += 1
        footprint = previous.swept_capsule_pixel_masks(
            (start, end), brush, 1., 1., w, h)
        touched = footprint["potential_cells"]
        if not touched:
            rejects["empty"] += 1
            return None
        if any(ids[y, x] != region or not opaque[y, x] for x, y in touched):
            rejects["foreign_alpha_region"] += 1
            return None
        new = sum(not covered[y, x] for x, y in touched)
        if not new:
            rejects["no_gain"] += 1
            return None
        return ((new, len(footprint["guaranteed_cells"]), brush),
                footprint)

    def accept(phase, region, color, start, end, brush, footprint):
        new_critical = 0
        for x, y in footprint["potential_cells"]:
            if protected[y, x] and not covered[y, x]:
                new_critical += 1
            covered[y, x] = True
        for x, y in footprint["guaranteed_cells"]:
            guaranteed[y, x] = True
        proposals.append({
            "paintable_id": int(region), "color_index": int(color),
            "brush_value": int(brush), "points": [
                [float(start[0]), float(start[1])],
                [float(end[0]), float(end[1])]],
            "phase": phase, "smooth": False, "drawing_mode": "normal",
            "safe_to_execute": False, "status": "MODEL_ONLY_NON_EXECUTABLE",
            "modeled_protected_dots_newly_touched": int(new_critical),
        })
        accepted[phase] += 1
        visited.add(int(region))
        touched_regions.add(int(region))

    # Allocate large regions one stroke per round, then explore other
    # offsets within them; no single top-left pixel can consume all trials.
    # Widths 2..10 only, probe along region interior and then validate the
    # full ideal capsule. Rejection does not consume another region slot.
    progress = True
    sweep = 0
    while broad and progress and accepted["broad"] < stroke_budget["broad"] \
            and trials["broad"] < trial_budget["broad"] and sweep < 10:
        progress = False
        for region, center, _, area, clearance in broad:
            if accepted["broad"] >= stroke_budget["broad"] or \
                    trials["broad"] >= trial_budget["broad"]:
                break
            broad_visited.add(int(region))
            # Revisit a different source-local location in successive rounds.
            # This seed can be rejected; no fallback to other-region paint.
            starts = (center,
                      (center[0]+12*sweep, center[1]),
                      (center[0], center[1]+12*sweep),
                      (center[0]-12*sweep, center[1]),
                      (center[0], center[1]-12*sweep))
            start = starts[(sweep % 4) + 1] if sweep else center
            sx, sy = map(int, start)
            if not (0 <= sx < w and 0 <= sy < h and ids[sy, sx] == region
                    and not covered[sy, sx]):
                continue
            max_width = min(10, max(2, int(2.0*clearance-1.4)))
            widths = tuple(dict.fromkeys(
                (max_width, max(2, max_width//2), 2)))
            best = None
            color = int(game[sy, sx])
            for brush in widths:
                for dx, dy in DIRECTIONS:
                    for sign in (1, -1):
                        for length in (12., 6., 2., 0.):
                            if trials["broad"] >= trial_budget["broad"]:
                                break
                            end = (float(sx)+sign*dx*length,
                                   float(sy)+sign*dy*length)
                            outcome = offer("broad", int(region),
                                            (float(sx),float(sy)),end,brush)
                            if outcome and (best is None or outcome[0] > best[0]):
                                best = (outcome[0], end, brush, outcome[1])
                        if trials["broad"] >= trial_budget["broad"]:
                            break
                    if trials["broad"] >= trial_budget["broad"]:
                        break
                if trials["broad"] >= trial_budget["broad"]:
                    break
            if best:
                _, end, brush, footprint = best
                accept("broad", region, color, (float(sx),float(sy)),
                       end, brush, footprint)
                progress = True
        sweep += 1

    # Detail ledger is independent of broad scheduling: always leave room
    # for protected dots. Source pixel centers, width=1, normal path.
    py, px = np.nonzero(protected & ~covered)
    for y, x in zip(py.tolist(), px.tolist()):
        if accepted["detail"] >= stroke_budget["detail"] or \
                trials["detail"] >= trial_budget["detail"]:
            break
        region = int(ids[y, x])
        visited.add(region)
        dot_attempted += 1
        outcome = offer("detail", region, (float(x), float(y)),
                        (float(x), float(y)), 1)
        if outcome is not None:
            accept("detail", region, int(game[y, x]), (float(x),float(y)),
                   (float(x),float(y)), 1, outcome[1])
    # If no protected residual remains, use detail reserve on uncovered
    # microregions without inventing any width >1 footprint safety.
    if accepted["detail"] < stroke_budget["detail"] and \
            trials["detail"] < trial_budget["detail"]:
        yy, xx = np.nonzero(opaque & ~covered)
        for y, x in zip(yy.tolist(), xx.tolist()):
            if accepted["detail"] >= stroke_budget["detail"] or \
                    trials["detail"] >= trial_budget["detail"]:
                break
            region = int(ids[y, x])
            visited.add(region)
            outcome = offer("detail", region, (float(x),float(y)),
                            (float(x),float(y)), 1)
            if outcome is not None:
                accept("detail", region, int(game[y, x]),
                       (float(x),float(y)), (float(x),float(y)), 1,
                       outcome[1])

    remain = int(np.count_nonzero(opaque & ~covered))
    result = {
        "schema": VERSION, "status": "PARTIAL" if remain else "MODEL_ONLY",
        "drawing_mode": "normal", "smooth": False,
        "safe_to_execute": False, "admissible_for_gameplay": False,
        "native_calibration": "UNVERIFIED", "source_owner_status": "MISSING",
        "coordinates": "ORIGINAL_PIXEL_CENTERS_NOT_EGRET",
        "source_shape": [int(h),int(w)],
        "visible_pixel_count": int(np.count_nonzero(opaque)),
        "potential_covered_pixel_count": int(np.count_nonzero(opaque & covered)),
        "guaranteed_covered_pixel_count": int(np.count_nonzero(opaque & guaranteed)),
        "uncovered_potential_pixel_count": remain,
        "protected_original_dot_count": int(protected_total),
        "protected_dot_potential_covered": int(np.count_nonzero(protected & covered)),
        "protected_dot_remaining": int(np.count_nonzero(protected & ~covered)),
        "protected_dot_attempted": int(dot_attempted),
        "regions_total": region_count, "regions_visited": len(visited),
        "regions_not_visited": region_count-len(visited),
        "regions_touched": len(touched_regions),
        "broad_region_candidates": len(broad_ids),
        "broad_region_visited": len(broad_visited),
        "trials": trials["broad"]+trials["detail"],
        "stroke_count": len(proposals),
        "phase_trials": trials, "phase_strokes": accepted,
        "rejected": rejects, "proposals": proposals,
    }
    result["result_sha256"] = digest(result)
    return result


def build_from_verified_s46(meta_bytes, raw_bytes, original_bytes, **kwargs):
    import engine001_bpred_s4r1_s46_source_contract as s46
    meta = s46.verify_quarantined(meta_bytes, raw_bytes, original_bytes)
    require(meta.get("source_original_only") is True
            and meta.get("admissible_for_gameplay") is False
            and meta.get("source_owner_status") == "MISSING"
            and meta.get("native_calibration") == "UNVERIFIED", "SOURCE_ADMISSION")
    with np.load(io.BytesIO(raw_bytes), allow_pickle=False) as z:
        arrays = {k: z[k] for k in
                  ("game_index","paintable_id","original_rgba","protected_original_dot")}
    result = build_candidates(arrays, **kwargs)
    result["input_sha256"] = meta["input_sha256"]
    result["source_packet_sha256"] = hashlib.sha256(meta_bytes).hexdigest()
    result["engine_git_blob_sha1"] = meta["engine_git_blob_sha1"]
    result["result_sha256"] = digest({k:v for k,v in result.items()
                                       if k!="result_sha256"})
    return result
