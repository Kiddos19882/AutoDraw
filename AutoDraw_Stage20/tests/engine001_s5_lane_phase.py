"""A7: phase/orientation ablation with measured Egret support; research only."""
import cv2
import numpy as np
import run_engine001_s5_native_adaptive_a1 as a
import run_engine001_s5_native_adaptive_a3 as p
import run_engine001_s5_native_adaptive_a4 as q


def phase_lanes(mask, pitch, phase, gain):
    """Whole maximal lanes, no segmentation by gain."""
    occupied = np.flatnonzero(mask.any(axis=1))
    if not len(occupied):
        return []
    lo, hi = map(int, (occupied[0], occupied[-1]))
    rows = sorted({lo, hi, *range(lo + phase, hi + 1, pitch)})
    result = []
    for i, y in enumerate(rows):
        xs = np.flatnonzero(mask[y])
        runs = [[(int(v[0]), y), (int(v[-1]), y)]
                for v in np.split(xs, np.flatnonzero(np.diff(xs) > 1) + 1)
                if len(v) >= 2 and gain[y, v].any()]
        if i % 2:
            runs = [list(reversed(v)) for v in reversed(runs)]
        result.extend(runs)
    return result


def choose_lanes(mask, gain, residual, core, proof, width, x, y):
    """Score measured core union of lanes (not connectors), local backing ROI."""
    h, w = mask.shape
    radius = p.R
    left, top = max(0, 3*x-radius), max(0, 3*y-radius)
    right = min(residual.shape[1], 3*(x+w-1)+radius+1)
    bottom = min(residual.shape[0], 3*(y+h-1)+radius+1)
    local = residual[top:bottom, left:right]
    kernel = np.flip(core).astype(np.uint8).copy()
    best, best_rank, log = None, None, []
    # Keep the original bounding-box direction and phase zero first on exact ties.
    for horizontal in (w >= h, w < h):
        m, g = (mask, gain) if horizontal else (mask.T, gain.T)
        pitch = p.lateral_pitch(proof, width, horizontal)
        for phase in range(pitch):
            runs = phase_lanes(m, pitch, phase, g)
            if not runs:
                continue
            nodes = np.zeros(local.shape, np.uint8)
            length = 0
            for run in runs:
                length += abs(run[1][0]-run[0][0])
                for u, v in p.grid_walk(run):
                    if not horizontal:
                        u, v = v, u
                    nodes[3*(y+v)-top, 3*(x+u)-left] = 1
            covered = cv2.dilate(nodes, kernel, anchor=(radius,radius),
                                 borderType=cv2.BORDER_CONSTANT,borderValue=0)>0
            new = int(np.count_nonzero(covered & local))
            rank = (new, -len(runs), -length)
            log.append(dict(horizontal=horizontal, phase=phase, pitch=pitch,
                            new_core_pixels=new, lanes=len(runs), lane_length=length))
            if best_rank is None or rank > best_rank:
                best, best_rank = (horizontal, runs, log[-1]), rank
    return best, log


def broad_plan(want, atlas, proof, stroke):
    paths, counts, ledger = [], {}, []
    colors = [c for c in np.unique(want.reshape(-1,3),axis=0) if np.any(c!=a.WHITE)]
    for color in sorted(colors,key=lambda c:-a.luma(a.rgb_int(c))):
        rgb = a.rgb_int(color)
        allowed = np.all(want==color,axis=2)
        covered = np.zeros(allowed.shape,bool)
        for width in range(10,1,-1):
            if width not in atlas:
                continue
            support, core = atlas[width]
            valid = p.fit(allowed,support)[::3,::3]
            residual = allowed & ~covered
            gain = cv2.dilate(residual.astype(np.uint8),core.astype(np.uint8),
                    anchor=(p.R,p.R),borderType=cv2.BORDER_CONSTANT,borderValue=0)[::3,::3]>0
            n, labels, stats, _ = cv2.connectedComponentsWithStats(valid.astype(np.uint8),connectivity=4)
            nodes = np.zeros(allowed.shape,np.uint8)
            npaths = nlane = 0
            for k in range(1,n):
                x,y,w,h,_ = map(int,stats[k])
                mask = labels[y:y+h,x:x+w]==k
                g = gain[y:y+h,x:x+w]
                best, candidates = choose_lanes(mask,g,residual,core,proof,width,x,y)
                if best is None:
                    continue
                horizontal,runs,chosen = best
                m = mask if horizontal else mask.T
                old, walk, order, changed = q.choose_route(m,runs)
                if not horizontal:
                    walk = [(v,u) for u,v in walk]
                walk = [(u+x,v+y) for u,v in walk]
                a.require(all(valid[v,u] for u,v in walk),"A7 invalid connector")
                for u,v in walk:
                    nodes[3*v,3*u]=1
                pts = [dict(x=a.OX/3+u,y=v) for u,v in p.compress(walk)]
                if len(pts)>=2:
                    paths.append(stroke(pts,width,rgb,len(paths)))
                    npaths+=1
                    nlane+=len(runs)
                    ledger.append(dict(color=rgb,width=width,component=k,chosen=chosen,
                        candidates=candidates,old_route_cost=q.cost(old),route_cost=q.cost(walk),
                        local_selected=changed,order=order))
            covered |= cv2.dilate(nodes,np.flip(core).astype(np.uint8).copy(),anchor=(p.R,p.R),
                         borderType=cv2.BORDER_CONSTANT,borderValue=0)>0
            counts[f"{rgb:06x}:{width}"]=dict(components=n-1,paths=npaths,lanes=nlane)
    return paths, counts, ledger
