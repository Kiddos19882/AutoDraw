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
