from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))
from run_local_nvidia_stage_comparison import (  # noqa: E402
    CASES,
    validate_browser_session,
    validate_manifest_binding,
)


def _valid_session():
    renderer = "ANGLE (NVIDIA, NVIDIA GeForce GTX 980 Direct3D11)"
    context = {"alpha": True, "antialias": True, "depth": True, "stencil": False}
    return {
        "browser": "Firefox",
        "version": "159.0.1",
        "expectedMajor": "159",
        "headless": False,
        "webgl": {"renderer": renderer},
        "expectedWebGLRenderer": {"renderer": renderer},
        "contextAttributes": context,
        "expectedContextAttributes": dict(context),
        "contextAttributeDifferences": {},
    }


def _valid_binding():
    case = CASES["vertical"]
    run_id = case["run_id"]
    session_id = case["session_id"]
    experiment_id = case["experiment_id"]
    manifest = {
        "runtimeProfile": {
            "sourceRunId": run_id,
            "sourceSessionId": session_id,
            "sourceExperimentId": experiment_id,
        },
        "fixtures": [{"id": "live-accepted-points", "sourceRunId": run_id}],
        "stageLevelCompositor": {"status": "generated_four_offline_variants"},
    }
    report = {
        "run_id": run_id,
        "session_id": session_id,
        "experiment_id": experiment_id,
        "formal_acceptance": {
            "capture": {"passed": True},
            "transform": {"passed": True},
        },
    }
    return manifest, report, run_id


def test_local_nvidia_browser_session_accepts_expected_headed_firefox_context():
    validate_browser_session(_valid_session())


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update({"headless": True}),
        lambda value: value.update({"version": "158.0"}),
        lambda value: value["contextAttributes"].update({"antialias": False}),
        lambda value: value["webgl"].update({"renderer": "Microsoft Basic Render Driver"}),
    ],
)
def test_local_nvidia_browser_session_rejects_wrong_source_environment(change):
    session = _valid_session()
    change(session)
    with pytest.raises(ValueError):
        validate_browser_session(session)


def test_stage_manifest_requires_exact_run_session_and_experiment_binding():
    manifest, report, run_id = _valid_binding()
    validate_manifest_binding(manifest, report, run_id)


@pytest.mark.parametrize("field", ["run_id", "session_id", "experiment_id"])
def test_stage_manifest_rejects_mismatched_comparison_report_binding(field):
    manifest, report, run_id = _valid_binding()
    report[field] = "different"
    with pytest.raises(ValueError):
        validate_manifest_binding(manifest, report, run_id)


def test_stage_manifest_rejects_failed_capture_or_transform_gate():
    manifest, report, run_id = _valid_binding()
    report["formal_acceptance"]["transform"]["passed"] = False
    with pytest.raises(ValueError):
        validate_manifest_binding(manifest, report, run_id)


def test_stage_manifest_rejects_unknown_expected_run():
    manifest, report, _ = _valid_binding()
    with pytest.raises(ValueError):
        validate_manifest_binding(manifest, report, "unknown-run")
