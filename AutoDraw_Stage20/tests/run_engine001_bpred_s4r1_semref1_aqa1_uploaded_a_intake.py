#!/usr/bin/env python3
"""SEMREF1-AQA1 frozen first-reviewer intake only; never native or semantic GT.

No A->B copying, no overlays/model masks, no visual feedback used for selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from engine001_bpred_s4r1_generic_source_maps import decode_original, git_blob_sha1
from engine001_bpred_s4r1_semref1_human_review_validation import (
    CODES, E0_BLOB, E0_PATH, FORBIDDEN, SELECTED, run as paired_run,
    validated_review,
)
from run_engine001_bpred_s4r1_corpus_integrity import manifest, REL_CORPUS, REL_E0

AQA1_E0 = "AutoDraw_Stage20/docs/ENGINE001_BPRED001_S4R1_SEMREF1_AQA1_UPLOADED_A_TECHNICAL_PREFLIGHT_PREREG_2026-11-21.md"
AQA1_E0_BLOB = "22b167a12ce45b04b96ca68edc9c3ed8f2e7e8b6"
INPUT_SHA = "75d0fb7e14d352a719691666cd6a55777dc4a713"
REL_A = Path("AutoDraw_Stage20/data/result_SEMREF1")
EXPECTED_BLOBS = {
    "0875c4b0561d_a.json": "10c42dea625d3efbf00a3f6081beb743664bff2f",
    "0875c4b0561d_a.png": "d5d8bf6a751362eb68bcfd3df3cd801950a17296",
    "473579bc287e_a.json": "99954a93c34a8cb539907acace9be6dd94cd132c",
    "473579bc287e_a.png": "93d42c3cdda41acf3351adc8fd4035c3a075e85a",
    "5f7e89e6ef4d_a.json": "2b9a4f1464bef58c71a4b236f1bdece51ac7605f",
    "5f7e89e6ef4d_a.png": "06d2be54c6560d6f9acf7408e8d2090bdae657e5",
    "ed23a65642d7_a.json": "10640cfe32b754d4ae477b1816ac4b2cef6bf0e7",
    "ed23a65642d7_a.png": "9ba3dbd1fdf383bd1ffb499e55a7d12c",
}
CATEGORIES = ("unreviewed", "critical", "color_region_boundary",
              "verified_interior", "ambiguous")


def count_a_labels(labels: np.ndarray) -> dict:
    """Technical class-count only, not semantic accuracy."""
    if (not isinstance(labels, np.ndarray) or labels.ndim != 3
            or labels.shape[2] != 3 or labels.dtype != np.uint8):
        raise ValueError("BLOCKED_AQA1_INVALID_LABEL_MATRIX")
    per = [int(np.count_nonzero(np.all(labels == c, axis=2))) for c in CODES]
    total = int(labels.shape[0] * labels.shape[1])
    if sum(per) != total:
        raise ValueError("BLOCKED_AQA1_INVALID_LABEL_CODES")
    out = dict(zip(CATEGORIES, per))
    out["source_pixels"] = total
    out["A_K"] = per[1] + per[2]
    out["A_I"] = per[3]
    out["A_review_fraction"] = float((per[1] + per[2] + per[3]) / total)
    out["single_reviewer_support"] = ("PRESENT_UNVERIFIED" if out["A_K"] and out["A_I"]
                                      else "BLOCKED_INSUFFICIENT_SINGLE_REVIEW_SUPPORT")
    return out


def audit(root: Path) -> dict:
    for doc, expected in ((AQA1_E0, AQA1_E0_BLOB), (E0_PATH, E0_BLOB)):
        raw = (root / doc).read_bytes()
        if git_blob_sha1(raw) != expected:
            raise ValueError("BLOCKED_AQA1_FROZEN_E0_DRIFT " + doc)
    folder = root / REL_A
    if not folder.is_dir():
        raise ValueError("BLOCKED_AQA1_ANNOTATIONS_NOT_A_DIRECTORY")
    observed = {p.name for p in folder.iterdir() if p.is_file()}
    if observed != set(EXPECTED_BLOBS):
        raise ValueError("BLOCKED_AQA1_FROZEN_EIGHT_FILES_DRIFT")
    for n, exp in EXPECTED_BLOBS.items():
        if git_blob_sha1((folder / n).read_bytes()) != exp:
            raise ValueError("BLOCKED_AQA1_UPLOADED_GIT_BLOB_DRIFT " + n)
    entries = {e["file"]: e for e in manifest(root / REL_E0)}
    if not all(entries.get(name, {}).get("role") == "DEV" for name in SELECTED):
        raise ValueError("BLOCKED_AQA1_FROZEN_SOURCE_DEV_ROLE_DRIFT")

    records, authors = [], set()
    for name in SELECTED:
        ent = entries[name]
        key = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        png_path = folder / (key + "_a.png")
        json_path = folder / (key + "_a.json")
        if not png_path.is_file() or not json_path.is_file():
            raise ValueError("BLOCKED_AQA1_FROZEN_LABEL_BASENAME_MISMATCH " + name)
        raw = (root / REL_CORPUS / name).read_bytes()
        if len(raw) != ent["bytes"] or git_blob_sha1(raw) != ent["git_blob"]:
            raise ValueError("BLOCKED_AQA1_ORIGINAL_SOURCE_GIT_BLOB_DRIFT " + name)
        original = decode_original(raw)
        if np.any(original["rgba"][:, :, 3] != 255):
            raise ValueError("BLOCKED_AQA1_FROZEN_OPAQUE_SOURCE_REQUIRED " + name)
        sidecar = json.loads(json_path.read_text(encoding="utf-8"))
        reviewer, labels = validated_review(original, png_path.read_bytes(), sidecar)
        authors.add(reviewer)
        counts = count_a_labels(labels)
        records.append({
            "file": name, "source_role": "DEV",
            "original_git_blob_sha1": original["git_blob_sha1"],
            "source_raw_sha256": original["sha256"],
            "source_hw": [original["height"], original["width"]],
            "original_rgba_sha256": sidecar["original_rgba_sha256"],
            "label_a_git_blob_sha1": EXPECTED_BLOBS[png_path.name],
            "label_a_png_sha256": sidecar["labels_png_sha256"],
            "label_a_source_only_blind_review_attested": sidecar["source_only_blind_review"],
            "single_reviewer_counts": counts,
            "single_reviewer_independence": "NOT_APPLICABLE_SINGLE_REVIEW",
            "science_eligible": False,
        })
    if len(authors) != 1:
        raise ValueError("BLOCKED_AQA1_EXPECT_EXACTLY_ONE_UPLOADED_A_AUTHOR")
    # Reuse the existing unchanged scorer's strict gate. No attempts to fake B.
    full_gate = paired_run(root, folder)
    if (full_gate["scientific_status"] != "BLOCKED_NO_INDEPENDENT_HUMAN_LABELS"
            or full_gate["records"] != [] or full_gate["heldout_outputs"] != 0
            or full_gate["stroke_admission"] != FORBIDDEN):
        raise ValueError("BLOCKED_AQA1_SEMREF1_SCIENCE_GATE_BYPASSED")

    return {
        "version": "ENGINE001_BPRED_S4R1_SEMREF1_AQA1_INTAKE_V1",
        "input_commit": INPUT_SHA,
        "frozen_AQA1_E0_git_blob": AQA1_E0_BLOB,
        "original_SEMREF1_E0_git_blob": E0_BLOB,
        "technical_status": "PASS_A_ONLY_SOURCE_AND_LABEL_INTEGRITY",
        "reviewer_count": len(authors),
        "reviewer_identification": "ONE_PSEUDONYM_ATTESTED_NOT_INDEPENDENT_GT",
        "pairs_a_checked": len(records),
        "pairs_b_checked": 0,
        "per_original": records,
        "science_status": "BLOCKED_MISSING_SECOND_INDEPENDENT_REVIEWER",
        "source_game_owner": "MISSING_NOT_GT",
        "semantic_false_safe_or_recall": None,
        "strict_s4": "BLOCKED",
        "stroke_admission": FORBIDDEN,
        "heldout_outputs": 0,
        "native_E3": "NOT_RUN",
        "game_E4_E5": "NOT_RUN",
        "exact_CHALK": None,
        "originals_modified": False,
        "label_a_png_modified": False,
        "model_images_generated": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    result = audit(a.root)
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if a.output:
        a.output.write_text(payload, encoding="utf-8")
    print(payload)
