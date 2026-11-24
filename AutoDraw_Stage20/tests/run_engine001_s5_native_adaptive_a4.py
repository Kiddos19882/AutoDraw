"""A4: local graph ordering of unchanged A3 maximal lanes; research only."""
import argparse
from collections import deque, Counter
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
import run_engine001_s5_native_adaptive_a3 as p
import run_engine001_s5_native_adaptive_a1 as a
import run_engine001_s5_native_adaptive_a2 as v

A3_BLOB="10b9d4855bf572e6937547a22d5ab5b8a3f3cec4"
A3_COUNTS={"home":(46,2361),"illustration":(312,23262),"second-png":(377,11901)}
R=p.R

def edge(u,w):
    return tuple(sorted((u,w)))

def cost(walk):
    edges=[edge(u,w) for u,w in zip(walk,walk[1:])]
    return len(edges),len(edges)-len(set(edges))

def nearest(mask,start,targets,used):
    """Shortest graph connector to any remaining endpoint; prefer unused edges on ties."""
    h,w=mask.shape
    q=deque([start])
    prev={start:None}
    while q:
        u=q.popleft()
        if u in targets:
            end=u
            path=[]
            while u is not None:
                path.append(u)
                u=prev[u]
            return end,path[::-1]
        candidates=[(u[0]+dx,u[1]+dy) for dx,dy in p.DIRS]
        candidates.sort(key=lambda z: edge(u,z) in used)
        for z in candidates:
            x,y=z
            if 0<=x<w and 0<=y<h and mask[y,x] and z not in prev:
                prev[z]=u
                q.append(z)
    raise RuntimeError("remaining lane unreachable")

def local_route(mask,runs):
    if not runs:
        return [],[]
    walk=p.grid_walk(runs[0])
    order=[(0,False)]
    used={edge(u,w) for u,w in zip(walk,walk[1:])}
    targets={}
    for i,(u,w) in enumerate(runs[1:],1):
        a.require(u not in targets and w not in targets and u!=w,"duplicate lane endpoint")
        targets[u]=(i,False)
        targets[w]=(i,True)
    while targets:
        end,connector=nearest(mask,walk[-1],targets,used)
        i,reverse=targets[end]
        u,w=runs[i]
        del targets[u]
        del targets[w]
        lane=p.grid_walk([w,u] if reverse else [u,w])
        step=connector+lane[1:]
        used.update(edge(x,y) for x,y in zip(step,step[1:]))
        walk.extend(step[1:])
        order.append((i,reverse))
    return walk,order

def choose_route(mask,runs):
    old=p.route(mask,runs)
    new,order=local_route(mask,runs)
    if cost(new)<cost(old):
        return old,new,order,True
    return old,old,[(i,False) for i in range(len(runs))],False

def route_metrics(paths):
    edges=Counter()
    for s in paths:
        pts=[(round(q["x"]-a.OX/3),round(q["y"])) for q in s["points"]]
        walk=p.grid_walk(pts)
        edges.update((s["colorRgb"],s["width"],edge(u,w)) for u,w in zip(walk,walk[1:]))
    return dict(total_edges=sum(edges.values()),unique_edges=len(edges),
                repeated_edges=sum(edges.values())-len(edges))

def broad_plan(want,atlas,proof,stroke):
    paths,alternative,counts,ledger=[],[],{},[]
    colors=[c for c in np.unique(want.reshape(-1,3),axis=0) if np.any(c!=a.WHITE)]
    for color in sorted(colors,key=lambda c:-a.luma(a.rgb_int(c))):
        rgb=a.rgb_int(color)
        allowed=np.all(want==color,axis=2)
        covered=np.zeros(allowed.shape,bool)
        for width in range(10,1,-1):
            if width not in atlas:
                continue
            support,core=atlas[width]
            valid=p.fit(allowed,support)[::3,::3]
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
                runs=p.lanes(m,p.lateral_pitch(proof,width,horizontal),g)
                if not runs:
                    continue
                walk,new,order,changed=choose_route(m,runs)
                ledger.append(dict(color=rgb,width=width,component=k,lanes=len(runs),
                    old_cost=cost(walk),new_cost=cost(new),local_selected=changed,order=order))
                if not horizontal:
                    walk=[(v,u) for u,v in walk]
                    new=[(v,u) for u,v in new]
                walk=[(u+x,v+y) for u,v in walk]
                new=[(u+x,v+y) for u,v in new]
                a.require(all(valid[v,u] for u,v in new),"invalid local connector")
                a.require(all(valid[v,u] for u,v in walk),"invalid connector")
                for u,v in walk:
                    nodes[3*v,3*u]=1
                pts=[dict(x=a.OX/3+u,y=v) for u,v in p.compress(walk)]
                if len(pts)>=2:
                    paths.append(stroke(pts,width,rgb,len(paths)))
                    alt_pts=[dict(x=a.OX/3+u,y=v) for u,v in p.compress(new)]
                    a.require(len(alt_pts)>=2,"lost lane")
                    alternative.append(stroke(alt_pts,width,rgb,len(alternative)))
                    npaths+=1;nlane+=len(runs)
            covered|=cv2.dilate(nodes,np.flip(core).astype(np.uint8),anchor=(R,R),
                   borderType=cv2.BORDER_CONSTANT,borderValue=0)>0
            counts[f"{rgb:06x}:{width}"]=dict(components=n-1,paths=npaths,lanes=nlane)
    return paths,alternative,counts,ledger


def panel(out,original,target):
    from run_engine001_s5_native_transfer_p2 import alpha_onto_white
    cells=[("ORIGINAL",alpha_onto_white(original)),("8 GAME COLORS",Image.fromarray(target,"RGB"))]
    for title,name in (("WIDTH 1","width1"),("A1 ACCEPTED","a1"),("A3 FINAL","a3"),("A4 BROAD","a4-broad"),("A4 FINAL","a4")):
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
    for module,blob in ((physical,a.PLANNER_BLOB),(a,v.A1_BLOB),(v,p.A2_BLOB),(p,A3_BLOB)):
        a.require(p2.git_blob(Path(module.__file__).read_bytes())==blob,"reference code drift")
    a.require(p2.git_blob((root/rel).read_bytes())==expected,"source drift")
    out=Path(os.environ["RUNNER_TEMP"])/("s5-adaptive-a4-"+case)
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
        driver.execute_script(p.fixture(native))
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
                  continuity=p.continuity(paths),raw_sha256=a.sha(out/(name+".png")),
                  plan_sha256=a.sha(out/(name+"-plan.json.gz")))
        save("width1",baseline,native.render(driver,"width1",baseline))
        broad1,_=a.broad_plan(want,stamps,proof,native.stroke)
        raw1=native.render(driver,"a1-broad",broad1)
        save("a1-broad",broad1,raw1)
        detail1,_=a.retain_detail(baseline,want,raw1[:,a.OX:a.OX+450],pad)
        final1=a.combine(broad1,detail1)
        a.require(len(final1)==v.A1_COUNTS[case],"A1 count drift")
        save("a1",final1,native.render(driver,"a1",final1))
        atlas,summary=p.measure(driver,native,out)
        broad,alternative,counts,ledger=broad_plan(want,atlas,proof,native.stroke)
        raw=native.render(driver,"a3-broad",broad)
        save("a3-broad",broad,raw)
        detail,reasons=a.retain_detail(baseline,want,raw[:,a.OX:a.OX+450],pad)
        final=a.combine(broad,detail)
        a.require(final and all(1<=p["width"]<=10 and p["colorRgb"]!=0xffffff for p in final),
                  "invalid A3 plan")
        save("a3",final,native.render(driver,"a3",final))
        a.require((len(broad),len(final))==A3_COUNTS[case],"A3 count drift")
        reference,ref_counts=p.broad_plan(want,atlas,proof,native.stroke)
        a.require(broad==reference and counts==ref_counts,"A3 plan drift")
        a.require([(s["width"],s["colorRgb"]) for s in broad]==
                  [(s["width"],s["colorRgb"]) for s in alternative],"A4 allocation drift")
        raw4=native.render(driver,"a4-broad",alternative)
        save("a4-broad",alternative,raw4)
        detail4,reasons4=a.retain_detail(baseline,want,raw4[:,a.OX:a.OX+450],pad)
        final4=a.combine(alternative,detail4)
        a.require(final4 and all(1<=s["width"]<=10 and s["colorRgb"]!=0xffffff for s in final4),
                  "invalid A4 plan")
        save("a4",final4,native.render(driver,"a4",final4))
        metrics3=route_metrics(broad)
        metrics4=route_metrics(alternative)
        a.require(metrics4["total_edges"]<=metrics3["total_edges"],"A4 length increased")
        a.write_json(out/"a4-route-ledger.json",ledger)
    panel(out,Image.open(source/"01-original.png"),target)
    a.write_json(out/"a4-results.json",dict(schema="ENGINE001_S5_ADAPTIVE_A4_V1",case=case,
        sha=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],source=rel,
        source_git_blob=expected,source_sha256=a.sha(root/rel),target_sha256=a.array_sha(target),
        geometry=geom,renderer=a.RENDERER,mode="normal",smooth=False,
        p1_blob=a.PLANNER_BLOB,a1_blob=v.A1_BLOB,a2_blob=p.A2_BLOB,a3_blob=A3_BLOB,
        archived_a2_path_count=p.A2_COUNTS[case],reference_parameters=params,atlas=summary,
        broad_counts=counts,detail_selection=reasons,detail_selection_a4=reasons4,results=results,
        route_metrics_a3=metrics3,route_metrics_a4=metrics4,
        human_visual_review="PENDING",exact_CHALK="NOT_RUN",independent_E5="NOT_RUN",
        production_admissible=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=tuple(A3_COUNTS),required=True)
    main(parser.parse_args().case)
