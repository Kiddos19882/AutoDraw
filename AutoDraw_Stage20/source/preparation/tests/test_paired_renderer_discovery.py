from __future__ import annotations

import json
from pathlib import Path

import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))
from run_paired_renderer_acceptance import (  # noqa: E402
    discover_paired_renderer_runs,
    renderer_reference_directory,
    renderer_manifest_path,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from renderer_acceptance import EXPECTED_EXECUTOR_CONFIG  # noqa: E402


def _write_candidate(root: Path, scenario: str, experiment_id: str, run_id: str):
    session_id = f"session-{experiment_id}"
    folder = root / f"experiment-20261106-b10-{scenario}-{experiment_id[:8]}"
    folder.mkdir(parents=True)
    plan_name = f"brush-plan-{scenario}-{experiment_id[:8]}.json"
    plan = {
        "generation": {
            "experiment_id": experiment_id,
            "test_case": scenario,
            "requested_brush_value": 10,
            "paired_renderer_capture": {
                "schema_version": 1,
                "scenario_id": scenario,
                "requested_radius": 10,
                "expected_strokes": 1,
                "renderer_path_mode": "smooth",
                "executor_parameters": dict(EXPECTED_EXECUTOR_CONFIG),
            },
        },
        "strokes": [{"points": [{"x": 230, "y": 20}, {"x": 230, "y": 220}]}],
    }
    (root / plan_name).write_text(json.dumps(plan), encoding="utf-8")
    experiment = {
        "experiment_id": experiment_id,
        "test_case": scenario,
        "drawing_plan_path": f"C:\\AutoDraw\\data\\results\\brush_behavior_tests\\{plan_name}",
        "game_monitor_summary": {
            "autodraw_experiment_id": experiment_id,
            "run_id": run_id,
            "session_id": session_id,
        },
    }
    monitor = {
        "record_type": "autodraw_game_monitor_run",
        "autodraw_experiment_id": experiment_id,
        "run_id": run_id,
        "session_id": session_id,
    }
    (folder / "experiment.json").write_text(json.dumps(experiment), encoding="utf-8")
    (folder / "monitor_report.json").write_text(json.dumps(monitor), encoding="utf-8")
    return folder


def test_discovery_finds_vertical_and_diagonal_run_bound_inputs(tmp_path):
    _write_candidate(tmp_path, "paired_renderer_vertical_single_stroke", "exp-vertical", "run-vertical")
    _write_candidate(tmp_path, "paired_renderer_diagonal_single_stroke", "exp-diagonal", "run-diagonal")

    candidates, rejected = discover_paired_renderer_runs(tmp_path)

    assert rejected == []
    assert {item["orientation"] for item in candidates} == {"vertical", "diagonal"}
    assert {item["run_id"] for item in candidates} == {"run-vertical", "run-diagonal"}


def test_discovery_rejects_missing_monitor_report(tmp_path):
    folder = _write_candidate(
        tmp_path, "paired_renderer_vertical_single_stroke", "exp-vertical", "run-vertical",
    )
    (folder / "monitor_report.json").unlink()

    candidates, rejected = discover_paired_renderer_runs(tmp_path)

    assert candidates == []
    assert len(rejected) == 1
    assert "monitor_report.json is missing" in rejected[0]["reasons"]


def test_discovery_rejects_duplicate_run_ids(tmp_path):
    _write_candidate(tmp_path, "paired_renderer_vertical_single_stroke", "exp-one", "run-duplicate")
    _write_candidate(tmp_path, "paired_renderer_diagonal_single_stroke", "exp-two", "run-duplicate")

    candidates, rejected = discover_paired_renderer_runs(tmp_path)

    assert len(candidates) == 1
    assert len(rejected) == 1
    assert any("duplicate run_id" in reason for reason in rejected[0]["reasons"])


def test_discovery_ignores_other_brush_scenarios(tmp_path):
    folder = tmp_path / "experiment-20261106-horizontal"
    folder.mkdir()
    (folder / "experiment.json").write_text(
        json.dumps({"test_case": "paired_renderer_single_stroke"}), encoding="utf-8",
    )

    candidates, rejected = discover_paired_renderer_runs(tmp_path)

    assert candidates == []
    assert rejected == []


def test_renderer_reference_directory_is_bound_to_each_nonbaseline_run(tmp_path):
    renderer_root = tmp_path / "committed"
    run_root = tmp_path / "run-bound"

    original = renderer_reference_directory(
        renderer_root, "vertical", "c860234f-995a-4789-9ac2-e05b322fe742", run_root,
    )
    additional = renderer_reference_directory(
        renderer_root, "vertical", "new-vertical-run", run_root,
    )

    assert original == renderer_root / "vertical"
    assert additional == run_root / "vertical" / "new-vertical-run"


def test_renderer_manifest_path_accepts_generated_run_bound_manifest_name(tmp_path):
    generated = tmp_path / "manifest.json"
    generated.write_text("{}", encoding="utf-8")

    resolved = renderer_manifest_path(tmp_path, "egret-5.4.1-renderer-reference-manifest.json")

    assert resolved == generated


def test_renderer_manifest_path_prefers_expected_committed_name(tmp_path):
    expected = tmp_path / "egret-5.4.1-renderer-reference-manifest.json"
    expected.write_text("{}", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{\"generated\": true}", encoding="utf-8")

    assert renderer_manifest_path(tmp_path, expected.name) == expected
