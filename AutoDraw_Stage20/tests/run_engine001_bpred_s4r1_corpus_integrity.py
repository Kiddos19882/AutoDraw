#!/usr/bin/env python3
"""ENGINE-001/BPRED-S4-R1 frozen E0 corpus integrity & leakage preflight.

Reads 31 frozen corpus files, NEVER generates heldout maps. DEV maps are
produced only after exact identity and conservative cross-split screening.
A perceptual hash is a warning/blocker, NOT proof of dataset independence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from engine001_bpred_s4r1_generic_source_maps import (
    decode_original, generic_source_maps, provisional_game128_owner_maps,
    original_source_region_uncertainty, original_alpha_interface_reference,
)
from run_engine001_b1r_p3b_engine128_adaptive32 import read_engine_palette

REL_CORPUS = Path("AutoDraw_Stage20/data/generated_autodraw_plan/images_31_first")
REL_OLD = Path("AutoDraw_Stage20/testImages")
REL_E0 = Path(
    "AutoDraw_Stage20/docs/"
    "ENGINE001_BPRED001_S4R1_AUTOMATIC_MULTIMAGE_PROTECTION_PREREG_2026-11-21.md"
)
VERSION = "ENGINE001_BPRED_S4R1_CORPUS_INTEGRITY_E2_V1"
MANIFEST_RX = re.compile(
    r"^\| \x60([^\x60]+)\x60 \| \x60([a-f0-9]{40})\x60"
    r" \| ([0-9]+) \| (DEV|KNOWN_CONTROL|LOCKED_HELDOUT) \|$",
    re.M,
)
NEAR_DHASH_MAX = 4
NEAR_PHASH_MAX = 6


def manifest(e0_path: Path) -> list[dict]:
    rows = [
        {"file": m.group(1), "git_blob": m.group(2),
         "bytes": int(m.group(3)), "role": m.group(4)}
        for m in MANIFEST_RX.finditer(e0_path.read_text(encoding="utf-8"))
    ]
    if (len(rows) != 31 or len({r["file"] for r in rows}) != 31 or
            len({r["git_blob"] for r in rows}) != 31 or
            sum(r["role"] == "KNOWN_CONTROL" for r in rows) != 8 or
            sum(r["role"] == "DEV" for r in rows) != 15 or
            sum(r["role"] == "LOCKED_HELDOUT" for r in rows) != 8 or
            any(Path(r["file"]).name != r["file"] for r in rows)):
        raise ValueError("BLOCKED_S4R1_FIRST_FROZEN_MANIFEST_OR_SPLIT")
    return rows


def perceptual_fingerprints(rgba: np.ndarray) -> tuple[int, int]:
    """Predeclared dHash64 and low-frequency pHash63 for candidate duplication."""
    # Transparent color is always composited against neutral 255, not black.
    rgb = rgba[:, :, :3].astype(np.float32)
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255
    white = np.clip(np.rint(rgb * alpha + 255.0 * (1.0 - alpha)), 0, 255).astype(np.uint8)
    gray = cv2.cvtColor(white, cv2.COLOR_RGB2GRAY)
    nine = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    dhash = 0
    for b in (nine[:, 1:] > nine[:, :-1]).ravel():
        dhash = (dhash << 1) | int(b)
    square = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    frequency = cv2.dct(square.astype(np.float32))[:8, :8].ravel()[1:]
    median = float(np.median(frequency))
    phash = 0
    for b in frequency > median:
        phash = (phash << 1) | int(b)
    return dhash, phash


def audit(root: Path) -> dict:
    files = manifest(root / REL_E0)
    old_dir = root / REL_OLD
    if not (root / REL_CORPUS).is_dir() or not old_dir.is_dir():
        raise ValueError("BLOCKED_S4R1_MISSING_SOURCE_DIRECTORIES")
    old_blobs: dict[str, list[str]] = {}
    for p in sorted(old_dir.iterdir()):
        if not p.is_file():
            continue
        raw = p.read_bytes()
        sha = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        old_blobs.setdefault(sha, []).append(p.name)
    records, fingerprints = [], {}
    for e in files:
        path = root / REL_CORPUS / e["file"]
        if not path.is_file():
            raise ValueError("BLOCKED_S4R1_MISSING_FROZEN_CORPUS_FILE:" + e["file"])
        raw = path.read_bytes()
        data = decode_original(raw)
        if (len(raw) != e["bytes"] or data["git_blob_sha1"] != e["git_blob"]):
            raise ValueError("BLOCKED_S4R1_ORIGINAL_GIT_BLOB_OR_SIZE_CHANGED:" + e["file"])
        old = old_blobs.get(e["git_blob"], [])
        if (e["role"] == "KNOWN_CONTROL") != bool(old):
            raise ValueError("BLOCKED_S4R1_HISTORICAL_CONTROL_SPLIT_LEAK:" + e["file"])
        fingerprints[e["file"]] = perceptual_fingerprints(data["rgba"])
        records.append({
            "file": e["file"], "role": e["role"],
            "sha256": data["sha256"], "git_blob_sha1": data["git_blob_sha1"],
            "bytes": e["bytes"], "width": data["width"], "height": data["height"],
            "mode": data["original_mode"],
            "exif_orientation": data["exif_orientation"],
            "historical_exact_blob_in_testImages": old,
            "has_any_nonopaque_alpha": bool(np.any(data["rgba"][:, :, 3] != 255)),
        })
    # This is a source-integrity diagnostic; do not inspect or tune on heldout output.
    roles = {r["file"]: r["role"] for r in records}
    cross, inside_heldout = [], []
    for a, b in combinations(sorted(roles), 2):
        da, pa = fingerprints[a]
        db, pb = fingerprints[b]
        distance_d = (da ^ db).bit_count()
        distance_p = (pa ^ pb).bit_count()
        if distance_d > NEAR_DHASH_MAX or distance_p > NEAR_PHASH_MAX:
            continue
        pair = {"a": a, "b": b, "dhash_hamming": distance_d,
                "phash_hamming": distance_p}
        if (roles[a] == "LOCKED_HELDOUT") != (roles[b] == "LOCKED_HELDOUT"):
            cross.append(pair)
        elif roles[a] == roles[b] == "LOCKED_HELDOUT":
            inside_heldout.append(pair)
    status = ("BLOCKED_SUSPECTED_CROSS_SPLIT_OR_HOLDOUT_DUPLICATE"
              if cross or inside_heldout else "PASS_SOURCE_PRE_SCREEN_ONLY")
    return {
        "version": VERSION, "dataset_path": str(REL_CORPUS),
        "e0": str(REL_E0), "corpus_files": len(records),
        "known_controls": 8, "dev": 15, "locked_heldout": 8,
        "source_identity": "PASS_SHA_AND_DECODING",
        "perceptual_screen": status,
        "potential_cross_split_duplicates": cross,
        "potential_heldout_internal_duplicates": inside_heldout,
        "semantic_independence": "UNKNOWN_NOT_ASSESSED",
        "crop_resize_reencode_leakage": "UNKNOWN_SCREEN_CANNOT_EXCLUDE",
        "native_brush_safety": "NOT_RUN",
        "records": records,
    }


def run_dev_maps(root: Path, audit_report: dict, output: Path) -> list[dict]:
    if audit_report["perceptual_screen"] != "PASS_SOURCE_PRE_SCREEN_ONLY":
        raise ValueError("BLOCKED_S4R1_CROSS_SPLIT_LEAKAGE_PREVENTS_DEV_OUTPUT")
    output.mkdir(parents=True, exist_ok=True)
    # Reuse P3B's genuine SHA-pinned 128-swatch engine parser; DO NOT call
    # its fixed-Egret 32-color weighting/assignment code.
    engine128, engine_provenance = read_engine_palette(
        root / "AutoDraw_Stage20/gameEngine/main.min_653f95bc.js"
    )
    summaries = []
    for r in audit_report["records"]:
        if r["role"] == "LOCKED_HELDOUT":
            continue
        name = r["file"]
        raw = (root / REL_CORPUS / name).read_bytes()
        src = decode_original(raw)
        maps = generic_source_maps(src["rgba"])
        # Nearest game swatch is only a diagnostic PROPOSAL, not source owner.
        proposal = provisional_game128_owner_maps(raw, engine128, engine_provenance)
        assert proposal["source_sha256"] == r["sha256"]
        assert proposal["source_git_blob_sha1"] == r["git_blob_sha1"]
        assert proposal["source_owner_status"] == maps["owner_status"] == "MISSING"
        assert proposal["proposal_status"].startswith("PROVISIONAL")
        assert maps["counts"]["candidate_interior"] == 0
        assert proposal["stroke_admission"].startswith("FORBIDDEN")
        regions = original_source_region_uncertainty(src["rgba"], maps)
        assert regions["source_rgba_sha256"] == hashlib.sha256(
            src["rgba"].tobytes()).hexdigest()
        assert regions["source_owner_status"] == "MISSING"
        assert regions["stroke_admission"].startswith("FORBIDDEN")
        alpha_reference = original_alpha_interface_reference(src["rgba"], maps, regions)
        assert alpha_reference["original_source_rgba_sha256"] == regions[
            "source_rgba_sha256"]
        assert alpha_reference["stroke_admission"].startswith("FORBIDDEN")
        assert np.all(regions["geometric_potential_core"] <= maps["unknown"])
        assert maps["stroke_admission"].startswith("FORBIDDEN")
        prefix = hashlib.sha256(name.encode("utf8")).hexdigest()[:12]
        png_sha = {}
        for key in ("source_edge", "protected", "unknown", "geometric_detail_evidence"):
            mask = (maps[key].astype(np.uint8) * 255)
            out_png = output / (prefix + "_" + key + ".png")
            Image.fromarray(mask, mode="L").save(out_png)
            png_sha[key] = hashlib.sha256(out_png.read_bytes()).hexdigest()
        preview_png = output / (prefix + "_provisional_game128_rgb.png")
        Image.fromarray(proposal["provisional_owner_rgb_preview"], mode="RGBA"
                        ).save(preview_png)
        png_sha["provisional_game128_rgb"] = hashlib.sha256(
            preview_png.read_bytes()).hexdigest()
        edges_png = output / (prefix + "_provisional_owner_edges.png")
        Image.fromarray(
            proposal["provisional_owner_edge"].astype(np.uint8) * 255, mode="L"
        ).save(edges_png)
        png_sha["provisional_owner_edges"] = hashlib.sha256(
            edges_png.read_bytes()).hexdigest()
        medoid_png = output / (prefix + "_source_region_medoids.png")
        Image.fromarray(regions["source_medoids_preview_rgba"], mode="RGBA"
                        ).save(medoid_png)
        png_sha["source_region_medoids"] = hashlib.sha256(
            medoid_png.read_bytes()).hexdigest()
        warning_png = output / (prefix + "_source_region_warning.png")
        Image.fromarray(regions["source_region_warning"].astype(np.uint8) * 255,
                        mode="L").save(warning_png)
        png_sha["source_region_warning"] = hashlib.sha256(
            warning_png.read_bytes()).hexdigest()
        assert len(png_sha) == 8
        assert (proposal["counts"]["opaque_assigned_provisionally"] +
                proposal["counts"]["unassigned_nonopaque"] ==
                src["height"] * src["width"])
        summaries.append({
            "file": name, "role": r["role"], "sha256": r["sha256"],
            "source_shape": [src["height"], src["width"]],
            "version": maps["version"],
            "owner_status": maps["owner_status"],
            "semantic_detail_status": maps["semantic_detail_status"],
            "stroke_admission": maps["stroke_admission"],
            "counts": maps["counts"],
            "derived_png_sha256": png_sha,
            "independent_source_alpha_reference": alpha_reference,
            "original_source_regions": {
                "version": regions["version"],
                "segmentation_method": regions["segmentation_method"],
                "source_rgba_sha256": regions["source_rgba_sha256"],
                "counts": regions["counts"],
                "representatives": regions["representatives"],
                "source_owner_status": regions["source_owner_status"],
                "region_owner_accuracy": regions["region_owner_accuracy"],
                "semantic_detail_status": regions["semantic_detail_status"],
                "stroke_admission": regions["stroke_admission"],
            },
            "owner128_proposal": {
                "version": proposal["version"],
                "status": proposal["proposal_status"],
                "source_owner_status": proposal["source_owner_status"],
                "game_engine_git_blob_sha1": proposal["game_engine_git_blob_sha1"],
                "game128_palette_sha256": proposal["game128_palette_sha256"],
                "counts": proposal["counts"],
                "lab_nearest_distance_mean": proposal["lab_nearest_distance_mean"],
                "lab_nearest_distance_p95": proposal["lab_nearest_distance_p95"],
                "owner_accuracy": proposal["owner_accuracy"],
                "stroke_admission": proposal["stroke_admission"],
            },
        })
    assert len(summaries) == 23
    assert len(list(output.glob("*.png"))) == 23 * 8
    applicable = [
        s for s in summaries if s["independent_source_alpha_reference"][
            "opaque_interface_pixels"] > 0
    ]
    if (len(applicable) != 6 or
            sum(s["role"] == "DEV" for s in applicable) != 1 or
            sum(s["role"] == "KNOWN_CONTROL" for s in applicable) != 5):
        raise ValueError("BLOCKED_S4R1_ALPHA_REFERENCE_APPLICABILITY_CHANGED")
    if any(s["independent_source_alpha_reference"]["alpha_reference_status"]
           != "PASS_ALPHA_SOURCE_REFERENCE_ONLY" for s in applicable):
        failures = [
            (s["file"], s["independent_source_alpha_reference"][
                "opaque_interface_unprotected_pixels"])
            for s in applicable if s["independent_source_alpha_reference"][
                "opaque_interface_unprotected_pixels"] > 0
        ]
        raise ValueError("FAIL_ALPHA_INTERFACE_SOURCE_PROTECTION:" + repr(failures))
    print("S4R1_DEV_ALPHA_SOURCE_REFERENCE", len(applicable),
          "DEV", 1, "KNOWN_CONTROL", 5,
          "OPAQUE_INTERFACE", sum(s["independent_source_alpha_reference"][
              "opaque_interface_pixels"] for s in applicable),
          "UNPROTECTED", sum(s["independent_source_alpha_reference"][
              "opaque_interface_unprotected_pixels"] for s in applicable))
    if not any(s["original_source_regions"]["counts"]["geometric_potential_core"] > 0
               for s in summaries):
        raise ValueError("FAIL_NOT_USEFUL_S4R1_ALL_DEV_SOURCE_REGION_CORES_EMPTY")
    (output / "dev_summary.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf8")
    return summaries


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--dev-maps-dir", type=Path)
    args = p.parse_args()
    result = audit(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps({k: v for k, v in result.items() if k != "records"},
                     ensure_ascii=False, sort_keys=True))
    if result["perceptual_screen"] != "PASS_SOURCE_PRE_SCREEN_ONLY":
        return 2
    if args.dev_maps_dir is not None:
        summaries = run_dev_maps(args.root, result, args.dev_maps_dir)
        print("S4R1_DEV_ONLY_SOURCE_MAPS", len(summaries),
              "OWNER128_ONLY_PROVISIONAL", "SOURCE_REGIONS_MODEL_ONLY",
              "STROKE_ADMISSION_ALWAYS_FORBIDDEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
