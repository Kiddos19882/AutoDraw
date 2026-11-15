#!/usr/bin/env python3
"""V34: source-RGB median recoloring of frozen V33 paths; native Egret only."""
from __future__ import annotations
import argparse,copy,hashlib,json,platform,sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from run_engine001_native_v29_brush2_v33 import (
    SOURCE_SHA,FROZEN_PLAN_SHA,FROZEN_PREVIEW_SHA,translate,logical_crop)
from run_engine001_visual_roi_palette_v28 import prepare_source,quantize_case,sheet,sha
from run_engine001_complex_holdout_v5 import native_batch

V33_ZIP_SHA="d3eeb4dc7bc37924aef7713b4b77c76ad3e4adeb2f7baad17b782f4764b66fb1"
ALPHA=(24,128)
ROI=(155,0,305,240)
def png_chunks(path):
    """Preserve exact IDAT bytes; ancillary metadata may be renderer-generated."""
    data=path.read_bytes()
    if not data.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        raise ValueError("V34R invalid native PNG signature")
    offset=8; chunks=[]
    while offset<len(data):
        if offset+12>len(data):raise ValueError("V34R truncated native PNG")
        size=int.from_bytes(data[offset:offset+4],"big")
        kind=data[offset+4:offset+8]
        stop=offset+12+size
        if stop>len(data):raise ValueError("V34R truncated PNG chunk")
        chunks.append((kind,data[offset+8:offset+8+size]))
        offset=stop
        if kind==b"IEND":break
    if offset!=len(data):raise ValueError("V34R unexpected PNG trailing data")
    return chunks

def png_pixel_exact_replay(reference,new):
    """Reject pixel/IDAT drift, allow only changed ancillary PNG metadata."""
    from io import BytesIO
    ref_bytes=reference.read_bytes();new_bytes=new.read_bytes()
    with Image.open(BytesIO(ref_bytes)) as a, Image.open(BytesIO(new_bytes)) as b:
        a=np.asarray(a.convert("RGBA"))
        b=np.asarray(b.convert("RGBA"))
    if a.shape!=(720,1380,4) or b.shape!=a.shape or not np.array_equal(a,b):
        raise ValueError("V34R frozen native pixel RGBA reproducibility FAILED")
    ref_chunks=png_chunks(reference);new_chunks=png_chunks(new)
    for key in (b"IHDR",b"IDAT"):
        left=[chunk for kind,chunk in ref_chunks if kind==key]
        right=[chunk for kind,chunk in new_chunks if kind==key]
        if not left or left!=right:
            raise ValueError("V34R frozen native critical PNG data changed: "+key.decode())
    ref_other=[(key,body) for key,body in ref_chunks if key not in (b"IHDR",b"IDAT",b"IEND")]
    new_other=[(key,body) for key,body in new_chunks if key not in (b"IHDR",b"IDAT",b"IEND")]
    return {"pixel_rgba_exact":True,
            "PNG_byte_exact":ref_bytes==new_bytes,
            "ancillary_chunks_differ":ref_other!=new_other,
            "reference_SHA256":hashlib.sha256(ref_bytes).hexdigest(),
            "replay_SHA256":hashlib.sha256(new_bytes).hexdigest(),
            "reference_ancillary_types":[kind.decode("latin1") for kind,_ in ref_other],
            "replay_ancillary_types":[kind.decode("latin1") for kind,_ in new_other]}

def rgb_int(rgb): return (int(rgb[0])<<16)|(int(rgb[1])<<8)|int(rgb[2])
def median_map(original,idx,classes):
    pixels=np.asarray(original.convert("RGB"),dtype=np.uint8)
    if pixels.shape!=(240,150,3) or idx.shape!=(240,150):
        raise ValueError("V34 source or label shape differs")
    result={}
    for k in classes:
        owned=pixels[idx==k]
        if not len(owned): raise ValueError("V34 empty retained color class")
        # Even samples: lower of two center sorted byte values, not mean.
        result[k]=[int(np.sort(owned[:,c])[((len(owned)-1)//2)]) for c in range(3)]
    return result
def recolor_strokes(base,colors):
    """Return color-only copy; leave frozen routing, width, order and metadata intact."""
    result=copy.deepcopy(base)
    if sorted(colors)!=[4,5,6,7]:
        raise ValueError("V34 expected four unchanged target color classes")
    for s in result:
        label=int(s["colorIndex"])
        if label not in colors: raise ValueError("V34 stroke with unknown palette class")
        rgb=colors[label]
        if len(rgb)!=3 or any(not isinstance(v,int) or not 0<=v<=255 for v in rgb):
            raise ValueError("V34 invalid color byte")
        s["colorRgb"]=rgb_int(rgb)
    if len(result)!=len(base) or any(
        {k:v for k,v in x.items() if k!="colorRgb"} !=
        {k:v for k,v in y.items() if k!="colorRgb"} for x,y in zip(base,result)):
        raise ValueError("V34 changed frozen geometry")
    return result

def warm_mask(source):
    rgb=np.asarray(source.convert("RGB"),dtype=np.uint8)
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    return ((hsv[:,:,0]>=3)&(hsv[:,:,0]<=27)&
            (hsv[:,:,1]>=77)&(hsv[:,:,2]>=51))
def mae(image,original,mask=None):
    x=np.asarray(image.convert("RGB"),np.int16)
    y=np.asarray(original.convert("RGB"),np.int16)
    if mask is not None:
        if not np.any(mask): raise ValueError("V34 empty warm ROI")
        x,y=x[mask],y[mask]
    return float(np.abs(x-y).mean())
def verify_inputs(source,v29,v33):
    if sha(source)!=SOURCE_SHA: raise ValueError("V34 source SHA changed")
    p=v29/"budgeted-plan.json"; pic=v29/"budgeted-roi.png"
    if sha(p)!=FROZEN_PLAN_SHA or sha(pic)!=FROZEN_PREVIEW_SHA:
        raise ValueError("V34 frozen V29 artifact changed")
    source_roi,canvas=prepare_source(source)
    idx,palette,skipped=quantize_case(source_roi,canvas,8,False,True)
    if skipped!=[0,1,2,3]:raise ValueError("V34 skip labels changed")
    plan=json.loads(p.read_text(encoding="utf-8"))
    if [k["rgb"] for k in plan["palette"]] != [k["rgb"] for k in palette]:
        raise ValueError("V34 palette drift")
    a,zero=translate(plan,idx,palette)
    if zero!=447 or sorted({s["colorIndex"] for s in a}) != [4,5,6,7]:
        raise ValueError("V34 baseline geometry drift")
    frozen=json.loads((v33/"native-width2-strokes.json").read_text(encoding="utf-8"))
    if frozen["strokes"]!=a or frozen["synthetic_accepted_points_not_chalk"]!=3890:
        raise ValueError("Original V33 native strokes disagree with V29 translation")
    manifest=json.loads((v33/"report.json").read_text(encoding="utf-8"))
    if manifest["source_sha256"]!=SOURCE_SHA or manifest["synthetic_strokes"]!=1945:
        raise ValueError("V33 report identity differs")
    for name,digest in manifest["derived_sha256"].items():
        if sha(v33/name)!=digest:raise ValueError("V33 artifact inner SHA mismatch: "+name)
    return source_roi,idx,palette,a,manifest

def main():
    p=argparse.ArgumentParser()
    for name in ("workspace","source","v29-archive","v33-archive","output"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V34 no-overwrite evidence")
    original,labels,palette,base,v33_report=verify_inputs(a.source,a.v29_archive,a.v33_archive)
    colors=median_map(original,labels[:,155:305],(4,5,6,7))
    b=recolor_strokes(base,colors)
    out=a.output;out.mkdir(parents=True)
    (out/"V34-B-strokes.json").write_text(json.dumps({
        "experiment":"ENGINE001_NATIVE_WARM_COLOR_V34","strokes":b,
        "original_V33_synthetic_vertices_NOT_CHALK":3890,
        "palette_source_median_by_class":colors},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Actual archived BoardPane/Egret WebGL native RGBA, never a CV/PIL brush.
    rgba_a,scenes_a,meta_a=native_batch(a.workspace,"V34-A",base,out)
    rgba_b,scenes_b,meta_b=native_batch(a.workspace,"V34-B",b,out)
    control_replay={}
    for stem in ["composite"]+[f"color-{k}" for k in (4,5,6,7)]:
        if not np.array_equal(rgba_a[stem][:,:,3],rgba_b[stem][:,:,3]):
            raise ValueError("V34R native alpha geometry changed: "+stem)
        control_replay[stem]=png_pixel_exact_replay(
            a.v33_archive/("V33-"+stem+".png"),out/("V34-A-"+stem+".png"))
    warm=warm_mask(original)
    img_a=logical_crop(rgba_a["composite"])
    img_b=logical_crop(rgba_b["composite"])
    img_a.save(out/"V34-A-roi.png");img_b.save(out/"V34-B-roi.png")
    sheet([original,img_a,img_b],["Original RGB","V33 frozen native A","V34 median RGB native B"],out/"comparison-full.png")
    sheet([original,img_a,img_b],["Original RGB","V33 native A","V34 median RGB B"],out/"comparison-faces.png",top=True)
    full_a,full_b=mae(img_a,original),mae(img_b,original)
    warm_a,warm_b=mae(img_a,original,warm),mae(img_b,original,warm)
    per_color={}
    target=np.repeat(np.repeat(labels,3,axis=0),3,axis=1)
    for k in (4,5,6,7):
        record={
            "old_rgb":next(s["colorRgb"] for s in base if s["colorIndex"]==k),
            "new_rgb":rgb_int(colors[k]),
            "target_pixels":int(np.count_nonzero(target==k))}
        for threshold in ALPHA:
            mask=rgba_a[f"color-{k}"][:,:,3]>=threshold
            actual={
                "native_target_recall":float(np.count_nonzero(mask&(target==k))/
                                             max(1,np.count_nonzero(target==k))),
                "painted_native_pixels":int(np.count_nonzero(mask)),
                "foreign_palette_pixel_count":int(np.count_nonzero(mask&(target>=0)&(target!=k))),
                "outside_artwork_roi_pixels":int(np.count_nonzero(mask[:,:155*3]))+
                                             int(np.count_nonzero(mask[:,305*3:]))}
            frozen=v33_report["native_per_color"][str(k)][str(threshold)]
            for key,value in actual.items():
                if isinstance(value,float):
                    if abs(value-frozen[key])>1e-12:
                        raise ValueError("V34 native recall changed from V33: "+str(k))
                elif value!=frozen[key]:
                    raise ValueError("V34 native color footprint changed from V33: "+str(k)+" "+key)
            if not frozen["inside_3_logical_halo"]:
                raise ValueError("V33 failed frozen color halo gate")
            record[str(threshold)]=actual
        per_color[str(k)]=record
    approved=bool(full_b<full_a and warm_b<warm_a)
    hashes={str(path.relative_to(out)).replace("\\","/"):sha(path)
            for path in out.rglob("*") if path.is_file()}
    report={
        "experiment":"ENGINE001_NATIVE_WARM_COLOR_V34R",
        "status":"E3_NATIVE_REPLAY_ONLY_NOT_LIVE",
        "source_sha256":SOURCE_SHA,
        "baseline_V33_sha":"386c8c24c0e99765230e7de0e11c864716a1e815",
        "identical_geometry":True,"native_alpha_identical":True,
        "v33_native_pixel_rgba_exact_replay":True,
        "v33_native_png_byte_hash_reproduced":all(v["PNG_byte_exact"] for v in control_replay.values()),
        "frozen_native_PNG_replay_per_scene":control_replay,
        "strokes":1945,"synthetic_vertices_NOT_CHALK":3890,
        "medians":colors,"per_color":per_color,
        "warm_pixel_count":int(warm.sum()),
        "full_source_rgb_mae":{"V33_A":full_a,"V34_B":full_b},
        "warm_source_rgb_mae":{"V33_A":warm_a,"V34_B":warm_b},
        "color_fidelity_improvement_diagnostic":approved,
        "production_quality_pass":False,
        "not_tested":["real E4","independent E5","exact CHALK","native >=99% each color"],
        "native_meta":{"A":meta_a,"B":meta_b},
        "derived_sha256":hashes,"versions":{"python":platform.python_version(),
        "numpy":np.__version__,"opencv":cv2.__version__,"pillow":Image.__version__}}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"candidate_improved":approved,
                      "full_rgb_mae":[full_a,full_b],
                      "warm_rgb_mae":[warm_a,warm_b],
                      "warm_pixels":int(warm.sum())},indent=2))
if __name__=="__main__":main()
