"""A5: union overlapping horizontal width1 intervals; frozen A4 broad routes."""
import argparse
from collections import defaultdict, Counter
import math
import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import run_engine001_s5_native_adaptive_a1 as a
import run_engine001_s5_native_adaptive_a2 as v
import run_engine001_s5_native_adaptive_a3 as p
import run_engine001_s5_native_adaptive_a4 as q

A4_BLOB="ee4fdc4ea34c6a33d0c55ee6d341edadd01a91c1"
A4_COUNTS={"home":2361,"illustration":23261,"second-png":11900}


def union_detail(paths):
    groups=defaultdict(list)
    before=Counter()
    length_before=Counter()
    for i,path in enumerate(paths):
        a.require(path["width"]==1 and len(path["points"])==2,"unexpected detail path")
        u,w=path["points"]
        x,y,z,t=u["x"],u["y"],w["x"],w["y"]
        a.require(all(math.isfinite(k) for k in (x,y,z,t)) and y==t and x!=z,
                  "nonhorizontal, nonfinite or degenerate detail")
        lo,hi=sorted((x,z))
        color=path["colorRgb"]
        groups[color,y].append((lo,hi,i))
        before[color]+=1
        length_before[color]+=hi-lo
    emitted=[]
    merged=0
    after=Counter()
    length_after=Counter()
    def emit(color,y,lo,hi,members):
        nonlocal merged
        first=min(members)
        if len(members)==1:
            path=paths[first]
        else:
            merged+=1
            path=dict(paths[first],points=[dict(x=lo,y=y),dict(x=hi,y=y)])
        emitted.append((first,path))
        after[color]+=1
        length_after[color]+=hi-lo
    for (color,y),items in groups.items():
        items.sort()
        lo,hi,i=items[0]
        members=[i]
        for x,z,j in items[1:]:
            if x<=hi:
                hi=max(hi,z)
                members.append(j)
            else:
                emit(color,y,lo,hi,members)
                lo,hi,members=x,z,[j]
        emit(color,y,lo,hi,members)
    emitted.sort(key=lambda item:item[0])
    out=[path for _,path in emitted]
    a.require(len(out)<=len(paths),"union count regression")
    for color in before:
        a.require(length_after[color]<=length_before[color]+1e-7*max(1,before[color]),
                  "union length regression")
    return out,dict(before=len(paths),after=len(out),merged_groups=merged,
                    per_color={str(c):dict(before=before[c],after=after[c],
                    length_before=length_before[c],length_after=length_after[c])
                    for c in sorted(before)})


def panel(out,original,target):
    from run_engine001_s5_native_transfer_p2 import alpha_onto_white
    cells=[("ORIGINAL",alpha_onto_white(original)),("8 GAME COLORS",Image.fromarray(target,"RGB"))]
    for title,name in (("WIDTH 1","width1"),("A1 ACCEPTED","a1"),("A3 FINAL","a3"),("A4 FINAL","a4"),("A5 FINAL","a5")):
        cells.append((title,Image.open(out/(name+"-crop.png"))))
    atlas=Image.new("RGB",(450*len(cells),760),(245,245,245))
    draw=ImageDraw.Draw(atlas)
    for i,(title,img) in enumerate(cells):
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
    for module,blob in ((physical,a.PLANNER_BLOB),(a,v.A1_BLOB),(v,p.A2_BLOB),(p,q.A3_BLOB),(q,A4_BLOB)):
        a.require(p2.git_blob(Path(module.__file__).read_bytes())==blob,"reference code drift")
    a.require(p2.git_blob((root/rel).read_bytes())==expected,"source drift")
    out=Path(os.environ["RUNNER_TEMP"])/("s5-adaptive-a5-"+case)
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
        control=[native.stroke(native.segment(200,100,12,0),4,0,0),
                 native.stroke([dict(x=x,y=y) for x,y in [(220,100),(240,100),(240,115),(220,115)]],7,0,1)]
        before=native.render(driver,"reference-original",control)
        driver.execute_script(p.fixture(native))
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
                  continuity=p.continuity(paths),raw_sha256=a.sha(out/(name+".png")),
                  plan_sha256=a.sha(out/(name+"-plan.json.gz")))
        save("width1",baseline,native.render(driver,"width1",baseline))
        broad1,_=a.broad_plan(want,stamps,proof,native.stroke)
        raw1=native.render(driver,"a1-broad",broad1)
        save("a1-broad",broad1,raw1)
        detail1,_=a.retain_detail(baseline,want,raw1[:,a.OX:a.OX+450],pad)
        final1=a.combine(broad1,detail1)
        a.require(len(final1)==v.A1_COUNTS[case],"A1 count drift")
        save("a1",final1,native.render(driver,"a1",final1))
        atlas,summary=p.measure(driver,native,out)
        broad,alternative,counts,ledger=q.broad_plan(want,atlas,proof,native.stroke)
        raw=native.render(driver,"a3-broad",broad)
        save("a3-broad",broad,raw)
        detail,reasons=a.retain_detail(baseline,want,raw[:,a.OX:a.OX+450],pad)
        final=a.combine(broad,detail)
        a.require(final and all(1<=p["width"]<=10 and p["colorRgb"]!=0xffffff for p in final),
                  "invalid A3 plan")
        save("a3",final,native.render(driver,"a3",final))
        a.require((len(broad),len(final))==q.A3_COUNTS[case],"A3 count drift")
        reference,ref_counts=p.broad_plan(want,atlas,proof,native.stroke)
        a.require(broad==reference and counts==ref_counts,"A3 plan drift")
        a.require([(s["width"],s["colorRgb"]) for s in broad]==
                  [(s["width"],s["colorRgb"]) for s in alternative],"A4 allocation drift")
        raw4=native.render(driver,"a4-broad",alternative)
        save("a4-broad",alternative,raw4)
        detail4,reasons4=a.retain_detail(baseline,want,raw4[:,a.OX:a.OX+450],pad)
        final4=a.combine(alternative,detail4)
        a.require(final4 and all(1<=s["width"]<=10 and s["colorRgb"]!=0xffffff for s in final4),
                  "invalid A4 plan")
        save("a4",final4,native.render(driver,"a4",final4))
        metrics3=q.route_metrics(broad)
        metrics4=q.route_metrics(alternative)
        a.require(metrics4["total_edges"]<=metrics3["total_edges"],"A4 length increased")
        a.write_json(out/"a4-route-ledger.json",ledger)
        a.require(len(final4)==A4_COUNTS[case],"A4 count drift")
        detail5,union=union_detail(detail4)
        final5=a.combine(alternative,detail5)
        a.require([s for s in final5 if s["width"]>1]==
                  [dict(s,strokeId=t["strokeId"]) for s,t in zip(
                      [s for s in final4 if s["width"]>1],
                      [s for s in final5 if s["width"]>1])],
                  "broad paths changed")
        save("a5",final5,native.render(driver,"a5",final5))
    panel(out,Image.open(source/"01-original.png"),target)
    a.write_json(out/"a5-results.json",dict(schema="ENGINE001_S5_ADAPTIVE_A5_V1",case=case,
        sha=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],source=rel,
        source_git_blob=expected,source_sha256=a.sha(root/rel),target_sha256=a.array_sha(target),
        geometry=geom,renderer=a.RENDERER,mode="normal",smooth=False,
        p1_blob=a.PLANNER_BLOB,a1_blob=v.A1_BLOB,a2_blob=p.A2_BLOB,a3_blob=q.A3_BLOB,a4_blob=A4_BLOB,detail_union=union,
        archived_a2_path_count=p.A2_COUNTS[case],reference_parameters=params,atlas=summary,
        broad_counts=counts,detail_selection=reasons,detail_selection_a4=reasons4,results=results,
        route_metrics_a3=metrics3,route_metrics_a4=metrics4,
        human_visual_review="PENDING",exact_CHALK="NOT_RUN",independent_E5="NOT_RUN",
        production_admissible=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--case",choices=tuple(A4_COUNTS),required=True)
    main(parser.parse_args().case)
