#!/usr/bin/env python3
"""ENGINE001 R2-P1 N1: replay real frozen DINOv2 features as safe merge hints.

Reuses the *same* pinned M0 labels and mathematical constraints. The neural
features may only change ranking among mathematically admissible neighbors.
No recolorization, new DINO inference, game32 conversion or native brush.
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
    SHAPE, SOURCE_SHA, PALETTE_BLOB, BG, G32_SHA, ROI, sha, pinned_source,
    merge_one_pass, render_source_medoids, strong_edges,
    _quality, _roi_metrics, _area_hist,
)

EXP = "ENGINE001_COLOR_ISLAND_R2_P1_NEURAL_MERGE_REPLAY_N1"
S4_ARTIFACT_SHA = "408f26b7d349bb5ee503bdf8f825c9f1dde9d639abd4bf4c96ee575beb3c860e"
S4_REPORT_SHA = "ac197d22a54ba0b586e708efa39ec384f7827a7f94fbfbec0cfd41fc8c9c1ef9"
S4_DENSE_SHA = "f0c7086208096c5475c326dfea419c003455048817461490cc908fcdb42cd3af"
S4_CHECKPOINT_SHA = "ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1"
S4_REVISION = "ed25f3a31f01632728cabb09d1542f84ab7b0056"
M0_ARTIFACT_SHA = "574320c11cd189adab08c1fd85de2119204589194e44c5df9d8279dcf6f2f782"
M0_REPORT_SHA = "b47ae1758f424641cde88c91e7e8a3c522617806242a2ddfd1f98fe8b3615b11"
M0_CI_SHA = "bf2ffce720c3ec21408971153c7f979807b11cdb"
COSINE_THRESHOLD, COSINE_SCALE, NEURAL_BONUS = 0.85, 0.15, 4.0


def _archive(path: Path, zip_sha: str, report_sha: str, label: str):
    if not path.is_file() or sha(path) != zip_sha:
        raise ValueError(f"BLOCKED_R2_P1_{label}_ZIP_SHA")
    with zipfile.ZipFile(path) as zipfile_obj:
        if zipfile_obj.testzip() is not None:
            raise ValueError(f"BLOCKED_R2_P1_{label}_ZIP_CRC")
        if 'report.json' not in zipfile_obj.namelist():
            raise ValueError(f"BLOCKED_R2_P1_{label}_REPORT_MISSING")
        raw = zipfile_obj.read('report.json')
        if hashlib.sha256(raw).hexdigest() != report_sha:
            raise ValueError(f"BLOCKED_R2_P1_{label}_REPORT_SHA")
        report = json.loads(raw)
        manifest = report.get('output_file_sha256', report.get('files_sha256', {}))
        if not manifest or set(zipfile_obj.namelist()) != set(manifest) | {'report.json'}:
            raise ValueError(f"BLOCKED_R2_P1_{label}_OUTPUT_MANIFEST")
        for name, expected in manifest.items():
            if hashlib.sha256(zipfile_obj.read(name)).hexdigest() != expected:
                raise ValueError(f"BLOCKED_R2_P1_{label}_MEMBER_SHA")
        raw_members = {name: zipfile_obj.read(name) for name in zipfile_obj.namelist()}
        return report, raw_members


def load_pinned_m0(path: Path):
    report, files = _archive(path, M0_ARTIFACT_SHA, M0_REPORT_SHA, 'M0')
    if (report.get('experiment') != 'ENGINE001_COLOR_ISLAND_R2_P1_NEURAL_MERGE_REPLAY_M0'
            or report.get('github_sha') != M0_CI_SHA
            or report.get('source_sha256') != SOURCE_SHA
            or report.get('palette_git_blob') != PALETTE_BLOB
            or report.get('frozen_g32_png_sha256') != G32_SHA
            or not report.get('math_only')
            or report.get('status') not in ('SOURCE_GATE_FAIL', 'SOURCE_RGB_VISUAL_PENDING')):
        raise ValueError('BLOCKED_R2_P1_M0_REPORT_PROVENANCE')
    def image(name, *, expected_dtype=None):
        val = np.asarray(Image.open(io.BytesIO(files[name])))
        if val.shape != SHAPE or (expected_dtype is not None and val.dtype != expected_dtype):
            raise ValueError('BLOCKED_R2_P1_M0_MEMBER_SHAPE')
        return val
    labels = image('M0_original_region_ids.tiff').astype(np.int32, copy=True)
    coarse = image('M0_coarse_context_ids.tiff').astype(np.int32, copy=True)
    protected = image('original_protected_union.png') > 0
    background = image('original_source_background.png') > 0
    original_source = np.asarray(Image.open(io.BytesIO(files['original_RGB.png'])).convert('RGB'))
    original_m0 = np.asarray(Image.open(io.BytesIO(files['M0_MERGED_RGB.png'])).convert('RGB'))
    baseline_ids = image('M0_merged_region_ids.tiff').astype(np.int32, copy=True)
    if (original_source.shape != (*SHAPE, 3) or original_m0.shape != (*SHAPE, 3)
            or np.any((labels < 0) != background) or not np.all(labels[~background] >= 0)
            or not np.array_equal(np.unique(labels[labels >= 0]),
                                  np.arange(int(labels.max()) + 1))):
        raise ValueError('BLOCKED_R2_P1_M0_PARTITION_PROVENANCE')
    return report, labels, coarse, protected, background, original_source, original_m0, baseline_ids


def load_real_s4_features(path: Path):
    report, files = _archive(path, S4_ARTIFACT_SHA, S4_REPORT_SHA, 'DINO_S4')
    model = report.get('checkpoint', {})
    if (report.get('source_sha256') != SOURCE_SHA
            or report.get('genuine_neural_encoder') != 'PRETRAINED_DINOV2_SMALL'
            or model.get('weights_sha256') != S4_CHECKPOINT_SHA
            or model.get('revision') != S4_REVISION
            or model.get('grid_hw') != [16, 16]
            or model.get('field_hwc') != [240, 150, 384]
            or hashlib.sha256(files['real-dinov2-dense-features.npz']).hexdigest() != S4_DENSE_SHA):
        raise ValueError('BLOCKED_R2_P1_DINO_REAL_PRETRAINED_PROVENANCE')
    with np.load(io.BytesIO(files['real-dinov2-dense-features.npz']), allow_pickle=False) as z:
        if 'dense' not in z.files or 'regions' not in z.files:
            raise ValueError('BLOCKED_R2_P1_DINO_ARCHIVE_CONTENT')
        field = z['dense'].copy()
        old_vectors = z['regions']
        if old_vectors.shape != (468,384):
            raise ValueError('BLOCKED_R2_P1_DINO_HISTORICAL_POOLING')
    if field.shape != (*SHAPE, 384) or field.dtype != np.float32 or not np.isfinite(field).all():
        raise ValueError('BLOCKED_R2_P1_DINO_FIELD_SHAPE')
    return field, {"real_pretrained_checkpoint_sha256": S4_CHECKPOINT_SHA,
                   "model_revision": S4_REVISION, "source_sha256": SOURCE_SHA,
                   "archived_s4_commit": report['github_sha'],
                   "original_dense_npz_sha256": S4_DENSE_SHA,
                   "dino_patch_grid": [16,16], "dense_field_shape":list(field.shape),
                   "historical_s4_region_vectors_used": False}


def pooled_vectors(field, region_ids):
    if (not isinstance(field,np.ndarray) or field.shape != (*SHAPE,384)
            or field.dtype != np.float32 or not np.isfinite(field).all()
            or region_ids.shape != SHAPE or region_ids.dtype != np.int32
            or np.any(region_ids < -1)):
        raise ValueError('BLOCKED_R2_P1_DINO_R2_FIELD_REGION_ALIGNMENT')
    n = int(region_ids.max()) + 1
    if n<1 or not np.array_equal(np.unique(region_ids[region_ids>=0]),np.arange(n)):
        raise ValueError('BLOCKED_R2_P1_DINO_R2_REGION_CONTIGUITY')
    vectors = np.zeros((n, field.shape[-1]), np.float64)
    for k in range(n):
        v = field[region_ids==k].astype(np.float64).mean(axis=0)
        norm = np.linalg.norm(v)
        if not np.isfinite(norm) or norm<1e-8:
            raise ValueError('BLOCKED_R2_P1_DINO_R2_VECTOR_NORM')
        vectors[k] = v/norm
    return vectors


def source_rgb_unsupported_chroma(rgb, output):
    """Identical original-RGB chroma-excess diagnostic for M0 and N1."""
    if rgb.shape!=(*SHAPE,3) or output.shape!=rgb.shape:
        raise ValueError('BLOCKED_R2_P1_DIAGNOSTIC_RGB_SHAPE')
    a=color.rgb2lab(rgb/255.)
    b=color.rgb2lab(output/255.)
    cha=np.hypot(a[...,1],a[...,2]);chb=np.hypot(b[...,1],b[...,2])
    return int(np.count_nonzero(chb>cha+12.0))


def run(source: Path, palette: Path, m0_archive: Path, s4_archive: Path, output: Path):
    if output.exists():
        raise ValueError('BLOCKED_R2_P1_NO_OUTPUT_OVERWRITE')
    rgb,palette_rgb,g32=pinned_source(source,palette)
    previous, labels, coarse, protected, bg, orig_image, frozen_m0_rgb, frozen_m0_ids=load_pinned_m0(m0_archive)
    if not np.array_equal(rgb,orig_image):
        raise ValueError('BLOCKED_R2_P1_SOURCE_RGB_ORIGINAL_M0_MISMATCH')
    field,model_provenance=load_real_s4_features(s4_archive)
    vectors=pooled_vectors(field,labels)
    # Integrity of baseline M0 after enabling the optional pair-scoring extension.
    m0_ids,m0_info=merge_one_pass(rgb,labels,coarse,protected)
    regenerated_m0=render_source_medoids(rgb,m0_ids,bg)
    if not np.array_equal(m0_ids,frozen_m0_ids):
        raise ValueError('BLOCKED_R2_P1_M0_BASELINE_LABELS_CHANGED')
    baseline_render_drift_pixels = int(np.count_nonzero(np.any(
        regenerated_m0 != frozen_m0_rgb, axis=2)))
    scored=[]
    def scorer(source_row,target_row,source_de,contacts,extra):
        src=int(source_row['id']); dst=int(target_row['id'])
        sim=float(vectors[src]@vectors[dst])
        bonus=NEURAL_BONUS*min(1.0,max(0.0,(sim-COSINE_THRESHOLD)/COSINE_SCALE)) if sim>=COSINE_THRESHOLD else 0.0
        scored.append({'source':src,'candidate_target':dst,'cosine':round(sim,7),
                       'source_median_deltaE00':round(float(source_de),7),
                       'neural_priority_bonus':round(bonus,7),'contacts':int(contacts)})
        return -bonus
    n1_ids, info=merge_one_pass(rgb,labels,coarse,protected,score_adjustment=scorer)
    n1_rgb=render_source_medoids(rgb,n1_ids,bg)
    qm0=_quality(rgb,regenerated_m0); qn1=_quality(rgb,n1_rgb)
    frozen_m0_quality=_quality(rgb,frozen_m0_rgb)
    e0=strong_edges(regenerated_m0)[0];e1=strong_edges(n1_rgb)[0];es=strong_edges(rgb)[0]
    overlap_m0=float(np.count_nonzero(es&e0)/max(1,int(es.sum())))
    overlap_n1=float(np.count_nonzero(es&e1)/max(1,int(es.sum())))
    m0_choices={int(i['source']):int(i['target']) for i in m0_info['accepted']}
    n1_choices={int(i['source']):int(i['target']) for i in info['accepted']}
    changes={str(i):{'M0':m0_choices.get(i),'N1':n1_choices.get(i)}
             for i in sorted(m0_choices.keys()|n1_choices.keys()) if m0_choices.get(i)!=n1_choices.get(i)}
    accents_m0=source_rgb_unsupported_chroma(rgb,regenerated_m0)
    accents_n1=source_rgb_unsupported_chroma(rgb,n1_rgb)
    guards={
        'authentic_pretrained_and_source_sha':True,
        'identical_source_partition_and_m0_labels':True,
        'frozen_m0_rgb_render_exact':baseline_render_drift_pixels==0,
        'protected_original_region_ids_unchanged':info['protected_unchanged'],
        'background_unchanged':info['background_unchanged'],
        'mean_deltaE00_not_worse_than_M0':qn1['mean_delta_e00']<=qm0['mean_delta_e00']+1e-7,
        'p95_deltaE00_not_worse_than_M0':qn1['p95_delta_e00']<=qm0['p95_delta_e00']+1e-7,
        'strong_edges_overlap_not_worse_than_M0':overlap_n1+1e-9>=overlap_m0,
        'unsupported_original_rgb_chroma_not_more_than_M0':accents_n1<=accents_m0,
        'R2_P1_frozen_source_mean_gate':qn1['mean_delta_e00']<=4.79698,
        'R2_P1_frozen_source_p95_gate':qn1['p95_delta_e00']<=20.0,
    }
    if not changes and baseline_render_drift_pixels==0:
        status='NEURAL_NO_EFFECT'
    else:
        status='SOURCE_RGB_VISUAL_PENDING' if all(guards.values()) else 'SOURCE_GATE_FAIL'
    output.mkdir(parents=True)
    images={
        'original_RGB.png':rgb,
        'B0_original_G32.png':palette_rgb[g32],
        'M0_original_frozen_RGB.png':frozen_m0_rgb,
        'M0_replayed_same_environment_RGB.png':regenerated_m0,
        'M0_frozen_vs_replayed_drift.png':(np.any(
            regenerated_m0 != frozen_m0_rgb,axis=2).astype(np.uint8)*255),
        'N1_DINO_HINTS_RGB.png':n1_rgb,
        'M0_N1_changed_pixels.png':(np.any(n1_rgb!=regenerated_m0,axis=2).astype(np.uint8)*255),
        'original_protected_source_union.png':(protected.astype(np.uint8)*255),
    }
    for name,array in images.items():
        Image.fromarray(array).save(output/name)
    Image.fromarray(n1_ids.astype(np.int32),mode='I').save(output/'N1_merged_region_ids.tiff')
    for name,(x0,y0,x1,y1) in ROI.items():
        imgs=[rgb,regenerated_m0,n1_rgb]
        crop=Image.new('RGB',((x1-x0)*len(imgs),y1-y0))
        for k,a in enumerate(imgs):
            crop.paste(Image.fromarray(a).crop((x0,y0,x1,y1)),(k*(x1-x0),0))
        crop.resize((crop.width*3,crop.height*3),Image.Resampling.NEAREST).save(output/f'detail_{name}.png')
    strip=Image.new('RGB',(150*4,240))
    for k,a in enumerate((rgb,palette_rgb[g32],regenerated_m0,n1_rgb)):
        strip.paste(Image.fromarray(a),(k*150,0))
    strip.resize((1200,480),Image.Resampling.NEAREST).save(output/'original_B0_M0_N1_2x.png')
    rep={
        'experiment':EXP, 'status':status, 'model_only':True,
        'github_sha':os.getenv('GITHUB_SHA'),'github_run_id':os.getenv('GITHUB_RUN_ID'),
        'source_sha256':SOURCE_SHA,'palette_blob_sha':PALETTE_BLOB,
        'frozen_g32_index_png_sha256':G32_SHA,
        'true_pretrained_inference':'REPLAY_OF_HISTORICAL_S4_NOT_NEW_INFERENCE',
        'checkpoint':model_provenance,
        'M0_original_CI_sha':M0_CI_SHA,
        'M0_archive_sha256':M0_ARTIFACT_SHA,
        'S4_archive_sha256':S4_ARTIFACT_SHA,
        'source_region_count':int(vectors.shape[0]),
        'source_regions_original_only':True,
        'DINO_dense_repooled_for_R2':True,
        'N1_neural_scorer_params':{'cosine_min':COSINE_THRESHOLD,'cosine_span':COSINE_SCALE,
                                   'max_priority_bonus':NEURAL_BONUS},
        'M0_merge_count':m0_info['merged_regions'],
        'N1_merge_count':info['merged_regions'],
        'M0_N1_changed_merge_choices':len(changes),
        'changed_merge_choices':changes,
        'neural_candidate_scores':scored,
        'N1_merge_ledger':info,
        'M0_RGB_source_quality':qm0,
        'M0_original_frozen_RGB_source_quality':frozen_m0_quality,
        'M0_frozen_to_same_environment_render_drift_pixels':baseline_render_drift_pixels,
        'M0_baseline_render_drift_disclaimer':
          'The N1 vs M0 differential uses the same-env recalculated M0, never reuses the frozen M0 render as a fake same-env comparison. Any nonzero drift fails source gates.',
        'N1_RGB_source_quality':qn1,
        'M0_source_edge_overlap':overlap_m0,
        'N1_source_edge_overlap':overlap_n1,
        'M0_original_rgb_unsupported_chroma_pixels':accents_m0,
        'N1_original_rgb_unsupported_chroma_pixels':accents_n1,
        'N1_area_histogram':_area_hist(n1_ids),
        'N1_roi_quality':_roi_metrics(rgb,n1_rgb,es),
        'source_gates':guards,
        'user_visual':'PENDING','N2_BIREFNET':'NOT_RUN',
        'game32_candidate':'NOT_RUN','native_Egret':'NOT_RUN',
        'original_V44B_410_LAST':'UNCHANGED_NOT_OVERLAID',
        'game_E4':'NOT_RUN','independent_E5':'NOT_RUN',
        'exact_CHALK':None,'production_accepted':False,
        'files_sha256':{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output/'report.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return rep


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for flag in ('source','palette','m0-archive','s4-archive','output'):
        parser.add_argument('--'+flag,type=Path,required=True)
    args=parser.parse_args()
    r=run(args.source,args.palette,args.m0_archive,args.s4_archive,args.output)
    print(json.dumps({'experiment':EXP,'status':r['status'],
          'source_regions':r['source_region_count'],
          'N1_M0_changed_merge_choices':r['M0_N1_changed_merge_choices'],
          'M0_source_quality':r['M0_RGB_source_quality'],
          'N1_source_quality':r['N1_RGB_source_quality'],
          'gates':r['source_gates']},ensure_ascii=False))