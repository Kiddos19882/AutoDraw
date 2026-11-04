from __future__ import annotations

"""Create a new isolated FILL-001-RS 45-task manifest for the existing single-task UI."""

import argparse
from datetime import datetime
from pathlib import Path
import re

from chalk_fill_matrix import build_fill001_rs_matrix, write_fill001_matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--series-id",
        default=f"fill001-rs-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if re.fullmatch(r"fill001-rs-[A-Za-z0-9][A-Za-z0-9_.-]{0,48}", args.series_id) is None:
        parser.error("--series-id должен начинаться с fill001-rs- и содержать только безопасные символы.")

    default_root = Path(__file__).resolve().parents[2] / "data" / "results" / "brush_behavior_tests" / "fill001_rs"
    output = args.output.resolve() if args.output else default_root / f"{args.series_id}.json"
    if output.exists():
        parser.error(f"Manifest уже существует; перезапись запрещена: {output}")

    matrix = build_fill001_rs_matrix(args.series_id)
    write_fill001_matrix(matrix, output)
    preflight = next(
        task for task in matrix["tasks"]
        if task["shape_id"] == "rectangle"
        and task["requested_radius"] == 10
        and task["repeat_index"] == 1
    )
    print(f"Manifest: {output}")
    print(f"Series: {matrix['series_id']}")
    print(f"Tasks: {len(matrix['tasks'])}; execution_allowed={matrix['execution_allowed']}")
    print(
        "Suggested single-task preflight: "
        f"{preflight['task_id']} | strokes={preflight['expected_strokes']} | "
        f"scanline_row_step={preflight['scanline_row_step']} | "
        f"offset={preflight['scanline_offset']} | "
        f"coverage={preflight['planned_coverage_fraction']:.6%} | "
        f"leakage={preflight['planned_leakage_pixels']}"
    )
    print("The manifest is not batch-executable; select exactly one task in the FILL-001 UI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
