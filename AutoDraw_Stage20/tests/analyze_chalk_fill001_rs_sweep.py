from __future__ import annotations

"""Reproduce the FILL-001-RS scanline spacing sweep and emit a JSON evidence report."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys

import cv2
import numpy as np

PREPARATION_DIR = Path(__file__).resolve().parents[1] / "source" / "preparation"
sys.path.insert(0, str(PREPARATION_DIR))

from chalk_fill_experiment import (  # noqa: E402
    FILL001_RADII,
    FILL001_SHAPES,
    FILL001_EXPECTED_MASK_SHA256,
)
from chalk_fill_fixed_radius_planner import build_fixed_radius_fill_plan  # noqa: E402
from chalk_fill_matrix import (  # noqa: E402
    FILL001_RS_SCANLINE_CONFIGS,
    FILL001_RS_SELECTION_POLICY,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cells = []
    candidate_records = []
    candidate_count = 0
    accepted_count = 0
    for shape in FILL001_SHAPES:
        for radius in FILL001_RADII:
            candidates = []
            for step in range(1, radius + 1):
                for offset in range(step):
                    candidate_count += 1
                    plan = build_fixed_radius_fill_plan(
                        shape,
                        radius,
                        scanline_row_step=step,
                        scanline_offset=offset,
                    )
                    summary = plan["summary"]
                    item = {
                        "shape_id": shape,
                        "radius": radius,
                        "scanline_row_step": step,
                        "scanline_offset": offset,
                        "planner_version": plan["planner_version"],
                        "plan_signature": plan["plan_signature"],
                        "stroke_count": summary["stroke_count"],
                        "path_length_logical_pixels": summary["path_length_logical_pixels"],
                        "estimated_sampling_points": summary["estimated_sampling_points"],
                        "coverage_fraction": summary["coverage_fraction"],
                        "uncovered_target_pixels": summary["uncovered_target_pixels"],
                        "leakage_pixels": summary["leakage_pixels"],
                        "quality_gate_passed": summary["quality_gate_passed"],
                    }
                    candidate_records.append(item)
                    if summary["coverage_fraction"] >= 0.99 and summary["leakage_pixels"] == 0:
                        accepted_count += 1
                        candidates.append(item)
            if not candidates:
                raise RuntimeError(f"No candidate passed the frozen gate for {shape}/r{radius}.")
            max_step = max(item["scanline_row_step"] for item in candidates)
            finalists = [item for item in candidates if item["scanline_row_step"] == max_step]
            selected = max(
                finalists,
                key=lambda item: (
                    item["coverage_fraction"],
                    -item["estimated_sampling_points"],
                    -item["path_length_logical_pixels"],
                    -item["stroke_count"],
                ),
            )
            key = (shape, radius)
            frozen_step, frozen_offset = FILL001_RS_SCANLINE_CONFIGS[key]
            if (selected["scanline_row_step"], selected["scanline_offset"]) != (frozen_step, frozen_offset):
                raise RuntimeError(
                    f"Frozen config mismatch for {shape}/r{radius}: "
                    f"computed={(selected['scanline_row_step'], selected['scanline_offset'])}, "
                    f"frozen={(frozen_step, frozen_offset)}"
                )
            cells.append({
                "shape_id": shape,
                "radius": radius,
                "target_mask_sha256": FILL001_EXPECTED_MASK_SHA256[shape],
                "candidate_count": sum(1 for step in range(1, radius + 1) for _ in range(step)),
                "accepted_candidate_count": len(candidates),
                "selection_policy": FILL001_RS_SELECTION_POLICY,
                "selected": selected,
            })

    report = {
        "schema_version": 1,
        "experiment_id": "FILL-001-RS-STATIC-SWEEP-V1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "opencv_version": cv2.__version__,
        "numpy_version": np.__version__,
        "canvas": {"width": 460, "height": 240},
        "shapes": list(FILL001_SHAPES),
        "radii": list(FILL001_RADII),
        "candidate_domain": "scanline_row_step=1..radius; scanline_offset=0..step-1",
        "candidate_count": candidate_count,
        "accepted_candidate_count": accepted_count,
        "acceptance_gate": {"coverage_fraction_min": 0.99, "leakage_pixels_max": 0},
        "selection_policy": FILL001_RS_SELECTION_POLICY,
        "cells": cells,
        "candidates": candidate_records,
        "evidence_limitations": [
            "OpenCV raster simulation only; game renderer has not been validated.",
            "estimated_sampling_points is a proxy, not exact CHALK.",
            "Exact CHALK is pointCount_after - pointCount_before in a valid live run.",
            "No live experiment is performed by this script.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "candidate_count": candidate_count,
        "accepted_candidate_count": accepted_count,
        "cells": len(cells),
        "status": "passed",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
