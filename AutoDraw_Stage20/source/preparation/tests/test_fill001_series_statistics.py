"""Synthetic evidence tests for FILL001-SERIES-001 read-only analytics."""
import json
from pathlib import Path

import pytest

from fill001_series_runner import build_manifest
from fill001_series_statistics import analyze_series, write_analysis


def manifest():
    return build_manifest(
        cycles=1, figures_per_cycle=3,
        shapes=["rectangle", "wide_irregular", "narrow_irregular"],
        methods=["spaced_scanlines"], radii=[10],
        series_id="statistics-synthetic",
    )


def save_case(folder, m, index, status, chalk):
    task = m["tasks"][index]
    quality = "PASS" if status == "PASS" else "FAIL"
    runtime = {
        "session_id": f"session-{index}", "run_id": f"run-{index}",
        "task_id": task["task_id"], "monitor_binding": "EXACT_RUN_BOUND",
        "quality_gate": quality, "pre_pointCount": 1,
        "post_pointCount": 1 + chalk,
        "quality_metrics": {
            "coverage_fraction": 0.993 if quality == "PASS" else 0.97,
            "leakage_pixels": index, "leakage_pixels_beyond_allowed_halo": 0,
        },
        "stage6_summary": {"duration_seconds": 52.0 + index, "completed_strokes": 29},
        "monitor_summary": {"event_count": 1000 + index, "dropped_events": 0},
    }
    d = {
        "schema": "FILL001_SERIES_RUN_V1", "series_id": m["series_id"],
        "manifest_sha256": m["manifest_sha256"], "task_id": task["task_id"],
        "status": status, "quality_gate": quality, "actual_chalk": chalk,
        "runtime": runtime,
    }
    (folder / (task["task_id"] + ".json")).write_text(json.dumps(d), encoding="utf-8")


def test_grouped_chalk_and_metrics_keep_quality_fail_separate(tmp_path):
    m = manifest()
    save_case(tmp_path, m, 0, "PASS", 150)
    save_case(tmp_path, m, 1, "QUALITY_FAIL", 99)
    save_case(tmp_path, m, 2, "PASS", 120)
    analysis = analyze_series(m, tmp_path)
    assert analysis["status"] == "COMPLETE"
    assert (analysis["quality_pass"], analysis["quality_fail"]) == (2, 1)
    assert analysis["lowest_observed_quality_pass_chalk"]["exact_chalk"] == 120
    assert analysis["grouped_statistics"]["brush_radius"]["10"]["chalk_quality_pass"]["mean"] == 135
    assert analysis["grouped_statistics"]["brush_radius"]["10"]["chalk_quality_fail"]["mean"] == 99
    assert analysis["grouped_statistics"]["brush_radius"]["10"]["metrics_quality_pass"]["coverage_fraction"]["count"] == 2
    assert analysis["grouped_statistics"]["shape_id+fill_method+brush_radius"]["rectangle|spaced_scanlines|10"]["quality_pass"] == 1
    assert not analysis["production_eligible"]
    target = tmp_path / "analysis.json"
    write_analysis(m, tmp_path, target)
    with pytest.raises(FileExistsError):
        write_analysis(m, tmp_path, target)


def test_missing_is_partial_not_zero_chalk(tmp_path):
    m = manifest()
    save_case(tmp_path, m, 0, "PASS", 123)
    result = analyze_series(m, tmp_path)
    assert result["status"] == "PARTIAL"
    assert len(result["missing"]) == 2
    assert result["observed"] == 1


@pytest.mark.parametrize("tamper", [
    lambda d: d.update(actual_chalk=1),
    lambda d: d["runtime"].update(monitor_binding="NOT_EVALUATED"),
    lambda d: d.update(manifest_sha256="wrong"),
    lambda d: d["runtime"].update(quality_gate="FAIL"),
])
def test_invalid_evidence_cannot_enter_stats(tmp_path, tamper):
    m = manifest()
    save_case(tmp_path, m, 0, "PASS", 123)
    p = tmp_path / (m["tasks"][0]["task_id"] + ".json")
    x = json.loads(p.read_text(encoding="utf-8"))
    tamper(x)
    p.write_text(json.dumps(x), encoding="utf-8")
    result = analyze_series(m, tmp_path)
    assert result["status"] == "PARTIAL"
    assert len(result["rejected"]) == 1
    assert result["lowest_observed_quality_pass_chalk"] is None


def test_quota_limited_diagnostics_never_enter_quality_ranking(tmp_path):
    m=manifest()
    save_case(tmp_path,m,0,"QUALITY_FAIL",5758)
    p=tmp_path/(m["tasks"][0]["task_id"]+".json")
    data=json.loads(p.read_text(encoding="utf-8"))
    data.update(status="QUOTA_LIMITED",quality_gate="NOT_EVALUATED")
    data["runtime"].update(
        execution_status="quota_limited",quality_gate="NOT_EVALUATED",
        post_pointCount=5759,
        quota_stop={"reason":"EXACT_REMAINING_BELOW_SAFETY_MARGIN",
                    "safety_margin_points":300,"remainingPoints":241,
                    "pointCount":5759,"maxPoints":6000,
                    "completed_strokes":100,"planned_strokes":141},
    )
    p.write_text(json.dumps(data),encoding="utf-8")
    report=analyze_series(m,tmp_path)
    assert report["quota_limited"]==1
    assert report["quality_pass"]==0
    assert report["quality_fail"]==0
    assert report["lowest_observed_quality_pass_chalk"] is None
    assert report["runs"][0]["exact_chalk"]==5758
    cell=report["grouped_statistics"]["shape_id"]["rectangle"]
    assert cell["chalk_quota_limited_diagnostic"]["mean"]==5758
    data["runtime"]["quota_stop"]["remainingPoints"]=301
    p.write_text(json.dumps(data),encoding="utf-8")
    bad=analyze_series(m,tmp_path)
    assert bad["rejected"] and bad["quota_limited"]==0
