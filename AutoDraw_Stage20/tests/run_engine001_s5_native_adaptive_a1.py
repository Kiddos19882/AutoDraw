"""A1 research: real native measured broad stamps + readback-selected P1 detail.
No production paths, no modeled raster as quality evidence.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

RENDERER = "real Egret 5.4.1 BoardPane/WebGLRenderer"
PLANNER_BLOB = "a268ee57aa4eeebe1c17927495cb8d8905d0e38b"
CASES = {"home": 2650, "illustration": 23588, "second-png": 11632}
RY, RX = 36, 39
OX = 465
WHITE = np.array([255,255,255],np.uint8)


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def masks(samples):
    """Actual sampled alpha windows: conservative observed union/intersection."""
    a = np.asarray(samples)
    require(a.shape==(2,73,79),"wrong alpha sample dimensions")
    support = (a>0).any(axis=0)
    core = (a>=128).all(axis=0)
    require(support.any() and core.any(),"empty sampled brush")
    require(not (support[0].any() or support[-1].any() or support[:,0].any()
                 or support[:,-1].any()),"native probe window clipped")
    return support,core


def measure_stamps(driver,native,out):
    paths,positions=[],[]
    for w in range(1,11):
        for y in (40,100):
            x=35+42*(w-1)
            paths.append(native.stroke(native.segment(x,y,12,0),w,0,len(paths)))
            positions.append((w,3*x,3*y))
    raw=native.render(driver,"native-stamp-atlas",paths)
    require(raw.shape==(720,1380,4),"native atlas shape")
    groups={w:[] for w in range(1,11)}
    for w,x,y in positions:
        groups[w].append(raw[y-RY:y+RY+1,x-RX:x+RX+1,3].copy())
    result,report={},{}
    for w,samples in groups.items():
        support,core=masks(samples)
        result[w]=(support,core)
        report[str(w)]=dict(support_pixels=int(support.sum()),core_pixels=int(core.sum()),
             alpha_difference=int(np.count_nonzero(samples[0]!=samples[1])),
             support_difference=int(np.count_nonzero((samples[0]>0)!=(samples[1]>0))),
             sample_centers=[list(p[1:]) for p in positions if p[0]==w])
    np.savez_compressed(out/"native-stamp-alpha.npz",
                        **{f"w{w}":np.stack(s) for w,s in groups.items()})
    write_json(out/"native-stamp-summary.json",report)
    return result,report


def pitch(proof,w):
    require(proof.get("renderer")==RENDERER and proof.get("smooth") is False
            and proof.get("mode")=="normal" and proof.get("probes")==80,
            "missing actual native footprint proof")
    m=proof["measurements"][f"horizontal:{w}"]
    x=min(9,math.floor(.8*m["axial_min_backing_px"]/3))
    y=math.floor(.8*m["lateral_min_backing_px"]/3)
    require(x>=1 and y>=1,"unusable integer logical pitch")
    return 3*x,3*y


def fit_centers(color_mask,support):
    return cv2.erode(color_mask.astype(np.uint8),support.astype(np.uint8),
                     anchor=(RX,RY),borderType=cv2.BORDER_CONSTANT,borderValue=0)>0


def rgb_int(rgb):
    return int.from_bytes(bytes(rgb),"big")


def luma(color):
    return 2126*((color>>16)&255)+7152*((color>>8)&255)+722*(color&255)


def broad_plan(want,stamps,proof,stroke):
    """Fit translated measured support, not nominal diameter or ideal capsule.
    Candidate predicted core is only an ordering heuristic; actual readback
    determines detail fallback.
    """
    h,w=want.shape[:2]
    colors=[c for c in np.unique(want.reshape(-1,3),axis=0) if np.any(c!=WHITE)]
    paths=[]
    counts={}
    for color in sorted(colors,key=lambda c:-luma(rgb_int(c))):
        allowed=np.all(want==color,axis=2)
        covered=np.zeros((h+2*RY,w+2*RX),bool)
        for width in range(10,1,-1):
            support,core=stamps[width]
            dx,dy=pitch(proof,width)
            fit=fit_centers(allowed,support)
            ys,xs=np.nonzero(fit[::dy,::dx])
            n=0
            for y,x in zip(ys*dy,xs*dx):
                y,x=int(y),int(x)
                region=covered[y:y+2*RY+1,x:x+2*RX+1]
                if not np.any(core&~region):
                    continue
                cx=(OX+x)/3
                cy=y/3
                pts=[dict(x=cx-6,y=cy),dict(x=cx+6,y=cy)]
                paths.append(stroke(pts,width,rgb_int(color),len(paths)))
                region|=core
                n+=1
            counts[f"{rgb_int(color):06x}:{width}"]=n
    return paths,counts


def white_rgb(raw):
    im=Image.fromarray(raw,"RGBA")
    bg=Image.new("RGBA",im.size,"white")
    bg.alpha_composite(im)
    return np.asarray(bg.convert("RGB"))


def nearest_palette(rgb,want):
    palette=np.unique(np.vstack((want.reshape(-1,3),WHITE[None,:])),axis=0)
    return palette[np.stack([np.square(rgb.astype(np.int32)-c).sum(axis=2)
                             for c in palette],axis=-1).argmin(axis=-1)]


def width1_pad(stamps,proof):
    ys,xs=np.nonzero(stamps[1][0])
    measured=proof["measurements"]["horizontal:1"]
    # Bounds around endpoints, plus three backing pixels for unmeasured
    # fractional phase and projected P1 segment length variation.
    px=max(0,int(np.max(np.abs(xs-RX)))-18,
           math.ceil((measured["axial_max_backing_px"]-36)/2))+3
    py=max(int(np.max(np.abs(ys-RY))),
           math.ceil(measured["lateral_max_backing_px"]/2))+3
    return px,py


def integral(mask):
    return cv2.integral(mask.astype(np.uint8),sdepth=cv2.CV_32S)


def area(s,x0,y0,x1,y1):
    return int(s[y1,x1])-int(s[y0,x1])-int(s[y1,x0])+int(s[y0,x0])


def retain_detail(baseline,want,broad_rgba,pad):
    """Only actual broad native readback can justify removing P1 paths."""
    require(broad_rgba.shape==(*want.shape[:2],4),"readback shape mismatch")
    h,w=want.shape[:2]
    nearest=nearest_palette(white_rgb(broad_rgba),want)
    valid=(broad_rgba[:,:,3]>=250)&np.all(nearest==want,axis=2)
    tables={}
    for color in np.unique(want.reshape(-1,3),axis=0):
        if np.all(color==WHITE):
            continue
        mask=np.all(want==color,axis=2)
        tables[rgb_int(color)]=(integral(mask),integral(mask&~valid))
    px,py=pad
    keep=[]
    reasons=Counter()
    for path in baseline:
        require(path["width"]==1,"baseline width drift")
        xy=path["points"]
        x0=max(0,min(w,math.floor(3*min(p["x"] for p in xy)-OX)-px))
        x1=max(0,min(w,math.ceil(3*max(p["x"] for p in xy)-OX)+px+1))
        y0=max(0,min(h,math.floor(3*min(p["y"] for p in xy))-py))
        y1=max(0,min(h,math.ceil(3*max(p["y"] for p in xy))+py+1))
        tables_for_color=tables.get(path["colorRgb"])
        if tables_for_color is None or x1<=x0 or y1<=y0:
            keep.append(path);reasons["no_backing_samples"]+=1
            continue
        total,missing=tables_for_color
        if not area(total,x0,y0,x1,y1):
            keep.append(path);reasons["no_backing_samples"]+=1
        elif area(missing,x0,y0,x1,y1):
            keep.append(path);reasons["actual_missing_or_wrong"]+=1
        else:
            reasons["already_native_covered"]+=1
    return keep,dict(reasons)


def combine(broad,detail):
    colors=sorted(set(p["colorRgb"] for p in broad+detail),key=lambda c:(-luma(c),c))
    out=[]
    for color in colors:
        for p in broad+detail:
            if p["colorRgb"]==color:
                out.append(dict(p,strokeId=f"icon-{len(out)}"))
    return out


def diagnostics(raw,want):
    crop=raw[:,OX:OX+450]
    nearest=nearest_palette(white_rgb(crop),want)
    fg=np.any(want!=WHITE,axis=2)
    edge=np.zeros(fg.shape,bool)
    d=np.any(want[1:]!=want[:-1],axis=2)
    edge[1:]|=d;edge[:-1]|=d
    d=np.any(want[:,1:]!=want[:,:-1],axis=2)
    edge[:,1:]|=d;edge[:,:-1]|=d
    gap=fg&((crop[:,:,3]<=24)|np.all(nearest==WHITE,axis=2))
    n,_,stats,_=cv2.connectedComponentsWithStats(gap.astype(np.uint8),connectivity=8)
    return dict(edge_pixels=int(edge.sum()),edge_nearest_correct=int((edge&np.all(nearest==want,axis=2)).sum()),
                largest_gap_component=int(stats[1:,cv2.CC_STAT_AREA].max()) if n>1 else 0)


def write_json(path,data):
    path.write_text(json.dumps(data,indent=2,sort_keys=True),encoding="utf8")


def save_plan(out,name,paths):
    with gzip.open(out/(name+"-plan.json.gz"),"wt",encoding="utf8") as f:
        json.dump(paths,f,separators=(",",":"))


def stats(paths):
    return dict(strokes=len(paths),width_histogram=dict(sorted(Counter(p["width"] for p in paths).items())),
                logical_path_length=sum(math.hypot(b["x"]-a["x"],b["y"]-a["y"])
                 for p in paths for a,b in zip(p["points"],p["points"][1:])))


def panel(out,original,prepared):
    from run_engine001_s5_native_transfer_p2 import alpha_onto_white
    items=[("ORIGINAL",alpha_onto_white(original)),("8 GAME COLORS",Image.fromarray(prepared,"RGB")),
           ("WIDTH 1 REFERENCE",Image.open(out/"width1-crop.png")),
           ("ADAPTIVE ACTUAL EGRET",Image.open(out/"adaptive-crop.png"))]
    atlas=Image.new("RGB",(4*450,760),(245,245,245))
    draw=ImageDraw.Draw(atlas)
    for i,(title,im) in enumerate(items):
        im=im.convert("RGB")
        im.thumbnail((450,720),Image.Resampling.NEAREST)
        atlas.paste(im,(450*i+(450-im.width)//2,30+(720-im.height)//2))
        draw.text((450*i+10,8),title,fill=(0,0,0))
    atlas.save(out/"comparison.png")


def main(case):
    import engine001_s5_native_brush_overlap as physical
    import run_engine001_s5_native_transfer_p2 as p2
    import run_engine001_s5_originals_native_transfer as transfer
    import run_engine001_s5_wv_full_native as native

    root=native.binding.ROOT
    rel,expected=p2.CASE[case]
    require(p2.git_blob((root/rel).read_bytes())==expected,"source blob drift")
    require(p2.git_blob(Path(physical.__file__).read_bytes())==PLANNER_BLOB,"accepted planner drift")
    out=Path(os.environ["RUNNER_TEMP"])/("s5-adaptive-a1-"+case)
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    source=out/"source"
    native.binding.pipeline.run(root,Path(rel),source,palette_only=True)
    image=np.asarray(Image.open(source/"palette-8.png").convert("RGBA"))
    target=np.where((image[:,:,3]==255)[:,:,None],image[:,:,:3],255).astype(np.uint8)
    require(1<=len(np.unique(target.reshape(-1,3),axis=0))<=9,"palette drift")
    Image.fromarray(target,"RGB").save(out/"prepared.png")
    geom=transfer.layout(target.shape[1],target.shape[0])
    want,_,_=transfer.projected(target,geom)
    Image.fromarray(want,"RGB").save(out/"projected-target.png")
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        require(not native.render(driver,"blank",[])[:,:,3].any(),"nonblank control")
        control=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        before=native.render(driver,"reference-original",control)
        driver.execute_script(native.full_fixture())
        require(np.array_equal(before,native.render(driver,"reference-expanded",control)),
                "native fixture drift")
        proof=physical.native_footprints(driver)
        write_json(out/"egret-physical-footprints.json",proof)
        stamps,stamp_report=measure_stamps(driver,native,out)
        baseline,params=physical.plan_same_color_overlap(target,geom,proof)
        require(len(baseline)==CASES[case],"historical width1 count drift")
        save_plan(out,"width1",baseline)
        base=native.render(driver,"width1",baseline)
        broad,counts=broad_plan(want,stamps,proof,native.stroke)
        save_plan(out,"broad",broad)
        broad_raw=native.render(driver,"broad",broad)
        pad=width1_pad(stamps,proof)
        detail,reasons=retain_detail(baseline,want,broad_raw[:,OX:OX+450],pad)
        final=combine(broad,detail)
        require(final and all(1<=p["width"]<=10 and p["colorRgb"]!=0xffffff for p in final),
                "invalid adaptive plan")
        save_plan(out,"adaptive",final)
        actual=native.render(driver,"adaptive",final)
        results={}
        for name,paths,raw in (("width1",baseline,base),("broad",broad,broad_raw),("adaptive",final,actual)):
            m,_,_,_=transfer.score(name,raw,target,geom,out)
            results[name]=dict(**stats(paths),metrics=m,detail_metrics=diagnostics(raw,want),
                               raw_sha256=sha(out/(name+".png")),
                               plan_sha256=sha(out/(name+"-plan.json.gz")))
    panel(out,Image.open(source/"01-original.png"),target)
    result=dict(schema="ENGINE001_S5_ADAPTIVE_A1_V1",case=case,sha=os.environ["GITHUB_SHA"],
        run=os.environ["GITHUB_RUN_ID"],source=rel,source_git_blob=expected,source_sha256=sha(root/rel),
        target_sha256=array_sha(target),source_size=[target.shape[1],target.shape[0]],
        geometry=geom,renderer=RENDERER,mode="normal",smooth=False,planner_blob=PLANNER_BLOB,
        reference_parameters=params,stamp_summary=stamp_report,pitch_backing={str(w):pitch(proof,w) for w in range(2,11)},
        broad_counts=counts,detail_pad_backing=pad,detail_selection=reasons,results=results,
        human_visual_review="PENDING",exact_CHALK="NOT_RUN",independent_E5="NOT_RUN",
        production_admissible=False)
    write_json(out/"a1-results.json",result)
    print("A1_RESULT "+json.dumps(result,separators=(",",":")),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--case",choices=tuple(CASES),required=True)
    main(p.parse_args().case)
