"""FILL001-SERIES-001 offline geometry preparation for pre-registered variants.

Reuses existing FILL-001 frozen masks, fixed-radius planner and frozen RS
spacing table. Never invokes Stage6, changes production defaults, claims exact
CHALK, or grants automatic game execution.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from chalk_fill_experiment import FILL001_EXPECTED_MASK_SHA256
from chalk_fill_fixed_radius_planner import build_fixed_radius_fill_plan
from chalk_fill_matrix import FILL001_RS_SCANLINE_CONFIGS
from fill001_series_runner import validate_manifest, SeriesBlocked

SCHEMA = "FILL001_SERIES_OFFLINE_GEOMETRY_V1"
SUPPORTED = {"dense_scanlines", "spaced_scanlines"}


def prepare_offline_variants(manifest: dict[str, Any]) -> dict[str, Any]:
    """Rebuild a plan once per unique shape/method/brush triplet."""
    validate_manifest(manifest)
    variants = {}
    tasks = []
    for task in manifest["tasks"]:
        shape = task["shape_id"]
        method = task["fill_method"]
        radius = task["brush_radius"]
        if method not in SUPPORTED:
            raise SeriesBlocked(f"Unsupported fill method {method!r}")
        key = f"{shape}:{method}:r{radius}"
        if key not in variants:
            if method == "dense_scanlines":
                step, offset = 1, 0
            else:
                step, offset = FILL001_RS_SCANLINE_CONFIGS[(shape, radius)]
            plan = build_fixed_radius_fill_plan(
                shape, radius, scanline_row_step=step, scanline_offset=offset
            )
            summary = plan["summary"]
            if plan["target_mask_sha256"] != FILL001_EXPECTED_MASK_SHA256[shape]:
                raise SeriesBlocked(f"Frozen target mask differs for {shape}")
            # This is a model, not an executable authorization.
            variants[key] = {
                "shape_id": shape, "fill_method": method,
                "radius": radius, "planner_version": plan["planner_version"],
                "scanline_row_step": step, "scanline_offset": offset,
                "plan_signature": plan["plan_signature"],
                "target_mask_sha256": plan["target_mask_sha256"],
                "stroke_count": summary["stroke_count"],
                "path_length_logical_pixels": summary["path_length_logical_pixels"],
                "estimated_sampling_points": summary["estimated_sampling_points"],
                "estimated_sampling_points_are_exact_chalk": False,
                "offline_coverage_fraction": summary["coverage_fraction"],
                "offline_leakage_pixels": summary["leakage_pixels"],
                "offline_quality_gate": "PASS" if summary["quality_gate_passed"] else "FAIL",
                "engine_chalk_status": "NOT_EVALUATED",
                "screen_png_quality_status": "NOT_EVALUATED",
                "execution_allowed": False,
            }
        tasks.append({
            "task_id": task["task_id"], "order": task["order"],
            "variant_key": key, "plan_signature": variants[key]["plan_signature"],
            "offline_quality_gate": variants[key]["offline_quality_gate"],
            "execution_allowed": False,
        })
    return {
        "schema": SCHEMA, "series_id": manifest["series_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "execution_allowed": False, "automatic_clear_allowed": False,
        "note": "OpenCV geometry proxy only; needs run-bound game CHALK and PNG evidence",
        "task_count": len(tasks), "unique_variants": len(variants),
        "variants": variants, "tasks": tasks,
    }


def write_offline_geometry(manifest: dict, destination: Path) -> Path:
    document = prepare_offline_variants(manifest)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline FILL-001 series geometry replay; no game input")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    output = write_offline_geometry(manifest, args.output)
    print(f"Offline geometry: {output} (not game executable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
