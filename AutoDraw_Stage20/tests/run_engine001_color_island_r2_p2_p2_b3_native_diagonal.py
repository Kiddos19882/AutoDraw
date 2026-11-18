#!/usr/bin/env python3
"""ENGINE-001 B3: native archived Egret source-only diagonal pairs; no game CHALK."""
from __future__ import annotations
import argparse,hashlib,io,json,os,platform
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from skimage import measure
from run_engine001_palette32_region_study import read_palette
from run_engine001_color_island_r2_p2_p2_b1_p0_game32 import git_blob,valid_zip
from run_engine001_complex_holdout_v5 import native_batch

EXP="ENGINE001_COLOR_ISLAND_R2_P2_P2_B3_DIAGONAL_NATIVE_FOOTPRINT"
B1_SHA="5998d4c9cc4e9f20eda637ebd0192ba5f38e824d22946fea6f3363dbfcbed916"
B1_REPORT_SHA="c50949662571307892f065576adae3c27201141e4c59eecd7273a71c95356cb4"
B1_CI_SHA="774dedb4f6a7cc51d91cf6b2567e14d38bd9d7f8"
M1_SHA="8bedc496bf01cf7205ecc8ceb7be8eb0f68b751b11c53ea67dbdd3982c7fe583"
M1_REPORT_SHA="89e4135ecd71820e21394751bb4a11f9a17b01edcddcfa6f1bd1f538f8a16969"
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
PALETTE_BLOB="461b5f3725b9b79888ad36e807b3cf4c9e445e98"
RENDERER_BLOB="74ad4d8ad162bb04bf8f1ff94860ef673c02512b"
CATEGORIES=("BOTH_FOREIGN","MIXED","BOTH_WHITE")
WIDTHS=(2,4)
EXPECTED_POPULATION={"BOTH_FOREIGN":13,"MIXED":10,"BOTH_WHITE":24}
H,W=240,150
ROI_X0=155
ALPHAS=(24,128)

def sha(data):return hashlib.sha256(data).hexdigest()

def load_inputs(source_path,palette_path,renderer_path,b1_zip,m1_zip):
    if sha(source_path.read_bytes())!=SOURCE_SHA:raise ValueError("BLOCKED_B3_SOURCE_SHA")
    if git_blob(palette_path.read_bytes())!=PALETTE_BLOB:raise ValueError("BLOCKED_B3_PALETTE_BLOB")
    if git_blob(renderer_path.read_bytes())!=RENDERER_BLOB:raise ValueError("BLOCKED_B3_RENDERER_BLOB")
    palette=read_palette(palette_path)
    with valid_zip(b1_zip,B1_SHA) as b,valid_zip(m1_zip,M1_SHA) as m:
        report=b.read("report.json")
        if sha(report)!=B1_REPORT_SHA:raise ValueError("BLOCKED_B3_B1_REPORT")
        meta=json.loads(report)
        if meta.get("github_sha")!=B1_CI_SHA or str(meta.get("github_run_id"))!="44230985963":
            raise ValueError("BLOCKED_B3_B1_RUN_BINDING")
        label_bytes=b.read("B1_CHROMA12_SPATIAL_indices.png")
        if sha(label_bytes)!=meta["file_sha256"]["B1_CHROMA12_SPATIAL_indices.png"]:
            raise ValueError("BLOCKED_B3_B1_INDEX_SHA")
        labels=np.asarray(Image.open(io.BytesIO(label_bytes)).convert("L"),dtype=np.uint8)
        mr=m.read("report.json")
        if sha(mr)!=M1_REPORT_SHA:raise ValueError("BLOCKED_B3_M1_REPORT")
        original=json.loads(mr)
        protect_bytes=m.read("source_protected_union.png")
        if sha(protect_bytes)!=original["file_sha256"]["source_protected_union.png"]:
            raise ValueError("BLOCKED_B3_M1_MASK_SHA")
        protected=np.asarray(Image.open(io.BytesIO(protect_bytes)).convert("L"))>0
    if (labels.shape!=(H,W) or protected.shape!=(H,W) or labels.max()>31 or
            int(protected.sum())!=7947 or palette.shape!=(32,3)):
        raise ValueError("BLOCKED_B3_INPUT_SHAPE")
    return labels,protected,palette

def pair_population(labels,protected):
    if (labels.shape!=(H,W) or protected.shape!=(H,W) or
        labels.dtype!=np.uint8 or protected.dtype!=np.bool_):
        raise ValueError("BLOCKED_B3_PAIR_INPUT")
    cc=np.zeros((H,W),dtype=np.int32)
    for k in range(32):
        if k==30:continue
        binary=labels==k
        if binary.any():
            owners=measure.label(binary,connectivity=1).astype(np.int32)
            cc[binary]=owners[binary]
    categories={name:[] for name in CATEGORIES}
    for y in range(H-1):
        for x in range(W-1):
            if protected[y:y+2,x:x+2].any():continue
            for orientation in (0,1):
                if orientation==0:
                    a=(y,x);b=(y+1,x+1); flank=((y,x+1),(y+1,x))
                else:
                    a=(y,x+1);b=(y+1,x);flank=((y,x),(y+1,x+1))
                owner=int(labels[a])
                if owner==30 or owner!=int(labels[b]) or cc[a]==cc[b]:continue
                flank_colors=[int(labels[pos]) for pos in flank]
                if any(k==owner for k in flank_colors):
                    raise AssertionError("BAD_B3_DIAGONAL_IS_NOT_4_DISCONNECTED")
                category=("BOTH_WHITE" if all(k==30 for k in flank_colors) else
                          "BOTH_FOREIGN" if all(k!=30 for k in flank_colors) else
                          "MIXED")
                categories[category].append({
                    "category":category,"owner":owner,"row":y,"col":x,
                    "orientation":orientation,"a":[a[1],a[0]],"b":[b[1],b[0]],
                    "flank_indices":flank_colors})
    return categories

def frozen_selection(pop):
    selected={}
    for category in CATEGORIES:
        ordered=sorted(pop[category],key=lambda p:(p["row"],p["col"],p["orientation"],p["owner"]))
        colors=set(); chosen=[]
        for p in ordered:
            if p["owner"] in colors:continue
            colors.add(p["owner"]);chosen.append(dict(p))
            if len(chosen)==2:break
        selected[category]=chosen
    return selected

def stroke(pair,width,palette,case_id):
    if width not in WIDTHS:raise ValueError("BLOCKED_B3_WIDTH")
    owner=int(pair["owner"])
    if not 0<=owner<32 or owner==30 or palette.shape!=(32,3):raise ValueError("BLOCKED_B3_OWNER")
    a,b=pair["a"],pair["b"]
    if (len(a)!=2 or len(b)!=2 or
        abs(int(a[0])-int(b[0]))!=1 or abs(int(a[1])-int(b[1]))!=1 or
        not (0<=a[0]<W and 0<=b[0]<W and 0<=a[1]<H and 0<=b[1]<H)):
        raise ValueError("BLOCKED_B3_DIAGONAL_COORDS")
    r,g,bl=[int(c) for c in palette[owner]]
    return {"strokeId":f"icon-{case_id}","colorIndex":owner,
            "colorRgb":(r<<16)|(g<<8)|bl,"width":int(width),
            "points":[{"x":ROI_X0+int(a[0]),"y":int(a[1])},
                      {"x":ROI_X0+int(b[0]),"y":int(b[1])}]}

def analyse_alpha(rgba,labels,owner,pair):
    if rgba.shape!=(720,1380,4) or rgba.dtype!=np.uint8:
        raise ValueError("BLOCKED_B3_NATIVE_PNG_SHAPE")
    if labels.shape!=(H,W) or not (0<=owner<32) or owner==30:raise ValueError("BLOCKED_B3_ALPHA_INDEX")
    target_board=np.full((240,460),-1,np.int16)
    target_board[:,ROI_X0:ROI_X0+W]=labels.astype(np.int16)
    backing=np.repeat(np.repeat(target_board,3,0),3,1)
    owner_mask=backing==owner
    # Native raster not ideal capsule. Distances are only post-capture diagnostics.
    distances=distance_transform_edt(~owner_mask)
    stats={}
    alpha=rgba[:,:,3]
    for threshold in ALPHAS:
        ink=alpha>=threshold
        data={
           "ink_pixels":int(ink.sum()),"own_pixels":int((ink&owner_mask).sum()),
           "foreign_color_pixels":int((ink&(backing>=0)&(backing!=30)&(backing!=owner)).sum()),
           "white_background_pixels":int((ink&(backing==30)).sum()),
           "outside_source_ROI_pixels":int((ink&(backing<0)).sum()),
           "beyond_3logical_from_owner_pixels":int((ink&(distances>9)).sum())
        }
        end_covered=[]
        for point in (pair["a"],pair["b"]):
            xx=(ROI_X0+point[0])*3; yy=point[1]*3
            end_covered.append(bool(np.any(ink[yy:yy+3,xx:xx+3])))
        data["both_diagonal_endpoint_cells_covered"]=all(end_covered)
        data["endpoint_cells_covered"]=end_covered
        stats[str(threshold)]=data
    gate=bool(stats["128"]["both_diagonal_endpoint_cells_covered"] and
              stats["24"]["foreign_color_pixels"]==0 and
              stats["24"]["beyond_3logical_from_owner_pixels"]==0 and
              stats["24"]["outside_source_ROI_pixels"]==0)
    return {"native_alpha":stats,"safe_join_gate":gate,
            "status":"SAFE_ON_THIS_ISOLATED_FIXTURE" if gate else "UNSAFE_OR_UNCOVERED_ISOLATED_FIXTURE"}

def run(workspace,source,palette_path,renderer,b1_zip,m1_zip,output):
    if output.exists():raise ValueError("BLOCKED_B3_OVERWRITE")
    labels,protected,palette=load_inputs(source,palette_path,renderer,b1_zip,m1_zip)
    pop=pair_population(labels,protected)
    counts={name:len(pop[name]) for name in CATEGORIES}
    if counts!=EXPECTED_POPULATION:raise ValueError(f"BLOCKED_B3_SOURCE_PAIR_POPULATION {counts}")
    selected=frozen_selection(pop)
    if any(not selected[name] for name in CATEGORIES):raise ValueError("BLOCKED_B3_NO_CATEGORY")
    output.mkdir(parents=True)
    (output/"selected_frozen_diagonal_pairs.json").write_text(json.dumps(
        {"population":counts,"selection":selected},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    per_batch={};case_serial=0
    for category in CATEGORIES:
        for width in WIDTHS:
            case_serial+=1
            name=f"{category.lower()}-width{width}"
            batch=output/name
            batch.mkdir()
            selected_pairs=selected[category]
            strokes=[stroke(p,width,palette,case_serial*100+i) for i,p in enumerate(selected_pairs)]
            (batch/"strokes.json").write_text(json.dumps(strokes,indent=2)+"\n")
            # Native rendering only (actual archived Egret Stage/BoardPane WebGL).
            images,info,manifest=native_batch(workspace,name,strokes,batch)
            cases={}
            for p in selected_pairs:
                owner=p["owner"]
                key=f"color-{owner}"
                if key not in images:raise ValueError("BLOCKED_B3_NATIVE_COLOR_MISSING")
                cases[str(owner)]={
                    "source_pair":p,"native_result":analyse_alpha(images[key],labels,owner,p),
                    "scene":info[key]}
            if "composite" not in images:raise ValueError("BLOCKED_B3_NATIVE_COMPOSITE_MISSING")
            per_batch[name]={"category":category,"width":width,"strokes":len(strokes),
                "synthetic_vertices_NOT_CHALK":sum(len(s["points"]) for s in strokes),
                "cases":cases,"renderer_manifest":manifest}
    hashes={str(p.relative_to(output)).replace("\\","/"):sha(p.read_bytes()) for p in sorted(output.rglob("*")) if p.is_file()}
    total=sum(len(v["cases"]) for v in per_batch.values())
    gate_summary={k:sum(d["native_result"]["safe_join_gate"] for d in batch["cases"].values())
                  for k,batch in per_batch.items()}
    report={"experiment":EXP,"status":"ISOLATED_NATIVE_CAPTURE_NOT_GAME",
        "github_sha":os.environ.get("GITHUB_SHA"),"github_run_id":os.environ.get("GITHUB_RUN_ID"),
        "source_sha256":SOURCE_SHA,"palette_git_blob":PALETTE_BLOB,
        "renderer_js_git_blob":RENDERER_BLOB,"b1_zip_sha256":B1_SHA,"m1_zip_sha256":M1_SHA,
        "protected_original_pixels":int(protected.sum()),"population_by_category":counts,
        "selected":selected,"batches":per_batch,"native_case_count":total,
        "native_safe_gate_counts":gate_summary,"file_sha256":hashes,
        "native_original_boardpane":True,"native_game_play_E4":"NOT_RUN","independent_E5":"NOT_RUN",
        "real_game_CHALK":None,"production_accepted":False,"human_visual":"PENDING",
        "version":{"python":platform.python_version(),"numpy":np.__version__}}
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--palette",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--b1-archive",type=Path,required=True)
    p.add_argument("--m1-archive",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=run(a.workspace.resolve(),a.source,a.palette,a.renderer,a.b1_archive,a.m1_archive,a.output)
    print(json.dumps({"cases":r["native_case_count"],"sampled":r["native_safe_gate_counts"]}))
