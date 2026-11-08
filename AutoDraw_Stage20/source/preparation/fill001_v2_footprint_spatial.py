from __future__ import annotations

"""Read-only spatial diagnostic for a frozen FILL001_SMOOTH_AB_V2 pair.

This is screen-RGB evidence, NOT an Egret native brush footprint replica.
The source mask, RGB threshold (8), accepted PNG hashes and run geometry are
never fitted or altered. Output always goes to a new directory.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from fill001_screen_mask_v2 import project_screen_mask_v2
from fill001_screen_mask_v2_binding import bind_from_monitor_run

SERIES = "fill001-20261108-204825"
SESSION = "c820c0bb-7955-4c7e-a14c-7e4f6f44cd4d"
PROTOCOL = "FILL001_V2_FOOTPRINT_SPATIAL_V1"
RUN_FILES = {
    "on": "game-monitor-run-20261108T175317308094Z-0f3f9299.json",  # replaced below by task identity search
    "off": "game-monitor-run-20261108T175317308094Z-0f3f9299.json",
}
PNG_THRESHOLD = 8


def _read_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return obj


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify_leakage(mask: np.ndarray, changed: np.ndarray) -> dict:
    """Partition leaking pixels without overlapping categories or mask fitting."""
    if mask.dtype != np.bool_ or changed.dtype != np.bool_ or mask.shape != changed.shape:
        raise ValueError("Expected equal-size boolean screen masks.")
    y_true, x_true = np.nonzero(mask)
    if not len(y_true):
        raise ValueError("Empty target mask.")
    top, bottom = int(y_true.min()), int(y_true.max())
    row_left = np.full(mask.shape[0], -1, dtype=np.int32)
    row_right = np.full(mask.shape[0], -1, dtype=np.int32)
    for y in range(top, bottom + 1):
        xs = np.flatnonzero(mask[y])
        if len(xs):
            row_left[y], row_right[y] = xs[0], xs[-1]
    leaking = changed & ~mask
    ys, xs = np.nonzero(leaking)
    regions = {"above": 0, "below": 0, "left": 0, "right": 0, "other": 0}
    distances = {key: [] for key in regions}
    for y, x in zip(ys.tolist(), xs.tolist()):
        if y < top:
            key, depth = "above", top - y
        elif y > bottom:
            key, depth = "below", y - bottom
        elif row_left[y] >= 0 and x < row_left[y]:
            key, depth = "left", row_left[y] - x
        elif row_right[y] >= 0 and x > row_right[y]:
            key, depth = "right", x - row_right[y]
        else:
            key, depth = "other", 0
        regions[key] += 1
        distances[key].append(depth)
    return {
        "leakage_pixels": int(np.count_nonzero(leaking)),
        "categories": regions,
        "max_depth_screen_px": {k: max(v, default=0) for k, v in distances.items()},
        "mask_screen_bbox_xyxy": [int(x_true.min()), top, int(x_true.max()), bottom],
    }


def _png(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.format != "PNG":
            raise ValueError("Expected PNG.")
        return np.asarray(image.convert("RGB"), dtype=np.int16)


def _overlay(mask: np.ndarray, changed: np.ndarray) -> Image.Image:
    # Diagnostic legend: green=covered, orange=uncovered, magenta=leak, dark=background.
    rgb = np.full((*mask.shape, 3), (23, 29, 40), dtype=np.uint8)
    rgb[mask & changed] = (35, 180, 94)
    rgb[mask & ~changed] = (246, 174, 44)
    rgb[~mask & changed] = (236, 61, 162)
    return Image.fromarray(rgb, "RGB")


def analyze_pair(root: Path, output: Path) -> dict:
    captures = root / "fill001" / "captures"
    monitor = root / "game_monitor_bridge" / SESSION
    manifest = _read_json(root / "fill001" / f"{SERIES}.json")
    if (manifest.get("experiment_protocol") != "FILL001_SMOOTH_AB_V2"
            or manifest.get("screen_mask_version") != "FILL001_SCREEN_MASK_V2"):
        raise ValueError("Wrong frozen V2 manifest.")
    if output.exists():
        raise FileExistsError(f"Refusing overwrite: {output}")
    results = {}
    # Run discovery uses the immutable E4 run_id from each specific capture.
    for mode in ("on", "off"):
        task = f"{SERIES}-rectangle-r10-s5-o0-v2-smooth-{mode}"
        evidence = captures / f"{task}-FILL001_SMOOTH_AB_V2.json"
        result_path = captures / f"{task}-FILL001_SMOOTH_AB_V2-result.json"
        result = _read_json(result_path)
        audit = _read_json(evidence)
        if (result["task_id"] != task or audit["task_id"] != task
                or result["run_id"] != audit["run_id"]
                or audit["status"] != "PASS_E4_RAW_CAPTURE"
                or result["raw_e4_status"] != "PASS_E4_RAW_CAPTURE"
                or result["screen_mask_version"] != "FILL001_SCREEN_MASK_V2"):
            raise ValueError(f"{mode}: run/task mismatch")
        matches = [
            p for p in monitor.glob("game-monitor-run-*.json")
            if p.name.endswith("-" + result["run_id"][:8] + ".json")
        ]
        if len(matches) != 1:
            raise ValueError(f"{mode}: raw Monitor run absent or ambiguous: {matches}")
        binding = bind_from_monitor_run(matches[0], evidence)
        roi = binding["screen_roi"]
        mask = project_screen_mask_v2(
            "rectangle", run_id=result["run_id"], screen_roi=roi,
            geometry=binding["geometry"],
        )
        before_path = captures / (task + "-before.png")
        after_path = captures / (task + "-after.png")
        if (_sha(before_path) != result["before_png_sha256"]
                or _sha(after_path) != result["after_png_sha256"]):
            raise ValueError(f"{mode}: frozen PNG SHA mismatch")
        before, after = _png(before_path), _png(after_path)
        if before.shape != after.shape or before.shape[:2] != mask.shape:
            raise ValueError(f"{mode}: image/geometry mismatch")
        changed = np.any(np.abs(after - before) > PNG_THRESHOLD, axis=2)
        spatial = classify_leakage(mask, changed)
        coverage = int(np.count_nonzero(mask & changed))
        target = int(np.count_nonzero(mask))
        expected = result["v2_audit"]
        if (target != expected["target_pixels"] or coverage != expected["covered_pixels"]
                or spatial["leakage_pixels"] != expected["leakage_pixels"]
                or int(np.count_nonzero(changed)) != expected["changed_pixels"]):
            raise ValueError(f"{mode}: V2 audit metrics mismatch; refusing diagnostic")
        results[mode] = {
            "run_id": result["run_id"], "raw_run_sha256": result["raw_run_sha256"],
            "evidence_sha256": _sha(evidence), "before_sha256": _sha(before_path),
            "after_sha256": _sha(after_path), "roi": roi,
            "mask_pixels": target, "covered_pixels": coverage,
            "uncovered_pixels": target - coverage, "coverage_fraction": coverage / target,
            "spatial": spatial, "overlay_file": f"{mode}-spatial-overlay.png",
        }
    if results["on"]["roi"] != results["off"]["roi"]:
        raise ValueError("Noncomparable ON/OFF screen ROI")
    output.mkdir(parents=True, exist_ok=False)
    for mode in ("on", "off"):
        task = f"{SERIES}-rectangle-r10-s5-o0-v2-smooth-{mode}"
        result = _read_json(captures / f"{task}-FILL001_SMOOTH_AB_V2-result.json")
        match = [p for p in monitor.glob("game-monitor-run-*.json")
                 if p.name.endswith("-" + result["run_id"][:8] + ".json")][0]
        binding = bind_from_monitor_run(
            match, captures / f"{task}-FILL001_SMOOTH_AB_V2.json"
        )
        mask = project_screen_mask_v2("rectangle", run_id=result["run_id"],
                                      screen_roi=binding["screen_roi"],
                                      geometry=binding["geometry"])
        before = _png(captures / f"{task}-before.png")
        after = _png(captures / f"{task}-after.png")
        changed = np.any(np.abs(after - before) > PNG_THRESHOLD, axis=2)
        _overlay(mask, changed).save(output / f"{mode}-spatial-overlay.png")
    report = {
        "protocol": PROTOCOL, "source_series": SERIES,
        "source_commit": "07f4f3ea14eb14598fa7ce08c3985e56acb0f73b",
        "threshold": PNG_THRESHOLD, "status": "DIAGNOSTIC_ONLY",
        "conditions": results,
        "limitations": [
            "This is live screenshot RGB only, not native Egret or isolated stroke width.",
            "Overlapping 27 strokes cannot identify one brush diameter uniquely.",
            "Region classification uses the nearest same-row target envelope; rounded corners are in left/right.",
            "No target dilation, erosion, translation or post-hoc threshold tuning.",
            "Original V2 and V1 acceptance outcomes remain unchanged.",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n",
                                         encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    report = analyze_pair(args.results_root, args.output_dir)
    for mode, item in report["conditions"].items():
        print(f"{mode}: coverage={item['coverage_fraction']:.6%}, "
              f"leak={item['spatial']['leakage_pixels']}, "
              f"regions={item['spatial']['categories']}, "
              f"depth={item['spatial']['max_depth_screen_px']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
