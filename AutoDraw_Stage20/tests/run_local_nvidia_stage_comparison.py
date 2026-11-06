#!/usr/bin/env python3
"""Compare saved local NVIDIA Stage A-D renders with their same-run live captures.

This is an offline diagnostic. It never opens the game or consumes CHALK, and it
never turns Stage metrics into a formal renderer acceptance decision.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

PREPARATION_ROOT = Path(__file__).resolve().parents[1] / "source" / "preparation"
sys.path.insert(0, str(PREPARATION_ROOT))
from renderer_acceptance import summarize_multi_axis_series  # noqa: E402

CASES = {
    "vertical": {
        "run_id": "c860234f-995a-4789-9ac2-e05b322fe742",
        "experiment_id": "6f2227c7bce94fa5acd0c633af5ed04f",
        "session_id": "30e55d53-8eae-4d99-884f-0cf0c6d0a8bc",
        "experiment_dir": "experiment-20261105-192426-b10-paired_renderer_vertical_single_stroke-6f2227c7",
    },
    "diagonal": {
        "run_id": "f69cb0f4-f5d0-4ff9-a3b7-1148c38fa07f",
        "experiment_id": "0e61bc40e5a8432fb87fa80b95889f4e",
        "session_id": "fa8c4845-3158-4763-8d53-c1b9f5fae144",
        "experiment_dir": "experiment-20261105-192602-b10-paired_renderer_diagonal_single_stroke-0e61bc40",
    },
}
VARIANTS = ("A", "B", "C", "D")


def _renderer_text(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    return " ".join(
        str(value.get(key, "") or "")
        for key in ("renderer", "unmaskedRenderer")
    ).strip()


def validate_browser_session(session: dict[str, Any]) -> None:
    """Fail closed unless the saved source PNGs came from the expected NVIDIA session."""
    if not isinstance(session, dict):
        raise ValueError("Browser session must be a JSON object.")
    version = str(session.get("version", ""))
    if session.get("browser") != "Firefox" or version.split(".", 1)[0] != "159":
        raise ValueError(f"Expected headed Firefox 159 source session; got {session.get('browser')!r} {version!r}.")
    if str(session.get("expectedMajor", "")) != "159":
        raise ValueError("Saved browser session does not declare expected Firefox major 159.")
    if session.get("headless") is not False:
        raise ValueError("Local NVIDIA source session must be headed (headless=false).")

    actual_renderer = _renderer_text(session.get("webgl"))
    expected_renderer = _renderer_text(session.get("expectedWebGLRenderer"))
    if "NVIDIA" not in actual_renderer.upper() or "NVIDIA" not in expected_renderer.upper():
        raise ValueError(
            "Both actual and expected WebGL renderer descriptions must identify NVIDIA; "
            f"actual={actual_renderer!r}, expected={expected_renderer!r}."
        )

    actual_context = session.get("contextAttributes")
    expected_context = session.get("expectedContextAttributes")
    if not isinstance(actual_context, dict) or actual_context.get("antialias") is not True:
        raise ValueError("Local NVIDIA WebGL context must have antialias=true.")
    if actual_context != expected_context:
        raise ValueError("Saved actual WebGL context attributes differ from expected source attributes.")
    if session.get("contextAttributeDifferences") not in ({}, None):
        raise ValueError("Saved browser session reports WebGL context attribute differences.")


def validate_manifest_binding(
    manifest: dict[str, Any],
    comparison_report: dict[str, Any],
    expected_run_id: str,
) -> None:
    """Require Stage, Monitor-derived comparison and original live run to be identical."""
    if not isinstance(manifest, dict) or not isinstance(comparison_report, dict):
        raise ValueError("Stage manifest and comparison report must be JSON objects.")
    profile = manifest.get("runtimeProfile")
    fixtures = manifest.get("fixtures")
    if not isinstance(profile, dict) or not isinstance(fixtures, list) or len(fixtures) != 1:
        raise ValueError("Stage manifest must contain one run-bound fixture and runtime profile.")
    fixture = fixtures[0]
    if not isinstance(fixture, dict) or fixture.get("id") != "live-accepted-points":
        raise ValueError("Stage manifest does not contain the expected live-accepted-points fixture.")
    if manifest.get("stageLevelCompositor", {}).get("status") != "generated_four_offline_variants":
        raise ValueError("Stage manifest does not confirm generation of all four A-D variants.")

    expected_bindings = {
        "run_id": expected_run_id,
        "session_id": CASES[next(
            name for name, item in CASES.items() if item["run_id"] == expected_run_id
        )]["session_id"],
        "experiment_id": CASES[next(
            name for name, item in CASES.items() if item["run_id"] == expected_run_id
        )]["experiment_id"],
    }
    for key, expected in expected_bindings.items():
        if comparison_report.get(key) != expected:
            raise ValueError(f"Comparison report {key} binding mismatch: {comparison_report.get(key)!r} != {expected!r}.")

    if profile.get("sourceRunId") != expected_run_id or fixture.get("sourceRunId") != expected_run_id:
        raise ValueError("Stage manifest sourceRunId does not match the expected live run.")
    if profile.get("sourceSessionId") != expected_bindings["session_id"]:
        raise ValueError("Stage manifest sourceSessionId does not match the expected live session.")
    if profile.get("sourceExperimentId") != expected_bindings["experiment_id"]:
        raise ValueError("Stage manifest sourceExperimentId does not match the expected live experiment.")

    formal = comparison_report.get("formal_acceptance")
    if not isinstance(formal, dict):
        raise ValueError("Same-run comparison report is missing formal capture/transform gates.")
    for gate in ("capture", "transform"):
        item = formal.get(gate)
        if not isinstance(item, dict) or item.get("passed") is not True:
            raise ValueError(f"Same-run {gate} gate must pass before Stage diagnostic comparison.")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _safe_extract(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"Local NVIDIA Stage ZIP failed CRC validation at {bad_member!r}.")
        root = destination.resolve()
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise ValueError(f"Unsafe path in Stage ZIP: {member.filename!r}.")
        archive.extractall(destination)


def run_diagnostics(
    archive_path: Path,
    paired_report_root: Path,
    experiment_root: Path,
    output_dir: Path,
    series_output: Path,
) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    paired_report_root = paired_report_root.resolve()
    experiment_root = experiment_root.resolve()
    output_dir = output_dir.resolve()
    series_output = series_output.resolve()

    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    if not paired_report_root.is_dir():
        raise FileNotFoundError(f"Paired report directory does not exist: {paired_report_root}")

    source_reports = sorted(paired_report_root.rglob("comparison-report-independent-transform.json"))
    if not source_reports:
        raise FileNotFoundError("No independent-transform per-run reports found for series aggregation.")
    reports = [_read_json(path) for path in source_reports]
    series = summarize_multi_axis_series(reports, required_repeats=3)
    series["report_count"] = len(reports)
    series["source_reports"] = [str(path) for path in source_reports]
    series_output.parent.mkdir(parents=True, exist_ok=True)
    series_output.write_text(json.dumps(series, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    output_dir.mkdir(parents=True, exist_ok=True)
    stage_root = Path(__file__).resolve().parents[1]
    comparator = Path(__file__).with_name("compare_stage_renderer_reference.py").resolve()
    stage_results: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="autodraw-local-nvidia-stage-") as temporary:
        extracted_root = Path(temporary) / "archive"
        extracted_root.mkdir(parents=True, exist_ok=True)
        _safe_extract(archive_path, extracted_root)

        for orientation, case in CASES.items():
            stage_dir = extracted_root / f"stage-level-{orientation}"
            session_path = stage_dir / "browser-session.json"
            manifest_path = stage_dir / "manifest.json"
            report_path = paired_report_root / orientation / "comparison-report-independent-transform.json"
            experiment_dir = experiment_root / case["experiment_dir"]
            for required in (session_path, manifest_path, report_path, experiment_dir / "before_clear-screen.png",
                             experiment_dir / "after_draw-screen.png"):
                if not required.exists():
                    raise FileNotFoundError(required)

            session = _read_json(session_path)
            manifest = _read_json(manifest_path)
            comparison_report = _read_json(report_path)
            validate_browser_session(session)
            validate_manifest_binding(manifest, comparison_report, case["run_id"])

            case_output = output_dir / orientation
            command = [
                sys.executable,
                str(comparator),
                "--orientation", orientation,
                "--stage-manifest", str(manifest_path),
                "--stage-png-dir", str(stage_dir),
                "--experiment-dir", str(experiment_dir),
                "--comparison-report", str(report_path),
                "--output-dir", str(case_output),
                "--variants", *VARIANTS,
            ]
            completed = subprocess.run(command, cwd=stage_root, check=False)
            if completed.returncode != 0:
                raise RuntimeError(
                    f"Local NVIDIA Stage comparator failed for {orientation} with exit code {completed.returncode}."
                )

            result_path = case_output / f"stage-level-{orientation}-comparison.json"
            result = _read_json(result_path)
            if result.get("status") != "DIAGNOSTIC_ONLY" or result.get("acceptance_decision_applied") is not False:
                raise ValueError(f"{orientation} Stage result must remain DIAGNOSTIC_ONLY.")
            if result.get("run_id") != case["run_id"] or result.get("post_hoc_alignment") is not False:
                raise ValueError(f"{orientation} Stage result has incorrect provenance or alignment status.")
            crosschecks = result.get("board_origin_crosschecks")
            if not isinstance(crosschecks, dict) or set(crosschecks) != set(VARIANTS):
                raise ValueError(f"{orientation} Stage result is missing one or more A-D origin crosschecks.")
            if any(item.get("passed") is not True for item in crosschecks.values()):
                raise ValueError(f"{orientation} Stage result contains a failed independent board-origin crosscheck.")
            stage_results[orientation] = {
                "run_id": result["run_id"],
                "status": result["status"],
                "browser": result.get("browser"),
                "baseline_round_trip": result.get("baseline_round_trip"),
                "board_origin_crosschecks": crosschecks,
                "variants": {
                    name: item.get("comparison_metrics")
                    for name, item in result.get("variants", {}).items()
                },
                "limitations": result.get("limitations", []),
            }

    summary = {
        "status": "complete",
        "acceptance_decision_applied": False,
        "series_acceptance": series,
        "local_nvidia_stage_comparisons": stage_results,
        "interpretation": (
            "Stage A-D results are diagnostic only. They do not count as PASS_PER_RUN captures. "
            "Multi-axis acceptance requires three unique formal PASS_PER_RUN runs for each orientation."
        ),
    }
    summary_path = output_dir / "local-nvidia-stage-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--paired-report-root", type=Path, required=True)
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--series-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_diagnostics(
            args.archive,
            args.paired_report_root,
            args.experiment_root,
            args.output_dir,
            args.series_output,
        )
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({
        "status": result["status"],
        "series_status": result["series_acceptance"]["status"],
        "orientations": {
            name: {
                "status": item["status"],
                "accepted": len(item["accepted_runs"]),
                "rejected": len(item["rejected_runs"]),
                "missing": item["missing_valid_repeats"],
            }
            for name, item in result["series_acceptance"]["orientations"].items()
        },
        "local_stage_variants": {
            orientation: item["variants"]
            for orientation, item in result["local_nvidia_stage_comparisons"].items()
        },
        "output": str(args.output_dir),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
