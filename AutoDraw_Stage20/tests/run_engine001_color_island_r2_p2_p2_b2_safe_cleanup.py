#!/usr/bin/env python3
"""B2: immutable B1 real-game32 small-component source-safe one-pass study."""
from __future__ import annotations
import argparse,hashlib,io,json,os,platform
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from skimage import color,filters,measure
from run_engine001_palette32_region_study import read_palette
from run_engine001_color_island_r2_p2_p2_b1_p0_game32 import (
    git_blob,valid_zip,get_de_table,palette_guard,source_metrics,composite,
    SOURCE_SHA,PALETTE_BLOB,M1_SHA,V44_SHA,V44_DETAIL_SHA)

EXP="ENGINE001_COLOR_ISLAND_R2_P2_P2_B2_SOURCE_SAFE_COMPONENT_CLEANUP"
B1_ZIP_SHA="5998d4c9cc4e9f20eda637ebd0192ba5f38e824d22946fea6f3363dbfcbed916"
B1_REPORT_SHA="c50949662571307892f065576adae3c27201141e4c59eecd7273a71c95356cb4"
M1_REPORT_SHA="89e4135ecd71820e21394751bb4a11f9a17b01edcddcfa6f1bd1f538f8a16969"
V44_PLAN_SHA="9db4dda0661ea529547e91a09dcae38b27043dad57383fb483b945f0de08496a"
B1_CI_SHA="774dedb4f6a7cc51d91cf6b2567e14d38bd9d7f8"
VARIANTS={"B2_SAFE4":{"max_area":4,"mean_extra":1.5,"max_extra":6.0},
          "B2_SAFE12":{"max_area":12,"mean_extra":2.5,"max_extra":8.0}}

def sha(b):return hashlib.sha256(b).hexdigest()

def load_inputs(source_file,palette_file,b1_zip,m1_zip,v44_zip):
    if sha(source_file.read_bytes())!=SOURCE_SHA:raise ValueError("BLOCKED_SOURCE_SHA")
    pal_bytes=palette_file.read_bytes()
    if git_blob(pal_bytes)!=PALETTE_BLOB:raise ValueError("BLOCKED_PALETTE_GIT_BLOB")
    palette=read_palette(palette_file)
    with valid_zip(b1_zip,B1_ZIP_SHA) as b,valid_zip(m1_zip,M1_SHA) as m,valid_zip(v44_zip,V44_SHA) as v:
        report=b.read("report.json")
        if sha(report)!=B1_REPORT_SHA:raise ValueError("BLOCKED_B1_REPORT_SHA")
        rb=json.loads(report)
        if (rb.get("github_sha")!=B1_CI_SHA or str(rb.get("github_run_id"))!="44230985963" or
            rb.get("source_sha256")!=SOURCE_SHA or rb.get("palette_git_blob")!=PALETTE_BLOB or
            rb.get("original_contour_strokes")!=410):
            raise ValueError("BLOCKED_B1_PROVENANCE")
        for name in ("ORIGINAL_RGB.png","B1_CHROMA12_SPATIAL_indices.png","G32_FROZEN_indices.png"):
            if sha(b.read(name))!=rb.get("file_sha256",{}).get(name):
                raise ValueError("BLOCKED_B1_MEMBER_SHA")
        original=np.asarray(Image.open(io.BytesIO(b.read("ORIGINAL_RGB.png"))).convert("RGB"))
        init=np.asarray(Image.open(io.BytesIO(b.read("B1_CHROMA12_SPATIAL_indices.png"))).convert("L"))
        b0=np.asarray(Image.open(io.BytesIO(b.read("G32_FROZEN_indices.png"))).convert("L"))
        mr=m.read("report.json")
        if sha(mr)!=M1_REPORT_SHA:raise ValueError("BLOCKED_M1_REPORT_SHA")
        meta=json.loads(mr)
        if sha(m.read("source_protected_union.png"))!=meta["file_sha256"]["source_protected_union.png"]:
            raise ValueError("BLOCKED_M1_PROTECTED_SHA")
        protected=np.asarray(Image.open(io.BytesIO(m.read("source_protected_union.png"))).convert("L"))>0
        if (original.shape!=(240,150,3) or init.shape!=(240,150) or b0.shape!=init.shape or
            protected.shape!=init.shape or np.any(init>31) or int(protected.sum())!=7947):
            raise ValueError("BLOCKED_B2_SHAPE")
        if sha(v.read("B/V44-B-color-100.png"))!=V44_DETAIL_SHA or sha(v.read("color-plans.json"))!=V44_PLAN_SHA:
            raise ValueError("BLOCKED_V44_SHA")
        scene=json.loads(v.read("color-plans.json"))["plans"]["B"]["strokes"]
        details=scene[-410:]
        if (len(scene)!=2355 or len(details)!=410 or sum(len(q["stroke"]["points"]) for q in details)!=1792 or
           any(q["layer"]!="detail" or q["stroke"]["width"]!=1 or q["stroke"]["colorIndex"]!=100
             or q["stroke"]["strokeId"]!=f"detail-v18-B-{i}" for i,q in enumerate(details))):
             raise ValueError("BLOCKED_V44_DETAIL_IDENTITY")
        contour=Image.open(io.BytesIO(v.read("B/V44-B-color-100.png"))).convert("RGBA")
        if contour.size!=(1380,720):raise ValueError("BLOCKED_V44_SIZE")
    return original,palette,init,b0,protected,contour

def build_components(labels):
    """Stable 4-connected components including white as target, whole snapshot."""
    if labels.shape!=(240,150) or labels.dtype!=np.uint8 or labels.max()>31:
        raise ValueError("BLOCKED_LABEL_SHAPE")
    comp_ids=np.full(labels.shape,-1,np.int32)
    components=[]
    for swatch in range(32):
        binary=(labels==swatch)
        if not binary.any():continue
        cc=measure.label(binary,connectivity=1)
        for local in range(1,int(cc.max())+1):
            px=np.flatnonzero(cc.ravel()==local)
            if not len(px):continue
            k=len(components)
            comp_ids.ravel()[px]=k
            components.append({"id":k,"swatch":swatch,"indices":px,
                               "pixels":int(len(px)),"first":int(px[0])})
    if np.any(comp_ids<0):raise AssertionError("BROKEN_COMPONENT_ENUM")
    return comp_ids,components

def safe_cleanup(labels,original,protected,palette,method):
    if method not in VARIANTS:raise ValueError("BLOCKED_METHOD")
    if labels.shape!=(240,150) or original.shape!=(240,150,3) or protected.shape!=(240,150):
        raise ValueError("BLOCKED_INPUT_SHAPE")
    params=VARIANTS[method]
    lab,plab,de=get_de_table(original,palette)
    allowed=palette_guard(lab,plab,12)
    if not np.all(allowed[np.arange(240)[:,None],np.arange(150)[None,:],labels]):
        raise ValueError("BLOCKED_B1_SOURCE_SUPPORT")
    comp_ids,components=build_components(labels)
    comp_info={r["id"]:r for r in components}
    current_de=np.take_along_axis(de,labels[:,:,None],axis=2)[:,:,0]
    height,width=labels.shape
    changed=labels.copy()
    accepted=[];reasons=Counter();ledger=[]
    for row in sorted(components,key=lambda r:(r["pixels"],r["first"])):
        id=row["id"];pixels=row["indices"];k=row["swatch"];area=row["pixels"]
        if area>params["max_area"] or k==30:continue
        ys,xs=np.unravel_index(pixels,labels.shape)
        if protected.ravel()[pixels].any():
            reasons["KEEP_ORIGINAL_PROTECTED"]+=1
            ledger.append({"id":id,"area":area,"status":"KEEP_ORIGINAL_PROTECTED"});continue
        contacts=Counter()
        for y,x in zip(ys,xs):
            for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                ny,nx=int(y+dy),int(x+dx)
                if ny<0 or ny>=height or nx<0 or nx>=width:continue
                if protected[ny,nx]:continue
                target_id=int(comp_ids[ny,nx])
                if target_id==id or comp_info[target_id]["pixels"]<=params["max_area"]:continue
                if color.deltaE_ciede2000(lab[y,x][None,:],lab[ny,nx][None,:])[0]>8:continue
                contacts[target_id]+=1
        if not contacts:
            reasons["KEEP_NO_SAFE_BIG_NEIGHBOR"]+=1
            ledger.append({"id":id,"area":area,"status":"KEEP_NO_SAFE_BIG_NEIGHBOR"});continue
        options=[]
        for target_id,c in sorted(contacts.items()):
            dest=comp_info[target_id]["swatch"]
            if not allowed[ys,xs,dest].all():continue
            extra=de[ys,xs,dest]-current_de[ys,xs]
            mean=float(extra.mean())
            maximum=float(extra.max())
            if mean<=params["mean_extra"] and maximum<=params["max_extra"]:
                options.append((mean,-c,dest,target_id,maximum))
        if not options:
            reasons["KEEP_UNSUPPORTED_OR_COLOR_COST"]+=1
            ledger.append({"id":id,"area":area,"status":"KEEP_UNSUPPORTED_OR_COLOR_COST"});continue
        mean,negcontact,dest,target,maximum=min(options)
        changed.ravel()[pixels]=dest
        accepted.append({"id":id,"area":area,"swatch_from":int(k),"swatch_to":int(dest),
                         "target_id":int(target),"target_area":int(comp_info[target]["pixels"]),
                         "safe_contacts":int(-negcontact),"mean_extra_deltaE00":mean,
                         "max_member_extra_deltaE00":maximum})
    if not np.array_equal(changed[protected],labels[protected]):raise AssertionError("PROTECTED_OWNER_DRIFT")
    if not np.all(allowed[np.arange(240)[:,None],np.arange(150)[None,:],changed]):
        raise AssertionError("INVALID_SWATCH_COLOR")
    return changed,{"status":"CANDIDATE_NOT_GAME_VALIDATED",
                     "method":method,"parameters":params,
                     "total_initial_4conn_components":len(components),
                     "accepted_region_count":len(accepted),
                     "changed_pixels":int((labels!=changed).sum()),
                     "rejected_reasons":dict(reasons),
                     "accepted_donors":accepted,
                     "rejected_ledger":ledger}

def screen(stats,base,g32,guard_exact,accepted):
    result={
        "protected_labels":bool(guard_exact),
        "original_chroma_no_extra":stats["excess_chroma_pixels"]<=base["excess_chroma_pixels"],
        "mean_deltaE":stats["mean_deltaE00"]<=base["mean_deltaE00"]+0.10,
        "p95_deltaE":stats["p95_deltaE00"]<=base["p95_deltaE00"]+0.10,
        "fixed_edges":stats["original_fixed_edge_fraction"]>=base["original_fixed_edge_fraction"]-0.02,
        "female_face":stats["female_face_eyes_mean_deltaE00"]<=base["female_face_eyes_mean_deltaE00"]+0.5,
        "male_face":stats["male_face_eyes_mean_deltaE00"]<=base["male_face_eyes_mean_deltaE00"]+0.5,
        "hands":stats["hands_orange_mean_deltaE00"]<=base["hands_orange_mean_deltaE00"]+0.5,
        "nonwhite_components":stats["nonwhite_components4"]<=g32["nonwhite_components4"],
        "nonwhite_singletons":stats["nonwhite_singletons"]<=g32["nonwhite_singletons"],
        "accepted_donors":accepted>0}
    return result

def sheet(images,palette,contour,filename,outline):
    canvas=Image.new("RGB",(900,1512),"white")
    dr=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype("DejaVuSans.ttf",19)
    except OSError:font=ImageFont.load_default()
    for i,(name,img) in enumerate(images.items()):
        x,y=(i%2)*450,(i//2)*756
        rgb=palette[img]
        out=composite(rgb,contour) if outline else Image.fromarray(rgb).resize((450,720),Image.Resampling.NEAREST)
        canvas.paste(out,(x,y+36))
        dr.text((x+6,y+8),name,font=font,fill="black")
    canvas.save(filename)

def run(source_file,palette_file,b1_zip,m1_zip,v44_zip,out):
    if out.exists():raise ValueError("BLOCKED_OUTPUT_OVERWRITE")
    source,palette,base,g32,protected,contour=load_inputs(source_file,palette_file,b1_zip,m1_zip,v44_zip)
    variants={"G32_FROZEN":g32,"B1_CHROMA12_SPATIAL_FROZEN":base}
    ledgers={}
    for method in VARIANTS:
        labels,ledger=safe_cleanup(base,source,protected,palette,method)
        variants[method]=labels
        ledgers[method]=ledger
    lab,plab,_=get_de_table(source,palette)
    gradient=filters.sobel(color.rgb2gray(source/255.0))
    thr=float(np.percentile(gradient[gradient>0],90))
    source_edge=gradient>=thr
    metrics={name:source_metrics(source,plab,lab,labels,palette,source_edge,thr)
             for name,labels in variants.items()}
    for method in VARIANTS:
        status=metrics[method]
        gates=screen(status,metrics["B1_CHROMA12_SPATIAL_FROZEN"],metrics["G32_FROZEN"],
                     np.array_equal(variants[method][protected],base[protected]),
                     ledgers[method]["accepted_region_count"])
        status["gates"]=gates
        status["status"]="SOURCE_SCREEN_PASS_VISUAL_PENDING" if all(gates.values()) else "SOURCE_GATE_FAIL"
    out.mkdir(parents=True)
    Image.fromarray(source).save(out/"ORIGINAL_RGB.png")
    for name,labels in variants.items():
        Image.fromarray(labels).save(out/(name+"_indices.png"))
        Image.fromarray(palette[labels]).save(out/(name+"_RGB.png"))
        composite(palette[labels],contour).save(out/(name+"_original_V44B.png"))
    sheet(variants,palette,contour,out/"B2_comparison_with_original_V44B.png",True)
    sheet(variants,palette,contour,out/"B2_comparison_without_contour.png",False)
    hashes={p.name:sha(p.read_bytes()) for p in sorted(out.iterdir()) if p.is_file()}
    report={
        "experiment":EXP,"status":"B2_ORIGINAL_SOURCE_CANDIDATES_REVIEW",
        "github_run_id":os.environ.get("GITHUB_RUN_ID"),"github_sha":os.environ.get("GITHUB_SHA"),
        "source_sha256":SOURCE_SHA,"palette_git_blob":PALETTE_BLOB,
        "b1_zip_sha256":B1_ZIP_SHA,"m1_zip_sha256":M1_SHA,"v44_zip_sha256":V44_SHA,
        "original_V44_detail_RGBA_SHA256":V44_DETAIL_SHA,
        "original_V44_detail_strokes":410,"original_V44_detail_vertices_NOT_CHALK":1792,
        "source_protected_pixels":int(protected.sum()),"variants":list(variants),
        "method_parameters":VARIANTS,"metrics":metrics,"ledgers":ledgers,"file_sha256":hashes,
        "game_round_brush":"NOT_RUN","game_E4":"NOT_RUN","game_E5":"NOT_RUN",
        "game_exact_CHALK":None,"human_visual_review":"PENDING","accepted_production":False,
        "versions":{"python":platform.python_version(),"numpy":np.__version__}}
    (out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--palette",type=Path,required=True)
    p.add_argument("--b1-archive",type=Path,required=True)
    p.add_argument("--m1-archive",type=Path,required=True)
    p.add_argument("--v44-archive",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=run(a.source,a.palette,a.b1_archive,a.m1_archive,a.v44_archive,a.output)
    print(json.dumps({n:{"status":r["metrics"][n].get("status","FROZEN"),
                           "regions":r["metrics"][n]["nonwhite_components4"],
                           "singletons":r["metrics"][n]["nonwhite_singletons"],
                           "donors":r["ledgers"][n]["accepted_region_count"]}
                      for n in VARIANTS},ensure_ascii=False))
