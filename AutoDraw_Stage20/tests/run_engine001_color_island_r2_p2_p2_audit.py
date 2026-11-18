#!/usr/bin/env python3
"""ENGINE-001 R2-P2-P2-A: source micro-regions versus unsupported game32 pixels.

NON-DESTRUCTIVE diagnostic. No region remap, no recoloring, no native brush.
All thresholds and provenance frozen in the R2-P2-P2-A protocol BEFORE implementation.
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
import zipfile

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import color
import scipy, skimage

EXP = 'ENGINE001_COLOR_ISLAND_R2_P2_P2_SOURCE_SUPPORT_AUDIT_A1'
SOURCE_SHA = '07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a'
PALETTE_BLOB = '461b5f3725b9b79888ad36e807b3cf4c9e445e98'
M1_ZIP_SHA = '8bedc496bf01cf7205ecc8ceb7be8eb0f68b751b11c53ea67dbdd3982c7fe583'
M1_REPORT_SHA = '89e4135ecd71820e21394751bb4a11f9a17b01edcddcfa6f1bd1f538f8a16969'
G32_SHA = 'b8dcd5f00d2c39c81997aaae084eaae19a776454e6fd6466209839288c1e5637'
SHAPE = (240, 150)
CHROMA_EXCESS = 12.0
DELTAE_EXCESS = 22.0
SOURCE_HUE_MIN_CHROMA = 12.0
PALETTE_HUE_MIN_CHROMA = 22.0
HUE_DIFF = 45.0
SAFE_NEIGHBOR_DE = 4.0
SMALL_SIZES = (1, 2, 4, 8, 24)
FOUR = ((-1,0),(1,0),(0,-1),(0,1))
DIAGONAL = ((-1,-1),(-1,1),(1,-1),(1,1))
STRUCT4 = np.array([[0,1,0],[1,1,1],[0,1,0]], dtype=np.uint8)
ROI = {
 'female_face_eyes':(26,34,85,100),
 'male_face_eyes':(72,14,123,92),
 'bow_hair':(10,26,70,100),
 'hands_orange':(31,125,115,165),
 'blouse_buttons':(24,92,105,147),
 'skirt_hem':(18,153,118,219),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha256(Path(path).read_bytes())


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def pinned_palette(path: Path):
    raw = Path(path).read_bytes()
    if blob_sha(raw) != PALETTE_BLOB:
        raise ValueError('BLOCKED_PALETTE_GIT_BLOB_SHA')
    obj = json.loads(raw)
    colors = np.array([item['rgb'] for item in obj['colors']], dtype=np.uint8)
    if colors.shape != (32,3) or len({tuple(x) for x in colors}) != 32 or not np.array_equal(colors[30],[255,255,255]):
        raise ValueError('BLOCKED_PALETTE_32_SWATCH_CONTRACT')
    return colors


def original_and_archive(source: Path, archive: Path):
    if file_sha(source) != SOURCE_SHA:
        raise ValueError('BLOCKED_ORIGINAL_SOURCE_SHA')
    if file_sha(archive) != M1_ZIP_SHA:
        raise ValueError('BLOCKED_FROZEN_M1_ZIP_SHA')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('BLOCKED_M1_ZIP_CRC')
        if sha256(z.read('report.json')) != M1_REPORT_SHA:
            raise ValueError('BLOCKED_M1_REPORT_SHA')
        report = json.loads(z.read('report.json'))
        if report.get('source_sha256') != SOURCE_SHA or report.get('g32_sha256') != G32_SHA:
            raise ValueError('BLOCKED_M1_REPORT_SOURCE_IDENTITY')
        for filename,digest in report['file_sha256'].items():
            if sha256(z.read(filename)) != digest:
                raise ValueError('BLOCKED_M1_INNER_FILE_SHA_'+filename)
        def im(name):
            return np.array(Image.open(io.BytesIO(z.read(name))))
        rgb = im('original_RGB.png')
        g32 = im('B0_frozen_G32.png')
        labels = im('M1_original_region_ids.tiff').astype(np.int32)
        merged = im('M1_merged_region_ids.tiff').astype(np.int32)
        coarse = im('M1_coarse_context_ids.tiff').astype(np.int32)
        protected = im('source_protected_union.png') > 0
        bg = im('source_white10_border_connected.png') > 0
    if rgb.shape!=(*SHAPE,3) or g32.shape!=rgb.shape or rgb.dtype!=np.uint8 or g32.dtype!=np.uint8:
        raise ValueError('BLOCKED_M1_RGB_SHAPE')
    if any(x.shape!=SHAPE for x in (labels,merged,coarse,protected,bg)):
        raise ValueError('BLOCKED_M1_MASK_SHAPE')
    if not np.array_equal(labels==-1,bg) or np.any(labels < -1) or len(np.unique(labels[labels>=0])) != 755:
        raise ValueError('BLOCKED_M1_PARTITION_OWNERSHIP')
    if np.any(merged[bg]!=-1) or np.any(merged[~bg]<0):
        raise ValueError('BLOCKED_M1_MERGED_BACKGROUND')
    return dict(rgb=rgb,g32=g32,labels=labels,merged=merged,coarse=coarse,protected=protected,bg=bg,report=report)


def exact_swatch_ids(g32: np.ndarray, palette: np.ndarray):
    if g32.ndim!=3 or g32.shape[-1]!=3 or palette.shape!=(32,3):
        raise ValueError('BLOCKED_G32_RGB_SHAPE')
    flat = np.ascontiguousarray(g32.reshape(-1,3))
    mapping={tuple(map(int,x)):i for i,x in enumerate(palette)}
    out=np.array([mapping.get(tuple(map(int,x)),-1) for x in flat],dtype=np.int16).reshape(g32.shape[:2])
    if np.any(out<0):
        raise ValueError('BLOCKED_UNRECOGNIZED_G32_SWATCH')
    return out


def mismatch_masks(source_rgb: np.ndarray, game_rgb: np.ndarray):
    if (source_rgb.shape!=game_rgb.shape or source_rgb.ndim!=3 or source_rgb.shape[-1]!=3
            or source_rgb.dtype!=np.uint8 or game_rgb.dtype!=np.uint8):
        raise ValueError('BLOCKED_INVALID_RGB_DIAGNOSTIC_INPUT')
    src=color.rgb2lab(source_rgb/255.0)
    game=color.rgb2lab(game_rgb/255.0)
    sC=np.hypot(src[...,1],src[...,2])
    gC=np.hypot(game[...,1],game[...,2])
    excess=gC-sC
    de=color.deltaE_ciede2000(src,game)
    sa=np.degrees(np.arctan2(src[...,2],src[...,1]))
    ga=np.degrees(np.arctan2(game[...,2],game[...,1]))
    hue_diff=np.abs((ga-sa+180.0)%360.0-180.0)
    active=(sC>=SOURCE_HUE_MIN_CHROMA)&(gC>=PALETTE_HUE_MIN_CHROMA)
    cm=excess>CHROMA_EXCESS
    dm=de>DELTAE_EXCESS
    hm=active&(hue_diff>HUE_DIFF)
    return {'chroma':cm,'delta_e':dm,'hue':hm,'union':cm|dm|hm,
            'delta_e_image':de,'chroma_excess':excess,'hue_diff':hue_diff,
            'hue_guard_active':active}


def hist(areas: np.ndarray):
    aa=np.asarray(areas,dtype=int)
    return {'count':int(len(aa)),**{f'area_le{n}':int((aa<=n).sum()) for n in SMALL_SIZES},
            'largest':int(aa.max()) if aa.size else 0}


def component_audit(mask: np.ndarray, *, max_items=12):
    if mask.ndim!=2 or mask.dtype!=bool:raise ValueError('BLOCKED_INVALID_COMPONENT_MASK')
    labels,n=ndi.label(mask,structure=STRUCT4)
    areas=np.bincount(labels.ravel(),minlength=n+1)[1:]
    # Rank by area, then label ID for deterministic output, no randomness.
    top=sorted(range(1,n+1),key=lambda i:(-int(areas[i-1]),i))[:max_items]
    boxes=[]
    for i in top:
        yy,xx=np.nonzero(labels==i)
        boxes.append({'area':int(areas[i-1]),'bbox_xyxy':[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],
                      'centroid_xy':[float(xx.mean()),float(yy.mean())]})
    return {'pixels':int(mask.sum()),'components4':hist(areas),'top_components':boxes}


def neighbors_of(ids: np.ndarray, y: int, x: int, directions):
    h,w=ids.shape;out=[]
    for dy,dx in directions:
        yy,xx=y+dy,x+dx
        if 0<=yy<h and 0<=xx<w and ids[yy,xx]>=0 and ids[yy,xx]!=ids[y,x]:
            out.append((yy,xx,int(ids[yy,xx])))
    return out


def singleton_audit(rgb:np.ndarray,ids:np.ndarray,coarse:np.ndarray,protected:np.ndarray,g32_ids:np.ndarray,
                    suspicion:dict):
    h,w=ids.shape
    if rgb.shape!=(h,w,3) or coarse.shape!=(h,w) or protected.shape!=(h,w) or g32_ids.shape!=(h,w):
        raise ValueError('BLOCKED_SINGLETON_AUDIT_SHAPE')
    sizes=np.bincount(ids[ids>=0]); singles=np.flatnonzero(sizes==1)
    is_single=np.isin(ids,singles)
    lab=color.rgb2lab(rgb/255.)
    rows=[]
    for y,x in np.argwhere(is_single):
        y=int(y);x=int(x);n4=neighbors_of(ids,y,x,FOUR)
        n8=n4+neighbors_of(ids,y,x,DIAGONAL)
        mine=lab[y,x][None,:]
        ranked4=sorted([(float(color.deltaE_ciede2000(mine,lab[yy,xx][None,:])[0]),yy,xx,owner) for yy,xx,owner in n4],key=lambda r:(r[0],r[1],r[2]))
        ranked8=sorted([(float(color.deltaE_ciede2000(mine,lab[yy,xx][None,:])[0]),yy,xx,owner) for yy,xx,owner in n8],key=lambda r:(r[0],r[1],r[2]))
        safe4=[(de,yy,xx,owner) for de,yy,xx,owner in ranked4 if not protected[yy,xx] and de<=SAFE_NEIGHBOR_DE and coarse[yy,xx]==coarse[y,x]]
        eligible=bool(not protected[y,x] and safe4)
        rows.append({'id':int(ids[y,x]),'xy':[x,y],'source_rgb':rgb[y,x].tolist(),
                     'game_swatch_index':int(g32_ids[y,x]),'protected':bool(protected[y,x]),
                     'four_neighbor_pixel_count':len(n4),'eight_neighbor_pixel_count':len(n8),
                     'four_neighbor_region_ids':sorted({v[2] for v in n4}),
                     'diagonal_only':bool(not n4 and n8),'fully_8_isolated':bool(not n8),
                     'nearest_four_original_delta_e00':ranked4[0][0] if ranked4 else None,
                     'nearest_eight_original_delta_e00':ranked8[0][0] if ranked8 else None,
                     'safe_merge_upper_bound':eligible,'safe_target_original_region_id':int(safe4[0][3]) if eligible else None,
                     'palette_chroma_suspect':bool(suspicion['chroma'][y,x]),
                     'palette_union_suspect':bool(suspicion['union'][y,x])})
    assert len(rows)==len(singles)
    return rows,is_single


def small_region_audit(rgb:np.ndarray, ids:np.ndarray, protected:np.ndarray, coarse:np.ndarray, *, max_area=24):
    """Non-mutating source small-component topology, separate from color swatches."""
    sizes=np.bincount(ids[ids>=0])
    lab=color.rgb2lab(rgb/255.0)
    rows=[]
    for region_id in np.flatnonzero((sizes>=1)&(sizes<=max_area)):
        pixels=np.argwhere(ids==region_id)
        local_lab=lab[pixels[:,0],pixels[:,1]]
        median=np.median(local_lab,axis=0)
        sq=np.sum((local_lab-median[None,:])**2,axis=1)
        medoid_idx=int(np.flatnonzero(sq<=float(sq.min())+1e-9)[0])
        y0,x0=map(int,pixels[medoid_idx])
        boundary4={};boundary8={};n4=0;n8=0
        for yy,xx in pixels:
            yy=int(yy);xx=int(xx)
            for ny,nx,target in neighbors_of(ids,yy,xx,FOUR):
                n4+=1;boundary4[target]=boundary4.get(target,0)+1
            for ny,nx,target in neighbors_of(ids,yy,xx,DIAGONAL):
                n8+=1;boundary8[target]=boundary8.get(target,0)+1
        rows.append({'id':int(region_id),'area':int(len(pixels)),
                     'protected_source_pixels':int(protected[pixels[:,0],pixels[:,1]].sum()),
                     'original_member_medoid_rgb':rgb[y0,x0].tolist(),
                     'medoid_source_pixel_xy':[x0,y0],
                     'distinct_four_neighbors':sorted(int(i) for i in boundary4),
                     'distinct_diagonal_neighbors':sorted(int(i) for i in boundary8),
                     'four_neighbor_contacts':int(n4), 'diagonal_neighbor_contacts':int(n8),
                     'four_connectivity_isolated':not bool(n4),
                     'eight_connectivity_isolated':not bool(n4 or n8),
                     'single_coarse_region':bool(np.all(coarse[pixels[:,0],pixels[:,1]]==coarse[pixels[0,0],pixels[0,1]])),
                    })
    return rows


def image_png(path: Path, array: np.ndarray):
    Image.fromarray(array).save(path)


def run(source:Path,palette_path:Path,m1_archive:Path,output:Path):
    if output.exists():raise ValueError('BLOCKED_NO_EVIDENCE_OVERWRITE')
    palette=pinned_palette(palette_path)
    item=original_and_archive(source,m1_archive)
    rgb=item['rgb'];g32=item['g32'];ids=item['labels'];bg=item['bg'];coarse=item['coarse'];protected=item['protected']
    game_ids=exact_swatch_ids(g32,palette)
    scores=mismatch_masks(rgb,g32)
    rows,singles=singleton_audit(rgb,ids,coarse,protected,game_ids,scores)
    small_rows=small_region_audit(rgb,ids,protected,coarse)
    count=len(rows)
    if count!=179 or sum(x['protected'] for x in rows)!=81:
        raise ValueError('BLOCKED_M1_SINGLETON_COUNT_DRIFT')
    if len({tuple(p) for p in palette.tolist()})!=32:
        raise ValueError('BLOCKED_PALETTE_DUPLICATES')
    white_and_srcfg=(game_ids==30)&(~bg)
    if (int(bg.sum())!=item['report']['source_background_pixels'] or
            int((game_ids==30).sum())!=item['report']['frozen_B0_white_pixels'] or
            int(white_and_srcfg.sum())!=item['report']['background_disagreement_pixels']):
        raise ValueError('BLOCKED_M1_BACKGROUND_RECONCILIATION')
    swatches=[]
    for i,color_rgb in enumerate(palette):
        owner=game_ids==i
        a=component_audit(owner & scores['chroma'])
        b=component_audit(owner & scores['union'])
        swatches.append({'index':i,'rgb':color_rgb.tolist(),'hex':'#'+''.join(f'{int(v):02X}' for v in color_rgb),
                         'total_assigned_pixels':int(owner.sum()),'suspect_chroma':a,'suspect_union':b,
                         'singleton_region_pixels':int((owner&singles).sum()),
                         'chroma_excess_on_protected_pixels':int((owner&scores['chroma']&protected).sum())})
    by_area=np.bincount(ids[ids>=0]);summary={
     'source_regions_original':int(by_area.size),'source_regions_area_hist':hist(by_area),
     'source_singletons':count,'protected_singletons':sum(r['protected'] for r in rows),
     'small_regions_area_le24':int(len(small_rows)),
     'small_regions_protected_any':int(sum(r['protected_source_pixels']>0 for r in small_rows)),
     'diagonal_only_singletons':sum(r['diagonal_only'] for r in rows),
     'fully_8_isolated_singletons':sum(r['fully_8_isolated'] for r in rows),
     'four_connected_neighbor_singletons':sum(r['four_neighbor_pixel_count']>0 for r in rows),
     'micro_merge_upper_bound_count':sum(r['safe_merge_upper_bound'] for r in rows),
     'singletons_game32_white':int(((game_ids==30)&singles).sum()),
     'source_background_pixels':int(bg.sum()),
     'B0_white_game_swatch_pixels':int((game_ids==30).sum()),
     'B0_white_source_foreground_pixels':int(white_and_srcfg.sum()),
     'chroma_suspect_pixels':int(scores['chroma'].sum()),
     'delta_e_suspect_pixels':int(scores['delta_e'].sum()),
     'hue_suspect_pixels':int(scores['hue'].sum()),
     'union_suspect_pixels':int(scores['union'].sum()),
     'chroma_suspect_at_source_singletons':int((scores['chroma']&singles).sum()),
     'chroma_suspect_at_source_protected':int((scores['chroma']&protected).sum()),
     'delta_e_source_to_G32_mean':float(np.mean(scores['delta_e_image'])),
     'delta_e_source_to_G32_p95':float(np.percentile(scores['delta_e_image'],95)),
    }
    output.mkdir(parents=True)
    imgs={
      'original_RGB.png':rgb,'B0_frozen_G32.png':g32,
      'source_singleton_regions.png':singles.astype(np.uint8)*255,
      'source_protected_union.png':protected.astype(np.uint8)*255,
      'source_background_white10.png':bg.astype(np.uint8)*255,
      'B0_white_source_foreground.png':white_and_srcfg.astype(np.uint8)*255,
      'G32_chroma_suspect_mask.png':scores['chroma'].astype(np.uint8)*255,
      'G32_deltaE_suspect_mask.png':scores['delta_e'].astype(np.uint8)*255,
      'G32_hue_suspect_mask.png':scores['hue'].astype(np.uint8)*255,
      'G32_union_suspect_mask.png':scores['union'].astype(np.uint8)*255,
      'G32_suspect_chroma_over_singleton.png':(scores['chroma']&singles).astype(np.uint8)*255,
    }
    overlay=rgb.astype(np.float32).copy()
    marked=scores['chroma']
    overlay[marked]=0.60*overlay[marked]+0.40*np.array([255,0,140],dtype=np.float32)
    imgs['DIAGNOSTIC_only_chroma_highlight_on_original.png']=np.rint(overlay).astype(np.uint8)
    for name,arr in imgs.items():image_png(output/name,arr)
    panel=Image.new('RGB',(4*150,240))
    mask=np.zeros_like(rgb);mask[scores['chroma']]=[255,255,255]
    for i,arr in enumerate((rgb,g32,mask,imgs['DIAGNOSTIC_only_chroma_highlight_on_original.png'])):
        panel.paste(Image.fromarray(arr),(i*150,0))
    panel.resize((1200,480),Image.Resampling.NEAREST).save(output/'original_B0_chroma_mask_overlay_2x.png')
    for name,(x0,y0,x1,y1) in ROI.items():
        crop=Image.new('RGB',((x1-x0)*4,y1-y0))
        for i,arr in enumerate((rgb,g32,mask,imgs['DIAGNOSTIC_only_chroma_highlight_on_original.png'])):
            crop.paste(Image.fromarray(arr).crop((x0,y0,x1,y1)),(i*(x1-x0),0))
        crop.resize((crop.width*3,crop.height*3),Image.Resampling.NEAREST).save(output/f'detail_{name}.png')
    (output/'singleton_region_ledger.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'small_region_ledger.json').write_text(json.dumps(small_rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={
      'experiment':EXP,'status':'DIAGNOSTIC_PASS_IMAGE_QUALITY_NOT_VALIDATED','model_only':True,
      'new_candidate_RGB':'NOT_RUN','no_original_or_G32_pixels_changed':True,
      'source_sha256':SOURCE_SHA,'palette_git_blob_sha':PALETTE_BLOB,'frozen_G32_index_sha256':G32_SHA,
      'm1_original_zip_sha256':M1_ZIP_SHA,'m1_original_report_sha256':M1_REPORT_SHA,
      'm1_source_commit':'5d31bcf0ef3d6f71848f7e89852c3ddf64a9d412',
      'github_sha':os.getenv('GITHUB_SHA'),'github_run_id':os.getenv('GITHUB_RUN_ID'),
      'numpy':np.__version__,'scipy':scipy.__version__,'skimage':skimage.__version__,
      'Pillow':Image.__version__,'python':platform.python_version(),
      'thresholds':{'chroma_excess':CHROMA_EXCESS,'deltaE00':DELTAE_EXCESS,
                   'source_chroma_min':SOURCE_HUE_MIN_CHROMA,'game_chroma_min':PALETTE_HUE_MIN_CHROMA,
                   'hue_delta_degrees':HUE_DIFF,'source_safe_4neighbor_deltaE00':SAFE_NEIGHBOR_DE},
      'summary':summary,'game32_swatch_diagnostics':swatches,
      'fixed_m1_report_status':item['report']['status'],'R2_M1_SOURCE_GATE_FAIL_HISTORY_RETAINED':True,
      'manual_visual':'PENDING','original_V44B_410_LAST':'UNCHANGED_NOT_OVERLAID',
      'game32_projection_candidate':'NOT_RUN','native_Egret':'NOT_RUN','game_E4':'NOT_RUN',
      'independent_E5':'NOT_RUN','exact_CHALK':None,'production_accepted':False,
      'files_sha256':{p.name:file_sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--palette',type=Path,required=True)
    p.add_argument('--m1-archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=run(a.source,a.palette,a.m1_archive,a.output)
    print(json.dumps({'experiment':EXP,'status':result['status'],'summary':result['summary']},ensure_ascii=False))
