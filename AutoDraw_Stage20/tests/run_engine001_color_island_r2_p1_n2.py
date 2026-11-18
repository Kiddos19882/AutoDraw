#!/usr/bin/env python3
"""R2-P1 N2: original-source-safe DINOv2 merging with optional real BiRefNet alpha hint.

Research-only: identical M0 source labels, same frozen N1 source-safe checks,
plus one preregistered *soft* alpha ranking term. No source recoloring, neural
RGB generation, game32 conversion, in-game brush execution, or new inference.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image
from skimage import color

from run_engine001_color_island_r2_p1_m0 import (
    SHAPE, SOURCE_SHA, PALETTE_BLOB, BG, G32_SHA, ROI, sha,
    pinned_source, merge_one_pass, render_source_medoids, strong_edges,
    _quality, _roi_metrics, _area_hist,
)
from run_engine001_color_island_r2_p1_n1 import (
    load_pinned_m0, load_real_s4_features, pooled_vectors,
    source_rgb_unsupported_chroma, S4_ARTIFACT_SHA, M0_ARTIFACT_SHA,
    COSINE_THRESHOLD, COSINE_SCALE, NEURAL_BONUS,
)

EXP = 'ENGINE001_COLOR_ISLAND_R2_P1_NEURAL_MERGE_REPLAY_N2'
S5_ZIP_SHA = 'fe143f904a2d3694213537f228b5a6b5580de916533eed51def393aafd900ea2'
S5_REPORT_SHA = '68fc9df38153670e6ea29d5e5e96a1e2e68919de7e3933de6224a8a7b9f2cae6'
S5_ALPHA_SHA = '3a5a09db0c7018cbc5fdbc2b1b8b518b98d7c33d414cdc432ad478cee40d60ec'
S5_MODEL_SHA = '5600024376f572a557870a5eb0afb1e5961636bef4e1e22132025467d0f03333'
S5_MODEL_MD5 = '4fab47adc4ff364be1713e97b7e66334'
ALPHA_DIFF_SPAN, ALPHA_PENALTY_MAX = 64.0, 2.0


def load_pinned_biref_alpha(path: Path):
    if not path.is_file() or sha(path) != S5_ZIP_SHA:
        raise ValueError('BLOCKED_R2_P1_N2_BIREFNET_ZIP_SHA')
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('BLOCKED_R2_P1_N2_BIREFNET_ZIP_CRC')
        raw = archive.read('report.json')
        if hashlib.sha256(raw).hexdigest() != S5_REPORT_SHA:
            raise ValueError('BLOCKED_R2_P1_N2_BIREFNET_REPORT_SHA')
        rep = json.loads(raw)
        checks = rep.get('output_sha256', {})
        if (not checks or set(archive.namelist()) != set(checks) | {'report.json'}
                or rep.get('source_sha256') != SOURCE_SHA
                or rep.get('model') != 'birefnet-general-lite'
                or rep.get('actual_pretrained_onnx_inference') is not True
                or rep.get('model_sha256') != S5_MODEL_SHA
                or rep.get('model_md5') != S5_MODEL_MD5
                or checks.get('foreground-alpha.png') != S5_ALPHA_SHA):
            raise ValueError('BLOCKED_R2_P1_N2_BIREFNET_PROVENANCE')
        for name, expected in checks.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError('BLOCKED_R2_P1_N2_BIREFNET_MEMBER_SHA')
        alpha = np.asarray(Image.open(io.BytesIO(archive.read('foreground-alpha.png')))).copy()
        source_rgb = np.asarray(Image.open(io.BytesIO(archive.read('original-RGB.png'))).convert('RGB')).copy()
    if (alpha.shape != SHAPE or alpha.dtype != np.uint8 or int(alpha.max()) == int(alpha.min())
            or source_rgb.shape != (*SHAPE,3) or source_rgb.dtype != np.uint8):
        raise ValueError('BLOCKED_R2_P1_N2_BIREFNET_SHAPE')
    return alpha, source_rgb, {'archive_sha256':S5_ZIP_SHA,
                                'report_sha256':S5_REPORT_SHA,
                                'alpha_sha256':S5_ALPHA_SHA,
                                'true_pretrained_checkpoint_sha256':S5_MODEL_SHA,
                                'source_sha256':SOURCE_SHA,
                                'new_neural_inference':'NOT_RUN'}


def region_alpha_means(alpha: np.ndarray, labels: np.ndarray):
    if (not isinstance(alpha,np.ndarray) or alpha.shape != SHAPE or alpha.dtype != np.uint8
            or not isinstance(labels,np.ndarray) or labels.shape != SHAPE
            or labels.dtype != np.int32 or np.any(labels < -1)):
        raise ValueError('BLOCKED_R2_P1_N2_ALPHA_REGION_ALIGNMENT')
    n = int(labels.max())+1
    if n<1 or not np.array_equal(np.unique(labels[labels>=0]),np.arange(n)):
        raise ValueError('BLOCKED_R2_P1_N2_NONCONTIGUOUS_REGIONS')
    summed = np.bincount(labels[labels>=0], weights=alpha[labels>=0].astype(np.float64),minlength=n)
    count = np.bincount(labels[labels>=0],minlength=n)
    if np.any(count<=0):
        raise ValueError('BLOCKED_R2_P1_N2_EMPTY_REGION')
    return summed/count


def pair_ranking_adjustment(vectors, region_id: int, target_id: int, alpha_means=None):
    if (not isinstance(vectors,np.ndarray) or vectors.ndim!=2
            or vectors.shape[1]!=384 or not np.isfinite(vectors).all()
            or region_id<0 or target_id<0 or max(region_id,target_id)>=len(vectors)):
        raise ValueError('BLOCKED_R2_P1_N2_DINO_SOURCE_FEATURES')
    similarity=float(vectors[region_id]@vectors[target_id])
    bonus=NEURAL_BONUS*min(1.,max(0.,(similarity-COSINE_THRESHOLD)/COSINE_SCALE)) if similarity>=COSINE_THRESHOLD else 0.
    penalty=0.
    if alpha_means is not None:
        if (not isinstance(alpha_means,np.ndarray) or alpha_means.shape!=(len(vectors),)
                or not np.isfinite(alpha_means).all()
                or np.any((alpha_means<0)|(alpha_means>255))):
            raise ValueError('BLOCKED_R2_P1_N2_ALPHA_MEANS_INVALID')
        penalty=ALPHA_PENALTY_MAX*min(1.,abs(float(alpha_means[region_id]-alpha_means[target_id]))/ALPHA_DIFF_SPAN)
    return -bonus+penalty, similarity, bonus, penalty


def _image(name: str, data: np.ndarray, output: Path):
    Image.fromarray(data).save(output/name)


def run(source: Path, palette: Path, m0_archive: Path, s4_archive: Path, s5_archive: Path, output: Path):
    if output.exists():
        raise ValueError('BLOCKED_R2_P1_N2_OUTPUT_OVERWRITE')
    rgb,game32,g32=pinned_source(source,palette)
    previous, labels, coarse, protected, bg, frozen_rgb, published_m0, published_m0_ids=load_pinned_m0(m0_archive)
    if not np.array_equal(rgb,frozen_rgb):
        raise ValueError('BLOCKED_R2_P1_N2_M0_SOURCE_DRIFT')
    field,dino_prov=load_real_s4_features(s4_archive)
    vectors=pooled_vectors(field,labels)
    alpha, alpha_rgb, alpha_prov=load_pinned_biref_alpha(s5_archive)
    if not np.array_equal(rgb,alpha_rgb):
        raise ValueError('BLOCKED_R2_P1_N2_S5_SOURCE_MISMATCH')
    means=region_alpha_means(alpha,labels)
    original_m0_ids,original_m0_merges=merge_one_pass(rgb,labels,coarse,protected)
    if not np.array_equal(original_m0_ids,published_m0_ids):
        raise ValueError('BLOCKED_R2_P1_N2_M0_FROZEN_LABELS_CHANGED')
    re_m0=render_source_medoids(rgb,original_m0_ids,bg)
    replay_drift_pixels=int(np.count_nonzero(np.any(re_m0!=published_m0,axis=2)))
    n1_scored=[];n2_scored=[]
    def score(ledger,source_row,target_row,source_de,contacts,extra,with_alpha):
        src=int(source_row['id']);dst=int(target_row['id'])
        adjustment,cosine,bonus,penalty=pair_ranking_adjustment(
            vectors,src,dst,means if with_alpha else None)
        ledger.append({'source':src,'target':dst,'cosine':round(cosine,7),
                       'dino_bonus':round(bonus,7),'biref_alpha_penalty':round(penalty,7),
                       'alpha_source':round(float(means[src]),5),
                       'alpha_target':round(float(means[dst]),5),
                       'deltaE00':round(float(source_de),7),'contacts':int(contacts)})
        return adjustment
    n1_ids,n1_info=merge_one_pass(rgb,labels,coarse,protected,score_adjustment=lambda *a:score(n1_scored,*a,False))
    n2_ids,n2_info=merge_one_pass(rgb,labels,coarse,protected,score_adjustment=lambda *a:score(n2_scored,*a,True))
    n1_rgb=render_source_medoids(rgb,n1_ids,bg)
    n2_rgb=render_source_medoids(rgb,n2_ids,bg)
    n1_quality=_quality(rgb,n1_rgb);n2_quality=_quality(rgb,n2_rgb)
    src_edge=strong_edges(rgb)[0]
    edge1=strong_edges(n1_rgb)[0];edge2=strong_edges(n2_rgb)[0]
    e1=float(np.count_nonzero(src_edge&edge1)/max(1,int(src_edge.sum())))
    e2=float(np.count_nonzero(src_edge&edge2)/max(1,int(src_edge.sum())))
    choices1={int(x['source']):int(x['target']) for x in n1_info['accepted']}
    choices2={int(x['source']):int(x['target']) for x in n2_info['accepted']}
    changed={str(s):{'N1':choices1.get(s),'N2':choices2.get(s)}
             for s in sorted(choices1.keys()|choices2.keys()) if choices1.get(s)!=choices2.get(s)}
    accents1=source_rgb_unsupported_chroma(rgb,n1_rgb)
    accents2=source_rgb_unsupported_chroma(rgb,n2_rgb)
    guards={
      'original_and_all_model_archive_source_provenance':True,
      'identical_4connected_partition_for_N1_and_N2':True,
      'replay_of_frozen_M0_merge_ids':True,
      'frozen_M0_exact_RGB_render':replay_drift_pixels==0,
      'N2_original_protected_pixels_unchanged':n2_info['protected_unchanged'],
      'N2_original_background_unchanged':n2_info['background_unchanged'],
      'N2_mean_error_not_worse_than_N1':n2_quality['mean_delta_e00']<=n1_quality['mean_delta_e00']+1e-7,
      'N2_p95_not_worse_than_N1':n2_quality['p95_delta_e00']<=n1_quality['p95_delta_e00']+1e-7,
      'N2_source_edge_overlap_not_worse_than_N1':e2+1e-9>=e1,
      'N2_unsupported_chroma_not_more_than_N1':accents2<=accents1,
      'R2_P1_source_mean_at_most_4_79698':n2_quality['mean_delta_e00']<=4.79698,
      'R2_P1_source_p95_at_most_20':n2_quality['p95_delta_e00']<=20.,
      'R2_P1_edge_at_least_M0_unmerged':e2+1e-9>=float(previous['M0_unmerged_edge_overlap']),
    }
    quality='SOURCE_RGB_VISUAL_PENDING' if all(guards.values()) else 'SOURCE_GATE_FAIL'
    neural_effect='N2_CHANGED_ELIGIBLE_MERGES' if changed else 'N2_NO_ADDITIONAL_MERGE_EFFECT'
    output.mkdir(parents=True)
    previews={
      'original_RGB.png':rgb,
      'B0_frozen_G32.png':game32[g32],
      'M0_replayed_RGB.png':re_m0,
      'M0_pinned_original_RGB.png':published_m0,
      'N1_DINO_RGB.png':n1_rgb,
      'N2_DINO_BIREFNET_RGB.png':n2_rgb,
      'N1_N2_changed_ownership.png':((n1_ids!=n2_ids).astype(np.uint8)*255),
      'N1_N2_changed_color_pixels.png':(np.any(n1_rgb!=n2_rgb,axis=2).astype(np.uint8)*255),
      'birefnet_soft_alpha.png':alpha,
      'source_protected_pixels.png':(protected.astype(np.uint8)*255),
    }
    for name, data in previews.items(): _image(name,data,output)
    Image.fromarray(n1_ids.astype(np.int32),mode='I').save(output/'N1_region_ids.tiff')
    Image.fromarray(n2_ids.astype(np.int32),mode='I').save(output/'N2_region_ids.tiff')
    comparisons=(rgb,re_m0,n1_rgb,n2_rgb)
    sheet=Image.new('RGB',(150*len(comparisons),240))
    for k,im in enumerate(comparisons):sheet.paste(Image.fromarray(im),(150*k,0))
    sheet.resize((1200,480),Image.Resampling.NEAREST).save(output/'original_M0_N1_N2_2x.png')
    for name,(x0,y0,x1,y1) in ROI.items():
        patch=Image.new('RGB',((x1-x0)*4,y1-y0))
        for k,im in enumerate(comparisons):
            patch.paste(Image.fromarray(im).crop((x0,y0,x1,y1)),((x1-x0)*k,0))
        patch.resize((patch.width*3,patch.height*3),Image.Resampling.NEAREST).save(output/f'detail_{name}.png')
    report={
      'experiment':EXP,'quality_status':quality,'status':quality,'neural_effect':neural_effect,
      'source_model_only':True,'github_sha':os.getenv('GITHUB_SHA'),
      'github_run_id':os.getenv('GITHUB_RUN_ID'),
      'source_sha256':SOURCE_SHA,'palette_blob_sha':PALETTE_BLOB,'frozen_G32_sha256':G32_SHA,
      'M0_archive_sha256':M0_ARTIFACT_SHA,'S4_archive_sha256':S4_ARTIFACT_SHA,
      'S5_archive_sha256':S5_ZIP_SHA,'S4_true_pretrained_features':dino_prov,
      'S5_true_pretrained_alpha':alpha_prov,
      'new_DINO_or_BIREFNET_inference':'NOT_RUN_ARCHIVED_GENUINE_REPLAY',
      'N1_N2_same_original_region_count':int(vectors.shape[0]),
      'M0_merge_count':original_m0_merges['merged_regions'],
      'N1_merge_count':n1_info['merged_regions'],
      'N2_merge_count':n2_info['merged_regions'],
      'N1_N2_changed_merge_choices':len(changed),
      'N1_N2_changed_ownership_pixels':int(np.count_nonzero(n1_ids!=n2_ids)),
      'N1_N2_changed_source_RGB_pixels':int(np.count_nonzero(np.any(n1_rgb!=n2_rgb,axis=2))),
      'changed_merge_choices':changed,'N1_candidate_scores':n1_scored,
      'N2_candidate_scores':n2_scored,'N1_merge_ledger':n1_info,'N2_merge_ledger':n2_info,
      'replayed_frozen_M0_color_tie_pixels':replay_drift_pixels,
      'M0_replay_color_precision_disclaimer':'Scientific N1/N2 comparisons recompute both images in the same process; any difference from pinned M0 RGB fails full source quality, and never counts as neural improvement.',
      'N1_quality_same_env':n1_quality,'N2_quality_same_env':n2_quality,
      'N1_source_edge_overlap':e1,'N2_source_edge_overlap':e2,
      'N1_original_rgb_unsupported_chroma_pixels':accents1,
      'N2_original_rgb_unsupported_chroma_pixels':accents2,
      'N1_region_sizes':_area_hist(n1_ids),'N2_region_sizes':_area_hist(n2_ids),
      'N2_ROI_quality':_roi_metrics(rgb,n2_rgb,src_edge),
      'source_gates':guards,'visual_review':'USER_PENDING','game32_candidate':'NOT_RUN',
      'native_Egret':'NOT_RUN','original_V44B_410_LAST':'UNCHANGED_NOT_OVERLAID',
      'game_E4':'NOT_RUN','independent_E5':'NOT_RUN','exact_CHALK':None,
      'production_accepted':False,'S5_alpha_fraction_128':float(np.mean(alpha>=128)),
      'file_sha256':{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    a=argparse.ArgumentParser()
    for flag in ('source','palette','m0-archive','s4-archive','s5-archive','output'):
        a.add_argument('--'+flag,type=Path,required=True)
    args=a.parse_args()
    result=run(args.source,args.palette,args.m0_archive,args.s4_archive,args.s5_archive,args.output)
    print(json.dumps({'experiment':EXP,'quality':result['quality_status'],
      'neural_effect':result['neural_effect'],
      'N1_N2_changed_merge_choices':result['N1_N2_changed_merge_choices'],
      'N1_quality':result['N1_quality_same_env'],'N2_quality':result['N2_quality_same_env'],
      'source_gates':result['source_gates']},ensure_ascii=False))
