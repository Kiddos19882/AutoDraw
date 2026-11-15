#!/usr/bin/env python3
"""V32: native Egret adaptive color-region completion; original V5 baseline unchanged."""
from __future__ import annotations
import argparse,hashlib,json,math,platform,sys
from collections import Counter
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"source"/"preparation"))
from run_engine001_complex_holdout_v5 import (source_palette,build_variants,
                                               metrics,SCALE)
from run_engine001_visual_roi_palette_v28 import sheet

SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
WIDTHS=(15,8,4,2)
MAX_STROKES=2500
MAX_VERTICES=5900
OLD_STROKES=123
OLD_VERTICES=558
ALPHA_MIN=24
ROI_X=155
W,H=150,240

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def proxy_mask(s:dict)->np.ndarray:
    """MODEL_ONLY candidate pruning. Never accept game color coverage using this."""
    mask=np.zeros((H,W),np.uint8)
    pts=s["points"]
    if len(pts)<2:raise ValueError("Source V5 stroke without two endpoints")
    coords=[(int(round(p["x"]-ROI_X-.5)),int(round(p["y"]-.5))) for p in pts]
    for a,b in zip(coords,coords[1:]):
        cv2.line(mask,a,b,1,int(s["width"]),cv2.LINE_8)
    return mask.astype(bool)

def candidate_spans(safe:np.ndarray,width:int):
    step=max(1,int(math.floor(.65*width)))
    min_len=max(4,int(math.ceil(.60*width)))
    # Width first; horizontal and vertical runs in deterministic coordinate order.
    for axis in (0,1):
        for fixed in range(0,H if axis==0 else W,step):
            line=safe[fixed,:] if axis==0 else safe[:,fixed]
            padded=np.pad(line.astype(np.uint8),(1,1))
            delta=np.diff(padded.astype(np.int16))
            for lo,hi in zip(np.flatnonzero(delta==1),np.flatnonzero(delta==-1)):
                if int(hi-lo)<min_len:continue
                if axis==0:
                    yield ((int(lo),int(fixed)),(int(hi-1),int(fixed)),axis)
                else:
                    yield ((int(fixed),int(lo)),(int(fixed),int(hi-1)),axis)

def make_candidate(label:int,color_rgb:tuple[int,int,int],width:int,a,b,ordinal:int):
    rgb=(color_rgb[0]<<16)|(color_rgb[1]<<8)|color_rgb[2]
    return {"strokeId":f"icon-{ordinal}","width":width,"colorRgb":rgb,
            "colorIndex":label,
            "points":[{"x":float(a[0]+ROI_X)+.5,"y":float(a[1])+.5},
                      {"x":float(b[0]+ROI_X)+.5,"y":float(b[1])+.5}]}

def plan_v32(labels:np.ndarray,palette:dict,baseline:list[dict]):
    if labels.shape!=(240,460):raise ValueError("Unexpected 460x240 source")
    if len(baseline)!=OLD_STROKES or sum(len(s["points"]) for s in baseline)!=OLD_VERTICES:
        raise ValueError("Frozen V5 baseline plan count drift")
    if any(s["strokeId"]!=f"icon-{i}" for i,s in enumerate(baseline)):
        raise ValueError("V5 stroke ordering drift")
    if palette["background_index"]!=0:
        raise ValueError("V5 fixed background color changed")
    target=labels[:,ROI_X:ROI_X+W]
    colors={int(k):tuple(rgb) for k,rgb in palette["palette_rgb"].items()}
    output=[{**s,"points":[dict(p) for p in s["points"]]} for s in baseline]
    decisions={}
    cap_reached=False
    for label in sorted(colors):
        if label==0:continue
        own=target==label
        if not np.any(own):
            decisions[str(label)]={"added":0,"reason":"EMPTY_CLASS"}
            continue
        covered=np.zeros((H,W),bool)
        for s in baseline:
            if int(s["colorIndex"])==label:
                covered|=proxy_mask(s)
        inward=cv2.distanceTransform(own.astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        attempts=accepted=foreign_rejections=redundant=0
        per_width=Counter()
        for width in WIDTHS:
            safe=(own if width==2 else (own&(inward>=width/2+1.0)))
            for a,b,axis in candidate_spans(safe,width):
                attempts+=1
                if len(output)>=MAX_STROKES or sum(len(s["points"]) for s in output)>MAX_VERTICES-2:
                    cap_reached=True
                    break
                c=make_candidate(label,colors[label],width,a,b,len(output))
                foot=proxy_mask(c)
                if np.any(foot&~own):
                    foreign_rejections+=1
                    continue
                gain=int(np.count_nonzero(foot&own&~covered))
                if gain<max(6,2*width):
                    redundant+=1
                    continue
                output.append(c)
                covered|=foot
                accepted+=1
                per_width[str(width)]+=1
            if cap_reached:break
        decisions[str(label)]={
            "source_pixels":int(own.sum()),"baseline_proxy_cells":sum(1 for _ in []),
            "attempts":attempts,"accepted_additions":accepted,
            "rejected_proxy_foreign":foreign_rejections,
            "rejected_proxy_low_gain":redundant,
            "per_width_additions":dict(per_width),"cap_reached":cap_reached}
        if cap_reached:break
    if not OLD_STROKES<len(output)<=MAX_STROKES:
        raise ValueError("V32 no new resource-bounded shape strokes")
    vertices=sum(len(s["points"]) for s in output)
    if vertices>MAX_VERTICES:
        raise ValueError("V32 vertex budget exceeded")
    if any(not 2<=len(s["points"])<=128 or s["width"] not in (2,4,8,15,30) or
           any(not(0<=p["x"]<460 and 0<=p["y"]<240) for p in s["points"])
           for s in output):
        raise ValueError("V32 invalid native stroke geometry")
    return output,{"base_strokes":OLD_STROKES,"added_strokes":len(output)-OLD_STROKES,
                   "total_strokes":len(output),"synthetic_vertices_not_chalk":vertices,
                   "cap_reached":cap_reached,"per_class":decisions,
                   "model_warning":"cv2 LINE_8 only selects candidates; native Egret is sole coverage evidence"}

def logical_crop(image:Image.Image)->Image.Image:
    # Original actual WebGL PNG is in 3x backing; downscale for side-by-side only.
    if image.size!=(1380,720):raise ValueError("Unexpected native backing PNG")
    return image.convert("RGB").resize((460,240),Image.Resampling.LANCZOS).crop((155,0,305,240))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--v5-archive",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    workspace=args.workspace.resolve()
    out=args.output
    if out.exists() and any(out.iterdir()):raise ValueError("Never overwrite V32 evidence")
    labels,palette,logical=source_palette(workspace)
    if palette["png_sha256"]!=SOURCE_SHA:raise ValueError("V32 source SHA mismatch")
    old=json.loads((args.v5_archive/"report.json").read_text())
    old_summary=old["observed"]["V5"]
    if (old["source"]["png_sha256"]!=SOURCE_SHA or old_summary["strokes"]!=123
        or old_summary["synthetic_vertices_not_chalk"]!=558 or
        abs(old_summary["silhouette"]["coverage"]-.35054958525722224)>1e-10):
        raise ValueError("Frozen V5 native baseline mismatch")
    variants,_=build_variants(labels,palette)
    base=variants["V5"]
    proposal,planning=plan_v32(labels,palette,base)
    out.mkdir(parents=True,exist_ok=True)
    (out/"V32-planned-strokes.json").write_text(json.dumps({
        "experiment":"ENGINE001_NATIVE_ADAPTIVE_COLOR_V32",
        "strokes":proposal},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    (out/"planning-diagnostic.json").write_text(json.dumps(
        planning,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    # Existing V5 native Egret BoardPane WebGL renderer, no mathematical mask replay.
    observed=metrics({"V32":proposal},labels,palette,workspace,out)["V32"]
    old_native=Image.open(args.v5_archive/"V5"/"V5-over-white.png").convert("RGB")
    with Image.open(out/"V32"/"V32-over-white.png") as im:
        new_native=im.convert("RGB").copy()
    orig_roi=logical.crop((155,0,305,240))
    crops=[orig_roi,logical_crop(old_native),logical_crop(new_native)]
    names=["Original RGB","V5 native Egret","V32 native Egret"]
    sheet(crops,names,out/"comparison-full.png")
    sheet(crops,names,out/"comparison-faces.png",top=True)
    for name,img in zip(("original-roi","v5-native-roi","v32-native-roi"),crops):
        img.save(out/(name+".png"))
    hashes={str(p.relative_to(out)).replace("\\","/"):sha(p) for p in out.rglob("*") if p.is_file()}
    report={
        "experiment":"ENGINE001_NATIVE_ADAPTIVE_COLOR_V32",
        "source_sha256":SOURCE_SHA,
        "source_baseline":"V5 actual native archived CI43692740514 artifact14153250506",
        "v5_native":{"strokes":123,"synthetic_vertices_not_chalk":558,
                     "silhouette_coverage":old_summary["silhouette"]["coverage"],
                     "status":old_summary["status"]},
        "v32_native":{"strokes":observed["strokes"],"synthetic_vertices_not_chalk":
                      observed["synthetic_vertices_not_chalk"],
                      "silhouette_coverage":observed["silhouette"]["coverage"],
                      "status":observed["status"],
                      "per_color":{k:{"coverage":v["native"]["coverage"],
                                     "halo_ok":v["exterior"]["all_leakage_in_3logical_halo"],
                                     "foreign_color_pixels":v["native_overlap_into_other_color_pixels"]}
                                   for k,v in observed["per_color"].items()}},
        "planning":planning,"derived_sha256":hashes,
        "result_status":"E3_NATIVE_MEASUREMENT_NOT_GAME",
        "safety":"NO_PRODUCTION_PROMOTION; quality thresholds fixed >=99% and <=3 logical px",
        "not_tested":["live E4","exact run-bound CHALK","independent E5","full original RGB quality"],
        "versions":{"python":platform.python_version(),"opencv":cv2.__version__,
                    "numpy":np.__version__,"pillow":Image.__version__}}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"v5":report["v5_native"],"v32":{
        "strokes":report["v32_native"]["strokes"],
        "vertices":report["v32_native"]["synthetic_vertices_not_chalk"],
        "silhouette_coverage":report["v32_native"]["silhouette_coverage"],
        "status":report["v32_native"]["status"]}},indent=2))
if __name__=="__main__":
    main()
