#!/usr/bin/env python3
"""ENGINE-001 R2-P2-P1 M1: stable original-member medoid and fixed source-edge scale.

Independent test-only P2 numerical baseline. P1 original code and failed gates
remain unchanged. No neural features, game32 color selection, game brush or CHALK.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import zipfile

import cv2
import numpy as np
from PIL import Image
import scipy
from skimage import color, filters
import skimage

from run_engine001_color_island_r2_p1_m0 import (
    SOURCE_SHA, PALETTE_BLOB, BG, SHAPE, G32_SHA, ROI, FINE, COARSE,
    SMALL_MAX, CONTACT_MIN, MERGE_DE, MERGE_EXTRA, CROSS_COARSE_DE,
    pinned_source, partition, detail_protection, strong_edges,
    region_stats, _de, _quality, _area_hist, _roi_metrics, sha,
)

EXP = "ENGINE001_COLOR_ISLAND_R2_P2_P1_STABLE_RGB_M1"
M0_ZIP_SHA = "574320c11cd189adab08c1fd85de2119204589194e44c5df9d8279dcf6f2f782"
M0_REPORT_SHA = "b47ae1758f424641cde88c91e7e8a3c522617806242a2ddfd1f98fe8b3615b11"
M0_SHA = "bf2ffce720c3ec21408971153c7f979807b11cdb"
MEDOID_TIE_EPSILON_SQUARED_LAB = 1e-9


def stable_region_stats(rgb, labels):
    """Original-member Lab medoid with row-major tie within frozen epsilon."""
    if (not isinstance(rgb,np.ndarray) or rgb.shape!=(*SHAPE,3) or rgb.dtype!=np.uint8
            or not isinstance(labels,np.ndarray) or labels.shape!=SHAPE
            or labels.dtype!=np.int32 or np.any(labels< -1)):
        raise ValueError('BLOCKED_R2_P2_REGION_STATS_SHAPE')
    lab = color.rgb2lab(rgb / 255.0)
    if not np.isfinite(lab).all():
        raise ValueError('BLOCKED_R2_P2_REGION_LAB_INVALID')
    flat_lab = lab.reshape(-1,3)
    flat_rgb = rgb.reshape(-1,3)
    flat_id = labels.ravel()
    result=[]
    for k in sorted(int(i) for i in np.unique(labels) if i>=0):
        indices=np.flatnonzero(flat_id==k)  # already row-major ascending
        if indices.size==0:
            raise ValueError('BLOCKED_R2_P2_EMPTY_REGION')
        pixels_lab=flat_lab[indices]
        median_lab=np.median(pixels_lab,axis=0)
        squared=np.sum((pixels_lab-median_lab[None,:])**2,axis=1)
        if not np.isfinite(squared).all():
            raise ValueError('BLOCKED_R2_P2_INVALID_MEDOID_DISTANCE')
        minimum=float(np.min(squared))
        allowed=np.flatnonzero(squared<=minimum+MEDOID_TIE_EPSILON_SQUARED_LAB)
        if not allowed.size:
            raise ValueError('BLOCKED_R2_P2_NO_MEDOID')
        medoid_index=int(indices[int(allowed[0])])  # first source pixel (row-major)
        best=flat_lab[medoid_index].copy()
        result.append({'id':k,'indices':indices,'pixels':int(len(indices)),
                       'med':median_lab,'rgb_medoid':flat_rgb[medoid_index].copy(),
                       'lab_medoid':best,
                       'original_medoid_linear_index':medoid_index,
                       'tie_candidates':int(len(allowed)),
                       'baseline':float(color.deltaE_ciede2000(pixels_lab,best[None,:]).mean())})
    return result


def render_stable_source_medoids(rgb, labels, bg):
    if (rgb.shape!=(*SHAPE,3) or labels.shape!=SHAPE or bg.shape!=SHAPE
            or not np.array_equal(labels==-1,bg)):
        raise ValueError('BLOCKED_R2_P2_RENDER_INPUT')
    out=rgb.copy()
    flat=out.reshape(-1,3)
    for row in stable_region_stats(rgb,labels):
        flat[row['indices']]=row['rgb_medoid']
    if not np.array_equal(out[bg],rgb[bg]):
        raise ValueError('BLOCKED_R2_P2_BACKGROUND_CHANGED')
    return out


def source_sobel_fixed_threshold(rgb):
    if rgb.shape!=(*SHAPE,3) or rgb.dtype!=np.uint8:
        raise ValueError('BLOCKED_R2_P2_INVALID_EDGE_SOURCE')
    magnitude=filters.sobel(color.rgb2gray(rgb/255.0))
    positives=magnitude[magnitude>0]
    if not positives.size or not np.isfinite(magnitude).all():
        raise ValueError('BLOCKED_R2_P2_EMPTY_OR_INVALID_EDGE')
    threshold=float(np.percentile(positives,90))
    return magnitude>=threshold, threshold


def fixed_edge_overlap(source_edges,source_threshold,preview):
    if (source_edges.shape!=SHAPE or source_edges.dtype!=np.bool_ or
            preview.shape!=(*SHAPE,3) or preview.dtype!=np.uint8 or
            not np.isfinite(source_threshold) or source_threshold<=0):
        raise ValueError('BLOCKED_R2_P2_INVALID_EDGE_METRIC')
    magnitude=filters.sobel(color.rgb2gray(preview/255.0))
    aligned=magnitude>=source_threshold
    intersection=int(np.count_nonzero(source_edges&aligned))
    return {'overlap_count':intersection,
            'source_edge_pixels':int(np.count_nonzero(source_edges)),
            'overlap_fraction':float(intersection/max(1,int(source_edges.sum()))),
            'fixed_source_sobel90_threshold':float(source_threshold),
            'candidate_edge_pixels_at_source_threshold':int(aligned.sum())}, aligned


def load_pinned_p1_m0(archive):
    if not archive.is_file() or sha(archive)!=M0_ZIP_SHA:
        raise ValueError('BLOCKED_R2_P2_ARCHIVED_M0_ZIP_SHA')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('BLOCKED_R2_P2_ARCHIVED_M0_ZIP_CRC')
        contents={name:z.read(name) for name in z.namelist()}
    if 'report.json' not in contents or hashlib.sha256(contents['report.json']).hexdigest()!=M0_REPORT_SHA:
        raise ValueError('BLOCKED_R2_P2_ARCHIVED_M0_REPORT_SHA')
    report=json.loads(contents['report.json'])
    if (report.get('experiment')!='ENGINE001_COLOR_ISLAND_R2_P1_NEURAL_MERGE_REPLAY_M0'
            or report.get('github_sha')!=M0_SHA or report.get('source_sha256')!=SOURCE_SHA
            or report.get('palette_git_blob')!=PALETTE_BLOB
            or report.get('frozen_g32_png_sha256')!=G32_SHA):
        raise ValueError('BLOCKED_R2_P2_ARCHIVED_M0_PROVENANCE')
    manifest=report.get('files_sha256')
    if not isinstance(manifest,dict) or set(manifest)|{'report.json'}!=set(contents):
        raise ValueError('BLOCKED_R2_P2_ARCHIVED_M0_MANIFEST')
    for name,digest in manifest.items():
        if hashlib.sha256(contents[name]).hexdigest()!=digest:
            raise ValueError('BLOCKED_R2_P2_ARCHIVED_M0_MEMBER_SHA')
    def im(name):
        return np.array(Image.open(io.BytesIO(contents[name])))
    return report,{'raw_ids':im('M0_original_region_ids.tiff').astype(np.int32),
                   'merged_ids':im('M0_merged_region_ids.tiff').astype(np.int32),
                   'coarse':im('M0_coarse_context_ids.tiff').astype(np.int32),
                   'source_rgb':im('original_RGB.png'),
                   'no_merge_rgb':im('M0_NO_MERGE_RGB.png'),
                   'merged_rgb':im('M0_MERGED_RGB.png'),
                   'background':im('original_source_background.png')>0}

def merge_one_pass_m1(rgb, labels, coarse, protected, *, score_adjustment=None):
    """Strict M0: frozen initial region statistics and one no-chain pass.

    Returns a mathematical source-only region map and complete merge ledger.
    This deterministic candidate interface will be shared with genuine N1.
    """
    if (rgb.shape != (*SHAPE, 3) or rgb.dtype != np.uint8 or
            labels.shape != SHAPE or labels.dtype != np.int32 or
            coarse.shape != SHAPE or protected.shape != SHAPE or
            protected.dtype != np.bool_ or
            np.any(labels < -1) or np.any(~np.isfinite(coarse))):
        raise ValueError("BLOCKED_R2_P2_MERGE_INPUT")
    areas = stable_region_stats(rgb, labels)
    lab = color.rgb2lab(rgb / 255.0).reshape(-1, 3)
    merged = labels.copy()
    ledger, accepted = [], []
    absorbed = set()
    received = set()
    for row in sorted(areas, key=lambda a: (a["pixels"], a["id"])):
        i = row["id"]
        if row["pixels"] > SMALL_MAX:
            continue
        if i in absorbed or i in received:
            ledger.append({"source": i, "status": "SKIP_ALREADY_IN_MERGE"})
            continue
        pixels = row["indices"]
        if np.any(protected.ravel()[pixels]):
            ledger.append({"source": i, "status": "KEEP_SOURCE_PROTECTED"})
            continue
        counts = Counter()
        blocked = set()
        yx = np.column_stack(np.unravel_index(pixels, SHAPE))
        for y, x in yx:
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                yy, xx = int(y + dy), int(x + dx)
                if yy < 0 or yy >= SHAPE[0] or xx < 0 or xx >= SHAPE[1]:
                    continue
                target = int(labels[yy, xx])
                if target < 0 or target == i:
                    continue
                counts[target] += 1
                if protected[yy, xx] or protected[y, x]:
                    blocked.add(target)
        possible = []
        reasons = Counter()
        for target, contacts in sorted(counts.items()):
            t = areas[target]
            why = None
            if target in absorbed:
                why = "TARGET_ALREADY_ABSORBED"
            elif contacts < CONTACT_MIN:
                why = "CONTACT_LT2"
            elif target in blocked:
                why = "PROTECTED_SEAM"
            elif t["pixels"] < row["pixels"]:
                why = "TARGET_SMALLER"
            elif t["pixels"] == row["pixels"] and target >= i:
                why = "SYMMETRIC_TIE"
            else:
                separation = _de(row["med"], t["med"])
                if separation > MERGE_DE:
                    why = "SOURCE_COLOR_DELTA_TOO_LARGE"
                elif not (np.all(coarse.ravel()[pixels] == coarse.ravel()[t["indices"][0]])
                          and np.all(coarse.ravel()[t["indices"]] == coarse.ravel()[t["indices"][0]])) and separation > CROSS_COARSE_DE:
                    why = "COARSE_CONTEXT_DIFFERS"
                else:
                    delta = float(color.deltaE_ciede2000(lab[pixels], t["lab_medoid"][None, :]).mean())
                    if delta - row["baseline"] > MERGE_EXTRA:
                        why = "EXTRA_COLOR_ERROR"
                    else:
                        adjustment = 0.0 if score_adjustment is None else float(
                            score_adjustment(row, t, separation, contacts, delta - row["baseline"]))
                        if not np.isfinite(adjustment):
                            raise ValueError("BLOCKED_R2_P2_INVALID_NEURAL_SCORE")
                        possible.append((separation + adjustment, -contacts, target,
                                         delta - row["baseline"], separation))
            if why:
                reasons[why] += 1
        if not possible:
            ledger.append({"source": i, "pixels": row["pixels"], "status": "KEEP_NO_SAFE_TARGET",
                           "reason_counts": dict(reasons)})
            continue
        chosen_score, minus_contact, target, extra, separation = min(possible)
        merged.ravel()[pixels] = target
        accepted.append({"source": i, "target": target, "pixels": row["pixels"],
                         "shared_contacts": -minus_contact, "source_median_deltaE00": round(separation, 8),
                         "extra_mean_deltaE00": round(extra, 8)})
        ledger.append({"source": i, "status": "MERGE_SOURCE_SAFE", "target": target,
                       "alternatives": len(possible), "rejection_counts": dict(reasons)})
        absorbed.add(i)
        received.add(target)
    if not np.array_equal(labels[protected], merged[protected]):
        raise AssertionError("R2-P2 original protected region reassigned")
    if not np.array_equal(labels[labels < 0], merged[labels < 0]):
        raise AssertionError("R2-P2 original background changed")
    return merged, {"accepted": accepted, "ledger": ledger,
                    "merged_regions": len(accepted),
                    "changed_pixels": int(sum(x["pixels"] for x in accepted)),
                    "protected_unchanged": True, "background_unchanged": True}



def _png(root,name,arr):
    Image.fromarray(np.asarray(arr)).save(root/name)


def _roi_fixed(rgb,no_merge,merged,edges,threshold):
    lab_src=color.rgb2lab(rgb/255.0)
    result={}
    for name,(x0,y0,x1,y1) in ROI.items():
        sub=edges[y0:y1,x0:x1]
        no,no_ed=fixed_edge_overlap(edges,threshold,no_merge)
        yes,yes_ed=fixed_edge_overlap(edges,threshold,merged)
        result[name]={
            'box_xyxy':[x0,y0,x1,y1],
            'source_edges':int(sub.sum()),
            'no_merge_fixed_edge_overlap':int((sub&no_ed[y0:y1,x0:x1]).sum()),
            'merged_fixed_edge_overlap':int((sub&yes_ed[y0:y1,x0:x1]).sum()),
            'rgb_changed_pixels_between_versions':int(np.count_nonzero(np.any(
               merged[y0:y1,x0:x1]!=no_merge[y0:y1,x0:x1],axis=2))),
        }
    return result


def source_chroma_excess(rgb,output):
    a=color.rgb2lab(rgb/255.)
    b=color.rgb2lab(output/255.)
    return int(np.count_nonzero(np.hypot(b[...,1],b[...,2])>
                                    np.hypot(a[...,1],a[...,2])+12.0))


def run(source,palette_path,m0_archive,output):
    if output.exists():
        raise ValueError('BLOCKED_R2_P2_OUTPUT_EXISTS')
    rgb,palette,g32=pinned_source(source,palette_path)
    frozen_report,p1=load_pinned_p1_m0(m0_archive)
    labels,bg,coarse,parts=partition(rgb,palette)
    protected,protect_stats,original_edges,detail_seeds=detail_protection(rgb)
    if (not np.array_equal(rgb,p1['source_rgb'])
            or not np.array_equal(bg,p1['background'])
            or not np.array_equal(labels,p1['raw_ids'])
            or not np.array_equal(coarse,p1['coarse'])):
        raise ValueError('BLOCKED_R2_P2_PARTITION_NOT_IDENTICAL_TO_FROZEN_M0')
    merged,ledger=merge_one_pass_m1(rgb,labels,coarse,protected)
    first=render_stable_source_medoids(rgb,labels,bg)
    final=render_stable_source_medoids(rgb,merged,bg)
    # Reproduction test: same original PNG bytes, but independent row-major copies.
    first_copy=render_stable_source_medoids(rgb.copy(order='C'),labels.copy(order='C'),bg.copy())
    merged_copy=render_stable_source_medoids(rgb.copy(order='C'),merged.copy(order='C'),bg.copy())
    stable=bool(np.array_equal(first,first_copy) and np.array_equal(final,merged_copy))
    if not stable:
        raise ValueError('BLOCKED_R2_P2_STABLE_MEDOID_REPRODUCTION')
    source_edges,threshold=source_sobel_fixed_threshold(rgb)
    base_edges,base_mask=fixed_edge_overlap(source_edges,threshold,first)
    merged_edges,merged_mask=fixed_edge_overlap(source_edges,threshold,final)
    lost=(source_edges&base_mask&~merged_mask)
    gained=(source_edges&merged_mask&~base_mask)
    no_merge_stats=_quality(rgb,first)
    merged_stats=_quality(rgb,final)
    base_chroma=source_chroma_excess(rgb,first)
    final_chroma=source_chroma_excess(rgb,final)
    original_source_bg=bg
    g32_white=g32==BG
    nearwhite=np.all(rgb>=245,axis=2)
    b0_white_source_fg=g32_white&~original_source_bg
    reverse=original_source_bg&~g32_white
    if np.any(np.logical_and(labels>=0,bg)):
        raise ValueError('BLOCKED_R2_P2_LABEL_BACKGROUND_OVERLAP')
    gates={
       'pinned_inputs_and_m0_archive_valid':True,
       'identical_original_rgb_partition_from_P1':True,
       'stable_medoid_cross_run_bitwise':stable,
       'protected_source_ownership':bool(ledger['protected_unchanged']),
       'source_background_not_modified':bool(ledger['background_unchanged'] and np.array_equal(final[bg],rgb[bg])),
       'original_RGB_medoid_member_only':True,
       'mean_deltaE00_not_worse_than_same_method_no_merge':
          merged_stats['mean_delta_e00']<=no_merge_stats['mean_delta_e00']+1e-9,
       'p95_deltaE00_not_worse_than_same_method_no_merge':
          merged_stats['p95_delta_e00']<=no_merge_stats['p95_delta_e00']+1e-9,
       'source_fixed_sobel90_edge_overlap_not_worse':
          merged_edges['overlap_count']>=base_edges['overlap_count'],
       'source_chroma_excess_not_increased':final_chroma<=base_chroma,
    }
    accepted=all(gates.values())
    status='SOURCE_RGB_VISUAL_PENDING' if accepted else 'SOURCE_GATE_FAIL'
    output.mkdir(parents=True)
    for name,im in {
        'original_RGB.png':rgb,'B0_frozen_G32.png':palette[g32],
        'P1_original_frozen_M0_NO_MERGE_RGB.png':p1['no_merge_rgb'],
        'P1_original_frozen_M0_MERGED_RGB.png':p1['merged_rgb'],
        'M1_NO_MERGE_RGB.png':first,'M1_MERGED_RGB.png':final,
        'source_white10_border_connected.png':bg.astype(np.uint8)*255,
        'frozen_G32_white.png':g32_white.astype(np.uint8)*255,
        'source_rgb245_nearwhite.png':nearwhite.astype(np.uint8)*255,
        'B0_white_source_foreground.png':b0_white_source_fg.astype(np.uint8)*255,
        'source_strong_edges.png':source_edges.astype(np.uint8)*255,
        'source_detail_seeds.png':detail_seeds.astype(np.uint8)*255,
        'source_protected_union.png':protected.astype(np.uint8)*255,
        'M1_fixed_threshold_no_merge_edges.png':base_mask.astype(np.uint8)*255,
        'M1_fixed_threshold_merged_edges.png':merged_mask.astype(np.uint8)*255,
        'M1_fixed_edge_lost.png':lost.astype(np.uint8)*255,
        'M1_fixed_edge_gained.png':gained.astype(np.uint8)*255,
    }.items():_png(output,name,im)
    for name,ids in {'M1_original_region_ids.tiff':labels,
                     'M1_merged_region_ids.tiff':merged,
                     'M1_coarse_context_ids.tiff':coarse}.items():
        Image.fromarray(ids.astype(np.int32),mode='I').save(output/name)
    sheet=Image.new('RGB',(150*5,240))
    for col,img in enumerate((rgb,palette[g32],p1['merged_rgb'],first,final)):
        sheet.paste(Image.fromarray(img),(150*col,0))
    sheet.resize((1500,480),Image.Resampling.NEAREST).save(output/'original_B0_P1_M1NO_M1MERGED_2x.png')
    for name,(x0,y0,x1,y1) in ROI.items():
        crop=Image.new('RGB',((x1-x0)*4,y1-y0))
        for j,img in enumerate((rgb,p1['merged_rgb'],first,final)):
            crop.paste(Image.fromarray(img).crop((x0,y0,x1,y1)),(j*(x1-x0),0))
        crop.resize((crop.width*3,crop.height*3),Image.Resampling.NEAREST).save(output/f'detail_{name}.png')
    diff=np.any(p1['merged_rgb']!=final,axis=2)
    p1_edge_original_threshold,_=strong_edges(rgb)
    report={
       'experiment':EXP,'status':status,'source_model_only':True,'math_only':True,
       'params_preregistered':True,'github_sha':os.getenv('GITHUB_SHA'),
       'github_run_id':os.getenv('GITHUB_RUN_ID'),
       'source_sha256':SOURCE_SHA,'palette_git_blob_sha':PALETTE_BLOB,
       'g32_sha256':G32_SHA,'frozen_M0_ZIP_sha256':M0_ZIP_SHA,
       'frozen_M0_report_sha256':M0_REPORT_SHA,'frozen_M0_CI_sha':M0_SHA,
       'numpy_version':np.__version__,'scikit_image_version':skimage.__version__,
       'scipy_version':scipy.__version__,'pillow_version':Image.__version__,
       'opencv_version':cv2.__version__,'python_version':platform.python_version(),
       'medoid_tie_epsilon_squared_lab':MEDOID_TIE_EPSILON_SQUARED_LAB,
       'partitions':parts,'M1_merge':ledger,'protected':protect_stats,
       'M1_raw_areas':_area_hist(labels),'M1_merged_areas':_area_hist(merged),
       'P1_M0_merge_areas':_area_hist(p1['merged_ids']),
       'M1_no_merge_quality':no_merge_stats,'M1_merged_quality':merged_stats,
       'M1_stable_render_reproduction':stable,
       'M1_vs_frozen_P1_rgb_changed_pixels':int(diff.sum()),
       'M1_vs_frozen_P1_merge_label_changed_pixels':int(np.count_nonzero(merged!=p1['merged_ids'])),
       'fixed_original_source_sobel90_threshold':threshold,
       'fixed_edge_original':int(source_edges.sum()),
       'fixed_edge_no_merge':base_edges,'fixed_edge_merged':merged_edges,
       'fixed_edge_lost_original_pixels':int(lost.sum()),
       'fixed_edge_gained_original_pixels':int(gained.sum()),
       'historical_P1_dynamic_gate':'RETAINED_AS_DISTINCT_NON_EQUIVALENT_METHOD_NOT_REEVALUATED',
       'source_background_pixels':int(bg.sum()),
       'frozen_B0_white_pixels':int(g32_white.sum()),
       'background_disagreement_pixels':int(np.count_nonzero(bg!=g32_white)),
       'B0_white_source_foreground_pixels':int(b0_white_source_fg.sum()),
       'source_foreground_B0_nonwhite_pixels':int(reverse.sum()),
       'original_rgb245_nearwhite_pixels':int(nearwhite.sum()),
       'original_rgb_chroma_excess_no_merge':base_chroma,
       'original_rgb_chroma_excess_merged':final_chroma,
       'roi_fixed_source_edges':_roi_fixed(rgb,first,final,source_edges,threshold),
       'source_gates':gates,
       'R2_P1_SOURCE_GATE_FAIL_HISTORY_UNCHANGED':True,
       'neural_features':'NOT_RUN','game32_candidate':'NOT_RUN',
       'original_V44B_410_LAST':'UNCHANGED_NOT_OVERLAID',
       'native_Egret':'NOT_RUN','game_E4':'NOT_RUN','independent_E5':'NOT_RUN',
       'exact_CHALK':None,'production_accepted':False,
       'file_sha256':{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--palette',required=True,type=Path)
    p.add_argument('--m0-archive',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    result=run(a.source,a.palette,a.m0_archive,a.output)
    print(json.dumps({'experiment':EXP,'status':result['status'],
      'merge_count':result['M1_merge']['merged_regions'],
      'mean':result['M1_merged_quality']['mean_delta_e00'],
      'no_merge_mean':result['M1_no_merge_quality']['mean_delta_e00'],
      'edge':result['fixed_edge_merged'],
      'gates':result['source_gates']},ensure_ascii=False))
