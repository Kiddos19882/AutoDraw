"""Frozen Illustration NoDot replay with whole-stroke source arc length >5."""
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import numpy as np
from PIL import Image
BASE_SHA="3fa893904b87701de47fb50e88b27bfe62996f57"
BASE_RUN="45465036156"
LIMIT=5.0
EPS=1e-9

def length_source(stroke,scale):
    pts=stroke["points"]
    return math.fsum(math.hypot(b["x"]-a["x"],b["y"]-a["y"]) for a,b in zip(pts,pts[1:]))/scale

def split(paths,scale):
    assert math.isfinite(scale) and scale>0
    keep,drop=[],[]
    for p in paths:
        (drop if length_source(p,scale)<=LIMIT+EPS else keep).append(p)
    return keep,drop

def contracts():
    def p(*coords):
        return {"points":[dict(x=x,y=y) for x,y in coords]}
    paths=[p((0,0),(3,4)),p((0,0),(5.00001,0)),p((0,0),(3,0),(3,3)),p((0,0),(0,0)),p((0,0),(2,0))]
    keep,drop=split(paths,1)
    assert keep==paths[1:3] and drop==[paths[0],paths[3],paths[4]]
    assert split([p((0,0),(2.5,0))],.5)[0]==[]
    print("NoDot-L5 inclusive cutoff and arc-length contracts PASS")

def main(radius,baseline):
    import run_engine001_s5_wv_full_native as native
    import run_engine001_s5_originals_native_transfer as transfer
    out=Path(os.environ["RUNNER_TEMP"])/f"s5-a14-nodot-l5-illustration-r{radius:02d}"
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()
    report=json.loads((baseline/"a14-nodot-results.json").read_text("utf8"))
    assert report["sha"]==BASE_SHA and str(report["run"])==BASE_RUN
    assert report["case"]=="illustration" and report["radii_source_px"]==[radius]
    assert report["smooth"] is False and report["brush_widths"]==[1]
    g=report["geometry"]
    assert sha(native.binding.ROOT/report["source"])==report["source_sha256"]
    results={}
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not native.render(driver,"blank",[])[:,:,3].any()
        probe=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        first=native.render(driver,"reference-original",probe)
        js=native.full_fixture()
        first_guard=js.index("function renderComplexHoldoutColorProbe(")
        last_guard=js.index("const board = makeTemporalBoard(",first_guard)
        guard=js[first_guard:last_guard]
        anchor=" ||\n          stroke.points.length > 128"
        assert guard.count(anchor)==1
        driver.execute_script(js[:first_guard]+guard.replace(anchor,"")+js[last_guard:])
        assert np.array_equal(first,native.render(driver,"reference-expanded",probe))
        for variant in ("f4","f6"):
            name=f"r{radius:02d}-{variant}"
            old=report["results"][name]
            plan=baseline/(name+"-plan.json.gz")
            archived=baseline/(name+".png")
            assert sha(plan)==old["plan_sha256"] and sha(archived)==old["raw_sha256"]
            with gzip.open(plan,"rt",encoding="utf8") as f:
                paths=json.load(f)
            assert len(paths)==old["strokes"]
            assert sum(len(p["points"]) for p in paths)==old["vertices"]
            assert all(p["width"]==1 and p["colorRgb"]!=0xffffff for p in paths)
            assert len({p["strokeId"] for p in paths})==len(paths)
            with gzip.open(baseline/(name+"-skipped-dots.json.gz"),"rt",encoding="utf8") as f:
                dots=json.load(f)
            assert not ({p["strokeId"] for p in paths}&{p["strokeId"] for p in dots})
            band=np.asarray(Image.open(baseline/(name+"-target.png")).convert("RGB"))
            assert band.shape[:2]==(g["height"],g["width"])
            Image.fromarray(band).save(out/(name+"-target.png"))
            control=native.render(driver,name+"-nodot-control",paths)
            old_raw=np.asarray(Image.open(archived).convert("RGBA"))
            assert old_raw.shape==control.shape
            control_diff=int(np.any(old_raw!=control,axis=2).sum())
            cm,_,_,_=transfer.score(name+"-nodot-control",control,band,g,out)
            keep,drop=split(paths,g["scale"])
            assert keep and len(keep)+len(drop)==len(paths)
            assert all(length_source(p,g["scale"])>LIMIT+EPS for p in keep)
            for suffix,data in (("-plan.json.gz",keep),("-omitted-short.json.gz",drop)):
                with gzip.open(out/(name+suffix),"wt",encoding="utf8") as f:
                    json.dump(data,f,separators=(",",":"))
            raw=native.render(driver,name,keep)
            metrics,_,_,_=transfer.score(name,raw,band,g,out)
            comparison=Image.new("RGB",(900,720),"white")
            comparison.paste(Image.open(out/(name+"-nodot-control-crop.png")),(0,0))
            comparison.paste(Image.open(out/(name+"-crop.png")),(450,0))
            comparison.save(out/(name+"-comparison.png"))
            results[name]=dict(control_strokes=len(paths),strokes=len(keep),
                omitted_short=len(drop),previously_omitted_dots=len(dots),
                control_vertices=old["vertices"],vertices=sum(len(p["points"]) for p in keep),
                min_source_length=min(length_source(p,g["scale"]) for p in keep),
                max_omitted_source_length=max((length_source(p,g["scale"]) for p in drop),default=None),
                control_source_length=math.fsum(length_source(p,g["scale"]) for p in paths),
                source_length=math.fsum(length_source(p,g["scale"]) for p in keep),
                archived_control_different_pixels=control_diff,control_metrics=cm,metrics=metrics,
                changed_pixels=int(np.any(raw!=control,axis=2).sum()),
                baseline_plan_sha256=sha(plan),raw_sha256=sha(out/(name+".png")),
                plan_sha256=sha(out/(name+"-plan.json.gz")))
            print("NODOT_L5 "+json.dumps({name:results[name]}),flush=True)
    native.binding.write_json(out/"a14-nodot-l5-results.json",dict(schema="ENGINE001_S5_A14_NODOT_L5_V1",
        baseline_sha=BASE_SHA,baseline_run=BASE_RUN,run=os.environ["GITHUB_RUN_ID"],sha=os.environ["GITHUB_SHA"],
        radius_source_px=radius,case="illustration",geometry=g,source_length_cutoff=LIMIT,
        brush_widths=[1],smooth=False,results=results,exact_CHALK="NOT_RUN",human_visual_review="PENDING"))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--contracts",action="store_true")
    p.add_argument("--radius",type=int,choices=(1,2))
    p.add_argument("--baseline",type=Path)
    a=p.parse_args()
    if a.contracts:
        contracts()
    else:
        main(a.radius,a.baseline)
