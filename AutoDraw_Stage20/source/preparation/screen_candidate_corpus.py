from __future__ import annotations
"""Offline corpus similarity triage; no automatic classification or CHALK approval."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from autodraw_project import open_project
from chalk_int006_validation import _normalize_manifest_strokes


def safe_child(root, rel):
    p = Path(rel)
    b = Path(root).resolve()
    target = (b / p).resolve()
    if p.is_absolute() or not target.is_relative_to(b):
        raise ValueError("Unsafe corpus relative path")
    return target


def file_sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(path):
    with Image.open(path) as src:
        image = ImageOps.exif_transpose(src)
        size = list(image.size)
        transparency = "A" in image.getbands() and image.getchannel("A").getextrema()[0] < 255
        rgb = Image.new("RGBA", image.size, "white")
        rgb.alpha_composite(image.convert("RGBA"))
        rgb = rgb.convert("RGB")
        rgb.thumbnail((256, 256), Image.Resampling.LANCZOS)
        grey = rgb.convert("L")
        g32 = np.array(ImageOps.pad(grey, (32, 32), color="white"), dtype=np.float32)
        dct = cv2.dct(g32)[:8, :8].ravel()
        median = float(np.median(dct[1:]))
        pbits = [False] + [v > median for v in dct[1:]]
        g9 = np.array(ImageOps.pad(grey, (9, 8), color="white"), dtype=np.int16)
        dbits = (g9[:, :-1] > g9[:, 1:]).ravel()
        def as_hex(bits):
            value = 0
            for bit in bits:
                value = (value << 1) | int(bit)
            return f"{value:016x}"
        arr = np.array(ImageOps.pad(rgb, (64, 64), color="white"), dtype=np.int16)
        chroma = float(np.mean(arr.max(axis=2) - arr.min(axis=2) >= 32))
        grey64 = np.array(ImageOps.pad(grey, (64, 64), color="white"), dtype=np.int16)
        edge = float(np.abs(np.diff(grey64, axis=0)).mean() + np.abs(np.diff(grey64, axis=1)).mean())
        packed = (arr[:, :, 0] // 32) * 64 + (arr[:, :, 1] // 32) * 8 + (arr[:, :, 2] // 32)
        _, counts = np.unique(packed, return_counts=True)
        dominance = float(counts.max() / counts.sum())
        return {
            "original_size": size, "transparency_present": bool(transparency),
            "chroma_fraction": round(chroma, 4), "edge_score": round(edge, 4),
            "dominant_coarse_color_fraction": round(dominance, 4),
            "phash64": as_hex(pbits), "dhash64": as_hex(dbits),
        }


def geometry_sha256(project_path, expected_n):
    strokes = open_project(project_path).json_file("drawing_plan")["strokes"]
    normalized = _normalize_manifest_strokes(strokes)
    if len(normalized) != expected_n:
        raise ValueError("DrawingPlan N inconsistent with manifest")
    h = hashlib.sha256()
    for stroke in normalized:
        h.update(json.dumps(stroke["points"], separators=(",", ":")).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def group_duplicates(rows, key):
    by_value = defaultdict(list)
    for row in rows:
        by_value[row[key]].append(row["dataset"] + "/" + row["source"])
    return [sorted(g) for g in by_value.values() if len(g) > 1]


def screen(datasets):
    if not datasets or len({x[0] for x in datasets}) != len(datasets):
        raise ValueError("Dataset labels must be unique")
    rows, configs = [], []
    for label, manifest_file, source_dir in datasets:
        mpath = Path(manifest_file).resolve()
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
        if manifest.get("protocol_eligibility") != "candidate_only_not_assessed":
            raise ValueError("Only candidate-only manifests are supported")
        records = manifest["records"]
        if not isinstance(records, list):
            raise ValueError("Manifest records must be an array")
        configs.append({"dataset": label, "configuration": manifest["configuration"]})
        for rec in records:
            image = safe_child(source_dir, rec["source"])
            source_hash = file_sha256(image)
            if source_hash != rec["source_sha256"]:
                raise ValueError("Source SHA-256 mismatch: " + rec["source"])
            plan = safe_child(mpath.parent.parent, rec["project_path"])
            rows.append({
                "dataset": label, "source": rec["source"],
                "source_sha256": source_hash,
                "drawing_plan_sha256": rec["drawing_plan_sha256"],
                "geometry_sha256_without_names": geometry_sha256(plan, rec["drawing_plan_stroke_count"]),
                "monochrome_N": rec["drawing_plan_stroke_count"],
                "color_N": rec.get("color_plan_stroke_count"),
                "family_label": rec.get("family_label", "unclassified"),
                **fingerprint(image),
            })
    rows.sort(key=lambda v: (v["dataset"], v["source"]))
    near_pairs = []
    all_pairs = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            p = (int(a["phash64"], 16) ^ int(b["phash64"], 16)).bit_count()
            d = (int(a["dhash64"], 16) ^ int(b["dhash64"], 16)).bit_count()
            pair = {
                "left": a["dataset"] + "/" + a["source"],
                "right": b["dataset"] + "/" + b["source"],
                "phash_distance": p, "dhash_distance": d,
                "status": "manual_review_required",
            }
            all_pairs.append(pair)
            if p <= 10 and d <= 10:
                near_pairs.append(pair)
    rank = lambda pair: (pair["phash_distance"] + pair["dhash_distance"], pair["left"], pair["right"])
    near_pairs.sort(key=rank)
    all_pairs.sort(key=rank)
    visual_counts = {
        "with_transparency": sum(r["transparency_present"] for r in rows),
        "low_chroma_at_most_0_10": sum(r["chroma_fraction"] <= 0.10 for r in rows),
        "dominant_coarse_color_at_least_0_75": sum(r["dominant_coarse_color_fraction"] >= 0.75 for r in rows),
        "edge_score_at_least_50": sum(r["edge_score"] >= 50 for r in rows),
    }
    return {
        "schema_version": 1, "type": "candidate_image_similarity_and_geometry_screen",
        "source_count": len(rows),
        "dataset_counts": {label: sum(r["dataset"] == label for r in rows) for label, _, _ in datasets},
        "configurations": configs,
        "configurations_match": all(x["configuration"] == configs[0]["configuration"] for x in configs),
        "source_exact_duplicate_groups": group_duplicates(rows, "source_sha256"),
        "geometry_exact_duplicate_groups": group_duplicates(rows, "geometry_sha256_without_names"),
        "perceptual_review_pairs": near_pairs,
        "perceptual_review_pair_count": len(near_pairs),
        "closest_20_pairs_review_only": all_pairs[:20],
        "visual_characteristics_counts": visual_counts,
        "records": rows,
        "perceptual_thresholds_review_only": {"phash_hamming_max": 10, "dhash_hamming_max": 10},
        "manual_family_classification": "not_performed",
        "independent_plan_count": None,
        "predictor_domain_eligibility": "not_assessed",
        "production_eligibility": "not_validated",
        "CHALK_measurement": "not_performed",
        "validation_95_percent": "not_performed",
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", nargs=3, action="append", required=True, metavar=("LABEL", "MANIFEST", "IMAGE_DIR"))
    p.add_argument("--output", required=True)
    a = p.parse_args(argv)
    result = screen(a.dataset)
    output = Path(a.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "source_count", "dataset_counts", "configurations_match",
        "source_exact_duplicate_groups", "geometry_exact_duplicate_groups",
        "perceptual_review_pair_count", "visual_characteristics_counts",
        "closest_20_pairs_review_only", "independent_plan_count",
        "predictor_domain_eligibility"
    )}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
