"""FILL001-SERIES-001 immutable single-figure logical DrawingPlan handoff.

Uses the project's established fixed-radius planner, 3 frozen masks, and
original FILL001_RS spacing table. Data only: never grants live execution or
changes Stage6 and legacy FILL-001 batch policies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from chalk_fill_experiment import FILL001_EXPECTED_MASK_SHA256
from chalk_fill_fixed_radius_planner import build_fixed_radius_fill_plan
from chalk_fill_matrix import FILL001_RS_SCANLINE_CONFIGS
from fill001_series_runner import validate_manifest, SeriesBlocked

PROTOCOL = "FILL001_SERIES_LOGICAL_DRAWING_PLAN_V1"
POLICY = "FILL001_CHALK_FIRST_PERIMETER_V2"


def _json_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def resolve_series_scanline_spacing(shape: str, radius: int, method: str) -> tuple[int, int]:
    """Resolve frozen series spacing for offline preview and signed handoff."""
    if method == "dense_scanlines":
        return 1, 0
    if method == "spaced_scanlines":
        try:
            return FILL001_RS_SCANLINE_CONFIGS[(shape, radius)]
        except KeyError as exc:
            raise SeriesBlocked("Unknown frozen series spacing cell") from exc
    raise SeriesBlocked("Unknown series fill method")


def build_series_source_plan(manifest: dict, task_id: str) -> dict:
    """Return deterministic non-executable geometry for exactly one task."""
    validate_manifest(manifest)
    candidates = [t for t in manifest["tasks"] if t["task_id"] == task_id]
    if len(candidates) != 1:
        raise SeriesBlocked("Series task ID missing or ambiguous")
    task = candidates[0]
    shape, radius, method = task["shape_id"], task["brush_radius"], task["fill_method"]
    step, offset = resolve_series_scanline_spacing(shape, radius, method)
    plan = build_fixed_radius_fill_plan(
        shape, radius, scanline_row_step=step, scanline_offset=offset,
    )
    if plan["target_mask_sha256"] != FILL001_EXPECTED_MASK_SHA256[shape]:
        raise SeriesBlocked("Frozen FILL-001 shape digest changed")
    strokes = []
    for i, item in enumerate(plan["strokes"]):
        if item.get("brush_value") != radius or len(item.get("points", [])) != 2:
            raise SeriesBlocked("Frozen planner stroke parameters changed")
        strokes.append({
            "name": f"series_{task_id}_{i+1:04}",
            "closed": False,
            "points": [
                {"x": float(p["x"]), "y": float(p["y"])}
                for p in item["points"]
            ],
            "metadata": {
                "role": "fill001_series_fixed_radius_scanline",
                "task_id": task_id,
                "brush_value": str(radius),
                "source_stroke_index": str(i),
                "plan_signature": plan["plan_signature"],
                "fill_method": method,
            },
        })
    signature = _json_sha(strokes)
    return {
        "schema_version": 1,
        "name": f"FILL001-SERIES {task_id}",
        "coordinate_system": "logical_board_pixels",
        "canvas": {"width": 460, "height": 240},
        "width": 460, "height": 240,
        "strokes": strokes,
        "generation": {
            "protocol": PROTOCOL,
            "quality_policy_id": POLICY,
            "series_id": manifest["series_id"],
            "series_manifest_sha256": manifest["manifest_sha256"],
            "task_id": task_id,
            "shape_id": shape, "fill_method": method,
            "brush_radius": radius,
            "scanline_row_step": step, "scanline_offset": offset,
            "planner_version": plan["planner_version"],
            "plan_signature": plan["plan_signature"],
            "frozen_target_mask_sha256": plan["target_mask_sha256"],
            "source_strokes_sha256": signature,
            "expected_strokes": len(strokes),
            "actual_chalk": None,
            "game_quality_status": "NOT_EVALUATED",
            "automatic_execution_allowed": False,
            "requires_fresh_single_run_preflight": True,
        },
        "summary": {
            "stroke_count": len(strokes),
            "path_length_logical_pixels": plan["summary"]["path_length_logical_pixels"],
            "modeled_coverage_fraction": plan["summary"]["coverage_fraction"],
            "modeled_leakage_pixels": plan["summary"]["leakage_pixels"],
            "modeled_quality_gate": "PASS" if plan["summary"]["quality_gate_passed"] else "FAIL",
            "estimated_sampling_points": plan["summary"]["estimated_sampling_points"],
            "estimated_sampling_points_are_exact_chalk": False,
        },
    }


def validate_series_source_plan(manifest: dict, document: Any) -> dict:
    if not isinstance(document, dict) or not isinstance(document.get("generation"), dict):
        raise SeriesBlocked("Source plan is not a FILL001 series DrawingPlan")
    generation = document["generation"]
    expected = build_series_source_plan(manifest, generation.get("task_id"))
    if document != expected:
        raise SeriesBlocked("Series DrawingPlan differs from frozen planner, method or task")
    return generation


def export_series_source_plan(manifest: dict, task_id: str, output: Path) -> Path:
    source = build_series_source_plan(manifest, task_id)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(source, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a validated logical series DrawingPlan (NO GAME INPUT)")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    export_series_source_plan(manifest, args.task_id, args.output)
    print(f"Exported offline DrawingPlan: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
