"""A27: frozen visual A26/A17 R3 W1, A15.1 broad fill and paired small fill: unchanged lanes vs same-color same-width A17 R3 joining. Native spill <=10%, no contour mutation. Rejected joins fall back to original lanes. No production promotion."""
from run_engine001_s5_native_a24 import proposals, actual, contracts as fill_contracts
from run_engine001_s5_native_a17 import join
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import numpy as np
from PIL import Image

def merge_candidates(paths,scale):
    # A17 nearest endpoint algorithm, independently for each color and width.
    groups={}
    for p in paths:groups.setdefault((p["colorRgb"],p["width"]),[]).append(p)
    result=[]
    for group in groups.values():
        # Track source strokes by vertex sequence (including reversed orientation).
        for p in join(group,scale,3):
            pts=p["points"]
            members=[]
            for q in group:
                a=q["points"]
                if any(pts[i:i+len(a)]==a or pts[i:i+len(a)]==a[::-1] for i in range(len(pts)-len(a)+1)):
                    members.append(q)
            assert members
            result.append((p,members))
    assert {p["strokeId"] for _,mm in result for p in mm}=={p["strokeId"] for p in paths}
    return result

def contracts():
    fill_contracts()
    def p(i,a,b,c=0,w=1):return dict(strokeId=str(i),points=[dict(x=a,y=0),dict(x=b,y=0)],width=w,colorRgb=c)
    pp=[p(1,0,6),p(2,8,14),p(3,14,20,1),p(4,14,20,0,2)]
    rr=merge_candidates(pp,1)
    assert len(rr)==3 and len(rr[0][1])==2
    assert len(merge_candidates([p(1,0,6),p(2,10,16)],1))==2

def main(radius,baseline,source,tolerance,contour):
    import run_engine001_s5_wv_full_native as native
    import run_engine001_s5_originals_native_transfer as transfer
    import engine001_s5_native_brush_overlap as physical
    from run_engine001_s5_native_a14 import bands
    from run_engine001_s5_native_a14_nodot_l5 import length_source
    out=Path(os.environ["RUNNER_TEMP"])/f"s5-a27-{contour}"
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    report=json.loads((baseline/"a26-results.json").read_text("utf8"))
    src=json.loads((source/"a14-nodot-results.json").read_text("utf8"))
    assert report["sha"]=="e59dc1ed745c06eb62feca6860d13d757785b11c" and str(report["run"])=="45692663252"
    assert report["stage"]=="17" and report["source_radius_px"]==radius==2 and report["smoothing"] is False
    assert src["sha"]=="3fa893904b87701de47fb50e88b27bfe62996f57" and str(src["run"])=="45465036156"
    assert src["case"]=="illustration" and src["radii_source_px"]==[2]
    g=report["geometry"]
    assert g==src["geometry"]
    assert sha(native.binding.ROOT/src["source"])==src["source_sha256"]==report["source_sha256"]
    name="a17-r3-w1"
    old=report["combined"][name]
    plan=baseline/(name+"-plan.json.gz")
    archived=baseline/(name+".png")
    assert sha(plan)==old["plan_sha256"] and sha(archived)==old["rgba_sha256"]
    with gzip.open(plan,"rt",encoding="utf8") as f:paths=json.load(f)
    assert len(paths)==old["strokes"]==1164 and sum(len(p["points"]) for p in paths)==old["vertices"]==66416
    assert all(p["width"]==1 and length_source(p,g["scale"])>5 for p in paths)
    target=np.asarray(Image.open(source/"rtv-prepared.png").convert("RGB"))
    assert np.array_equal(target,np.asarray(Image.open(baseline/"rtv04-prepared.png").convert("RGB")))
    band,_,_=bands(target,radius)
    assert np.array_equal(band,np.asarray(Image.open(baseline/"all-colors-original-contour-band.png").convert("RGB")))
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
                    p=dict(p,strokeId=f"icon-{1000000+width*100000+len(seen)}")
                    assert p["strokeId"] not in {q["strokeId"] for q in paths+accepted}
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
            # Only after ordinary per-lane native acceptance, join W3/W2/W1.
            # Same nearest endpoint rule as A17, preserve original vertices.
            original_count=len(accepted)
            if contour=="joined" and width<=3 and accepted:
                merged=[]
                used=set()
                for candidate,members in merge_candidates(accepted,g["scale"]):
                    fresh=[q for q in members if q["strokeId"] not in used]
                    if not fresh:continue
                    # Ambiguous duplicate/subsequence membership must fail closed.
                    if len(fresh)!=len(members) or len(members)==1:
                        merged.extend(fresh)
                        used.update(q["strokeId"] for q in fresh)
                        continue
                    response=driver.execute_script(native.binding.native.CMD,[candidate])
                    solo,meta=native.binding.native.read_webgl_result(response,out,f"join-w{width:02d}")
                    assert meta["renderer"]=="real Egret 5.4.1 BoardPane/WebGLRenderer" and meta["strokeCount"]==1
                    alpha=solo[:,:,3]
                    n=int((alpha>0).sum())
                    crop=alpha[:,465:915]
                    rgb=np.array([(candidate["colorRgb"]>>16)&255,(candidate["colorRgb"]>>8)&255,candidate["colorRgb"]&255],np.uint8)
                    own=np.all(want==rgb,axis=2)
                    foreign=n-int(((crop>0)&own).sum())
                    gain=int(((crop>24)&own&missing).sum())
                    ok=n>0 and foreign*100<=tolerance*n and gain>0
                    # Require no loss of own-color residual support from the original lanes.
                    if ok:
                        union=np.zeros_like(crop,bool)
                        for q in members:
                            rr=driver.execute_script(native.binding.native.CMD,[q])
                            ss,mm=native.binding.native.read_webgl_result(rr,out,"join-control")
                            assert mm["strokeCount"]==1
                            union|=ss[:,465:915,3]>24
                        lost=int((union&own&missing&~(crop>24)).sum())
                        ok=lost==0
                    else:lost=None
                    trial_log.append(dict(kind="join",width=width,stroke=candidate,member_ids=[q["strokeId"] for q in members],ink_pixels=n,foreign_pixels=foreign,residual_contact=gain,lost_residual=lost,accepted=ok))
                    merged.extend([candidate] if ok else members)
                    used.update(q["strokeId"] for q in members)
                assert used=={q["strokeId"] for q in accepted}
                accepted=[dict(p,strokeId=f"icon-{3000000+width*100000+i}") for i,p in enumerate(merged)]
            print("A27 joining",width,"before",original_count,"after",len(accepted),flush=True)
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
            print("A27 width",width,"accepted",len(accepted),"tested",len(seen),flush=True)
        comparison=Image.new("RGB",(1800,720),"white")
        for i,label in enumerate(("projected-target","stage1-contour-crop","stage2-big-crop","stage3-small-crop")):
            comparison.paste(Image.open(out/(label+".png")).convert("RGB"),(450*i,0))
        comparison.save(out/"three-stage-comparison.png")
    native.binding.write_json(out/"a27-results.json",dict(schema="ENGINE001_S5_A27_V1",contour=contour,contour_run=report["run"],contour_plan_sha256=old["plan_sha256"],contour_rgba_sha256=old["rgba_sha256"],tolerance_percent=tolerance,run=os.environ["GITHUB_RUN_ID"],sha=os.environ["GITHUB_SHA"],radius=radius,case="illustration",baseline_sha=report["sha"],history=history,trials=trial_log,exact_CHALK="NOT_RUN",human_visual_review="PENDING"))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--contracts",action="store_true")
    p.add_argument("--radius",type=int,choices=(1,2))
    p.add_argument("--baseline",type=Path)
    p.add_argument("--source",type=Path)
    p.add_argument("--tolerance",type=int,choices=(10,20))
    p.add_argument("--contour",choices=("control","joined"))
    a=p.parse_args()
    if a.contracts:contracts()
    else:
        if a.radius!=2 or a.tolerance!=10 or a.contour is None:p.error("A27 requires radius 2, tolerance 10 and contour")
        main(a.radius,a.baseline,a.source,a.tolerance,a.contour)
