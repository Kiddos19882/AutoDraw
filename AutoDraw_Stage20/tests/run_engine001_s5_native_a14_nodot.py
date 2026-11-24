"""Illustration F4/F6: skip isolated singleton walks, native Egret replay."""
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
    import engine001_s5_a14_free_angle as free
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
    out=Path(os.environ["RUNNER_TEMP"])/(f"s5-a14-nodot-{case}-r{radius:02d}")
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
        js=native.full_fixture()
        first_guard=js.index("function renderComplexHoldoutColorProbe(")
        last_guard=js.index("const board = makeTemporalBoard(",first_guard)
        guard=js[first_guard:last_guard]
        anchor=" ||\n          stroke.points.length > 128"
        assert guard.count(anchor)==1
        js=js[:first_guard]+guard.replace(anchor,"")+js[last_guard:]
        driver.execute_script(js)
        assert np.array_equal(first,native.render(driver,"reference-expanded",control))
        # Native proof: one continuous stroke with 512 distinct adjacent points.
        probe=[]
        for i in range(512):
            y,x=divmod(i,64)
            probe.append(dict(x=180+(x if y%2==0 else 63-x),y=40+y))
        probe_rgba=native.render(driver,"unlimited-512-vertex-probe",[native.stroke(probe,1,0,0)])
        probe_meta=json.loads((out/"unlimited-512-vertex-probe.json").read_text("utf8"))
        assert probe_meta["strokeCount"]==1 and probe_meta["paintCounter"]["used"]==512
        assert probe_rgba[:,:,3].any()
        proof=physical.native_footprints(driver)
        native.binding.write_json(out/"egret-physical-footprints.json",proof)
        for variant in ('f4','f6'):
            name=f"r{radius:02d}-{variant}"
            band,mask,edge=bands(rtv,radius)
            Image.fromarray(edge.astype(np.uint8)*255).save(out/"contour.png")
            Image.fromarray(mask.astype(np.uint8)*255).save(out/(name+"-mask.png"))
            Image.fromarray(band).save(out/(name+"-target.png"))
            dots=set()
            def mark_segment(x,y,dx,dy):
                pts=native.segment(x,y,dx,dy)
                dots.add(id(pts))
                return pts
            all_paths=free.proposals(band,geom,proof,variant,native.stroke,mark_segment)
            # stroke() retains the exact points list. Tag only singleton conversions.
            control_paths=all_paths
            if variant=="f6":
                reference=native.render(driver,name+"-control-before-prune",control_paths)
                control_paths,trials=free.native_prune(control_paths,reference,
                    lambda n,candidate:native.render(driver,name+f"-control-trial-{n:02d}",candidate))
                assert np.array_equal(native.render(driver,name+"-control-check",control_paths),reference)
            control_raw=native.render(driver,name+"-control",control_paths)
            control_metrics,_,_,_=transfer.score(name+"-control",control_raw,band,geom,out)
            paths=[p for p in control_paths if id(p["points"]) not in dots]
            skipped=[p for p in control_paths if id(p["points"]) in dots]
            assert len(paths)+len(skipped)==len(control_paths)
            assert all(len(p["points"])==2 for p in skipped)
            with gzip.open(out/(name+"-control-plan.json.gz"),"wt",encoding="utf8") as f:
                json.dump(control_paths,f,separators=(",",":"))
            with gzip.open(out/(name+"-skipped-dots.json.gz"),"wt",encoding="utf8") as f:
                json.dump(skipped,f,separators=(",",":"))
            params=dict(variant=variant,skip_singleton_walks=True,
                skipped_dots=len(skipped),control_strokes=len(control_paths),
                control_vertices=sum(len(p["points"]) for p in control_paths),
                control_metrics=control_metrics)
            assert paths and all(len(p["points"])>=2 for p in paths)
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
            results[name]=dict(radius_source_px=radius,source_band_pixels=int(mask.sum()),strokes=len(paths),max_vertices_per_stroke=max(len(p["points"]) for p in paths),vertices=sum(len(p['points']) for p in paths),logical_length=sum(float(np.hypot(q['x']-p['x'],q['y']-p['y'])) for s in paths for p,q in zip(s['points'],s['points'][1:])),planner=params,metrics=metrics,alpha_audit=audit,simulation_counter=meta.get("paintCounter"),raw_sha256=sha(out/(name+".png")),plan_sha256=sha(out/(name+"-plan.json.gz")))
            p2.make_comparison(out,Image.fromarray(original),Image.fromarray(band),Image.open(out/(name+"-crop.png")))
            (out/"actual-egret-three-way.png").rename(out/(name+"-comparison.png"))
    native.binding.write_json(out/"a14-nodot-results.json",dict(schema="ENGINE001_S5_A14_ILLUSTRATION_NO_DOT_V1",per_stroke_vertex_cap=None,radii_source_px=[radius],case=case,run=os.environ["GITHUB_RUN_ID"],sha=os.environ["GITHUB_SHA"],source=rel,source_sha256=sha(root/rel),geometry=geom,brush_widths=[1],smooth=False,mode="normal",interior_fill=False,strict_spill=False,results=results,exact_CHALK="NOT_RUN",human_visual_review="PENDING"))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=("illustration",))
    parser.add_argument("--contracts",action="store_true")
    parser.add_argument("--radius",type=int,choices=(1,2),required=True)
    args=parser.parse_args()
    if args.contracts:
        contracts()
    else:
        main(args.case,args.radius)
