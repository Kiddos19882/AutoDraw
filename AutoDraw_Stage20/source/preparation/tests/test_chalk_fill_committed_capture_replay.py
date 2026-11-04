from __future__ import annotations

import json
from pathlib import Path
import shutil

import cv2
import numpy as np

import chalk_fill_ui
from chalk_fill_matrix import load_fill001_matrix
from chalk_fill_experiment import build_fill_target_mask


TASK_ID = "fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1"
SESSION_ID = "bb261898-8296-41f5-a333-eb0b81016410"


class _StatusVar:
    def __init__(self):
        self.value = ""

    def set(self, value):
        self.value = value


def test_real_committed_fill001_evidence_runs_through_capture_button(tmp_path, monkeypatch, capsys):
    """Replay the user's committed FILL-001 attempt through Fill001Tab.finalize_capture.

    This intentionally uses the actual manifest, attempt, executor report, Bridge
    session/run JSON and before/after PNGs committed with the 2026-11-04 preflight.
    Only absolute machine-local paths are relocated into tmp_path; evidence bytes
    and all validation criteria remain unchanged.
    """
    repo_root = Path(__file__).resolve().parents[3]
    results_root = repo_root / "data" / "results" / "brush_behavior_tests"
    manifest_source = results_root / "fill001_rs" / "fill001-rs-preflight-20261104-7.04.json"
    attempt_source = (
        results_root / "fill001" / "attempts" / f"{TASK_ID}.json"
    )
    report_source = (
        repo_root / "data" / "results" / "execution_20261104_070545_500355_cf845f.json"
    )
    source_plan = repo_root / "data" / "runtime" / "current_brush_behavior_test.json"
    before_source = results_root / "fill001" / "captures" / f"{TASK_ID}-before.png"
    after_source = results_root / "fill001" / "captures" / f"{TASK_ID}-after.png"
    session_source = results_root / "game_monitor_bridge" / SESSION_ID
    legacy_session_id = "3323cf8e-01ca-4009-8f16-27d657d857f8"
    legacy_session_source = results_root / "game_monitor_bridge" / legacy_session_id / "session.json"

    required = (
        manifest_source,
        attempt_source,
        report_source,
        source_plan,
        before_source,
        after_source,
        session_source / "session.json",
        legacy_session_source,
        session_source / "game-monitor-run-20261104T040456791496Z-9ea6d0bb.json",
        session_source / "game-monitor-run-20261104T040548835772Z-6a17a297.json",
    )
    missing = [str(path) for path in required if not path.is_file()]
    assert not missing, "Committed live evidence bundle is incomplete: " + ", ".join(missing)

    sandbox_results = tmp_path / "results" / "brush_behavior_tests"
    output_dir = sandbox_results / "fill001"
    captures_dir = output_dir / "captures"
    captures_dir.mkdir(parents=True)
    bridge_root = sandbox_results / "game_monitor_bridge"
    bridge_root.mkdir(parents=True)
    session_destination = bridge_root / SESSION_ID
    shutil.copytree(session_source, session_destination)
    # This real pre-schema-2 session has no Bridge diagnostics and must not
    # block a later FILL-001 binding merely because its directory still exists.
    legacy_session_destination = bridge_root / legacy_session_id
    legacy_session_destination.mkdir()
    shutil.copy2(legacy_session_source, legacy_session_destination / "session.json")

    manifest_path = sandbox_results / "fill001_rs" / manifest_source.name
    manifest_path.parent.mkdir(parents=True)
    shutil.copy2(manifest_source, manifest_path)

    plan_destination = tmp_path / "runtime" / source_plan.name
    plan_destination.parent.mkdir(parents=True)
    shutil.copy2(source_plan, plan_destination)

    report_path = tmp_path / "execution.json"
    report = json.loads(report_source.read_text(encoding="utf-8"))
    report["source_plan_file"] = str(plan_destination)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    before_png = captures_dir / before_source.name
    after_png = captures_dir / after_source.name
    shutil.copy2(before_source, before_png)
    shutil.copy2(after_source, after_png)

    attempt_path = output_dir / "attempts" / attempt_source.name
    attempt_path.parent.mkdir(parents=True)
    attempt = json.loads(attempt_source.read_text(encoding="utf-8"))
    attempt["manifest_path"] = str(manifest_path)
    attempt["execution_report_path"] = str(report_path)
    attempt["before_png"] = str(before_png)
    attempt["after_png"] = str(after_png)
    attempt_path.write_text(json.dumps(attempt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    matrix = load_fill001_matrix(manifest_path)
    matching_tasks = [task for task in matrix["tasks"] if task.get("task_id") == TASK_ID]
    assert len(matching_tasks) == 1
    task = matching_tasks[0]
    assert task["expected_strokes"] == 27
    assert task["requested_radius"] == 10
    assert task["scanline_row_step"] == 5
    assert task["scanline_offset"] == 0

    import chalk_fill_capture_adapter

    ui_errors = []
    png_audit_result = {}
    original_png_audit = chalk_fill_capture_adapter.audit_fill001_png_pair

    def _record_png_audit(*args, **kwargs):
        result = original_png_audit(*args, **kwargs)
        png_audit_result.update(result)
        return result

    monkeypatch.setattr(
        chalk_fill_capture_adapter, "audit_fill001_png_pair", _record_png_audit
    )
    monkeypatch.setattr(
        chalk_fill_ui.messagebox,
        "showerror",
        lambda title, message, **_kwargs: ui_errors.append((title, message)),
    )
    monkeypatch.setattr(
        chalk_fill_ui.messagebox,
        "showwarning",
        lambda title, message, **_kwargs: ui_errors.append((title, message)),
    )

    tab = chalk_fill_ui.Fill001Tab.__new__(chalk_fill_ui.Fill001Tab)
    tab.root = None
    tab.output_dir = output_dir
    tab.matrix = matrix
    tab.manifest_path = manifest_path
    tab.active_task = task
    tab.active_run_record = attempt_path
    tab.active_plan_path = None
    tab.before_png_path = before_png
    tab.after_png_path = after_png
    tab.capture_region = dict(attempt["screen_roi"])
    tab.status_var = _StatusVar()
    tab._refresh_tasks = lambda: None

    tab.finalize_capture()

    assert len(ui_errors) == 1
    assert "PNG evidence не прошёл независимый audit." in ui_errors[0][1]
    assert png_audit_result["png_audit_status"] == "failed"
    assert (
        png_audit_result["coverage_fraction"] < 0.99
        or png_audit_result["leakage_pixels"] > 0
    )
    with capsys.disabled():
        print(
            "FILL-001 committed PNG audit: "
            f"coverage={png_audit_result['coverage_fraction']:.6%}, "
            f"leakage={png_audit_result['leakage_pixels']}, "
            f"status={png_audit_result['png_audit_status']}"
        )

        # Pixel-coordinate diagnosis on the immutable committed PNG pair.
        # This is test-only reporting: it does not alter the capture or gate.
        before_pixels, _ = chalk_fill_capture_adapter._png_pixels(before_png)
        after_pixels, _ = chalk_fill_capture_adapter._png_pixels(after_png)
        changed = np.any(
            np.abs(after_pixels.astype(np.int16) - before_pixels.astype(np.int16)) > 8,
            axis=2,
        )
        screen_height, screen_width = changed.shape
        scale_x = (screen_width - 1) / 460
        scale_y = (screen_height - 1) / 240
        logical_mask = build_fill_target_mask(task["shape_id"])
        logical_x = np.clip(
            np.rint(np.arange(screen_width, dtype=np.float64) / scale_x).astype(np.intp),
            0, 459,
        )
        logical_y = np.clip(
            np.rint(np.arange(screen_height, dtype=np.float64) / scale_y).astype(np.intp),
            0, 239,
        )
        screen_mask = logical_mask[np.ix_(logical_y, logical_x)]
        uncovered = screen_mask & ~changed
        leakage = ~screen_mask & changed
        yy, xx = np.indices(changed.shape)
        lx = logical_x[xx]
        ly = logical_y[yy]
        zones = {
            "top_y_lt_75": uncovered & (ly < 75),
            "bottom_y_gt_165": uncovered & (ly > 165),
            "left_middle_x_le_94": uncovered & (lx <= 94) & (ly >= 75) & (ly <= 165),
            "right_middle_x_ge_366": uncovered & (lx >= 366) & (ly >= 75) & (ly <= 165),
        }
        classified = np.zeros_like(uncovered)
        for zone_mask in zones.values():
            classified |= zone_mask
        zones["interior_or_other"] = uncovered & ~classified

        def _components(mask):
            count, labels, stats, _centroids = cv2.connectedComponentsWithStats(
                mask.astype(np.uint8), connectivity=8
            )
            components = [
                {
                    "area": int(stats[index, cv2.CC_STAT_AREA]),
                    "bbox_xywh": [
                        int(stats[index, cv2.CC_STAT_LEFT]),
                        int(stats[index, cv2.CC_STAT_TOP]),
                        int(stats[index, cv2.CC_STAT_WIDTH]),
                        int(stats[index, cv2.CC_STAT_HEIGHT]),
                    ],
                }
                for index in range(1, count)
            ]
            return sorted(components, key=lambda item: item["area"], reverse=True)

        plan_source = results_root / "fill001" / "plans" / f"{TASK_ID}.json"
        plan_data = json.loads(plan_source.read_text(encoding="utf-8"))
        transformed_segments = []
        for stroke in plan_data["strokes"]:
            p0, p1 = stroke["points"]
            x0, y0 = float(p0["x"]) * scale_x, float(p0["y"]) * scale_y
            x1, y1 = float(p1["x"]) * scale_x, float(p1["y"]) * scale_y
            transformed_segments.append((x0, y0, x1, y1))

        def _nearest_segment_distances(points):
            distances = []
            for py, px in points:
                best = float("inf")
                for x0, y0, x1, y1 in transformed_segments:
                    dx, dy = x1 - x0, y1 - y0
                    denom = dx * dx + dy * dy
                    t = 0.0 if denom == 0 else max(
                        0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / denom)
                    )
                    qx, qy = x0 + t * dx, y0 + t * dy
                    best = min(best, float(np.hypot(px - qx, py - qy)))
                distances.append(best)
            return distances

        uncovered_coords = [tuple(map(int, point)) for point in np.argwhere(uncovered)]
        leakage_coords = [tuple(map(int, point)) for point in np.argwhere(leakage)]
        distances = _nearest_segment_distances(uncovered_coords)
        distance_bands = {
            "le_2px": sum(value <= 2 for value in distances),
            "2_to_5px": sum(2 < value <= 5 for value in distances),
            "5_to_10px": sum(5 < value <= 10 for value in distances),
            "gt_10px": sum(value > 10 for value in distances),
        }
        print("FILL-001 actual PNG residual diagnostics: " + json.dumps({
            "screen_size": [screen_width, screen_height],
            "screen_scale": [scale_x, scale_y],
            "uncovered_target_pixels": int(np.count_nonzero(uncovered)),
            "uncovered_zones": {name: int(np.count_nonzero(mask)) for name, mask in zones.items()},
            "uncovered_bbox_xywh": (
                [int(np.min(np.where(uncovered)[1])), int(np.min(np.where(uncovered)[0])),
                 int(np.max(np.where(uncovered)[1]) - np.min(np.where(uncovered)[1]) + 1),
                 int(np.max(np.where(uncovered)[0]) - np.min(np.where(uncovered)[0]) + 1)]
                if uncovered_coords else None
            ),
            "uncovered_components_largest_20": _components(uncovered)[:20],
            "uncovered_nearest_scanline_distance_bands": distance_bands,
            "uncovered_rows": {
                str(int(row)): int(value)
                for row, value in enumerate(np.count_nonzero(uncovered, axis=1)) if value
            },
            "leakage_pixels": int(np.count_nonzero(leakage)),
            "leakage_coordinates_xy": [[x, y] for y, x in leakage_coords],
            "leakage_components": _components(leakage),
            "transformed_scanline_endpoints_xy": [
                [[x0, y0], [x1, y1]] for x0, y0, x1, y1 in transformed_segments
            ],
        }, ensure_ascii=False, sort_keys=True))

    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    saved_attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    saved_matrix = load_fill001_matrix(manifest_path)
    capture_path = captures_dir / f"{TASK_ID}-capture.json"

    # Runtime binding must succeed even in the presence of the stale legacy
    # session, while the independent PNG gate must continue to reject capture.
    assert saved_report["runtime_binding_status"] == "passed"
    assert saved_report["runtime_binding"]["run_id"] == "6a17a297-ea14-4527-9527-bfd8de3bd335"
    assert saved_report["runtime_binding"]["exact_chalk"] == 1260
    assert saved_attempt["status"] == "execution_completed_pending_runtime_and_png_audit"
    assert saved_attempt["capture_path"] is None
    assert not capture_path.exists()
    pending = [task for task in saved_matrix["tasks"] if task.get("task_id") == TASK_ID]
    assert len(pending) == 1
    assert pending[0]["capture_status"] == "pending"
    assert pending[0].get("capture_path") is None
