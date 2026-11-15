#!/usr/bin/env python3
"""ENGINE-001 V16: blind jacket seam reference validation (no inference or paint).

Only score external independently-reviewed positive/negative masks. A generated
candidate, a Canny edge, and a dark-suit proxy are NEVER valid ground truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_line_extraction_v14_report import check_source, ROI, SOURCE_SHA

EXPECTED_OUTPUT_SHA = {
    "anilines": "2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b",
    "fdog": "ab83ae4410f8ec5be90019030a57d3f391f1c62398a61f867cde4abba71d32ec",
}
ROI_SHAPE = (ROI[3] - ROI[1], ROI[2] - ROI[0])
KERNEL = np.ones((3, 3), dtype=np.uint8)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_mask(path: Path) -> np.ndarray:
    if not path.is_file():
        raise ValueError(f"Missing annotation mask: {path.name}")
    with Image.open(path) as im:
        if im.size != (ROI_SHAPE[1], ROI_SHAPE[0]) or im.mode != "L":
            raise ValueError("Annotation mask must be L PNG at 100x189 source pixels")
        mask = np.asarray(im, dtype=np.uint8)
    if not np.all((mask == 0) | (mask == 255)):
        raise ValueError("Annotation must be binary 0/255; no interpolation or colors")
    return mask == 255


def validate_annotation(
    manifest: dict, positive: np.ndarray, negative: np.ndarray
) -> None:
    if not isinstance(manifest, dict):
        raise ValueError("Annotation manifest must be a JSON object")
    if manifest.get("source_sha256") != SOURCE_SHA:
        raise ValueError("Annotation source SHA mismatch")
    if manifest.get("roi") != list(ROI):
        raise ValueError("Annotation source-coordinate ROI mismatch")
    if not manifest.get("annotation_id") or not manifest.get("reviewer_id"):
        raise ValueError("Annotation id and independent reviewer id required")
    if not manifest.get("annotation_version") or not manifest.get("reviewed_at"):
        raise ValueError("Missing annotation provenance/version")
    if manifest.get("blind_to_model_outputs") is not True:
        raise ValueError("Explicit blind source-only reviewer attestation required")
    if positive.shape != ROI_SHAPE or negative.shape != ROI_SHAPE:
        raise ValueError("Invalid annotation dimensions")
    if positive.dtype != np.dtype(bool) or negative.dtype != np.dtype(bool):
        raise ValueError("Annotation must be boolean arrays")
    if not positive.any() or not negative.any():
        raise ValueError("Both positive and negative annotations must be nonempty")
    close = cv2.dilate(positive.astype(np.uint8), KERNEL).astype(bool)
    if np.any(close & negative):
        raise ValueError("Positive +/-1px neighborhood conflicts with definite negatives")


def read_review(annotation_dir: Path) -> tuple[dict, np.ndarray, np.ndarray]:
    man_path = annotation_dir / "annotation.json"
    if not man_path.is_file():
        raise ValueError("Annotation manifest MISSING — status BLOCKED")
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    positive_file = annotation_dir / "seams_positive.png"
    negative_file = annotation_dir / "definite_nonseam.png"
    for name, file in [("positive_sha256", positive_file),
                       ("negative_sha256", negative_file)]:
        if not manifest.get(name) or sha256(file) != manifest[name]:
            raise ValueError(f"Annotation file missing or changed: {name}")
    pos, neg = read_mask(positive_file), read_mask(negative_file)
    validate_annotation(manifest, pos, neg)
    return manifest, pos, neg


def evaluate_mask(candidate: np.ndarray, positive: np.ndarray,
                  negative: np.ndarray) -> dict:
    """No claims of global semantic precision on partially labeled pixels."""
    if (candidate.shape != ROI_SHAPE or positive.shape != ROI_SHAPE or
            negative.shape != ROI_SHAPE or any(arr.dtype != np.dtype(bool)
            for arr in (candidate, positive, negative))):
        raise ValueError("Candidate and references must be ROI-sized boolean masks")
    near_candidate = cv2.dilate(candidate.astype(np.uint8), KERNEL).astype(bool)
    positive_band = cv2.dilate(positive.astype(np.uint8), KERNEL).astype(bool)
    if np.any(positive_band & negative):
        raise ValueError("Positive/negative labels conflict within 1px")
    positive_pixels = int(np.count_nonzero(positive))
    negative_pixels = int(np.count_nonzero(negative))
    if positive_pixels == 0 or negative_pixels == 0:
        raise ValueError("Ground truth must include both labeled classes")
    positive_matched = int(np.count_nonzero(positive & near_candidate))
    negative_candidates = int(np.count_nonzero(negative & candidate))
    adjudicated_supported = int(np.count_nonzero(positive_band & candidate))
    adjudicated_candidate_total = adjudicated_supported + negative_candidates
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(
        positive.astype(np.uint8), connectivity=8
    )
    gaps = 0
    for index in range(1, component_count):
        belong = labels == index
        area = int(stats[index, cv2.CC_STAT_AREA])
        matched = int(np.count_nonzero(belong & near_candidate))
        if matched * 2 < area:
            gaps += 1
    return {
        "candidate_pixels": int(np.count_nonzero(candidate)),
        "annotated_positive_pixels": positive_pixels,
        "annotated_negative_pixels": negative_pixels,
        "positive_matched_within_1px": positive_matched,
        "positive_recall_1px": positive_matched / positive_pixels,
        "negative_candidate_pixels": negative_candidates,
        "nonseam_candidate_density": negative_candidates / negative_pixels,
        "adjudicated_supported_candidate_pixels": adjudicated_supported,
        "adjudicated_candidate_total": adjudicated_candidate_total,
        "supported_candidate_fraction_on_labeled_pixels":
            (adjudicated_supported / adjudicated_candidate_total
             if adjudicated_candidate_total else None),
        "positive_components": component_count - 1,
        "positive_gap_components": gaps,
        "global_semantic_precision": None,
        "recognizability": "NOT_TESTED",
        "native_egret": "NOT_RUN",
        "exact_game_chalk": None,
    }


def read_v14_candidate(path: Path, engine: str) -> np.ndarray:
    if engine not in EXPECTED_OUTPUT_SHA or sha256(path) != EXPECTED_OUTPUT_SHA[engine]:
        raise ValueError(f"V14 {engine} output SHA mismatch; fail closed")
    with Image.open(path) as im:
        if im.size != (200, 320):
            raise ValueError("Expected original 200x320 candidate PNG")
        full = np.asarray(im.convert("L"), dtype=np.uint8)
    x0, y0, x1, y1 = ROI
    return full[y0:y1, x0:x1] < 128


def prepare_source_only(source: Path, output_dir: Path) -> None:
    check_source(source)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Review pack directory not empty — refuse overwriting")
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as im:
        crop = im.convert("RGB").crop(ROI)
        crop.save(output_dir / "reviewer_source_only.png")
    template = {
        "annotation_id": "PENDING_INDEPENDENT_REVIEW",
        "reviewer_id": "PENDING",
        "annotation_version": "PENDING",
        "reviewed_at": "PENDING",
        "blind_to_model_outputs": False,
        "source_sha256": SOURCE_SHA,
        "roi": list(ROI),
        "positive_sha256": None,
        "negative_sha256": None,
        "annotation_status": "BLOCKED_NOT_ANNOTATED",
    }
    # Offline reviewer receives a source-only browser UI; no model prediction
    # and no implicit or fabricated positive/negative annotation is included.
    annotator = Path(__file__).with_name("engine001_seam_reference_v16_annotator.html")
    if not annotator.is_file():
        raise ValueError("Source-only annotation UI missing; refuse incomplete pack")
    shutil.copyfile(annotator, output_dir / "annotate_source_only.html")
    (output_dir / "annotation.template.json").write_text(
        json.dumps(template, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--prepare-review", type=Path)
    p.add_argument("--annotation-dir", type=Path)
    p.add_argument("--anilines", type=Path)
    p.add_argument("--fdog", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.prepare_review is not None:
        if any(v is not None for v in (args.annotation_dir, args.anilines,
                                       args.fdog, args.output)):
            p.error("--prepare-review cannot be combined with evaluation")
        prepare_source_only(args.source, args.prepare_review)
        print("BLOCKED: no independent source-only seam annotation yet")
        return 0
    if any(v is None for v in (args.annotation_dir, args.anilines,
                               args.fdog, args.output)):
        p.error("Evaluation requires annotation-dir, both V14 outputs and output")
    check_source(args.source)
    manifest, positive, negative = read_review(args.annotation_dir)
    results = {
        "experiment_id": "ENGINE001_ANILINES_SEAM_REFERENCE_V16",
        "status": "ANNOTATION_SCORING_ONLY_NOT_ARTWORK_ACCEPTANCE",
        "source_sha256": SOURCE_SHA,
        "annotation": manifest,
        "candidate_threshold": 128,
        "metrics": {},
    }
    for engine, path in [("anilines", args.anilines), ("fdog", args.fdog)]:
        results["metrics"][engine] = evaluate_mask(
            read_v14_candidate(path, engine), positive, negative
        )
    out = args.output
    if out.exists():
        raise ValueError("Refusing to overwrite V16 evidence report")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print("V16 annotation scoring complete; NOT a painting quality PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
