"""Exact V5 CHALK binding tests; all data synthetic and no game input."""
from copy import deepcopy

import pytest

from fill001_v5_finalization import validate_v5_bridge_runs
from fill001_v5_handoff import Fill001V5Error

SID="e4-fresh-v5-session"
CANDIDATE="K_trim_0_y190_w2"


def make_run(n=29, radius=None, pre=1, post=1290, run_id="run-a"):
    if radius is None:
        radius=[10,2]
    return {
        "schema_version":1,
        "record_type":"autodraw_game_monitor_run",
        "session_id":SID, "run_id":run_id,
        "started_at_utc":"2026-11-10T09:00:00+00:00",
        "finished_at_utc":"2026-11-10T09:00:10+00:00",
        "execution_status":"completed",
        "monitor_dropped_events":0, "monitor_error_count":0,
        "collector_sequence_gap_count":0,"bridge_send_failures_delta":0,
        "non_consuming_stroke_candidate_count":0,
        "point_delta_matches_chalk":True,"monitor_errors":[],
        "stroke_count":n,"stroke_candidate_count":n,
        "pre_test_snapshot":{"isExact":True,"pointCount":pre,
                             "maxPoints":6000,"remainingPoints":6000-pre},
        "post_test_snapshot":{"isExact":True,"pointCount":post,
                              "maxPoints":6000,"remainingPoints":6000-post},
        "chalk":{"status":"exact","consumed_points":post-pre,
                 "pre_point_count":pre,"post_point_count":post,
                 "max_points":6000},
        "observed_brush_radii":radius,
        "events":[{"monitorVersion":"0.2.4","type":"DRAW_SAMPLE"}],
        "event_count":1,
    }


def test_single_run_exact_chalk_and_both_radii():
    result=validate_v5_bridge_runs(
        [make_run()],session_id=SID,candidate_id=CANDIDATE,
    )
    assert result["exact_chalk"]==1289
    assert result["stroke_count"]==29
    assert result["run_ids"]==["run-a"]
    assert result["observed_brush_radii"]==[2,10]


def test_split_v5_strokes_requires_contiguous_exact_counters():
    first=make_run(28,[10],1,1289,"run-a")
    second=make_run(1,[2],1289,1290,"run-b")
    second["started_at_utc"]="2026-11-10T09:00:20+00:00"
    result=validate_v5_bridge_runs(
        [second,first],session_id=SID,candidate_id=CANDIDATE,
    )
    assert result["bridge_run_stroke_counts"]==[28,1]
    assert result["exact_chalk"]==1289


@pytest.mark.parametrize("edit,expected",[
    (lambda r:r.update(session_id="other"),"session"),
    (lambda r:r.update(stroke_count=28),"stroke"),
    (lambda r:r.update(monitor_dropped_events=1),"dropped"),
    (lambda r:r.update(point_delta_matches_chalk=False),"dropped"),
    (lambda r:r["chalk"].update(consumed_points=42),"CHALK"),
    (lambda r:r["pre_test_snapshot"].update(pointCount=2),"counters"),
    (lambda r:r.update(observed_brush_radii=[30]),"radii"),
    (lambda r:r["events"][0].update(monitorVersion="0.2.3"),"Monitor"),
])
def test_fail_closed_when_any_run_binding_property_breaks(edit,expected):
    run=make_run()
    edit(run)
    with pytest.raises(Fill001V5Error,match=expected):
        validate_v5_bridge_runs(
            [run],session_id=SID,candidate_id=CANDIDATE,
        )


def test_no_run_and_wrong_candidate_never_give_chalk():
    with pytest.raises(Fill001V5Error,match="one or two"):
        validate_v5_bridge_runs([],session_id=SID,candidate_id=CANDIDATE)
    with pytest.raises(Fill001V5Error,match="Unknown"):
        validate_v5_bridge_runs(
            [make_run()],session_id=SID,candidate_id="unapproved",
        )
