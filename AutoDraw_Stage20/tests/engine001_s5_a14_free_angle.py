"""Free-angle proposals; only native replay measures or accepts coverage."""
import math
from collections import defaultdict
import numpy as np
from scipy.spatial import cKDTree
from scipy import ndimage as ndi
import engine001_s5_a14_routes as base

VARIANTS=("f","f1","f2","f3","f4","f5","f6")
D8=base.DIRS+((1,1),(1,-1),(-1,1),(-1,-1))

def visible(a,b,mask):
    # Source-color centerline filter, not a brush footprint estimate.
    n=max(1,math.ceil(4*max(abs(b[0]-a[0]),abs(b[1]-a[1]))))
    for t in range(n+1):
        x=math.floor(a[0]+(b[0]-a[0])*t/n+.5)
        y=math.floor(a[1]+(b[1]-a[1])*t/n+.5)
        if not (0<=y<mask.shape[0] and 0<=x<mask.shape[1] and mask[y,x]):
            return False
    return True

def diagonal(mask):
    ys,xs=np.nonzero(mask)
    remaining=set(zip(xs.tolist(),ys.tolist()))
    def adj(p):
        x,y=p
        return [(x+dx,y+dy) for dx,dy in D8 if (x+dx,y+dy) in remaining]
    walks=[]
    for seed in sorted(remaining,key=lambda p:(p[1],p[0])):
        if seed not in remaining:
            continue
        remaining.remove(seed)
        walk=[seed]
        while True:
            choices=adj(walk[-1])
            if not choices:
                break
            p=min(choices,key=lambda p:(len(adj(p)),p[1],p[0]))
            remaining.remove(p)
            walk.append(p)
        walks.append(walk)
    assert sum(map(len,walks))==int(mask.sum())
    return walks

def shortcut(walk,mask):
    if len(walk)<3:
        return walk[:]
    result=[walk[0]]
    i=0
    while i<len(walk)-1:
        # Bounded search effort, not a limit on stroke length.
        j=min(len(walk)-1,i+64)
        while j>i+1 and not visible(walk[i],walk[j],mask):
            j-=1
        if not visible(walk[i],walk[j],mask):
            j=i+1
        result.append(walk[j])
        i=j
    return result

def rdp(walk,mask,tolerance=1.0):
    if len(walk)<3:
        return walk[:]
    pts=np.asarray(walk,dtype=float)
    keep={0,len(walk)-1}
    stack=[(0,len(walk)-1)]
    while stack:
        i,j=stack.pop()
        if j<=i+1:
            continue
        v=pts[j]-pts[i]
        d=pts[i+1:j]-pts[i]
        denom=float(v@v)
        delta=d-np.clip(d@v/denom,0,1)[:,None]*v if denom else d
        ds=np.sum(delta*delta,axis=1)
        k=i+1+int(ds.argmax())
        if ds.max()<=tolerance*tolerance and visible(walk[i],walk[j],mask):
            continue
        keep.add(k)
        stack.extend(((i,k),(k,j)))
    return [walk[i] for i in sorted(keep)]

def connect(walks,mask,radius=4):
    if not walks:
        return []
    ends=[p for w in walks for p in (w[0],w[-1])]
    tree=cKDTree(ends)
    remaining=set(range(len(walks)))
    result=[]
    for i in range(len(walks)):
        if i not in remaining:
            continue
        remaining.remove(i)
        walk=list(walks[i])
        while True:
            end=walk[-1]
            candidates=sorted(tree.query_ball_point(end,radius),
                              key=lambda k:(math.dist(end,ends[k]),k))
            for k in candidates:
                j=k//2
                if j in remaining and visible(end,ends[k],mask):
                    lane=walks[j] if k%2==0 else walks[j][::-1]
                    walk.extend(lane[1:] if end==lane[0] else lane)
                    remaining.remove(j)
                    break
            else:
                break
        result.append(walk)
    return result

def proposals(target,g,proof,variant,stroke,segment):
    if variant in ("f","f5"):
        return base.plan(target,g,proof,"f",stroke,segment)
    result=[]
    colors=[c for c in np.unique(target.reshape(-1,3),axis=0) if np.any(c!=255)]
    colors.sort(key=lambda c:-sum(int(v)*k for v,k in zip(c,(2126,7152,722))))
    for color in colors:
        mask=np.all(target==color,axis=2)
        labels,_=ndi.label(mask,structure=np.ones((3,3),bool) if variant in ("f1","f6") else base.CROSS)
        for k,sl in enumerate(ndi.find_objects(labels),1):
            local=labels[sl]==k
            if variant in ("f1","f6"):
                walks=diagonal(local)
            else:
                walks=base.choose(local,g["scale"],proof,"f")
            walks=[base.compress(w) for w in walks]
            if variant in ("f2","f6"):
                walks=[shortcut(w,local) for w in walks]
            if variant in ("f3","f6"):
                walks=[rdp(w,local) for w in walks]
            if variant in ("f4","f6"):
                walks=connect(walks,local)
            rgb=int.from_bytes(bytes(color),"big")
            for walk in walks:
                pts=[dict(x=g["left"]+g["scale"]*(x+sl[1].start+.5),
                          y=g["top"]+g["scale"]*(y+sl[0].start+.5)) for x,y in walk]
                pts=[p for i,p in enumerate(pts) if i==0 or p!=pts[i-1]]
                if len(pts)==1:
                    pts=segment(pts[0]["x"],pts[0]["y"],.5,0)
                result.append(stroke(pts,1,rgb,len(result)))
    return result

def native_prune(paths,reference,replay,rounds=12):
    """Delete only when actual complete Egret RGBA is pixel-identical."""
    # First try short paths, distribute batches over original plan.
    order=sorted(range(len(paths)),key=lambda i:(len(paths[i]["points"]),i))
    live=set(range(len(paths)))
    trials=[]
    for n,group in enumerate(np.array_split(order,rounds)):
        removed=live.intersection(map(int,group))
        if not removed or len(removed)==len(live):
            continue
        candidate=[p for i,p in enumerate(paths) if i in live and i not in removed]
        actual=replay(n,candidate)
        accepted=bool(np.array_equal(actual,reference))
        if accepted:
            live.difference_update(removed)
        trials.append(dict(batch=n,attempted=len(removed),accepted=accepted,
                           remaining=len(live),different_pixels=int(np.any(actual!=reference,axis=2).sum())))
    return [p for i,p in enumerate(paths) if i in live],trials

def contracts():
    m=np.eye(20,dtype=bool)
    w=diagonal(m)
    assert len(w)==1 and len(w[0])==20
    assert len(shortcut(w[0],m))==2
    assert len(rdp(w[0],m))==2
    m=np.ones((10,10),bool);m[4:6,4:6]=False
    assert not visible((0,0),(9,9),m)
    assert len(connect([[(0,0),(1,0)],[(3,0),(4,0)]],m))==1
    p=[dict(points=[0,1]),dict(points=[2,3])]
    rgba=np.zeros((2,2,4),np.uint8)
    out,log=native_prune(p,rgba,lambda n,c:rgba.copy(),2)
    assert len(out)==1 and log[0]["accepted"]
    print("F1-F6 proposal and exact native replay gate contracts PASS")

if __name__=="__main__":
    contracts()
