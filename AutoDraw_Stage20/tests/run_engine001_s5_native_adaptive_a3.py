"""A3: uninterrupted measured-native same-color lanes, no artificial splitting."""
import argparse
from collections import Counter, deque
import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_s5_native_adaptive_a1 as a
import run_engine001_s5_native_adaptive_a2 as v

R=36
DIRS=((1,0),(0,1),(-1,0),(0,-1))
A2_BLOB="646211253c80e329595f0e15620bb4e238d3e1fd"
A2_COUNTS={"home":3880,"illustration":25338,"second-png":12892}


def shapes():
    result=[]
    for x,y in DIRS:
        result.extend([[(0,0),(x,y)],[(-x,-y),(0,0)]])
    for x,y in DIRS:
        for u,w in DIRS:
            if x*u+y*w<=0:
                result.append([(-x,-y),(0,0),(u,w)])
    a.require(len(result)==20,"local probe count")
    return result


def local_masks(samples):
    z=np.asarray(samples)
    a.require(z.shape==(40,73,73),"wrong local probe dimensions")
    support=(z>0).any(axis=0)
    core=(z>=128).all(axis=0)
    a.require(support.any() and core.any(),"empty local native footprint")
    a.require(not(support[0].any() or support[-1].any() or support[:,0].any()
                  or support[:,-1].any()),"local native footprint clipped")
    return support,core


def fixture(native):
    js=native.full_fixture()
    first=js.index("function renderComplexHoldoutColorProbe(")
    last=js.index("const board = makeTemporalBoard(",first)
    part=js[first:last]
    old=" ||\n          stroke.points.length > 128"
    a.require(part.count(old)==1,"unexpected fixture vertex gate")
    return js[:first]+part.replace(old,"")+js[last:]


def grid_walk(points):
    """Expand axis-aligned integer nodes; no maximum segment length."""
    if not points:
        return []
    out=[points[0]]
    for (x,y),(u,w) in zip(points,points[1:]):
        a.require(x==u or y==w,"non-axis segment")
        dx=(u>x)-(u<x);dy=(w>y)-(w<y)
        for i in range(1,abs(u-x)+abs(w-y)+1):
            out.append((x+i*dx,y+i*dy))
    return out


def measure(driver,native,out):
    samples={w:[] for w in range(1,11)}
    ledger=[]
    patterns=shapes()
    for translation in range(2):
        for start in range(0,20,8):
            name=f"local-t{translation}-s{start}"
            paths,places=[],[]
            for width in range(1,11):
                x=35+42*(width-1)+translation
                for j,shape in enumerate(patterns[start:start+8]):
                    y=18+27*j+translation
                    pts=[dict(x=x+dx,y=y+dy) for dx,dy in shape]
                    paths.append(native.stroke(pts,width,0,len(paths)))
                    places.append((width,start+j,x,y))
            raw=native.render(driver,name,paths)
            a.save_plan(out,name,paths)
            for width,idx,x,y in places:
                window=raw[3*y-R:3*y+R+1,3*x-R:3*x+R+1,3].copy()
                a.require(window.shape==(73,73) and window.any(),"empty native local sample")
                samples[width].append(window)
                ledger.append(dict(width=width,shape=idx,translation=translation,
                                   atlas=name,center=[x,y]))
    atlas={w:local_masks(s) for w,s in samples.items()}
    np.savez_compressed(out/"a3-local-alpha.npz",**{f"w{w}":np.stack(s) for w,s in samples.items()})
    a.write_json(out/"a3-probe-ledger.json",ledger)
    paths,points_by_width=[],{}
    for width in range(1,11):
        x=35+42*(width-1)
        pts=[(x-14,60),(x+14,60),(x+14,66),(x-14,66),(x-14,72)]
        points_by_width[width]=pts
        paths.append(native.stroke([dict(x=u,y=w) for u,w in pts],width,0,len(paths)))
    raw=native.render(driver,"long-serpentine-probes",paths)
    a.save_plan(out,"long-serpentine-probes",paths)
    report={}
    eligible={}
    for width,(support,core) in atlas.items():
        # Each column is 42 logical units. Probe length 28 and brush <=10;
        # verify no ink touching that column boundary (cross-contamination).
        x=35+42*(width-1)
        left=3*(x-21);right=3*(x+21)
        actual=raw[:,left:right,3]>0
        a.require(actual.any() and not actual[:,0].any() and not actual[:,-1].any(),
                  "long probe clipped/contaminated")
        predicted=np.zeros((720,1380),bool)
        for u,w in grid_walk(points_by_width[width]):
            predicted[3*w-R:3*w+R+1,3*u-R:3*u+R+1]|=support
        outside=int(np.count_nonzero(actual&~predicted[:,left:right]))
        report[str(width)]=dict(local_samples=len(samples[width]),support=int(support.sum()),
            core=int(core.sum()),long_native_support=int(actual.sum()),
            long_outside_measured_sweep=outside,eligible=outside==0)
        if outside==0:
            eligible[width]=(support,core)
    a.write_json(out/"a3-measured-atlas-summary.json",report)
    return eligible,report


def fit(mask,support):
    # Observed support only, including possible asymmetric joint footprint.
    yy,xx=np.nonzero(support)
    y0,y1=min(int(yy.min()),R),max(int(yy.max()),R)+1
    x0,x1=min(int(xx.min()),R),max(int(xx.max()),R)+1
    return cv2.erode(mask.astype(np.uint8),support[y0:y1,x0:x1].astype(np.uint8),
           anchor=(R-x0,R-y0),borderType=cv2.BORDER_CONSTANT,borderValue=0)>0


def lateral_pitch(proof,width,horizontal):
    key=("horizontal" if horizontal else "vertical")+f":{width}"
    span=proof["measurements"][key]["lateral_min_backing_px"]
    return max(1,math.floor(.8*span/3))


def lanes(mask,pitch,gain):
    """Maximal nondegenerate runs; include last occupied row."""
    occupied=np.flatnonzero(mask.any(axis=1))
    if not len(occupied):
        return []
    rows=list(range(int(occupied[0]),int(occupied[-1])+1,pitch))
    if rows[-1]!=occupied[-1]:
        rows.append(int(occupied[-1]))
    result=[]
    for index,y in enumerate(rows):
        xs=np.flatnonzero(mask[y])
        if not len(xs):
            continue
        pieces=np.split(xs,np.flatnonzero(np.diff(xs)>1)+1)
        selected=[]
        for run in pieces:
            if len(run)>=2 and gain[y,run].any():
                selected.append([(int(run[0]),y),(int(run[-1]),y)])
        if index%2:
            selected=[list(reversed(p)) for p in reversed(selected)]
        result.extend(selected)
    return result


def connect(mask,start,end):
    """BFS only inside same measured-valid component; x/y grid coords."""
    if start==end:
        return [start]
    h,w=mask.shape
    # Prefer direct axis/elbow connections, otherwise shortest graph route.
    for elbow in ((end[0],start[1]),(start[0],end[1])):
        walk=grid_walk([start,elbow,end])
        if all(mask[y,x] for x,y in walk):
            return walk
    q=deque([start])
    prev={start:None}
    while q:
        u=q.popleft()
        if u==end:
            path=[]
            while u is not None:
                path.append(u);u=prev[u]
            return path[::-1]
        for dx,dy in DIRS:
            x,y=u[0]+dx,u[1]+dy
            v=(x,y)
            if 0<=x<w and 0<=y<h and mask[y,x] and v not in prev:
                prev[v]=u;q.append(v)
    raise RuntimeError("same-component connector unavailable")


def route(mask,runs):
    walk=[]
    for run in runs:
        if walk:
            walk.extend(connect(mask,walk[-1],run[0])[1:])
            walk.extend(grid_walk(run)[1:])
        else:
            walk=grid_walk(run)
    return walk


def compress(walk):
    if len(walk)<3:
        return walk[:]
    result=[walk[0]]
    for i in range(1,len(walk)-1):
        u,x,w=walk[i-1:i+2]
        d=(x[0]-u[0],x[1]-u[1])
        e=(w[0]-x[0],w[1]-x[1])
        if d!=e:
            result.append(x)
    result.append(walk[-1])
    return result


def broad_plan(want,atlas,proof,stroke):
    paths,counts=[],{}
    colors=[c for c in np.unique(want.reshape(-1,3),axis=0) if np.any(c!=a.WHITE)]
    for color in sorted(colors,key=lambda c:-a.luma(a.rgb_int(c))):
        rgb=a.rgb_int(color)
        allowed=np.all(want==color,axis=2)
        covered=np.zeros(allowed.shape,bool)
        for width in range(10,1,-1):
            if width not in atlas:
                continue
            support,core=atlas[width]
            valid=fit(allowed,support)[::3,::3]
            # Coverage heuristic, not actual alpha; no artificial cut within lanes.
            gain=cv2.dilate((allowed&~covered).astype(np.uint8),core.astype(np.uint8),
                anchor=(R,R),borderType=cv2.BORDER_CONSTANT,borderValue=0)[::3,::3]>0
            n,labels,stats,_=cv2.connectedComponentsWithStats(valid.astype(np.uint8),connectivity=4)
            nodes=np.zeros(allowed.shape,np.uint8)
            npaths=nlane=0
            for k in range(1,n):
                x,y,w,h,_=map(int,stats[k])
                m=labels[y:y+h,x:x+w]==k
                g=gain[y:y+h,x:x+w]
                horizontal=w>=h
                if not horizontal:
                    m=m.T;g=g.T
                runs=lanes(m,lateral_pitch(proof,width,horizontal),g)
                if not runs:
                    continue
                walk=route(m,runs)
                if not horizontal:
                    walk=[(v,u) for u,v in walk]
                walk=[(u+x,v+y) for u,v in walk]
                a.require(all(valid[v,u] for u,v in walk),"invalid connector")
                for u,v in walk:
                    nodes[3*v,3*u]=1
                pts=[dict(x=a.OX/3+u,y=v) for u,v in compress(walk)]
                if len(pts)>=2:
                    paths.append(stroke(pts,width,rgb,len(paths)))
                    npaths+=1;nlane+=len(runs)
            covered|=cv2.dilate(nodes,np.flip(core).astype(np.uint8),anchor=(R,R),
                   borderType=cv2.BORDER_CONSTANT,borderValue=0)>0
            counts[f"{rgb:06x}:{width}"]=dict(components=n-1,paths=npaths,lanes=nlane)
    return paths,counts


def continuity(paths):
    lengths=[sum(math.hypot(q["x"]-p["x"],q["y"]-p["y"])
                 for p,q in zip(s["points"],s["points"][1:])) for s in paths]
    return dict(paths=len(paths),vertices=sum(len(s["points"]) for s in paths),
        max_vertices=max((len(s["points"]) for s in paths),default=0),
        multi_vertex=sum(len(s["points"])>2 for s in paths),
        longer_than_24=sum(x>24 for x in lengths),
        length_at_most_3=sum(x<=3 for x in lengths),
        longest=max(lengths,default=0),median=float(np.median(lengths)) if lengths else 0,
        total=sum(lengths))


def panel(out,original,target):
    from run_engine001_s5_native_transfer_p2 import alpha_onto_white
    cells=[("ORIGINAL",alpha_onto_white(original)),("8 GAME COLORS",Image.fromarray(target,"RGB"))]
    for title,name in (("WIDTH 1","width1"),("A1 ACCEPTED","a1"),("A3 BROAD","a3-broad"),("A3 FINAL","a3")):
        cells.append((title,Image.open(out/(name+"-crop.png"))))
    atlas=Image.new("RGB",(450*len(cells),760),(245,245,245))
    draw=ImageDraw.Draw(atlas)
    for i,(title,img) in enumerate(cells):
        img=img.convert("RGB")
        img.thumbnail((450,720),Image.Resampling.NEAREST)
        atlas.paste(img,(i*450+(450-img.width)//2,30+(720-img.height)//2))
        draw.text((i*450+10,8),title,fill=(0,0,0))
    atlas.save(out/"comparison.png")


def main(case):
    import engine001_s5_native_brush_overlap as physical
    import run_engine001_s5_native_transfer_p2 as p2
    import run_engine001_s5_originals_native_transfer as transfer
    import run_engine001_s5_wv_full_native as native
    root=native.binding.ROOT
    rel,expected=p2.CASE[case]
    for module,blob in ((physical,a.PLANNER_BLOB),(a,v.A1_BLOB),(v,A2_BLOB)):
        a.require(p2.git_blob(Path(module.__file__).read_bytes())==blob,"reference code drift")
    a.require(p2.git_blob((root/rel).read_bytes())==expected,"source drift")
    out=Path(os.environ["RUNNER_TEMP"])/("s5-adaptive-a3-"+case)
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    source=out/"source"
    native.binding.pipeline.run(root,Path(rel),source,palette_only=True)
    rgba=np.asarray(Image.open(source/"palette-8.png").convert("RGBA"))
    target=np.where((rgba[:,:,3]==255)[:,:,None],rgba[:,:,:3],255).astype(np.uint8)
    geom=transfer.layout(target.shape[1],target.shape[0])
    want,_,_=transfer.projected(target,geom)
    Image.fromarray(target,"RGB").save(out/"prepared.png")
    Image.fromarray(want,"RGB").save(out/"projected-target.png")
    results={}
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        a.require(not native.render(driver,"blank",[])[:,:,3].any(),"nonblank")
        control=[native.stroke(native.segment(200,100,12,0),4,0,0),
                 native.stroke([dict(x=x,y=y) for x,y in [(220,100),(240,100),(240,115),(220,115)]],7,0,1)]
        before=native.render(driver,"reference-original",control)
        driver.execute_script(fixture(native))
        a.require(np.array_equal(before,native.render(driver,"reference-expanded",control)),
                  "fixture drift")
        proof=physical.native_footprints(driver)
        a.write_json(out/"egret-physical-footprints.json",proof)
        stamps,_=a.measure_stamps(driver,native,out)
        baseline,params=physical.plan_same_color_overlap(target,geom,proof)
        a.require(len(baseline)==a.CASES[case],"P1 count drift")
        pad=a.width1_pad(stamps,proof)
        def save(name,paths,raw):
            a.save_plan(out,name,paths)
            m,_,_,_=transfer.score(name,raw,target,geom,out)
            results[name]=dict(**a.stats(paths),metrics=m,detail_metrics=a.diagnostics(raw,want),
                  continuity=continuity(paths),raw_sha256=a.sha(out/(name+".png")),
                  plan_sha256=a.sha(out/(name+"-plan.json.gz")))
        save("width1",baseline,native.render(driver,"width1",baseline))
        broad1,_=a.broad_plan(want,stamps,proof,native.stroke)
        raw1=native.render(driver,"a1-broad",broad1)
        save("a1-broad",broad1,raw1)
        detail1,_=a.retain_detail(baseline,want,raw1[:,a.OX:a.OX+450],pad)
        final1=a.combine(broad1,detail1)
        a.require(len(final1)==v.A1_COUNTS[case],"A1 count drift")
        save("a1",final1,native.render(driver,"a1",final1))
        atlas,summary=measure(driver,native,out)
        broad,counts=broad_plan(want,atlas,proof,native.stroke)
        raw=native.render(driver,"a3-broad",broad)
        save("a3-broad",broad,raw)
        detail,reasons=a.retain_detail(baseline,want,raw[:,a.OX:a.OX+450],pad)
        final=a.combine(broad,detail)
        a.require(final and all(1<=p["width"]<=10 and p["colorRgb"]!=0xffffff for p in final),
                  "invalid A3 plan")
        save("a3",final,native.render(driver,"a3",final))
    panel(out,Image.open(source/"01-original.png"),target)
    a.write_json(out/"a3-results.json",dict(schema="ENGINE001_S5_ADAPTIVE_A3_V1",case=case,
        sha=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],source=rel,
        source_git_blob=expected,source_sha256=a.sha(root/rel),target_sha256=a.array_sha(target),
        geometry=geom,renderer=a.RENDERER,mode="normal",smooth=False,
        p1_blob=a.PLANNER_BLOB,a1_blob=v.A1_BLOB,a2_blob=A2_BLOB,
        archived_a2_path_count=A2_COUNTS[case],reference_parameters=params,atlas=summary,
        broad_counts=counts,detail_selection=reasons,results=results,
        human_visual_review="PENDING",exact_CHALK="NOT_RUN",independent_E5="NOT_RUN",
        production_admissible=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=tuple(A2_COUNTS),required=True)
    main(parser.parse_args().case)
