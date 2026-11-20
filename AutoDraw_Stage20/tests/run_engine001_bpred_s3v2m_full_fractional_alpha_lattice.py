#!/usr/bin/env python3
"""S3v2m: frozen full fractional-alpha premult integer bounds on genuine Egret PNG."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image
import run_engine001_bpred_s3v2l_isolated_rgb_lattice as l
import run_engine001_bpred_s3v2k_owner_alpha_interval as k

EXPERIMENT="ENGINE001_BPRED_S3V2M_FULL_FRACTIONAL_ALPHA_INTEGER_LATTICE_V1"
E0_FILE="ENGINE001_BPRED001_S3V2M_FULL_FRACTIONAL_ALPHA_INTEGER_LATTICE_PREREG_2026-11-20.md"
E0_BLOB="33d40233c271bb8086d1d9c01d45eef3b401679e"
L_RUN="44743578450"
L_SHA="bc4d45e8ad5d1d063bbb750ce78c19452fff7e09"
SOURCE_RUN="44721915503"
SOURCE_SHA="ad1fa7fd66d4df563d729b7faae27651ca8279ea"

def blocked(s):
    raise ValueError("BLOCKED_BPRED_S3V2M_"+s)

def g1(color,alpha):
    """All alpha in [A-.5,A+.5], all p floor/rint/ceil, conservative extrema."""
    c=np.asarray(color,dtype=np.float64)
    a=np.asarray(alpha,dtype=np.float64)
    if c.shape!=(3,) or a.ndim!=1 or np.any(~np.isfinite(c)) or np.any(c<0) or np.any(c>255) or np.any(~np.isfinite(a)) or np.any(a<1) or np.any(a>254):
        blocked("INVALID_COLOR_OR_PARTIAL_ALPHA")
    low_a=a-.5
    high_a=a+.5
    pmin=np.floor(c[None,:]*low_a[:,None]/255.)
    pmax=np.ceil(c[None,:]*high_a[:,None]/255.)
    low=np.clip(np.floor(255.*pmin/high_a[:,None]+.5)-2.,0.,255.)
    high=np.clip(np.floor(255.*pmax/low_a[:,None]+.5)+2.,0.,255.)
    if np.any(low>high):
        blocked("INVERTED_INTERVAL")
    return low.astype(np.uint8),high.astype(np.uint8)

def check_l_archive(z):
    members=z.namelist()
    if len(members)!=3 or len(set(members))!=3 or z.testzip() is not None:
        blocked("S3V2L_CRC_OR_SET")
    r=json.loads(z.read("report.json"))
    frozen={"experiment":l.EXPERIMENT,"E0_blob":l.E0_BLOB,"source_sha":SOURCE_SHA,
            "source_run":SOURCE_RUN,"github_sha":L_SHA,"github_run_id":L_RUN,
            "F2_lattice_outside_physical_pixels":327,
            "partial_alpha_physical_pixels":8648,
            "F3_alpha255_physical_pixels":53752,
            "original_C0_canvas_pass_40":31,"original_C0_QH_webgl_pass_40":21,
            "source_hidden_alpha0_changed_owner_pixels":21}
    for name,value in frozen.items():
        if r.get(name)!=value:
            blocked("S3V2L_BASELINE_DRIFT_"+name)
    hashes=r.get("members_sha256")
    if not isinstance(hashes,dict) or len(hashes)!=2 or set(hashes)!=set(members)-{"report.json"}:
        blocked("S3V2L_HASH_SET")
    for name,sha in hashes.items():
        if hashlib.sha256(z.read(name)).hexdigest()!=sha:
            blocked("S3V2L_HASH_"+name)
    negatives=json.loads(z.read("ALL_F2_PHYSICAL_RGB_OUTSIDE_FIXED_LATTICE.json"))
    if len(negatives)!=327:
        blocked("S3V2L_327_DRIFT")
    return negatives

def verify_e0(workspace):
    p=workspace/"AutoDraw_Stage20"/"docs"/E0_FILE
    if not p.is_file():
        blocked("E0_MISSING")
    raw=p.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if blob!=E0_BLOB:
        blocked("E0_BLOB_DRIFT")

def run(source_zip,k_zip,l_zip,output,workspace=None):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    if workspace is not None:
        verify_e0(workspace)
    with ZipFile(source_zip) as source,ZipFile(k_zip) as old,ZipFile(l_zip) as recent:
        scenes,risks=k.check_parent(source)
        l.check_negative_archive(old)
        negatives=check_l_archive(recent)
        original_negative_keys={(p["sample_id"],*p["native_physical_xy"]) for p in negatives}
        if len(original_negative_keys)!=327:
            blocked("DUPLICATE_327_NEGATIVE")
        output.mkdir(parents=True,exist_ok=False)
        rows=[];misses=[];recovered=set()
        total=0;informative=0;qualified=0;opaque=0;opaque_wrong=0
        for w in k.WIDTHS:
            for relation in k.RELATIONS:
                for variant in ("A_ONLY","B_ONLY"):
                    case=scenes[(w,relation,variant)]
                    native=k.rgba(source,case,"ALIGNED_MAIN_RGBA")
                    color=k.rgb_owner(case["source_strokes"][0])
                    alpha=native[:,:,3]
                    ys,xs=np.where((alpha>0)&(alpha<255))
                    rgba=native[ys,xs]
                    a=rgba[:,3].astype(np.float64)
                    lo,hi=g1(color,a)
                    actual=rgba[:,:3]
                    covered=np.all((actual>=lo)&(actual<=hi),axis=1)
                    widths=hi.astype(np.int16)-lo.astype(np.int16)
                    useful=np.all(widths<=16,axis=1)
                    q=a>=16
                    total+=len(a)
                    qualified+=int(q.sum())
                    informative+=int((q&useful).sum())
                    for i in range(len(a)):
                        key=(case["sample_id"],int(xs[i]),int(ys[i]))
                        if key in original_negative_keys and covered[i]:
                            recovered.add(key)
                        if not covered[i]:
                            misses.append({"sample_id":case["sample_id"],"width":w,"relation":relation,
                                           "variant":variant,"native_physical_xy":[int(xs[i]),int(ys[i])],
                                           "owner_RGB":color.tolist(),"actual_RGBA":rgba[i].tolist(),
                                           "G1_lower_RGB":lo[i].tolist(),"G1_upper_RGB":hi[i].tolist(),
                                           "was_F2_negative":key in original_negative_keys})
                    opaque_mask=alpha==255
                    opaque+=int(opaque_mask.sum())
                    opaque_wrong+=int((np.any(native[:,:,:3]!=color[None,None,:],axis=2)&opaque_mask).sum())
                    rows.append({"sample_id":case["sample_id"],"width":w,"relation":relation,
                                 "variant":variant,"partial_alpha_pixels":len(a),
                                 "G1_misses":int((~covered).sum()),
                                 "G1_qualified_alpha16to254":int(q.sum()),
                                 "G1_width_le16_alpha16to254":int((q&useful).sum()),
                                 "G2_unknown_low_alpha":int((a<=15).sum()),
                                 "G2_unknown_wide_alpha16to254":int((q&~useful).sum()),
                                 "G1_recovered_F2_negative":sum((case["sample_id"],int(xs[i]),int(ys[i])) in original_negative_keys and covered[i] for i in range(len(a)))})
        if len(rows)!=40 or total!=8648 or qualified!=7753 or opaque!=53752 or len(original_negative_keys)!=327:
            blocked("ORIGINAL_NATIVE_SOURCE_DRIFT")
        if len(recovered)+sum(m["was_F2_negative"] for m in misses)!=327:
            blocked("NEGATIVE_ACCOUNTING")
        if len(risks)!=21:
            blocked("OWNER_ALPHA0_RISK_DRIFT")
        output_files={
            "ALL_40_G1_TRUE_ISOLATED_NATIVE_SOURCE.json":rows,
            "ALL_G1_OUT_OF_ENVELOPE_ORIGINAL_PIXELS.json":misses}
        for name,data in output_files.items():
            (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
        r={"experiment":EXPERIMENT,"E0_blob":E0_BLOB,"github_sha":os.getenv("GITHUB_SHA"),
           "github_run_id":os.getenv("GITHUB_RUN_ID"),
           "source_run":SOURCE_RUN,"source_sha":SOURCE_SHA,
           "source_archive_crc_sha_members":856,"prior_S3v2k_negative":3186,
           "prior_S3v2l_negative":327,"prior_S3v2l_sha":L_SHA,
           "partial_alpha_physical_pixels":total,"alpha16to254_pixels":qualified,
           "G1_out_of_envelope_physical_pixels":len(misses),
           "G1_recovered_prior_327":len(recovered),
           "G2_informative_alpha16to254_pixels":informative,
           "G2_informative_fraction":informative/qualified,
           "D0_source_negative_integrity":"PASS",
           "D1_source_known_G1_coverage":"PASS_SOURCE_KNOWN_ONLY" if not misses else "FAIL",
           "D2_nonvacuous_90pct":"PASS" if informative/qualified>=.90 else "FAIL",
           "D3_opaque_native_RGB_exact":"PASS" if opaque_wrong==0 else "FAIL",
           "opaque_native_pixels":opaque,"opaque_owner_wrong_pixels":opaque_wrong,
           "D3_original_C0_canvas_pass_40":31,"D3_original_C0_QH_webgl_pass_40":21,
           "D3_source_hidden_alpha0_owner_damage":21,
           "D3_S3v2k_source_owner_interval":"FAIL_UNCHANGED",
           "D3_S3v2l_F2":"FAIL_UNCHANGED",
           "original_EF_protected_quality":"FAIL_UNCHANGED",
           "S0_BLIND_used":False,"new_native_E3":False,"E4_game":"NOT_RUN",
           "E5_independent":"NOT_RUN","exact_game_CHALK":None,
           "source_owner_safety":"MODEL_ONLY_UNKNOWN","production_promotion":False}
        r["members_sha256"]={name:hashlib.sha256((output/name).read_bytes()).hexdigest()
                              for name in output_files}
        (output/"report.json").write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
        print("BPRED_S3V2M_G1",r["D1_source_known_G1_coverage"],len(misses),
              "recovered",len(recovered),"/327",flush=True)
        print("BPRED_S3V2M_G2",r["D2_nonvacuous_90pct"],informative,qualified,flush=True)
        return r

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for flag in ("source-zip","negative-zip","lattice-zip","output","workspace"):
        ap.add_argument("--"+flag,required=flag!="workspace",type=Path)
    a=ap.parse_args()
    run(a.source_zip,a.negative_zip,a.lattice_zip,a.output,a.workspace)
