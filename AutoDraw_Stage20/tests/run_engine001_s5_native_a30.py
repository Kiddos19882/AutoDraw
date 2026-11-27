"""A30 fixed-radius contour routing comparison; see frozen experiment preregistration."""
import argparse
from collections import defaultdict
import gzip
import heapq
import itertools
import json
import math
import os
from pathlib import Path

import networkx as nx
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

import run_engine001_s5_native_a29 as a29

ARMS = ("tangent", "geodesic", "blossom", "combined", "postman", "topology")
SCALE = a29.SCALE
A29_HASHES = {
    6: ("1ef3e19c3361b3a2f7831098cd933a080d2081a030906f025e8e80b33c563382",
        "9c99dda9923ce3ad4bc7f87292b2b3159764be4589bd9fe07e2ec2cb1ec2a42b",
        "258214b26aeecfa8a7cd472e25ad10fd6d581dd76bad6676c02d85a53f77106c",
        "3d3bbe7c79bb036ace82d640436f953399a30d2e93f88674731137e569d45fdb"),
    12: ("c12278d802fb33b230ddb83960a3c627c504003eee0db1efaad445a8cf1b2f3a",
         "4d3a488899129762cc783f216f2ada5b12220bafccf7656abb8238bc64f45949",
         "b9f95eff79267113e98f79f1d6f6c8cf29b52945320c036116f5ad170960c4fa",
         "79dff607a1ea8b326e767635defcc36b86e8b39abe325ccdb656fcd83e5b8e0e"),
}


def xy(p):
    return np.array([p["x"], p["y"]], dtype=float)


def as_point(v):
    return dict(x=float(v[0]), y=float(v[1]))


def length(points):
    return math.fsum(math.hypot(b["x"]-a["x"], b["y"]-a["y"])
                     for a, b in zip(points, points[1:]))


def attach(out, points):
    assert points
    out.extend(points[1:] if out and out[-1] == points[0] else points)


def samples(a, b):
    d = float(np.linalg.norm(a-b))
    t = np.linspace(0, 1, max(2, math.ceil(d*12)+1))
    return np.floor((a+(b-a)*t[:, None])*3).astype(int)


def straight_ok(a, b, allowed):
    q = samples(a, b)
    return bool(((q[:, 0] >= 0) & (q[:, 0] < allowed.shape[1]) &
                 (q[:, 1] >= 0) & (q[:, 1] < allowed.shape[0])).all()
                and allowed[q[:, 1], q[:, 0]].mean() >= .8)


def masks(raw, projected, color):
    canvas = np.full(raw.shape[:2] + (3,), 255, np.uint8)
    canvas[:, 465:915] = projected
    rgb = a29.rgb_value(color)
    source = np.all(canvas == rgb, axis=2)
    allowed = distance_transform_edt(~source) <= 3*SCALE*3
    painted = (raw[:, :, 3] > 24) & np.all(raw[:, :, :3] == rgb, axis=2)
    # Existing painted same-color pixels can also carry a geodesic path.
    cost = np.where(painted, 1., np.where(source, 2., np.where(allowed, 8., np.inf)))
    return allowed, cost


def geodesic(a, b, cost, radius):
    """Bounded A* in backing pixels, exact logical endpoints; no off-mask moves."""
    start, goal = tuple(np.floor(a*3).astype(int)), tuple(np.floor(b*3).astype(int))
    w, h = cost.shape[1], cost.shape[0]
    if not all(0 <= x < w and 0 <= y < h for x,y in (start,goal)):
        return None
    cap = 2*radius*SCALE
    if start == goal:
        return [as_point(a), as_point(b)]
    # Endpoint exemptions do not exempt any other sample.
    def field(p):
        return 1. if p in (start,goal) else cost[p[1],p[0]]
    dist, prior = {start: 0.}, {}
    queue = [(math.dist(start,goal), 0., start)]
    while queue:
        _, g, p = heapq.heappop(queue)
        if g != dist.get(p):
            continue
        if p == goal:
            break
        for dx,dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            q = (p[0]+dx,p[1]+dy)
            if not (0 <= q[0] < w and 0 <= q[1] < h):
                continue
            # Search is confined to a fixed length ellipse, not an adaptive radius.
            if math.dist(start,q)+math.dist(q,goal) > cap*3+2:
                continue
            fq = field(q)
            if not math.isfinite(fq):
                continue
            if dx and dy and not (math.isfinite(field((p[0]+dx,p[1]))) or
                                  math.isfinite(field((p[0],p[1]+dy)))):
                continue
            ng = g + math.hypot(dx,dy)*(field(p)+fq)/2
            if ng < dist.get(q, math.inf):
                dist[q], prior[q] = ng, p
                heapq.heappush(queue,(ng+math.dist(q,goal), ng, q))
    else:
        return None
    path = [goal]
    while path[-1] != start:
        path.append(prior[path[-1]])
    path.reverse()
    # Only remove collinear intermediate grid centers.
    mids = [p for i,p in enumerate(path[1:-1],1)
            if (p[0]-path[i-1][0],p[1]-path[i-1][1]) !=
               (path[i+1][0]-p[0],path[i+1][1]-p[1])]
    pp = []
    for v in [as_point(a)] + [as_point((np.array(p,dtype=float)+.5)/3) for p in [start]+mids+[goal]] + [as_point(b)]:
        if not pp or pp[-1] != v:
            pp.append(v)
    if len(pp) < 2 or length(pp) > cap+1e-9:
        return None
    # Verify the exact piecewise linear route after collinear compression.
    for u,v in zip(pp,pp[1:]):
        for x,y in samples(xy(u),xy(v)):
            if not math.isfinite(field((x,y))):
                return None
    return pp


def tangent(points, side):
    p = xy(points[0 if side == 0 else -1])
    seq = points[1:] if side == 0 else points[-2::-1]
    for v in seq:
        d = p-xy(v)
        n = np.linalg.norm(d)
        if n > 1e-10:
            return d/n
    return np.zeros(2)


def turn_cost(a, b, pp, tangents):
    va = tangent(pp, 0)
    vb = tangent(pp, 1)
    # The outgoing tangent of source a should oppose the bridge start outward vector.
    return 2*SCALE*(2+float(np.clip(tangents[a]@va,-1,1))+
                     float(np.clip(tangents[b]@vb,-1,1)))


def candidates(group, allowed, cost, radius):
    positions = np.array([xy(p["points"][0 if side==0 else -1]) for p in group for side in (0,1)])
    direct, curved = {}, {}
    for a,b in sorted(cKDTree(positions).query_pairs(radius*SCALE)):
        if a//2 == b//2:
            continue
        av,bv = positions[a],positions[b]
        if straight_ok(av,bv,allowed):
            direct[a,b] = [as_point(av),as_point(bv)]
        pp = geodesic(av,bv,cost,radius)
        if pp is not None:
            curved[a,b] = pp
        # For geodesic comparison keep a valid straight path if A* cannot find
        # a supported bounded path, preserving the A29 center-corridor fallback.
        elif (a,b) in direct:
            curved[a,b] = direct[a,b]
    return direct, curved


def select(group, edges, tangents=False, blossom=False):
    tv = [tangent(p["points"],side) for p in group for side in (0,1)]
    values = {key:length(pp)+(turn_cost(*key,pp,tv) if tangents else 0.)
              for key,pp in edges.items()}
    if blossom:
        graph = nx.Graph()
        graph.add_nodes_from(range(2*len(group)))
        # Integer costs and sorted insertion give deterministic ties.
        for (a,b),v in sorted(values.items()):
            graph.add_edge(a,b,weight=-round(v*1e6))
        chosen = [tuple(sorted(edge)) for edge in nx.max_weight_matching(graph,maxcardinality=True)]
    else:
        parents = list(range(len(group)))
        def root(i):
            while i != parents[i]:
                i = parents[i]
            return i
        used, chosen = set(), []
        for a,b in sorted(values,key=lambda e:(values[e],e)):
            if a in used or b in used or root(a//2)==root(b//2):
                continue
            parents[root(a//2)] = root(b//2)
            used.update((a,b))
            chosen.append((a,b))
    chosen = sorted(chosen)
    links = {}
    for a,b in chosen:
        assert a not in links and b not in links
        links[a]=(b,edges[a,b]);links[b]=(a,edges[a,b][::-1])
    return links


def endpoint_paths(group, links):
    """Traverse alternating original paths/bridges, including closed matching cycles."""
    remaining, result, memberships = set(range(len(group))), [], []
    while remaining:
        seed = min(remaining)
        # Find component reachable via linked endpoints.
        comp, todo = {seed}, [seed]
        while todo:
            i = todo.pop()
            for endpoint in (2*i,2*i+1):
                if endpoint in links:
                    j = links[endpoint][0]//2
                    if j not in comp:
                        comp.add(j); todo.append(j)
        ends = [2*i+s for i in sorted(comp) for s in (0,1) if 2*i+s not in links]
        entry = min(ends) if ends else 2*min(comp)
        pp, members, visited = [], [], set()
        while True:
            i,side = divmod(entry,2)
            assert i in remaining and i not in visited
            visited.add(i); members.append(group[i]["strokeId"])
            attach(pp,group[i]["points"] if side==0 else group[i]["points"][::-1])
            exitpoint = entry^1
            if exitpoint not in links:
                break
            nxt, bridge = links[exitpoint]
            attach(pp,bridge)
            if nxt//2 in visited:
                assert not ends and nxt//2 == seed and pp[0] == pp[-1]
                break
            entry = nxt
        assert visited == comp
        remaining -= visited
        result.append(pp);memberships.append(members)
    return result,memberships


def contact_forest(group, allowed, radius):
    """Nearest valid endpoint-to-vertex contacts, then Kruskal on original strokes."""
    coords, refs = [], []
    for i,p in enumerate(group):
        for j,v in enumerate(p["points"]):
            coords.append(xy(v)); refs.append((i,j))
    coords=np.asarray(coords); kd=cKDTree(coords)
    possible={}
    for i,p in enumerate(group):
        for j in (0,len(p["points"])-1):
            av=xy(p["points"][j]); near=kd.query_ball_point(av,radius*SCALE)
            # For every other stroke choose shortest admissible contact.
            for k in near:
                q,m=refs[k]
                if i==q:
                    continue
                bv=coords[k]
                d=float(np.linalg.norm(av-bv))
                a,b=(i,j),(q,m)
                if b<a:
                    a,b=b,a
                key=(a[0],b[0])
                rank=(d,a,b)
                if key in possible and possible[key] <= rank:
                    continue
                if straight_ok(av,bv,allowed):
                    possible[key]=rank
    parent=list(range(len(group)))
    def root(i):
        while parent[i]!=i:
            i=parent[i]
        return i
    selected=[]
    for d,a,b in sorted(possible.values()):
        if root(a[0])==root(b[0]):
            continue
        parent[root(a[0])]=root(b[0]); selected.append((a,b))
    attach_indices=[{0,len(p["points"])-1} for p in group]
    for a,b in selected:
        attach_indices[a[0]].add(a[1]); attach_indices[b[0]].add(b[1])
    forest=nx.Graph()
    def edge(a,b,pp,kind,member):
        assert a!=b and not forest.has_edge(a,b)
        forest.add_edge(a,b,pts=pp,start=a,length=length(pp),kind=kind,member=member)
    for i,p in enumerate(group):
        ids=sorted(attach_indices[i])
        for a,b in zip(ids,ids[1:]):
            edge((i,a),(i,b),p["points"][a:b+1],"original",p["strokeId"])
    for a,b in selected:
        edge(a,b,[group[a[0]]["points"][a[1]],group[b[0]]["points"][b[1]]],"connector",None)
    assert nx.is_forest(forest)
    return forest


def oriented(data,u):
    return data["pts"] if data["start"]==u else data["pts"][::-1]


def postman(forest):
    """Optimal open Chinese postman route per tree: double all non-diameter edges."""
    results=[]
    for nodes in nx.connected_components(forest):
        tree=forest.subgraph(nodes)
        start=min(nodes)
        d=nx.single_source_dijkstra_path_length(tree,start,weight="length")
        a=max(d,key=lambda n:(d[n],n))
        d=nx.single_source_dijkstra_path_length(tree,a,weight="length")
        b=max(d,key=lambda n:(d[n],n))
        diam=nx.shortest_path(tree,a,b,weight="length")
        spine={frozenset((u,v)) for u,v in zip(diam,diam[1:])}
        routed=nx.MultiGraph()
        for u,v,data in tree.edges(data=True):
            routed.add_edge(u,v,**data)
            if frozenset((u,v)) not in spine:
                routed.add_edge(u,v,**data)
        if a==b or not nx.has_eulerian_path(routed,source=a):
            # Degenerate zero-length tree: still find a real topological diameter.
            a=next(n for n in routed if routed.degree(n)%2)
        pp, members=[], []
        traversed=0
        for u,v,k in nx.eulerian_path(routed,source=a,keys=True):
            data=routed[u][v][k]; attach(pp,oriented(data,u)); traversed+=1
            if data["member"] is not None:members.append(data["member"])
        assert traversed==routed.number_of_edges()
        expected=2*sum(d["length"] for _,_,d in tree.edges(data=True))-d[b]
        # d is distances from a; if the degenerate branch ran, expected remains valid.
        assert abs(length(pp)-expected)<1e-6
        results.append((pp,members))
    return results


def topology(forest):
    """At each junction pair half-edges with most continuous direction; no retracing."""
    continuation={}
    for node in sorted(forest):
        neighbors=sorted(forest[node])
        if len(neighbors)<2:continue
        match=nx.Graph();match.add_nodes_from(neighbors)
        rays={n:-tangent(oriented(forest[node][n],node),0) for n in neighbors}
        for a,b in itertools.combinations(neighbors,2):
            # Opposite rays correspond to a continuous stroke through this junction.
            match.add_edge(a,b,weight=-round(float(rays[a]@rays[b])*1e6))
        for a,b in nx.max_weight_matching(match,maxcardinality=True):
            continuation[node,a]=b; continuation[node,b]=a
    used=set();result=[]
    starts=sorted((u,v) for u in forest for v in forest[u] if (u,v) not in continuation)
    for u,v in starts:
        if frozenset((u,v)) in used:continue
        pp,members=[],[]
        while True:
            edge=frozenset((u,v));assert edge not in used;used.add(edge)
            data=forest[u][v];attach(pp,oriented(data,u))
            if data["member"] is not None:members.append(data["member"])
            nxt=continuation.get((v,u))
            if nxt is None:break
            u,v=v,nxt
        result.append((pp,members))
    assert len(used)==forest.number_of_edges()
    return result


def build(paths,raw,projected,radius):
    out={arm:[] for arm in ARMS}; membership={arm:[] for arm in ARMS}
    for (color,width),gg in itertools.groupby(paths,key=lambda p:(p["colorRgb"],p["width"])):
        group=list(gg);allowed,cost=masks(raw,projected,color)
        direct,curved=candidates(group,allowed,cost,radius)
        for name,edges,t,b in (("tangent",direct,True,False),("geodesic",curved,False,False),
                               ("blossom",direct,False,True),("combined",curved,True,True)):
            pp,mm=endpoint_paths(group,select(group,edges,t,b))
            assert sorted(x for m in mm for x in m)==sorted(p["strokeId"] for p in group)
            for points,members in zip(pp,mm):
                out[name].append(dict(points=points,width=width,colorRgb=color))
                membership[name].append(members)
        forest=contact_forest(group,allowed,radius)
        for name,routed in (("postman",postman(forest)),("topology",topology(forest))):
            assert set(x for _,m in routed for x in m)=={p["strokeId"] for p in group}
            for points,members in routed:
                out[name].append(dict(points=points,width=width,colorRgb=color))
                membership[name].append(members)
        print("color",hex(color), "direct",len(direct),"curved",len(curved),
              "cumulative",{k:len(v) for k,v in out.items()},flush=True)
    for arm,plan in out.items():
        for i,p in enumerate(plan):
            p["strokeId"]=f"icon-{9000000+i}"
            assert len(p["points"])>=2 and p["width"]==1
            assert all(0<=q["x"]<460 and 0<=q["y"]<240 for q in p["points"])
    return out,membership


def contracts():
    a29.contracts()
    def p(i,a,b):
        return dict(strokeId=str(i),width=1,colorRgb=0,points=[as_point(a),as_point(b)])
    group=[p(0,(1,1),(2,1)),p(1,(3,1),(4,1)),p(2,(5,1),(6,1))]
    allow=np.ones((30,30),bool);cost=np.ones_like(allow,float)
    direct,curved=candidates(group,allow,cost,12)
    for blossom in (False,True):
        pp,mm=endpoint_paths(group,select(group,direct,True,blossom))
        assert sorted(x for m in mm for x in m)==["0","1","2"]
    # Blossom may close a cycle; every endpoint is used once and closure is retained.
    cycle={(1,2):[as_point((2,1)),as_point((3,1))],
           (3,4):[as_point((4,1)),as_point((5,1))],
           (0,5):[as_point((1,1)),as_point((6,1))]}
    pp,mm=endpoint_paths(group,select(group,cycle,False,True))
    assert len(pp)==1 and pp[0][0]==pp[0][-1]
    cost[:,8]=np.inf
    assert geodesic(np.array([1.,1.]),np.array([4.,1.]),cost,12) is None
    cost[7,8]=1
    assert geodesic(np.array([1.,1.]),np.array([4.,1.]),cost,12) is not None
    forest=contact_forest(group,allow,12)
    assert nx.is_tree(forest)
    assert len(postman(forest))==1 and len(topology(forest))==1
    # T branch: topology covers edges once, postman traverses one edge twice.
    g=nx.Graph()
    for v in ((1,0),(-1,0),(0,1)):
        u=(0,0);points=[as_point(u),as_point(v)]
        g.add_edge(u,v,start=u,pts=points,length=1.,kind="original",member=str(v))
    assert sum(length(p) for p,m in postman(g))==4
    assert sum(length(p) for p,m in topology(g))==3
    assert len(topology(g))==2
    print("A30 contracts PASS",flush=True)


def accepted(folder,radius,tail):
    key=f"corridor-r{radius}"
    names=[key+"-contour-plan.json.gz",key+"-full-plan.json.gz",
           key+"-contour.png",key+"-full.png"]
    for n,h in zip(names,A29_HASHES[radius]):assert a29.sha(folder/n)==h,n
    with gzip.open(folder/names[0],"rt",encoding="utf8") as f:pp=json.load(f)
    with gzip.open(folder/names[1],"rt",encoding="utf8") as f:full=json.load(f)
    assert full==pp+tail and len(pp)=={6:758,12:480}[radius]
    return pp,full,*[np.array(Image.open(folder/n).convert("RGBA")) for n in names[2:]]


def stats(plan,base):
    l=math.fsum(length(p["points"]) for p in plan)
    return dict(strokes=len(plan),vertices=sum(len(p["points"]) for p in plan),
                logical_length=l,added_logical_length=l-base,
                short_source_lt_equal5=sum(length(p["points"])<=5*SCALE for p in plan))


def main(folder,a29folder,radius,model_only):
    paths,full,raw,final,target,projected=a29.read_baseline(folder)
    tail=full[len(paths):];ac,af,acraw,afraw=accepted(a29folder,radius,tail)
    base=math.fsum(length(p["points"]) for p in paths)
    plans,membership=build(paths,raw,projected,radius)
    for name,plan in plans.items():print(name,stats(plan,base),flush=True)
    if model_only:return
    import run_engine001_s5_wv_full_native as native
    import run_engine001_s5_originals_native_transfer as transfer
    out=Path(os.environ["RUNNER_TEMP"])/f"s5-a30-r{radius}";out.mkdir(exist_ok=False);native.OUT=out
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
        reference=native.render(driver,"reference-original",line)
        js=native.full_fixture()
        a=js.index("function renderComplexHoldoutColorProbe(")
        b=js.index("const board = makeTemporalBoard(",a)
        guard=js[a:b];anchor=" ||\n          stroke.points.length > 128";assert guard.count(anchor)==1
        driver.execute_script(js[:a]+guard.replace(anchor,"")+js[b:])
        assert np.array_equal(reference,native.render(driver,"reference-expanded",line))
        for name,pp,expected in (("a27-contour",paths,raw),("a27-full",full,final),
                                 ("a29-contour",ac,acraw),("a29-full",af,afraw)):
            assert np.array_equal(expected,native.render(driver,name,pp)),name
        base_score=transfer.score("a27-full",final,target,geo,out)[0]
        accept_score=transfer.score("a29-full",afraw,target,geo,out)[0]
        grid=Image.new("RGB",(450*4,760*4),"white");draw=ImageDraw.Draw(grid)
        def panel(idx,label,r,f):
            for row,im in enumerate((r,f)):
                col=idx%4;y=(idx//4*2+row)*760;x=col*450
                pic=Image.new("RGBA",(450,720),"white");pic.alpha_composite(Image.fromarray(im[:,465:915],"RGBA"))
                grid.paste(pic.convert("RGB"),(x,y+40));draw.text((x+5,y+5),label+(" contour" if row==0 else " full"),fill="black")
        panel(0,"A27",raw,final);panel(1,f"A29 R{radius}",acraw,afraw)
        for i,(name,pp) in enumerate(plans.items(),2):
            combined=pp+tail;assert combined[len(pp):]==tail and len({p["strokeId"] for p in combined})==len(combined)
            r=native.render(driver,name+"-contour",pp);f=native.render(driver,name+"-full",combined)
            c,d=a29.difference(r,raw),a29.difference(f,final)
            res=dict(**stats(pp,base),full_strokes=len(combined),full_vertices=sum(len(p["points"]) for p in combined),
                     contour_diff_a27=c,full_diff_a27=d,contour_diff_a29=a29.difference(r,acraw),
                     full_diff_a29=a29.difference(f,afraw),
                     full_score=transfer.score(name+"-full",f,target,geo,out)[0],
                     quality="PIXEL_IDENTICAL" if c["rgba_changed"]==d["rgba_changed"]==0 else "VISUAL_REVIEW_REQUIRED",
                     contour_plan_sha256=save(name+"-contour",pp),full_plan_sha256=save(name+"-full",combined),
                     contour_png_sha256=a29.sha(out/(name+"-contour.png")),full_png_sha256=a29.sha(out/(name+"-full.png")),
                     membership=membership[name])
            results[name]=res;panel(i,name+" "+str(len(pp)),r,f)
            print(name,json.dumps({k:v for k,v in res.items() if k!="membership"}),flush=True)
            native.binding.write_json(out/"a30-results.json",dict(schema="ENGINE001_S5_A30_V1",radius=radius,
                sha=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],baseline_a27=a29.EXPECTED,
                baseline_a29=A29_HASHES[radius],a27_score=base_score,a29_score=accept_score,results=results,
                smooth=False,exact_CHALK="NOT_RUN",live_E4="NOT_RUN",E5="NOT_RUN",user_visual_review="PENDING"))
        grid.save(out/"comparison.png")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--contracts",action="store_true")
    p.add_argument("--baseline",type=Path);p.add_argument("--a29",type=Path);p.add_argument("--radius",type=int,choices=(6,12))
    p.add_argument("--model-only",action="store_true");args=p.parse_args()
    if args.contracts:contracts()
    else:
        if args.baseline is None or args.a29 is None or args.radius is None:p.error("baseline, a29, radius required")
        main(args.baseline,args.a29,args.radius,args.model_only)
