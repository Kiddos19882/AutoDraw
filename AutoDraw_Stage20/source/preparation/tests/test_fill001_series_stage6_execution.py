"""Headless contract regression for generic Stage6 run report normalization."""
from copy import deepcopy

import pytest

from fill001_series_runner import SeriesBlocked
from fill001_series_stage6_execution import normalized_series_run


def example():
    task={"task_id":"series-figure-1"}
    result={
        "status":"completed",
        "request":{"task_id":"series-figure-1","session_id":"sid"},
        "monitor_binding":"EXACT_RUN_BOUND",
        "actual_chalk":1706,
        "game_png_quality":"PASS",
        "binding":{
            "status":"EXACT_RUN_BOUND","run_ids":["run-1"],
            "pre_pointCount":1,"post_pointCount":1707,
            "exact_chalk":1706,"monitor_event_count":8157,
            "excluded_zero_point_slider_drags":4,
        },
        "stage6_summary":{
            "status":"completed","completed_strokes":29,
            "duration_seconds":72.734,"mouse_release":{"succeeded":True}
        },
        "png_audit":{
            "coverage_fraction":0.99377,"leakage_pixels":600,
            "active_quality_metrics":{
                "leakage_pixels_beyond_allowed_halo":0,
                "max_perimeter_overshoot_logical_px":1.327,
            },
        },
        "before_png":{"sha256":"a"*64},
        "after_settled_png":{"sha256":"b"*64},
    }
    return task,result


def test_exact_report_becomes_series_record():
    task,result=example()
    data=normalized_series_run(task,result)
    assert data["actual_chalk"]==1706
    assert data["monitor_binding"]=="EXACT_RUN_BOUND"
    assert data["quality_gate"]=="PASS"
    assert data["monitor_summary"]["event_count"]==8157
    assert data["quality_metrics"]["coverage_fraction"]==0.99377


def test_valid_complete_quality_fail_keeps_exact_chalk():
    task,result=example()
    result["game_png_quality"]="FAIL"
    assert normalized_series_run(task,result)["quality_gate"]=="FAIL"


@pytest.mark.parametrize("mutate",[
    lambda r:r.update(monitor_binding="NOT_EVALUATED"),
    lambda r:r.update(game_png_quality="NOT_EVALUATED"),
    lambda r:r.update(status="BLOCKED"),
    lambda r:r["stage6_summary"]["mouse_release"].update(succeeded=False),
    lambda r:r.update(actual_chalk=1),
    lambda r:r["binding"].update(status="UNKNOWN"),
    lambda r:r["binding"].update(run_ids=[]),
    lambda r:r.update(after_settled_png=None),
    lambda r:r["request"].update(task_id="other"),
])
def test_incomplete_execution_refuses_series_acceptance(mutate):
    task,result=example()
    mutate(result)
    with pytest.raises(SeriesBlocked):
        normalized_series_run(task,result)


def test_quota_limited_stage6_is_diagnostic_not_quality_pass():
    from fill001_series_stage6_execution import QUOTA_GUARD_ERROR
    task,result=example()
    result.update(
        status="QUOTA_LIMITED",game_png_quality="NOT_EVALUATED",actual_chalk=5758,
        quota_stop={"reason":"EXACT_REMAINING_BELOW_SAFETY_MARGIN",
                    "safety_margin_points":300,"remainingPoints":241,
                    "pointCount":5759,"maxPoints":6000,
                    "completed_strokes":100,"planned_strokes":141})
    result["binding"].update(pre_pointCount=1,post_pointCount=5759,
                             exact_chalk=5758,maxPoints=6000,stroke_count=100)
    result["stage6_summary"].update(
        status="failed",completed_strokes=100,total_strokes=141,
        error=QUOTA_GUARD_ERROR)
    normalized=normalized_series_run(task,result)
    assert normalized["execution_status"]=="quota_limited"
    assert normalized["quality_gate"]=="NOT_EVALUATED"
    assert normalized["actual_chalk"]==5758
    assert normalized["stage6_summary"]["completed_strokes"]==100


@pytest.mark.parametrize("damage",[
    lambda r:r["quota_stop"].update(remainingPoints=300),
    lambda r:r["quota_stop"].update(pointCount=5758),
    lambda r:r["quota_stop"].update(completed_strokes=141),
    lambda r:r["stage6_summary"].update(error="Other failure"),
    lambda r:r["stage6_summary"]["mouse_release"].update(succeeded=False),
    lambda r:r.update(after_settled_png=None),
    lambda r:r["binding"].update(stroke_count=99),
    lambda r:r.update(monitor_binding="NOT_EVALUATED"),
])
def test_invalid_quota_evidence_must_block(damage):
    from fill001_series_stage6_execution import QUOTA_GUARD_ERROR
    task,result=example()
    result.update(
        status="QUOTA_LIMITED",game_png_quality="NOT_EVALUATED",actual_chalk=5758,
        quota_stop={"reason":"EXACT_REMAINING_BELOW_SAFETY_MARGIN",
                    "safety_margin_points":300,"remainingPoints":241,
                    "pointCount":5759,"maxPoints":6000,
                    "completed_strokes":100,"planned_strokes":141})
    result["binding"].update(pre_pointCount=1,post_pointCount=5759,
                             exact_chalk=5758,maxPoints=6000,stroke_count=100)
    result["stage6_summary"].update(
        status="failed",completed_strokes=100,total_strokes=141,
        error=QUOTA_GUARD_ERROR)
    damage(result)
    with pytest.raises(SeriesBlocked):
        normalized_series_run(task,result)
