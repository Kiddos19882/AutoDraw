#!/usr/bin/env python3
"""Discover and replay every saved vertical/diagonal paired-renderer experiment."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PureWindowsPath
from typing import Any

PREPARATION_ROOT = Path(__file__).resolve().parents[1] / "source" / "preparation"
sys.path.insert(0, str(PREPARATION_ROOT))
from renderer_acceptance import EXPECTED_EXECUTOR_CONFIG, summarize_multi_axis_series  # noqa: E402

SCENARIOS = {
    "paired_renderer_vertical_single_stroke": {
        "orientation": "vertical",
        "offline_png": "live-accepted-points-width-10-webgl-board-reference.png",
        "manifest": "egret-5.4.1-renderer-reference-manifest.json",
    },
    "paired_renderer_diagonal_single_stroke": {
        "orientation": "diagonal",
        "offline_png": "live-accepted-points-width-10-webgl-board-reference.png",
        "manifest": "egret-5.4.1-renderer-reference-manifest.json",
    },
}
ORIGINAL_RUN_IDS = {
    "vertical": "c860234f-995a-4789-9ac2-e05b322fe742",
    "diagonal": "f69cb0f4-f5d0-4ff9-a3b7-1148c38fa07f",
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _scenario_from_name(value: str) -> str | None:
    return next((scenario for scenario in SCENARIOS if scenario in value), None)


def _plan_filename(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    return PureWindowsPath(raw).name or Path(raw).name


def discover_paired_renderer_runs(
    experiment_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Find all vertical/diagonal captures and preflight their run-bound inputs."""
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_run_ids: dict[str, str] = {}

    for experiment_dir in sorted(experiment_root.glob("experiment-*")):
        if not experiment_dir.is_dir():
            continue
        experiment_path = experiment_dir / "experiment.json"
        try:
            experiment = _read_json(experiment_path)
        except Exception as exc:
            scenario = _scenario_from_name(experiment_dir.name)
            if scenario is not None:
                rejected.append({
                    "scenario_id": scenario,
                    "orientation": SCENARIOS[scenario]["orientation"],
                    "experiment_dir": str(experiment_dir),
                    "run_id": None,
                    "experiment_id": None,
                    "reasons": [f"experiment.json unavailable or invalid: {exc}"],
                })
            continue

        scenario = experiment.get("test_case")
        if scenario not in SCENARIOS:
            scenario = _scenario_from_name(experiment_dir.name)
        if scenario not in SCENARIOS:
            continue

        orientation = SCENARIOS[scenario]["orientation"]
        summary = experiment.get("game_monitor_summary")
        summary = summary if isinstance(summary, dict) else {}
        run_id = summary.get("run_id")
        session_id = summary.get("session_id")
        experiment_id = experiment.get("experiment_id")
        candidate: dict[str, Any] = {
            "scenario_id": scenario,
            "orientation": orientation,
            "experiment_dir": str(experiment_dir),
            "run_id": run_id,
            "session_id": session_id,
            "experiment_id": experiment_id,
        }
        reasons: list[str] = []

        if not experiment_id or summary.get("autodraw_experiment_id") != experiment_id:
            reasons.append("experiment id is missing or not bound to Game Monitor summary")
        if not run_id:
            reasons.append("Game Monitor run_id is missing")
        if not session_id:
            reasons.append("Game Monitor session_id is missing")

        monitor_path = experiment_dir / "monitor_report.json"
        if not monitor_path.is_file():
            reasons.append("monitor_report.json is missing")
        else:
            try:
                monitor = _read_json(monitor_path)
                if monitor.get("record_type") != "autodraw_game_monitor_run":
                    reasons.append("monitor report record_type is invalid")
                if monitor.get("run_id") != run_id or monitor.get("session_id") != session_id:
                    reasons.append("monitor report run/session binding mismatch")
                if monitor.get("autodraw_experiment_id") != experiment_id:
                    reasons.append("monitor report experiment binding mismatch")
            except Exception as exc:
                reasons.append(f"monitor_report.json is invalid: {exc}")

        plan_name = _plan_filename(experiment.get("drawing_plan_path"))
        plan_path = experiment_root / plan_name if plan_name else None
        if plan_path is None or not plan_path.is_file():
            reasons.append(f"drawing plan is missing: {plan_name or '<no path>'}")
        else:
            try:
                plan = _read_json(plan_path)
                generation = plan.get("generation")
                generation = generation if isinstance(generation, dict) else {}
                contract = generation.get("paired_renderer_capture")
                contract = contract if isinstance(contract, dict) else {}
                if generation.get("experiment_id") != experiment_id:
                    reasons.append("drawing plan experiment_id mismatch")
                if generation.get("test_case") != scenario:
                    reasons.append("drawing plan test_case mismatch")
                if generation.get("requested_brush_value") != 10:
                    reasons.append("drawing plan requested brush value is not 10")
                if contract.get("schema_version") != 1 or contract.get("scenario_id") != scenario:
                    reasons.append("paired renderer capture contract mismatch")
                if contract.get("requested_radius") != 10 or contract.get("expected_strokes") != 1:
                    reasons.append("paired renderer capture radius/stroke contract mismatch")
                if contract.get("renderer_path_mode") != "smooth":
                    reasons.append("paired renderer path mode is not smooth")
                if contract.get("executor_parameters") != EXPECTED_EXECUTOR_CONFIG:
                    reasons.append("drawing plan executor parameters differ from the frozen profile")
                if not isinstance(plan.get("strokes"), list) or len(plan["strokes"]) != 1:
                    reasons.append("drawing plan must contain exactly one stroke")
            except Exception as exc:
                reasons.append(f"drawing plan is invalid: {exc}")

        if run_id:
            previous = seen_run_ids.get(str(run_id))
            if previous is not None:
                reasons.append(f"duplicate run_id also appears in {previous}")
            else:
                seen_run_ids[str(run_id)] = experiment_dir.name

        candidate["plan_path"] = str(plan_path) if plan_path is not None else None
        if reasons:
            rejected.append({**candidate, "reasons": reasons})
        else:
            candidates.append(candidate)

    return candidates, rejected


def renderer_reference_directory(
    renderer_root: Path,
    orientation: str,
    run_id: str,
    run_reference_root: Path | None = None,
) -> Path:
    """Return a renderer reference bound to this exact live run."""
    if run_id == ORIGINAL_RUN_IDS.get(orientation):
        return renderer_root / orientation
    root = run_reference_root if run_reference_root is not None else renderer_root / "paired-renderer"
    return root / orientation / run_id


def _write_preflight_rejection(output_root: Path, item: dict[str, Any]) -> Path:
    orientation = item["orientation"]
    identity = str(item.get("experiment_id") or Path(item["experiment_dir"]).name)
    safe_identity = re.sub(r"[^A-Za-z0-9_.-]+", "_", identity)
    report_path = (
        output_root / orientation / "preflight-rejected" / safe_identity
        / "comparison-report-independent-transform.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "source": "paired_renderer_discovery_preflight",
        "scenario_id": item["scenario_id"],
        "run_id": item.get("run_id"),
        "experiment_id": item.get("experiment_id"),
        "formal_acceptance": {
            "status": "REJECTED_PER_RUN",
            "passed": False,
            "failed_checks": ["preflight_input_binding"],
        },
        "preflight_rejection_reasons": item["reasons"],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path


def run_acceptance(
    experiment_root: Path,
    blank: Path,
    renderer_root: Path,
    output_root: Path,
    run_reference_root: Path | None = None,
) -> dict[str, Any]:
    experiment_root = experiment_root.resolve()
    blank = blank.resolve()
    renderer_root = renderer_root.resolve()
    run_reference_root = run_reference_root.resolve() if run_reference_root is not None else None
    output_root = output_root.resolve()
    if not experiment_root.is_dir():
        raise FileNotFoundError(experiment_root)
    if not blank.is_file():
        raise FileNotFoundError(blank)
    output_root.mkdir(parents=True, exist_ok=True)

    candidates, rejected = discover_paired_renderer_runs(experiment_root)
    per_run_results: list[dict[str, Any]] = []
    tool_errors: list[dict[str, str]] = []

    for item in rejected:
        _write_preflight_rejection(output_root, item)

    comparator = Path(__file__).with_name("compare_live_renderer_reference.py").resolve()
    for candidate in candidates:
        orientation = candidate["orientation"]
        reference = SCENARIOS[candidate["scenario_id"]]
        offline_dir = renderer_reference_directory(
            renderer_root, orientation, str(candidate["run_id"]), run_reference_root,
        )
        offline_png = offline_dir / reference["offline_png"]
        manifest = offline_dir / reference["manifest"]
        if not offline_png.is_file() or not manifest.is_file():
            rejected_item = {
                **candidate,
                "reasons": [
                    "run-bound offline renderer reference is missing: "
                    f"expected {offline_png.name} and {manifest.name} under {offline_dir}"
                ],
            }
            rejected.append(rejected_item)
            _write_preflight_rejection(output_root, rejected_item)
            continue

        if candidate["run_id"] == ORIGINAL_RUN_IDS[orientation]:
            case_output = output_root / orientation
        else:
            case_output = output_root / orientation / str(candidate["run_id"])
        case_output.mkdir(parents=True, exist_ok=True)

        source_dir = case_output / "source-captures"
        source_dir.mkdir(parents=True, exist_ok=True)
        for filename in ("before_clear-screen.png", "after_draw-screen.png"):
            source = Path(candidate["experiment_dir"]) / filename
            if source.is_file():
                (source_dir / filename).write_bytes(source.read_bytes())

        command = [
            sys.executable,
            str(comparator),
            "--experiment-dir", candidate["experiment_dir"],
            "--blank", str(blank),
            "--offline-png", str(offline_png),
            "--manifest", str(manifest),
            "--plan", str(candidate["plan_path"]),
            "--output-dir", str(case_output),
            "--same-run-geometry",
        ]
        completed = subprocess.run(command, cwd=Path(__file__).resolve().parents[1], check=False)
        report_path = case_output / "comparison-report-independent-transform.json"
        if completed.returncode not in (0, 2) or not report_path.is_file():
            tool_errors.append({
                "run_id": str(candidate["run_id"]),
                "error": f"Comparator execution failed (exit={completed.returncode}, report_exists={report_path.is_file()}).",
            })
            continue

        try:
            report = _read_json(report_path)
            if report.get("run_id") != candidate["run_id"]:
                raise ValueError("comparison report run_id mismatch")
            if report.get("experiment_id") != candidate["experiment_id"]:
                raise ValueError("comparison report experiment_id mismatch")
            if report.get("scenario_id") != candidate["scenario_id"]:
                raise ValueError("comparison report scenario_id mismatch")
            formal = report.get("formal_acceptance")
            status = formal.get("status") if isinstance(formal, dict) else "MISSING"
            per_run_results.append({
                "orientation": orientation,
                "run_id": candidate["run_id"],
                "experiment_id": candidate["experiment_id"],
                "status": status,
                "passed": status == "PASS_PER_RUN",
                "report": str(report_path),
            })
        except Exception as exc:
            tool_errors.append({"run_id": str(candidate["run_id"]), "error": str(exc)})

    report_paths = sorted(output_root.rglob("comparison-report-independent-transform.json"))
    reports = [_read_json(path) for path in report_paths]
    series = summarize_multi_axis_series(reports, required_repeats=3)
    series["report_count"] = len(reports)
    series["source_reports"] = [str(path) for path in report_paths]
    series["preflight_rejected_attempts"] = rejected
    series_path = output_root / "multi-axis-series-summary.json"
    series_path.write_text(json.dumps(series, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    discovery = {
        "schema_version": 1,
        "status": "COMPLETE" if not tool_errors else "TOOL_ERROR",
        "discovered_valid_inputs": len(candidates),
        "preflight_rejected_attempts": rejected,
        "per_run_results": per_run_results,
        "tool_errors": tool_errors,
        "series_status": series["status"],
        "series_summary_path": str(series_path),
    }
    discovery_path = output_root / "paired-renderer-discovery-summary.json"
    discovery_path.write_text(json.dumps(discovery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"series": series, "discovery": discovery}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--blank", type=Path, required=True)
    parser.add_argument("--renderer-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--run-reference-root", type=Path, default=None,
        help="Root containing per-run offline references at <orientation>/<run_id>/; original repeat-1 references remain under --renderer-root.",
    )
    args = parser.parse_args()
    try:
        result = run_acceptance(
            args.experiment_root, args.blank, args.renderer_root, args.output_root,
            args.run_reference_root,
        )
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    series = result["series"]
    print(json.dumps({
        "status": result["discovery"]["status"],
        "discovered_valid_inputs": result["discovery"]["discovered_valid_inputs"],
        "per_run_results": result["discovery"]["per_run_results"],
        "preflight_rejected_attempts": result["discovery"]["preflight_rejected_attempts"],
        "series_status": series["status"],
        "orientations": {
            name: {
                "accepted": len(item["accepted_runs"]),
                "rejected": len(item["rejected_runs"]),
                "missing": item["missing_valid_repeats"],
            }
            for name, item in series["orientations"].items()
        },
        "tool_errors": result["discovery"]["tool_errors"],
    }, ensure_ascii=False, indent=2))
    return 1 if result["discovery"]["tool_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
