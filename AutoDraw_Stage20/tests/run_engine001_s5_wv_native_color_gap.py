"""Render-based color-hole repair: one native short stroke per affected source pixel."""
import gzip
import json
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_s5_wv_full_native as base
import run_engine001_s5_wv_native_feedback as feedback


def white_readback(native_rgba, target):
    crop=Image.fromarray(native_rgba[:720,465:915])
    white=Image.new("RGBA",crop.size,"white")
    white.alpha_composite(crop)
    arr=np.asarray(white.convert("RGB")).astype(np.float32)
    want,rows,cols=feedback.projected_target(target)
    colors=np.unique(target.reshape(-1,3),axis=0).astype(np.float32)
    squared=np.stack([np.square(arr-color).sum(axis=2) for color in colors],axis=-1)
    nearest=colors[squared.argmin(axis=2)]
    fg=np.any(want!=255,axis=2)
    missing=fg & np.all(nearest==255,axis=2)
    return missing,rows,cols


def patches_from_visual(native_rgba, target, first_id):
    missing,rows,cols=white_readback(native_rgba,target)
    yy,xx=np.nonzero(missing)
    sid=rows[yy]*target.shape[1]+cols[xx]
    ids,inverse=np.unique(sid,return_inverse=True)
    counts=np.bincount(inverse,minlength=len(ids))
    xxpos=np.bincount(inverse,weights=xx.astype(float),minlength=len(ids))/counts
    yypos=np.bincount(inverse,weights=yy.astype(float),minlength=len(ids))/counts
    sy,sx=np.divmod(ids,target.shape[1])
    repair=[]
    for i,(x,y,u,v) in enumerate(zip(xxpos,yypos,sx,sy)):
        rgb=int.from_bytes(bytes(target[int(v),int(u)]),"big")
        bx=(465+float(x)+.5)/3
        by=(float(y)+.5)/3
        repair.append(base.stroke(base.segment(bx,by,.5,0),1,rgb,first_id+i))
    return repair,int(missing.sum())


def main():
    base.main(20,"global")
    out=base.OUT
    target=np.asarray(Image.open(out/"source/02-prepared.png"))
    with gzip.open(out/"native-plan.json.gz","rt") as f:
        paths=json.load(f)
    assert len(paths)==8922
    rgba=np.asarray(Image.open(out/"full.png"))
    initial_mask,_,_=white_readback(rgba,target)
    assert int(initial_mask.sum())==12932
    history=[dict(phase="baseline",nearest_white_wrong=int(initial_mask.sum()),
                  alpha=feedback.diagnostic(rgba,target),
                  metrics=json.loads((out/"results.json").read_text())["metrics"]["full"],
                  cumulative_strokes=len(paths))]
    with base.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not base.render(driver,"color-blank",[])[:,:,3].any()
        control=[base.stroke(base.segment(200,100,12,0),4,0,0)]
        reference=base.render(driver,"color-control-original",control)
        driver.execute_script(base.full_fixture())
        assert np.array_equal(reference,base.render(driver,"color-control-full",control))
        for n in (1,2):
            extra,wrong_count=patches_from_visual(rgba,target,1000000*n)
            if not extra:
                history.append(dict(phase="round%d-clear"%n,nearest_white_wrong=0,
                                    added_strokes=0,cumulative_strokes=len(paths)))
                break
            paths.extend(extra)
            with gzip.open(out/("color-round%d-plan.json.gz"%n),"wt") as file:
                json.dump(paths,file,separators=(",",":"))
            rgba=base.render(driver,"color-round%d"%n,paths)
            metrics=base.score("color-round%d"%n,rgba,target)
            wrong,_,_=white_readback(rgba,target)
            history.append(dict(phase="color-round%d"%n,nearest_white_wrong=int(wrong.sum()),
                                previous_wrong=wrong_count,
                                alpha=feedback.diagnostic(rgba,target),
                                metrics=metrics,
                                added_strokes=len(extra),cumulative_strokes=len(paths)))
    report=dict(run=__import__("os").environ["GITHUB_RUN_ID"],
         sha=__import__("os").environ["GITHUB_SHA"],method="color-white-centroid",
         source_plan_sha256="2f8762aa40d352bc5649234d653817ab1dba9530cfba14599b89fb7ad225dca3",
         mode="normal",smooth=False,baseline_tolerance=20,
         history=history,exact_CHALK="NOT_RUN")
    base.binding.write_json(out/"color-gap-results.json",report)
    print("COLOR_GAP_RESULTS "+json.dumps(report,separators=(",",":")))


if __name__=="__main__":
    main()
