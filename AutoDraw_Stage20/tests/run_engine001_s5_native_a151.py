"""A15.1: per-stroke native spill tolerance, frozen F4-L5 contour."""
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

def runs(row):
    e=np.flatnonzero(np.diff(np.r_[False,row,False].astype(np.int8)))
    return zip(e[::2],e[1::2])

def lanes(safe,residual,pitch,vertical,contact):
    m=safe.T if vertical else safe
    r=residual.T if vertical else residual
    result=[]
    # Residual is native observed, dilation merely selects possible lanes.
    near=ndi.maximum_filter(r,size=(2*contact+1,2*contact+1))
    for y in range(0,m.shape[0],pitch):
        for x,z in runs(m[y]):
            if near[y,x:z].any():
                result.append(((y,x),(y,z-1)) if vertical else ((x,y),(z-1,y)))
    return result

def proposals(target,missing,g,proof,width,extra,stroke,seed):
    # Work in actual backing pixels. Same-color mask includes prior painted contour.
    out=[]
    scale=g["scale"]
    for color in sorted(np.unique(target.reshape(-1,3),axis=0).tolist(),key=lambda c:-sum(v*k for v,k in zip(c,(2126,7152,722)))):
        if color==[255,255,255]:
            continue
        mask=np.all(target==color,axis=2)
        residual=missing&mask
        if not residual.any():
            continue
        labels,n=ndi.label(mask)
        for i,sl in enumerate(ndi.find_objects(labels),1):
            local=labels[sl]==i
            rem=residual[sl]&local
            if not rem.any():
                continue
            options=[]
            for vertical,d in ((False,"horizontal"),(True,"vertical")):
                m=proof["measurements"][d+":"+str(width)]
                lat=m["lateral_max_backing_px"]
                cap=max(0,m["axial_max_backing_px"]-36)
                # Rectangular conservative clearance from measured spans, not coverage.
                cross=max(0,math.ceil(lat/2)+extra)
                along=max(0,math.ceil(cap/2)+extra+1)
                footprint=(2*along+1,2*cross+1) if vertical else (2*cross+1,2*along+1)
                safe=ndi.binary_erosion(local,structure=np.ones(footprint,bool),border_value=0)
                pitch=max(1,math.floor(.8*m["lateral_min_backing_px"]))
                candidates=[]
                # Try all phase offsets, choose maximum residual proximity then fewer lanes.
                for phase in range(pitch):
                    shifted=safe.copy()
                    # lanes() uses zero-origin grid, so shift by slicing in cross direction.
                    if vertical:
                        ll=lanes(shifted[:,phase:],rem[:,phase:],pitch,True,max(cross,along))
                        ll=[((a[0]+phase,a[1]),(b[0]+phase,b[1])) for a,b in ll]
                    else:
                        ll=lanes(shifted[phase:,:],rem[phase:,:],pitch,False,max(cross,along))
                        ll=[((a[0],a[1]+phase),(b[0],b[1]+phase)) for a,b in ll]
                    ll=[(a,b) for a,b in ll if math.dist(a,b)/(3*scale)>5+1e-9]
                    # Score contact using residual proximity only, not claimed coverage.
                    touched=np.zeros(local.shape,bool)
                    for (x,y),(xx,yy) in ll:
                        touched[min(y,yy):max(y,yy)+1,min(x,xx):max(x,xx)+1]=True
                    contact=ndi.maximum_filter(touched,size=2*max(cross,along)+1)&rem
                    candidates.append((int(contact.sum()),-len(ll),ll))
                options.append(max(candidates,key=lambda v:v[:2]))
            chosen=max(options,key=lambda v:v[:2])[2]
            for a,b in chosen:
                pts=[dict(x=155+(x+sl[1].start+.5)/3,y=(y+sl[0].start+.5)/3) for x,y in (a,b)]
                out.append(stroke(pts,width,int.from_bytes(bytes(color),"big"),seed+len(out)))
    return out

def actual(raw,want):
    crop=raw[:,465:915]
    a=crop[:,:,3].astype(np.float32)/255
    rgb=np.rint(crop[:,:,:3].astype(np.float32)*a[:,:,None]+255*(1-a[:,:,None])).astype(np.uint8)
    palette=np.unique(want.reshape(-1,3),axis=0)
    nearest=palette[np.stack([np.square(rgb.astype(np.float32)-c).sum(axis=2) for c in palette],axis=-1).argmin(axis=-1)]
    fg=np.any(want!=255,axis=2)
    correct=fg&(crop[:,:,3]>24)&np.all(nearest==want,axis=2)
    return correct,fg&~correct

def contracts():
    from run_engine001_s5_native_a14_nodot_l5 import contracts as l5
    l5()
    m=np.ones((20,30),bool)
    assert lanes(m,m,3,False,2)
    assert lanes(m,m,3,True,2)
    raw=np.zeros((720,1380,4),np.uint8)
    want=np.zeros((720,450,3),np.uint8)
    good,missing=actual(raw,want)
    assert not good.any() and missing.all()

def main(radius,baseline,source,tolerance):
    import run_engine001_s5_wv_full_native as native
    import run_engine001_s5_originals_native_transfer as transfer
    import engine001_s5_native_brush_overlap as physical
    from run_engine001_s5_native_a14 import bands
    from run_engine001_s5_native_a14_nodot_l5 import length_source
    out=Path(os.environ["RUNNER_TEMP"])/f"s5-a151-illustration-r{radius:02d}-t{tolerance}"
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    report=json.loads((baseline/"a14-nodot-l5-results.json").read_text("utf8"))
    src=json.loads((source/"a14-nodot-results.json").read_text("utf8"))
    assert report["sha"]=="5858e37586a832b91ba40bce0afd6249e9579b1e" and str(report["run"])=="45512562848"
    assert src["sha"]=="3fa893904b87701de47fb50e88b27bfe62996f57" and str(src["run"])=="45465036156"
    assert report["case"]==src["case"]=="illustration" and report["radius_source_px"]==radius and src["radii_source_px"]==[radius]
    g=report["geometry"]
    assert g==src["geometry"]
    assert sha(native.binding.ROOT/src["source"])==src["source_sha256"]
    name=f"r{radius:02d}-f4"
    old=report["results"][name]
    plan=baseline/(name+"-plan.json.gz")
    archived=baseline/(name+".png")
    assert sha(plan)==old["plan_sha256"] and sha(archived)==old["raw_sha256"]
    with gzip.open(plan,"rt",encoding="utf8") as f:paths=json.load(f)
    assert len(paths)==old["strokes"] and all(p["width"]==1 and length_source(p,g["scale"])>5+1e-9 for p in paths)
    target=np.asarray(Image.open(source/"rtv-prepared.png").convert("RGB"))
    band,_,_=bands(target,radius)
    assert np.array_equal(band,np.asarray(Image.open(baseline/(name+"-target.png")).convert("RGB")))
    Image.fromarray(target).save(out/"full-target.png")
    want,_,_=transfer.projected(target,g)
    Image.fromarray(want).save(out/"projected-target.png")
    fg=np.any(want!=255,axis=2)
    history=[]
    def save_plan(label,pp):
        with gzip.open(out/(label+"-plan.json.gz"),"wt",encoding="utf8") as f:json.dump(pp,f,separators=(",",":"))
    def save_stage(label,raw,pp):
        Image.fromarray(raw).save(out/(label+".png"))
        metrics,_,_,_=transfer.score(label,raw,target,g,out)
        _,missing=actual(raw,want)
        Image.fromarray(missing.astype(np.uint8)*255).save(out/(label+"-residual.png"))
        save_plan(label,pp)
        return dict(stage=label,strokes=len(pp),vertices=sum(len(p["points"]) for p in pp),source_length=math.fsum(length_source(p,g["scale"]) for p in pp),metrics=metrics,residual_pixels=int(missing.sum()))
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not native.render(driver,"blank",[])[:,:,3].any()
        control=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        first=native.render(driver,"reference-original",control)
        js=native.full_fixture()
        a=js.index("function renderComplexHoldoutColorProbe(")
        b=js.index("const board = makeTemporalBoard(",a)
        guard=js[a:b]
        anchor=" ||\n          stroke.points.length > 128"
        assert guard.count(anchor)==1
        driver.execute_script(js[:a]+guard.replace(anchor,"")+js[b:])
        assert np.array_equal(first,native.render(driver,"reference-expanded",control))
        proof=physical.native_footprints(driver)
        native.binding.write_json(out/"egret-physical-footprints.json",proof)
        raw=native.render(driver,"stage1-contour",paths)
        assert np.array_equal(raw,np.asarray(Image.open(archived).convert("RGBA")))
        history.append(save_stage("stage1-contour",raw,paths))
        trial_log=[]
        for width in range(10,0,-1):
            good,missing=actual(raw,want)
            accepted=[]
            seen=set()
            # Same original coordinates; no translated or approximate footprints.
            for extra in (0,-max(1, min(proof["measurements"][d+":"+str(width)]["lateral_max_backing_px"] for d in ("horizontal","vertical"))//8)):
                batch=proposals(want,missing,g,proof,width,extra,native.stroke,1000000+width*100000)
                for p in batch:
                    key=(p["colorRgb"],tuple((v["x"],v["y"]) for v in p["points"]))
                    if key in seen:continue
                    seen.add(key)
                    assert len(p["points"])>=2 and length_source(p,g["scale"])>5+1e-9
                    p=dict(p,strokeId=f"a151-{width}-{len(seen)}")
                    # Render using the same native fixture, but avoid writing hundreds of
                    # full-size PNGs: retain the per-stroke audit and packed native alpha crop.
                    response=driver.execute_script(native.binding.native.CMD,[p])
                    label=f"probe-w{width:02d}"
                    solo,meta=native.binding.native.read_webgl_result(response,out,label)
                    assert meta["renderer"]=="real Egret 5.4.1 BoardPane/WebGLRenderer"
                    assert meta["strokeCount"]==1
                    alpha=solo[:,:,3]
                    ink=alpha>0
                    n=int(ink.sum())
                    crop=alpha[:,465:915]
                    rgb=np.array([(p["colorRgb"]>>16)&255,(p["colorRgb"]>>8)&255,p["colorRgb"]&255],np.uint8)
                    own=np.all(want==rgb,axis=2)
                    foreign=n-int(((crop>0)&own).sum())
                    gain=int(((crop>24)&own&missing).sum())
                    ok=n>0 and foreign*100<=tolerance*n and gain>0
                    trial_log.append(dict(width=width,extra=extra,stroke=p,ink_pixels=n,foreign_pixels=foreign,residual_contact=gain,accepted=ok))
                    if ok:accepted.append(p)
            if accepted:
                paths=paths+accepted
                new=native.render(driver,f"accepted-w{width:02d}",paths)
                new_good,new_missing=actual(new,want)
                delta=dict(lost_correct=int((good&~new_good).sum()),gained_correct=int((missing&new_good).sum()),
                           new_outside=int(((new[:,465:915,3]>0)&(raw[:,465:915,3]==0)&~fg).sum()))
                raw=new
            else:delta=dict(lost_correct=0,gained_correct=0,new_outside=0)
            save_plan(f"accepted-w{width:02d}",accepted)
            history.append(dict(width=width,accepted=bool(accepted),added_strokes=len(accepted),**delta,**save_stage(f"after-w{width:02d}",raw,paths)))
            if width in (4,1):
                history.append(save_stage("stage2-big" if width==4 else "stage3-small",raw,paths))
            native.binding.write_json(out/"per-stroke-audit.json",trial_log)
            print("A151 width",width,"accepted",len(accepted),"tested",len(seen),flush=True)
        comparison=Image.new("RGB",(1800,720),"white")
        for i,label in enumerate(("projected-target","stage1-contour-crop","stage2-big-crop","stage3-small-crop")):
            comparison.paste(Image.open(out/(label+".png")).convert("RGB"),(450*i,0))
        comparison.save(out/"three-stage-comparison.png")
    native.binding.write_json(out/"a151-results.json",dict(schema="ENGINE001_S5_A151_V1",tolerance_percent=tolerance,run=os.environ["GITHUB_RUN_ID"],sha=os.environ["GITHUB_SHA"],radius=radius,case="illustration",baseline_sha=report["sha"],history=history,trials=trial_log,exact_CHALK="NOT_RUN",human_visual_review="PENDING"))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--contracts",action="store_true")
    p.add_argument("--radius",type=int,choices=(1,2))
    p.add_argument("--baseline",type=Path)
    p.add_argument("--source",type=Path)
    p.add_argument("--tolerance",type=int,choices=(10,20))
    a=p.parse_args()
    if a.contracts:contracts()
    else:main(a.radius,a.baseline,a.source,a.tolerance)
