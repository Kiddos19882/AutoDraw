"""Eight-color wV. Unrestricted, full-scene Egret normal redraw on one board."""
from collections import Counter
import argparse
import hashlib
import gzip
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image
import run_engine001_s5_wv_native_binding as binding

OUT = Path(os.environ["RUNNER_TEMP"]) / "wv-full"
SPANS = (4, 7, 10, 13, 15, 19, 21, 25, 27, 31)  # native backing, binding CI 45203361169
DIRECTIONS = ((.75,0), (0,.75), (.5,.5), (.5,-.5))


def stroke(points, width, rgb, index):
    return dict(points=points, width=width, colorRgb=rgb, strokeId=f"icon-{index}")


def segment(x,y,dx,dy):
    return [dict(x=x-dx/2,y=min(239.999,max(0,y-dy/2))), dict(x=x+dx/2,y=min(239.999,max(0,y+dy/2)))]


def full_fixture():
    js = binding.os_pinned_source(binding.ROOT / "tests/game_renderer_reference.js")
    first = js.index("function makeTemporalBoard(")
    last = js.index("function renderTemporalStudy", first)
    part = js[first:last]
    old = "new BoardPane(false, 6000)"
    assert part.count(old) == 1
    js = js[:first]+part.replace(old,"new BoardPane(false, Math.max(6000,1+strokes.reduce((n,s)=>n+s.points.length,0)))")+js[last:]
    first = js.index("function renderComplexHoldoutColorProbe(")
    last = js.index("const board = makeTemporalBoard(",first)
    part = js[first:last]
    for old in (" || strokes.length > 3000", 'if (count > 5900) throw new Error("V5 point budget exceeded.");'):
        assert part.count(old) == 1
        part = part.replace(old,"")
    return js[:first]+part+js[last:]


def render(driver, name, paths):
    response = driver.execute_script(binding.native.CMD, paths)
    rgba, meta = binding.native.read_webgl_result(response,OUT,name)
    assert meta["renderer"]=="real Egret 5.4.1 BoardPane/WebGLRenderer" and meta["sceneDiagnostics"]["stageAttached"]
    if paths:
        assert meta["mode"]=="normal" and meta["strokeCount"]==len(paths)
        assert meta["syntheticAcceptedVerticesNotChalk"]==sum(len(p["points"]) for p in paths)
    binding.write_json(OUT/(name+".json"),meta)
    return rgba


def measure_segments(driver):
    probes, positions = [], []
    for iy in range(4):
        for ix in range(4):
            for k,(dx,dy) in enumerate(DIRECTIONS):
                center=binding.board_point(32+ix,32+iy)
                x=center['x']%1+32+24*(4*k+ix)
                y=center['y']%1+36+32*iy
                probes.append(stroke(segment(x,y,dx,dy),1,0,len(probes)))
                positions.append(((ix,iy,k),x,y))
    rgba=render(driver,"calibration",probes)
    masks={}
    for key,x,y in positions:
        i,j=int(3*x),int(3*y)
        mask=rgba[j-5:j+6,i-5:i+6,3]>=128
        dy,dx=np.nonzero(mask)
        masks[key]=(dx-5,dy-5)
    assert any(len(dx) for dx,dy in masks.values())
    return masks


def choose_segment(x,y,owner,owners,masks,extra_percent=0,orientation='balanced'):
    c=binding.board_point(x,y)
    candidates=[]
    for k,(vx,vy) in enumerate(DIRECTIONS):
        dx,dy=masks[x%4,y%4,k]
        sx=np.floor((int(3*c['x'])+dx+.5-465)/2.25).astype(int)
        sy=np.floor((int(3*c['y'])+dy+.5)/2.25).astype(int)
        inside=(sx>=0)&(sx<owners.shape[1])&(sy>=0)&(sy<owners.shape[0])
        same=np.zeros_like(inside)
        same[inside]=owners[sy[inside],sx[inside]]==owner
        hit=int(((sx==x)&(sy==y)).sum())
        spill=int((~same).sum())
        rank=(hit>0,-spill,hit)
        candidates.append((rank,segment(c['x'],c['y'],vx,vy),k))
    baseline=max(candidates,key=lambda candidate:candidate[0])[0]
    allowed_spill=(-baseline[1])*(100+extra_percent)//100
    eligible=[(rank,path,k) for rank,path,k in candidates
              if rank[0]==baseline[0] and -rank[1]<=allowed_spill]
    if orientation == "balanced":
        rank,path,k=max(eligible,key=lambda candidate:(candidate[0][2],candidate[0][1]))
    else:
        assert orientation in ("axis-first","diagonal-first")
        preferred=(0,1,2,3) if orientation=="axis-first" else (2,3,0,1)
        rank,path,k=min(eligible,key=lambda candidate:(preferred.index(candidate[2]),-candidate[0][2],-candidate[0][1]))
    return path,rank


def luminance(rgb):
    return 2126*((rgb>>16)&255)+7152*((rgb>>8)&255)+722*(rgb&255)


def arrange_strokes(records,strategy):
    """Same strokes, alternate compositing order only. Phase 0=source sweep, 1=residual."""
    if strategy in ("global","axis-first","diagonal-first"):
        ordered=sorted(records,key=lambda r:(r["phase"],r["index"]))
    elif strategy=="owner-paired":
        ordered=sorted(records,key=lambda r:(r["owner"],r["phase"],r["index"]))
    elif strategy=="light-to-dark":
        ordered=sorted(records,key=lambda r:(-luminance(r["color"]),r["phase"],r["index"]))
    elif strategy=="dark-to-light":
        ordered=sorted(records,key=lambda r:(luminance(r["color"]),r["phase"],r["index"]))
    else:
        raise ValueError("unknown strategy "+strategy)
    return [r["path"] for r in ordered]


def score(name,rgba,target):
    image=Image.fromarray(rgba)
    white=Image.new("RGBA",image.size,"white")
    white.alpha_composite(image)
    crop=white.convert("RGB").crop((465,0,915,720))
    crop.save(OUT/(name+"-crop.png"))
    arr=np.asarray(crop).astype(float)
    rows=np.floor((np.arange(720)+.5)/2.25).astype(int)
    cols=np.floor((np.arange(450)+.5)/2.25).astype(int)
    want=target[rows[:,None],cols]
    palette=np.unique(target.reshape(-1,3),axis=0)
    distances=np.stack([np.square(arr-color).sum(axis=2) for color in palette],axis=2)
    closest=palette[distances.argmin(axis=2)]
    correct=np.all(closest==want,axis=2)
    fg=np.any(want!=255,axis=2)
    return dict(backing_pixels=int(correct.size),nearest_correct=int(correct.sum()),
                fg=int(fg.sum()),fg_correct=int(correct[fg].sum()),
                fg_read_as_white=int((fg&np.all(closest==255,axis=2)).sum()),
                mean_absolute_rgb_error=float(abs(arr-want).mean()))


def main(extra_percent=0,strategy='global'):
    assert strategy=='global' or extra_percent==20, 'variant requires frozen 20% policy'
    OUT.mkdir()
    src=OUT/"source"
    binding.pipeline.run(binding.ROOT,binding.pipeline.reference.original.dev.SOURCES[0],src,second_lane_audit=True)
    result=json.loads((src/"results.json").read_bytes())
    assert result["plan_sha256"]=="2f8762aa40d352bc5649234d653817ab1dba9530cfba14599b89fb7ad225dca3"
    target=np.array(Image.open(src/"02-prepared.png"))
    with np.load(src/"zones.npz") as a:
        owners=a["paintable_id"]
    with gzip.open(src/"plan.json.gz") as f:
        original=json.load(f)["proposals"]
    base, repairs=[],[]
    records=[]
    diagnostics=Counter()
    with binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not render(driver,"blank",[])[:,:,3].any()
        control=[stroke(segment(200,100,12,0),4,0,0)]
        reference=render(driver,"control-original",control)
        driver.execute_script(full_fixture())
        assert np.array_equal(reference,render(driver,"control-full",control))
        masks=measure_segments(driver)
        for i,p in enumerate(original):
            x,y=map(int,p["points"][0])
            color=int.from_bytes(bytes(target[y,x]),"big")
            width=max((n for n,s in enumerate(SPANS,1) if 400*s<=9*p['brush_value']*(100+extra_percent)),default=1)
            if len(p["points"])==1:
                orient=strategy if strategy in ("axis-first","diagonal-first") else "balanced"
                points,rank=choose_segment(x,y,p['paintable_id'],owners,masks,extra_percent,orient)
                if orient!="balanced":
                    reference,_=choose_segment(x,y,p['paintable_id'],owners,masks,extra_percent,"balanced")
                    diagnostics["changed_residual_direction"]+=int(points!=reference)
                diagnostics["predicted_target_hit"]+=int(rank[0])
                diagnostics["predicted_outside_owner"]+=int(rank[1]<0)
                path=stroke(points,width,color,i)
                repairs.append(path)
                phase=1
            else:
                points=[binding.board_point(*xy) for xy in p["points"]]
                path=stroke(points,width,color,i)
                base.append(path)
                phase=0
            records.append(dict(owner=int(p['paintable_id']),color=color,phase=phase,index=i,path=path))
        paths=arrange_strokes(records,strategy)
        assert len(paths)==len(original) and len(set(p["colorRgb"] for p in paths))==8
        assert len(base)==6042 and len(repairs)==2880
        diagnostics["changed_path_order"]=sum(a["strokeId"]!=b["strokeId"] for a,b in zip(paths,base+repairs))
        with gzip.open(OUT/"native-plan.json.gz","wt") as f:
            json.dump(paths,f,separators=(",",":"))
        metrics={}
        for name,group in (("before-repair",base),("full",paths)):
            rgba=render(driver,name,group)
            metrics[name]=score(name,rgba,target)
    binding.write_json(OUT/"results.json",dict(sha=os.environ['GITHUB_SHA'],run=os.environ['GITHUB_RUN_ID'],
        extra_tolerance_percent=extra_percent,strategy=strategy,
        native_plan_sha256=hashlib.sha256(json.dumps(paths,separators=(",",":")).encode()).hexdigest(),
        source_sha256=result["input_sha256"],source_plan_sha256=result["plan_sha256"],
        base=len(base),repairs=len(repairs),colors=8,diagnostics=dict(diagnostics),metrics=metrics))
    print(metrics)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--extra-tolerance-percent",type=int,choices=(0,10,15,20),default=0)
    parser.add_argument("--strategy",choices=("global","owner-paired","light-to-dark","dark-to-light","axis-first","diagonal-first"),default="global")
    args=parser.parse_args()
    main(args.extra_tolerance_percent,args.strategy)
