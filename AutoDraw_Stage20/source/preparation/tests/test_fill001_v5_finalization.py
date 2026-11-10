"""Exact V5 CHALK binding tests; all data synthetic and no game input."""
from copy import deepcopy
import json

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


def test_v5_phone_touch_cannot_be_accepted_as_planned_mouse_down():
    run = make_run()
    starts = [(100.0+i, 200.0+i) for i in range(29)]
    run["events"] = [
        {"monitorVersion": "0.2.4", "type": "POINTER_DOWN_CANDIDATE",
         "clientX": x, "clientY": y}
        for x, y in starts
    ]
    run["event_count"] = 29
    accepted = validate_v5_bridge_runs(
        [run], session_id=SID, candidate_id=CANDIDATE,
        expected_pointer_down_client=starts,
    )
    assert accepted["exact_chalk"] == 1289
    corrupted = deepcopy(run)
    corrupted["events"][4]["clientX"] += 17
    with pytest.raises(Fill001V5Error, match="differs from frozen planned"):
        validate_v5_bridge_runs(
            [corrupted], session_id=SID, candidate_id=CANDIDATE,
            expected_pointer_down_client=starts,
        )
    extra = deepcopy(run)
    extra["events"].append({
        "monitorVersion": "0.2.4", "type": "POINTER_DOWN_CANDIDATE",
        "clientX": 999, "clientY": 999,
    })
    extra["event_count"] = 30
    with pytest.raises(Fill001V5Error, match="29 planned pointer-down"):
        validate_v5_bridge_runs(
            [extra], session_id=SID, candidate_id=CANDIDATE,
            expected_pointer_down_client=starts,
        )


def test_finalizer_refuses_absent_raw_pointer_binding_even_with_completed_summary(tmp_path):
    from fill001_v5_finalization import finalize_v5_stage6_attempt
    (tmp_path / "before.png").write_bytes(b"png")
    (tmp_path / "after.png").write_bytes(b"png")
    (tmp_path / SID).mkdir()
    with pytest.raises(Fill001V5Error, match="29 independent planned"):
        finalize_v5_stage6_attempt(
            bridge_root=tmp_path, request={
                "session_id": SID, "candidate_id": CANDIDATE,
            }, baseline_files=set(),
            summary={"status": "completed", "completed_strokes": 29},
            pre_png=tmp_path / "before.png", post_png=tmp_path / "after.png",
            timeout_seconds=0,
        )


def _real_shaped_slider_and_29_strokes():
    """Reduced immutable-shape fixture for ed74ffd: 29 paint + 5 zero-point drags."""
    planned=[(625.0,193.0),(625.0,191.0)]+[
        (596.0,float(199+6*i)) for i in range(26)
    ]+[(630.0,395.0)]
    # Use 29 unique ordered starts; no acceptance is based on estimated CHALK.
    assert len(planned)==29
    controls=[(1207,171,30),(1315,171,8),(1305,171,10),
              (1358,171,1),(1353,171,1)]
    events=[]
    metrics=[]
    def append(x,y,radius,consumed):
        number=len(metrics)+1
        sid=f"pointer-stroke-{number}"
        events.append({
            "monitorVersion":"0.2.4","type":"POINTER_DOWN_CANDIDATE",
            "strokeId":sid,"clientX":x,"clientY":y,
            "board":{"currentRadius":radius},
        })
        metrics.append({
            "stroke_id":sid,"lifecycle_status":"complete",
            "point_count_delta":consumed,
            "point_update_event_count":consumed,
            "point_count_delta_matches_updates": True if consumed else None,
        })
    for x,y,r in controls[:2]:
        append(x,y,r,0)
    for x,y in planned[:28]:
        append(x,y,10,1)
    for x,y,r in controls[2:]:
        append(x,y,r,0)
    append(*planned[28],2,1)
    run=make_run(29,[1,2,8,10,30],pre=1,post=1707)
    run["events"]=events
    run["event_count"]=len(events)
    run["per_stroke_metrics"]=metrics
    run["stroke_candidate_count"]=34
    run["non_consuming_stroke_candidate_count"]=5
    rect={"left":483.45,"top":108.22,"right":1176.70,"bottom":470.62}
    slider={"left":1203.0,"top":167.0,"right":1367.0,"bottom":175.0}
    return run,planned,rect,slider


def test_real_29_stroke_monitor_run_excludes_only_five_slider_drags():
    run,planned,rect,slider=_real_shaped_slider_and_29_strokes()
    result=validate_v5_bridge_runs(
        [run],session_id=SID,candidate_id=CANDIDATE,
        expected_pointer_down_client=planned,
        expected_board_client_rect=rect,slider_client_corridor=slider,
    )
    assert result["exact_chalk"]==1706
    assert result["excluded_zero_point_slider_drags"]==5
    assert result["stroke_count"]==29
    assert result["observed_brush_radii"]==[10,2]


@pytest.mark.parametrize("tamper,message",[
    ("phone_click","Unexpected off-plan"),
    ("slider_point_consumed","Unexpected off-plan"),
    ("slider_outside_track","Unexpected off-plan"),
    ("wrong_paint_radius","drawing radius"),
    ("missing_metric","Missing complete"),
    ("wrong_stroke_id","stroke lifecycle"),
    ("point_delta_unmatched","matched exact"),
    ("unverified_corridor","overlaps game board"),
])
def test_real_shaped_v5_binding_stays_fail_closed(tamper,message):
    run,planned,rect,slider=_real_shaped_slider_and_29_strokes()
    if tamper=="phone_click":
        run["events"][2]["clientX"]+=18
    elif tamper=="slider_point_consumed":
        run["per_stroke_metrics"][0]["point_count_delta"]=1
    elif tamper=="slider_outside_track":
        run["events"][0]["clientX"]=1190
    elif tamper=="wrong_paint_radius":
        run["events"][2]["board"]["currentRadius"]=30
    elif tamper=="missing_metric":
        run["per_stroke_metrics"].pop()
    elif tamper=="wrong_stroke_id":
        run["per_stroke_metrics"][2]["stroke_id"]="other"
    elif tamper=="point_delta_unmatched":
        run["per_stroke_metrics"][2]["point_count_delta_matches_updates"]=False
    elif tamper=="unverified_corridor":
        slider["left"]=500
        slider["right"]=800
        slider["top"]=110
        slider["bottom"]=470
    with pytest.raises(Fill001V5Error,match=message):
        validate_v5_bridge_runs(
            [run],session_id=SID,candidate_id=CANDIDATE,
            expected_pointer_down_client=planned,
            expected_board_client_rect=rect,slider_client_corridor=slider,
        )


def test_slider_exclusion_never_allowed_without_verifiable_bounds():
    run,planned,rect,slider=_real_shaped_slider_and_29_strokes()
    with pytest.raises(Fill001V5Error,match="both verified"):
        validate_v5_bridge_runs(
            [run],session_id=SID,candidate_id=CANDIDATE,
            expected_pointer_down_client=planned,
            expected_board_client_rect=rect,
        )
    with pytest.raises(Fill001V5Error,match="dropped/invalid"):
        validate_v5_bridge_runs(
            [run],session_id=SID,candidate_id=CANDIDATE,
            expected_pointer_down_client=planned,
        )


def test_exact_bound_chalk_survives_independent_png_capture_failure(tmp_path):
    from fill001_v5_finalization import finalize_v5_stage6_attempt
    run,planned,rect,slider=_real_shaped_slider_and_29_strokes()
    folder=tmp_path / SID
    folder.mkdir()
    (folder/"game-monitor-run-verified.json").write_text(json.dumps(run), encoding="utf-8")
    first=tmp_path/"before.png"
    last=tmp_path/"after.png"
    first.write_bytes(b"unchanged-before-placeholder")
    last.write_bytes(b"unchanged-post-placeholder")
    def fail_capture(exact_post):
        assert exact_post == 1707
        raise OSError("simulated missing settled PNG")
    result=finalize_v5_stage6_attempt(
        bridge_root=tmp_path,
        request={
            "session_id":SID,"candidate_id":CANDIDATE,
            "attempt_id":"synthetic-one-run",
            "expected_pointer_down_client":planned,
            "board_client_rect":rect,
            "slider_client_corridor":slider,
        },
        baseline_files=set(),
        summary={"status":"completed","completed_strokes":29},
        pre_png=first,post_png=last,
        post_capture_callback=fail_capture,
        timeout_seconds=0.1,
    )
    assert result["binding"]["exact_chalk"]==1706
    assert result["binding"]["excluded_zero_point_slider_drags"]==5
    assert result["quality_gate"]=="NOT_EVALUATED"
    assert result["status"]=="EXACT_RUN_BOUND_PNG_AUDIT_BLOCKED"
    assert "simulated missing settled PNG" in result["quality_error"]
    assert first.read_bytes()==b"unchanged-before-placeholder"
