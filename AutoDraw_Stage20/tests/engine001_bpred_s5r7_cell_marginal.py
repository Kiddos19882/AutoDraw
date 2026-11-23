#!/usr/bin/env python3
"""S5-R7 source-only dual-axis cell candidates and dynamic marginal cover.

Extends frozen S5-R6 split/merge topology. Research only, no game execution.
"""
from __future__ import annotations

import hashlib
import io
from collections import Counter, defaultdict

import numpy as np
from scipy import ndimage

import engine001_bpred_s5r2_region_candidates as source
import engine001_bpred_s5r3_clearance_paths as r3
import engine001_bpred_s5r6_boustrophedon_cells as r6

VERSION = "ENGINE001_BPRED_S5R7_CELL_MARGINAL_COVER_V1"


def dual_graphs(ids, opaque):
    a = r6.decompose(ids, opaque)
    b = r6.decompose(np.ascontiguousarray(ids.T),
                     np.ascontiguousarray(opaque.T))
    if a["opaque_pixels"] != b["opaque_pixels"] or a["opaque_pixels"] != int(opaque.sum()):
        raise source.BlockedS5R2("BLOCKED_S5R7_AXIS_OWNER_DISAGREE")
    return (a, b)


def _candidate_from_span(cell, span, axis, clearance, game):
    """A maximal EDT-safe straight corridor, in source pixel centers."""
    yy, x0, x1 = span
    if x1 - x0 < 3:
        return None
    if axis:
        # Transposed graph's x-coordinate is original y, its row is original x.
        line = clearance[ x0:x1 + 1, yy]
    else:
        line = clearance[yy, x0:x1 + 1]
    if line.size < 4:
        return None
    pos = int(np.argmax(line))
    radius = float(line[pos])
    width = min(10, max(2, int((radius - .72) * 2)))
    if radius < width/2 + .72:
        return None
    good = line >= width/2 + .72
    lo = pos
    hi = pos
    while lo > 0 and bool(good[lo-1]):
        lo -= 1
    while hi < len(line)-1 and bool(good[hi+1]):
        hi += 1
    if hi - lo < 3:
        return None
    a, b = x0 + lo, x0 + hi
    pts = ((float(yy), float(a)), (float(yy), float(b))) if axis else (
        (float(a), float(yy)), (float(b), float(yy)))
    center = (int(pts[0][0]), int(pts[0][1]))
    swatch = int(game[center[1], center[0]])
    return dict(owner=cell["region"], cell=cell["id"], axis=90 if axis else 0,
                points=pts, width=width, color=swatch, estimated_gain=(hi-lo+1)*width,
                cell_area=cell["area"])


def _generate(ids, game, clearance, graphs, max_pool=8000):
    proposals = []
    for axis, graph in enumerate(graphs):
        for cell in graph["cells"]:
            if cell["area"] < 8:
                continue
            spans = cell["spans"]
            # No per-image tuning: keep longest and topologically distinct
            # second interval where useful. Candidate enumeration is cheap;
            # capsule oracle calls are only in _validate_candidates.
            best = sorted(spans, key=lambda s: (-(s[2]-s[1]), s[0]))
            chosen = []
            for span in best:
                if len(chosen) == 2:
                    break
                if any(abs(span[0] - other[0]) < 3 for other in chosen):
                    continue
                p = _candidate_from_span(cell, span, axis, clearance, game)
                if p is not None and p["estimated_gain"] >= 8:
                    proposals.append(p)
                    chosen.append(span)
    # E0 geometric orientation decision BEFORE calling the capsule oracle:
    # each source-owner region (which can comprise many sweep cells) chooses
    # the direction with the greatest sum of its six longest safe spans.
    # This is a deterministic region-level approximation, explicitly not
    # a per-pixel/semantic or result-dependent orientation search.
    by_axis=defaultdict(list)
    for p in proposals:
        by_axis[(p["owner"],p["axis"])].append(p["estimated_gain"])
    axes={}
    for owner in set(p["owner"] for p in proposals):
        cost={a:sum(sorted(by_axis.get((owner,a),()),reverse=True)[:6])
              for a in (0,90)}
        axes[owner]=90 if cost[90]>cost[0] else 0
    proposals=[p for p in proposals if p["axis"]==axes[p["owner"]]]
    proposals.sort(key=lambda p: (-p["estimated_gain"], -p["cell_area"],
                                  p["owner"], p["axis"], p["cell"]))
    return proposals[:max_pool], axes


def _validate_candidates(proposals, ids, game, opaque, *, max_calls=1400):
    h, w = game.shape
    pool = []
    seen = set()
    tried = 0
    rejected = Counter()
    for p in proposals:
        if tried >= max_calls:
            break
        key = (p["owner"], p["points"], p["width"])
        if key in seen:
            continue
        seen.add(key)
        tried += 1
        model = source.swept_capsule_pixel_masks(p["points"], p["width"],
                                                 1., 1., w, h)
        coords = model["potential_cells"]
        if not coords:
            rejected["empty"] += 1
            continue
        flat = np.fromiter((y*w+x for x, y in coords), dtype=np.int64,
                           count=len(coords))
        yy, xx = np.divmod(flat, w)
        if (not np.all(opaque[yy, xx]) or
                not np.all(ids[yy, xx] == p["owner"]) or
                not np.all(game[yy, xx] == p["color"])):
            rejected["owner_or_alpha"] += 1
            continue
        pool.append((p, model, flat))
    return pool, tried, dict(rejected)


def _detail_paths(mask, ids, unlimited):
    if not unlimited:
        for y, x in zip(*np.nonzero(mask)):
            point = (float(x), float(y))
            yield x, y, (point, point), 0
        return

    # Choose the direction requiring fewer straight runs for each owner.
    residual = np.where(mask, ids, 0)
    horizontal = residual.copy()
    horizontal[:, 1:] *= residual[:, 1:] != residual[:, :-1]
    vertical = residual.copy()
    vertical[1:] *= residual[1:] != residual[:-1]
    size = int(residual.max()) + 1
    column_owner = (np.bincount(vertical.ravel(), minlength=size)
                    < np.bincount(horizontal.ravel(), minlength=size))
    for axis, rows in enumerate((residual, residual.T)):
        for row, values in enumerate(rows):
            bounds = np.flatnonzero(np.diff(values, prepend=-1, append=-1))
            for start, end in zip(bounds[:-1], bounds[1:]):
                owner = values[start]
                if owner == 0 or column_owner[owner] != bool(axis):
                    continue
                x, y = (row, start) if axis else (start, row)
                last = (row, end-1) if axis else (end-1, row)
                first = (float(x), float(y))
                points = (first,) if end-start == 1 else (first, tuple(map(float, last)))
                yield x, y, points, axis * 90


def build_candidates(arrays, *, max_trials=2000, max_strokes=200):
    return _build_candidates(arrays, max_trials, max_strokes, _generate,
                             _validate_candidates, VERSION)


def _build_candidates(arrays, max_trials, max_strokes, generate, validate, version, *, unlimited=False):
    if not unlimited and (type(max_trials) is not int or not 1 <= max_trials <= 2000):
        raise source.BlockedS5R2("BLOCKED_S5R7_TRIAL_BUDGET")
    if not unlimited and (type(max_strokes) is not int or not 1 <= max_strokes <= 200):
        raise source.BlockedS5R2("BLOCKED_S5R7_STROKE_BUDGET")
    game, ids, rgba, protected, opaque = source._source_arrays(arrays)
    edge = arrays.get("source_edge")
    if not isinstance(edge, np.ndarray) or edge.dtype != np.bool_ or edge.shape != game.shape:
        raise source.BlockedS5R2("BLOCKED_S5R7_SOURCE_EDGE")
    h, w = game.shape
    graphs = dual_graphs(ids, opaque)
    walls = np.zeros((h, w), bool)
    walls[0] = walls[-1] = True
    walls[:, 0] = walls[:, -1] = True
    changed = ids[:, 1:] != ids[:, :-1]
    walls[:, 1:] |= changed
    walls[:, :-1] |= changed
    changed = ids[1:, :] != ids[:-1, :]
    walls[1:, :] |= changed
    walls[:-1, :] |= changed
    walls |= ~opaque
    clearance = ndimage.distance_transform_edt(~walls)
    raw, chosen_axes = generate(ids, game, clearance, graphs)
    owner_area = np.bincount(ids[opaque], minlength=int(ids.max())+1)
    owner_edge = np.bincount(ids[edge & opaque], minlength=len(owner_area))
    owner_protected = np.bincount(ids[protected], minlength=len(owner_area))
    border_owner = set(int(x) for x in np.unique(np.concatenate(
        (ids[0], ids[-1], ids[:,0], ids[:,-1]))))
    accepted = {"broad":0, "detail":0}
    trials = {"broad":0, "detail":0}
    rejected = Counter()
    covered = np.zeros_like(opaque)
    guaranteed = np.zeros_like(opaque)
    owner_covered = Counter()
    owner_strokes = Counter()
    swatch_strokes = Counter()
    cell_strokes = Counter()
    proposed = []

    pool, n_trials, counters = validate(
        raw, ids, game, opaque, max_calls=float("inf") if unlimited else min(1400,max_trials))
    trials["broad"] = n_trials
    rejected.update(counters)
    flat_cover = covered.ravel()
    owner_areas = owner_area

    for _ in range(len(pool) if unlimited else min(80, max_strokes)):
        best = None
        best_score = -1.0
        best_gain = 0
        for i, (meta, model, cells) in enumerate(pool):
            if cells is None:
                continue
            gain = int(np.count_nonzero(~flat_cover[cells]))
            if not gain:
                continue
            region = meta["owner"]
            # Frozen unlearned allocation formula: residual model gain,
            # source-owner deficit and novelty. No hard color quotas.
            fraction = owner_covered[region] / max(1, int(owner_areas[region]))
            novelty = 1.5 if owner_strokes[region] == 0 else 1.0
            deficit = max(.15, 1.0-fraction)
            boundary_proxy = min(1.0, owner_edge[region] /
                                 max(1,owner_areas[region]))
            detail_proxy = float(owner_protected[region] > 0)
            internal_white = float(meta["color"] == 6 and region not in border_owner)
            # E0 source-geometry proxies, NOT semantic ground truth.
            # All coefficients fixed before original4x2 outcome is reviewed.
            score = gain * (
                1.0 + 0.35*novelty + 0.35*deficit +
                0.10*boundary_proxy + 0.10*detail_proxy + 0.10*internal_white
            ) / (1.0 + 0.18*owner_strokes[region] +
                 0.12*swatch_strokes[meta["color"]])
            if score > best_score:
                best, best_score, best_gain = i, score, gain
        if best is None:
            break
        meta, model, cells = pool[best]
        newly_covered = ~flat_cover[cells]
        protected_flat = protected.ravel()
        touch = int(np.count_nonzero(newly_covered & protected_flat[cells]))
        flat_cover[cells] = True
        for x, y in model["guaranteed_cells"]:
            guaranteed[y,x] = True
        owner = meta["owner"]
        owner_covered[owner] += best_gain
        owner_strokes[owner] += 1
        swatch_strokes[meta["color"]] += 1
        cell_strokes[(meta["axis"], meta["cell"])] += 1
        accepted["broad"] += 1
        proposed.append({
            "phase":"broad", "paintable_id": int(owner),
            "color_index": int(meta["color"]),
            "points": [[float(x),float(y)] for x,y in meta["points"]],
            "brush_value": int(meta["width"]), "axis_degrees": int(meta["axis"]),
            "cell_id": int(meta["cell"]),
            "drawing_mode":"normal", "smooth":False,
            "safe_to_execute":False, "status":"MODEL_ONLY_NON_EXECUTABLE",
            "modeled_new_potential_cells": best_gain,
            "modeled_protected_dots_newly_touched": touch})
        if "lane_axis" in meta:
            proposed[-1]["lane_axis_degrees"] = meta["lane_axis"]
        pool[best] = (meta, model, None)

    # Same reserved detail phase as R3-R6; exact source-owner/model oracle.
    if unlimited or (max_trials>1400 and max_strokes>80):
        detail_strokes = float("inf") if unlimited else min(120, max_strokes-80)
        detail_trials = float("inf") if unlimited else min(600, max_trials-1400)
        masks = (opaque & ~covered,) if unlimited else (protected & ~covered, opaque & ~covered)
        for mask in masks:
            for x, y, pt, axis in _detail_paths(mask, ids, unlimited):
                if accepted["detail"] >= detail_strokes or \
                        trials["detail"] >= detail_trials:
                    break
                if covered[y,x]:
                    continue
                trials["detail"] += 1
                model = source.swept_capsule_pixel_masks(pt,1,1.,1.,w,h)
                ink = model["potential_cells"]
                if not ink or any(ids[py,px] != ids[y,x] or
                                  game[py,px] != game[y,x] or not opaque[py,px]
                                  for px,py in ink):
                    rejected["detail_unsafe"]+=1
                    continue
                fresh = [(px,py) for px,py in ink if not covered[py,px]]
                if not fresh:
                    continue
                touch = sum(protected[py,px] for px,py in fresh)
                for px,py in ink:
                    covered[py,px] = True
                for px,py in model["guaranteed_cells"]:
                    guaranteed[py,px] = True
                proposed.append({
                    "phase":"detail", "paintable_id":int(ids[y,x]),
                    "color_index":int(game[y,x]),
                    "points": [list(point) for point in pt],
                    "brush_value":1, "axis_degrees":axis,
                    "cell_id":None, "drawing_mode":"normal", "smooth":False,
                    "safe_to_execute":False, "status":"MODEL_ONLY_NON_EXECUTABLE",
                    "modeled_new_potential_cells":len(fresh),
                    "modeled_protected_dots_newly_touched":int(touch)})
                accepted["detail"]+=1
            if accepted["detail"] >= detail_strokes:
                break
    total = int(opaque.sum())
    result = {
        "schema":version, "status":"PARTIAL" if total>covered.sum() else "MODEL_ONLY",
        "source_shape":[int(h),int(w)],
        "drawing_mode":"normal","smooth":False,
        "source_owner_status":"MISSING", "native_calibration":"UNVERIFIED",
        "native_Egret":"NOT_RUN","coordinates":"ORIGINAL_PIXEL_CENTERS_NOT_EGRET",
        "safe_to_execute":False,"admissible_for_gameplay":False,
        "visible_pixel_count":total,
        "potential_covered_pixel_count":int(covered.sum()),
        "guaranteed_covered_pixel_count":int(guaranteed.sum()),
        "uncovered_potential_pixel_count":total-int(covered.sum()),
        "protected_original_dot_count":int(protected.sum()),
        "protected_dot_potential_covered":int(np.count_nonzero(protected & covered)),
        "protected_dot_remaining":int(np.count_nonzero(protected & ~covered)),
        "modeled_white6_covered":int(np.count_nonzero(covered & (game==6))),
        "modeled_nonwhite6_covered":int(np.count_nonzero(covered & (game!=6))),
        "modeled_source_edge_covered":int(np.count_nonzero(covered & edge)),
        "topology":{
            "row_cells":len(graphs[0]["cells"]),"column_cells":len(graphs[1]["cells"]),
            "row_split":graphs[0]["split_events"],"row_merge":graphs[0]["merge_events"],
            "column_split":graphs[1]["split_events"],
            "column_merge":graphs[1]["merge_events"],
            "row_area":graphs[0]["opaque_pixels"],
            "column_area":graphs[1]["opaque_pixels"]},
        "scheduler":{
            "raw_candidate_count":len(raw),
            "valid_source_candidates":len(pool),
            "owner_broad_count":len(owner_strokes),
            "swatch_broad_count":len(swatch_strokes),
            "per_owner_broad":{str(k):v for k,v in sorted(owner_strokes.items())},
            "per_swatch_broad":{str(k):v for k,v in sorted(swatch_strokes.items())},
            "orientation_broad":{str(a):sum(s["axis_degrees"]==a for s in proposed
                                        if s["phase"]=="broad") for a in (0,90)},
            "covered_cell_count":len(cell_strokes),
            "marginal_formula":"gain*(1+.35*novelty+.35*deficit+.10*edge_ratio+.10*protected_owner+.10*interior_white)/(1+.18*owner_strokes+.12*swatch_strokes)",
            "chosen_axis_per_owner":{str(k):v for k,v in sorted(chosen_axes.items())},
            "orientation_cost_rule":"highest sum of 6 longest EDT-safe lane area proxies per owner, tie angle0",
            "native_pitch_semantics":"SOURCE_ONLY_NOT_EGRET"},
        "phase_strokes":accepted,"phase_trials":trials,
        "stroke_count":len(proposed),"trials":sum(trials.values()),
        "rejected":dict(rejected),"proposals":proposed,
        "web_methods":{
            "Boustrophedon_Cellular_Decomposition":"APPLIED_dual_axis_row_column_split_merge_graphs",
            "Euclidean_Distance_Transform":"APPLIED_clearance",
            "parallel_sweep_lanes":"APPLIED_straight_two_point",
            "greedy_geometric_set_cover":"PARTIAL_dynamic_marginal_owner_deficit",
            "Medial_Axis":"NOT_IMPLEMENTED",
            "Contour_Parallel":"NOT_IMPLEMENTED",
            "Spiral":"NOT_IMPLEMENTED"}}
    result["result_sha256"]=r3._digest(result)
    return result


def build_from_verified_s46(meta_bytes, raw_bytes, original_bytes, **kwargs):
    import engine001_bpred_s4r1_s46_source_contract as s46
    meta = s46.verify_quarantined(meta_bytes, raw_bytes, original_bytes)
    if not (meta.get("source_original_only") is True and
            meta.get("source_owner_status") == "MISSING" and
            meta.get("native_calibration") == "UNVERIFIED" and
            meta.get("admissible_for_gameplay") is False):
        raise source.BlockedS5R2("BLOCKED_S5R7_SOURCE")
    with np.load(io.BytesIO(raw_bytes), allow_pickle=False) as p:
        arrays = {k:p[k] for k in ("game_index","paintable_id","original_rgba",
                                 "protected_original_dot","source_edge")}
    result = build_candidates(arrays,**kwargs)
    result["source_packet_sha256"]=hashlib.sha256(meta_bytes).hexdigest()
    result["input_sha256"]=meta["input_sha256"]
    result["engine_git_blob_sha1"]=meta["engine_git_blob_sha1"]
    result["result_sha256"]=r3._digest({k:v for k,v in result.items()
                                       if k!="result_sha256"})
    return result
