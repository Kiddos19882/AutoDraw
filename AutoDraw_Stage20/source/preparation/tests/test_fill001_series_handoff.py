"""Experimental single-task FILL-001 series handoff regression; no Stage6 input."""
from copy import deepcopy
import json

import pytest

from fill001_series_runner import SeriesBlocked, build_manifest
from fill001_series_handoff import (
    build_series_source_plan, validate_series_source_plan, export_series_source_plan,
)


def manifest():
    return build_manifest(
        cycles=3, figures_per_cycle=10,
        shapes=["rectangle", "wide_irregular", "narrow_irregular"],
        methods=["dense_scanlines", "spaced_scanlines"],
        radii=[1, 5, 10, 20, 30], series_id="source-all-30",
    )


def test_full_factorial_source_identity_and_nonexecutability():
    m = manifest()
    signatures = {}
    for task in m["tasks"]:
        source = build_series_source_plan(m, task["task_id"])
        meta = validate_series_source_plan(m, source)
        assert meta["task_id"] == task["task_id"]
        assert meta["automatic_execution_allowed"] is False
        assert meta["requires_fresh_single_run_preflight"] is True
        assert meta["actual_chalk"] is None
        assert source["summary"]["estimated_sampling_points_are_exact_chalk"] is False
        assert len(source["strokes"]) == source["summary"]["stroke_count"]
        assert all(x["metadata"]["brush_value"] == str(task["brush_radius"])
                   for x in source["strokes"])
        signatures[task["task_id"]] = meta["source_strokes_sha256"]
    assert len(signatures) == 30


@pytest.mark.parametrize("mutate", [
    lambda x: x["generation"].update(automatic_execution_allowed=True),
    lambda x: x["strokes"][0]["points"][0].update(x=99999),
    lambda x: x["strokes"][0]["metadata"].update(brush_value="30"),
    lambda x: x["generation"].update(shape_id="wide_irregular"),
    lambda x: x["generation"].update(source_strokes_sha256="wrong"),
    lambda x: x["summary"].update(estimated_sampling_points_are_exact_chalk=True),
])
def test_tampered_plan_rejected(mutate):
    m = manifest()
    plan = build_series_source_plan(m, m["tasks"][0]["task_id"])
    mutate(plan)
    with pytest.raises(SeriesBlocked):
        validate_series_source_plan(m, plan)


def test_export_refuses_to_overwrite(tmp_path):
    m = manifest()
    path = tmp_path / "drawing-plan.json"
    export_series_source_plan(m, m["tasks"][0]["task_id"], path)
    assert json.loads(path.read_text(encoding="utf-8")) == build_series_source_plan(
        m, m["tasks"][0]["task_id"])
    with pytest.raises(FileExistsError):
        export_series_source_plan(m, m["tasks"][0]["task_id"], path)
