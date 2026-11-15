#!/usr/bin/env python3
"""ENGINE-001 V20 additive short-fragment recovery, OFFLINE / not Egret."""
import argparse,io,json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from skimage.morphology import skeletonize
from run_engine001_anilines_v19_audit import SOURCE_SHA,ANILINES_SHA,frozen_b,pinned,sha

INK=(49,38,43)
N8=tuple((dx,dy) for dy in (-1,0,1) for dx in (-1,0,1) if dx or dy)

def chain_of_component(points):
    nodes=set(points)
    if not 2<=len(nodes)<=9 or len(nodes)!=len(points):return None
    adj={p:sorted((p[0]+dx,p[1]+dy) for dx,dy in N8
                  if (p[0]+dx,p[1]+dy) in nodes) for p in nodes}
    if any(len(ns)>2 or len(ns)==0 for ns in adj.values()):return None
    ends=sorted((p for p in nodes if len(adj[p])==1),key=lambda p:(p[1],p[0]))
    if len(ends)!=2:return None
    chain=[ends[0]];prev=None
    while len(chain)<len(nodes):
        here=chain[-1]
        opts=[p for p in adj[here] if p!=prev]
        if len(opts)!=1 or opts[0] in chain:return None
        chain.append(opts[0]);prev=here
    return chain if chain[-1]==ends[1] else None

def palette_of(source):
    canvas=Image.new("RGB",(460,240),(255,255,255))
    canvas.paste(Image.fromarray(source).resize((150,240),Image.Resampling.LANCZOS),(155,0))
    labels=np.asarray(canvas.quantize(colors=8,method=Image.Quantize.MEDIANCUT,
                                     dither=Image.Dither.NONE),dtype=np.uint8)
    bg=int(np.argmax(np.bincount(labels.ravel(),minlength=256)))
    return labels,bg

def geometry_masks(points):
    source=np.zeros((320,200),np.uint8)
    logical=np.zeros((240,460),np.uint8)
    for a,b in zip(points,points[1:]):
        cv2.line(source,a,b,1,1,cv2.LINE_8)
    coords=[(round(x*.75+155),round(y*.75)) for x,y in points]
    for a,b in zip(coords,coords[1:]):
        cv2.line(logical,a,b,1,1,cv2.LINE_8)
    return source.astype(bool),logical.astype(bool)

def owner_guard(raster,palette,bg):
    if raster.shape!=(240,460) or palette.shape!=(240,460):
        raise ValueError("Bad color ownership dimensions")
    yy,xx=np.nonzero(raster)
    if not len(yy):return None
    labels=set()
    for y,x in zip(yy.tolist(),xx.tolist()):
        if x<156 or x>=304 or y<1 or y>=239:return None
        label=int(palette[y,x])
        if label==bg or np.any(palette[y-1:y+2,x-1:x+2]!=label):return None
        labels.add(label)
    return next(iter(labels)) if len(labels)==1 else None

def components(mask):
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8)
    result=[]
    for i in range(1,n):
        ys,xs=np.where(labels==i)
        result.append([(int(x),int(y)) for x,y in zip(xs,ys)])
    result.sort(key=lambda pts:min((y,x) for x,y in pts))
    return result

def candidates(missed,ani,palette,bg):
    selected=[];rejected={"singleton_or_long":0,"branched_or_cycle":0,
                          "raster_outside_source":0,"owner_ambiguous":0}
    input_components=components(missed)
    source_add=np.zeros((320,200),bool)
    logical_add=np.zeros((240,460),bool)
    for points in input_components:
        if not 2<=len(points)<=9:
            rejected["singleton_or_long"]+=1;continue
        chain=chain_of_component(points)
        if chain is None:
            rejected["branched_or_cycle"]+=1;continue
        source,logical=geometry_masks(chain)
        if np.any(source & ~ani):
            rejected["raster_outside_source"]+=1;continue
        owner=owner_guard(logical,palette,bg)
        if owner is None:
            rejected["owner_ambiguous"]+=1;continue
        selected.append({"id":f"v20-extra-{len(selected)}",
                         "source_points":chain,
                         "logical_points":[[x*.75+155,y*.75] for x,y in chain],
                         "owner_palette_label":owner,
                         "brush_width_parameter":1,"preview_color_rgb":INK})
        source_add|=source;logical_add|=logical
    if sum(rejected.values())+len(selected)!=len(input_components):
        raise ValueError("V20 candidate accounting mismatch")
    if len(selected)>100 or sum(len(p["source_points"]) for p in selected)>900:
        raise ValueError("V20 research quota exceeded")
    if np.any(source_add & ~ani):
        raise ValueError("V20 foreign source pixel")
    return selected,rejected,source_add,logical_add,len(input_components)

def run(source_file,ani_file,v18_zip,output):
    raw=pinned(source_file,SOURCE_SHA)
    if len(raw)!=97308:raise ValueError("Wrong frozen source byte size")
    original=np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"))
    gray=np.asarray(Image.open(io.BytesIO(pinned(ani_file,ANILINES_SHA))).convert("L"))
    if original.shape!=(320,200,3) or gray.shape!=(320,200):
        raise ValueError("Unexpected frozen dimensions")
    frozen,broi=frozen_b(v18_zip)
    skeleton=skeletonize(gray<128)
    baseline=cv2.dilate(frozen.astype(np.uint8),np.ones((3,3),np.uint8))>0
    missed=skeleton & ~baseline
    if (int(skeleton.sum()),int((skeleton&baseline).sum()),int(missed.sum()))!=(5943,5792,151):
        raise ValueError("V19 baseline mismatch")
    labels,bg=palette_of(original)
    paths,rejected,source_add,logical_add,ncomp=candidates(missed,gray<128,labels,bg)
    final=frozen|source_add
    final_near=cv2.dilate(final.astype(np.uint8),np.ones((3,3),np.uint8))>0
    supported=int((skeleton&final_near).sum())
    allowed=cv2.dilate((gray<128).astype(np.uint8),np.ones((3,3),np.uint8))>0
    if supported<5792 or np.any(source_add&~allowed):
        raise ValueError("Coverage regression or foreign AniLines pixel")
    preview=broi.copy()
    paint=logical_add[:,155:305]
    preview[paint]=INK
    new_only=np.full_like(broi,255);new_only[paint]=INK
    source_roi=np.asarray(Image.fromarray(original).resize((150,240),Image.Resampling.LANCZOS))
    panel=np.concatenate([source_roi,broi,preview],axis=1)
    metrics={"source_skeleton":5943,"baseline_supported_1px":5792,
             "final_supported_1px":supported,"added_support_pixels":supported-5792,
             "remaining_unsupported":5943-supported,"missing_components":ncomp,
             "baseline_paths":410,"baseline_vertices":1792,
             "accepted_paths":len(paths),"added_vertices":sum(len(p["source_points"]) for p in paths),
             "rejected":rejected,"accepted_source_raster_pixels":int(source_add.sum()),
             "accepted_logical_raster_pixels":int(logical_add.sum()),
             "foreign_source_beyond1px":int((source_add&~allowed).sum()),
             "new_owner_violations":0,"background_label":bg}
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError("Refuse evidence overwrite")
    output.mkdir(parents=True,exist_ok=True)
    images={"v20-three-panel.png":panel,"v20-new-only.png":new_only,
            "v20-source-added.png":source_add.astype(np.uint8)*255}
    hashes={}
    for name,img in images.items():
        dest=output/name;Image.fromarray(img).save(dest);hashes[name]=sha(dest.read_bytes())
    (output/"added-paths.json").write_text(json.dumps(paths,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    hashes["added-paths.json"]=sha((output/"added-paths.json").read_bytes())
    report={"experiment":"ENGINE001_ANILINES_V20_OWNER_GUARDED_SHORT_RECOVERY",
            "status":"OFFLINE_DIAGNOSTIC_NO_NATIVE",
            "geometry_result":"GAIN" if supported>5792 else "NO_GAIN",
            "source_sha256":SOURCE_SHA,"anilines_sha256":ANILINES_SHA,
            "v18_zip_sha256":sha(Path(v18_zip).read_bytes()),
            "metrics":metrics,"artifacts_sha256":hashes,
            "not_tested":["native Egret width1","game CHALK","color painting",
                          "true semantic seam","independent E5"]}
    (output/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--anilines",required=True,type=Path)
    p.add_argument("--v18-zip",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.anilines,a.v18_zip,a.output)["metrics"],indent=2))
