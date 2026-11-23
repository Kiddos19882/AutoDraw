#!/usr/bin/env python3
"""ENGINE-001 S5-R4: source-only region-stratified repeated offset lanes.

Native measured Egret straight-lane pitch guides proposal geometry only.
All final candidate safety checks use existing ideal capsule oracle; NEVER gameplay.
"""
from __future__ import annotations

import hashlib
import io
import json
from collections import Counter

import numpy as np
from scipy import ndimage

import engine001_bpred_s5r2_region_candidates as source
import engine001_bpred_s5r3_clearance_paths as r3

VERSION = "ENGINE001_BPRED_S5R4_REGION_OFFSET_LANES_MODEL_ONLY_V1"
OFFSETS = (0, 1, -1, 2, -2, 3, -3)


def build_candidates(arrays, *, max_trials=2000, max_strokes=200, allocation="area"):
    if type(max_trials) is not int or not 1 <= max_trials <= 2000:
        raise source.BlockedS5R2("BLOCKED_S5R4_TRIAL_BUDGET")
    if type(max_strokes) is not int or not 1 <= max_strokes <= 200:
        raise source.BlockedS5R2("BLOCKED_S5R4_STROKE_BUDGET")
    if allocation not in ("area", "content_s5r5"):
        raise source.BlockedS5R2("BLOCKED_S5R4_ALLOCATION_MODE")
    game, ids, rgba, protected, opaque = source._source_arrays(arrays)
    h, w = game.shape
    content_mode = allocation == "content_s5r5"
    if content_mode:
        source_edge = arrays.get("source_edge")
        if (not isinstance(source_edge, np.ndarray) or source_edge.shape != game.shape
                or source_edge.dtype != np.bool_):
            raise source.BlockedS5R2("BLOCKED_S5R5_SOURCE_EDGE_CONTRACT")
        exterior_ids = set(int(v) for v in np.unique(np.concatenate((
            ids[0], ids[-1], ids[:, 0], ids[:, -1])))) - {0}
    else:
        source_edge = None
        exterior_ids = set()
    seeds, dot_count = source._priority_seeds(ids, opaque, protected)
    # Classify source components without modifying original color/region masks.
    # White touching outer border is a SOFT lower-priority exterior candidate;
    # contained white remains eligible for eyes, clothing and highlights.
    if content_mode:
        def region_group(item):
            region, (cx, cy), *_ = item
            color = int(game[cy, cx])
            return 0 if color != 6 else (2 if region in exterior_ids else 1)
        edge_by_region = np.bincount(
            ids[source_edge & opaque].ravel(),
            minlength=int(ids.max()) + 1)
        # Source-edge evidence ranks source components within their content
        # class; it is never a license to overpaint the protected border.
        grouped = [[r for r in sorted(seeds,
                        key=lambda x: (-int(edge_by_region[x[0]] > 0),
                                       -x[3], -x[4], x[0]))
                    if region_group(r) == cls] for cls in range(3)]
        ordered_seeds = []
        # Bounded weighted round-robin to retain white interior AND exterior candidates.
        while any(grouped):
            for cls in (0, 0, 1, 0, 2):
                if grouped[cls]:
                    ordered_seeds.append(grouped[cls].pop(0))
    else:
        ordered_seeds = sorted(seeds, key=lambda r: (-r[3], -r[4], r[0]))
        region_group = None
    walls = np.zeros((h, w), bool)
    walls[0] = walls[-1] = True
    walls[:, 0] = walls[:, -1] = True
    same_h = ids[:, 1:] != ids[:, :-1]
    same_v = ids[1:, :] != ids[:-1, :]
    walls[:, 1:] |= same_h
    walls[:, :-1] |= same_h
    walls[1:, :] |= same_v
    walls[:-1, :] |= same_v
    walls |= ~opaque
    clearance = ndimage.distance_transform_edt(~walls)
    covered = np.zeros((h, w), bool)
    guaranteed = np.zeros((h, w), bool)
    proposals = []
    totals = {"broad": 0, "detail": 0}
    trials = {"broad": 0, "detail": 0}
    rejected = {"coarse": 0, "unsafe": 0, "zero_gain": 0, "budget": 0}
    catalogue = []
    seen_lines = set()
    visited = set()
    region_lines = Counter()
    candidate_regions = set()

    def offer(phase, region, start, end, size, *, cached=None):
        limit = 1400 if phase == "broad" else 600
        if trials[phase] >= limit or sum(trials.values()) >= max_trials:
            rejected["budget"] += 1
            return None
        trials[phase] += 1
        model = cached if cached is not None else source.swept_capsule_pixel_masks(
            (start, end), size, 1., 1., w, h)
        cells = model["potential_cells"]
        if not cells or any(ids[y, x] != region or not opaque[y, x]
                            or int(game[y, x]) != int(game[int(start[1]), int(start[0])])
                            for x, y in cells):
            rejected["unsafe"] += 1
            return None
        return model

    def accept(phase, region, start, end, size, footprint):
        new = sum(not covered[y, x] for x, y in footprint["potential_cells"])
        if not new:
            rejected["zero_gain"] += 1
            return False
        touch = sum(protected[y, x] and not covered[y, x]
                    for x, y in footprint["potential_cells"])
        for x, y in footprint["potential_cells"]:
            covered[y, x] = True
        for x, y in footprint["guaranteed_cells"]:
            guaranteed[y, x] = True
        totals[phase] += 1
        region_lines[region] += int(phase == "broad")
        proposals.append({
            "phase": phase, "paintable_id": int(region),
            "color_index": int(game[int(start[1]), int(start[0])]),
            "points": [[float(start[0]), float(start[1])],
                       [float(end[0]), float(end[1])]],
            "brush_value": int(size), "drawing_mode": "normal", "smooth": False,
            "safe_to_execute": False, "status": "MODEL_ONLY_NON_EXECUTABLE",
            "modeled_new_potential_cells": int(new),
            "modeled_protected_dots_newly_touched": int(touch)})
        return True

    # Generate a bounded source-region catalogue. A region may have multiple
    # long, genuinely shifted parallel lanes, not one corridor around its seed.
    # Bias only the *search*, never declare distance/EDT a native safety proof.
    for region, center, _dot, area, maximum in ordered_seeds:
        if trials["broad"] >= min(1400, max_trials):
            break
        if area < 6 or maximum < 1.5:
            continue
        visited.add(region)
        cx, cy = center
        pref = min(10, max(2, int((maximum - .71) * 2)))
        widths = tuple(dict.fromkeys((pref, max(2, pref // 2), 2)))
        # Offset order is breadth-first across region seeds, and bounded by
        # the original broad trial cap. Candidate sort later uses actual cells.
        for width in widths:
            if trials["broad"] >= min(1400, max_trials):
                break
            threshold = width / 2 + .72
            for vertical in (False, True):
                if trials["broad"] >= min(1400, max_trials):
                    break
                for offset in OFFSETS:
                    if trials["broad"] >= min(1400, max_trials):
                        break
                    shift = offset * width  # candidate source pixels; NOT Egret px
                    x = cx + (shift if vertical else 0)
                    y = cy + (0 if vertical else shift)
                    if not (0 <= x < w and 0 <= y < h) or                             ids[y, x] != region or clearance[y, x] < threshold:
                        rejected["coarse"] += 1
                        continue
                    if vertical:
                        line_ids = ids[:, x]
                        line_clr = clearance[:, x]
                        at, limit = y, h
                    else:
                        line_ids = ids[y, :]
                        line_clr = clearance[y, :]
                        at, limit = x, w
                    lo = at
                    hi = at
                    while lo > 0 and line_ids[lo-1] == region and                             line_clr[lo-1] >= threshold:
                        lo -= 1
                    while hi < limit-1 and line_ids[hi+1] == region and                             line_clr[hi+1] >= threshold:
                        hi += 1
                    if hi - lo < 2:
                        rejected["coarse"] += 1
                        continue
                    start = (float(x), float(lo)) if vertical else (float(lo), float(y))
                    end = (float(x), float(hi)) if vertical else (float(hi), float(y))
                    signature = (region, width, start, end)
                    if signature in seen_lines:
                        rejected["coarse"] += 1
                        continue
                    seen_lines.add(signature)
                    footprint = offer("broad", region, start, end, width)
                    if footprint is not None:
                        candidate_regions.add(region)
                        catalogue.append((len(footprint["potential_cells"]), region,
                                          start, end, width, footprint))
    # Prefer high incremental coverage, with bounded per-region use so that
    # the first large source region does not monopolize the 80 broad strokes.
    sorted_catalogue = sorted(
        catalogue, key=lambda t: (-t[0], t[1], -t[4], t[2], t[3]))
    if content_mode:
        class_of_region = {r[0]: region_group(r) for r in seeds}
        groups = [[p for p in sorted_catalogue if class_of_region[p[1]] == cls]
                  for cls in range(3)]
        selected = set()
        # Soft group quotas: content up to 60, enclosed whites up to 12,
        # border-connected white up to 8. Unspent slots return to all groups.
        for cls, quota in ((0, 60), (1, 12), (2, 8)):
            used = 0
            for item in groups[cls]:
                if totals["broad"] >= min(80, max_strokes) or used >= quota:
                    break
                _, region, start, end, width, footprint = item
                if region_lines[region] >= 8:
                    continue
                if accept("broad", region, start, end, width, footprint):
                    used += 1
                selected.add((region, width, start, end))
        for item in sorted_catalogue:
            if totals["broad"] >= min(80, max_strokes):
                break
            _, region, start, end, width, footprint = item
            if (region, width, start, end) in selected or region_lines[region] >= 8:
                continue
            accept("broad", region, start, end, width, footprint)
    else:
        for _size, region, start, end, width, footprint in sorted_catalogue:
            if totals["broad"] >= min(80, max_strokes):
                break
            if region_lines[region] >= 8:
                continue
            accept("broad", region, start, end, width, footprint)

    # Independently reserved protected pixel stage, same budget as signed R3.
    if max_trials > 1400 and max_strokes > 80:
        for mask in (protected & ~covered, opaque & ~covered):
            yy, xx = np.nonzero(mask)
            for y, x in zip(yy.tolist(), xx.tolist()):
                if totals["detail"] >= min(120, max_strokes - 80) or                         trials["detail"] >= min(600, max_trials - 1400):
                    break
                if covered[y, x]:
                    continue
                region = int(ids[y, x])
                point = (float(x), float(y))
                footprint = offer("detail", region, point, point, 1)
                if footprint is not None:
                    accept("detail", region, point, point, 1, footprint)
            if totals["detail"] >= min(120, max_strokes - 80):
                break

    remaining = int(np.count_nonzero(opaque & ~covered))
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
        "protected_original_dot_count": dot_count,
        "protected_dot_potential_covered": int(np.count_nonzero(protected & covered)),
        "protected_dot_remaining": int(np.count_nonzero(protected & ~covered)),
        "regions_total": len(seeds), "regions_broad_evaluated": len(visited),
        "regions_feasible_corridors": len(candidate_regions),
        "regions_with_multiple_accepted_lanes":
            sum(count > 1 for count in region_lines.values()),
        "offset_candidate_catalogue_count": len(catalogue),
        "phase_strokes": totals, "phase_trials": trials,
        "stroke_count": len(proposals), "trials": sum(trials.values()),
        "rejected": rejected, "proposals": proposals}
    if content_mode:
        white_covered = int(np.count_nonzero(covered & (game == 6) & opaque))
        content_covered = int(np.count_nonzero(covered & (game != 6) & opaque))
        source_edge_covered = int(np.count_nonzero(covered & source_edge))
        groups_touched = [set() for _ in range(3)]
        for p in proposals:
            groups_touched[class_of_region[p["paintable_id"]]].add(p["paintable_id"])
        result.update({
            "schema": "ENGINE001_BPRED_S5R5_CONTENT_STRATIFIED_LANES_MODEL_ONLY_V1",
            "allocation_policy": "content_s5r5",
            "modeled_white6_covered": white_covered,
            "modeled_nonwhite6_covered": content_covered,
            "modeled_source_edge_covered": source_edge_covered,
            "source_edge_total": int(source_edge.sum()),
            "covered_region_groups": {
                "nonwhite": len(groups_touched[0]),
                "enclosed_white6": len(groups_touched[1]),
                "exterior_white6": len(groups_touched[2])},
            "method_provenance": {
                "Euclidean_Distance_Transform": "APPLIED_clearance_preflight",
                "region_offset_sweeps": "APPLIED_parallel_line_candidates_not_full_boustrophedon",
                "greedy_residual_cover": "PARTIAL_area_rank_with_content_quotas",
                "Boustrophedon_Cellular_Decomposition": "NOT_IMPLEMENTED",
                "Medial_Axis": "NOT_IMPLEMENTED",
                "Contour_Parallel": "NOT_IMPLEMENTED",
                "Spiral_Toolpath": "NOT_IMPLEMENTED"}})
    result["result_sha256"] = r3._digest(result)
    return result


def build_from_verified_s46(meta_bytes, raw_bytes, original_bytes, **kwargs):
    import engine001_bpred_s4r1_s46_source_contract as s46
    meta = s46.verify_quarantined(meta_bytes, raw_bytes, original_bytes)
    if not (meta.get("source_original_only") is True
            and meta.get("source_owner_status") == "MISSING"
            and meta.get("native_calibration") == "UNVERIFIED"
            and meta.get("admissible_for_gameplay") is False):
        raise source.BlockedS5R2("BLOCKED_S5R4_SOURCE")
    with np.load(io.BytesIO(raw_bytes), allow_pickle=False) as packet:
        fields = ["game_index", "paintable_id", "original_rgba", "protected_original_dot"]
        if kwargs.get("allocation") == "content_s5r5":
            fields.append("source_edge")
        arrays = {k: packet[k] for k in fields}
    result = build_candidates(arrays, **kwargs)
    result["source_packet_sha256"] = hashlib.sha256(meta_bytes).hexdigest()
    result["input_sha256"] = meta["input_sha256"]
    result["engine_git_blob_sha1"] = meta["engine_git_blob_sha1"]
    result["result_sha256"] = r3._digest({k: v for k, v in result.items()
                                        if k != "result_sha256"})
    return result
