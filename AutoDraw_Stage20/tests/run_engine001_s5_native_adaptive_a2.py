"""A2: native measured length/width atlas + actual-readback residual subsegments."""
import argparse
from collections import Counter
import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_s5_native_adaptive_a1 as a

LENGTHS=(24,12,6,3)
RY,RX=36,57
A1_BLOB="d04bfa0487197f9cacbe2161d02d9c73bed08b5f"
A1_COUNTS={"home":2283,"illustration":23231,"second-png":11577}


def mask_pair(samples):
    z=np.asarray(samples)
    a.require(z.shape==(2,73,115),"invalid A2 sample dimensions")
    support=(z>0).any(axis=0)
    core=(z>=128).all(axis=0)
    a.require(support.any() and core[RY,RX],"empty core")
    a.require(not(support[0].any() or support[-1].any() or
                  support[:,0].any() or support[:,-1].any()),"clipped support")
    return support,core


def center_span(line,center):
    a.require(line[center],"missing measured center")
    lo=hi=center
    while lo>0 and line[lo-1]:
        lo-=1
    while hi+1<len(line) and line[hi+1]:
        hi+=1
    return hi-lo+1


def pitch(core,length):
    ax=center_span(core[RY],RX)
    lat=center_span(core[:,RX],RY)
    dx=min(math.floor(.8*ax/3),math.floor(.75*length))
    dy=math.floor(.8*lat/3)
    return 3*max(1,dx),3*max(1,dy),dict(axial=ax,lateral=lat,
                 axial_overlap=dx>=1,lateral_overlap=dy>=1)


def measure(driver,native,out):
    atlas,report,samples={}, {}, {}
    for length in LENGTHS:
        paths,centers=[],[]
        for width in range(1,11):
            x=35+42*(width-1)
            for y in (40,100):
                paths.append(native.stroke(native.segment(x,y,length,0),width,0,len(paths)))
                centers.append((width,3*x,3*y))
        raw=native.render(driver,f"a2-atlas-L{length}",paths)
        a.require(raw.shape==(720,1380,4),"atlas dimensions")
        for width in range(1,11):
            windows=np.stack([raw[y-RY:y+RY+1,x-RX:x+RX+1,3].copy()
                              for w,x,y in centers if w==width])
            s,c=mask_pair(windows)
            key=f"w{width}_l{length}"
            atlas[width,length]=(s,c)
            samples[key]=windows
            report[key]=dict(support=int(s.sum()),core=int(c.sum()),
                    alpha_disagreement=int(np.count_nonzero(windows[0]!=windows[1])),
                    centers=[list(z[1:]) for z in centers if z[0]==width],
                    pitch=list(pitch(c,length)[:2]),spans=pitch(c,length)[2])
    np.savez_compressed(out/"a2-alpha-windows.npz",**samples)
    a.write_json(out/"a2-atlas-summary.json",report)
    return atlas,report


def fit(mask,support):
    # Crop only empty kernel margins; retain actual anchor, not an ideal shape.
    yy,xx=np.nonzero(support)
    y0,y1=min(int(yy.min()),RY),max(int(yy.max()),RY)+1
    x0,x1=min(int(xx.min()),RX),max(int(xx.max()),RX)+1
    return cv2.erode(mask.astype(np.uint8),support[y0:y1,x0:x1].astype(np.uint8),
           anchor=(RX-x0,RY-y0),borderType=cv2.BORDER_CONSTANT,borderValue=0)>0


def broad_plan(want,atlas,stroke):
    h,w=want.shape[:2]
    colors=[c for c in np.unique(want.reshape(-1,3),axis=0) if np.any(c!=a.WHITE)]
    paths,counts=[],{}
    for color in sorted(colors,key=lambda c:-a.luma(a.rgb_int(c))):
        rgb=a.rgb_int(color)
        allowed=np.all(want==color,axis=2)
        covered=np.zeros((h+2*RY,w+2*RX),bool)
        for width in range(10,1,-1):
            for length in LENGTHS:
                support,core=atlas[width,length]
                dx,dy,_=pitch(core,length)
                valid=fit(allowed,support)
                primary=valid[::dy,::dx]
                py,px=np.nonzero(primary)
                sy,sx=np.nonzero(valid[::3,::3])
                n=0
                minimum=math.ceil(.35*int(core.sum()))
                for phase,ys,xs in ((0,py*dy,px*dx),(1,sy*3,sx*3)):
                    for y,x in zip(ys,xs):
                        y,x=int(y),int(x)
                        if phase and y%dy==0 and x%dx==0:
                            continue
                        region=covered[y:y+2*RY+1,x:x+2*RX+1]
                        gain=int(np.count_nonzero(core&~region))
                        if gain<(minimum if phase else 1):
                            continue
                        cx=(a.OX+x)/3
                        cy=y/3
                        paths.append(stroke([dict(x=cx-length/2,y=cy),
                            dict(x=cx+length/2,y=cy)],width,rgb,len(paths)))
                        region|=core
                        n+=1
                counts[f"{rgb:06x}:{width}:{length}"]=n
    return paths,counts


def ranges(needed):
    """Inclusive sample ranges, extended one sample and merged."""
    needed=np.asarray(needed,dtype=bool)
    out=[]
    i=0
    while i<len(needed):
        if not needed[i]:
            i+=1
            continue
        start=i
        while i+1<len(needed) and needed[i+1]:
            i+=1
        lo=max(0,start-1)
        hi=min(len(needed)-1,i+1)
        if out and lo<=out[-1][1]+1:
            out[-1]=(out[-1][0],hi)
        else:
            out.append((lo,hi))
        i+=1
    return out


def residual(baseline,want,broad_rgba,pad):
    a.require(broad_rgba.shape==(*want.shape[:2],4),"readback dimensions")
    h,w=want.shape[:2]
    nearest=a.nearest_palette(a.white_rgb(broad_rgba),want)
    valid=(broad_rgba[:,:,3]>=250)&np.all(nearest==want,axis=2)
    tables={}
    for color in np.unique(want.reshape(-1,3),axis=0):
        if np.all(color==a.WHITE):
            continue
        m=np.all(want==color,axis=2)
        tables[a.rgb_int(color)]=(a.integral(m),a.integral(m&~valid))
    px,py=pad
    out,counts=[],Counter()
    for p in baseline:
        a.require(p["width"]==1 and len(p["points"])==2,"unexpected P1 path")
        u,v=p["points"]
        dx=v["x"]-u["x"]
        dy=v["y"]-u["y"]
        n=max(2,math.ceil(3*math.hypot(dx,dy))+1)
        ts=np.linspace(0,1,n)
        pts=[dict(x=u["x"]+float(t)*dx,y=u["y"]+float(t)*dy) for t in ts]
        t=tables.get(p["colorRgb"])
        needed=[]
        if t is None:
            out.append(p);counts["no_color_samples"]+=1
            continue
        for q in pts:
            x=3*q["x"]-a.OX;y=3*q["y"]
            x0=max(0,min(w,math.floor(x)-px))
            x1=max(0,min(w,math.ceil(x)+px+1))
            y0=max(0,min(h,math.floor(y)-py))
            y1=max(0,min(h,math.ceil(y)+py+1))
            needed.append(x1<=x0 or y1<=y0 or
                not a.area(t[0],x0,y0,x1,y1) or bool(a.area(t[1],x0,y0,x1,y1)))
        spans=ranges(needed)
        if not spans:
            counts["omitted"]+=1
        elif spans==[(0,n-1)]:
            out.append(p);counts["full"]+=1
        else:
            counts["split_original"]+=1
            for lo,hi in spans:
                a.require(hi>lo,"degenerate residual")
                out.append(dict(p,points=[pts[lo],pts[hi]]))
                counts["split_output"]+=1
    counts["residual_paths"]=len(out)
    return out,dict(counts)


def panel(out,original,target):
    from run_engine001_s5_native_transfer_p2 import alpha_onto_white
    items=[("ORIGINAL",alpha_onto_white(original)),("8 GAME COLORS",Image.fromarray(target,"RGB"))]
    for title,name in (("WIDTH 1","width1"),("A1 ACCEPTED","a1"),("A2 ADAPTIVE","a2")):
        items.append((title,Image.open(out/(name+"-crop.png"))))
    atlas=Image.new("RGB",(2250,760),(245,245,245))
    draw=ImageDraw.Draw(atlas)
    for i,(title,img) in enumerate(items):
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
    a.require(p2.git_blob((root/rel).read_bytes())==expected,"source drift")
    a.require(p2.git_blob(Path(physical.__file__).read_bytes())==a.PLANNER_BLOB,"P1 drift")
    a.require(p2.git_blob(Path(a.__file__).read_bytes())==A1_BLOB,"A1 drift")
    out=Path(os.environ["RUNNER_TEMP"])/("s5-adaptive-a2-"+case)
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
        control=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        before=native.render(driver,"reference-original",control)
        driver.execute_script(native.full_fixture())
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
                  raw_sha256=a.sha(out/(name+".png")),plan_sha256=a.sha(out/(name+"-plan.json.gz")))
        save("width1",baseline,native.render(driver,"width1",baseline))
        broad1,_=a.broad_plan(want,stamps,proof,native.stroke)
        raw1=native.render(driver,"a1-broad",broad1)
        save("a1-broad",broad1,raw1)
        detail1,_=a.retain_detail(baseline,want,raw1[:,a.OX:a.OX+450],pad)
        final1=a.combine(broad1,detail1)
        a.require(len(final1)==A1_COUNTS[case],"accepted A1 count drift")
        save("a1",final1,native.render(driver,"a1",final1))
        atlas,summary=measure(driver,native,out)
        broad2,counts=broad_plan(want,atlas,native.stroke)
        raw2=native.render(driver,"a2-broad",broad2)
        save("a2-broad",broad2,raw2)
        detail2,split=residual(baseline,want,raw2[:,a.OX:a.OX+450],pad)
        final2=a.combine(broad2,detail2)
        a.require(final2 and all(1<=p["width"]<=10 and p["colorRgb"]!=0xffffff for p in final2),
                  "invalid A2 plan")
        save("a2",final2,native.render(driver,"a2",final2))
    panel(out,Image.open(source/"01-original.png"),target)
    import json
    result=dict(schema="ENGINE001_S5_ADAPTIVE_A2_V1",case=case,sha=os.environ["GITHUB_SHA"],
        run=os.environ["GITHUB_RUN_ID"],source=rel,source_git_blob=expected,
        source_sha256=a.sha(root/rel),target_sha256=a.array_sha(target),
        geometry=geom,renderer=a.RENDERER,mode="normal",smooth=False,
        p1_blob=a.PLANNER_BLOB,a1_blob=A1_BLOB,reference_parameters=params,
        native_atlas=summary,broad_counts=counts,residual=split,detail_pad_backing=pad,
        results=results,human_visual_review="PENDING",exact_CHALK="NOT_RUN",
        independent_E5="NOT_RUN",production_admissible=False)
    a.write_json(out/"a2-results.json",result)
    print("A2_RESULT "+json.dumps(result,separators=(",",":")),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=tuple(A1_COUNTS),required=True)
    main(parser.parse_args().case)
