#!/usr/bin/env python3
"""S3v2n E0: correlated alpha and integer premult transitions on genuine Egret source.

Research-only offline math; source-known E2, not new native E3, not S4 BLIND.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
from fractions import Fraction
import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import run_engine001_bpred_s3v2m_full_fractional_alpha_lattice as m
import run_engine001_bpred_s3v2l_isolated_rgb_lattice as l
import run_engine001_bpred_s3v2k_owner_alpha_interval as k

EXPERIMENT="ENGINE001_BPRED_S3V2N_CORRELATED_ALPHA_PREMULT_TRANSITIONS_V1"
E0_FILE="ENGINE001_BPRED001_S3V2N_CORRELATED_ALPHA_PREMULT_TRANSITIONS_PREREG_2026-11-20.md"
E0_BLOB="81f1a18ed5b04265123c337a3cbd63985a835307"
M_RUN="44751330819"
M_SHA="442fc99c094dda7c93af1c86354c51a905bf7200"


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3V2N_"+reason)


def floor_fraction(x:Fraction)->int:
    return x.numerator//x.denominator


def ceil_fraction(x:Fraction)->int:
    return -((-x.numerator)//x.denominator)


def nearest_even_fraction(x:Fraction)->int:
    n=floor_fraction(x)
    rem=x.numerator-n*x.denominator
    two=2*rem
    if two>x.denominator or (two==x.denominator and (n&1)):
        return n+1
    return n


def readback(p:int,alpha:Fraction)->int:
    if alpha<=0 or p<0 or p>255:
        blocked("INVALID_PREMULT_READBACK")
    ratio=Fraction(255*p,1)/alpha
    r=floor_fraction(ratio+Fraction(1,2))
    return max(0,min(255,r))


@lru_cache(maxsize=65536)
def channel_bounds(color:int,alpha_byte:int)->tuple[int,int]:
    """All physical a and the 3 p quantizers, including both transition sides.

    Exact Fraction breakpoints avoid float rounding ambiguity. For fixed p, the
    readback is nonincreasing in a, so endpoints bound an entire open interval.
    No fitting to actual native pixels or per-width lookup tables.
    """
    if (type(color) is not int or type(alpha_byte) is not int
            or not (0<=color<=255) or not (1<=alpha_byte<=254)):
        blocked("INVALID_COLOR_OR_PARTIAL_ALPHA")
    if color==0:
        return (0,2)  # original frozen ±2 uncertainty padding
    L=Fraction(2*alpha_byte-1,2)
    U=Fraction(2*alpha_byte+1,2)
    tmin=Fraction(color,255)*L
    tmax=Fraction(color,255)*U
    imin=max(0,floor_fraction(tmin)-2)
    imax=min(255,ceil_fraction(tmax)+2)
    breaks={L,U}
    for n in range(imin,imax+1):
        integer=Fraction(255*n,color)
        half=Fraction(255*(2*n+1),2*color)
        if L<integer<U:
            breaks.add(integer)
        if L<half<U:
            breaks.add(half)
    intervals=sorted(breaks)
    minima=[];maxima=[]
    def candidates(a:Fraction):
        t=Fraction(color,255)*a
        return {floor_fraction(t),ceil_fraction(t),nearest_even_fraction(t)}
    # At each discontinuity evaluate all exact boundary values.
    for a in intervals:
        for p in candidates(a):
            if 0<=p<=255:
                val=readback(p,a)
                minima.append(val);maxima.append(val)
    # On each open span, p constant. Evaluate *one-sided* limits of each p
    # with that span's endpoints; this can only over-cover any tie.
    for left,right in zip(intervals[:-1],intervals[1:]):
        middle=(left+right)/2
        for p in candidates(middle):
            if 0<=p<=255:
                minima.append(readback(p,right))
                maxima.append(readback(p,left))
    if not minima:
        blocked("EMPTY_INTEGER_LATTICE")
    low=max(0,min(minima)-2)
    high=min(255,max(maxima)+2)
    if low>high:
        blocked("INVERTED_INTEGER_LATTICE")
    return (low,high)


def g3(color,alpha):
    c=np.asarray(color,dtype=np.float64)
    a=np.asarray(alpha)
    if (c.shape!=(3,) or a.ndim!=1 or np.any(~np.isfinite(c))
            or np.any(c<0) or np.any(c>255)
            or np.any(c!=np.floor(c)) or np.any(~np.isfinite(a.astype(np.float64)))
            or np.any(a<1) or np.any(a>254) or np.any(a!=np.floor(a))):
        blocked("INVALID_COLOR_OR_PARTIAL_ALPHA")
    c=[int(x) for x in c]
    as_int=np.asarray(a,dtype=np.int16)
    lo=np.empty((len(a),3),dtype=np.uint8)
    hi=np.empty((len(a),3),dtype=np.uint8)
    for j,ch in enumerate(c):
        for A in np.unique(as_int):
            l_,u_=channel_bounds(ch,int(A))
            mask=as_int==A
            lo[mask,j]=l_
            hi[mask,j]=u_
    return lo,hi


def verify_e0(workspace):
    p=workspace/"AutoDraw_Stage20"/"docs"/E0_FILE
    if not p.is_file():
        blocked("E0_MISSING")
    raw=p.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if blob!=E0_BLOB:
        blocked("E0_BLOB_DRIFT")


def check_m_archive(z):
    names=z.namelist()
    if (len(names)!=3 or len(set(names))!=3 or z.testzip() is not None
            or any(x.startswith("/") or "\\" in x or ".." in Path(x).parts for x in names)):
        blocked("S3V2M_ARCHIVE_CRC")
    r=json.loads(z.read("report.json"))
    checks={
        "experiment":m.EXPERIMENT,"E0_blob":m.E0_BLOB,
        "source_run":m.SOURCE_RUN,"source_sha":m.SOURCE_SHA,
        "github_run_id":M_RUN,"github_sha":M_SHA,
        "source_archive_crc_sha_members":856,
        "prior_S3v2k_negative":3186,"prior_S3v2l_negative":327,
        "partial_alpha_physical_pixels":8648,"alpha16to254_pixels":7753,
        "G1_out_of_envelope_physical_pixels":0,
        "G1_recovered_prior_327":327,
        "G2_informative_alpha16to254_pixels":6360,
        "D1_source_known_G1_coverage":"PASS_SOURCE_KNOWN_ONLY",
        "D2_nonvacuous_90pct":"FAIL",
        "opaque_native_pixels":53752,
        "D3_opaque_native_RGB_exact":"PASS",
        "D3_original_C0_canvas_pass_40":31,
        "D3_original_C0_QH_webgl_pass_40":21,
        "D3_source_hidden_alpha0_owner_damage":21}
    for key,expected in checks.items():
        if r.get(key)!=expected:
            blocked("S3V2M_BASELINE_DRIFT_"+key)
    hashes=r.get("members_sha256")
    if (not isinstance(hashes,dict) or len(hashes)!=2
            or set(hashes)!=set(names)-{"report.json"}):
        blocked("S3V2M_HASH_SET")
    for name,sha in hashes.items():
        if hashlib.sha256(z.read(name)).hexdigest()!=sha:
            blocked("S3V2M_OUTPUT_SHA_"+name)
    cases=json.loads(z.read("ALL_40_G1_TRUE_ISOLATED_NATIVE_SOURCE.json"))
    misses=json.loads(z.read("ALL_G1_OUT_OF_ENVELOPE_ORIGINAL_PIXELS.json"))
    if (len(cases)!=40 or len({x["sample_id"] for x in cases})!=40
            or len(misses)!=0
            or sum(x["partial_alpha_pixels"] for x in cases)!=8648
            or sum(x["G1_width_le16_alpha16to254"] for x in cases)!=6360):
        blocked("S3V2M_CASES_DRIFT")
    return {x["sample_id"]:x for x in cases}


def bin_label(alpha):
    if alpha<=15:return "A01_15"
    if alpha<=63:return "A16_63"
    if alpha<=127:return "A64_127"
    return "A128_254"


def run(source_zip,k_zip,l_zip,m_zip,output,workspace=None):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    if workspace is not None:
        verify_e0(workspace)
    with ZipFile(source_zip) as original, ZipFile(k_zip) as older, ZipFile(l_zip) as prior, ZipFile(m_zip) as previous:
        scenes,risks=k.check_parent(original) # source archive CRC/856 SHA
        l.check_negative_archive(older)        # 3186 old negative + 3 SHA
        f2neg=m.check_l_archive(prior)          # 327 original native source physical negatives
        g1rows=check_m_archive(previous)        # G1 previous zero error, 6360 useful
        negkeys={(x["sample_id"],*x["native_physical_xy"]) for x in f2neg}
        if len(negkeys)!=327 or len(risks)!=21:
            blocked("PRIOR_NEGATIVE_OR_OWNER_COUNT")
        output.mkdir(parents=True,exist_ok=False)
        records=[];misses=[]
        bins={x:{"partial":0,"informative_G1":0,"informative_G3":0,
                 "G3_misses":0,"UNKNOWN":0}
              for x in ("A01_15","A16_63","A64_127","A128_254")}
        n=0;qualified=0;g1_useful=0;g3_useful=0
        recovered=set();opaque=0;wrong_opaque=0; g1_misses=0
        for width in k.WIDTHS:
            for relation in k.RELATIONS:
                for variant in ("A_ONLY","B_ONLY"):
                    sc=scenes[(width,relation,variant)]
                    native=k.rgba(original,sc,"ALIGNED_MAIN_RGBA")
                    color=k.rgb_owner(sc["source_strokes"][0])
                    alpha=native[:,:,3]
                    ys,xs=np.where((alpha>0)&(alpha<255))
                    rgba=native[ys,xs]
                    a=rgba[:,3].astype(np.float64)
                    lo3,hi3=g3(color,a)
                    lo1,hi1=m.g1(color,a)
                    raw=rgba[:,:3]
                    good3=np.all((raw>=lo3)&(raw<=hi3),axis=1)
                    good1=np.all((raw>=lo1)&(raw<=hi1),axis=1)
                    useful3=np.all((hi3.astype(np.int16)-lo3.astype(np.int16))<=16,axis=1)
                    useful1=np.all((hi1.astype(np.int16)-lo1.astype(np.int16))<=16,axis=1)
                    gate=(a>=16)
                    n+=len(a);qualified+=int(gate.sum())
                    g1_misses+=int((~good1).sum())
                    g1_useful+=int((gate&useful1).sum())
                    g3_useful+=int((gate&useful3).sum())
                    priorrow=g1rows.get(sc["sample_id"])
                    if (priorrow is None or priorrow["partial_alpha_pixels"]!=len(a)
                            or priorrow["G1_width_le16_alpha16to254"]!=int((gate&useful1).sum())):
                        blocked("G1_PER_CASE_DRIFT_"+sc["sample_id"])
                    for j in range(len(a)):
                        key=(sc["sample_id"],int(xs[j]),int(ys[j]))
                        binname=bin_label(int(a[j]))
                        b=bins[binname]
                        b["partial"]+=1
                        b["informative_G1"]+=int(bool(useful1[j]) and bool(gate[j]))
                        b["informative_G3"]+=int(bool(useful3[j]) and bool(gate[j]))
                        b["UNKNOWN"]+=int(not (bool(useful3[j]) and bool(gate[j])))
                        if key in negkeys and bool(good3[j]):
                            recovered.add(key)
                        if not bool(good3[j]):
                            b["G3_misses"]+=1
                            misses.append({
                                "sample_id":sc["sample_id"],"width":width,"relation":relation,
                                "variant":variant,"native_physical_xy":[int(xs[j]),int(ys[j])],
                                "actual_RGBA":rgba[j].tolist(),"source_owner_RGB":color.tolist(),
                                "G1_lower_RGB":lo1[j].tolist(),"G1_upper_RGB":hi1[j].tolist(),
                                "G3_lower_RGB":lo3[j].tolist(),"G3_upper_RGB":hi3[j].tolist(),
                                "prior_F2_negative":key in negkeys})
                    omask=alpha==255
                    opaque+=int(omask.sum())
                    wrong_opaque+=int((np.any(native[:,:,:3]!=color[None,None,:],axis=2)&omask).sum())
                    records.append({
                        "sample_id":sc["sample_id"],"width":width,"relation":relation,
                        "variant":variant,"partial_alpha_pixels":len(a),
                        "G1_misses":int((~good1).sum()),
                        "G3_misses":int((~good3).sum()),
                        "G1_informative_alpha16_254":int((gate&useful1).sum()),
                        "G3_informative_alpha16_254":int((gate&useful3).sum()),
                        "alpha16_254_count":int(gate.sum()),
                        "G3_UNKNOWN_alpha1_15":int((~gate).sum()),
                        "G3_UNKNOWN_wide_alpha16_254":int((gate&~useful3).sum()),
                        "old_F2_327_recovered":int(sum(
                            (sc["sample_id"],int(xs[j]),int(ys[j])) in negkeys and bool(good3[j])
                            for j in range(len(a))))})
        if (len(records)!=40 or len({x["sample_id"] for x in records})!=40 or
                n!=8648 or qualified!=7753 or opaque!=53752 or g1_useful!=6360 or g1_misses!=0):
            blocked("UNTOUCHED_NATIVE_G1_SOURCE_DRIFT")
        if len(recovered)+sum(bool(p["prior_F2_negative"]) for p in misses)!=327:
            blocked("F2_ORIGINAL_NEGATIVE_ACCOUNTING")
        if len(risks)!=21:
            blocked("ORIGINAL_OWNER_ALPHA0_DAMAGE_DRIFT")
        payload={
            "ALL_40_G3_CORRELATED_NATIVE_SOURCE.json":records,
            "ALL_G3_ORIGINAL_NATIVE_RGB_MISSES.json":misses,
            "G3_ORIGINAL_ALPHA_BUCKETS.json":bins}
        for name,value in payload.items():
            (output/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf8")
        report={
            "experiment":EXPERIMENT,"E0_blob":E0_BLOB,
            "github_sha":os.getenv("GITHUB_SHA"),
            "github_run_id":os.getenv("GITHUB_RUN_ID"),
            "original_source_run":m.SOURCE_RUN,"original_source_sha":m.SOURCE_SHA,
            "source_original_member_SHA_verified":856,
            "prior_S3v2k_negative_RGB":3186,
            "prior_S3v2l_F2_negative_RGB":327,
            "prior_S3v2m_run":M_RUN,"prior_S3v2m_sha":M_SHA,
            "prior_G1_misses":g1_misses,"prior_G1_informative":g1_useful,
            "prior_G1_usefulness":"FAIL_UNCHANGED",
            "original_true_isolated_scenes":40,
            "original_partial_alpha_physical_pixels":n,
            "original_alpha16_254_physical_pixels":qualified,
            "original_opaque_native_pixels":opaque,
            "G3_out_of_interval_physical_pixels":len(misses),
            "G3_recovered_prior_F2_negative":len(recovered),
            "G3_informative_alpha16_254":g3_useful,
            "G3_informative_fraction":g3_useful/qualified,
            "G3_UNKNOWN_total_partial":n-g3_useful,
            "D0_source_provenance":"PASS",
            "D1_original_RGB_coverage":"PASS_SOURCE_KNOWN_ONLY" if not misses else "FAIL",
            "D2_usefulness_frozen90pct":"PASS" if g3_useful/qualified>=.90 else "FAIL",
            "D3_opaque_owner_control":"PASS" if not wrong_opaque else "FAIL",
            "original_opaque_mismatch":wrong_opaque,
            "D4_original_C0_canvas_pass40":31,
            "D4_original_C0_QH_webgl_pass40":21,
            "D4_source_alpha0_owner_damage":21,
            "D4_S3v2k_I1":"FAIL_UNCHANGED",
            "D4_S3v2l_F2":"FAIL_UNCHANGED",
            "D4_S3v2m_G2":"FAIL_UNCHANGED",
            "original_EF_protected_quality":"FAIL_UNCHANGED",
            "source_owner_safety":"MODEL_ONLY_UNKNOWN",
            "S0_BLIND_used":False,"new_original_E3":False,
            "E4_live_game":"NOT_RUN","E5_independent":"NOT_RUN",
            "exact_game_CHALK":None,"production_promotion":False}
        report["members_sha256"]={
            name:hashlib.sha256((output/name).read_bytes()).hexdigest()
            for name in payload}
        (output/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf8")
        print("BPRED_S3V2N_SOURCE",n,"G3_MISS",len(misses),
              "F2_RECOVERED",len(recovered),"/327",flush=True)
        print("BPRED_S3V2N_USEFUL",g3_useful,"/",qualified,
              "D1",report["D1_original_RGB_coverage"],
              "D2",report["D2_usefulness_frozen90pct"],flush=True)
        return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for flag in ("source-zip","negative-zip","lattice-zip","previous-zip","output","workspace"):
        ap.add_argument("--"+flag,type=Path,required=flag!="workspace")
    args=ap.parse_args()
    run(args.source_zip,args.negative_zip,args.lattice_zip,
        args.previous_zip,args.output,args.workspace)
