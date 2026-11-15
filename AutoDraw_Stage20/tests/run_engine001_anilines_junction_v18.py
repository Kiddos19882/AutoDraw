#!/usr/bin/env python3
"""ENGINE-001 V18 A/B: graph repair and tangent pairing; offline research only."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from skimage.morphology import skeletonize
from run_engine001_anilines_brush1_v17 import simplify as rdp, length as arc

SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
ANI_SHA="2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b"
INK=(49,38,43)
DOT_LIMIT=-0.9063077870366499
DIRECTIONS=tuple((dx,dy) for dy in (-1,0,1) for dx in (-1,0,1) if dx or dy)

def order(p): return p[1],p[0]
def edge(a,b): return (a,b) if a<b else (b,a)
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def build_graph(skel):
    if skel.shape!=(320,200) or skel.dtype!=np.dtype(bool):
        raise ValueError("Expected 200x320 boolean skeleton")
    pixels={(int(x),int(y)) for y,x in np.argwhere(skel)}
    adj={p:set() for p in pixels}
    omitted=0
    for x,y in pixels:
        p=x,y
        for dx,dy in DIRECTIONS:
            q=(x+dx,y+dy)
            if q not in pixels or order(p)>=order(q): continue
            if dx and dy and ((x+dx,y) in pixels or (x,y+dy) in pixels):
                omitted+=1
                continue
            adj[p].add(q);adj[q].add(p)
    return {p:sorted(v,key=order) for p,v in adj.items()},omitted

def trace(adj):
    deg={p:len(v) for p,v in adj.items()}
    visited=set();chains=[]
    def walk(a,b):
        out=[a,b]; visited.add(edge(a,b));prev,cur=a,b
        while deg[cur]==2:
            nxt=adj[cur][0] if adj[cur][1]==prev else adj[cur][1]
            e=edge(cur,nxt)
            if e in visited: break
            visited.add(e);out.append(nxt);prev,cur=cur,nxt
        return out
    for p in sorted((q for q in adj if deg[q]!=2),key=order):
        for q in adj[p]:
            if edge(p,q) not in visited: chains.append(walk(p,q))
    for p in sorted(adj,key=order):
        for q in adj[p]:
            if edge(p,q) not in visited: chains.append(walk(p,q))
    expected={edge(p,q) for p,ns in adj.items() for q in ns}
    if expected!=visited:raise ValueError("Graph edge conservation FAILED")
    return chains,deg,len(expected)

def tangent(c,end):
    pts=c if end==0 else list(reversed(c))
    a=np.asarray(pts[0],float)
    v=np.asarray(pts[min(3,len(pts)-1)],float)-a
    n=float(np.linalg.norm(v))
    return v/n if n else None

def join_pairs(chains,degree):
    ends={}
    for i,c in enumerate(chains):
        for end in (0,1):
            at=c[0] if end==0 else c[-1]
            if degree[at]>=3:ends.setdefault(at,[]).append((i,end))
    pairs={};pair_count=0
    for at in sorted(ends,key=order):
        options=[]
        for n,a in enumerate(ends[at]):
            for b in ends[at][n+1:]:
                if a[0]==b[0]:continue
                ta,tb=tangent(chains[a[0]],a[1]),tangent(chains[b[0]],b[1])
                if ta is None or tb is None:continue
                dot=float(ta@tb)
                if dot<=DOT_LIMIT:options.append((1+dot,a,b))
        for _,a,b in sorted(options,key=lambda z:(z[0],z[1],z[2])):
            if a in pairs or b in pairs:continue
            pairs[a]=b;pairs[b]=a;pair_count+=1
    return pairs,pair_count

def stitch(chains,pairs):
    used=set();routes=[];members=[]
    endkeys=sorted(((i,e) for i in range(len(chains)) for e in (0,1)),
                   key=lambda z:(z in pairs,z[0],z[1]))
    for start in endkeys:
        if start[0] in used:continue
        cur=start;route=[];ids=[]
        while cur is not None:
            i,end=cur
            if i in used:break
            used.add(i);ids.append(i)
            segment=chains[i] if end==0 else list(reversed(chains[i]))
            if route and route[-1]!=segment[0]:raise ValueError("Nonmatching junction")
            route.extend(segment if not route else segment[1:])
            next_half=pairs.get((i,1-end))
            cur=next_half if next_half and next_half[0] not in used else None
        routes.append(route);members.append(ids)
    if len(used)!=len(chains):raise ValueError("Lost source chain")
    return routes,members

def render_variant(kind,routes,members,chains,skel,inkmask,out,suppressed,edges,branches,pairs):
    source=np.zeros((320,200),np.uint8)
    canvas=np.full((240,460,3),255,np.uint8)
    overlapping=np.zeros((240,460),np.uint16)
    paths=[];short_reject=0;rescued=0;retained=set();total=0.
    for path,ids in zip(routes,members):
        if arc(path)<4:short_reject+=1;continue
        rescued+=sum(arc(chains[i])<4 for i in ids)
        retained.update(ids)
        points=rdp(path,epsilon=0.6)
        for index in range(0,len(points)-1,127):
            part=points[index:min(index+128,len(points))]
            if len(part)<2:continue
            logical=[[x*.75+155,y*.75] for x,y in part]
            if len(logical)>128 or any(not(math.isfinite(x) and math.isfinite(y) and 155<=x<305 and 0<=y<240) for x,y in logical):
                raise ValueError("Invalid logical path")
            paths.append({"id":f"v18-{kind}-{len(paths)}","origin_chains":ids,
                          "source_points":part,"logical_points":logical,
                          "brush_width_parameter":1,"color_rgb":INK})
            total+=arc(part)
            cv2.polylines(source,[np.asarray(part,np.int32).reshape(-1,1,2)],False,255,1,cv2.LINE_8)
            coords=np.asarray([[round(x),round(y)] for x,y in logical],np.int32).reshape(-1,1,2)
            cv2.polylines(canvas,[coords],False,INK,1,cv2.LINE_8)
            surface=np.zeros((240,460),np.uint8)
            cv2.polylines(surface,[coords],False,1,1,cv2.LINE_8)
            overlapping+=surface
    verts=sum(len(p["source_points"]) for p in paths)
    if len(paths)>4000 or verts>30000:raise ValueError("V18 prereg quota exceeded")
    nearby=cv2.dilate((source>0).astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    permitted=cv2.dilate(inkmask.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    preview=np.any(canvas[:,155:305]!=255,axis=2)
    nearest=np.asarray(Image.fromarray(inkmask.astype(np.uint8)*255).resize((150,240),Image.Resampling.NEAREST))>0
    preview_near=cv2.dilate(preview.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    results={"graph_pixels":int(skel.sum()),"graph_edges":edges,"suppressed_diagonal_edges":suppressed,
             "branch_pixels":branches,"raw_chains":len(chains),
             "short_raw_chains":sum(arc(c)<4 for c in chains),
             "short_final_routes_rejected":short_reject,"short_raw_chains_rescued":rescued,
             "paired_junctions":pairs,"stitched_routes":len(routes),"paths":len(paths),
             "vertices":verts,"total_source_length":total,"retained_graph_chain_count":len(retained),
             "skeleton_recall_within1px":float((skel&nearby).sum()/max(1,skel.sum())),
             "source_foreign_exact":int(((source>0)&~inkmask).sum()),
             "source_foreign_beyond1px":int(((source>0)&~permitted).sum()),
             "logical_nearest_recall_within1px":float((nearest&preview_near).sum()/max(1,nearest.sum())),
             "logical_overlap_pixels":int((overlapping>1).sum())}
    Image.fromarray(canvas).save(out/f"{kind}-logical.png")
    Image.fromarray(canvas[:,155:305]).save(out/f"{kind}-roi.png")
    Image.fromarray(source).save(out/f"{kind}-source-path-mask.png")
    (out/f"{kind}-paths.json").write_text(json.dumps(paths,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return results

def run(source_file,ani_file,control_file,out):
    if digest(source_file)!=SOURCE_SHA or source_file.stat().st_size!=97308:raise ValueError("Wrong pinned image SHA")
    if digest(ani_file)!=ANI_SHA:raise ValueError("Wrong frozen AniLines SHA")
    src=np.asarray(Image.open(source_file).convert("RGB"))
    raw=np.asarray(Image.open(ani_file).convert("L"))
    if src.shape!=(320,200,3) or raw.shape!=(320,200):raise ValueError("Wrong dimensions")
    if control_file is not None:
        ctl=np.asarray(Image.open(control_file).convert("RGB"))
        if ctl.shape!=(240,150,3):raise ValueError("V17 control dimensions mismatch")
    else:ctl=np.full((240,150,3),255,np.uint8)
    if out.exists() and any(out.iterdir()):raise ValueError("Refuse overwrite")
    out.mkdir(parents=True,exist_ok=True)
    mask=raw<128;skel=skeletonize(mask)
    adj,omitted=build_graph(skel)
    chains,degree,edges=trace(adj)
    branches=sum(v>=3 for v in degree.values())
    A=render_variant("A",chains,[[i] for i in range(len(chains))],chains,
                     skel,mask,out,omitted,edges,branches,0)
    pairing,num_pairs=join_pairs(chains,degree)
    routes,members=stitch(chains,pairing)
    B=render_variant("B",routes,members,chains,skel,mask,out,omitted,edges,branches,num_pairs)
    src_roi=np.asarray(Image.fromarray(src).resize((150,240),Image.Resampling.LANCZOS))
    a=np.asarray(Image.open(out/"A-roi.png").convert("RGB"))
    b=np.asarray(Image.open(out/"B-roi.png").convert("RGB"))
    Image.fromarray(np.concatenate([src_roi,ctl,a,b],axis=1)).save(out/"source-v17-a-b-comparison.png")
    reports={"experiment":"ENGINE001_ANILINES_JUNCTION_REPAIR_V18","status":"OFFLINE_NON_NATIVE_RESEARCH",
             "source_sha256":SOURCE_SHA,"anilines_sha256":ANI_SHA,"A":A,"B":B}
    files=sorted([p for p in out.iterdir() if p.is_file()])
    reports["artifacts_sha256"]={p.name:digest(p) for p in files}
    (out/"report.json").write_text(json.dumps(reports,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    return reports

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--anilines",type=Path,required=True)
    p.add_argument("--v17-roi",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    report=run(args.source,args.anilines,args.v17_roi,args.output)
    print(json.dumps({"A":report["A"],"B":report["B"]},indent=2))
