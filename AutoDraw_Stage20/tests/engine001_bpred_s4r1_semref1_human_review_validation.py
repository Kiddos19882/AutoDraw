#!/usr/bin/env python3
"""S4R1 SEMREF1: validation-only two-reviewer source pixel labels.

No automatic segmentation, no game owner GT, no stroke admission. Reviewer
sidecars are attestations, NOT independently authenticated human provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from engine001_bpred_s4r1_generic_source_maps import (
    decode_original, generic_source_maps, original_source_region_uncertainty,
)
from run_engine001_bpred_s4r1_corpus_integrity import manifest, REL_CORPUS, REL_E0

VERSION = "ENGINE001_BPRED_S4R1_SEMREF1_SOURCE_REVIEW_V1"
E0_BLOB = "734ef71adeabfedeaaab0f3edccb62254fbca24a"
E0_PATH = "AutoDraw_Stage20/docs/ENGINE001_BPRED001_S4R1_SEMREF1_HUMAN_DEV_REFERENCE_PREREG_2026-11-21.md"
SELECTED = (
    "6f6fff4105b941bf85b1fbd8519a.jpg",
    "ima56655ges.jpg",
    "EZAL3k9ddfs.jpg",
    "images (1).png",
)
CODES = np.array(((0, 0, 0), (255, 0, 255), (0, 255, 255),
                  (0, 255, 0), (255, 255, 0)), dtype=np.uint8)
FORBIDDEN = "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_label_bytes(data: bytes, hw: tuple[int, int]) -> np.ndarray:
    """Reject palette, resampling, alpha, invalid colors and altered geometry."""
    with Image.open(io.BytesIO(data)) as img:
        if img.format != "PNG" or img.mode != "RGB" or img.size != (hw[1], hw[0]):
            raise ValueError("BLOCKED_SEMREF1_LABEL_PNG_MODE_OR_SOURCE_SIZE")
        rgb = np.asarray(img, dtype=np.uint8).copy()
    if not np.isin(rgb.reshape(-1, 3).view("V3"), CODES.view("V3")).all():
        raise ValueError("BLOCKED_SEMREF1_INVALID_LABEL_COLOR")
    return rgb


def validated_review(decoded: dict, png: bytes, sidecar: dict) -> tuple[str, np.ndarray]:
    """Check source binding and independent-review claims; not proof of authorship."""
    expected = {
        "source_raw_sha256": decoded["sha256"],
        "source_git_blob_sha1": decoded["git_blob_sha1"],
        "original_rgba_sha256": sha(decoded["rgba"].tobytes()),
        "original_hw": [decoded["height"], decoded["width"]],
        "labels_png_sha256": sha(png),
        "source_only_blind_review": True,
    }
    if not isinstance(sidecar, dict) or any(sidecar.get(k) != v for k, v in expected.items()):
        raise ValueError("BLOCKED_SEMREF1_SOURCE_OR_REVIEW_PROVENANCE")
    rid = sidecar.get("reviewer_id")
    tool = sidecar.get("annotation_tool_and_version")
    stamp = sidecar.get("review_timestamp")
    if (not isinstance(rid, str) or not rid.strip() or len(rid) > 80
            or not isinstance(tool, str) or not tool.strip() or len(tool) > 200
            or not isinstance(stamp, str)):
        raise ValueError("BLOCKED_SEMREF1_REVIEWER_METADATA")
    try:
        ts = datetime.fromisoformat(stamp)
    except ValueError as e:
        raise ValueError("BLOCKED_SEMREF1_REVIEW_TIMESTAMP") from e
    if ts.tzinfo is None:
        raise ValueError("BLOCKED_SEMREF1_REVIEW_TIMESTAMP_TIMEZONE")
    return rid, source_label_bytes(png, (decoded["height"], decoded["width"]))


def score_pair(decoded: dict, source: dict, regions: dict,
               reviews: list[tuple[bytes, dict]]) -> dict:
    if not isinstance(reviews, list) or len(reviews) != 2:
        raise ValueError("BLOCKED_SEMREF1_TWO_INDEPENDENT_REVIEWS_REQUIRED")
    first_id, a = validated_review(decoded, *reviews[0])
    second_id, b = validated_review(decoded, *reviews[1])
    if first_id == second_id:
        raise ValueError("BLOCKED_SEMREF1_REVIEWER_IDENTITIES_NOT_DISTINCT")
    rgba = decoded["rgba"]
    h, w = rgba.shape[:2]
    if (source.get("owner_status") != "MISSING"
            or regions.get("source_owner_status") != "MISSING"
            or source.get("stroke_admission") != FORBIDDEN
            or regions.get("stroke_admission") != FORBIDDEN
            or not np.array_equal(source.get("source_rgb"), rgba[:, :, :3])
            or not np.array_equal(source.get("source_alpha"), rgba[:, :, 3])):
        raise ValueError("BLOCKED_SEMREF1_SOURCE_OWNER_ORIGINAL_PROVENANCE")
    masks = [source.get(k) for k in ("protected", "unknown", "candidate_interior")]
    core = regions.get("geometric_potential_core")
    if (any(not isinstance(v, np.ndarray) or v.dtype != bool
            or v.shape != (h, w) for v in masks + [core])
            or not np.all(masks[0] | masks[1])
            or np.any(masks[0] & masks[1])
            or np.any(masks[2])
            or np.any(core & ~masks[1])
            or regions.get("source_rgba_sha256") != sha(rgba.tobytes())):
        raise ValueError("BLOCKED_SEMREF1_SOURCE_UNKNOWN_NOT_ADMISSIBLE")
    agreement = np.all(a == b, axis=2)
    critical = agreement & (np.all(a == CODES[1], axis=2) |
                            np.all(a == CODES[2], axis=2))
    interior = agreement & np.all(a == CODES[3], axis=2)
    k, i = int(critical.sum()), int(interior.sum())
    counts = {
        "agreed_critical_or_region_boundary": k,
        "agreed_verified_interior": i,
        "reviewer_disagreement_or_unreviewed_or_ambiguous": int((~(critical | interior)).sum()),
        "protected_on_reviewed_critical": int((critical & masks[0]).sum()),
        "unknown_on_reviewed_critical": int((critical & masks[1]).sum()),
        "hypothetical_core_on_reviewed_critical": int((critical & core).sum()),
        "protected_on_reviewed_interior": int((interior & masks[0]).sum()),
        "hypothetical_core_on_reviewed_interior": int((interior & core).sum()),
    }
    return {
        "version": VERSION,
        "scientific_status": ("BLOCKED_INSUFFICIENT_VERIFIED_SUPPORT" if not k or not i
                              else "SOURCE_ONLY_HUMAN_ATTESTED_RISK_PROXY_NOT_NATIVE"),
        "reviewer_independence": "ATTESTED_NOT_EXTERNALLY_AUTHENTICATED",
        "source_game_owner": "MISSING_NOT_GT",
        "source_raw_sha256": decoded["sha256"],
        "original_rgba_sha256": sha(rgba.tobytes()),
        "counts": counts,
        "protected_recall_on_reviewed_critical": (counts["protected_on_reviewed_critical"]/k if k else None),
        "core_fraction_on_reviewed_interior": (counts["hypothetical_core_on_reviewed_interior"]/i if i else None),
        "stroke_admission": FORBIDDEN,
        "strict_s4": "BLOCKED",
        "native_E3": "NOT_RUN",
        "game_E4": "NOT_RUN",
        "exact_CHALK": None,
    }


def run(root: Path, labels_root: Path | None) -> dict:
    e0 = (root / E0_PATH).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(e0)).encode() + b"\0" + e0).hexdigest()
    if actual != E0_BLOB:
        raise ValueError("BLOCKED_SEMREF1_FROZEN_E0_CHANGED")
    result = {
        "version": VERSION,
        "source_subset": list(SELECTED),
        "strict_s4": "BLOCKED",
        "heldout_outputs": 0,
        "stroke_admission": FORBIDDEN,
        "scientific_status": "BLOCKED_NO_INDEPENDENT_HUMAN_LABELS",
        "records": [],
        "game_E4": "NOT_RUN",
        "exact_CHALK": None,
    }
    if labels_root is None:
        return result
    entries = {v["file"]: v for v in manifest(root / REL_E0) if v["role"] == "DEV"}
    if not all(k in entries for k in SELECTED):
        raise ValueError("BLOCKED_SEMREF1_FROZEN_DEV_SUBSET_MISMATCH")
    # Preflight all inputs before scoring anything: no partial-cohort promotion.
    inputs = []
    for name in SELECTED:
        key = hashlib.sha256(name.encode()).hexdigest()[:12]
        pairs = []
        for suffix in ("a", "b"):
            png_path = labels_root / (key + "_" + suffix + ".png")
            json_path = labels_root / (key + "_" + suffix + ".json")
            if not png_path.is_file() or not json_path.is_file():
                return result  # scientifically blocked, no false zero-error PASS
            pairs.append((png_path.read_bytes(), json.loads(json_path.read_text(encoding="utf8"))))
        inputs.append((name, pairs))
    for name, reviews in inputs:
        entry = entries[name]
        raw = (root / REL_CORPUS / name).read_bytes()
        decoded = decode_original(raw)
        if (len(raw) != entry["bytes"]
                or decoded["git_blob_sha1"] != entry["git_blob"]
                or np.any(decoded["rgba"][:, :, 3] != 255)):
            raise ValueError("BLOCKED_SEMREF1_ORIGINAL_DEV_SOURCE_DRIFT")
        sm = generic_source_maps(decoded["rgba"])
        rg = original_source_region_uncertainty(decoded["rgba"], sm)
        score = score_pair(decoded, sm, rg, reviews)
        result["records"].append({"file": name, "role": "DEV", **score})
    if len(result["records"]) == 4 and all(
            v["scientific_status"] == "SOURCE_ONLY_HUMAN_ATTESTED_RISK_PROXY_NOT_NATIVE"
            for v in result["records"]):
        result["scientific_status"] = "PARTIAL_SOURCE_ONLY_HUMAN_ATTESTATIONS_NEED_INDEPENDENT_VALIDATION"
    else:
        result["scientific_status"] = "BLOCKED_INSUFFICIENT_VERIFIED_SUPPORT"
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--labels-root", type=Path, default=None)
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.labels_root), indent=2, ensure_ascii=False, allow_nan=False))
