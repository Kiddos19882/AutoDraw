"""A14 route alternatives: source-center geometry only, never native coverage."""
import math
from collections import defaultdict
import numpy as np
from scipy import ndimage as ndi

VARIANTS=("a","b","c24","c48","c96","cfree","d","e","f")
CROSS=ndi.generate_binary_structure(2,1)
DIRS=((1,0),(0,1),(-1,0),(0,-1))

def runs(mask,vertical=False):
    m=mask.T if vertical else mask
    for y,row in enumerate(m):
        edges=np.flatnonzero(np.diff(np.r_[False,row,False].astype(np.int8)))
        for x,z in zip(edges[::2],edges[1::2]):
            yield [(y,i) if vertical else (i,y) for i in range(x,z)]

def pieces(lane,scale,proof,vertical,length):
    if length is None:
        return [lane]
    span=proof["measurements"][("vertical" if vertical else "horizontal")+":1"]["axial_min_backing_px"]/3
    chunk=max(3,math.ceil(length/scale)+1)
    # Preserve P2 overlap for length 12; larger length extrapolates axial span
    # by centerline length difference, explicitly a hypothesis for native test.
    advance=max(1,min(math.floor(.75*(chunk-1)),math.floor(.8*(span+length-12)/scale)))
    result=[]
    start=0
    while start<len(lane):
        stop=min(len(lane),start+chunk)
        result.append(lane[start:stop])
        if stop==len(lane):
            break
        start=min(stop-1,start+advance)
    return result

def axis(mask,scale,proof,vertical=False,length=None):
    return [p for lane in runs(mask,vertical) for p in pieces(lane,scale,proof,vertical,length)]

def neighbors(p):
    x,y=p
    return [(x+dx,y+dy) for dx,dy in DIRS]

def join(lanes):
    """Greedy endpoint adjacency; only actual 4-neighbor lane cells."""
    endpoints=defaultdict(set)
    for i,lane in enumerate(lanes):
        endpoints[lane[0]].add(i)
        endpoints[lane[-1]].add(i)
    remaining=set(range(len(lanes)))
    result=[]
    for seed in range(len(lanes)):
        if seed not in remaining:
            continue
        walk=list(lanes[seed])
        remaining.remove(seed)
        while True:
            candidates=[(i,p) for p in neighbors(walk[-1]) for i in endpoints.get(p,()) if i in remaining]
            if not candidates:
                break
            i,p=min(candidates)
            lane=lanes[i]
            walk.extend(lane if lane[0]==p else lane[::-1])
            remaining.remove(i)
        result.append(walk)
    return result

def shells(mask):
    """Nested 4-neighbor boundary shells, greedy contiguous graph trails."""
    current=mask.copy()
    result=[]
    while current.any():
        inner=ndi.binary_erosion(current,structure=CROSS,border_value=0)
        ys,xs=np.nonzero(current&~inner)
        remaining=set(zip(xs.tolist(),ys.tolist()))
        for seed in sorted(remaining,key=lambda p:(p[1],p[0])):
            if seed not in remaining:
                continue
            walk=[seed]
            remaining.remove(seed)
            while True:
                choices=[p for p in neighbors(walk[-1]) if p in remaining]
                if not choices:
                    break
                p=min(choices,key=lambda p:(sum(q in remaining for q in neighbors(p)),p[1],p[0]))
                remaining.remove(p)
                walk.append(p)
            result.append(walk)
        current=inner
    return result

def compress(walk):
    if len(walk)<3:
        return walk[:]
    result=[walk[0]]
    for a,b,c in zip(walk,walk[1:],walk[2:]):
        if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):
            result.append(b)
    return result+[walk[-1]]

def cost(walks):
    return sum(max(2,len(compress(w))) for w in walks)

def choose(mask,scale,proof,variant):
    if variant=="b":
        h=axis(mask,scale,proof,False,12)
        v=axis(mask,scale,proof,True,12)
        return min((h,v),key=len)
    if variant.startswith("c"):
        return axis(mask,scale,proof,False,None if variant=="cfree" else int(variant[1:]))
    if variant=="d":
        return join(axis(mask,scale,proof))
    if variant=="e":
        return shells(mask)
    if variant=="f":
        h=join(axis(mask,scale,proof))
        v=join(axis(mask,scale,proof,True))
        e=shells(mask)
        return min((h,v,e),key=lambda w:(cost(w),len(w)))
    raise ValueError(variant)

def plan(target,g,proof,variant,stroke,segment):
    scale=g["scale"]
    # All four historical A14 projections fit native measured pitch.
    for direction in ("horizontal","vertical"):
        lateral=proof["measurements"][direction+":1"]["lateral_min_backing_px"]/3
        if not 0<scale<=.8*lateral:
            raise ValueError("unsupported source pitch; do not silently drop subrows")
    result=[]
    colors=[c for c in np.unique(target.reshape(-1,3),axis=0) if np.any(c!=255)]
    colors.sort(key=lambda c:-sum(int(v)*k for v,k in zip(c,(2126,7152,722))))
    for color in colors:
        mask=np.all(target==color,axis=2)
        labels,n=ndi.label(mask,structure=CROSS)
        for k,sl in enumerate(ndi.find_objects(labels),1):
            local=labels[sl]==k
            walks=choose(local,scale,proof,variant)
            visited=np.zeros(local.shape,bool)
            rgb=int.from_bytes(bytes(color),"big")
            for walk in walks:
                for x,y in walk:
                    assert local[y,x]
                    visited[y,x]=True
                assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(walk,walk[1:]))
                pts=compress(walk)
                board=[dict(x=g["left"]+scale*(x+sl[1].start+.5),
                            y=g["top"]+scale*(y+sl[0].start+.5)) for x,y in pts]
                if len(board)==1:
                    board=segment(board[0]["x"],board[0]["y"],.5,0)
                result.append(stroke(board,1,rgb,len(result)))
            assert np.array_equal(visited,local)
    return result

def contracts():
    proof={"measurements":{d+":1":{"axial_min_backing_px":38,"lateral_min_backing_px":3} for d in ("horizontal","vertical")}}
    m=np.zeros((35,45),bool)
    m[2:33,3:40]=True
    m[7:28,8:35]=False
    m[15,8:35]=True
    m[0,0]=True
    for variant in VARIANTS[1:]:
        walks=choose(m,.3,proof,variant)
        seen=set(p for w in walks for p in w)
        assert seen==set(zip(*np.nonzero(m.T)))
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for w in walks for a,b in zip(w,w[1:]))
        assert walks==choose(m,.3,proof,variant)
        assert all(len(compress(w))>=1 for w in walks)
    assert len(axis(np.ones((1,300),bool),.3,proof,length=24))<len(axis(np.ones((1,300),bool),.3,proof,length=12))
    # Alternating unit steps create more than 128 genuine turns.
    walk=[(0,0)]
    for i in range(511):
        x,y=walk[-1]
        walk.append((x+1,y) if i%2==0 else (x,y+1))
    assert len(compress(walk))==512 and cost([walk])==512
    staircase=np.zeros((257,257,3),np.uint8)+255
    for x,y in walk:
        staircase[y,x]=0
    planned=plan(staircase,dict(left=155,top=0,scale=.3),proof,"e",
                 lambda pts,width,rgb,i:dict(points=pts,width=width,colorRgb=rgb),
                 lambda x,y,dx,dy:[dict(x=x-dx/2,y=y),dict(x=x+dx/2,y=y)])
    assert len(planned)==1 and len(planned[0]["points"])==512
    print("A14 route source contracts PASS; one 512-vertex stroke preserved")
if __name__=="__main__":
    contracts()
