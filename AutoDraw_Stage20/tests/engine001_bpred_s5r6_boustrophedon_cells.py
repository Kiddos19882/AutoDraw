#!/usr/bin/env python3
"""Source-only true row-sweep cellular decomposition with split/merge graph.

Research stage S5-R6. All candidate paint remains MODEL_ONLY and fail closed.
No user/game coordinate calibration or native paint is inferred.
"""
from __future__ import annotations

import hashlib
import io
import json

import numpy as np
from scipy import ndimage

import engine001_bpred_s5r2_region_candidates as source
import engine001_bpred_s5r3_clearance_paths as r3

VERSION = "ENGINE001_BPRED_S5R6_BOUSTROPHEDON_SWEEP_CELLS_V1"


def decompose(ids, opaque, *, max_runs=1_000_000):
    """Maximal x-intervals per scan row; node changes on genuine split/merge.

    Each accepted pixel belongs to one and only one cell span, whether or not
    source-owner IDs are equal for two disconnected spatial components.
    """
    if not (isinstance(ids, np.ndarray) and ids.dtype == np.int32 and
            ids.ndim == 2 and isinstance(opaque, np.ndarray) and
            opaque.dtype == np.bool_ and opaque.shape == ids.shape):
        raise source.BlockedS5R2("BLOCKED_S5R6_CELL_INPUT")
    if np.any((ids <= 0) & opaque) or np.any((ids != 0) & ~opaque):
        raise source.BlockedS5R2("BLOCKED_S5R6_CELL_OWNER")
    h, w = ids.shape
    cells = []
    events = []
    edges = []
    previous = []
    total_runs = 0
    for y in range(h):
        row = ids[y]
        changes = np.flatnonzero(row[1:] != row[:-1]) + 1
        bounds = np.concatenate(([0], changes, [w]))
        current = [(int(bounds[i]), int(bounds[i + 1] - 1), int(row[bounds[i]]))
                   for i in range(len(bounds)-1) if row[bounds[i]] != 0]
        total_runs += len(current)
        if total_runs > max_runs:
            raise source.BlockedS5R2("BLOCKED_S5R6_MAX_RUNS")
        in_links = [[] for _ in current]
        out_links = [[] for _ in previous]
        p = 0
        for j, (x0, x1, region) in enumerate(current):
            while p < len(previous) and previous[p][1] < x0:
                p += 1
            k = p
            while k < len(previous) and previous[k][0] <= x1:
                if previous[k][2] == region:
                    in_links[j].append(k)
                    out_links[k].append(j)
                k += 1
        mapped = []
        for j, (x0, x1, region) in enumerate(current):
            src = in_links[j]
            if len(src) == 1 and len(out_links[src[0]]) == 1:
                cell_id = previous[src[0]][3]
            else:
                cell_id = len(cells)
                cells.append({"id": cell_id, "region": region, "area": 0,
                              "spans": [], "parents": []})
                kind = ("appearance" if not src else
                        "split" if len(src) == 1 else
                        "merge" if all(len(out_links[k]) == 1 for k in src)
                        else "complex")
                events.append({"kind": kind, "row": int(y), "cell": cell_id,
                               "from": sorted(set(previous[k][3] for k in src))})
                for old in sorted(set(previous[k][3] for k in src)):
                    cells[cell_id]["parents"].append(old)
                    edges.append((old, cell_id))
            c = cells[cell_id]
            c["spans"].append((int(y), x0, x1))
            c["area"] += x1 - x0 + 1
            mapped.append((x0, x1, region, cell_id))
        for i, (_, _, _, cell_id) in enumerate(previous):
            if not out_links[i]:
                events.append({"kind": "disappearance", "row": int(y),
                               "cell": cell_id, "from": []})
        previous = mapped
    for _, _, _, cell_id in previous:
        events.append({"kind": "disappearance", "row": int(h), "cell": cell_id,
                       "from": []})
    expected = np.bincount(ids[opaque], minlength=int(ids.max()) + 1)
    observed = np.zeros_like(expected)
    for c in cells:
        observed[c["region"]] += c["area"]
    if not np.array_equal(expected, observed) or             sum(c["area"] for c in cells) != int(np.count_nonzero(opaque)):
        raise source.BlockedS5R2("BLOCKED_S5R6_DROPPED_PIXELS")
    if any(b <= a for a, b in edges):
        raise source.BlockedS5R2("BLOCKED_S5R6_CELL_DAG")
    return {"cells": cells, "edges": edges, "events": events,
            "runs": total_runs, "opaque_pixels": int(opaque.sum()),
            "split_events": sum(e["kind"] == "split" for e in events),
            "merge_events": sum(e["kind"] in ("merge", "complex") for e in events)}


def build_candidates(arrays, *, max_trials=2000, max_strokes=200):
    if type(max_trials) is not int or not 1 <= max_trials <= 2000:
        raise source.BlockedS5R2("BLOCKED_S5R6_TRIAL_LIMIT")
    if type(max_strokes) is not int or not 1 <= max_strokes <= 200:
        raise source.BlockedS5R2("BLOCKED_S5R6_STROKE_LIMIT")
    game, ids, rgba, protected, opaque = source._source_arrays(arrays)
    edge = arrays.get("source_edge")
    if not (isinstance(edge, np.ndarray) and edge.shape == game.shape and
            edge.dtype == np.bool_):
        raise source.BlockedS5R2("BLOCKED_S5R6_SOURCE_EDGE")
    h, w = game.shape
    topology = decompose(ids, opaque)
    walls = np.zeros_like(opaque)
    walls[0] = walls[-1] = True
    walls[:, 0] = walls[:, -1] = True
    changed_h = ids[:, 1:] != ids[:, :-1]
    changed_v = ids[1:, :] != ids[:-1, :]
    walls[:, 1:] |= changed_h
    walls[:, :-1] |= changed_h
    walls[1:, :] |= changed_v
    walls[:-1, :] |= changed_v
    walls |= ~opaque
    clearance = ndimage.distance_transform_edt(~walls)
    covered = np.zeros_like(opaque)
    guaranteed = np.zeros_like(opaque)
    trials = {"broad": 0, "detail": 0}
    accepted = {"broad": 0, "detail": 0}
    rejected = {"unsafe": 0, "zero_gain": 0, "coarse": 0}
    proposals = []
    cell_used = {}
    # Prioritize source-owned non-background interiors; internal white source
    # components remain candidates. No per-image/quota post-hoc policy.
    def cell_priority(c):
        sy, x0, x1 = max(c["spans"], key=lambda z: z[2]-z[1])
        color = int(game[sy, (x0+x1)//2])
        return (color == 6, -c["area"], -len(c["spans"]), c["id"])
    ordered = sorted(topology["cells"], key=cell_priority)

    def offer(region, points, width, phase):
        if trials[phase] >= (1400 if phase == "broad" else 600):
            return None
        trials[phase] += 1
        model = source.swept_capsule_pixel_masks(points, width, 1., 1., w, h)
        potential = model["potential_cells"]
        if not potential or any(
                ids[y, x] != region or not opaque[y, x] or
                game[y, x] != game[int(points[0][1]), int(points[0][0])]
                for x, y in potential):
            rejected["unsafe"] += 1
            return None
        gain = sum(not covered[y, x] for x, y in potential)
        if not gain:
            rejected["zero_gain"] += 1
            return None
        return model, gain

    def accept(region, points, width, phase, model, gain, cell_id=None):
        touched = 0
        for x, y in model["potential_cells"]:
            if not covered[y, x] and protected[y, x]:
                touched += 1
            covered[y, x] = True
        for x, y in model["guaranteed_cells"]:
            guaranteed[y, x] = True
        accepted[phase] += 1
        if cell_id is not None:
            cell_used[cell_id] = cell_used.get(cell_id, 0) + 1
        proposals.append({
            "phase": phase, "paintable_id": int(region),
            "color_index": int(game[int(points[0][1]), int(points[0][0])]),
            "points": [[float(x), float(y)] for x, y in points],
            "brush_value": int(width), "cell_id": cell_id,
            "drawing_mode": "normal", "smooth": False, "safe_to_execute": False,
            "status": "MODEL_ONLY_NON_EXECUTABLE",
            "modeled_new_potential_cells": int(gain),
            "modeled_protected_dots_newly_touched": int(touched)})

    # Cellular boustrophedon: explore different scan lines within the same
    # sweep cell, using EDT-clipped interior intervals and distinct row bands.
    # Reserve evaluation budget and all width-1 details as in R3/R4/R5.
    for c in ordered:
        if accepted["broad"] >= min(80, max_strokes) or                 trials["broad"] >= min(1400, max_trials):
            break
        spans = sorted(c["spans"], key=lambda p: (-(p[2]-p[1]), p[0]))
        used_y = []
        cell_count = 0
        for width in (10, 6, 3, 2):
            if cell_count >= 6 or accepted["broad"] >= min(80, max_strokes) or                     trials["broad"] >= min(1400, max_trials):
                break
            clearance_min = width / 2 + .72
            for y, x0, x1 in spans:
                if cell_count >= 6 or accepted["broad"] >= min(80, max_strokes) or                         trials["broad"] >= min(1400, max_trials):
                    break
                if x1 - x0 < max(2, width):
                    rejected["coarse"] += 1
                    continue
                if any(abs(y - prev) < width for prev in used_y):
                    continue
                eligible = np.flatnonzero(clearance[y, x0:x1+1] >= clearance_min)
                if len(eligible) < 3:
                    rejected["coarse"] += 1
                    continue
                center = (x0 + x1)//2
                if not (x0 <= center <= x1) or clearance[y, center] < clearance_min:
                    continue
                a = center
                b = center
                while a > x0 and clearance[y, a-1] >= clearance_min:
                    a -= 1
                while b < x1 and clearance[y, b+1] >= clearance_min:
                    b += 1
                if b-a < 2:
                    rejected["coarse"] += 1
                    continue
                pts = ((float(a), float(y)), (float(b), float(y)))
                offered = offer(c["region"], pts, width, "broad")
                if offered is None:
                    continue
                model, gain = offered
                accept(c["region"], pts, width, "broad", model, gain, c["id"])
                used_y.append(y)
                cell_count += 1
                # One wide sample per width pass before smaller brush options.
                break

    if max_trials > 1400 and max_strokes > 80:
        for mask in (protected & ~covered, opaque & ~covered):
            yy, xx = np.nonzero(mask)
            for y, x in zip(yy.tolist(), xx.tolist()):
                if accepted["detail"] >= min(120, max_strokes - 80) or                         trials["detail"] >= min(600, max_trials - 1400):
                    break
                if covered[y, x]:
                    continue
                pts = ((float(x), float(y)), (float(x), float(y)))
                o = offer(int(ids[y, x]), pts, 1, "detail")
                if o:
                    accept(int(ids[y, x]), pts, 1, "detail", o[0], o[1])
            if accepted["detail"] >= min(120, max_strokes - 80):
                break
    remaining = int(np.count_nonzero(opaque & ~covered))
    # Keep a compact but genuine cell/event source ledger; never export 2M
    # repeated per-pixel cell records into the model JSON.
    graph = {
        "cell_count": len(topology["cells"]),
        "run_count": topology["runs"],
        "edge_count": len(topology["edges"]),
        "split_events": topology["split_events"],
        "merge_events": topology["merge_events"],
        "source_owner_area_verified": topology["opaque_pixels"],
        "cells_with_accepted_broad_lanes": len(cell_used),
        "cells_multiple_broad_lanes": sum(v > 1 for v in cell_used.values()),
        "event_sample": topology["events"][:60],
        "edges_sample": topology["edges"][:60]}
    result = {
        "schema": VERSION, "status": "PARTIAL" if remaining else "MODEL_ONLY",
        "source_shape": [int(h), int(w)], "drawing_mode": "normal",
        "smooth": False, "source_owner_status": "MISSING",
        "native_calibration": "UNVERIFIED", "native_Egret": "NOT_RUN",
        "coordinates": "ORIGINAL_PIXEL_CENTERS_NOT_EGRET",
        "safe_to_execute": False, "admissible_for_gameplay": False,
        "visible_pixel_count": int(opaque.sum()),
        "potential_covered_pixel_count": int(np.count_nonzero(opaque & covered)),
        "guaranteed_covered_pixel_count": int(np.count_nonzero(opaque & guaranteed)),
        "uncovered_potential_pixel_count": remaining,
        "protected_original_dot_count": int(protected.sum()),
        "protected_dot_potential_covered": int(np.count_nonzero(protected & covered)),
        "protected_dot_remaining": int(np.count_nonzero(protected & ~covered)),
        "modeled_white6_covered": int(np.count_nonzero(covered & opaque & (game == 6))),
        "modeled_nonwhite6_covered": int(np.count_nonzero(covered & opaque & (game != 6))),
        "modeled_source_edge_covered": int(np.count_nonzero(covered & edge)),
        "topology": graph, "phase_strokes": accepted, "phase_trials": trials,
        "stroke_count": len(proposals), "trials": sum(trials.values()),
        "rejected": rejected, "proposals": proposals,
        "web_methods": {
            "Boustrophedon_Cellular_Decomposition": "APPLIED_row_sweep_split_merge_graph",
            "Euclidean_Distance_Transform": "APPLIED_scipy_edt_clearance",
            "parallel_sweep_lanes": "APPLIED_bounded_interior_rows",
            "geometric_set_cover": "PARTIAL_new_uncovered_potential_gate",
            "Medial_Axis": "NOT_IMPLEMENTED",
            "Contour_Parallel": "NOT_IMPLEMENTED",
            "Spiral_Toolpath": "NOT_IMPLEMENTED"}}
    result["result_sha256"] = r3._digest(result)
    return result


def build_from_verified_s46(meta_bytes, raw_bytes, original_bytes, **kwargs):
    import engine001_bpred_s4r1_s46_source_contract as s46
    meta = s46.verify_quarantined(meta_bytes, raw_bytes, original_bytes)
    if not (meta.get("source_original_only") is True and
            meta.get("source_owner_status") == "MISSING" and
            meta.get("native_calibration") == "UNVERIFIED" and
            meta.get("admissible_for_gameplay") is False):
        raise source.BlockedS5R2("BLOCKED_S5R6_SOURCE")
    with np.load(io.BytesIO(raw_bytes), allow_pickle=False) as packet:
        arrays = {k: packet[k] for k in
                  ("game_index", "paintable_id", "original_rgba",
                   "protected_original_dot", "source_edge")}
    result = build_candidates(arrays, **kwargs)
    result["source_packet_sha256"] = hashlib.sha256(meta_bytes).hexdigest()
    result["input_sha256"] = meta["input_sha256"]
    result["engine_git_blob_sha1"] = meta["engine_git_blob_sha1"]
    result["result_sha256"] = r3._digest({k: v for k, v in result.items()
                                        if k != "result_sha256"})
    return result
