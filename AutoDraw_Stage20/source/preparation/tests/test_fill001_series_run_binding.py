"""Isolated synthetic exact CHALK binding for variable-length FILL001 series."""
from copy import deepcopy
import pytest

from fill001_series_run_binding import validate_series_bridge_runs, SeriesBindingBlocked


def sample_run():
    def down(sid,x,y,r):
        return {
            "type":"POINTER_DOWN_CANDIDATE", "strokeId":sid,
            "clientX":x, "clientY":y,
            "board":{"currentRadius":r}, "monitorVersion":"0.2.4"
        }
    down_events=[down("control",600,100,20),down("stroke-1",200,100,10),down("stroke-2",250,100,10)]
    metrics=[
        {"stroke_id":"control","lifecycle_status":"complete","point_count_delta":0,"point_update_event_count":0},
        {"stroke_id":"stroke-1","lifecycle_status":"complete","point_count_delta":40,"point_count_delta_matches_updates":True},
        {"stroke_id":"stroke-2","lifecycle_status":"complete","point_count_delta":60,"point_count_delta_matches_updates":True},
    ]
    return {
        "schema_version":1, "record_type":"autodraw_game_monitor_run",
        "session_id":"sid", "run_id":"run-1", "started_at_utc":"2026-11-11T01:00:00Z",
        "execution_status":"completed", "monitor_dropped_events":0,"monitor_error_count":0,
        "collector_sequence_gap_count":0, "bridge_send_failures_delta":0,
        "point_delta_matches_chalk":True, "monitor_errors":[],
        "pre_test_snapshot":{"isExact":True,"pointCount":1,"maxPoints":6000,"remainingPoints":5999},
        "post_test_snapshot":{"isExact":True,"pointCount":101,"maxPoints":6000,"remainingPoints":5899},
        "chalk":{"status":"exact","pre_point_count":1,"post_point_count":101,
                 "consumed_points":100,"max_points":6000},
        "event_count":3,"events":down_events,"per_stroke_metrics":metrics,
        "stroke_candidate_count":3,"stroke_count":2,
        "non_consuming_stroke_candidate_count":1,
    }


def run_gate(runs):
    return validate_series_bridge_runs(
        runs, session_id="sid", task_id="figure-1",
        expected_pointer_down_client=[(200,100),(250,100)],
        expected_brush_radii=[10,10],
        board_client_rect={"left":100,"right":400,"top":20,"bottom":260},
        slider_client_corridor={"left":550,"right":700,"top":80,"bottom":120},
    )


def test_full_generic_run_with_slider_exclusion():
    result=run_gate([sample_run()])
    assert result["status"] == "EXACT_RUN_BOUND"
    assert result["pre_pointCount"] == 1
    assert result["post_pointCount"] == 101
    assert result["exact_chalk"] == 100
    assert result["stroke_count"] == 2
    assert result["excluded_zero_point_slider_drags"] == 1
    assert result["png_quality"] == "NOT_EVALUATED"


@pytest.mark.parametrize("damage", [
    lambda r:r.update(monitor_dropped_events=1),
    lambda r:r["post_test_snapshot"].update(pointCount=100),
    lambda r:r["chalk"].update(consumed_points=101),
    lambda r:r["events"][1]["board"].update(currentRadius=30),
    lambda r:r["events"][1].update(clientX=300),
    lambda r:r["per_stroke_metrics"][1].update(point_count_delta=0),
    lambda r:r["per_stroke_metrics"][0].update(point_count_delta=1),
    lambda r:r["events"][0].update(clientX=450),
    lambda r:r.update(stroke_count=3),
    lambda r:r.update(non_consuming_stroke_candidate_count=0),
    lambda r:r.update(event_count=2),
    lambda r:r.update(session_id="other"),
    lambda r:r.update(run_id=""),
])
def test_invalid_bridge_binding_always_rejected(damage):
    r=sample_run()
    damage(r)
    with pytest.raises(SeriesBindingBlocked):
        run_gate([r])


def test_cross_run_duplicate_identity_rejected():
    r=sample_run()
    with pytest.raises(SeriesBindingBlocked):
        run_gate([r,deepcopy(r)])


def test_wrong_or_ambiguous_slider_corridor_rejected():
    r=sample_run()
    with pytest.raises(SeriesBindingBlocked):
        validate_series_bridge_runs(
            [r],session_id="sid",task_id="figure-1",
            expected_pointer_down_client=[(200,100),(250,100)],
            expected_brush_radii=[10,10],
            board_client_rect={"left":100,"right":400,"top":20,"bottom":260},
            slider_client_corridor={"left":300,"right":700,"top":80,"bottom":120},
        )
