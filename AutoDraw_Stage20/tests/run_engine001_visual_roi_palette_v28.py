#!/usr/bin/env python3
"""ENGINE-001 V28 immutable ROI-only MEDIANCUT color preview comparisons."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/"source"/"preparation"))
from color_scanline import build_color_scanline_plan,render_color_scanline_preview,validate_color_scanline_plan
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare_source(path):
    if Path(path).stat().st_size!=97308 or sha(path)!=SOURCE_SHA:
        raise ValueError("V28 original source SHA/byte count mismatch")
    with Image.open(path) as img:
        if img.size!=(200,320):raise ValueError("Frozen V28 source dimension")
        roi=img.convert("RGB").resize((150,240),Image.Resampling.LANCZOS)
    canvas=Image.new("RGB",(460,240),"white")
    canvas.paste(roi,(155,0))
    return roi,canvas

def quantize_case(roi,canvas,count,full_canvas,skip_white):
    base=canvas if full_canvas else roi
    quant=base.quantize(colors=count,method=Image.Quantize.MEDIANCUT,
                         dither=Image.Dither.NONE)
    raw=np.asarray(quant,dtype=np.int32)
    target=raw[:,155:305] if full_canvas else raw
    labels=sorted({int(n) for n in np.unique(raw)})
    if len(labels)!=count:raise ValueError("Pillow quantization produced unexpected number of labels")
    rawpal=quant.getpalette()
    colors=[]
    for key in labels:
        rgb=[int(v) for v in rawpal[key*3:key*3+3]]
        if len(rgb)!=3:raise ValueError("Truncated palette")
        colors.append({"id":f"class-{key}","name":f"Class {key}","rgb":rgb,
                       "hex":"#"+''.join(f"{v:02X}" for v in rgb)})
    if len(set(tuple(v["rgb"]) for v in colors))!=count:raise ValueError("Duplicate palette RGB")
    index_map=np.full((240,460),-1,dtype=np.int32)
    class_by_label={key:i for i,key in enumerate(labels)}
    skipped=[]
    for key,i in class_by_label.items():
        if skip_white and all(v>=245 for v in colors[i]["rgb"]):
            skipped.append(i)
        else:
            index_map[:,155:305][target==key]=i
    if not np.any(index_map>=0):raise ValueError("No remaining visible pixels")
    if np.any(index_map[:,:155]!=-1) or np.any(index_map[:,305:]!=-1):
        raise ValueError("Outside ROI pixel mapping")
    return index_map,colors,skipped

def sheet(items,names,out,top=False):
    if top:items=[i.crop((0,0,150,125)) for i in items]
    w,h=items[0].size
    scale=3;pad=16;head=40
    canvas=Image.new("RGB",(len(items)*(w*scale+pad)+pad,h*scale+head+pad),"#e7ebf0")
    d=ImageDraw.Draw(canvas)
    for i,(item,label) in enumerate(zip(items,names)):
        if item.size!=(w,h):raise ValueError("Bad sheet source size")
        x=pad+i*(w*scale+pad)
        d.text((x+3,12),label,fill="#151515")
        canvas.paste(item.resize((w*scale,h*scale),Image.Resampling.NEAREST),(x,head))
    canvas.save(out)

def run(original,frozen_a,output):
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError("No overwrite original evidence")
    roi,canvas=prepare_source(original)
    cases=[
        ("A-full-canvas8",8,True,False),
        ("B-source-roi8",8,False,False),
        ("C-source-roi6",6,False,False),
        ("D-roi8-skipwhite",8,False,True),
    ]
    output.mkdir(parents=True,exist_ok=True)
    saved={};pictures=[]
    for name,n,full,skip in cases:
        indexes,palette,skipped=quantize_case(roi,canvas,n,full,skip)
        plan=build_color_scanline_plan(indexes,palette,row_step_px=1,row_offset_px=0,
                                       source_name="wV6VeZI9S1Y.png")
        validate_color_scanline_plan(plan)
        preview=render_color_scanline_preview(plan,max_dimension=1600)
        if preview.size!=(460,240):raise ValueError("Unexpected native preview size")
        arr=np.asarray(preview.convert("RGBA"))
        if np.any(arr[:,:155,3]!=0) or np.any(arr[:,305:,3]!=0):
            raise ValueError("V28 preview outside frozen ROI")
        backdrop=Image.new("RGB",(460,240),"white")
        backdrop.paste(preview,(0,0),preview)
        cropped=backdrop.crop((155,0,305,240))
        cropped.save(output/(name+".png"))
        preview.save(output/(name+"-alpha.png"))
        (output/(name+"-plan.json")).write_text(
            json.dumps(plan,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf8")
        summary=plan["summary"]
        quota=summary.get("point_quota_estimate",{})
        saved[name]={
            "palette_rgb":[x["rgb"] for x in palette],
            "ignored_near_white_indices":skipped,
            "visible_index_pixels":int((indexes>=0).sum()),
            "stroke_count":len(plan["strokes"]),
            "point_vertices":sum(len(stroke["points"]) for stroke in plan["strokes"]),
            "color_switch_count":summary.get("color_switch_count"),
            "forecast_game_points":quota.get("estimated_point_count"),
            "forecast_vs6000_ratio":round(quota.get("estimated_point_count",0)/6000,4),
            "rgb_mae":round(float(np.abs(np.asarray(cropped,dtype=np.int16)-
                                           np.asarray(roi,dtype=np.int16)).mean()),4),
            "alpha_pixels":int((arr[:,155:305,3]>0).sum()),
            "roi_gate":"PASS"
        }
        pictures.append(cropped)
    with Image.open(frozen_a) as im:
        frozen=im.convert("RGB")
    if frozen.size!=(150,240) or np.any(np.asarray(frozen)!=np.asarray(pictures[0])):
        raise ValueError("V28 baseline A differs from genuine V27 native scanline preview")
    names=["Original","A canvas8","B ROI8","C ROI6","D ROI8 skipwhite"]
    sheet([roi]+pictures,names,output/"comparison-full.png")
    sheet([roi]+pictures,names,output/"comparison-faces.png",top=True)
    roi.save(output/"original-source-roi.png")
    hashes={f.name:sha(f) for f in output.iterdir() if f.is_file()}
    report={"experiment":"ENGINE001_VISUAL_ROI_PALETTE_V28",
            "status":"OFFLINE_FIXED_PALETTE_COLOR_PLANS_NOT_GAME",
            "source_sha256":SOURCE_SHA,
            "baseline_v27_scanline_roi_sha256":sha(frozen_a),
            "roi":{"x":155,"y":0,"width":150,"height":240},
            "modes":saved,"derived_sha256":hashes,
            "not_tested":["real board CHALK","live game color painting","E5",
                          "actual >=99% fill / 3px leakage","human independent recognizability"]}
    (output/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(json.dumps({k:{n:v[n] for n in ("stroke_count","forecast_game_points","rgb_mae",
      "color_switch_count","visible_index_pixels")} for k,v in saved.items()},indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("source","frozen-a","output"):
        p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args()
    run(a.source,a.frozen_a,a.output)
