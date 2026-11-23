"""ENGINE-001 S5 transfer P2: unmodified user-accepted native overlap on new originals.

Do not modify the accepted S5 P1 native planner or use mathematical footprint proxies.
This driver only selects fresh originals, prepares their 8 original-authentic swatches,
saves true Egret brush readback and renders its unchanged width-1 overlap plan.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import engine001_s5_native_brush_overlap as physical
import run_engine001_s5_originals_native_transfer as transfer
import run_engine001_s5_wv_full_native as native

CASE = {
    "home": ("data/generated_autodraw_plan/images_31_first/free-icon-font-home-3917033.png",
             "4c1f9c7a6682451d3949c539480e2f7550c5eedf"),
    "illustration": ("data/generated_autodraw_plan/images_31_first/4534364.jpg",
                     "27050fbd1661f1c36a0abea3ee0dc25eb84d86a5"),
    "second-png": ("data/generated_autodraw_plan/images2_50_second/32543623432543.png",
                   "c76730e9ffd255b3e9155229ce97d86285d019fd"),
}
RENDERER = "real Egret 5.4.1 BoardPane/WebGLRenderer"


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def alpha_onto_white(image):
    rgba=image.convert("RGBA")
    white=Image.new("RGBA",rgba.size,(255,255,255,255))
    white.alpha_composite(rgba)
    return white.convert("RGB")


def make_comparison(out,original,prepared,rendered):
    # Visual panel of actual originals, actual eight game swatches and real
    # native readback. No generated/reconstructed fake brush outputs.
    names=["ORIGINAL","8 GAME COLORS","ACTUAL EGRET"]
    cells=[alpha_onto_white(original),alpha_onto_white(prepared),rendered.convert("RGB")]
    panel_w,panel_h=350,440
    atlas=Image.new("RGB",(panel_w*len(cells),panel_h),(245,245,245))
    draw=ImageDraw.Draw(atlas)
    for i,(name,im) in enumerate(zip(names,cells)):
        im.thumbnail((panel_w-20,panel_h-53),Image.Resampling.NEAREST)
        x=i*panel_w+(panel_w-im.width)//2
        y=35+(panel_h-53-im.height)//2
        atlas.paste(im,(x,y))
        draw.text((i*panel_w+12,12),name,fill=(25,25,25))
    atlas.save(out/"actual-egret-three-way.png")


def main(case):
    rel,expected_blob=CASE[case]
    root=native.binding.ROOT
    raw=(root/rel).read_bytes()
    actual_blob=git_blob(raw)
    if actual_blob != expected_blob:
        raise RuntimeError("BLOCKED_SOURCE_BLOB_DRIFT "+rel+" "+actual_blob)
    out=Path(os.environ["RUNNER_TEMP"])/("s5-p2-"+case)
    out.mkdir(parents=True,exist_ok=False)
    native.OUT=out
    source=out/"source"
    native.binding.pipeline.run(root,Path(rel),source,palette_only=True)
    image=Image.open(source/"palette-8.png").convert("RGBA")
    rgba=np.asarray(image,dtype=np.uint8)
    target=np.where((rgba[:,:,3]==255)[:,:,None],rgba[:,:,:3],255).astype(np.uint8)
    assert target.shape[0]>0 and target.shape[1]>0
    ncolors=int(np.unique(target.reshape(-1,3),axis=0).shape[0])
    if not 1<=ncolors<=9:
        raise RuntimeError("BLOCKED_TARGET_NOT_EIGHT_GAME_COLORS "+str(ncolors))
    Image.fromarray(target,"RGB").save(out/"prepared-8-white-background.png")
    geom=transfer.layout(target.shape[1],target.shape[0])
    info=json.loads((source/"palette.json").read_text())
    original=Image.open(source/"01-original.png").convert("RGBA")
    records={}
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        blank=native.render(driver,"blank",[])
        if np.any(blank[:,:,3]):
            raise RuntimeError("BLOCKED_NONBLANK_NATIVE_BOARD")
        control=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        before=native.render(driver,"reference-original",control)
        driver.execute_script(native.full_fixture())
        after=native.render(driver,"reference-capacity-expanded",control)
        if not np.array_equal(before,after):
            raise RuntimeError("BLOCKED_NATIVE_FIXTURE_CHANGED_BRUSH")
        proof=physical.native_footprints(driver)
        native.binding.write_json(out/"egret-physical-footprints.json",proof)
        paths,params=physical.plan_same_color_overlap(target,geom,proof)
        if not paths or params["parameters"]["native_width"]!=1:
            raise RuntimeError("BLOCKED_NOT_ACCEPTED_NATIVE_P1")
        if len(set(p["colorRgb"] for p in paths))>8:
            raise RuntimeError("BLOCKED_PALETTE_DRIFT")
        if any(int(p["width"])!=1 for p in paths):
            raise RuntimeError("BLOCKED_BRUSH_WIDTH_DRIFT")
        with gzip.open(out/"accepted-p1-overlap-plan.json.gz","wt",encoding="utf8") as f:
            json.dump(paths,f,separators=(",",":"))
        rendered=native.render(driver,"actual-native-egret",paths)
        measures,_,_,_=transfer.score("actual-native-egret",rendered,target,geom,out)
        records=dict(strokes=len(paths),metrics=measures,planner=params)
        print("P2_NATIVE_RESULT "+json.dumps({"case":case,**records},separators=(",",":")),flush=True)
    make_comparison(out,original,image,Image.open(out/"actual-native-egret-crop.png"))
    native.binding.write_json(out/"transfer-p2-results.json",{
        "schema":"ENGINE001_S5_ACCEPTED_NATIVE_TRANSFER_P2_V1",
        "case":case,"github_sha":os.environ.get("GITHUB_SHA","LOCAL"),
        "run":os.environ.get("GITHUB_RUN_ID","LOCAL"),
        "original":rel,"original_git_blob":actual_blob,
        "original_sha256":hashlib.sha256(raw).hexdigest(),
        "original_size":[original.width,original.height],
        "whole_original":True,"prepared_palette_manifest":info,
        "prepared_white_target_colors":ncolors,"geometry":geom,
        "renderer":RENDERER,"mode":"normal","smooth":False,
        "brush_widths_used":[1],"real_footprint_probes":proof["probes"],
        "accepted_algorithm":"engine001_s5_native_brush_overlap.plan_same_color_overlap",
        "accepted_algorithm_parent_sha":"796aefb36a727184a0bdcfc12aa278ed01d3fe2e",
        "no_production_changes":True,"human_visual_review":"PENDING",
        "exact_CHALK":"NOT_RUN","independent_E5":"NOT_RUN",
        "results":records})


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--case",choices=tuple(CASE),required=True)
    main(ap.parse_args().case)
