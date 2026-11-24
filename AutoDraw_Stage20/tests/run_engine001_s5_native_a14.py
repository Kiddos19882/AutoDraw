"""A14: original P2 overlap painter on RTV source contour bands only."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image

RADII=(5,10)
NARROW_RADII=(1,2,3)

def bands(rgb,radius):
    if rgb.ndim!=3 or rgb.shape[2]!=3 or rgb.dtype!=np.uint8 or radius not in (*RADII,*NARROW_RADII):
        raise ValueError("invalid band input")
    fg=np.any(rgb!=255,axis=2)
    edge=np.zeros(fg.shape,bool)
    horizontal=np.any(rgb[:,1:]!=rgb[:,:-1],axis=2)
    vertical=np.any(rgb[1:]!=rgb[:-1],axis=2)
    edge[:,1:] |= horizontal
    edge[:,:-1] |= horizontal
    edge[1:] |= vertical
    edge[:-1] |= vertical
    edge[0] |= fg[0]
    edge[-1] |= fg[-1]
    edge[:,0] |= fg[:,0]
    edge[:,-1] |= fg[:,-1]
    mask=fg & (distance_transform_edt(~edge)<=radius) if edge.any() else np.zeros_like(fg)
    return np.where(mask[...,None],rgb,255).astype(np.uint8),mask,edge

def contracts():
    white=np.full((40,50,3),255,np.uint8)
    assert not bands(white,5)[1].any()
    rgb=white.copy()
    rgb[2:38,2:48]=[55,55,55]
    rgb[2:38,25:48]=[120,120,120]
    original=rgb.copy()
    a,m,e=bands(rgb,5)
    c,n,_=bands(rgb,10)
    assert e[20,24] and e[20,25] and e[2,15]
    assert m[20,19] and not m[20,18] and n[20,18]
    assert np.all(~m|n) and n.sum()>m.sum()
    assert np.array_equal(a[m],rgb[m]) and np.all(a[~m]==255)
    assert np.array_equal(rgb,original)
    solid=np.zeros((40,40,3),np.uint8)
    assert bands(solid,5)[1][0,20] and not bands(solid,5)[1][20,20]
    previous=np.zeros(rgb.shape[:2],bool)
    for radius in NARROW_RADII:
        narrow,mask,edge=bands(rgb,radius)
        assert mask[20,24-radius] and not mask[20,23-radius]
        assert mask[20,25+radius] and not mask[20,26+radius]
        assert np.all(~previous|mask) and mask.sum()>previous.sum()
        assert np.array_equal(narrow[mask],rgb[mask]) and np.all(narrow[~mask]==255)
        assert np.array_equal(rgb,original)
        previous=mask
    assert np.all(~previous|m)
    print("A14 source band contracts PASS (1/2/3 and 5/10)")

def main(case,narrow=False):
    import engine001_s5_native_brush_overlap as physical
    import engine001_s5_zone_methods as methods
    import run_engine001_s5_native_transfer_p2 as p2
    import run_engine001_s5_originals_native_transfer as transfer
    import run_engine001_s5_wv_full_native as native
    root=native.binding.ROOT
    rel,blob=("testImages/wV6VeZI9S1Y.png","d3cd95b846f036a3f8acecf75d2a237e46dcf13a") if case=="wv" else p2.CASE[case]
    assert p2.git_blob((root/rel).read_bytes())==blob
    for module,expected in ((physical,"a268ee57aa4eeebe1c17927495cb8d8905d0e38b"),(methods,"f482f99ab80654f8bd36a61bd999b42bebf0d19f")):
        assert p2.git_blob(Path(module.__file__).read_bytes())==expected
    out=Path(os.environ["RUNNER_TEMP"])/(("s5-a14-narrow-" if narrow else "s5-a14-")+case)
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    src=out/"source"
    native.binding.pipeline.run(root,Path(rel),src,palette_only=True)
    original=np.asarray(Image.open(src/"01-original.png").convert("RGBA"))
    rgba=np.asarray(Image.open(src/"palette-8.png").convert("RGBA"))
    target=np.where((rgba[:,:,3]==255)[:,:,None],rgba[:,:,:3],255).astype(np.uint8)
    rtv,before,after,protected,report,ledger=methods.run_variant(original,target,"rtv")
    assert report["neutral_to_chromatic"]==report["chromatic_to_neutral"]==0
    Image.fromarray(rtv).save(out/"rtv-prepared.png")
    np.savez_compressed(out/"rtv-zones.npz",before=before,after=after,protected=protected)
    native.binding.write_json(out/"rtv-report.json",report)
    native.binding.write_json(out/"rtv-ledger.json",ledger)
    geom=transfer.layout(target.shape[1],target.shape[0])
    results={}
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not native.render(driver,"blank",[])[:,:,3].any()
        control=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        first=native.render(driver,"reference-original",control)
        driver.execute_script(native.full_fixture())
        assert np.array_equal(first,native.render(driver,"reference-expanded",control))
        proof=physical.native_footprints(driver)
        native.binding.write_json(out/"egret-physical-footprints.json",proof)
        for radius in (NARROW_RADII if narrow else RADII):
            name=f"p2-rtv-r{radius:02d}"
            band,mask,edge=bands(rtv,radius)
            Image.fromarray(edge.astype(np.uint8)*255).save(out/"contour.png")
            Image.fromarray(mask.astype(np.uint8)*255).save(out/(name+"-mask.png"))
            Image.fromarray(band).save(out/(name+"-target.png"))
            paths,params=physical.plan_same_color_overlap(band,geom,proof)
            assert all(p["width"]==1 and p["colorRgb"]!=0xffffff for p in paths)
            with gzip.open(out/(name+"-plan.json.gz"),"wt",encoding="utf8") as f:
                json.dump(paths,f,separators=(",",":"))
            raw=native.render(driver,name,paths)
            metrics,_,_,_=transfer.score(name,raw,band,geom,out)
            projected,_,_=transfer.projected(band,geom)
            allowed=np.any(projected!=255,axis=2)
            alpha=raw[:,465:915,3]
            audit={}
            for threshold in (0,24,128):
                ink=alpha>threshold
                audit[str(threshold)]=dict(within=int((ink&allowed).sum()),outside_band=int((ink&~allowed).sum()),outside_crop=int((raw[:,:,3]>threshold).sum()-ink.sum()))
            meta=json.loads((out/(name+".json")).read_text("utf8"))
            results[name]=dict(radius_source_px=radius,source_band_pixels=int(mask.sum()),strokes=len(paths),planner=params,metrics=metrics,alpha_audit=audit,simulation_counter=meta.get("paintCounter"),raw_sha256=sha(out/(name+".png")),plan_sha256=sha(out/(name+"-plan.json.gz")))
            p2.make_comparison(out,Image.fromarray(original),Image.fromarray(band),Image.open(out/(name+"-crop.png")))
            (out/"actual-egret-three-way.png").rename(out/(name+"-comparison.png"))
    native.binding.write_json(out/"a14-results.json",dict(schema="ENGINE001_S5_A14_V1",radii_source_px=list(NARROW_RADII if narrow else RADII),case=case,run=os.environ["GITHUB_RUN_ID"],sha=os.environ["GITHUB_SHA"],source=rel,source_sha256=sha(root/rel),geometry=geom,brush_widths=[1],smooth=False,mode="normal",interior_fill=False,strict_spill=False,results=results,exact_CHALK="NOT_RUN",human_visual_review="PENDING"))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=("home","illustration","second-png","wv"))
    parser.add_argument("--contracts",action="store_true")
    parser.add_argument("--narrow",action="store_true")
    args=parser.parse_args()
    if args.contracts:
        contracts()
    else:
        main(args.case,args.narrow)
