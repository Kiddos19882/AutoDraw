#!/usr/bin/env python3
"""VIS1 real AutoDraw original-source visual review ZIP directory builder.

Only PIL/NumPy rendering of actual frozen original RGB, math masks and already
existing source-only AWEAK2/AWEAK3 proposals. No image generation or new model.
Neither hypothetical core nor palette preview authorizes an Egret/game stroke.
No derived pixel outputs from any LOCKED_HELDOUT image, even thumbnails.
"""
from __future__ import annotations

import argparse
from html import escape
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from engine001_bpred_s4r1_generic_source_maps import (
    decode_original, generic_source_maps, original_source_region_uncertainty,
    provisional_game128_owner_maps, git_blob_sha1,
)
from engine001_bpred_s4r1_semref1_human_review_validation import (
    CODES, SELECTED, validated_review, FORBIDDEN,
)
from run_engine001_bpred_s4r1_semref1_aqa1_uploaded_a_intake import (
    REL_A, audit as audit_aqa1,
)
from run_engine001_bpred_s4r1_corpus_integrity import (
    REL_CORPUS, REL_E0, audit as audit_corpus, manifest,
)
from run_engine001_b1r_p3b_engine128_adaptive32 import read_engine_palette
from run_engine001_bpred_s4r1_aweak2_multiscale_lab_source_proposal import (
    source_multiscale_lab_proposal,
)
from run_engine001_bpred_s4r1_aweak3_perceptual_slic_coherence import (
    coherence_trial, compare_weak_mark_tradeoff,
)

VERSION = "ENGINE001_BPRED_S4R1_VIS1_REAL_SOURCE_V1"
E0_PATH = ("AutoDraw_Stage20/docs/"
           "ENGINE001_BPRED001_S4R1_VIS1_LATEST_SOURCE_MAP_VISUAL_REVIEW_SPEC_2026-11-21.md")
E0_BLOB = "1c67aaec9d3238695d1631be607d3db8f8337105"
RGBA_WHITE = (255,255,255,255)
COLORS = {
    "source_edges": (239,62,73),
    "protected": (222,60,77),
    "unknown": (233,174,65),
    "hypothetical_core": (29,193,161),
    "slic_warning": (188,90,241),
    "aweak2_added": (255,114,32),
    "aweak3_new": (39,218,154),
    "aweak3_K_risk": (241,48,65),
    "aweak3_I_gain": (18,218,132),
    "human_critical": (255,0,255),
    "human_boundary": (0,255,255),
    "human_interior": (0,255,0),
    "human_ambiguous": (255,255,0),
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def white_composite(rgba: np.ndarray) -> np.ndarray:
    """Display-only white backdrop, preserves original opaque values."""
    if rgba.dtype != np.uint8 or rgba.ndim!=3 or rgba.shape[2]!=4:
        raise ValueError("BLOCKED_VIS1_RGB_SOURCE_FORMAT")
    image = Image.fromarray(rgba,mode="RGBA")
    board = Image.new("RGBA", image.size, RGBA_WHITE)
    return np.asarray(Image.alpha_composite(board,image).convert("RGB")).copy()


def overlay(original_rgb: np.ndarray, mask: np.ndarray,
            col: tuple[int,int,int], opacity: float=0.72) -> np.ndarray:
    """Colorize only display pixels; never change source/regions."""
    if (not isinstance(original_rgb,np.ndarray) or original_rgb.dtype!=np.uint8
            or original_rgb.ndim!=3 or original_rgb.shape[2]!=3
            or not isinstance(mask,np.ndarray) or mask.dtype!=bool
            or mask.shape!=original_rgb.shape[:2]
            or not (0<=opacity<=1)):
        raise ValueError("BLOCKED_VIS1_OVERLAY_DIMENSIONS")
    output=original_rgb.copy()
    tint=np.asarray(col,np.float32)
    output[mask]=np.clip(np.rint(
        original_rgb[mask].astype(np.float32)*(1-opacity)+tint*opacity
    ),0,255).astype(np.uint8)
    return output


def protected_unknown_preview(display_rgb: np.ndarray, maps: dict) -> np.ndarray:
    """Red = protected evidence; gold = UNKNOWN, NEVER safe."""
    if (np.any(maps["protected"] & maps["unknown"]) or
            not np.all(maps["protected"] | maps["unknown"])):
        raise ValueError("BLOCKED_VIS1_PROTECTED_UNKNOWN_INVALID")
    result=overlay(display_rgb,maps["unknown"],COLORS["unknown"],0.74)
    result=overlay(result,maps["protected"],COLORS["protected"],0.82)
    return result


def human_A_preview(display_rgb: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Incomplete user strokes are unreviewed/transparent, not negatives."""
    if display_rgb.shape[:2]!=labels.shape[:2] or labels.dtype!=np.uint8:
        raise ValueError("BLOCKED_VIS1_HUMAN_VISUAL_SOURCE_DIMS")
    out=display_rgb.copy()
    for i,category in enumerate(("unused","human_critical","human_boundary",
                                 "human_interior","human_ambiguous")):
        if i==0:continue
        m=np.all(labels==CODES[i],axis=2)
        out[m]=overlay(out,m,COLORS[category],0.80)[m]
    return out


def AWEAK3_conflict_preview(display_rgb: np.ndarray, labels: np.ndarray,
                             added: np.ndarray) -> np.ndarray:
    """Compare source-derived AWEAK3 new hypothetical core vs weak A hints."""
    if display_rgb.shape[:2]!=labels.shape[:2] or added.shape!=labels.shape[:2]:
        raise ValueError("BLOCKED_VIS1_CONFLICT_SHAPE")
    out=display_rgb.copy()
    K=np.all(labels==CODES[1],axis=2)|np.all(labels==CODES[2],axis=2)
    I=np.all(labels==CODES[3],axis=2)
    out=overlay(out,added & I,COLORS["aweak3_I_gain"],0.88)
    out=overlay(out,added & K,COLORS["aweak3_K_risk"],0.95)
    return out


def full_rgb_png(path: Path, pixels: np.ndarray, wh: tuple[int,int]) -> str:
    """All source preview PNGs are true source resolution, never thumbnails."""
    if pixels.dtype!=np.uint8 or pixels.shape!=(wh[1],wh[0],3):
        raise ValueError("BLOCKED_VIS1_NON_NATIVE_SOURCE_IMAGE_SHAPE")
    im=Image.fromarray(pixels,mode="RGB")
    im.save(path)
    with Image.open(path) as check:
        check.load()
        if check.size!=wh or check.mode!="RGB":
            raise ValueError("BLOCKED_VIS1_PNG_VERIFY_SIZE_MODE")
    return sha256_file(path)


def rgb_font(size: int, bold: bool=False):
    name=("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    for prefix in ("/usr/share/fonts/truetype/dejavu/",""):
        try:
            return ImageFont.truetype(prefix+name,size)
        except OSError:
            pass
    return ImageFont.load_default()


def placeholder(wh: tuple[int,int], caption: str) -> np.ndarray:
    im=Image.new("RGB",wh,(229,232,235))
    d=ImageDraw.Draw(im)
    f=rgb_font(18,True)
    d.multiline_text((15,max(10,wh[1]//2-25)),caption,
                     font=f,fill=(75,85,98),spacing=5)
    return np.asarray(im,dtype=np.uint8)


PANELS = (
    ("01_original_view","01  ORIGINAL RGB"),
    ("02_proposed_game128","02  GAME128 PROPOSAL"),
    ("03_slic_medoids","03  SLIC COLOR AREAS"),
    ("04_original_edges_overlay","04  SOURCE RGB EDGES"),
    ("05_protected_unknown","05  RED=PROTECTED / GOLD=UNKNOWN"),
    ("06_p2_geometric_core","06  P2 HYPOTHETICAL CORE"),
    ("07_region_warning_overlay","07  P2 REGION WARNINGS"),
    ("08_aweak2_lab_protected_additions","08  AWEAK2 ADDED PROTECTION"),
    ("09_aweak3_core_trial","09  AWEAK3 HYPOTHETICAL CORE"),
    ("10_aweak3_new_potential_core","10  AWEAK3 NEW POTENTIAL"),
    ("11_human_A_hints_overlay","11  HUMAN A WEAK HINTS"),
    ("12_aweak3_A_conflict_overlay","12  AWEAK3 vs HUMAN A"),
)


def contact_sheet(panels: dict[str,np.ndarray|None],label: str) -> Image.Image:
    """12 labeled tiles, whitespace padded, never change saved source masks."""
    cell_w,cell_h=360,270
    top=62
    columns=4
    sheet=Image.new("RGB",(cell_w*columns,top+cell_h*3),(240,243,247))
    d=ImageDraw.Draw(sheet)
    d.rectangle((0,0,sheet.width,top),fill=(19,33,47))
    d.text((19,11),label,font=rgb_font(21,True),fill=(250,250,250))
    d.text((20,37),"SOURCE ONLY | RESEARCH | HYPOTHETICAL IS NOT SAFE",
           font=rgb_font(12),fill=(189,209,224))
    for i,(key,title) in enumerate(PANELS):
        x=(i%columns)*cell_w
        y=top+(i//columns)*cell_h
        d.rectangle((x+4,y+5,x+cell_w-5,y+cell_h-5),fill=(255,255,255),
                    outline=(210,218,228),width=1)
        d.text((x+11,y+12),title,font=rgb_font(12,True),fill=(25,44,61))
        arr=panels.get(key)
        if arr is None:
            arr=placeholder((340,224),"NOT APPLICABLE\n(no opaque input / A review)")
        src=Image.fromarray(arr,mode="RGB")
        src.thumbnail((cell_w-20,cell_h-52),resample=Image.Resampling.LANCZOS)
        start=x+(cell_w-src.width)//2
        line=y+40+(cell_h-52-src.height)//2
        sheet.paste(src,(start,line))
    return sheet


def html_index(rows: list[dict]) -> str:
    style="""body{background:#101a26;color:#eef3fa;font-family:Arial,sans-serif;margin:0 auto;padding:26px;max-width:1500px}
a{color:#7ed5ed}section{background:#1b2c3e;border-radius:16px;padding:14px 20px;margin-bottom:22px}
img{max-width:100%;height:auto;border-radius:10px}small{color:#a6b8c8}.alert{color:#ffd28a}h1{font-size:27px}"""
    entries=[]
    for row in rows:
        folder=escape(row["id"])
        name=escape(row["original_filename"])
        role=escape(row["role"])
        state=escape(row["AWEAK3_status"])
        entries.append(
            f'<section><h2>{name} <small>{role}</small></h2>'
            f'<p class="alert">AWEAK3: {state}; A hints: {bool(row["human_A"])}</p>'
            f'<a href="{folder}/00_contact_sheet.png"><img loading="lazy" src="{folder}/00_contact_sheet.png" alt="Visual contact sheet {name}"></a>'
            f'<p><a href="{folder}/01_original_view.png">Original pixels</a> · '
            f'<a href="{folder}/03_slic_medoids.png">SLIC colors</a> · '
            f'<a href="{folder}/05_protected_unknown.png">Protected/UNKNOWN</a> · '
            f'<a href="{folder}/06_p2_geometric_core.png">P2 core</a> · '
            f'<a href="{folder}/raw_original{escape(Path(row["original_filename"]).suffix)}">Raw source bytes</a></p></section>'
        )
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>AutoDraw VIS1 source maps review</title>'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><style>'
            +style+'</style></head><body><h1>AutoDraw VIS1 — исходные карты, S4-R1</h1>'
            '<p class="alert">Настоящие карты программных алгоритмов. Это НЕ финальный результат игровой кисти. '
            'Красный = source protected, золото = UNKNOWN, зелёный = математически потенциальная область, НЕ доказанная SAFE. '
            'AWEAK2/AWEAK3 — только отвергнутые для production эксперименты. '
            'В сборке нет закрытых H8/BLIND120 изображений.</p>'
            +''.join(entries)+'</body></html>\n')


def build(root: Path,out: Path) -> dict:
    e0=root/E0_PATH
    if git_blob_sha1(e0.read_bytes())!=E0_BLOB:
        raise ValueError("BLOCKED_VIS1_FROZEN_OUTPUT_PROTOCOL_CHANGED")
    identities=audit_corpus(root)
    if identities["perceptual_screen"]!="PASS_SOURCE_PRE_SCREEN_ONLY":
        raise ValueError("BLOCKED_VIS1_CROSS_SPLIT_SCREEN")
    frozen=manifest(root/REL_E0)
    select={r["file"]:r for r in frozen if r["role"]!="LOCKED_HELDOUT"}
    if len(select)!=23 or sum(r["role"]=="DEV" for r in select.values())!=15:
        raise ValueError("BLOCKED_VIS1_EXPECT_15DEV_8KNOWN_NO_HELDOUT")
    aqa=audit_aqa1(root)
    if (aqa["pairs_a_checked"]!=4 or aqa["pairs_b_checked"]!=0
            or aqa["technical_status"]!="PASS_A_ONLY_SOURCE_AND_LABEL_INTEGRITY"):
        raise ValueError("BLOCKED_VIS1_AQA1_PROVENANCE")
    game128,engine_provenance=read_engine_palette(
        root/"AutoDraw_Stage20/gameEngine/main.min_653f95bc.js"
    )
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    detailed=[]
    for entry in identities["records"]:
        name=entry["file"]
        if entry["role"]=="LOCKED_HELDOUT":
            # Audit already checked identity only; no map/preview generation.
            continue
        if name not in select:
            raise ValueError("BLOCKED_VIS1_UNFROZEN_ROLE")
        original_path=root/REL_CORPUS/name
        raw=original_path.read_bytes()
        decoded=decode_original(raw)
        if (decoded["git_blob_sha1"]!=select[name]["git_blob"]
                or decoded["sha256"]!=entry["sha256"]):
            raise ValueError("BLOCKED_VIS1_ORIGINAL_BYTES_DIFFER")
        rgba=decoded["rgba"]
        original_copy=rgba.copy()
        hw=tuple(rgba.shape[:2])
        wh=(decoded["width"],decoded["height"])
        image_id=hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        folder=out/image_id
        folder.mkdir(parents=True,exist_ok=False)
        original_file=folder/("raw_original"+Path(name).suffix)
        shutil.copyfile(original_path,original_file)
        if original_file.read_bytes()!=raw:
            raise ValueError("BLOCKED_VIS1_RAW_ORIGINAL_NOT_BYTE_IDENTICAL")
        source=generic_source_maps(rgba)
        regions=original_source_region_uncertainty(rgba,source)
        proposal=provisional_game128_owner_maps(raw,game128,engine_provenance)
        if (source["owner_status"]!="MISSING"
                or regions["source_owner_status"]!="MISSING"
                or proposal["source_owner_status"]!="MISSING"
                or source["stroke_admission"]!=FORBIDDEN
                or regions["stroke_admission"]!=FORBIDDEN
                or np.any(source["candidate_interior"])):
            raise ValueError("BLOCKED_VIS1_OWNER_OR_STROKE_GATE")
        display=white_composite(rgba)
        medoids=white_composite(regions["source_medoids_preview_rgba"])
        palette_preview=white_composite(proposal["provisional_owner_rgb_preview"])
        colors={
            "01_original_view":display,
            "02_proposed_game128":palette_preview,
            "03_slic_medoids":medoids,
            "04_original_edges_overlay":overlay(display,source["source_edge"],COLORS["source_edges"]),
            "05_protected_unknown":protected_unknown_preview(display,source),
            "06_p2_geometric_core":overlay(display,regions["geometric_potential_core"],COLORS["hypothetical_core"]),
            "07_region_warning_overlay":overlay(display,regions["source_region_warning"],COLORS["slic_warning"],0.62),
        }
        candidate_status="SKIPPED_ALPHA_NONOPAQUE"
        candidate=None
        if bool(np.all(rgba[:,:,3]==255)):
            awe2=source_multiscale_lab_proposal(rgba,source,regions)
            candidate=coherence_trial(rgba,source,regions)
            added=candidate["newly_unexcluded_core"]
            if (np.any(added & source["protected"])
                    or np.any(regions["geometric_potential_core"] & ~candidate["trial_core"])):
                raise ValueError("BLOCKED_VIS1_AWEAK3_SOURCE_CONSERVATION")
            colors.update({
                "08_aweak2_lab_protected_additions":overlay(display,awe2["added"],COLORS["aweak2_added"],0.84),
                "09_aweak3_core_trial":overlay(display,candidate["trial_core"],COLORS["hypothetical_core"]),
                "10_aweak3_new_potential_core":overlay(display,added,COLORS["aweak3_new"],0.88),
            })
            candidate_status="RESEARCH_ONLY_OPAQUE_NO_SAFE_PROMOTION"

        human_A=False
        proxy=None
        if name in SELECTED:
            if candidate is None:
                raise ValueError("BLOCKED_VIS1_FOUR_A_DEV_MUST_BE_OPAQUE")
            key=hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
            label_png=(root/REL_A/(key+"_a.png")).read_bytes()
            label_json=json.loads((root/REL_A/(key+"_a.json")).read_text("utf8"))
            _,a=validated_review(decoded,label_png,label_json)
            human_A=True
            colors.update({
                "11_human_A_hints_overlay":human_A_preview(display,a),
                "12_aweak3_A_conflict_overlay":AWEAK3_conflict_preview(
                    display,a,candidate["newly_unexcluded_core"]
                )
            })
            proxy=compare_weak_mark_tradeoff(a,regions,candidate)
            detailed.append(image_id)
        if not np.array_equal(rgba,original_copy):
            raise ValueError("BLOCKED_VIS1_ORIGINAL_RGBA_MUTATED")
        png_hashes={}
        for key,arr in colors.items():
            png_hashes[key+".png"]=full_rgb_png(folder/(key+".png"),arr,wh)
        sheet=contact_sheet(colors,name+" / "+entry["role"])
        sheet.save(folder/"00_contact_sheet.png",format="PNG")
        png_hashes["00_contact_sheet.png"]=sha256_file(folder/"00_contact_sheet.png")
        r={
            "id":image_id,"original_filename":name,"role":entry["role"],
            "source_original_git_blob_sha1":decoded["git_blob_sha1"],
            "source_original_raw_sha256":decoded["sha256"],
            "original_copy_sha256":sha256_file(original_file),
            "source_shape_hw":[int(hw[0]),int(hw[1])],
            "source_map_version":source["version"],
            "SLIC_version":regions["version"],
            "game128_proposal_version":proposal["version"],
            "source_owner_status":"MISSING",
            "stroke_admission":FORBIDDEN,
            "geometric_core_is_native_safe":False,
            "human_A":human_A,"AWEAK3_status":candidate_status,
            "baseline_P2_core_pixels":int(np.count_nonzero(regions["geometric_potential_core"])),
            "AWEAK3_trial_core_pixels":int(np.count_nonzero(candidate["trial_core"])) if candidate is not None else None,
            "AWEAK3_new_core_pixels":int(np.count_nonzero(candidate["newly_unexcluded_core"])) if candidate is not None else None,
            "human_A_weak_proxy_evaluation":proxy,
            "derived_png_sha256":png_hashes
        }
        results.append(r)
        print("VIS1_REAL_SOURCE",entry["role"],name,wh,
              "PNG",len(png_hashes),"A",human_A,"AWEAK3",candidate_status,flush=True)
    if (len(results)!=23 or len(detailed)!=4
            or len({x["id"] for x in results})!=23
            or any(x["role"]=="LOCKED_HELDOUT" for x in results)
            or {x["original_filename"] for x in results if x["human_A"]}!=set(SELECTED)):
        raise ValueError("BLOCKED_VIS1_SOURCE_SELECTION_OR_LABEL_LEAKAGE")
    ordered=sorted(results,key=lambda x:(not x["human_A"],x["role"]!="DEV",x["original_filename"]))
    (out/"00_review_atlas.html").write_text(html_index(ordered),encoding="utf8")
    guide=(
        "AutoDraw VIS1 — самый свежий визуальный снимок исследовательских карт S4-R1\n"
        "==============================================================\n\n"
        "Откройте 00_review_atlas.html двойным щелчком в Chrome/Firefox.\n"
        "Первые 4 — ваши исходники с человеческими приблизительными отметками A;\n"
        "затем остальные DEV и KNOWN_CONTROL. В каждой папке 00_contact_sheet.png\n"
        "показывает 12 панелей, а отдельные PNG сохранены в полном разрешении.\n"
        "raw_original.* — точная копия исходных файлов без изменения байтов.\n\n"
        "КРАСНЫЙ: protected = карта источниковой защиты (не полная семантика).\n"
        "ЗОЛОТОЙ: UNKNOWN = нет доказанной безопасности; НЕ можно красить.\n"
        "БИРЮЗОВЫЙ: P2/AWEAK3 hypothetical core = только геометрическая идея, НЕ SAFE.\n"
        "ФИОЛЕТОВЫЙ: source SLIC region warnings.\n"
        "ОРАНЖЕВЫЙ: дополнительная защита AWEAK2 (вариант уже НЕ принят).\n"
        "ЯРКО-ЗЕЛЁНЫЙ: новые потенциальные области AWEAK3 (вариант НЕ принят).\n"
        "AWEAK3+Human A: КРАСНЫЙ = пересечение нового core и приблизительных\n"
        "  важных отметок, ЗЕЛЁНЫЙ = пересечение нового core и визуального интерьера.\n"
        "Human A: пурпур=важное, голубой=визуальная граница, зелёный=интерьер.\n"
        "Неоцвеченный пиксель A — не отрицательное доказательство.\n\n"
        "Варианты AWEAK2/AWEAK3 не изменяли active AutoDraw и не доказали безопасность.\n"
        "Прогноз palette128 — ближайший Lab цвет из двигателя, не настоящий owner.\n"
        "Карты сформированы исходными Python-функциями на GitHub CI commit,\n"
        "НЕ ImageGen и НЕ итоговая отрисовка Egret.\n"
        "У источников с прозрачностью неподдерживаемые AWEAK2/AWEAK3 пропущены;\n"
        "нельзя делать вид, что альфа была непрозрачной.\n\n"
        "Вопросы для просмотра: сохранился ли силуэт? не пропали ли глаза/лицо?\n"
        "нет ли искусственных мелких пятен? не слились ли разные визуальные цвета?\n"
        "добавляет ли AWEAK3 площадь, заходя на контуры/важные детали?\n"
        "Не нужна оценка каждого пикселя и никакой новой разметки.\n\n"
        "8 LOCKED_HELDOUT только audit hash/identity; H8 preview здесь нет.\n"
        "S0 BLIND120, second50 не открывались. S4 BLOCKED, S5/S6 НЕ начинались.\n"
        "CHALK и игровая точность по этим PNG НЕ измеряются.\n"
    )
    (out/"README_RU.txt").write_text(guide,encoding="utf8")
    result={
        "version":VERSION,
        "frozen_VIS1_E0_git_blob":E0_BLOB,
        "ci_code_sha":os.environ.get("GITHUB_SHA","UNKNOWN_LOCAL"),
        "source_corpus":"frozen_31",
        "source_preflight_identity":"PASS_AUDIT_31",
        "source_preflight_leakage":identities["perceptual_screen"],
        "source_png_derived_images":len(results),
        "DEV_originals":sum(r["role"]=="DEV" for r in results),
        "KNOWN_CONTROL_originals":sum(r["role"]=="KNOWN_CONTROL" for r in results),
        "LOCKED_HELDOUT_derived":0,
        "A_reviewed_DEV_detailed":len(detailed),
        "A_weak_hints_only":True,
        "originals_byte_identical":True,
        "output_generation":"PIL_NumPy_on_existing_AutoDraw_source_maps",
        "generated_image_model_used":False,
        "current_production_modified":False,
        "AWEAK2_AWEAK3_adopted":False,
        "source_owner_ground_truth":"MISSING",
        "strict_S4":"BLOCKED",
        "stroke_admission":FORBIDDEN,
        "native_E3_game_E4_independent_E5":"NOT_RUN",
        "exact_game_CHALK":None,
        "images":ordered,
    }
    (out/"manifest.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+"\n",
        encoding="utf8"
    )
    # Verify actual saved previews on disk; reject any impossible full-res file.
    for rec in ordered:
        path=out/rec["id"]
        for png,digest in rec["derived_png_sha256"].items():
            if sha256_file(path/png)!=digest:
                raise ValueError("BLOCKED_VIS1_DERIVED_PNG_SHA_MISMATCH")
            with Image.open(path/png) as im:
                if png!="00_contact_sheet.png":
                    if im.size!=(rec["source_shape_hw"][1],rec["source_shape_hw"][0]):
                        raise ValueError("BLOCKED_VIS1_DERIVED_FULL_RES_SIZE")
        raw=path/("raw_original"+Path(rec["original_filename"]).suffix)
        if sha256_file(raw)!=rec["source_original_raw_sha256"]:
            raise ValueError("BLOCKED_VIS1_RAW_ORIGINAL_SHA_MISMATCH")
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    result=build(args.root,args.out)
    print("VIS1_BUILD_PASS",json.dumps({
        k:result[k] for k in ("source_png_derived_images","DEV_originals",
                             "KNOWN_CONTROL_originals","LOCKED_HELDOUT_derived",
                             "A_reviewed_DEV_detailed","strict_S4")
    },ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
