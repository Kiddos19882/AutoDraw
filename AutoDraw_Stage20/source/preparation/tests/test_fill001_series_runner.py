"""Synthetic-only FILL001-SERIES-001 tests; never connect to the game."""
import json
from pathlib import Path

import pytest

from fill001_series_runner import (
    SeriesBlocked, build_manifest, run_with_validated_callbacks,
    validate_manifest, write_manifest,
)


def manifest(**kwargs):
    return build_manifest(cycles=kwargs.pop("cycles", 2),
                          figures_per_cycle=kwargs.pop("figures_per_cycle", 3),
                          shapes=kwargs.pop("shapes", ["rectangle", "wide_irregular", "narrow_irregular"]),
                          methods=kwargs.pop("methods", ["dense_scanlines", "spaced_scanlines"]),
                          radii=kwargs.pop("radii", [1, 5, 10]),
                          series_id="series-test")


def fake_callbacks(*, invalid_run=False, invalid_clear=False):
    state = {"n": 0, "clears": 0}
    def observe(task):
        state["n"] += 1
        return {"valid": True, "fresh_board": True, "pointCount": 1,
                "calibration_valid": True, "session_id": f"fresh-{state['n']}"}
    def run(task):
        return {"task_id": task["task_id"], "session_id": f"fresh-{state['n']}",
                "execution_status": "completed", "monitor_binding": "EXACT_RUN_BOUND",
                "quality_gate": "PASS" if not invalid_run else "FAIL",
                "mouse_release_succeeded": True, "pre_pointCount": 1,
                "post_pointCount": 101, "actual_chalk": 100,
                "run_id": f"run-{state['n']}",
                "before_png_sha256": "a"*64, "after_settled_png_sha256": "b"*64}
    def clear(task):
        state["clears"] += 1
        return {"valid": not invalid_clear, "pointCount": 1,
                "mouse_released": True, "fresh_board": True}
    return state, observe, run, clear


def test_schedule_counts_order_and_identity():
    m = manifest()
    assert len(m["tasks"]) == 6
    assert [t["cycle"] for t in m["tasks"]] == [1, 1, 1, 2, 2, 2]
    assert [t["figure_in_cycle"] for t in m["tasks"]] == [1, 2, 3, 1, 2, 3]
    assert m["execution_allowed"] is False
    assert m["automatic_clear_allowed"] is False
    validate_manifest(m)


@pytest.mark.parametrize("field,value", [
    ("cycles", 0), ("cycles", -2), ("cycles", True),
    ("figures_per_cycle", 0), ("figures_per_cycle", 101),
    ("cycles", 101), ("shapes", ["unknown"]),
    ("methods", ["oracle"]), ("radii", [0]), ("radii", [3]),
    ("shapes", ["rectangle", "rectangle"]),
])
def test_invalid_schedule_fails_closed(field, value):
    with pytest.raises(SeriesBlocked):
        manifest(**{field:value})


def test_too_many_tasks_blocked():
    with pytest.raises(SeriesBlocked, match="250"):
        manifest(cycles=10, figures_per_cycle=26)


def test_manifest_tampering_and_write_without_overwrite(tmp_path):
    m = manifest()
    p = tmp_path / "manifest.json"
    write_manifest(m, p)
    assert json.loads(p.read_text(encoding="utf-8")) == m
    with pytest.raises(FileExistsError):
        write_manifest(m, p)
    m["tasks"][0]["execution_allowed"] = True
    with pytest.raises(SeriesBlocked):
        validate_manifest(m)


def test_all_figures_capture_then_clear_except_final(tmp_path):
    m = manifest()
    state, observe, run, clear = fake_callbacks()
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path,
        observe_blank=observe, run_one=run, clear_and_verify=clear)
    assert report["status"] == "completed"
    assert report["accepted"] == 6
    assert report["exact_chalk_sum_of_accepted_runs"] == 600
    assert sum(x["accepted"] for x in report["grouped_exact_chalk_statistics"]["shape"].values()) == 6
    assert sum(x["total_exact_chalk"] for x in report["grouped_exact_chalk_statistics"]["brush"].values()) == 600
    assert state == {"n": 6, "clears": 5}
    assert len(list(tmp_path.glob("*.json"))) == 11


def test_no_clear_after_quality_fail_and_negative_result_saved(tmp_path):
    m = manifest()
    state, observe, run, clear = fake_callbacks(invalid_run=True)
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path,
        observe_blank=observe, run_one=run, clear_and_verify=clear)
    assert report["status"] == "blocked"
    assert report["accepted"] == 0
    assert state["clears"] == 0
    saved = list(tmp_path.glob("*.json"))
    assert len(saved) == 1
    assert json.loads(saved[0].read_text(encoding="utf-8"))["status"] == "BLOCKED"


def test_no_next_figure_on_unverified_clear(tmp_path):
    m = manifest()
    state, observe, run, clear = fake_callbacks(invalid_clear=True)
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path,
        observe_blank=observe, run_one=run, clear_and_verify=clear)
    assert report["status"] == "blocked"
    assert report["accepted"] == 1
    assert state == {"n": 1, "clears": 1}
    negative = list(tmp_path.glob("*.clear.json"))
    assert len(negative) == 1
    assert json.loads(negative[0].read_text(encoding="utf-8"))["status"] == "BLOCKED"


def test_stop_before_game_interaction(tmp_path):
    m = manifest()
    state, observe, run, clear = fake_callbacks()
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path, observe_blank=observe,
        run_one=run, clear_and_verify=clear,
        stop_requested=lambda: True)
    assert report["status"] == "stopped"
    assert state == {"n": 0, "clears": 0}


def test_existing_run_never_overwritten(tmp_path):
    m = manifest()
    path = tmp_path / (m["tasks"][0]["task_id"] + ".json")
    path.write_text("immutable evidence", encoding="utf-8")
    state, observe, run, clear = fake_callbacks()
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path, observe_blank=observe,
        run_one=run, clear_and_verify=clear)
    assert report["status"] == "blocked"
    assert state["n"] == 0
    assert path.read_text(encoding="utf-8") == "immutable evidence"
