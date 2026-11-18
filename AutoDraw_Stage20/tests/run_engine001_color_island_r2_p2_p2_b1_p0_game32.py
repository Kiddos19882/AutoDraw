#!/usr/bin/env python3
"""ENGINE-001 R2-P2-P2-B1: source-supported 32-swatch diagnostic, not game fill."""
from __future__ import annotations
import argparse, hashlib, io, json, os, platform, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage import color, filters, measure
import skimage
from run_engine001_palette32_region_study import read_palette
from run_engine001_rgb_visual_mvp_p0 import composite

EXPERIMENT="ENGINE001_COLOR_ISLAND_R2_P2_P2_B1_P0_GAME32_SOURCE_SUPPORT"
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
PALETTE_BLOB="461b5f3725b9b79888ad36e807b3cf4c9e445e98"
P0_SHA="8edf928b96a5af56bfc91afd753affcbbfbcaaf821b4e372457eaf9128930536"
P0_CI_SHA="b0b134d98c7ed7093dc61fcf02e0ba87e3f1e3c2"
M1_SHA="8bedc496bf01cf7205ecc8ceb7be8eb0f68b751b11c53ea67dbdd3982c7fe583"
M1_REPORT_SHA="89e4135ecd71820e21394751bb4a11f9a17b01edcddcfa6f1bd1f538f8a16969"
V44_SHA="43cb8e14a7e387b26772612ac06d1c7c6f176b8bd0c2d41e8945042fc80304a1"
V44_DETAIL_SHA="0145975e4578bc86c1e4feb44d5ff93ecd486d576faf97626e1267a5c12b0275"
V44_PLAN_SHA="9db4dda0661ea529547e91a09dcae38b27043dad57383fb483b945f0de08496a"
ROIS={
"female_face_eyes": (26,34,85,100), "male_face_eyes": (72,14,123,92),
"bow_hair": (10,26,70,100), "hands_orange": (31,125,115,165),
"blouse_buttons": (24,92,105,147), "skirt_hem": (18,153,118,219)}
CANDIDATES=("G32_FROZEN","P0_NEAREST32","B1_CHROMA12","B1_CHROMA20","B1_CHROMA12_SPATIAL")

def digest(b): return hashlib.sha256(b).hexdigest()
def git_blob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def valid_zip(p,expected):
    b=Path(p).read_bytes()
    if digest(b)!=expected:raise ValueError("BLOCKED_ARCHIVE_SHA")
    z=zipfile.ZipFile(io.BytesIO(b))
    if z.testzip() is not None:raise ValueError("BLOCKED_ARCHIVE_CRC")
    return z
def png(z,name):
    return np.asarray(Image.open(io.BytesIO(z.read(name))).convert("RGB"))
def pinned_inputs(p0_path,m1_path,v44_path,palette_path,source_path):
    source_bytes=source_path.read_bytes()
    if digest(source_bytes)!=SOURCE_SHA:raise ValueError("BLOCKED_ORIGINAL_SOURCE_SHA")
    pal_bytes=palette_path.read_bytes()
    if git_blob(pal_bytes)!=PALETTE_BLOB:raise ValueError("BLOCKED_GAME_PALETTE_GIT_BLOB")
    palette=read_palette(palette_path)
    if palette.shape!=(32,3) or not np.array_equal(palette[30],[255,255,255]):
        raise ValueError("BLOCKED_PALETTE_SHAPE")
    with valid_zip(p0_path,P0_SHA) as p,valid_zip(m1_path,M1_SHA) as m,valid_zip(v44_path,V44_SHA) as v:
        rp=json.loads(p.read("report.json"))
        rm=json.loads(m.read("report.json"))
        if (rp.get("experiment")!="ENGINE001_RGB_VISUAL_MVP_P0_EDGE_AWARE_PREFILTER" or
            rp.get("github_sha")!=P0_CI_SHA or rp.get("source_sha256")!=SOURCE_SHA or
            rp.get("github_run_id")!="44229576245" and str(rp.get("github_run_id"))!="44229576245"):
            raise ValueError("BLOCKED_P0_REPORT_PROVENANCE")
        if digest(m.read("report.json"))!=M1_REPORT_SHA or rm.get("source_sha256")!=SOURCE_SHA:
            raise ValueError("BLOCKED_M1_REPORT")
        for n in ("ORIGINAL_RGB_RGB.png","BILATERAL_LOW_RGB.png"):
            if digest(p.read(n))!=rp.get("file_sha256",{}).get(n):
                raise ValueError("BLOCKED_P0_PNG_SHA")
        for n in ("original_RGB.png","source_protected_union.png","B0_frozen_G32.png"):
            if digest(m.read(n))!=rm.get("file_sha256",{}).get(n):
                raise ValueError("BLOCKED_M1_PNG_SHA")
        original=png(p,"ORIGINAL_RGB_RGB.png")
        filtered=png(p,"BILATERAL_LOW_RGB.png")
        m1_original=png(m,"original_RGB.png")
        protected=np.asarray(Image.open(io.BytesIO(m.read("source_protected_union.png"))).convert("L"))>0
        baseline=png(m,"B0_frozen_G32.png")
        if (original.shape!=(240,150,3) or filtered.shape!=original.shape or
            baseline.shape!=original.shape or protected.shape!=(240,150) or
            not np.array_equal(original,m1_original) or int(protected.sum())!=7947):
            raise ValueError("BLOCKED_P0_M1_SHAPE_OR_ORIGINAL_DRIFT")
        if digest(v.read("B/V44-B-color-100.png"))!=V44_DETAIL_SHA or digest(v.read("color-plans.json"))!=V44_PLAN_SHA:
            raise ValueError("BLOCKED_V44_PNG_OR_PLAN")
        vp=json.loads(v.read("color-plans.json"))
        entries=vp["plans"]["B"]["strokes"]
        if len(entries)!=2355:raise ValueError("BLOCKED_V44_STROKE_COUNT")
        detail=entries[-410:]
        if (len(detail)!=410 or
            sum(len(e["stroke"]["points"]) for e in detail)!=1792 or
            any(e["layer"]!="detail" or e["stroke"]["strokeId"]!=f"detail-v18-B-{i}" or
                e["stroke"]["width"]!=1 or e["stroke"]["colorIndex"]!=100
                for i,e in enumerate(detail))):
            raise ValueError("BLOCKED_V44_DETAIL_IDENTITY")
        contour=Image.open(io.BytesIO(v.read("B/V44-B-color-100.png"))).convert("RGBA")
        if contour.size!=(1380,720):raise ValueError("BLOCKED_V44_SIZE")
    lookup={tuple(int(x) for x in v):i for i,v in enumerate(palette)}
    try:
        b0=np.asarray([lookup[tuple(x)] for x in baseline.reshape(-1,3)],dtype=np.uint8).reshape(240,150)
    except KeyError as e:
        raise ValueError("BLOCKED_G32_OUTSIDE_PALETTE") from e
    return original,filtered,protected,palette,b0,contour

def get_de_table(source,palette):
    if source.shape!=(240,150,3) or palette.shape!=(32,3):
        raise ValueError("BLOCKED_DE_SHAPE")
    lab=color.rgb2lab(source/255.0)
    plab=color.rgb2lab(palette[None,:,:]/255.0)[0]
    dist=color.deltaE_ciede2000(lab[:,:,None,:],plab[None,None,:,:])
    if not np.isfinite(dist).all():raise ValueError("BLOCKED_NONFINITE_DE")
    return lab,plab,dist.astype(np.float32)

def palette_guard(lab,plab,delta_chroma):
    if delta_chroma not in (12,20):raise ValueError("BLOCKED_UNREGISTERED_GUARD")
    source_c=np.hypot(lab[:,:,1],lab[:,:,2])
    pal_c=np.hypot(plab[:,1],plab[:,2])
    allowed=(pal_c[None,None,:]<=source_c[:,:,None]+delta_chroma) & (
        plab[None,None,:,0]<=lab[:,:,None,0]+22)
    if not np.all(allowed.any(axis=2)):
        raise ValueError("BLOCKED_NO_VALID_SOURCE_SUPPORTED_SWATCH")
    return allowed

def choose_by_support(d,allowed):
    if d.shape!=(240,150,32) or allowed.shape!=d.shape:
        raise ValueError("BLOCKED_COLOR_MAP_SHAPE")
    if not allowed.any(axis=-1).all():
        raise ValueError("BLOCKED_EMPTY_VALID_CHOICES")
    return np.argmin(np.where(allowed,d,np.inf),axis=2).astype(np.uint8)

def spatial_smooth(labels,de,allowed,source_lab,protected,iterations=2):
    """Synchronous, original-source edge-aware Potts; no transfer through protected."""
    if (iterations!=2 or labels.shape!=(240,150) or de.shape!=(240,150,32) or
            allowed.shape!=de.shape or protected.shape!=labels.shape):
        raise ValueError("BLOCKED_UNREGISTERED_SPATIAL")
    if not np.all(allowed[np.arange(240)[:,None],np.arange(150)[None,:],labels]):
        raise ValueError("BLOCKED_INVALID_INITIAL_OWNER")
    initial=labels.copy()
    h,w=labels.shape
    for _ in range(2):
        energy=de.copy()
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            if dy==1:s0=(slice(None,-1),slice(None)); s1=(slice(1,None),slice(None))
            elif dy==-1:s0=(slice(1,None),slice(None));s1=(slice(None,-1),slice(None))
            elif dx==1:s0=(slice(None),slice(None,-1));s1=(slice(None),slice(1,None))
            else:s0=(slice(None),slice(1,None));s1=(slice(None),slice(None,-1))
            distance=color.deltaE_ciede2000(source_lab[s0],source_lab[s1])
            weak=(distance<=8)&(~protected[s0])&(~protected[s1])
            # Difference penalty strictly applies only to original RGB weak seams.
            energy[s0]+=2.5*weak[:,:,None]*(np.arange(32)[None,None,:]!=labels[s1][:,:,None])
        new=np.argmin(np.where(allowed,energy,np.inf),axis=2).astype(np.uint8)
        new[protected]=initial[protected]
        labels=new
    if not np.array_equal(labels[protected],initial[protected]):
        raise AssertionError("BLOCKED_PROTECTED_LABEL_CHANGED")
    return labels

def topology(idx):
    components=0;singles=0; small=0
    for k in range(32):
        if k==30:continue
        mask=(idx==k)
        if not mask.any():continue
        region=measure.label(mask,connectivity=1)
        counts=np.bincount(region.ravel())[1:]
        components+=len(counts)
        singles+=int((counts==1).sum())
        small+=int((counts<=4).sum())
    return {"nonwhite_components4":int(components),"nonwhite_singletons":int(singles),
            "nonwhite_area_le4_components":int(small),
            "palette_indices_used":[int(x) for x in np.unique(idx)],
            "nonwhite_pixels":int(np.count_nonzero(idx!=30))}

def source_metrics(source,plab,lab,idx,palette,source_edges,thr):
    candidate=palette[idx]
    d=color.deltaE_ciede2000(lab,color.rgb2lab(candidate/255.0))
    chroma_source=np.hypot(lab[:,:,1],lab[:,:,2])
    chroma_palette=np.hypot(plab[:,1],plab[:,2])
    suspect=(chroma_palette[idx] > chroma_source +12)
    result={"mean_deltaE00":float(d.mean()),"p95_deltaE00":float(np.percentile(d,95)),
        "excess_chroma_pixels":int(suspect.sum()),
        "original_fixed_edge_fraction":float((source_edges&(filters.sobel(color.rgb2gray(candidate/255.0))>=thr)).sum()/max(1,int(source_edges.sum()))),
        **topology(idx)}
    for name,(x0,y0,x1,y1) in ROIS.items():
        result[name+"_mean_deltaE00"]=float(d[y0:y1,x0:x1].mean())
    result["chroma_suspect_A5015B"]=int((suspect & (idx==15)).sum())
    result["chroma_suspect_E20085"]=int((suspect & (idx==10)).sum())
    return result

def screen(metrics,base):
    return {
        "mean_deltaE":metrics["mean_deltaE00"]<=base["mean_deltaE00"]+1.0,
        "p95_deltaE":metrics["p95_deltaE00"]<=base["p95_deltaE00"]+1.0,
        "chroma_suspect":metrics["excess_chroma_pixels"]<=0.4*base["excess_chroma_pixels"],
        "fixed_edges":metrics["original_fixed_edge_fraction"]>=base["original_fixed_edge_fraction"]-0.02,
        "component_count":metrics["nonwhite_components4"]<=base["nonwhite_components4"],
        "singleton_count":metrics["nonwhite_singletons"]<=base["nonwhite_singletons"],
        "female_face":metrics["female_face_eyes_mean_deltaE00"]<=base["female_face_eyes_mean_deltaE00"]+2,
        "male_face":metrics["male_face_eyes_mean_deltaE00"]<=base["male_face_eyes_mean_deltaE00"]+2,
        "hands":metrics["hands_orange_mean_deltaE00"]<=base["hands_orange_mean_deltaE00"]+2,
    }

def comparison(variants,palette,contour,filename,overlay):
    size=(1350,1512)
    canvas=Image.new("RGB",size,"white")
    draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype("DejaVuSans.ttf",19)
    except OSError:font=ImageFont.load_default()
    for i,(name,idx) in enumerate(variants.items()):
        row,col=divmod(i,3)
        x,y=col*450,row*756
        rgb=palette[idx]
        art=(composite(rgb,contour) if overlay else Image.fromarray(rgb).resize((450,720),Image.Resampling.NEAREST))
        canvas.paste(art,(x,y+36))
        draw.text((x+8,y+8),name,font=font,fill="black")
    canvas.save(filename)

def run(source_path,palette_path,p0_archive,m1_archive,v44_archive,output):
    if output.exists():raise ValueError("BLOCKED_OVERWRITE")
    source,filtered,protected,palette,base_idx,contour=pinned_inputs(p0_archive,m1_archive,v44_archive,palette_path,source_path)
    lab,plab,de=get_de_table(source,palette)
    _,_,filtered_de=get_de_table(filtered,palette)
    allowed12=palette_guard(lab,plab,12)
    allowed20=palette_guard(lab,plab,20)
    labels12=choose_by_support(de,allowed12)
    variants={
        "G32_FROZEN":base_idx,
        "P0_NEAREST32":np.argmin(filtered_de,axis=2).astype(np.uint8),
        "B1_CHROMA12":labels12,
        "B1_CHROMA20":choose_by_support(de,allowed20),
        "B1_CHROMA12_SPATIAL":spatial_smooth(labels12,de,allowed12,lab,protected)}
    if not np.array_equal(variants["B1_CHROMA12_SPATIAL"][protected],labels12[protected]):
        raise ValueError("BLOCKED_PROTECTED_DRIFT")
    magnitude=filters.sobel(color.rgb2gray(source/255.0))
    positives=magnitude[magnitude>0];thr=float(np.percentile(positives,90))
    source_edges=magnitude>=thr
    report_metrics={k:source_metrics(source,plab,lab,v,palette,source_edges,thr) for k,v in variants.items()}
    base=report_metrics["G32_FROZEN"]
    gates={}
    for name,stats in report_metrics.items():
        if name=="G32_FROZEN":
            stats["status"]="FROZEN_CONTROL_NOT_A_CANDIDATE"
            continue
        result=screen(stats,base)
        gates[name]=result
        stats["gates"]=result
        stats["status"]="SOURCE_SCREEN_PASS_VISUAL_PENDING" if all(result.values()) else "SOURCE_GATE_FAIL"
    output.mkdir(parents=True)
    Image.fromarray(source).save(output/"ORIGINAL_RGB.png")
    Image.fromarray(filtered).save(output/"P0_BILATERAL_LOW_RGB.png")
    for n,idx in variants.items():
        Image.fromarray(idx).save(output/(n+"_indices.png"))
        rgb=palette[idx]
        Image.fromarray(rgb).save(output/(n+"_RGB.png"))
        composite(rgb,contour).save(output/(n+"_plus_original_V44B.png"))
    comparison(variants,palette,contour,output/"game32_without_contour.png",False)
    comparison(variants,palette,contour,output/"game32_plus_true_V44B.png",True)
    file_sha={p.name:digest(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()}
    report={
        "experiment":EXPERIMENT,"status":"SOURCE_DIAGNOSTIC_GAME32_VISUAL_PENDING",
        "github_sha":os.environ.get("GITHUB_SHA"),"github_run_id":os.environ.get("GITHUB_RUN_ID"),
        "source_sha256":SOURCE_SHA,"palette_git_blob":PALETTE_BLOB,
        "p0_zip_sha256":P0_SHA,"m1_zip_sha256":M1_SHA,"v44_zip_sha256":V44_SHA,
        "contour_E3_sha256":V44_DETAIL_SHA,"original_contour_strokes":410,"original_contour_vertices_NOT_CHALK":1792,
        "source_strong_sobel90":thr,"protected_original_pixels":int(protected.sum()),
        "spatial_protected_labels_identical_to_chroma12":bool(np.array_equal(variants["B1_CHROMA12_SPATIAL"][protected],labels12[protected])),
        "candidate_index_maps":list(variants),"metrics":report_metrics,"file_sha256":file_sha,
        "version":{"python":platform.python_version(),"numpy":np.__version__,"Pillow":Image.__version__,
                   "skimage":skimage.__version__},
        "game_brush":"NOT_RUN","game_E4":"NOT_RUN","game_E5":"NOT_RUN","exact_CHALK":None,
        "human_visual":"PENDING","production_accepted":False}
    (output/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--palette",type=Path,required=True)
    ap.add_argument("--p0-archive",type=Path,required=True)
    ap.add_argument("--m1-archive",type=Path,required=True)
    ap.add_argument("--v44-archive",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    r=run(a.source,a.palette,a.p0_archive,a.m1_archive,a.v44_archive,a.output)
    print(json.dumps({k:{"status":v["status"],"mean_deltaE00":v["mean_deltaE00"],
                         "chroma_suspects":v["excess_chroma_pixels"],"components":v["nonwhite_components4"]}
                      for k,v in r["metrics"].items()},ensure_ascii=False))
