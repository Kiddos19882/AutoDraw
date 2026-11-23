"""Research-only: test if true-white strokes erase source colored details."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_s5_wv_full_native as base


def inspect(rgba, prepared):
    cropped=rgba[:720,465:915]
    rows=np.floor((np.arange(720)+.5)/2.25).astype(int)
    cols=np.floor((np.arange(450)+.5)/2.25).astype(int)
    expected=prepared[rows[:,None],cols]
    colored=np.any(expected!=255,axis=2)
    alpha=cropped[:,:,3]
    pure_white=(alpha==255)&np.all(cropped[:,:,:3]==255,axis=2)
    return dict(colored_alpha0=int((colored&(alpha==0)).sum()),
                colored_alpha24=int((colored&(alpha<=24)).sum()),
                colored_opaque_white=int((colored&pure_white).sum()),
                nonwhite_ink_on_white=int(((~colored)&(alpha>24)&np.any(cropped[:,:,:3]!=255,axis=2)).sum()))


def main(policy):
    base.main(20,"global")
    out=base.OUT
    with gzip.open(out/"native-plan.json.gz","rt") as f:
        paths=json.load(f)
    target=np.asarray(Image.open(out/"source/02-prepared.png"))
    baseline=np.asarray(Image.open(out/"full.png"))
    assert len(paths)==8922
    whites=[p for p in paths if p["colorRgb"]==0xffffff]
    colored=[p for p in paths if p["colorRgb"]!=0xffffff]
    assert len(whites)==3174 and len(colored)==5748
    chosen=colored if policy=="skip-white" else whites+colored
    with base.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not base.render(driver,"white-policy-blank",[])[:,:,3].any()
        control=[base.stroke(base.segment(200,100,12,0),4,0,0)]
        reference=base.render(driver,"white-policy-control-original",control)
        driver.execute_script(base.full_fixture())
        assert np.array_equal(reference,base.render(driver,"white-policy-control-full",control))
        rendered=base.render(driver,policy,chosen)
        metrics=base.score(policy,rendered,target)
    result=dict(policy=policy,sha=__import__("os").environ["GITHUB_SHA"],
      run=__import__("os").environ["GITHUB_RUN_ID"],
      plan_sha256="2f8762aa40d352bc5649234d653817ab1dba9530cfba14599b89fb7ad225dca3",
      native_base=len(paths),white_strokes=len(whites),painted_strokes=len(chosen),
      baseline_raw=inspect(baseline,target),candidate_raw=inspect(rendered,target),
      baseline=json.loads((out/"results.json").read_text())["metrics"]["full"],
      metrics=metrics,exact_CHALK="NOT_RUN")
    base.binding.write_json(out/"white-policy-result.json",result)
    print("WHITE_POLICY_RESULT "+json.dumps(result,separators=(",",":")))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--policy",choices=("skip-white","white-first"),required=True)
    main(parser.parse_args().policy)
