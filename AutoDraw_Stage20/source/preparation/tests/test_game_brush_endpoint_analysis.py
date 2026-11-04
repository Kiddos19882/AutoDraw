from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PREPARATION_SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PREPARATION_SOURCE))

from game_brush_endpoint_analysis import analyze_run


def _run(points, *, line_width=10, deltas=None):
    events = [
        {"type": "DRAW_SAMPLE", "pointDelta": value}
        for value in (deltas if deltas is not None else [1] * len(points))
    ]
    events.extend(
        {"type": "POINT_QUOTA_UPDATE"}
        for _ in range(sum(value for value in (deltas if deltas is not None else [1] * len(points)) if value > 0))
    )
    return {
        "run_id": "fixture",
        "brush_radius": line_width,
        "chalk": {"consumed_points": sum(value for value in (deltas if deltas is not None else [1] * len(points)) if value > 0)},
        "stroke_count": 1,
        "events": events,
        "accepted_points": [
            {"stroke_id": "stroke-1", "t": index, "x": point[0], "y": point[1]}
            for index, point in enumerate(points)
        ],
    }


def test_smooth_midpoint_endpoint_round_cap_reaches_last_sample_when_spacing_within_width():
    report = analyze_run(_run([(0, 0), (6, 0), (12, 0)]))
    stroke = report["per_stroke"][0]

    assert stroke["smooth_path_terminal_point"] == {"x": 9.0, "y": 0.0}
    assert stroke["last_accepted_segment_length"] == 6.0
    assert stroke["ideal_round_cap_covers_last_sample_center"] is True
    assert stroke["ideal_round_cap_margin_to_last_sample"] == 2.0


def test_smooth_midpoint_endpoint_reports_ideal_gap_when_spacing_exceeds_width():
    report = analyze_run(_run([(0, 0), (14, 0)]))
    stroke = report["per_stroke"][0]

    assert stroke["smooth_path_terminal_point"] == {"x": 7.0, "y": 0.0}
    assert stroke["ideal_round_cap_covers_last_sample_center"] is False
    assert stroke["ideal_geometric_gap_to_last_sample_center"] == 2.0


def test_single_point_stroke_has_no_terminal_segment_to_evaluate():
    report = analyze_run(_run([(5, 7)]))
    stroke = report["per_stroke"][0]

    assert stroke["smooth_path_terminal_point"] is None
    assert stroke["ideal_round_cap_covers_last_sample_center"] is None


def test_coordinate_completeness_requires_one_coordinate_per_accepted_delta():
    report = analyze_run(_run([(0, 0)], deltas=[2]))

    assert report["positive_draw_sample_point_delta_sum"] == 2
    assert report["accepted_point_coordinates_complete_for_observed_deltas"] is False


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, "not-a-number", None])
def test_invalid_coordinates_are_rejected(bad):
    run = _run([(0, 0)])
    run["accepted_points"][0]["x"] = bad

    with pytest.raises(ValueError):
        analyze_run(run)

def test_committed_fill001_capture_reproduces_endpoint_and_frame_cadence_metrics():
    project_root = Path(__file__).resolve().parents[3]
    raw_path = (
        project_root
        / "data"
        / "results"
        / "brush_behavior_tests"
        / "game_monitor_bridge"
        / "bb261898-8296-41f5-a333-eb0b81016410"
        / "game-monitor-run-20261104T040548835772Z-6a17a297.json"
    )
    run = json.loads(raw_path.read_text(encoding="utf-8"))
    report = analyze_run(run)

    assert report["run_id"] == "6a17a297-ea14-4527-9527-bfd8de3bd335"
    assert report["chalk_consumed_points"] == 1260
    assert report["stroke_count_in_run"] == 27
    assert report["accepted_point_coordinates_complete_for_observed_deltas"] is True

    segments = report["within_stroke_segment_lengths"]
    assert segments["count"] == 1233
    assert segments["median"] == 6
    assert segments["p95"] == 10
    assert segments["max"] == 13
    assert segments["over_line_width"] == 3

    final_segments = report["last_segment_per_stroke"]
    assert final_segments["count"] == 27
    assert final_segments["min"] == 3
    assert final_segments["max"] == 9
    assert report["ideal_round_cap_covers_last_accepted_sample_centers"] == 27

    timing = report["accepted_point_time_intervals_ms"]
    assert timing["count"] == 1233
    assert timing["median"] == 33
    assert timing["p90"] == 35
    assert timing["p95"] == 36
    assert timing["max"] == 81
    assert timing["over_40ms"] == 27
