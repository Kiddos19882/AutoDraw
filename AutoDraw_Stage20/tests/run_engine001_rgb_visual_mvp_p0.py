#!/usr/bin/env python3
"""ENGINE001 RGB visual MVP P0: standalone source-only prefilter; no game/Egret fill."""
from __future__ import annotations
import argparse,hashlib,io,json,platform,zipfile
from pathlib import Path
import cv2,numpy as np,skimage
from PIL import Image,ImageDraw,ImageFont
from skimage import color,filters

EXP='ENGINE001_RGB_VISUAL_MVP_P0_EDGE_AWARE_PREFILTER'
SOURCE_SHA='07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a'
M1_SHA='8bedc496bf01cf7205ecc8ceb7be8eb0f68b751b11c53ea67dbdd3982c7fe583'
M1_REPORT_SHA='89e4135ecd71820e21394751bb4a11f9a17b01edcddcfa6f1bd1f538f8a16969'
V44_SHA='43cb8e14a7e387b26772612ac06d1c7c6f176b8bd0c2d41e8945042fc80304a1'
V44_IMAGE_SHA='0145975e4578bc86c1e4feb44d5ff93ecd486d576faf97626e1267a5c12b0275'
V44_PLAN_SHA='9db4dda0661ea529547e91a09dcae38b27043dad57383fb483b945f0de08496a'
METHODS={
'BILATERAL_LOW':{'op':'bilateral','d':5,'sigmaColor':18,'sigmaSpace':2.0},
'BILATERAL_MID':{'op':'bilateral','d':7,'sigmaColor':28,'sigmaSpace':3.0},
'MEANSHIFT_LOW':{'op':'meanshift','sp':5,'sr':15,'maxLevel':0},
'MEANSHIFT_MID':{'op':'meanshift','sp':7,'sr':25,'maxLevel':0}}
def sha(blob): return hashlib.sha256(blob).hexdigest()
def archive(path,expected):
    b=Path(path).read_bytes()
    if sha(b)!=expected: raise ValueError('BLOCKED_ZIP_SHA')
    z=zipfile.ZipFile(io.BytesIO(b))
    if z.testzip() is not None: raise ValueError('BLOCKED_ZIP_CRC')
    return z
def inputs(source,m1zip,v44zip):
    data=Path(source).read_bytes()
    if sha(data)!=SOURCE_SHA: raise ValueError('BLOCKED_SOURCE_SHA')
    full=np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))
    if full.shape!=(320,200,3):raise ValueError('BLOCKED_FULL_SIZE')
    with archive(m1zip,M1_SHA) as m,archive(v44zip,V44_SHA) as v:
        if sha(m.read('report.json'))!=M1_REPORT_SHA:raise ValueError('BLOCKED_M1_REPORT')
        mr=json.loads(m.read('report.json'))
        if (mr.get('github_sha')!='5d31bcf0ef3d6f71848f7e89852c3ddf64a9d412'
             or mr.get('source_sha256')!=SOURCE_SHA):raise ValueError('BLOCKED_M1_PROVENANCE')
        names=('original_RGB.png','M1_MERGED_RGB.png','source_protected_union.png')
        for n in names:
            if sha(m.read(n))!=mr.get('file_sha256',{}).get(n):raise ValueError('BLOCKED_M1_MEMBER')
        raw=np.asarray(Image.open(io.BytesIO(m.read(names[0]))).convert('RGB'))
        frozen=np.asarray(Image.open(io.BytesIO(m.read(names[1]))).convert('RGB'))
        protected=np.asarray(Image.open(io.BytesIO(m.read(names[2]))).convert('L'))>0
        if raw.shape!=(240,150,3) or frozen.shape!=raw.shape or protected.shape!=(240,150):
            raise ValueError('BLOCKED_ROI_SHAPE')
        if not np.array_equal(raw,np.asarray(Image.fromarray(full).resize((150,240),Image.Resampling.LANCZOS))):
            raise ValueError('BLOCKED_RESIZE_DRIFT')
        if sha(v.read('B/V44-B-color-100.png'))!=V44_IMAGE_SHA or sha(v.read('color-plans.json'))!=V44_PLAN_SHA:
            raise ValueError('BLOCKED_V44_SHA')
        p=json.loads(v.read('color-plans.json'))['plans']['B']['strokes']
        detail=p[-410:]
        if (len(p)!=2355 or len(detail)!=410 or sum(len(e['stroke']['points']) for e in detail)!=1792 or
            any(e['layer']!='detail' or e['stroke']['width']!=1 or e['stroke']['colorIndex']!=100 or
                e['stroke']['strokeId']!=f'detail-v18-B-{i}' for i,e in enumerate(detail))):
            raise ValueError('BLOCKED_V44_DETAIL_IDENTITY')
        contour=Image.open(io.BytesIO(v.read('B/V44-B-color-100.png'))).convert('RGBA')
        if contour.size!=(1380,720):raise ValueError('BLOCKED_V44_BACKING')
    return full,raw,frozen,protected,contour
def filter_candidate(full,method,raw,protected):
    if full.shape!=(320,200,3) or full.dtype!=np.uint8 or raw.shape!=(240,150,3) or protected.shape!=(240,150):
        raise ValueError('BLOCKED_SHAPE')
    if method['op']=='bilateral':
        f=cv2.bilateralFilter(full,method['d'],method['sigmaColor'],method['sigmaSpace'])
    elif method['op']=='meanshift':
        f=cv2.pyrMeanShiftFiltering(full,method['sp'],method['sr'],maxLevel=method['maxLevel'])
    else:raise ValueError('BLOCKED_METHOD')
    out=np.asarray(Image.fromarray(f).resize((150,240),Image.Resampling.LANCZOS)).copy()
    out[protected]=raw[protected]
    if not np.array_equal(out[protected],raw[protected]):raise AssertionError('PROTECTED_CHANGED')
    return out
def composite(roi,contour):
    # Reuse previously validated P4b layout/alpha method; no synthetic outline.
    from run_engine001_color32_s2b_p4b_v44b_hybrid import compose
    _,screen=compose(Image.fromarray(roi),contour)
    return screen.crop((465,0,915,720)).convert('RGB')
def metrics(source,rgb,protected,contour,edge,thr,low):
    d=color.deltaE_ciede2000(color.rgb2lab(source/255.),color.rgb2lab(rgb/255.))
    g=filters.sobel(color.rgb2gray(rgb/255.))
    alpha=np.asarray(contour.getchannel('A'))[:,465:915].reshape(240,3,150,3).mean(axis=(1,3))
    trace=alpha>=24
    mask=low&~protected
    hor=mask[:,:-1]&mask[:,1:];ver=mask[:-1,:]&mask[1:,:]
    def rough(x):
        x=x.astype(np.float32)
        dx=np.abs(x[:,:-1]-x[:,1:]).mean(2)
        dy=np.abs(x[:-1,:]-x[1:,:]).mean(2)
        return float((dx[hor].sum()+dy[ver].sum())/max(1,int(hor.sum()+ver.sum())))
    prev=rough(source);new=rough(rgb)
    r={'whole_mean_deltaE00':float(d.mean()),'whole_p95_deltaE00':float(np.percentile(d,95)),
       'contour_alpha24_mean_deltaE00':float(d[trace].mean()),
       'protected_pixels':int(protected.sum()),'protected_exact':bool(np.array_equal(source[protected],rgb[protected])),
       'fixed_source_strong_sobel_overlap':float((edge&(g>=thr)).sum()/max(1,int(edge.sum()))),
       'flat_region_roughness_original':prev,'flat_region_roughness_candidate':new,
       'flat_region_roughness_reduction':float(1-new/max(1e-9,prev)),
       'changed_pixels':int(np.any(rgb!=source,axis=2).sum()),
       'distinct_RGB_colors':int(np.unique(rgb.reshape(-1,3),axis=0).shape[0])}
    passed=(r['protected_exact'] and r['whole_mean_deltaE00']<=3 and r['whole_p95_deltaE00']<=12
            and r['contour_alpha24_mean_deltaE00']<=6 and r['fixed_source_strong_sobel_overlap']>=.85
            and r['flat_region_roughness_reduction']>=.05)
    r['source_gate']='SOURCE_SCREEN_PASS_VISUAL_PENDING' if passed else 'SOURCE_GATE_FAIL'
    return r
def sheet(variants,contour,path,with_contour):
    names=list(variants)
    labels=['Оригинал RGB','M1 (архив)','Bilateral мягкий','Bilateral средний','Mean shift мягкий','Mean shift средний']
    out=Image.new('RGB',(1350,1512),'white');dr=ImageDraw.Draw(out)
    try:font=ImageFont.truetype('DejaVuSans.ttf',19)
    except OSError:font=ImageFont.load_default()
    for i,name in enumerate(names):
        row,col=divmod(i,3);x=col*450;y=row*756
        im=(composite(variants[name],contour) if with_contour else
            Image.fromarray(variants[name]).resize((450,720),Image.Resampling.NEAREST))
        out.paste(im,(x,y+36));dr.text((x+8,y+6),labels[i],font=font,fill='black')
    out.save(path)
def run(source,m1,v44,out):
    if out.exists():raise ValueError('BLOCKED_OUTPUT_EXISTS')
    full,original,old,protected,contour=inputs(source,m1,v44)
    grad=filters.sobel(color.rgb2gray(original/255.))
    positive=grad[grad>0]
    threshold=float(np.percentile(positive,90))
    edge=grad>=threshold
    low=(grad>0)&(grad<np.percentile(positive,50))
    variants={'ORIGINAL_RGB':original,'M1_MERGED':old}
    for n,par in METHODS.items():variants[n]=filter_candidate(full,par,original,protected)
    out.mkdir(parents=True)
    result={}
    for n,rgb in variants.items():
        Image.fromarray(rgb).save(out/(n+'_RGB.png'))
        composite(rgb,contour).save(out/(n+'_plus_original_V44B.png'))
        result[n]=metrics(original,rgb,protected,contour,edge,threshold,low)
    sheet(variants,contour,out/'comparison_RGB.png',False)
    sheet(variants,contour,out/'comparison_with_native_V44B.png',True)
    hashes={p.name:sha(p.read_bytes()) for p in sorted(out.iterdir()) if p.is_file()}
    report={'experiment':EXP,'status':'SOURCE_VISUAL_EXPERIMENT_NOT_GAME_VALIDATED',
            'source_sha256':SOURCE_SHA,'m1_zip_sha256':M1_SHA,'v44_zip_sha256':V44_SHA,
            'contour_native_SHA256':V44_IMAGE_SHA,'contour_strokes':410,'contour_vertices_not_CHALK':1792,
            'protected_pixels':int(protected.sum()),'source_sobel90_threshold':threshold,
            'methods':METHODS,'metrics':result,'file_sha256':hashes,
            'github_sha':__import__('os').environ.get('GITHUB_SHA'),
            'github_run_id':__import__('os').environ.get('GITHUB_RUN_ID'),
            'versions':{'python':platform.python_version(),'numpy':np.__version__,'OpenCV':cv2.__version__,
                        'Pillow':Image.__version__,'skimage':skimage.__version__},
            'human_visual':'PENDING','native_Egret_fill':'NOT_RUN','game_E4':'NOT_RUN','game_E5':'NOT_RUN','exact_CHALK':None}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--m1-archive',type=Path,required=True)
    p.add_argument('--v44-archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    report=run(a.source,a.m1_archive,a.v44_archive,a.output)
    print(json.dumps({k:v['source_gate'] for k,v in report['metrics'].items()},ensure_ascii=False))
