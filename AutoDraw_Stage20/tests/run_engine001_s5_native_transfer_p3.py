"""S5-TRANSFER-P3: full EZAL, real Egret tiled native readback, no resampling of ink."""
import argparse
import gzip
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

SOURCE = "data/generated_autodraw_plan/images_31_first/EZAL3k9ddfs.jpg"
SOURCE_SHA = "51a55d9591ac9fb8e9aed72f7ee8f4c1e4235916745eb3e0935f0625aa53c373"
PLANNER_BLOB = "a268ee57aa4eeebe1c17927495cb8d8905d0e38b"
W, H = 1235, 1920
CW, CH, HALO = 176, 300, 24
TW, TH = CW+2*HALO, CH+2*HALO
NX, NY = 8, 7
BX, BY = 466, 12
RENDERER = "real Egret 5.4.1 BoardPane/WebGLRenderer"
GEOM = dict(left=BX/3, top=BY/3, scale=2/3, width=TW, height=TH)
WHITE = np.array([255, 255, 255], dtype=np.uint8)


def require(test, message):
    if not test:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def array_sha(arr):
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf8"))


def bounds(row, col):
    x, y = col*CW, row*CH
    return x, y, min(W,x+CW), min(H,y+CH)


def tile_target(target, row, col):
    x,y,_,_ = bounds(row,col)
    ox,oy = x-HALO,y-HALO
    a,b,c,d = max(0,ox),max(0,oy),min(W,ox+TW),min(H,oy+TH)
    tile = np.full((TH,TW,3),255,np.uint8)
    tile[b-oy:d-oy,a-ox:c-ox] = target[b:d,a:c]
    return tile


def region(raw, row, col, rect):
    """Exact integer backing coordinates of a global source rectangle."""
    x,y,_,_ = bounds(row,col)
    a,b,c,d = rect
    sx,sy = BX+2*(a-x+HALO), BY+2*(b-y+HALO)
    ex,ey = sx+2*(c-a),sy+2*(d-b)
    require(BX<=sx<ex<=BX+2*TW and BY<=sy<ey<=BY+2*TH,
            "rectangle outside tile backing")
    return raw[sy:ey,sx:ex]


def white_rgb(raw):
    img = Image.fromarray(raw,"RGBA")
    bg = Image.new("RGBA",img.size,"white")
    bg.alpha_composite(img)
    return np.asarray(bg.convert("RGB"))


def native_row(row, out):
    import engine001_s5_native_brush_overlap as physical
    import run_engine001_s5_wv_full_native as native
    root = native.binding.ROOT
    require(digest(root/SOURCE)==SOURCE_SHA,"source SHA drift")
    require(blob(Path(physical.__file__))==PLANNER_BLOB,"accepted planner drift")
    out.mkdir(parents=True,exist_ok=False)
    source = out/"source"
    native.binding.pipeline.run(root,Path(SOURCE),source,palette_only=True)
    image = np.asarray(Image.open(source/"palette-8.png").convert("RGBA"))
    require(image.shape==(H,W,4),"source preparation resized")
    require(Image.open(source/"01-original.png").size==(W,H),"original size drift")
    target = np.where((image[:,:,3]==255)[:,:,None],image[:,:,:3],255).astype(np.uint8)
    palette = np.unique(target.reshape(-1,3),axis=0)
    require(1<=len(palette)<=9,"palette drift")
    Image.fromarray(target,"RGB").save(out/"prepared.png")
    native.OUT=out
    tiles=[]
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        require(not native.render(driver,"blank",[])[:,:,3].any(),"nonblank control")
        control=[native.stroke(native.segment(200,100,12,0),4,0,0)]
        before=native.render(driver,"reference-original",control)
        driver.execute_script(native.full_fixture())
        require(np.array_equal(before,native.render(driver,"reference-expanded",control)),
                "native fixture changed brush")
        proof=physical.native_footprints(driver)
        require(proof["probes"]==80 and proof["smooth"] is False,"invalid native proof")
        write_json(out/"egret-physical-footprints.json",proof)
        for col in range(NX):
            name=f"tile-{row}-{col}"
            tile=tile_target(target,row,col)
            paths,params=physical.plan_same_color_overlap(tile,GEOM,proof)
            require(all(p["width"]==1 and p["colorRgb"]!=0xffffff for p in paths),
                    "width/white drift")
            require(len(set(p["colorRgb"] for p in paths))<=8,"stroke palette drift")
            plan=out/(name+"-plan.json.gz")
            with gzip.open(plan,"wt",encoding="utf8") as f:
                json.dump(paths,f,separators=(",",":"))
            raw=native.render(driver,name,paths)
            require(raw.shape==(720,1380,4),"invalid native frame")
            if not paths:
                require(not raw[:,:,3].any(),"empty tile not blank")
            png=out/(name+".png")
            # Preserve exact native RGBA, not a generated brush representation.
            require(np.array_equal(np.asarray(Image.open(png).convert("RGBA")),raw),
                    "saved native RGBA mismatch")
            meta=out/(name+".json")
            record=dict(row=row,col=col,core=list(bounds(row,col)),geometry=GEOM,
                        target_sha256=array_sha(tile),raw_sha256=digest(png),
                        plan_sha256=digest(plan),meta_sha256=digest(meta),
                        strokes=len(paths),planner=params)
            tiles.append(record)
            print("P3_TILE "+json.dumps(record,separators=(",",":")),flush=True)
    write_json(out/"row.json",dict(schema="ENGINE001_S5_P3_ROW_V1",row=row,
        source=SOURCE,source_sha256=SOURCE_SHA,target_sha256=array_sha(target),
        source_size=[W,H],planner_blob=PLANNER_BLOB,renderer=RENDERER,
        mode="normal",smooth=False,footprints_sha256=digest(out/"egret-physical-footprints.json"),
        sha=os.environ["GITHUB_SHA"],run=os.environ["GITHUB_RUN_ID"],tiles=tiles))


def measure(raw,target):
    """All backing pixels; stripwise nearest global palette, no RGB proxy for brush."""
    palette=np.unique(np.vstack((target.reshape(-1,3),WHITE[None,:])),axis=0)
    counts=dict(backing_pixels=0,foreground_pixels=0,nearest_correct=0,
        foreground_correct=0,fg_nearest_white_wrong=0,fg_alpha0=0,
        fg_alpha24=0,fg_gap_union=0,ink_on_white_alpha24=0)
    abs_sum=0
    for y in range(0,H,64):
        t=target[y:y+64]
        want=np.repeat(np.repeat(t,2,axis=0),2,axis=1)
        a=raw[2*y:2*(y+len(t))]
        arr=white_rgb(a).astype(np.int32)
        nearest=palette[np.stack([np.square(arr-c).sum(axis=2)
                                for c in palette],axis=-1).argmin(axis=-1)]
        fg=np.any(want!=255,axis=2)
        correct=np.all(nearest==want,axis=2)
        wrong=np.all(nearest==255,axis=2)
        alpha=a[:,:,3]
        masks=dict(foreground_pixels=fg,nearest_correct=correct,
            foreground_correct=fg&correct,fg_nearest_white_wrong=fg&wrong,
            fg_alpha0=fg&(alpha==0),fg_alpha24=fg&(alpha<=24),
            fg_gap_union=fg&(wrong|(alpha<=24)),ink_on_white_alpha24=(~fg)&(alpha>24))
        counts["backing_pixels"]+=fg.size
        for key,mask in masks.items():
            counts[key]+=int(mask.sum())
        abs_sum+=int(np.abs(arr-want).sum())
    counts["rgb_mae"]=abs_sum/(counts["backing_pixels"]*3)
    return counts


def assemble(rows_dir,out):
    out.mkdir(parents=True,exist_ok=False)
    records={}
    target=None
    for row in range(NY):
        folder=rows_dir/f"S5-P3-row-{row}"
        m=read_json(folder/"row.json")
        require(m["schema"]=="ENGINE001_S5_P3_ROW_V1" and m["row"]==row
            and m["sha"]==os.environ["GITHUB_SHA"] and m["run"]==os.environ["GITHUB_RUN_ID"]
            and m["source"]==SOURCE and m["source_sha256"]==SOURCE_SHA
            and m["source_size"]==[W,H] and m["planner_blob"]==PLANNER_BLOB
            and m["renderer"]==RENDERER and m["mode"]=="normal" and m["smooth"] is False,
            "row provenance mismatch")
        t=np.asarray(Image.open(folder/"prepared.png").convert("RGB"))
        require(t.shape==(H,W,3) and array_sha(t)==m["target_sha256"],"target hash mismatch")
        if target is None:
            target=t.copy()
        require(np.array_equal(t,target),"different full-source palettes")
        proof=read_json(folder/"egret-physical-footprints.json")
        require(digest(folder/"egret-physical-footprints.json")==m["footprints_sha256"]
                and proof["probes"]==80 and proof["renderer"]==RENDERER
                and proof["mode"]=="normal" and proof["smooth"] is False,"proof mismatch")
        require(len(m["tiles"])==NX,"missing tiles")
        for rec in m["tiles"]:
            col=rec["col"]
            key=(row,col)
            require(rec["row"]==row and 0<=col<NX and key not in records
                and rec["core"]==list(bounds(row,col)) and rec["geometry"]==GEOM
                and rec["target_sha256"]==array_sha(tile_target(target,row,col)),
                "tile geometry/target mismatch")
            name=f"tile-{row}-{col}"
            png=folder/(name+".png")
            plan=folder/(name+"-plan.json.gz")
            meta=folder/(name+".json")
            require(digest(png)==rec["raw_sha256"] and digest(plan)==rec["plan_sha256"]
                and digest(meta)==rec["meta_sha256"],"tile artifact hash mismatch")
            md=read_json(meta)
            require(md["renderer"]==RENDERER and md["sceneDiagnostics"]["stageAttached"],
                "native scene not attached")
            with gzip.open(plan,"rt",encoding="utf8") as f:
                paths=json.load(f)
            require(len(paths)==rec["strokes"] and all(p["width"]==1 and p["colorRgb"]!=0xffffff
                    for p in paths) and len(set(p["colorRgb"] for p in paths))<=8,
                    "plan width/count/colors invalid")
            if paths:
                require(md["mode"]=="normal" and md["strokeCount"]==len(paths)
                    and md["syntheticAcceptedVerticesNotChalk"]==sum(len(p["points"]) for p in paths),
                    "native mode/count mismatch")
            records[key]=(png,rec)
    require(len(records)==NX*NY,"not all tiles present")

    @lru_cache(maxsize=4)
    def load(row,col):
        a=np.asarray(Image.open(records[row,col][0]).convert("RGBA"))
        require(a.shape==(720,1380,4),"raw PNG size mismatch")
        if not records[row,col][1]["strokes"]:
            require(not a[:,:,3].any(),"empty tile ink")
        return a

    mosaic=np.zeros((2*H,2*W,4),np.uint8)
    cover=np.zeros((2*H,2*W),np.uint8)
    for row,col in sorted(records):
        x,y,x1,y1=bounds(row,col)
        crop=region(load(row,col),row,col,(x,y,x1,y1))
        mosaic[2*y:2*y1,2*x:2*x1]=crop
        cover[2*y:2*y1,2*x:2*x1]+=1
    require(np.all(cover==1),"incomplete/overlapping mosaic")
    seams=[]
    for row,col in sorted(records):
        x,y,x1,y1=bounds(row,col)
        for dr,dc,axis in ((0,1,"vertical"),(1,0,"horizontal")):
            other=(row+dr,col+dc)
            if other not in records:
                continue
            rect=(max(0,x1-8),y,min(W,x1+8),y1) if dc else (x,max(0,y1-8),x1,min(H,y1+8))
            a=region(load(row,col),row,col,rect)
            b=region(load(*other),*other,rect)
            seams.append(dict(axis=axis,first=[row,col],second=list(other),rect=list(rect),
                pixels=a.shape[0]*a.shape[1],rgba_different=int(np.any(a!=b,axis=2).sum()),
                rgb_abs_sum=int(np.abs(white_rgb(a).astype(np.int32)-white_rgb(b)).sum())))
    require(len(seams)==NY*(NX-1)+NX*(NY-1),"missing internal seam")
    summary={}
    for axis in ("vertical","horizontal"):
        s=[v for v in seams if v["axis"]==axis]
        pixels=sum(v["pixels"] for v in s)
        summary[axis]=dict(count=len(s),backing_pixels=pixels,
            rgba_different=sum(v["rgba_different"] for v in s),
            rgb_mae=sum(v["rgb_abs_sum"] for v in s)/(3*pixels))
    Image.fromarray(mosaic,"RGBA").save(out/"actual-egret-mosaic-rgba.png")
    rgb=white_rgb(mosaic)
    Image.fromarray(rgb,"RGB").save(out/"actual-egret-mosaic.png")
    Image.fromarray(target,"RGB").save(out/"prepared.png")
    original=Image.open(rows_dir/"S5-P3-row-0"/"source"/"01-original.png").convert("RGB")
    require(original.size==(W,H),"original size mismatch")
    original.save(out/"original.png")
    panel=Image.new("RGB",(6*W,2*H))
    panel.paste(original.resize((2*W,2*H),Image.Resampling.NEAREST),(0,0))
    panel.paste(Image.fromarray(target).resize((2*W,2*H),Image.Resampling.NEAREST),(2*W,0))
    panel.paste(Image.fromarray(rgb),(4*W,0))
    panel.save(out/"original-prepared-actual-egret.png")
    result=dict(schema="ENGINE001_S5_TRANSFER_P3_V1",sha=os.environ["GITHUB_SHA"],
        run=os.environ["GITHUB_RUN_ID"],source=SOURCE,source_sha256=SOURCE_SHA,
        target_sha256=array_sha(target),source_size=[W,H],native_mosaic_size=[2*W,2*H],
        tiles=len(records),coverage_exact_once=True,strokes=sum(rec["strokes"] for _,rec in records.values()),
        renderer=RENDERER,mode="normal",smooth=False,brush_widths_used=[1],
        planner_blob=PLANNER_BLOB,metrics=measure(mosaic,target),seam_summary=summary,seams=seams,
        mosaic_rgba_sha256=digest(out/"actual-egret-mosaic-rgba.png"),
        human_visual_review="PENDING",exact_CHALK="NOT_RUN",independent_E5="NOT_RUN",
        single_native_board=False)
    write_json(out/"p3-results.json",result)
    print("P3_RESULT "+json.dumps(result,separators=(",",":")),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--row",type=int,choices=range(NY))
    p.add_argument("--assemble",type=Path)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    require((a.row is None)!=(a.assemble is None),"select row OR assembly")
    if a.row is not None:
        native_row(a.row,a.out)
    else:
        assemble(a.assemble,a.out)
