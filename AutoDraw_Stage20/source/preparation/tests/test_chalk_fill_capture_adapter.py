from __future__ import annotations

import numpy as np
from PIL import Image
import pytest

from chalk_fill_capture_adapter import (
    FILL001_SAMPLING_PROFILE,
    audit_fill001_png_pair,
    build_fill001_capture,
)
from chalk_fill_experiment import build_fill_target_mask
from chalk_fill_matrix import FillMatrixError, build_fill001_matrix


def _snapshot(count):
    return {"isExact": True, "pointCount": count, "currentRadius": 5}


def _monitor_export(task):
    events = [
        {"t": 0, "type": "BRUSH_CHANGE_APPLIED", "strokeId": None,
         "after": {"currentRadius": task["requested_radius"]}},
    ]
    point_count = 100
    for index in range(task["expected_strokes"]):
        stroke_id = f"stroke-{index + 1}"
        events.extend([
            {"t": index * 10 + 1, "type": "DRAW_START", "strokeId": stroke_id,
             "before": _snapshot(point_count)},
            {"t": index * 10 + 2, "type": "DRAW_START_APPLIED", "strokeId": stroke_id,
             "after": _snapshot(point_count + 1)},
            {"t": index * 10 + 3, "type": "DRAW_SAMPLE", "strokeId": stroke_id,
             "pointDelta": 4, "after": _snapshot(point_count + 5)},
            {"t": index * 10 + 4, "type": "DRAW_END", "strokeId": stroke_id,
             "before": _snapshot(point_count + 5), "after": _snapshot(point_count + 5)},
        ])
        point_count += 5
    return {
        "schemaVersion": 1,
        "monitorVersion": "test-monitor",
        "eventCount": len(events),
        "droppedEvents": 0,
        "errors": [],
        "events": events,
    }


def _png_pair(tmp_path, shape_id):
    mask = build_fill_target_mask(shape_id)
    before = np.zeros((240, 460, 3), dtype=np.uint8)
    after = before.copy()
    after[mask] = 255
    before_path = tmp_path / "before.png"
    after_path = tmp_path / "after.png"
    Image.fromarray(before).save(before_path)
    Image.fromarray(after).save(after_path)
    return before_path, after_path


def test_png_audit_checks_real_files_hash_coverage_and_leakage(tmp_path):
    matrix = build_fill001_matrix("ADAPTER-TEST")
    task = matrix["tasks"][0]
    before, after = _png_pair(tmp_path, task["shape_id"])
    result = audit_fill001_png_pair(task["shape_id"], before, after)
    assert result["png_audit_status"] == "passed"
    assert result["coverage_fraction"] == 1.0
    assert result["leakage_pixels"] == 0
    assert len(result["before_png_sha256"]) == 64
    assert len(result["after_png_sha256"]) == 64


def test_monitor_adapter_builds_exact_capture_from_real_event_schema(tmp_path):
    matrix = build_fill001_matrix("ADAPTER-TEST")
    task = matrix["tasks"][0]
    before, after = _png_pair(tmp_path, task["shape_id"])
    capture = build_fill001_capture(
        task,
        _monitor_export(task),
        sampling_profile=FILL001_SAMPLING_PROFILE,
        before_png=before,
        after_png=after,
        run_id="live-run-001",
        bridge_diagnostics={"run_id": "live-run-001", "event_count": len(_monitor_export(task)["events"]), "bridge_failures": 0, "sequence_gaps": 0},
    )
    assert capture["exact_chalk"] == task["expected_strokes"] * 5
    assert sum(capture["stroke_chalk_deltas"]) == capture["exact_chalk"]
    assert capture["coverage_fraction"] == 1.0
    assert capture["png_audit_status"] == "passed"


def test_monitor_adapter_rejects_truncated_or_untrusted_evidence(tmp_path):
    matrix = build_fill001_matrix("ADAPTER-TEST")
    task = matrix["tasks"][0]
    before, after = _png_pair(tmp_path, task["shape_id"])
    export = _monitor_export(task)
    export["eventCount"] += 1
    with pytest.raises(FillMatrixError):
        build_fill001_capture(
            task, export, sampling_profile=FILL001_SAMPLING_PROFILE,
            before_png=before, after_png=after, run_id="live-run-002",
            bridge_diagnostics={"run_id": "live-run-002", "event_count": len(_monitor_export(task)["events"]), "bridge_failures": 0, "sequence_gaps": 0},
        )

    export = _monitor_export(task)
    with pytest.raises(FillMatrixError):
        build_fill001_capture(
            task, export, sampling_profile=FILL001_SAMPLING_PROFILE,
            before_png=before, after_png=after, run_id="live-run-003",
            bridge_diagnostics={"run_id": "live-run-003", "event_count": len(_monitor_export(task)["events"]), "bridge_failures": 1, "sequence_gaps": 0},
        )
