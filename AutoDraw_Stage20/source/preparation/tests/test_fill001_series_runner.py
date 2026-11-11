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
        proof = {"schema": "FILL001_SERIES_BLANK_SCREEN_VERIFICATION_V1",
                 "status": "PASS", "session_id": f"fresh-{state['n']}",
                 "post_clear_pointCount": 1, "changed_screen_pixels": 0,
                 "reference_png_sha256": "a"*64,
                 "post_clear_png_sha256": "b"*64,
                 "clear_ui_action_proven": False,
                 "mapping_sha256": "a"*64,
                 "last_settled_at_utc": "2026-11-11T00:00:11+00:00"}
        return {"valid": not invalid_clear, "pointCount": 1,
                "mouse_released": True, "fresh_board": True,
                "blank_screen_verification": proof}
    return state, observe, run, clear


def test_schedule_counts_order_and_identity():
    m = manifest()
    assert len(m["tasks"]) == 6
    assert [t["cycle"] for t in m["tasks"]] == [1, 1, 1, 2, 2, 2]
    assert [t["figure_in_cycle"] for t in m["tasks"]] == [1, 2, 3, 1, 2, 3]
    assert [t["shape_id"] for t in m["tasks"]] == ["rectangle", "wide_irregular", "narrow_irregular"] * 2
    assert [t["fill_method"] for t in m["tasks"]] == ["dense_scanlines", "spaced_scanlines"] * 3
    assert [t["brush_radius"] for t in m["tasks"]] == [1, 5, 10] * 2
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
    assert len(list(tmp_path.glob("*.json"))) == 12
    summary = tmp_path / "series-test.summary.json"
    assert summary.is_file()
    assert json.loads(summary.read_text(encoding="utf-8"))["status"] == "completed"


def test_quality_fail_is_retained_and_still_requires_verified_clear(tmp_path):
    m = manifest()
    state, observe, run, clear = fake_callbacks(invalid_run=True)
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path,
        observe_blank=observe, run_one=run, clear_and_verify=clear)
    assert report["status"] == "completed"
    assert report["accepted"] == 0
    assert report["quality_failed"] == 6
    assert report["completed_with_bound_chalk"] == 6
    assert report["exact_chalk_sum_of_quality_failed_runs"] == 600
    assert state["clears"] == 5
    saved = [p for p in tmp_path.glob("*.json")
             if not p.name.endswith((".clear.json", ".summary.json"))]
    assert len(saved) == 6
    assert all(json.loads(p.read_text(encoding="utf-8"))["status"] == "QUALITY_FAIL"
               for p in saved)


def test_incomplete_chalk_stops_without_clear(tmp_path):
    m = manifest()
    state, observe, run, clear = fake_callbacks()
    def invalid_run(task):
        payload = run(task)
        payload["actual_chalk"] = 99
        return payload
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path,
        observe_blank=observe, run_one=invalid_run, clear_and_verify=clear)
    assert report["status"] == "blocked"
    assert report["accepted"] == 0
    assert report["quality_failed"] == 0
    assert state["clears"] == 0


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

def test_missing_blank_screen_proof_never_advances(tmp_path):
    m = manifest()
    state, observe, run, clear = fake_callbacks()
    def unsafe_clear(task):
        payload = clear(task)
        payload.pop("blank_screen_verification")
        return payload
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path, observe_blank=observe,
        run_one=run, clear_and_verify=unsafe_clear)
    assert report["status"] == "blocked"
    assert report["accepted"] == 1
    assert state["n"] == 1
    path = next(tmp_path.glob("*.clear.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "BLOCKED"

def test_previous_clear_evidence_prevents_any_new_game_action(tmp_path):
    m = manifest()
    stale = tmp_path / (m["tasks"][0]["task_id"] + ".clear.json")
    stale.write_text("old clear evidence", encoding="utf-8")
    state, observe, run, clear = fake_callbacks()
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path, observe_blank=observe,
        run_one=run, clear_and_verify=clear)
    assert report["status"] == "blocked"
    assert state == {"n": 0, "clears": 0}
    assert stale.read_text(encoding="utf-8") == "old clear evidence"


def test_immutable_summary_blocks_repeat_before_callbacks(tmp_path):
    m = manifest()
    summary = tmp_path / "series-test.summary.json"
    summary.write_text("original summary", encoding="utf-8")
    state, observe, run, clear = fake_callbacks()
    with pytest.raises(SeriesBlocked, match="summary"):
        run_with_validated_callbacks(
            m, results_dir=tmp_path, observe_blank=observe,
            run_one=run, clear_and_verify=clear)
    assert state == {"n": 0, "clears": 0}
    assert summary.read_text(encoding="utf-8") == "original summary"


@pytest.mark.parametrize("stale", [False, True])
def test_same_bridge_session_allowed_after_verified_clear(tmp_path, stale):
    m = manifest(cycles=1, figures_per_cycle=3)
    state = {"n": 0, "clears": 0, "proof": None}
    def observe(task):
        state["n"] += 1
        x = {"valid": True, "fresh_board": True,
             "pointCount": 1, "calibration_valid": True,
             "session_id": "persistent-session",
             "mapping_sha256": "a"*64,
             "observed_at_utc": f"2026-11-11T00:00:{(state['n'] - 1)*10 + 2:02d}+00:00"}
        if state["proof"] is not None:
            x["blank_screen_verification"] = state["proof"]
            if stale:
                x["observed_at_utc"] = "2026-11-11T00:00:00+00:00"
        return x
    def run(task):
        return {
            "task_id": task["task_id"], "session_id": "persistent-session",
            "run_id": "run-" + str(state["n"]),
            "execution_status": "completed", "monitor_binding": "EXACT_RUN_BOUND",
            "quality_gate": "PASS", "mouse_release_succeeded": True,
            "pre_pointCount": 1, "post_pointCount": 101, "actual_chalk": 100,
            "before_png_sha256": "a"*64, "after_settled_png_sha256": "b"*64,
        }
    def clear(task):
        state["clears"] += 1
        proof = {
            "schema": "FILL001_SERIES_BLANK_SCREEN_VERIFICATION_V1",
            "status": "PASS", "session_id": "persistent-session",
            "post_clear_pointCount": 1, "changed_screen_pixels": 0,
            "reference_png_sha256": "a"*64,
            "post_clear_png_sha256": "b"*64,
            "clear_ui_action_proven": False,
            "mapping_sha256": "a"*64,
            "last_settled_at_utc": f"2026-11-11T00:00:{(state['n'] - 1)*10 + 11:02d}+00:00",
        }
        state["proof"] = proof
        return {"valid": True, "pointCount": 1, "mouse_released": True,
                "fresh_board": True, "blank_screen_verification": proof}
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path, observe_blank=observe,
        run_one=run, clear_and_verify=clear)
    if stale:
        assert report["status"] == "blocked"
        assert report["accepted"] == 1
        assert state["clears"] == 1
        assert state["n"] == 2
    else:
        assert report["status"] == "completed"
        assert report["accepted"] == 3
        assert state["clears"] == 2


def test_same_session_without_clear_provenance_stops_before_second_draw(tmp_path):
    m = manifest(cycles=1, figures_per_cycle=3)
    state, _, run, clear = fake_callbacks()
    def observe(task):
        state["n"] += 1
        return {"valid": True, "fresh_board": True, "pointCount": 1,
                "calibration_valid": True, "session_id": "reused"}
    def run_reused(task):
        result = run(task)
        result["session_id"] = "reused"
        return result
    def clear_reused(task):
        result = clear(task)
        result["blank_screen_verification"]["session_id"] = "reused"
        return result
    result = run_with_validated_callbacks(
        m, results_dir=tmp_path, observe_blank=observe,
        run_one=run_reused, clear_and_verify=clear_reused)
    assert result["status"] == "blocked"
    assert result["accepted"] == 1
    assert state["n"] == 2


def test_recycled_bridge_run_id_blocked_even_in_distinct_sessions(tmp_path):
    m = manifest(cycles=1, figures_per_cycle=3)
    state, observe, run, clear = fake_callbacks()
    def reused_run(task):
        value = run(task)
        value["run_id"] = "recycled"
        return value
    report = run_with_validated_callbacks(
        m, results_dir=tmp_path, observe_blank=observe,
        run_one=reused_run, clear_and_verify=clear)
    assert report["status"] == "blocked"
    assert report["accepted"] == 1
    assert state["n"] == 2


def test_engine001_existing_clear_proof_is_accepted_without_zero_pixel_rule():
    from fill001_series_runner import _clear_proof_valid
    proof = {
        "schema": "FILL001_SERIES_ENGINE001_CLEAR_REUSE_V1",
        "status": "PASS", "session_id": "session-1",
        "mapping_sha256": "a"*64,
        "post_clear_pointCount": 1,
        "reference_png_sha256": "b"*64,
        "post_clear_png_sha256": "c"*64,
        "last_settled_at_utc": "2026-11-11T00:00:11+00:00",
        "engine001_visual_status": "restored_within_pixel_tolerance",
        "engine001_tolerance_percent": 0.15,
        "engine001_changed_percent": 0.06,
        "clear_ui_action_proven": True,
        "screen_evidence_status": "ENGINE001_EXISTING_COMPARATOR_PASS",
    }
    assert _clear_proof_valid(proof, "session-1") is True
    proof["engine001_changed_percent"] = 0.16
    assert _clear_proof_valid(proof, "session-1") is False
    proof["engine001_changed_percent"] = 0.06
    proof["engine001_tolerance_percent"] = 0.2
    assert _clear_proof_valid(proof, "session-1") is False
    proof["engine001_tolerance_percent"] = 0.15
    proof["session_id"] = "foreign"
    assert _clear_proof_valid(proof, "session-1") is False


def test_shared_owner_lock_blocks_parallel_auto_draw_process(tmp_path):
    from chalk_test_blocks import (
        acquire_chalk_block_owner_lock, release_chalk_block_owner_lock,
    )
    from fill001_series_runner import run_with_series_owner_lock
    m = manifest(cycles=1, figures_per_cycle=1)
    parent = tmp_path / "series"
    parent.mkdir()
    held = acquire_chalk_block_owner_lock(parent / "series-owner.json")
    assert held is not None
    state, observe, run, clear = fake_callbacks()
    try:
        with pytest.raises(SeriesBlocked, match="game-control lock"):
            run_with_series_owner_lock(
                m, results_dir=parent / "run-a",
                observe_blank=observe, run_one=run,
                clear_and_verify=clear,
            )
        assert state == {"n": 0, "clears": 0}
    finally:
        release_chalk_block_owner_lock(held)


def test_series_owner_lock_released_after_success(tmp_path):
    from fill001_series_runner import run_with_series_owner_lock
    m = manifest(cycles=1, figures_per_cycle=1)
    state, observe, run, clear = fake_callbacks()
    folder = tmp_path / "series" / "run"
    result = run_with_series_owner_lock(
        m, results_dir=folder,
        observe_blank=observe, run_one=run, clear_and_verify=clear,
    )
    assert result["status"] == "completed"
    assert result["accepted"] == 1
    assert state == {"n": 1, "clears": 0}
    state2, observe2, run2, clear2 = fake_callbacks()
    m2 = build_manifest(
        cycles=1, figures_per_cycle=1, shapes=["rectangle"],
        methods=["dense_scanlines"], radii=[10], series_id="different-series",
    )
    next_result = run_with_series_owner_lock(
        m2, results_dir=tmp_path / "series" / "other",
        observe_blank=observe2, run_one=run2, clear_and_verify=clear2,
    )
    assert next_result["accepted"] == 1
