"""Research-only: real native Egret feedback on three additional S5 originals.
Hello/Pink: full prepared source and unchanged connected plan.
EZAL: deterministic detail-rich 200x320 ROI derived from entire original.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from PIL import Image
import run_engine001_s5_wv_full_native as native

CASES={"hello":1,"ezal":2,"pink":3}

def choose_roi(rgb):
    h,w=rgb.shape[:2]
    assert h>=320 and w>=200
    edges=np.zeros((h,w),np.int32)
    edges[:,1:]+=np.any(rgb[:,1:]!=rgb[:,:-1],axis=2)
    edges[1:]+=np.any(rgb[1:]!=rgb[:-1],axis=2)
    pixels=(3*edges+np.any(rgb!=255,axis=2)).astype(np.int64)
    s=np.pad(pixels.cumsum(0).cumsum(1),((1,0),(1,0)))
    scores=s[320:,200:]-s[:-320,200:]-s[320:,:-200]+s[:-320,:-200]
    y,x=np.unravel_index(int(scores.argmax()),scores.shape)
    return int(x),int(y),int(scores[y,x])

def layout(w,h):
    scale=min(150/w,240/h)
    return {"left":155+(150-w*scale)/2,"top":(240-h*scale)/2,
            "scale":float(scale),"width":w,"height":h}

def board_point(x,y,g):
    return {"x":g["left"]+g["scale"]*(float(x)+.5),
            "y":g["top"]+g["scale"]*(float(y)+.5)}

def projected(target,g):
    xx=155+(np.arange(450)+.5)/3
    yy=(np.arange(720)+.5)/3
    cols=np.floor((xx-g["left"])/g["scale"]).astype(np.int32)
    rows=np.floor((yy-g["top"])/g["scale"]).astype(np.int32)
    valid=(rows[:,None]>=0)&(rows[:,None]<len(target))&(cols[None,:]>=0)&(cols[None,:]<target.shape[1])
    wanted=target[np.clip(rows,0,len(target)-1)[:,None],
                  np.clip(cols,0,target.shape[1]-1)[None,:]]
    return np.where(valid[...,None],wanted,255).astype(np.uint8),cols,rows

def score(name,rgba,target,g,out):
    assert rgba.shape==(720,1380,4)
    img=Image.fromarray(rgba[:720,465:915],"RGBA")
    white=Image.new("RGBA",img.size,"white")
    white.alpha_composite(img)
    arr=np.asarray(white.convert("RGB"))
    white.convert("RGB").save(out/(name+"-crop.png"))
    want,cols,rows=projected(target,g)
    pal=np.unique(np.vstack((target.reshape(-1,3),np.array([[255,255,255]],np.uint8))),axis=0)
    nearest=pal[np.stack([np.square(arr.astype(np.float32)-c).sum(axis=2)
                          for c in pal],axis=-1).argmin(axis=-1)]
    fg=np.any(want!=255,axis=2)
    alpha=rgba[:720,465:915,3]
    whitewrong=np.all(nearest==255,axis=2)
    gaps=fg&(whitewrong|(alpha<=24))
    correct=np.all(want==nearest,axis=2)
    metrics={"backing_pixels":int(correct.size),"foreground_pixels":int(fg.sum()),
             "nearest_correct":int(correct.sum()),"foreground_correct":int((correct&fg).sum()),
             "fg_nearest_white_wrong":int((fg&whitewrong).sum()),
             "fg_alpha0":int((fg&(alpha==0)).sum()),
             "fg_alpha24":int((fg&(alpha<=24)).sum()),
             "fg_gap_union":int(gaps.sum()),
             "ink_on_white_alpha24":int(((~fg)&(alpha>24)).sum()),
             "rgb_mae":float(abs(arr.astype(np.float32)-want).mean())}
    return metrics,gaps,cols,rows

def repair(rgba,target,g,method,out,seed):
    measure,missing,cols,rows=score("measured",rgba,target,g,out)
    yy,xx=np.nonzero(missing)
    if method=="centroid":
        ids,idx=np.unique(rows[yy].astype(np.int64)*target.shape[1]+cols[xx],return_inverse=True)
        count=np.bincount(idx,minlength=len(ids))
        px=np.bincount(idx,weights=xx.astype(float),minlength=len(ids))/count
        py=np.bincount(idx,weights=yy.astype(float),minlength=len(ids))/count
        sy,sx=np.divmod(ids,target.shape[1])
    else:
        assert method=="pixel"
        px,py,sx,sy=xx,yy,cols[xx],rows[yy]
    result=[]
    for i,(x,y,tx,ty) in enumerate(zip(px,py,sx,sy)):
        rgb=int.from_bytes(bytes(target[int(ty),int(tx)]),"big")
        cx=155+(float(x)+.5)/3
        cy=(float(y)+.5)/3
        result.append(native.stroke(native.segment(cx,cy,.5,0),1,rgb,seed+i))
    return result,int(missing.sum()),measure

def original_paths(proposals,target,g):
    broad,residual=[],[]
    for i,p in enumerate(proposals):
        x,y=map(int,p["points"][0])
        assert 0<=x<target.shape[1] and 0<=y<len(target)
        rgb=int.from_bytes(bytes(target[y,x]),"big")
        allowed=3*g["scale"]*float(p["brush_value"])*1.2
        width=max((n for n,s in enumerate(native.SPANS,1) if s<=allowed),default=1)
        if len(p["points"])==1:
            c=board_point(x,y,g)
            pts=native.segment(c["x"],c["y"],.5,0)
            residual.append(native.stroke(pts,width,rgb,i))
        else:
            broad.append(native.stroke([board_point(px,py,g) for px,py in p["points"]],width,rgb,i))
    return broad+residual,{"method":"full-original-s5-connected-plan",
                           "broad":len(broad),"singletons_replaced":len(residual)}

def roi_paths(target,g):
    paths=[]
    for y,row in enumerate(target):
        x=0
        while x<len(row):
            end=x+1
            while end<len(row) and np.array_equal(row[x],row[end]):
                end+=1
            if np.any(row[x]!=255):
                if end==x+1:
                    c=board_point(x,y,g)
                    pts=native.segment(c["x"],c["y"],.5,0)
                else:
                    pts=[board_point(x,y,g),board_point(end-1,y,g)]
                paths.append(native.stroke(pts,1,int.from_bytes(bytes(row[x]),"big"),len(paths)))
            x=end
    return paths,{"method":"ROI-source-row-runs-no-white-strokes",
                  "broad":len(paths),"singletons_replaced":0}

def main(case):
    root=native.binding.ROOT
    relative=native.binding.pipeline.reference.original.dev.SOURCES[CASES[case]]
    out=Path(os.environ["RUNNER_TEMP"])/("s5-transfer-"+case)
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    roi_only=case=="ezal"
    src=out/"source"
    native.binding.pipeline.run(root,relative,src,
                                palette_only=roi_only,second_lane_audit=False)
    rgba=np.asarray(Image.open(src/"palette-8.png").convert("RGBA"))
    original=np.where((rgba[...,3]==255)[...,None],rgba[...,:3],255).astype(np.uint8)
    original_sha=hashlib.sha256((root/relative).read_bytes()).hexdigest()
    if roi_only:
        x,y,priority=choose_roi(original)
        target=original[y:y+320,x:x+200].copy()
        source_roi={"x":x,"y":y,"width":200,"height":320,
                    "selection":"original-source-detail-density","priority":priority}
    else:
        target=original
        source_roi={"x":0,"y":0,"width":target.shape[1],"height":len(target),
                    "selection":"full-original"}
        assert np.array_equal(np.asarray(Image.open(src/"02-prepared.png")),target)
    Image.fromarray(target,"RGB").save(out/"native-source-target.png")
    g=layout(target.shape[1],len(target))
    if roi_only:
        paths,method=roi_paths(target,g)
        source_plan_sha="ROI_DERIVED_FROM_ORIGINAL_ONLY"
    else:
        with gzip.open(src/"plan.json.gz","rt") as f:
            proposals=json.load(f)["proposals"]
        source_plan_sha=json.loads((src/"results.json").read_text())["plan_sha256"]
        paths,method=original_paths(proposals,target,g)
    assert paths and len(set(p["colorRgb"] for p in paths))<=8
    with gzip.open(out/"baseline-plan.json.gz","wt") as f:
        json.dump(paths,f,separators=(",",":"))
    history=[]
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not native.render(driver,"blank",[])[:,:,3].any()
        control=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        before=native.render(driver,"control-original",control)
        driver.execute_script(native.full_fixture())
        assert np.array_equal(before,native.render(driver,"control-full",control))
        image=native.render(driver,"baseline",paths)
        current,_,_,_=score("baseline",image,target,g,out)
        history.append({"phase":"baseline","strokes":len(paths),"metrics":current})
        print("S5_TRANSFER "+json.dumps({"case":case,**history[-1]},separators=(",",":")),flush=True)
        for n in range(1,5):
            choice="centroid" if n<=2 else "pixel"
            extra,count,previous=repair(image,target,g,choice,out,1000000*n)
            if not extra:
                history.append({"phase":"clear","round":n,"strokes":len(paths),"metrics":previous})
                break
            paths.extend(extra)
            with gzip.open(out/("repair-"+str(n)+"-plan.json.gz"),"wt") as f:
                json.dump(paths,f,separators=(",",":"))
            image=native.render(driver,"feedback-"+str(n),paths)
            current,_,_,_=score("feedback-"+str(n),image,target,g,out)
            history.append({"phase":"feedback","round":n,"method":choice,
                            "detected":count,"added_strokes":len(extra),
                            "strokes":len(paths),"metrics":current})
            print("S5_TRANSFER "+json.dumps({"case":case,**history[-1]},separators=(",",":")),flush=True)
    result={"schema":"ENGINE001_S5_NATIVE_CROSS_ORIGINAL_FEEDBACK_V1",
            "run":os.environ["GITHUB_RUN_ID"],"sha":os.environ["GITHUB_SHA"],
            "original_source":relative,"original_sha256":original_sha,
            "source_size":[original.shape[1],original.shape[0]],
            "selected_region":source_roi,"board_geometry":g,
            "source_plan_sha256":source_plan_sha,"baseline":method,
            "native_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
            "mode":"normal","smooth":False,"research_stroke_limit":"none",
            "roi_only":roi_only,"visual_quality":"PENDING","exact_CHALK":"NOT_RUN",
            "history":history}
    native.binding.write_json(out/"transfer-results.json",result)
    print("S5_TRANSFER_RESULT "+json.dumps(result,separators=(",",":")),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--case",required=True,choices=tuple(CASES))
    main(p.parse_args().case)
