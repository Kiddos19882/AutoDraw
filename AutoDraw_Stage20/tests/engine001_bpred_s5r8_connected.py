"""Research-only connected source-cell sweeps. All geometry is in source pixels."""
from collections import Counter

import numpy as np

import engine001_bpred_s5r7_cell_marginal as r7


VERSION = "ENGINE001_BPRED_S5R8_CONNECTED_CELL_SWEEPS_V1"


def _generate(ids, game, clearance, graphs):
    _, axes = r7._generate(ids, game, clearance, graphs)
    proposals = []
    for axis, graph in enumerate(graphs):
        for cell in graph["cells"]:
            if axes.get(cell["region"]) != 90 * axis:
                continue
            lanes = []
            for span in cell["spans"]:
                if lanes and span[0] - last_row < lanes[-1]["width"]:
                    continue
                lane = r7._candidate_from_span(cell, span, axis, clearance, game)
                if lane is None:
                    continue
                last_row = span[0]
                lanes.append(lane)
            for start in range(0, len(lanes), 10):
                group = lanes[start:start + 10]
                width = min(lane["width"] for lane in group)
                length = sum(lane["estimated_gain"] / lane["width"] for lane in group)
                proposals.append(dict(group[0], lanes=group, width=width,
                                      estimated_gain=length * width))
    proposals.sort(key=lambda p: (-p["estimated_gain"], p["owner"], p["cell"]))
    return proposals, axes


def _validate(proposals, ids, game, opaque, *, max_calls):
    h, w = game.shape
    pool = []
    rejected = Counter()
    calls = 0

    def measure(points, proposal):
        nonlocal calls
        calls += 1
        model = r7.source.swept_capsule_pixel_masks(points, proposal["width"], 1., 1., w, h)
        flat = np.fromiter((y*w+x for x, y in model["potential_cells"]), dtype=np.int64)
        if (not flat.size or not opaque.ravel()[flat].all()
                or not (ids.ravel()[flat] == proposal["owner"]).all()
                or not (game.ravel()[flat] == proposal["color"]).all()):
            return None
        return model, flat

    def finish(points, proposal):
        if not points or calls >= max_calls:
            return
        result = measure(points, proposal)
        if result is None:
            rejected["whole_path_unsafe"] += 1
        else:
            meta = dict(proposal, points=tuple(points))
            pool.append((meta, *result))

    for proposal in proposals:
        points = []
        for index, lane in enumerate(proposal["lanes"]):
            if calls >= max_calls:
                break
            entry, exit_point = lane["points"][::(-1 if index % 2 else 1)]
            if points:
                # The connector shares an exact endpoint with both lane caps.
                if calls + 1 >= max_calls:
                    break
                if measure((points[-1], entry), proposal) is None:
                    rejected["split_unsafe_connector"] += 1
                    finish(points, proposal)
                    points = []
            points.extend((entry, exit_point))
        finish(points, proposal)
        if calls >= max_calls:
            break
    return pool, calls, dict(rejected)


def build_candidates(arrays, *, max_trials=2000, max_strokes=200):
    plan = r7._build_candidates(arrays, max_trials, max_strokes, _generate, _validate, VERSION)
    plan["web_methods"]["parallel_sweep_lanes"] = "APPLIED_connected_in_cell_snake"
    for stroke in plan["proposals"]:
        if stroke["phase"] == "detail":
            # A single source dot, with one geometric vertex.
            stroke["points"] = stroke["points"][:1]
    plan["result_sha256"] = r7.r3._digest({k:v for k,v in plan.items() if k != "result_sha256"})
    return plan
