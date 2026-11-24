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

from run_engine001_s5_native_a14 import bands, contracts

def main(case,radius):
    import engine001_s5_a14_routes as routes
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
    out=Path(os.environ["RUNNER_TEMP"])/(f"s5-a14-routes-{case}-r{radius:02d}")
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
        for variant in routes.VARIANTS:
            name=f"r{radius:02d}-{variant}"
            band,mask,edge=bands(rtv,radius)
            Image.fromarray(edge.astype(np.uint8)*255).save(out/"contour.png")
            Image.fromarray(mask.astype(np.uint8)*255).save(out/(name+"-mask.png"))
            Image.fromarray(band).save(out/(name+"-target.png"))
            if variant=="a":
                paths,params=physical.plan_same_color_overlap(band,geom,proof)
            else:
                paths=routes.plan(band,geom,proof,variant,native.stroke,native.segment)
                params=dict(variant=variant,source_center_model=True)
            assert paths and all(2<=len(p["points"])<=128 for p in paths)
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
            results[name]=dict(radius_source_px=radius,source_band_pixels=int(mask.sum()),strokes=len(paths),vertices=sum(len(p['points']) for p in paths),logical_length=sum(float(np.hypot(q['x']-p['x'],q['y']-p['y'])) for s in paths for p,q in zip(s['points'],s['points'][1:])),planner=params,metrics=metrics,alpha_audit=audit,simulation_counter=meta.get("paintCounter"),raw_sha256=sha(out/(name+".png")),plan_sha256=sha(out/(name+"-plan.json.gz")))
            p2.make_comparison(out,Image.fromarray(original),Image.fromarray(band),Image.open(out/(name+"-crop.png")))
            (out/"actual-egret-three-way.png").rename(out/(name+"-comparison.png"))
    native.binding.write_json(out/"a14-routes-results.json",dict(schema="ENGINE001_S5_A14_ROUTES_V1",radii_source_px=[radius],case=case,run=os.environ["GITHUB_RUN_ID"],sha=os.environ["GITHUB_SHA"],source=rel,source_sha256=sha(root/rel),geometry=geom,brush_widths=[1],smooth=False,mode="normal",interior_fill=False,strict_spill=False,results=results,exact_CHALK="NOT_RUN",human_visual_review="PENDING"))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=("home","illustration","second-png","wv"))
    parser.add_argument("--contracts",action="store_true")
    parser.add_argument("--radius",type=int,choices=(1,2),required=True)
    args=parser.parse_args()
    if args.contracts:
        contracts()
    else:
        main(args.case,args.radius)
