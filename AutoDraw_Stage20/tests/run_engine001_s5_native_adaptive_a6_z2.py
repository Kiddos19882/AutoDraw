"""Z2 independent and joint zoning methods -> fresh A5 -> actual Egret."""
import argparse
import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import engine001_s5_zone_merge as z
import engine001_s5_zone_methods as methods
import run_engine001_s5_native_adaptive_a1 as a
import run_engine001_s5_native_adaptive_a2 as v
import run_engine001_s5_native_adaptive_a3 as p
import run_engine001_s5_native_adaptive_a4 as q
import run_engine001_s5_native_adaptive_a5 as f

A5_BLOB = "08bbd613e4ec1e827d18c189ab42578d7309f617"
A5_COUNTS = {"home":1376, "illustration":22000, "second-png":11432}
ZONE_COUNTS = {"home":1, "illustration":3134, "second-png":2584}


def panel(out, original, target, maps):
    from run_engine001_s5_native_transfer_p2 import alpha_onto_white
    cells=[("ORIGINAL",alpha_onto_white(Image.fromarray(original))),
           ("A5 SOURCE",Image.fromarray(target))]
    for key, img in maps.items():
        cells.append((key.upper()+" SOURCE",Image.fromarray(img)))
    for key in ("a5", *maps):
        cells.append((key.upper()+" EGRET",Image.open(out/(key+"-crop.png"))))
    w,h=450,760
    atlas=Image.new("RGB",(w*len(cells),h),(245,245,245))
    draw=ImageDraw.Draw(atlas)
    for i,(title,img) in enumerate(cells):
        img=img.convert("RGB")
        img.thumbnail((w,h-40),Image.Resampling.NEAREST)
        atlas.paste(img,(i*w+(w-img.width)//2,30+(h-40-img.height)//2))
        draw.text((i*w+10,8),title,fill=(0,0,0))
    atlas.save(out/"comparison.png")


def main(case,batch):
    import engine001_s5_native_brush_overlap as physical
    import run_engine001_s5_native_transfer_p2 as p2
    import run_engine001_s5_originals_native_transfer as transfer
    import run_engine001_s5_wv_full_native as native
    import engine001_bpred_s4r1_rag3_hierarchy as rag
    import engine001_bpred_s4r1_dg1_source_detail_atoms as dg
    root=native.binding.ROOT
    rel,expected=p2.CASE[case]
    for module,blob in ((physical,a.PLANNER_BLOB),(a,v.A1_BLOB),(v,p.A2_BLOB),
            (p,q.A3_BLOB),(q,f.A4_BLOB),(f,A5_BLOB),
            (rag,"f600e3580f1a3d09bd96f5688e5212fd0b178039"),(dg,"840b3b24cee38f044600dc9a9e18af617a263b7f")):
        a.require(p2.git_blob(Path(module.__file__).read_bytes())==blob,"reference code drift: "+module.__name__)
    a.require(p2.git_blob((root/rel).read_bytes())==expected,"source drift")
    out=Path(os.environ["RUNNER_TEMP"])/("s5-adaptive-a6-z2-"+case+"-"+batch)
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    source=out/"source"
    native.binding.pipeline.run(root,Path(rel),source,palette_only=True)
    rgba=np.asarray(Image.open(source/"palette-8.png").convert("RGBA"))
    original=np.asarray(Image.open(source/"01-original.png").convert("RGBA"))
    target=np.where((rgba[:,:,3]==255)[:,:,None],rgba[:,:,:3],255).astype(np.uint8)
    a.require(original.shape==rgba.shape,"source dimensions differ")
    geom=transfer.layout(target.shape[1],target.shape[0])
    want,_,_=transfer.projected(target,geom)
    source_rgb=np.where((original[:,:,3]==255)[:,:,None],original[:,:,:3],255).astype(np.uint8)
    original_want,_,_=transfer.projected(source_rgb,geom)
    Image.fromarray(target,"RGB").save(out/"prepared.png")
    Image.fromarray(want,"RGB").save(out/"projected-target.png")
    before,ids=z.region_counts(target)
    a.require(before["zones"]==ZONE_COUNTS[case],"A5 zone count drift")
    maps={}
    zone_reports={}
    failures={}
    cn=None
    cn_meta=None
    if any("cn" in methods.FLAGS[key] for key in methods.BATCHES[batch]):
        try:
            cn,cn_meta=methods.load_cn()
            np.save(out/"cn-probabilities.npy",cn)
            a.write_json(out/"cn-provenance.json",cn_meta)
        except Exception as exc:
            cn_meta=dict(status="BLOCKED",error=str(exc))
            a.write_json(out/"cn-provenance.json",cn_meta)
    palette,provenance=native.binding.pipeline.reference.original.palette.read_engine_palette(
        root/"gameEngine/main.min_653f95bc.js")
    palette=np.asarray(palette,dtype=np.uint8)
    a.require(palette.shape==(128,3),"game palette drift")
    compat,neutral,lab=methods.palette_compatibility(palette)
    named=methods.palette_compatibility(palette,cn)[0] if cn is not None else None
    payload=dict(rgb=palette.tolist(),neutral=neutral.tolist(),lab=lab.tolist(),
                 compatibility=compat.tolist(),cn_compatibility=named.tolist() if named is not None else None,
                 cn_probabilities=methods.cn_probabilities(palette,cn).tolist() if cn is not None else None,
                 engine=provenance,cn=cn_meta)
    a.write_json(out/"game128-compatibility.json",payload)
    for preset in methods.BATCHES[batch]:
        try:
            img,before_ids,after_ids,protected,report,ledger=methods.run_variant(original,target,preset,cn)
            a.require(np.array_equal(ids,before_ids),"baseline labels drift")
            a.require(report["neutral_to_chromatic"]==0 and report["chromatic_to_neutral"]==0,"neutral color drift")
            maps[preset]=img
            zone_reports[preset]=report
            Image.fromarray(img,"RGB").save(out/(preset+"-prepared.png"))
            colors=np.random.default_rng(0).integers(30,232,(int(after_ids.max())+1,3),dtype=np.uint8)
            colors[0]=255
            Image.fromarray(colors[after_ids],"RGB").save(out/(preset+"-zones.png"))
            np.savez_compressed(out/(preset+"-zones.npz"),baseline_ids=before_ids,
                zone_ids=after_ids,protected_dots=protected,prepared=img)
            a.write_json(out/(preset+"-merge-ledger.json"),ledger)
        except Exception as exc:
            failures[preset]=repr(exc)
            a.write_json(out/"variant-failures.json",failures)
    colors=np.random.default_rng(0).integers(30,232,(int(ids.max())+1,3),dtype=np.uint8)
    colors[0]=255
    Image.fromarray(colors[ids],"RGB").save(out/"a5-zones.png")
    a.write_json(out/"zone-results.json",dict(baseline=before,variants=zone_reports,failures=failures))
    results={}
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        a.require(not native.render(driver,"blank",[])[:,:,3].any(),"nonblank")
        control=[native.stroke(native.segment(200,100,12,0),4,0,0),
                 native.stroke([dict(x=x,y=y) for x,y in [(220,100),(240,100),(240,115),(220,115)]],7,0,1)]
        first=native.render(driver,"reference-original",control)
        driver.execute_script(p.fixture(native))
        a.require(np.array_equal(first,native.render(driver,"reference-expanded",control)),"fixture drift")
        proof=physical.native_footprints(driver)
        a.write_json(out/"egret-physical-footprints.json",proof)
        stamps,_=a.measure_stamps(driver,native,out)
        pad=a.width1_pad(stamps,proof)
        atlas,summary=p.measure(driver,native,out)
        def save(name,paths,raw,img,projected):
            a.save_plan(out,name,paths)
            m,_,_,_=transfer.score(name,raw,img,geom,out)
            fixed,_,_,_=transfer.score(name+"-fixed-a5",raw,target,geom,out)
            actual=a.white_rgb(raw[:,a.OX:a.OX+450])
            err=np.abs(actual.astype(np.int16)-original_want.astype(np.int16))
            fg=np.any(want!=a.WHITE,axis=2)
            results[name]=dict(**a.stats(paths),metrics=m,detail_metrics=a.diagnostics(raw,projected),
                 fixed_a5_metrics=fixed,original_rgb_mae=float(err.mean()),
                 original_foreground_rgb_mae=float(err[fg].mean()) if fg.any() else None,
                 continuity=p.continuity(paths),raw_sha256=a.sha(out/(name+".png")),
                 plan_sha256=a.sha(out/(name+"-plan.json.gz")))
        for key,img in {"a5":target,**maps}.items():
            projected,_,_=transfer.projected(img,geom)
            baseline,params=physical.plan_same_color_overlap(img,geom,proof)
            if key=="a5":
                a.require(len(baseline)==a.CASES[case],"P1 count drift")
            _,broad,counts,ledger=q.broad_plan(projected,atlas,proof,native.stroke)
            raw=native.render(driver,key+"-broad",broad)
            save(key+"-broad",broad,raw,img,projected)
            detail,reasons=a.retain_detail(baseline,projected,raw[:,a.OX:a.OX+450],pad)
            detail,union=f.union_detail(detail)
            final=a.combine(broad,detail)
            a.require(final and all(1<=s["width"]<=10 and s["colorRgb"]!=0xffffff for s in final),"invalid final")
            if key=="a5":
                a.require(len(final)==A5_COUNTS[case] and len(broad)==q.A3_COUNTS[case][0],"A5 count drift")
            save(key,final,native.render(driver,key,final),img,projected)
            results[key]["detail_selection"]=reasons
            results[key]["detail_union"]=union
            results[key]["broad_counts"]=counts
            results[key]["broad_route_metrics"]=q.route_metrics(broad)
            a.write_json(out/(key+"-route-ledger.json"),ledger)
    panel(out,original,target,maps)
    (out/"comparison.png").rename(out/"batch-comparison.png")
    for key,img in maps.items():
        panel(out,original,target,{key:img})
        (out/"comparison.png").rename(out/(key+"-comparison.png"))
    a.write_json(out/"a6-z2-results.json",dict(schema="ENGINE001_S5_ADAPTIVE_A6_Z2_V1",
        batch=batch,cn_provenance=cn_meta,failures=failures,
        case=case,sha=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],
        source=rel,source_git_blob=expected,source_sha256=a.sha(root/rel),
        source_manifest_sha256=a.sha(source/"source-manifest.json"),
        target_sha256=a.array_sha(target),variant_sha256={k:a.array_sha(i) for k,i in maps.items()},
        geometry=geom,renderer=a.RENDERER,mode="normal",smooth=False,
        a5_blob=A5_BLOB,a4_blob=f.A4_BLOB,atlas=summary,zones=zone_reports,results=results,
        human_visual_review="PENDING",exact_CHALK="NOT_RUN",independent_E5="NOT_RUN",
        production_admissible=False))
    a.require(not failures,"one or more methods failed; retain partial artifacts")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=tuple(A5_COUNTS),required=True)
    parser.add_argument("--batch",choices=tuple(methods.BATCHES),required=True)
    args=parser.parse_args()
    main(args.case,args.batch)
