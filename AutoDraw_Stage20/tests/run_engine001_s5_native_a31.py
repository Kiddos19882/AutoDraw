"""A31 research-only fixed R6 Blossom optimization, see preregistration."""
import argparse
from collections import Counter
import gzip
import itertools
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

import run_engine001_s5_native_a30 as a30
a29 = a30.a29
RADIUS = 6
CAP = RADIUS * a30.SCALE
BUDGETS = (5, 10, 15, 20)
A30_HASHES = {
    "blossom-contour-plan.json.gz": "b73f48df4bc99709a944de2c6be9db8ac808ed91d6c6356bb47443a31035cfe6",
    "blossom-full-plan.json.gz": "0780bc5fb7290975782aa3e85231e243133f7df8db27a432a5f97f03ee1e1a17",
    "blossom-contour.png": "5c67942be394f38105131bf197ac569122c023bcf9100acd32fe35f1485e945a",
    "blossom-full.png": "b22bbbb04b822e45fac8fb0c8eb983e611b2f107a3ca3fd21763bd1962bc6691",
}

def point(v):
    return (v["x"], v["y"])

def edges_of(plan):
    c = Counter()
    for p in plan:
        for x,y in zip(p["points"], p["points"][1:]):
            a,b = point(x),point(y)
            if a != b:
                c[p["colorRgb"],p["width"],*sorted((a,b))] += 1
    return c

def direct_graph(group, allowed):
    pos=np.array([a30.xy(p["points"][s]) for p in group for s in (0,-1)])
    return {(a,b):[a30.as_point(pos[a]),a30.as_point(pos[b])]
            for a,b in sorted(cKDTree(pos).query_pairs(CAP))
            if a//2!=b//2 and a30.straight_ok(pos[a],pos[b],allowed)}

def components(group,links):
    owner={};closed=set()
    for i in range(len(group)):
        if i in owner:continue
        todo=[i];owner[i]=i;ends=0
        while todo:
            k=todo.pop()
            for j in (2*k,2*k+1):
                if j not in links:ends+=1;continue
                n=links[j][0]//2
                if n not in owner:owner[n]=i;todo.append(n)
        assert ends in (0,2)
        if ends==0:closed.add(i)
    return owner,closed

def cycle_repair(group,edges):
    links=a30.select(group,edges,False,True)
    ranked=sorted(edges,key=lambda e:(a30.length(edges[e]),e))
    while True:
        owner,closed=components(group,links)
        choice=None
        for a,b in ranked:
            if owner[a//2]==owner[b//2]:continue
            if any(x in links and owner[x//2] not in closed for x in (a,b)):continue
            choice=(a,b);break
        if choice is None:break
        a,b=choice
        for x in (a,b):
            if x in links:
                y=links.pop(x)[0]; del links[y]
        links[a]=(b,edges[a,b]);links[b]=(a,edges[a,b][::-1])
    pp,mm=a30.endpoint_paths(group,links)
    return [dict(points=p,width=1,colorRgb=group[0]["colorRgb"],members=m)
            for p,m in zip(pp,mm)]

def group_candidates(paths,allowed,repeat,cache):
    # Exact stored vertices, and all actual path endpoints. Each new chord <= R6.
    coords=[]; owners=[]; indices=[]; arcs=[]
    for i,p in paths.items():
        q=np.array([point(v) for v in p["points"]])
        pref=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))]
        closed=bool(np.array_equal(q[0],q[-1]))
        ids=np.arange(len(q))
        cost=np.zeros(len(q)) if closed else np.minimum(pref,pref[-1]-pref)
        if not repeat and not closed:
            ids=np.array([0,len(q)-1])
        coords.extend(q[ids]);owners.extend([i]*len(ids));indices.extend(ids);arcs.extend(cost[ids])
    if not coords:return []
    coords=np.asarray(coords);owners=np.asarray(owners);indices=np.asarray(indices);arcs=np.asarray(arcs)
    kd=cKDTree(coords)
    out={}
    for a,p in paths.items():
        for side in (0,-1):
            av=np.array(point(p["points"][side]))
            near=np.asarray(kd.query_ball_point(av,CAP),dtype=int)
            near=near[owners[near]!=a]
            if not len(near):continue
            dist=np.linalg.norm(coords[near]-av,axis=1)
            costs=dist+arcs[near]
            for k in np.lexsort((indices[near],owners[near],costs)):
                n=near[k];b=int(owners[n]);j=int(indices[n])
                key=tuple(sorted((a,b))); rank=(float(costs[k]),a,b,side,j,float(dist[k]),float(arcs[n]))
                if key in out and out[key]<=rank:continue
                ck=tuple(sorted((tuple(av),tuple(coords[n]))))
                if ck not in cache:cache[ck]=a30.straight_ok(av,coords[n],allowed)
                if cache[ck]:out[key]=rank
    return list(out.values())

def merged(a,b,side,j):
    assert a["colorRgb"]==b["colorRgb"]
    aa=a["points"] if side==-1 else a["points"][::-1]
    bb=b["points"];out=list(aa)
    if bb[0]==bb[-1]:
        if j==len(bb)-1:j=0
        route=bb[j:]+bb[1:j+1] if j else bb
    else:
        left=a30.length(bb[:j+1]);right=a30.length(bb[j:])
        if left<=right:
            route=bb[j::-1]+bb[1:]
        else:
            route=bb[j:]+bb[-2::-1]
    a30.attach(out,route)
    return dict(points=out,width=1,colorRgb=a["colorRgb"],members=a["members"]+b["members"])

def optimize(initial,masks,cap,repeat):
    paths={i:p for i,p in enumerate(initial)}
    caches={c:{} for c in masks}
    total=math.fsum(a30.length(p["points"]) for p in initial)
    joins=[];rounds=0
    while True:
        bycolor={}
        for i,p in paths.items():bycolor.setdefault(p["colorRgb"],{})[i]=p
        choices=[]
        for c,g in bycolor.items():
            choices.extend(group_candidates(g,masks[c],repeat,caches[c]))
        count=0
        for cost,a,b,side,j,d,arc in sorted(choices):
            if a not in paths or b not in paths:continue
            if total+cost>cap+1e-8:continue
            aa,bb=paths[a],paths[b]
            p=merged(aa,bb,side,j)
            actual=a30.length(p["points"])-a30.length(aa["points"])-a30.length(bb["points"])
            assert abs(actual-cost)<1e-7,(actual,cost)
            assert repeat or arc<1e-8
            assert d<=CAP+1e-8
            del paths[a];del paths[b]
            # New id prevents reuse of stale candidates in this round.
            new=len(initial)+len(joins)
            paths[new]=p;total+=actual;count+=1
            joins.append(dict(bridge_logical=d,retrace_logical=arc,added_logical=actual,
                              color=p["colorRgb"],a=a,b=b,new=new,side=side,vertex=j))
        rounds+=1
        if not count:break
    print("merge",repeat,"budget",cap,"rounds",rounds,"strokes",len(paths),"length",total,flush=True)
    out=sorted(paths.values(),key=lambda p:(list(masks).index(p["colorRgb"]),min(p["members"])))
    return out,joins

def build(paths,raw,projected):
    base=math.fsum(a30.length(p["points"]) for p in paths)
    original=edges_of(paths);colors={};initial=[]
    for (c,w),g in itertools.groupby(paths,key=lambda p:(p["colorRgb"],p["width"])):
        group=list(g);assert w==1 and c not in colors
        colors[c]=a30.masks(raw,projected,c)[0]
        initial.extend(cycle_repair(group,direct_graph(group,colors[c])))
    no_repeat,joins=optimize(initial,colors,math.inf,False)
    joins=[dict(phase="no-retrace",**j) for j in joins]
    variants={"cycle-repair":(initial,[]),"interior-no-retrace":(no_repeat,joins)}
    for b in BUDGETS:
        p,j=optimize(no_repeat,colors,base*(1+b/100),True)
        variants[f"hybrid-{b}pct"]=(p,joins+[dict(phase="hybrid",**x) for x in j])
    result={}
    for name,(pp,joins) in variants.items():
        members=[p["members"] for p in pp]
        assert sorted(x for m in members for x in m)==sorted(p["strokeId"] for p in paths)
        plan=[dict(points=p["points"],width=p["width"],colorRgb=p["colorRgb"],strokeId=f"icon-{9100000+i}")
              for i,p in enumerate(pp)]
        assert not original-edges_of(plan),name
        stats=a30.stats(plan,base)
        if name.startswith("hybrid"):
            cap=int(name.split("-")[1].replace("pct",""))
            assert stats["logical_length"]<=base*(1+cap/100)+1e-7
        assert len(plan)<=len(initial) and all(len(p["points"])>=2 for p in plan)
        print(name,stats,flush=True)
        result[name]=(plan,members,joins)
    return result

def contracts():
    a30.contracts()
    def st(i,p):
        return dict(points=[dict(x=x,y=y) for x,y in p],colorRgb=0,width=1,members=[str(i)],strokeId=str(i))
    a=st(0,[(1,2),(2,2)])
    b=st(1,[(3,1),(3,2),(3,3),(3,4)])
    r=merged(a,b,-1,1)
    assert abs(a30.length(r["points"])-5-1)<1e-9  # 1+3+1 bridge+1 retrace
    assert not edges_of([a,b])-edges_of([r])
    loop=st(2,[(3,2),(4,2),(4,3),(3,2)])
    r=merged(a,loop,-1,1)
    assert not edges_of([a,loop])-edges_of([r])
    assert abs(a30.length(r["points"])-a30.length(a["points"])-a30.length(loop["points"])-2)<1e-9
    mask=np.ones((30,30),bool)
    pp,j=optimize([a,b],{0:mask},6,True)
    assert len(pp)==1 and len(j)==1
    pp,j=optimize([a,b],{0:mask},4,True)
    assert len(pp)==2
    print("A31 contracts PASS",flush=True)

def accepted_a30(folder,tail):
    for n,h in A30_HASHES.items():assert a29.sha(folder/n)==h,n
    def load(n):
        with gzip.open(folder/n,"rt",encoding="utf8") as f:return json.load(f)
    p=load("blossom-contour-plan.json.gz");full=load("blossom-full-plan.json.gz")
    assert len(p)==745 and full==p+tail
    return p,full,*[np.array(Image.open(folder/n).convert("RGBA")) for n in ("blossom-contour.png","blossom-full.png")]

def main(folder,a29folder,a30folder,model_only):
    paths,full,raw,final,target,projected=a29.read_baseline(folder)
    tail=full[len(paths):];c29,f29,r29,p29=a30.accepted(a29folder,6,tail)
    c30,f30,r30,p30=accepted_a30(a30folder,tail)
    base=math.fsum(a30.length(p["points"]) for p in paths)
    plans=build(paths,raw,projected)
    if model_only:return
    import run_engine001_s5_wv_full_native as native
    import run_engine001_s5_originals_native_transfer as transfer
    out=Path(os.environ["RUNNER_TEMP"])/"s5-a31-r6";out.mkdir(exist_ok=False);native.OUT=out
    geo=transfer.layout(414,483)
    assert np.array_equal(transfer.projected(target,geo)[0],projected)
    results={}
    def save(label,pp):
        f=out/(label+"-plan.json.gz")
        with gzip.open(f,"wt",encoding="utf8") as s:json.dump(pp,s,separators=(",",":"))
        return a29.sha(f)
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not native.render(driver,"blank",[])[:,:,3].any()
        line=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        ref=native.render(driver,"reference-original",line)
        js=native.full_fixture();a=js.index("function renderComplexHoldoutColorProbe(");b=js.index("const board = makeTemporalBoard(",a)
        guard=js[a:b];anchor=" ||\n          stroke.points.length > 128";assert guard.count(anchor)==1
        driver.execute_script(js[:a]+guard.replace(anchor,"")+js[b:])
        assert np.array_equal(ref,native.render(driver,"reference-expanded",line))
        grid=Image.new("RGB",(450*3,760*6),"white");draw=ImageDraw.Draw(grid)
        def panel(idx,label,r,f):
            for row,im in enumerate((r,f)):
                x=idx%3*450;y=(idx//3*2+row)*760
                pic=Image.new("RGBA",(450,720),"white");pic.alpha_composite(Image.fromarray(im[:,465:915],"RGBA"))
                grid.paste(pic.convert("RGB"),(x,y+40));draw.text((x+5,y+5),label+(" contour" if row==0 else " full"),fill="black")
        for i,(name,c,f,r,p) in enumerate((("a27",paths,full,raw,final),("a29",c29,f29,r29,p29),("a30",c30,f30,r30,p30))):
            assert np.array_equal(r,native.render(driver,name+"-contour",c)),name
            assert np.array_equal(p,native.render(driver,name+"-full",f)),name
            panel(i,name,r,p)
        for i,(name,(pp,members,joins)) in enumerate(plans.items(),3):
            combined=pp+tail
            assert combined[len(pp):]==tail and len({p["strokeId"] for p in combined})==len(combined)
            r=native.render(driver,name+"-contour",pp);f=native.render(driver,name+"-full",combined)
            c,d=a29.difference(r,raw),a29.difference(f,final)
            res=dict(**a30.stats(pp,base),full_strokes=len(combined),full_vertices=sum(len(p["points"]) for p in combined),
                     contour_diff_a27=c,full_diff_a27=d,contour_diff_a29=a29.difference(r,r29),full_diff_a29=a29.difference(f,p29),
                     contour_diff_a30=a29.difference(r,r30),full_diff_a30=a29.difference(f,p30),
                     full_score=transfer.score(name+"-full",f,target,geo,out)[0],
                     quality="PIXEL_IDENTICAL" if c["rgba_changed"]==d["rgba_changed"]==0 else "VISUAL_REVIEW_REQUIRED",
                     contour_plan_sha256=save(name+"-contour",pp),full_plan_sha256=save(name+"-full",combined),
                     contour_png_sha256=a29.sha(out/(name+"-contour.png")),full_png_sha256=a29.sha(out/(name+"-full.png")),
                     membership=members,joins=joins)
            results[name]=res;panel(i,name+" "+str(len(pp)),r,f)
            print(name,json.dumps({k:v for k,v in res.items() if k not in ("membership","joins")}),flush=True)
            native.binding.write_json(out/"a31-results.json",dict(schema="ENGINE001_S5_A31_V1",radius=6,
                 sha=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],baseline_a27=a29.EXPECTED,
                 baseline_a29=a30.A29_HASHES[6],baseline_a30=A30_HASHES,results=results,
                 smooth=False,exact_CHALK="NOT_RUN",live_E4="NOT_RUN",E5="NOT_RUN",user_visual_review="PENDING"))
        grid.save(out/"comparison.png")

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--contracts",action="store_true")
    p.add_argument("--baseline",type=Path);p.add_argument("--a29",type=Path);p.add_argument("--a30",type=Path);p.add_argument("--model-only",action="store_true")
    args=p.parse_args()
    if args.contracts:contracts()
    else:
        if not all((args.baseline,args.a29,args.a30)):p.error("baseline, a29, a30 required")
        main(args.baseline,args.a29,args.a30,args.model_only)
