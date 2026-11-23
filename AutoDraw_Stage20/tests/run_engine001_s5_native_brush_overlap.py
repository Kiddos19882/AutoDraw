"""S5 two-axis real Egret footprint overlap vs original full-source native planner."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

import engine001_s5_native_brush_overlap as native_footprint
import run_engine001_s5_originals_native_transfer as transfer
import run_engine001_s5_wv_full_native as native

CASE={"wv":0,"hello":1,"pink":3}

def original_native_full(proposals,target,g,driver,case):
    if case!="wv":
        return transfer.original_paths(proposals,target,g)[0]
    masks=native.measure_segments(driver)
    broad,repair=[],[]
    for i,p in enumerate(proposals):
        x,y=map(int,p["points"][0])
        rgb=int.from_bytes(bytes(target[y,x]),"big")
        width=max((n for n,s in enumerate(native.SPANS,1)
                   if 400*s<=9*p["brush_value"]*120),default=1)
        if len(p["points"])==1:
            with np.load(native.OUT/"source"/"zones.npz") as zone:
                owners=zone["paintable_id"]
            points,_=native.choose_segment(x,y,p["paintable_id"],owners,masks,20)
            repair.append(native.stroke(points,width,rgb,i))
        else:
            broad.append(native.stroke([native.binding.board_point(*q)
                    for q in p["points"]],width,rgb,i))
    return broad+repair

def main(case):
    root=native.binding.ROOT
    relative=native.binding.pipeline.reference.original.dev.SOURCES[CASE[case]]
    out=Path(os.environ["RUNNER_TEMP"])/("s5-native-overlap-"+case)
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    src=out/"source"
    native.binding.pipeline.run(root,relative,src,second_lane_audit=(case=="wv"))
    target=np.asarray(Image.open(src/"02-prepared.png"))
    assert target.shape[2]==3 and len(np.unique(target.reshape(-1,3),axis=0))==8
    g=transfer.layout(target.shape[1],len(target))
    with gzip.open(src/"plan.json.gz","rt") as f:
        proposals=json.load(f)["proposals"]
    source_info=json.loads((src/"results.json").read_text())
    history={}
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not native.render(driver,"blank",[])[:,:,3].any()
        control=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        before=native.render(driver,"control-original",control)
        driver.execute_script(native.full_fixture())
        assert np.array_equal(before,native.render(driver,"control-full",control))
        proof=native_footprint.native_footprints(driver)
        native.binding.write_json(out/"egret-physical-footprints.json",proof)
        baseline_paths=original_native_full(proposals,target,g,driver,case)
        with gzip.open(out/"old-native-plan.json.gz","wt") as f:
            json.dump(baseline_paths,f,separators=(",",":"))
        baseline_rgba=native.render(driver,"old-native",baseline_paths)
        bscore,_,_,_=transfer.score("old-native",baseline_rgba,target,g,out)
        print("NATIVE_OVERLAP_BASELINE "+json.dumps({"case":case,"strokes":len(baseline_paths),
             "metrics":bscore},separators=(",",":")),flush=True)
        paths,plan_report=native_footprint.plan_same_color_overlap(target,g,proof)
        with gzip.open(out/"overlap-native-plan.json.gz","wt") as f:
            json.dump(paths,f,separators=(",",":"))
        rgba=native.render(driver,"native-overlap",paths)
        score,_,_,_=transfer.score("native-overlap",rgba,target,g,out)
        history=dict(baseline={"paths":len(baseline_paths),"metrics":bscore},
                     measured_overlap={"paths":len(paths),"metrics":score})
        print("NATIVE_OVERLAP_RESULT "+json.dumps({"case":case,"strokes":len(paths),
             "metrics":score,"pitch":plan_report["parameters"]},separators=(",",":")),flush=True)
    report=dict(schema="ENGINE001_S5_NATIVE_TWO_AXIS_EGRET_OVERLAP_V1",
        sha=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],
        source=str(relative),source_sha256=source_info["input_sha256"],
        source_plan_sha256=source_info["plan_sha256"],source_size=target.shape[:2],
        game_colors=8,normal=True,smooth=False,reference="full-original-source-plan",
        renderer="real Egret 5.4.1 BoardPane/WebGLRenderer",
        footprint_mode="actual alpha128 readback, four phases per width and angle",
        measured_native_geometry=proof["measurements"],
        algorithm=plan_report,results=history,
        gameplay_CHALK="NOT_RUN",production_admissible=False)
    native.binding.write_json(out/"native-overlap-results.json",report)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--case",required=True,choices=tuple(CASE))
    main(p.parse_args().case)
