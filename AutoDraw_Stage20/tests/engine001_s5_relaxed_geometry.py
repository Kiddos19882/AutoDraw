"""A9 research-only soft geometry. Native readback is evidence; masks rank MODEL_ONLY."""
import math
import cv2
import numpy as np

TREATMENTS = (("10", .1), ("20", .2), ("30", .3), ("50", .5), ("free", None))
DIRS = ((1,0), (0,1), (1,1), (1,-1))
WHITE = np.array([255,255,255], np.uint8)
ORIGIN_X = 155
R = 36


def correlate(image, kernel):
    return cv2.filter2D(image.astype(np.float32), cv2.CV_32F,
                       kernel.astype(np.float32), anchor=(R,R),
                       borderType=cv2.BORDER_CONSTANT)


def candidate_mask(target, support, core, tolerance):
    """A tolerance is a proxy fraction of entire measured support, not native leakage."""
    hits = correlate(target, core)
    valid = hits > .5
    if tolerance is not None:
        valid &= correlate(target, support) >= support.sum() * (1-tolerance) - .01
    return valid


def runs_for_direction(valid, benefit, direction, pitch):
    """Maximal runs on a backing-pixel lattice; no minimum length filter."""
    dyx = np.argwhere(valid)
    if not len(dyx):
        return []
    y, x = dyx.T
    dx, dy = direction
    cross = dx*y - dy*x
    along = dx*x + dy*y
    scores = benefit[y,x]
    phases = cross % pitch
    phase = int(np.argmax(np.bincount(phases, weights=np.maximum(scores,0),
                                      minlength=pitch)))
    keep = phases == phase
    x,y,cross,along,scores = (v[keep] for v in (x,y,cross,along,scores))
    order = np.lexsort((along,cross))
    x,y,cross,along,scores = (v[order] for v in (x,y,cross,along,scores))
    breaks = np.flatnonzero((np.diff(cross)!=0) |
                            (np.diff(along)!=dx*dx+dy*dy))+1
    bounds = np.r_[0,breaks,len(x)]
    runs = []
    for l,h in zip(bounds[:-1],bounds[1:]):
        if h<=l or not np.any(scores[l:h]>0):
            continue
        runs.append(((int(x[l]),int(y[l])), (int(x[h-1]),int(y[h-1]))))
    return runs


def tap_end(point, shape):
    x,y = point
    return (x+1,y) if x+1<shape[1] else ((x-1,y) if x else (x,y+1 if y+1<shape[0] else y-1))


def sweep(runs, core, shape):
    nodes = np.zeros(shape,np.uint8)
    for start,end in runs:
        if start == end:
            end = tap_end(start,shape)
        cv2.line(nodes,start,end,1,1,cv2.LINE_8)
    return cv2.dilate(nodes,np.flip(core).astype(np.uint8).copy(),anchor=(R,R),
                      borderType=cv2.BORDER_CONSTANT,borderValue=0)>0


def choose(valid, benefit, delta, core, pitch):
    best,rank = None,None
    for direction in DIRS:
        stride = max(1,int(round(pitch*math.hypot(*direction))))
        runs = runs_for_direction(valid,benefit,direction,stride)
        if not runs:
            continue
        mask = sweep(runs,core,valid.shape)
        improvement = int(delta[mask].sum(dtype=np.int64))
        length = sum(math.dist(u,v) for u,v in runs)
        key = (improvement,-len(runs),-length)
        if improvement>0 and (rank is None or key>rank):
            best,rank = (runs,mask,direction,improvement),key
    return best


def plan(want, atlas, proof, stroke, tolerance, actual=None, repair=False, offset=0):
    current = np.full_like(want,255) if actual is None else actual.copy()
    colors, areas = np.unique(want.reshape(-1,3),axis=0,return_counts=True)
    order = sorted(range(len(colors)),key=lambda i:(np.all(colors[i]==WHITE),-int(areas[i]),tuple(colors[i])))
    target16 = want.astype(np.int16)
    paths,ledger = [],[]
    for i in order:
        color=colors[i]
        if not repair and np.all(color==WHITE):
            continue
        target=np.all(want==color,axis=2)
        new_error=np.abs(target16-color.astype(np.int16)).sum(axis=2)
        for width in ((4,) if repair else range(10,3,-1)):
            if width not in atlas:
                continue
            support,core=atlas[width]
            old_error=np.abs(current.astype(np.int16)-target16).sum(axis=2)
            delta=(old_error-new_error).astype(np.int32)
            if not np.any(delta>0):
                continue
            benefit=correlate(delta,core)
            valid=candidate_mask(target,support,core,tolerance)
            if not np.any(valid & (benefit>0)):
                continue
            spans=[proof["measurements"][f"{d}:{width}"]["lateral_min_backing_px"]
                   for d in ("horizontal","vertical")]
            pitch=max(1,math.floor(.8*min(spans)))
            selected=choose(valid,benefit,delta,core,pitch)
            if selected is None:
                continue
            runs,mask,direction,improvement=selected
            rgb=int.from_bytes(bytes(color),"big")
            taps=0
            for start,end in runs:
                if start==end:
                    taps+=1
                    end=tap_end(start,want.shape[:2])
                points=[dict(x=ORIGIN_X+x/3,y=y/3) for x,y in (start,end)]
                paths.append(stroke(points,width,rgb,offset+len(paths)))
            current[mask]=color
            ledger.append(dict(width=width,color=rgb,direction=direction,
                               lanes=len(runs),taps=taps,pitch_backing=pitch,
                               predicted_rgb_improvement=improvement,
                               candidate_centers=int(valid.sum())))
    return paths,ledger


def validate(paths):
    for s in paths:
        if s["width"] not in range(4,11) or len(s["points"])<2:
            raise ValueError("A9 forbidden brush or invalid path")
        if not all(0<=p["x"]<460 and 0<=p["y"]<240 for p in s["points"]):
            raise ValueError("A9 point outside board")
