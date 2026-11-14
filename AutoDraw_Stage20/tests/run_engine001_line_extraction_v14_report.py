#!/usr/bin/env python3
"""Produce V14 source-bound FDoG/AniLines offline image diagnostics.

This does not judge semantic seams or assign game CHALK.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

SOURCE_SHA = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
SOURCE_DIM = (200, 320)
ROI = (100, 62, 200, 251)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def check_source(path: Path) -> dict:
    if not path.is_file() or sha(path) != SOURCE_SHA or path.stat().st_size != 97308:
        raise ValueError("Pinned repository PNG SHA/size mismatch")
    with Image.open(path) as source:
        if source.size != SOURCE_DIM:
            raise ValueError("Pinned PNG dimensions mismatch")
    return {"source_sha256": SOURCE_SHA, "source_size": list(SOURCE_DIM)}


def evaluate(source: np.ndarray, generated: np.ndarray) -> dict:
    if source.shape != (320,200,3) or generated.shape != (320,200):
        raise ValueError("Unexpected output shape: only original 200x320 accepted")
    gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY)
    canny = cv2.Canny(cv2.GaussianBlur(gray, (3,3), 0), 60, 120, L2gradient=True)>0
    mask = generated < 128
    x0,y0,x1,y1 = ROI
    candidate = mask[y0:y1,x0:x1]
    reference = canny[y0:y1,x0:x1]
    near = cv2.dilate(candidate.astype(np.uint8), np.ones((3,3),np.uint8)) > 0
    matching = int(np.count_nonzero(reference & near))
    total = int(np.count_nonzero(reference))
    n,_,stats,_ = cv2.connectedComponentsWithStats(candidate.astype(np.uint8), connectivity=8)
    dark = (gray < 105).astype(np.uint8)
    eroded = cv2.erode(dark, np.ones((5,5),np.uint8))[y0:y1,x0:x1].astype(bool)
    return {
        "full_line_pixels": int(np.count_nonzero(mask)),
        "roi": list(ROI),
        "roi_candidate_pixels": int(np.count_nonzero(candidate)),
        "roi_reference_canny_pixels": total,
        "roi_reference_within1px": matching,
        "roi_canny_recall_proxy": matching/total if total else None,
        "roi_candidate_not_exact_canny_pixels": int(np.count_nonzero(candidate & ~reference)),
        "roi_components_ge8": sum(int(stats[i,cv2.CC_STAT_AREA]>=8) for i in range(1,n)),
        "roi_dark_interior_proxy_area": int(np.count_nonzero(eroded)),
        "roi_candidate_dark_interior_px": int(np.count_nonzero(candidate & eroded)),
        "ground_truth_seams": "NOT_ANNOTATED",
        "recognition": "NOT_VALIDATED",
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--engine",required=True,choices=["fdog","anilines"])
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--generated",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--upstream-sha",required=True)
    p.add_argument("--weights",type=Path)
    args=p.parse_args()
    args.source=args.source.resolve()
    args.generated=args.generated.resolve()
    args.output=args.output.resolve()
    binding=check_source(args.source)
    if not args.generated.is_file():
        raise RuntimeError("Inference output missing")
    with Image.open(args.source) as original:
        source=np.asarray(original.convert("RGB"),dtype=np.uint8)
    with Image.open(args.generated) as out:
        if out.size != SOURCE_DIM:
            raise ValueError(f"Inference output size {out.size} differs from 200x320")
        generated=np.asarray(out.convert("L"),dtype=np.uint8)
    if np.all(generated==generated.flat[0]):
        raise ValueError("Blank/constant inferred image is not usable")
    metrics=evaluate(source,generated)
    x0,y0,x1,y1=ROI
    src_crop=source[y0:y1,x0:x1]
    output_rgb=np.repeat(generated[:,:,None],3,axis=2)
    out_crop=output_rgb[y0:y1,x0:x1]
    mask=generated<128
    overlay=source.copy()
    overlay[mask]=(0.35*source[mask]+0.65*np.asarray((255,0,0))).round().astype(np.uint8)
    parts={
        "source.png":source,
        "line-output.png":generated,
        "jacket-source.png":src_crop,
        "jacket-output.png":generated[y0:y1,x0:x1],
        "jacket-overlay.png":overlay[y0:y1,x0:x1],
    }
    H,W=src_crop.shape[:2]
    compare=np.full((H,W*3,3),255,dtype=np.uint8)
    compare[:,:W]=src_crop
    compare[:,W:2*W]=out_crop
    compare[:,2*W:3*W]=overlay[y0:y1,x0:x1]
    parts["jacket-comparison.png"]=compare
    args.output.mkdir(parents=True,exist_ok=True)
    digests={}
    for name,array in parts.items():
        dest=args.output/name
        Image.fromarray(array).save(dest)
        digests[name]=sha(dest)
    data={
        "experiment_id":"ENGINE001_FDOG_ANILINES_V14",
        "status":"OFFLINE_EXTRACTION_ONLY_NOT_QUALITY_PASS",
        "engine":args.engine,
        "source":binding,
        "inference_png_sha256":sha(args.generated),
        "upstream_git_sha":args.upstream_sha,
        "checkout_sha":os.environ.get("GITHUB_SHA"),
        "weights_sha256":sha(args.weights) if args.weights else None,
        "versions":{"python":platform.python_version(),"opencv":cv2.__version__,
                    "numpy":np.__version__,"pillow":Image.__version__},
        "metrics":metrics,
        "derived_sha256":digests,
        "native_egret":"NOT_RUN",
        "exact_chalk":None,
    }
    (args.output/"report.json").write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"engine":args.engine,"metrics":metrics,"derived_sha256":digests},ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
