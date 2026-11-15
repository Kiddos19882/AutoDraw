#!/usr/bin/env python3
"""V27 diagnostic of existing color plans, keeps ROI leakage FAIL for each mode."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/"source"/"preparation"))
from color_scanline import build_color_scanline_plan,render_color_scanline_preview,validate_color_scanline_plan
from geometry_color_plan import build_geometry_color_plan,render_geometry_color_preview,validate_geometry_color_plan

SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
ANILINES_SHA="2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b"

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(source):
    if sha(source)!=SOURCE_SHA or Path(source).stat().st_size!=97308:
        raise ValueError("V26 original source SHA/size mismatch")
    with Image.open(source) as image:
        if image.size!=(200,320):raise ValueError("V26 original source dimensions mismatch")
        roi=image.convert("RGB").resize((150,240),Image.Resampling.LANCZOS)
    canvas=Image.new("RGB",(460,240),(255,255,255))
    canvas.paste(roi,(155,0))
    quant=canvas.quantize(colors=8,method=Image.Quantize.MEDIANCUT,
                          dither=Image.Dither.NONE)
    labels=np.asarray(quant,dtype=np.int32)
    raw_palette=quant.getpalette()
    used=sorted({int(x) for x in np.unique(labels)})
    if len(used)!=8:raise ValueError("V26 expected exactly eight frozen quantized classes")
    colors=[]
    for label in used:
        rgb=tuple(raw_palette[label*3:label*3+3])
        if len(rgb)!=3:raise ValueError("Truncated quantization palette")
        colors.append({"id":f"v26-class-{label}","name":f"Class {label}",
                       "rgb":list(rgb),"hex":"#"+''.join(f"{c:02X}" for c in rgb)})
    if len(set(tuple(x["rgb"]) for x in colors))!=8:
        raise ValueError("Duplicate frozen palette colors")
    mapping={label:i for i,label in enumerate(used)}
    index_map=np.full((240,460),-1,dtype=np.int32)
    for label,i in mapping.items():
        index_map[:,155:305][labels[:,155:305]==label]=i
    if np.any(index_map[:,:155]!=-1) or np.any(index_map[:,305:]!=-1):
        raise ValueError("V26 color plan outside source ROI")
    if np.any(index_map[:,155:305]<0):raise ValueError("Unassigned source ROI class")
    return roi,index_map,colors,canvas

def draw_sheet(items,labels,out,crop=None):
    if crop is not None:items=[im.crop(crop) for im in items]
    w,h=items[0].size
    if any(im.size!=(w,h) for im in items):raise ValueError("Comparison canvas mismatch")
    scale=3;pad=14;heading=42
    block=w*scale
    image=Image.new("RGB",(len(items)*block+(len(items)+1)*pad,h*scale+heading+pad),"#e8ecf0")
    d=ImageDraw.Draw(image)
    for idx,(im,label) in enumerate(zip(items,labels)):
        x=pad+idx*(block+pad)
        d.text((x+2,12),label,fill="#171717")
        image.paste(im.resize((w*scale,h*scale),Image.Resampling.NEAREST),(x,heading))
    image.save(out)

def run(source,ani_file,v18_roi,v20_panel,output):
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError("Refuse overwrite")
    roi,idx,colors,canvas=prepare(source)
    if sha(ani_file)!=ANILINES_SHA:raise ValueError("Frozen AniLines SHA differs")
    ani=Image.open(ani_file).convert("L")
    if ani.size!=(200,320):raise ValueError("AniLines dimensions")
    ani=ani.resize((150,240),Image.Resampling.NEAREST).convert("RGB")
    b=Image.open(v18_roi).convert("RGB")
    panel=Image.open(v20_panel).convert("RGB")
    if b.size!=(150,240) or panel.size!=(450,240):raise ValueError("Old comparison size mismatch")
    v20=panel.crop((300,0,450,240))
    output.mkdir(parents=True,exist_ok=True)
    plans={}
    previews={}
    for mode in ("scanline","contour","skeleton"):
        if mode=="scanline":
            plan=build_color_scanline_plan(idx,colors,source_name="wV6VeZI9S1Y.png",
                                           row_step_px=1,row_offset_px=0)
            validate_color_scanline_plan(plan)
            image=render_color_scanline_preview(plan,max_dimension=1600)
        else:
            plan=build_geometry_color_plan(idx,colors,mode=mode,
                                            simplify_tolerance_px=0.8,
                                            min_component_area=1,color_grouping=True,
                                            canvas_size=(460,240),
                                            source_name="wV6VeZI9S1Y.png")
            validate_geometry_color_plan(plan)
            image=render_geometry_color_preview(plan,max_dimension=1600)
        if image.size!=(460,240):raise ValueError("Generated preview not logical canvas")
        rgba=np.asarray(image.convert("RGBA"))
        left=int(np.count_nonzero(rgba[:,:155,3]))
        right=int(np.count_nonzero(rgba[:,305:,3]))
        outside_mask=np.zeros((240,460),bool)
        outside_mask[:,:155]=rgba[:,:155,3]>0
        outside_mask[:,305:]=rgba[:,305:,3]>0
        ys,xs=np.where(outside_mask)
        violation_bbox=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())] if len(xs) else None
        roi_gate="PASS" if left+right==0 else "FAIL"
        preview=Image.new("RGB",(460,240),"white")
        preview.paste(image,(0,0),image)
        crop=preview.crop((155,0,305,240))
        crop.save(output/(mode+"-roi.png"))
        image.save(output/(mode+"-full-alpha.png"))
        p=output/(mode+"-plan.json")
        p.write_text(json.dumps(plan,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
        d=np.asarray(crop,dtype=np.int16)
        target=np.asarray(roi,dtype=np.int16)
        # Diagnostic only, NOT a perceptual recognition score.
        mae=float(np.abs(d-target).mean())
        plans[mode]={"stroke_count":len(plan["strokes"]),
                     "point_vertices":sum(len(x["points"]) for x in plan["strokes"]),
                     "source_rgb_mae":round(mae,4),
                     "preview_alpha_pixel_count":int(np.count_nonzero(rgba[:,155:305,3])),
                     "roi_gate":roi_gate,
                     "outside_source_roi_alpha_pixels":left+right,
                     "outside_left_alpha_pixels":left,
                     "outside_right_alpha_pixels":right,
                     "outside_alpha_bbox_logical":violation_bbox,
                     "summary":plan.get("summary",{})}
        previews[mode]=crop
    labels=["Original RGB","AniLines V14","V18-B","V20","Color scanline","Color contour","Color skeleton"]
    items=[roi,ani,b,v20]+[previews[k] for k in ("scanline","contour","skeleton")]
    draw_sheet(items,labels,output/"comparison-full.png")
    draw_sheet(items,labels,output/"comparison-faces.png",crop=(0,0,150,125))
    roi.save(output/"source-roi.png")
    hashes={f.name:sha(f) for f in sorted(output.iterdir()) if f.is_file()}
    report={"experiment":"ENGINE001_VISUAL_COLOR_DIAGNOSTIC_V27",
            "status":"OFFLINE_DIAGNOSTIC_ROI_GATE_RECORDED_NOT_GAME",
            "source_sha256":SOURCE_SHA,"anilines_sha256":ANILINES_SHA,
            "quantization":"Pillow RGB 8-color MEDIANCUT no dither of white 460x240 canvas; 150x240 source ROI",
            "palette":colors,"roi":{"x":155,"y":0,"width":150,"height":240},
            "modes":plans,"roi_gate_overall":"PASS" if all(v["roi_gate"]=="PASS" for v in plans.values()) else "FAIL",
            "artifacts_sha256":hashes,
            "no_game_chalk":True,"not_tested":["native Egret color painting","game run","live CHALK",
              "recognition validated by observers","actual >=99% coverage and <=3 logical px leakage"]}
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:{q:plans[k][q] for q in ("stroke_count","point_vertices","source_rgb_mae",
      "preview_alpha_pixel_count")} for k in plans},indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for arg in ("source","anilines","v18-roi","v20-panel","output"):
        p.add_argument("--"+arg,required=True,type=Path)
    a=p.parse_args()
    run(a.source,a.anilines,a.v18_roi,a.v20_panel,a.output)
