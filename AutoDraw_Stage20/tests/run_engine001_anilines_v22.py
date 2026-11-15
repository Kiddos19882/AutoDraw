#!/usr/bin/env python3
"""ENGINE-001 V22 no-geometry palette owner proxy classification."""
import argparse,io,json,platform
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from skimage.morphology import skeletonize
from run_engine001_anilines_v19_audit import SOURCE_SHA,ANILINES_SHA,frozen_b,pinned,sha
from run_engine001_anilines_v20 import (palette_of,geometry_masks,owner_guard,
                                        components,chain_of_component,candidates)
from run_engine001_anilines_v21 import split_chain

def raster_profile(raster,palette,bg):
    if raster.shape!=(240,460) or palette.shape!=(240,460):
        raise ValueError("Expected 460x240 raster/palette")
    yy,xx=np.nonzero(raster)
    if not len(xx):raise ValueError("Empty candidate raster")
    outside=0;center_bg=0;center_mixed=False;near3=False;near5=False
    centers=set()
    for y,x in zip(yy.tolist(),xx.tolist()):
        if x<155 or x>=305 or not 0<=y<240:
            outside+=1
        center=int(palette[y,x]);centers.add(center)
        if center==bg:center_bg+=1
        for radius in (1,2):
            ymin=max(0,y-radius);ymax=min(240,y+radius+1)
            xmin=max(0,x-radius);xmax=min(460,x+radius+1)
            has_other=bool(np.any(palette[ymin:ymax,xmin:xmax]!=center))
            if radius==1:near3|=has_other
            else:near5|=has_other
    center_mixed=len(centers)>1
    # Tests below must not authorize drawing: this is descriptive only.
    return {"raster_pixels":len(xx),"outside_roi":outside,
            "background_center_pixels":center_bg,
            "any_background_center":center_bg>0,
            "mixed_center_classes":center_mixed,
            "mixed_3x3":near3,"mixed_5x5":near5,
            "uniform_nonbackground_1x1":outside==0 and center_bg==0 and not center_mixed,
            "uniform_nonbackground_3x3":outside==0 and center_bg==0 and not center_mixed and not near3,
            "uniform_nonbackground_5x5":outside==0 and center_bg==0 and not center_mixed and not near5}

def original_ambiguous(missed,ani,palette,bg):
    selected,rejected,_,_,n=candidates(missed,ani,palette,bg)
    if n!=83 or len(selected)!=9 or rejected["owner_ambiguous"]!=23:
        raise ValueError("Frozen V20 population changed")
    rejected_components=[]
    for index,points in enumerate(components(missed)):
        if not 2<=len(points)<=9:continue
        chain=chain_of_component(points)
        if chain is None:continue
        sr,lr=geometry_masks(chain)
        if np.any(sr&~ani):continue
        if owner_guard(lr,palette,bg) is None:
            rejected_components.append((index,chain))
    if len(rejected_components)!=23 or sum(len(c) for _,c in rejected_components)!=56:
        raise ValueError("Frozen V21 23x56 identities changed")
    for _,chain in rejected_components:
        runs,vertices,edges=split_chain(chain,ani,palette,bg)
        if runs or any(vertices) or any(edges):raise ValueError("V21 no-gain baseline changed")
    return rejected_components

def describe(original,ani,missing,palette,bg):
    chains=original_ambiguous(missing,ani,palette,bg)
    summaries=[];verts=[];links=[]
    counts={"background_center":0,"mixed_center":0,"mixed_3x3":0,
            "mixed_5x5":0,"uniform_nonbg_1x1":0,"uniform_nonbg_3x3":0,
            "uniform_nonbg_5x5":0,"outside_roi":0}
    def tally(seq,p):
        seq.append(p)
    for i,chain in chains:
        record={"component_index":i,"vertex_count":len(chain)}
        for n,p in enumerate(chain):
            source,logical=geometry_masks([p,p])
            if np.any(source&~ani):raise ValueError("Missing vertex outside genuine source")
            q=raster_profile(logical,palette,bg)
            q.update({"component_index":i,"source_xy":list(p),
                      "source_dark_gray_lt105":bool(cv2.cvtColor(original,cv2.COLOR_RGB2GRAY)[p[1],p[0]]<105)})
            verts.append(q)
        for a,bb in zip(chain,chain[1:]):
            source,logical=geometry_masks([a,bb])
            if np.any(source&~ani):raise ValueError("Missing edge outside genuine source")
            q=raster_profile(logical,palette,bg)
            q.update({"component_index":i,"source_start":list(a),"source_end":list(bb)})
            links.append(q)
        record["vertices"]=len(chain);record["links"]=len(chain)-1
        summaries.append(record)
    if len(verts)!=56 or len(links)!=33:raise ValueError("V21 population conservation")
    def aggregate(items):
        return {"count":len(items),"background_center":sum(p["any_background_center"] for p in items),
                "background_center_pixels":sum(p["background_center_pixels"] for p in items),
                "mixed_center":sum(p["mixed_center_classes"] for p in items),
                "mixed_3x3":sum(p["mixed_3x3"] for p in items),
                "mixed_5x5":sum(p["mixed_5x5"] for p in items),
                "uniform_nonbg_1x1":sum(p["uniform_nonbackground_1x1"] for p in items),
                "uniform_nonbg_3x3":sum(p["uniform_nonbackground_3x3"] for p in items),
                "uniform_nonbg_5x5":sum(p["uniform_nonbackground_5x5"] for p in items),
                "outside_roi":sum(bool(p["outside_roi"]) for p in items)}
    return summaries,verts,links,aggregate(verts),aggregate(links)

def run(source_file,ani_file,v18_zip,output):
    data=pinned(source_file,SOURCE_SHA)
    if len(data)!=97308:raise ValueError("Frozen source size mismatch")
    original=np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))
    gray=np.asarray(Image.open(io.BytesIO(pinned(ani_file,ANILINES_SHA))).convert("L"))
    if original.shape!=(320,200,3) or gray.shape!=(320,200):raise ValueError("Frozen geometry dimensions")
    frozen,_=frozen_b(v18_zip)
    skel=skeletonize(gray<128)
    near=cv2.dilate(frozen.astype(np.uint8),np.ones((3,3),np.uint8))>0
    missed=skel&~near
    if (int(skel.sum()),int((skel&near).sum()),int(missed.sum()))!=(5943,5792,151):
        raise ValueError("Frozen V19 baseline mismatch")
    palette,bg=palette_of(original)
    groups,verts,links,v,l=describe(original,gray<128,missed,palette,bg)
    roi=np.asarray(Image.fromarray(original).resize((150,240),Image.Resampling.LANCZOS))
    overlay=roi.copy()
    # Colors are display categories only, NOT paint commands or semantic annotations.
    legend={"bg_center":[255,25,50],"nonbg_3x3_mixed":[255,175,0],
            "nonbg_uniform":[0,165,220]}
    for x in verts:
        px,py=x["source_xy"]
        xx=round(px*.75);yy=round(py*.75)
        cls="bg_center" if x["any_background_center"] else ("nonbg_3x3_mixed" if x["mixed_3x3"] else "nonbg_uniform")
        cv2.circle(overlay,(xx,yy),2,legend[cls],-1,cv2.LINE_8)
    metrics={"frozen_v18_supported":5792,"frozen_v20_supported":5812,
             "frozen_v21_supported":5812,"source_skeleton":5943,
             "ambiguous_components":len(groups),"vertex_profiles":v,"link_profiles":l,
             "source_dark_vertex_count":sum(x["source_dark_gray_lt105"] for x in verts),
             "palette_bg_label":bg,"geometry_modified":False}
    out=Path(output)
    if out.exists() and any(out.iterdir()):raise ValueError("Refuse V22 evidence overwrite")
    out.mkdir(parents=True,exist_ok=True)
    files={}
    for name,obj in (("component-summary.json",groups),("vertex-profiles.json",verts),
                     ("link-profiles.json",links)):
        q=out/name;q.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        files[name]=sha(q.read_bytes())
    q=out/"rejection-categories-roi.png";Image.fromarray(overlay).save(q);files[q.name]=sha(q.read_bytes())
    # Derived palette indices are a diagnostic and not the original image colors.
    q=out/"quantized-palette-labels.png";Image.fromarray(palette[:,155:305]).save(q)
    files[q.name]=sha(q.read_bytes())
    report={"experiment":"ENGINE001_ANILINES_V22_PALETTE_PROXY_AUDIT",
            "status":"OFFLINE_DIAGNOSTIC_NO_NEW_PATHS",
            "source_sha256":SOURCE_SHA,"anilines_sha256":ANILINES_SHA,
            "v18_zip_sha256":sha(Path(v18_zip).read_bytes()),
            "versions":{"python":platform.python_version(),"opencv":cv2.__version__,
                        "numpy":np.__version__,"pillow":Image.__version__},
            "metrics":metrics,"derived_sha256":files,
            "not_tested":["true per-color boundary","native Egret width1",
                          "game exact CHALK","semantic quality","independent E5"]}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--anilines",required=True,type=Path)
    p.add_argument("--v18-zip",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(run(a.source,a.anilines,a.v18_zip,a.output)["metrics"],indent=2))
