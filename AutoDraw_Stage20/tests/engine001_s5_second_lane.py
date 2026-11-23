"""Find two connected parallel sweeps inside exactly the original sweep cell."""
from functools import lru_cache

import numpy as np
from scipy.ndimage import binary_erosion

import engine001_bpred_s5r2_region_candidates as source


@lru_cache(maxsize=9)
def stamp(width):
    radius = width
    size = 2 * radius + 1
    points = [(radius, radius)]
    kernel = np.zeros((size, size), bool)
    for x, y in source.swept_capsule_pixel_masks(points,width,1,1,size,size)["potential_cells"]:
        kernel[y,x] = True
    return kernel


def second_lane(proposal, cell):
    """Search both orientations, widths 2..original width; retain one verified gain."""
    # Use a tight local rectangle to keep the per-cell masks small.
    spans = cell["spans"]
    left = min(s[1] for s in spans)
    top = min(s[0] for s in spans)
    mask = np.zeros((max(s[0] for s in spans)-top+1,
                     max(s[2] for s in spans)-left+1), bool)
    for row, x0, x1 in spans:
        mask[row-top, x0-left:x1-left+1] = True
    if proposal["axis"] == 90:
        mask = mask.T
        left, top = top, left
    # Padding makes excursions beyond the source-cell bounding box observable.
    pad = 6
    mask = np.pad(mask, pad)
    left -= pad
    top -= pad
    height,width = mask.shape

    def footprint(path, brush):
        return source.swept_capsule_pixel_masks(path,brush,1,1,width,height)["potential_cells"]

    original = [(x-left,y-top) for x,y in proposal["points"]]
    baseline = footprint(original, proposal["width"])
    status = "no_two_spaced_lanes"
    evidence = []
    for brush in range(proposal["width"],1,-1):
        centers = binary_erosion(mask, structure=stamp(brush))
        for axis in (proposal["axis"], 90-proposal["axis"]):
            rows = centers.T if axis else centers
            lanes = []
            best = None
            for y,row in enumerate(rows):
                changes = np.flatnonzero(np.diff(row, prepend=False, append=False))
                for lo, stop in zip(changes[::2], changes[1::2]):
                    if stop-lo < 4:
                        continue
                    current = (int(lo), int(stop-1), y)
                    for x0,x1,y0 in lanes:
                        if y-y0 < brush:
                            continue
                        if status == "no_two_spaced_lanes":
                            status = "no_gainful_safe_join"
                        for a,b,c,d in ((x0,x1,current[1],current[0]),
                                        (x1,x0,current[0],current[1])):
                            path = [(a,y0),(b,y0),(c,y),(d,y)]
                            if axis:
                                path = [(v,u) for u,v in path]
                            ink = footprint(path, brush)
                            if any(not mask[py,px] for px,py in ink):
                                continue
                            gain = len(ink-baseline)
                            if gain and (best is None or gain > best["gain"]):
                                best = dict(width=brush, axis=axis, gain=gain,
                                            points=[(x+left,py+top) for x,py in path])
                    lanes.append(current)
            if best is not None:
                evidence.append(best)
    return evidence, ("found" if evidence else status)
