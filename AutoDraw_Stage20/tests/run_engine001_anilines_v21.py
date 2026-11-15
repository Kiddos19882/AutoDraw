#!/usr/bin/env python3
"""ENGINE-001 V21: no-bridge color-owner split of V20-rejected chains, offline only."""
import argparse,io,json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from skimage.morphology import skeletonize
from run_engine001_anilines_v19_audit import SOURCE_SHA,ANILINES_SHA,frozen_b,pinned,sha
from run_engine001_anilines_v20 import (INK,palette_of,geometry_masks,owner_guard,
                                        components,chain_of_component,candidates)

def split_chain(chain,ani,palette,bg):
    """Return consecutive >=2 source-point runs; never bridge over unsafe edges."""
    valid=[]
    for p in chain:
        source,logical=geometry_masks([p,p])
        valid.append(bool(np.any(logical) and not np.any(source & ~ani)
                          and owner_guard(logical,palette,bg) is not None))
    edges=[]
    for i in range(len(chain)-1):
        if not valid[i] or not valid[i+1]:
            edges.append(False);continue
        source,logical=geometry_masks(chain[i:i+2])
        edges.append(bool(not np.any(source & ~ani) and
                          owner_guard(logical,palette,bg) is not None))
    result=[]
    start=None
    for i,ok in enumerate(edges):
        if ok:
            if start is None:start=i
        elif start is not None:
            result.append(chain[start:i+1])
            start=None
    if start is not None:result.append(chain[start:])
    return result,valid,edges

def recover(missing,ani,palette,bg):
    frozen_paths,rejections,source20,logical20,ncomp=candidates(missing,ani,palette,bg)
    if ncomp!=83 or len(frozen_paths)!=9 or rejections["owner_ambiguous"]!=23:
        raise ValueError("Frozen V20 candidate counts changed")
    ambiguous=[]
    for idx,points in enumerate(components(missing)):
        if not 2<=len(points)<=9:continue
        chain=chain_of_component(points)
        if chain is None:continue
        source,logical=geometry_masks(chain)
        if np.any(source & ~ani):continue
        if owner_guard(logical,palette,bg) is None:
            ambiguous.append((idx,chain))
    if len(ambiguous)!=23:raise ValueError("Ambiguous original V20 identities changed")
    new=[];src=np.zeros((320,200),bool);log=np.zeros((240,460),bool)
    audit=[]
    for idx,chain in ambiguous:
        runs,valid,edges=split_chain(chain,ani,palette,bg)
        audit.append({"component_index":idx,"size":len(chain),
                      "eligible_vertices":sum(valid),"blocked_vertices":len(valid)-sum(valid),
                      "eligible_edges":sum(edges),"blocked_edges":len(edges)-sum(edges),
                      "recovered_subpaths":len(runs)})
        for sub in runs:
            sm,lm=geometry_masks(sub)
            owner=owner_guard(lm,palette,bg)
            if owner is None or np.any(sm&~ani):raise ValueError("Unsafe V21 subpath")
            entry={"id":f"v21-extra-{len(new)}","component_index":idx,
                   "source_points":sub,
                   "logical_points":[[x*.75+155,y*.75] for x,y in sub],
                   "owner_palette_label":owner,
                   "brush_width_parameter":1,"preview_color_rgb":INK}
            new.append(entry);src|=sm;log|=lm
    if len(new)>100 or sum(len(x["source_points"]) for x in new)>900:
        raise ValueError("V21 quota exceeded")
    if np.any(src&~ani):raise ValueError("Foreign source pixel")
    return new,audit,src,log,source20,logical20

def run(source_file,ani_file,v18_zip,output):
    raw=pinned(source_file,SOURCE_SHA)
    if len(raw)!=97308:raise ValueError("Wrong source bytes")
    original=np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"))
    grayscale=np.asarray(Image.open(io.BytesIO(pinned(ani_file,ANILINES_SHA))).convert("L"))
    if original.shape!=(320,200,3) or grayscale.shape!=(320,200):
        raise ValueError("Wrong frozen dimensions")
    frozen,broi=frozen_b(v18_zip)
    skeleton=skeletonize(grayscale<128)
    baseline=cv2.dilate(frozen.astype(np.uint8),np.ones((3,3),np.uint8))>0
    missed=skeleton&~baseline
    if (int(skeleton.sum()),int((skeleton&baseline).sum()),int(missed.sum()))!=(5943,5792,151):
        raise ValueError("Unexpected frozen baseline")
    palette,bg=palette_of(original)
    paths,audit,source21,logical21,source20,logical20=recover(missed,grayscale<128,palette,bg)
    merged20=frozen|source20
    near20=cv2.dilate(merged20.astype(np.uint8),np.ones((3,3),np.uint8))>0
    if int((skeleton&near20).sum())!=5812:raise ValueError("V20 frozen comparison changed")
    merged21=merged20|source21
    near21=cv2.dilate(merged21.astype(np.uint8),np.ones((3,3),np.uint8))>0
    final=int((skeleton&near21).sum())
    if final<5812:raise ValueError("V21 source-support regression")
    margin=cv2.dilate((grayscale<128).astype(np.uint8),np.ones((3,3),np.uint8))>0
    if np.any(source21&~margin):raise ValueError("Source beyond1px violation")
    prev20=broi.copy()
    prev20[logical20[:,155:305]]=INK
    prev21=prev20.copy()
    prev21[logical21[:,155:305]]=INK
    srcroi=np.asarray(Image.fromarray(original).resize((150,240),Image.Resampling.LANCZOS))
    panel=np.concatenate([srcroi,prev20,prev21],axis=1)
    metrics={"skeleton_pixels":5943,"v18_supported_1px":5792,
             "v20_supported_1px":5812,"v21_supported_1px":final,
             "new_support_vs_v20":final-5812,"remaining_missed":5943-final,
             "v20_paths":9,"v20_vertices":20,
             "v21_extra_paths":len(paths),
             "v21_extra_vertices":sum(len(x["source_points"]) for x in paths),
             "v21_new_source_raster_pixels":int(source21.sum()),
             "v21_new_logical_raster_pixels":int(logical21.sum()),
             "v21_source_foreign_beyond1px":int((source21&~margin).sum()),
             "v21_owner_guard_violations":0,
             "ambiguous_original_components":len(audit),
             "ambiguous_eligible_vertices":sum(x["eligible_vertices"] for x in audit),
             "ambiguous_blocked_vertices":sum(x["blocked_vertices"] for x in audit),
             "ambiguous_eligible_edges":sum(x["eligible_edges"] for x in audit),
             "ambiguous_blocked_edges":sum(x["blocked_edges"] for x in audit)}
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError("No overwriting V21 evidence")
    output.mkdir(parents=True,exist_ok=True)
    images={"v21-three-panel.png":panel,
            "v21-extra-source.png":source21.astype(np.uint8)*255,
            "v21-extra-logical.png":logical21.astype(np.uint8)*255}
    hashes={}
    for name,data in images.items():
        p=output/name
        Image.fromarray(data).save(p);hashes[name]=sha(p.read_bytes())
    for name,data in (("extra-paths.json",paths),("ambiguous-audit.json",audit)):
        p=output/name
        p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
        hashes[name]=sha(p.read_bytes())
    report={"experiment":"ENGINE001_ANILINES_V21_OWNER_SPLIT",
            "status":"OFFLINE_DIAGNOSTIC_NON_NATIVE",
            "geometry_result":"GAIN" if final>5812 else "NO_GAIN",
            "source_sha256":SOURCE_SHA,"anilines_sha256":ANILINES_SHA,
            "v18_zip_sha256":sha(Path(v18_zip).read_bytes()),
            "metrics":metrics,"artifacts_sha256":hashes,
            "not_tested":["real color owner","Egret native width1","game exact CHALK",
                           "recognizability","independent E5"]}
    (output/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True,type=Path)
    parser.add_argument("--anilines",required=True,type=Path)
    parser.add_argument("--v18-zip",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(run(args.source,args.anilines,args.v18_zip,args.output)["metrics"],indent=2))
