#!/usr/bin/env python3
"""ENGINE-001 E5: independent native Stage A-D vs nine immutable live RGB captures.

The source PNGs have no live alpha channel. Native alpha is diagnostic only.
No runtime/game interaction or production changes are performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path, PureWindowsPath

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "preparation"))
from renderer_acceptance import (  # noqa: E402
    evaluate_per_run_acceptance, validate_paired_capture,
    validate_renderer_comparison, validate_transform_geometry,
)
from renderer_geometry import (  # noqa: E402
    build_same_run_geometry_audit_input,
    detect_board_bounds_from_screenshots,
    derive_live_board_screen_transform,
)
from compare_stage_renderer_reference import compare_stage_variants  # noqa: E402
from run_egret_stage_reference_firefox import discover_engine001_cases  # noqa: E402

PROTOCOL = "ENGINE001_E5_NATIVE_SCREEN_V1"


def load(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return result


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alpha_diagnostics(path: Path) -> dict:
    with Image.open(path) as source:
        alpha = np.asarray(source.convert("RGBA"), dtype=np.uint8)[:, :, 3]
    output = {"source": "native_backing_alpha_only", "size": [alpha.shape[1], alpha.shape[0]]}
    for threshold in (1, 24, 64, 128, 254):
        y, x = np.where(alpha > threshold)
        output[str(threshold)] = {
            "count": len(x),
            "bbox_xywh": ([int(x.min()), int(y.min()),
                           int(x.max()-x.min()+1), int(y.max()-y.min()+1)]
                          if len(x) else None),
        }
    return output


def compare_one(case: dict, workspace: Path, native_root: Path, output_root: Path) -> dict:
    experiment_dir = (workspace / case["monitor"]).parent
    experiment_path = experiment_dir / "experiment.json"
    experiment = load(experiment_path)
    run_path = experiment_dir / "monitor_report.json"
    run = load(run_path)
    audit = load(experiment_dir / "engine001-lab-audit.json")
    plan_path = (workspace / "AutoDraw_Stage20/data/results/brush_behavior_tests"
                 / PureWindowsPath(experiment["drawing_plan_path"]).name)
    plan = load(plan_path)
    matrix = experiment["chalk_experiment_matrix"]
    if (run["run_id"] != case["run_id"] or audit["run_id"] != run["run_id"]
            or audit["source_experiment_id"] != experiment["experiment_id"]
            or plan["generation"]["chalk_experiment_matrix"] != matrix):
        raise ValueError("Immutable ENGINE-001 plan/experiment/run identity mismatch.")
    native_dir = native_root / case["output_subdir"]
    manifest_path = native_dir / "manifest.json"
    manifest = load(manifest_path)
    fixtures = manifest.get("fixtures", [])
    if len(fixtures) != 1 or fixtures[0].get("id") != "live-accepted-points":
        raise ValueError("Native renderer fixture missing or ambiguous.")
    fixture = fixtures[0]
    points = [{"x": p["x"], "y": p["y"]} for p in run["accepted_points"]]
    if fixture["sourceRunId"] != run["run_id"] or fixture["points"] != points:
        raise ValueError("Native renderer did not replay the exact accepted point coordinates.")
    capture_gate = validate_paired_capture(experiment, run, plan, fixture)

    before_path = experiment_dir / "before_clear-screen.png"
    after_path = experiment_dir / "after_draw-screen.png"
    before = np.asarray(Image.open(before_path).convert("RGB"), dtype=np.uint8)
    after = np.asarray(Image.open(after_path).convert("RGB"), dtype=np.uint8)
    if before.shape != after.shape:
        raise ValueError("Full-screen before/after image dimensions differ.")
    size = (before.shape[1], before.shape[0])
    roi = plan["generation"]["screen_transform"]["screen_roi"]
    inspect = build_same_run_geometry_audit_input(experiment, run, size)
    board_bounds = detect_board_bounds_from_screenshots(before, after, roi)
    geometry = derive_live_board_screen_transform(
        run, inspect, roi, size, screenshot_board_bounds=board_bounds["bounds"],
    )
    geometry_gate = validate_transform_geometry(geometry, experiment["test_case"])
    output_dir = output_root / case["output_subdir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    input_report = {
        "run_id": run["run_id"], "transform": geometry,
        "screen_compositing": {
            "screen_size": {"width": size[0], "height": size[1]},
            "browser": {"expected_user_agent": manifest["browser"]["userAgent"]},
        },
        "board_bounds_audit": board_bounds,
        "thresholds": {"formal_screen_rgb_delta": 24.0},
    }
    input_path = output_dir / "same-run-comparison-input.json"
    input_path.write_text(json.dumps(input_report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    stage = compare_stage_variants(
        experiment["test_case"], manifest_path, native_dir, experiment_dir,
        input_path, output_dir, ["A", "B", "C", "D"],
    )
    crosscheck = stage["board_origin_crosschecks"]["A"]
    if not crosscheck["passed"]:
        geometry_gate["passed"] = False
        geometry_gate["status"] = "FAIL"
        geometry_gate["failed_checks"].append("native_stage_origin_crosscheck")
    metrics = stage["variants"]["A"]["comparison_metrics"]
    pixel_gate = validate_renderer_comparison(
        metrics, metrics["observed_pixels"], metric_suffix="screen_rgb_delta_24",
    )
    formal = evaluate_per_run_acceptance(capture_gate, geometry_gate, pixel_gate)
    source_paths = [experiment_path, run_path, experiment_dir/"engine001-lab-audit.json",
                    plan_path, before_path, after_path, experiment_dir/"before_clear-board.png",
                    experiment_dir/"after_draw-board.png", manifest_path]
    for source in source_paths:
        historical = audit.get("raw_sha256", {}).get(source.name)
        if historical is not None and sha(source) != historical:
            raise ValueError(f"Immutable capture SHA-256 mismatch: {source}")
    native_a = native_dir/"stage-level-A-webgl-exact_fractional_backing_origin.png"
    result = {
        "protocol": PROTOCOL, "status": formal["status"],
        "run_id": run["run_id"], "session_id": run["session_id"],
        "experiment_id": experiment["experiment_id"],
        "scenario": experiment["test_case"], "repeat_index": matrix["repeat_index"],
        "exact_chalk": run["chalk"]["consumed_points"],
        "accepted_count": len(points), "observed_mode": "smooth=true",
        "sources": {str(path): sha(path) for path in source_paths},
        "native_stage_png_sha256": {v: stage["variants"][v]["stage_png_sha256"]
                                    for v in ("A", "B", "C", "D")},
        "capture_gate": capture_gate, "geometry_gate": geometry_gate,
        "pixel_gate": pixel_gate, "formal_acceptance": formal,
        "stage_comparison": stage, "native_alpha": alpha_diagnostics(native_a),
        "limits": [
            "Live screenshots are RGB, not native alpha; alpha-to-alpha comparison unavailable",
            "A is run-bound native Egret WebGL fractional Stage placement; B/C/D are controls",
            "Native Stage replay models final PNG, not original temporal rendering order",
            "No post-hoc alignment or acceptance threshold changes",
        ],
    }
    (output_dir/"e5-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    journal = args.journal if args.journal.is_absolute() else workspace/args.journal
    cases = discover_engine001_cases(journal.resolve(), workspace)
    args.output_root.mkdir(parents=True, exist_ok=True)
    done, blocked = [], []
    for case in cases:
        try:
            result = compare_one(case, workspace, args.reference_root.resolve(),
                                 args.output_root.resolve())
            done.append(result)
            print(f"{case['name']}: {result['status']}, IoU={result['stage_comparison']['variants']['A']['comparison_metrics']['iou']:.6f}", flush=True)
        except Exception as error:
            blocked.append({"case": case["name"], "status": "BLOCKED", "error": repr(error)})
            print(f"{case['name']}: BLOCKED: {error!r}", file=sys.stderr, flush=True)
    counts = Counter(r["status"] for r in done)
    summary = {
        "protocol": PROTOCOL,
        "source_evidence_commit": "177165361b0340515fe3bb74f4847ab3ec579ebc",
        "journal_sha256": sha(journal),
        "status": ("PASS_E5_SCREEN_RGB_9_OF_9" if len(done) == 9
                   and counts["PASS_PER_RUN"] == 9 else "PARTIAL_E5"),
        "completed": len(done), "accepted": counts["PASS_PER_RUN"],
        "rejected": counts["REJECTED_PER_RUN"], "blocked": blocked,
        "runs": [{"run_id": item["run_id"], "scenario": item["scenario"],
                  "repeat_index": item["repeat_index"], "status": item["status"],
                  "metrics": item["stage_comparison"]["variants"]["A"]["comparison_metrics"]}
                 for item in done],
        "interpretation": "Screen RGB gate only; not bitwise parity, live alpha or temporal E5.",
    }
    (args.output_root/(PROTOCOL+".json")).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8",
    )
    print(json.dumps({"status": summary["status"], "completed": len(done),
                      "accepted": summary["accepted"], "rejected": summary["rejected"],
                      "blocked": blocked}, ensure_ascii=False))
    return 0 if len(done) == 9 and not blocked else 2


if __name__ == "__main__":
    raise SystemExit(main())
