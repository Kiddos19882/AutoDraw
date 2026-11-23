"""Research-only: finish real Egret color-white gaps by exact backing-pixel feedback."""
import gzip
import json
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_s5_wv_full_native as base
import run_engine001_s5_wv_native_color_gap as color_gap
import run_engine001_s5_wv_native_feedback as alpha_gap


def at_real_missing_pixels(rgba, target, first_id):
    missing, rows, cols = color_gap.white_readback(rgba, target)
    yy, xx = np.nonzero(missing)
    strokes = []
    for i, (x, y) in enumerate(zip(xx, yy)):
        rgb = int.from_bytes(bytes(target[rows[y], cols[x]]), "big")
        bx=(465+int(x)+.5)/3
        by=(int(y)+.5)/3
        strokes.append(base.stroke(base.segment(bx, by, .5, 0), 1, rgb, first_id+i))
    return strokes, int(missing.sum())


def main():
    color_gap.main()
    out=base.OUT
    with gzip.open(out/"color-round2-plan.json.gz","rt") as f:
        paths=json.load(f)
    previous=json.loads((out/"color-gap-results.json").read_text())
    target=np.asarray(Image.open(out/"source/02-prepared.png"))
    rgba=np.asarray(Image.open(out/"color-round2.png"))
    assert len(paths)==15699
    assert previous["history"][-1]["nearest_white_wrong"]==1809
    history=[dict(phase="color-centroid-2",nearest_white_wrong=1809,
                  metrics=previous["history"][-1]["metrics"],
                  cumulative_strokes=len(paths))]
    with base.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not base.render(driver,"dense-blank",[])[:,:,3].any()
        control=[base.stroke(base.segment(200,100,12,0),4,0,0)]
        original=base.render(driver,"dense-control-original",control)
        driver.execute_script(base.full_fixture())
        assert np.array_equal(original,base.render(driver,"dense-control-full",control))
        for round_number in (3, 4):
            extra, n = at_real_missing_pixels(rgba,target,1000000*round_number)
            if not extra:
                history.append(dict(phase="dense-round%d-clear"%round_number,
                                    nearest_white_wrong=0,added_strokes=0,
                                    cumulative_strokes=len(paths)))
                break
            paths.extend(extra)
            with gzip.open(out/("dense-round%d-plan.json.gz"%round_number),"wt") as f:
                json.dump(paths,f,separators=(",",":"))
            rgba=base.render(driver,"dense-round%d"%round_number,paths)
            metrics=base.score("dense-round%d"%round_number,rgba,target)
            remaining,_,_=color_gap.white_readback(rgba,target)
            history.append(dict(phase="dense-round%d"%round_number,
                                previous_wrong=n,
                                nearest_white_wrong=int(remaining.sum()),
                                alpha=alpha_gap.diagnostic(rgba,target),
                                added_strokes=len(extra),cumulative_strokes=len(paths),
                                metrics=metrics))
    report=dict(run=__import__("os").environ["GITHUB_RUN_ID"],
                sha=__import__("os").environ["GITHUB_SHA"],
                method="source-centroid-2-then-native-backing-pixels",
                source_plan_sha256="2f8762aa40d352bc5649234d653817ab1dba9530cfba14599b89fb7ad225dca3",
                baseline_tolerance=20,mode="normal",smooth=False,
                history=history,exact_CHALK="NOT_RUN")
    base.binding.write_json(out/"dense-results.json",report)
    print("DENSE_CLOSURE_RESULTS "+json.dumps(report,separators=(",",":")))


if __name__=="__main__":
    main()
