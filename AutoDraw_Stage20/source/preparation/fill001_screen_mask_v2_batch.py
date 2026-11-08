from __future__ import annotations

"""Re-analyze the two already-committed FILL001_SMOOTH_AB_V1 captures.

Only JSON metrics are emitted. Full-screen screenshots are never uploaded.
The original V1 quality result is preserved and cannot be overridden by V2.
"""

import argparse
import hashlib
import json
from pathlib import Path

from chalk_fill_matrix import FillMatrixError
from fill001_screen_mask_v2 import audit_screen_mask_v2
from fill001_screen_mask_v2_binding import bind_from_monitor_run

SERIES = "fill001-20261108-185918"
SESSION = "15e3de92-f847-420f-b0d5-faea8dd38b4c"
CASES = {
    "on": ("358f1e65", "20261108T160326076317Z"),
    "off": ("b76d43c3", "20261108T160516151130Z"),
}


def replay_pair(results_root: Path, output_dir: Path) -> dict:
    captures = results_root / "fill001" / "captures"
    monitor = results_root / "game_monitor_bridge" / SESSION
    rows = {}
    for mode, (short_run, timestamp) in CASES.items():
        name = f"{SERIES}-rectangle-r10-s5-o0-smooth-{mode}"
        evidence_path = captures / f"{name}-FILL001_SMOOTH_AB_V1.json"
        result_path = captures / f"{name}-FILL001_SMOOTH_AB_V1-result.json"
        run_path = monitor / f"game-monitor-run-{timestamp}-{short_run}.json"
        if not all(path.is_file() for path in (evidence_path, result_path, run_path)):
            raise FillMatrixError(f"V2 {mode}: missing committed run or report.")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        binding = bind_from_monitor_run(run_path, evidence_path)
        if (result.get("run_id") != binding["geometry"]["run_id"]
                or result.get("renderer_geometry_sha256")
                != binding["provenance"]["native_geometry_sha256"]):
            raise FillMatrixError("V2 binding does not match frozen result geometry.")
        before = captures / f"{name}-before.png"
        after = captures / f"{name}-after.png"
        for png, field in ((before, "before_png_sha256"), (after, "after_png_sha256")):
            if hashlib.sha256(png.read_bytes()).hexdigest() != result.get(field):
                raise FillMatrixError(f"V2 {mode}: committed PNG SHA mismatch.")
        row = audit_screen_mask_v2(
            "rectangle", before, after, run_id=result["run_id"],
            screen_roi=binding["screen_roi"], geometry=binding["geometry"],
        )
        if (row["v1_original"]["leakage_pixels"] !=
                result["png_audit"]["leakage_pixels"] or
                row["v1_original"]["coverage_fraction"] !=
                result["png_audit"]["coverage_fraction"]):
            raise FillMatrixError("V2 replay disagrees with immutable V1 PNG audit.")
        rows[mode] = {
            "binding": binding["provenance"],
            "diagnostic": row,
        }
    if output_dir.exists():
        raise FillMatrixError("V2 refuses to overwrite prior diagnostic evidence.")
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "protocol": "FILL001_SCREEN_MASK_V2",
        "series": SERIES,
        "status": "DIAGNOSTIC_ONLY",
        "acceptance_override": False,
        "conditions": rows,
        "limitations": [
            "DOM client-to-screen offsets are independently checked per run.",
            "No native Egret footprint-versus-live pixel-equivalence claimed.",
            "V1 frozen thresholds and historical FAIL outcomes are unchanged.",
        ],
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FILL-001 saved Screen Mask V2 pair")
    parser.add_argument("--results-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    report = replay_pair(args.results_root, args.output_dir)
    for mode, row in report["conditions"].items():
        v1 = row["diagnostic"]["v1_original"]
        v2 = row["diagnostic"]
        print(
            f"{mode}: V1 leakage={v1['leakage_pixels']} "
            f"coverage={v1['coverage_fraction']:.8f}; "
            f"V2 leakage={v2['leakage_pixels']} "
            f"coverage={v2['coverage_fraction']:.8f} "
            f"({v2['v2_diagnostic_gate']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
