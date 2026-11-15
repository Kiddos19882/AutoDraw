#!/usr/bin/env python3
"""ENGINE-001 V19 frozen V18-B diagnostic; no path/paint modification."""
import argparse, hashlib, io, json, platform, zipfile
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from skimage import __version__ as skimage_version
from skimage.morphology import skeletonize

SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
ANILINES_SHA="2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b"
B_SHA={"B-source-path-mask.png":"99647975bcc6437a0180626ba967ea72cc588bebebb2b363ef08f6a068fb1235",
       "B-paths.json":"752dbc5ff55e90b0d38f492fadfde9be8811b70ebc66bce4999f716c4a86ed57",
       "B-roi.png":"e2c604a31556b0414a451e36d6b7d2aa66cf01c65a36c4a31d3f9d601a3f1adf"}
ROI=(100,62,200,251)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(path, expected):
    data=Path(path).read_bytes()
    if sha(data)!=expected: raise ValueError("Pinned SHA mismatch: "+str(path))
    return data


def frozen_b(zip_file):
    # Reject malformed archives consistently, before treating any content as evidence.
    if not zipfile.is_zipfile(zip_file):
        raise ValueError("Invalid V18 artifact ZIP: "+str(zip_file))
    with zipfile.ZipFile(zip_file) as archive:
        report=json.loads(archive.read("report.json"))
        if report.get("source_sha256")!=SOURCE_SHA or report.get("anilines_sha256")!=ANILINES_SHA:
            raise ValueError("Wrong V18 source binding")
        for name, expected in B_SHA.items():
            if sha(archive.read(name))!=expected or report.get("artifacts_sha256",{}).get(name)!=expected:
                raise ValueError("Wrong V18 artifact SHA: "+name)
        mask=np.asarray(Image.open(io.BytesIO(archive.read("B-source-path-mask.png"))).convert("L"))
        roi=np.asarray(Image.open(io.BytesIO(archive.read("B-roi.png"))).convert("RGB"))
        strokes=json.loads(archive.read("B-paths.json"))
    if mask.shape!=(320,200) or roi.shape!=(240,150,3) or len(strokes)!=410:
        raise ValueError("V18-B shape or stroke count mismatch")
    return mask>0,roi


def missed_components(missed):
    n, _, stats, _ = cv2.connectedComponentsWithStats(missed.astype(np.uint8), 8)
    bins={"1":0,"2":0,"3-4":0,"5-9":0,"10+":0}
    details=[]
    for i in range(1,n):
        x,y,w,h,area=map(int,stats[i])
        group="1" if area==1 else "2" if area==2 else "3-4" if area<=4 else "5-9" if area<=9 else "10+"
        bins[group]+=1
        details.append({"pixels":area,"bbox_xywh":[x,y,w,h]})
    details.sort(key=lambda d:(-d["pixels"],d["bbox_xywh"][1],d["bbox_xywh"][0]))
    return bins, details[:30], n-1


def analyze(source, anilines, v18_zip, output):
    raw=pinned(source,SOURCE_SHA)
    if len(raw)!=97308: raise ValueError("Original source length mismatch")
    src=np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"))
    gray=np.asarray(Image.open(io.BytesIO(pinned(anilines,ANILINES_SHA))).convert("L"))
    if src.shape!=(320,200,3) or gray.shape!=(320,200):
        raise ValueError("Input image dimensions mismatch")
    predicted, broi=frozen_b(v18_zip)
    skeleton=skeletonize(gray<128)
    covered=skeleton & (cv2.dilate(predicted.astype(np.uint8),np.ones((3,3),np.uint8))>0)
    missed=skeleton & ~covered
    if int(skeleton.sum())!=5943 or int(covered.sum())!=5792:
        raise ValueError("Frozen V18-B baseline does not match")
    if int(covered.sum()+missed.sum())!=int(skeleton.sum()):
        raise ValueError("Skeleton count conservation failed")
    bins,top,ncomponents=missed_components(missed)
    if sum(bins.values())!=ncomponents:raise ValueError("Component count error")
    # Proximity to original eight-neighbor junctions is NOT a cause attribution.
    neighbor_count=cv2.filter2D(skeleton.astype(np.uint8),-1,np.ones((3,3),np.uint8),
                                borderType=cv2.BORDER_CONSTANT)-skeleton.astype(np.uint8)
    jprox=cv2.dilate((skeleton & (neighbor_count>=3)).astype(np.uint8),
                     np.ones((5,5),np.uint8))>0
    inroi=np.zeros_like(missed)
    inroi[ROI[1]:ROI[3],ROI[0]:ROI[2]]=True
    dark=cv2.erode((cv2.cvtColor(src,cv2.COLOR_RGB2GRAY)<105).astype(np.uint8),
                   np.ones((5,5),np.uint8))>0
    # Reproduce unchanged V5 palette only for neighborhood risk diagnostics.
    logical=Image.new("RGB",(460,240),(255,255,255))
    logical.paste(Image.fromarray(src).resize((150,240),Image.Resampling.LANCZOS),(155,0))
    qfull=np.asarray(logical.quantize(colors=8,method=Image.Quantize.MEDIANCUT,
                                      dither=Image.Dither.NONE),dtype=np.uint8)
    palette=qfull[:,155:305]
    labels,counts=np.unique(qfull,return_counts=True)
    bg=int(labels[np.argmax(counts)])
    ink=np.any(broi!=255,axis=2)
    owner={str(i):int((ink & (palette==i)).sum()) for i in range(8)}
    padded=np.pad(palette,1,mode="edge")
    near_other=np.zeros_like(ink)
    near_bg=np.zeros_like(ink)
    for dy in range(3):
        for dx in range(3):
            around=padded[dy:dy+240,dx:dx+150]
            near_other|=(around!=palette)
            near_bg|=(around==bg)
    risk=ink & near_other
    background_risk=ink & near_bg
    if sum(owner.values())!=int(ink.sum()):raise ValueError("Color-owner sum mismatch")
    source_roi=np.asarray(logical,dtype=np.uint8)[:,155:305]
    source_miss=src.copy()
    source_miss[missed]=(255,15,40)
    miss_roi=np.asarray(Image.fromarray(source_miss).resize((150,240),Image.Resampling.NEAREST))
    risk_roi=source_roi.copy()
    risk_roi[ink]=(49,38,43)
    risk_roi[risk]=(255,166,0)
    risk_roi[background_risk]=(255,35,55)
    comparison=np.concatenate([source_roi,broi,miss_roi,risk_roi],axis=1)
    metrics={
        "skeleton_pixels":int(skeleton.sum()),"covered_1px":int(covered.sum()),
        "missed_1px":int(missed.sum()),"coverage_1px":float(covered.sum()/skeleton.sum()),
        "missed_components":ncomponents,"component_size_bins":bins,"largest_missed_components":top,
        "missed_near_original_8neighbor_junction_2px":int((missed & jprox).sum()),
        "missed_other":int((missed & ~jprox).sum()),
        "source_mixed_roi_missed_pixels":int((missed & inroi).sum()),
        "source_other_missed_pixels":int((missed & ~inroi).sum()),
        "source_mixed_roi_skeleton_pixels":int((skeleton & inroi).sum()),
        "missed_dark_interior_proxy_pixels":int((missed & dark).sum()),
        "missed_dark_interior_and_mixed_roi":int((missed & dark & inroi).sum()),
        "logical_ink_pixels":int(ink.sum()),"palette_bg_index":bg,
        "owner_label_counts":owner,"ink_multiclass_neighborhood_proxy":int(risk.sum()),
        "ink_background_neighborhood_proxy":int(background_risk.sum())
    }
    output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refusing overwrite of V19 evidence")
    output.mkdir(parents=True,exist_ok=True)
    images={
        "original-resized.png":source_roi,"frozen-v18-b.png":broi,
        "missing-original-overlay.png":miss_roi,"palette-risk-overlay.png":risk_roi,
        "v19-comparison.png":comparison,"source-missed-binary.png":missed.astype(np.uint8)*255,
    }
    hashes={}
    for name, arr in images.items():
        dest=output/name
        Image.fromarray(arr).save(dest)
        hashes[name]=sha(dest.read_bytes())
    report={
        "experiment":"ENGINE001_ANILINES_V19_MISSING_DETAIL_AND_COLOR_AUDIT",
        "status":"OFFLINE_DIAGNOSTIC_ONLY_NOT_NATIVE",
        "source_sha256":SOURCE_SHA,"anilines_sha256":ANILINES_SHA,
        "v18_artifact_zip_sha256":sha(Path(v18_zip).read_bytes()),
        "v18_b_mask_sha256":B_SHA["B-source-path-mask.png"],
        "v18_b_paths_sha256":B_SHA["B-paths.json"],
        "versions":{"python":platform.python_version(),"cv2":cv2.__version__,
                    "numpy":np.__version__,"pillow":Image.__version__,
                    "skimage":skimage_version},
        "metrics":metrics,"derived_sha256":hashes,
        "not_tested":["true seam labels","color class painting safety","native Egret width1",
                      "game exact CHALK","E5"]
    }
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                                      encoding="utf-8")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--anilines",type=Path,required=True)
    p.add_argument("--v18-zip",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(analyze(a.source,a.anilines,a.v18_zip,a.output)["metrics"],
                     ensure_ascii=False,indent=2))
