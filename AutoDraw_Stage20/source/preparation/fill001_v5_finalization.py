"""Run-bound FILL-001 V5 finalization: exact CHALK and original screen PNG.

Do not infer CHALK from an arbitrary post-drawing heartbeat or predicted length.
Use only complete Game Monitor runs from the one fresh Bridge session and
unmodified before/after PNG files captured by the same Stage6 attempt.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from typing import Any, Callable

from fill001_v5_handoff import Fill001V5Error

POLICY = "FILL001_CHALK_FIRST_PERIMETER_V2"
# Runtime contract: guard against mixing a current V5 executor with stale finalizer code.
V5_BINDING_CONTRACT = "FILL001_V5_SLIDER_AWARE_BINDING_V2"


def _exact(snapshot: Any) -> tuple[int,int]:
    if not isinstance(snapshot, dict) or snapshot.get("isExact") is not True:
        raise Fill001V5Error("V5 run has no exact BoardPane resource snapshot.")
    points, total, left = [snapshot.get(k) for k in (
        "pointCount", "maxPoints", "remainingPoints"
    )]
    if (type(points) is not int or type(total) is not int or type(left) is not int
            or total <= 0 or points < 0 or left < 0 or points + left != total):
        raise Fill001V5Error("V5 run exact point counters are inconsistent.")
    return points,total


def validate_v5_bridge_runs(
    runs: list[dict], *,
    session_id: str, candidate_id: str,
    expected_pre: int = 1,
    expected_pointer_down_client: list[tuple[float,float]] | None = None,
    expected_board_client_rect: dict[str, float] | None = None,
    slider_client_corridor: dict[str, float] | None = None,
) -> dict:
    """An exact run chain needs 29 stroke candidates, all radii and no drops."""
    if not isinstance(runs, list) or not 1 <= len(runs) <= 2:
        raise Fill001V5Error("Expected one or two completed V5 Bridge runs.")
    ordered = sorted(runs, key=lambda x: x.get("started_at_utc", ""))
    expected_last = 2 if candidate_id == "K_trim_0_y190_w2" else (
        3 if candidate_id == "K_trim_0_y189_w3" else None
    )
    if expected_last is None:
        raise Fill001V5Error("Unknown frozen V5 candidate.")
    counts, radii, run_ids, totals = [], [], [], []
    all_pointer_downs: list[dict] = []
    all_metric_rows: list[dict] = []
    strict_slider_witness = expected_board_client_rect is not None or slider_client_corridor is not None
    if strict_slider_witness and (expected_board_client_rect is None or slider_client_corridor is None
            or expected_pointer_down_client is None):
        raise Fill001V5Error("Slider exclusion requires both verified board and slider bounds and planned inputs.")
    if strict_slider_witness:
        def check_rect(rect: dict, label: str) -> None:
            if (not isinstance(rect, dict) or set(rect) != {"left", "top", "right", "bottom"}
                    or any(type(rect[k]) not in (int, float) or not math.isfinite(rect[k]) for k in rect)
                    or rect["right"] <= rect["left"] or rect["bottom"] <= rect["top"]):
                raise Fill001V5Error(f"Invalid verified V5 {label} rectangle.")
        check_rect(expected_board_client_rect, "board")
        check_rect(slider_client_corridor, "slider")
        if not (slider_client_corridor["left"] >= expected_board_client_rect["right"]
                or slider_client_corridor["right"] <= expected_board_client_rect["left"]
                or slider_client_corridor["bottom"] <= expected_board_client_rect["top"]
                or slider_client_corridor["top"] >= expected_board_client_rect["bottom"]):
            raise Fill001V5Error("V5 slider corridor overlaps game board.")
    last_post = expected_pre
    for run in ordered:
        if not isinstance(run, dict) or run.get("session_id") != session_id:
            raise Fill001V5Error("V5 Bridge run session mismatch.")
        if (
            not isinstance(run, dict)
            or run.get("schema_version") != 1
            or run.get("record_type") != "autodraw_game_monitor_run"
            or run.get("session_id") != session_id
            or run.get("execution_status") != "completed"
            or run.get("monitor_dropped_events") != 0
            or run.get("monitor_error_count") != 0
            or run.get("collector_sequence_gap_count") != 0
            or run.get("bridge_send_failures_delta") != 0
            or (not strict_slider_witness and run.get("non_consuming_stroke_candidate_count") != 0)
            or run.get("point_delta_matches_chalk") is not True
            or run.get("monitor_errors") != []
        ):
            raise Fill001V5Error("V5 Bridge run was incomplete or has dropped/invalid events.")
        count = run.get("stroke_count")
        extras = run.get("non_consuming_stroke_candidate_count")
        if (type(extras) is not int or extras < 0 or extras > 10):
            raise Fill001V5Error("Invalid V5 non-consuming slider input count.")
        if (type(count) is not int or count <= 0 or count > 29
                or run.get("stroke_candidate_count") != count + (extras if strict_slider_witness else 0)):
            raise Fill001V5Error("Unexpected V5 Bridge stroke count.")
        pre, maximum = _exact(run.get("pre_test_snapshot"))
        post, post_max = _exact(run.get("post_test_snapshot"))
        chalk = run.get("chalk")
        if (post_max != maximum or pre != last_post or post < pre
                or not isinstance(chalk, dict)
                or chalk.get("status") != "exact"
                or chalk.get("pre_point_count") != pre
                or chalk.get("post_point_count") != post
                or chalk.get("consumed_points") != post-pre
                or chalk.get("max_points") != maximum):
            raise Fill001V5Error("V5 exact CHALK is not continuous and run-bound.")
        if not isinstance(run.get("run_id"), str) or not run["run_id"]:
            raise Fill001V5Error("Missing Game Monitor run ID.")
        seen_radii = run.get("observed_brush_radii")
        # Bridge serializes observed slider radii as JSON floats (10.0),
        # while game pointer-down currentRadius is an integer. Normalize only
        # mathematically integral finite numeric values; never accept bool,
        # fractional radii, NaN, infinity or unplanned drawing widths.
        def integral_radius(value: Any) -> bool:
            return (type(value) in (int, float)
                    and 1 <= value <= 30
                    and (type(value) is int
                         or (math.isfinite(value) and value.is_integer())))
        if (not isinstance(seen_radii, list) or not seen_radii
                or any(not integral_radius(v) for v in seen_radii)
                or (not strict_slider_witness
                    and any(v not in (10, expected_last) for v in seen_radii))):
            raise Fill001V5Error("V5 Bridge observed unexpected brush radii.")
        events = run.get("events")
        if (not isinstance(events, list)
                or run.get("event_count") != len(events)
                or any(not isinstance(e, dict) or e.get("monitorVersion") != "0.2.4"
                       for e in events)):
            raise Fill001V5Error("V5 raw Bridge events have wrong Monitor version.")
        run_downs = [event for event in events if event.get("type") == "POINTER_DOWN_CANDIDATE"]
        if strict_slider_witness:
            metrics = run.get("per_stroke_metrics")
            if (not isinstance(metrics, list) or len(metrics) != len(run_downs)
                    or len(metrics) != count + extras):
                raise Fill001V5Error("Missing complete per-stroke slider and drawing metrics.")
            for down, metric in zip(run_downs, metrics):
                if (not isinstance(metric, dict) or down.get("strokeId") != metric.get("stroke_id")
                        or metric.get("lifecycle_status") != "complete"):
                    raise Fill001V5Error("V5 stroke lifecycle cannot be tied to pointer event.")
            all_metric_rows.extend(metrics)
        all_pointer_downs.extend(run_downs)
        counts.append(count)
        radii.extend(seen_radii)
        totals.append((pre,post))
        run_ids.append(run["run_id"])
        last_post = post
    if sum(counts) != 29 or (not strict_slider_witness and set(radii) != {10,expected_last}):
        raise Fill001V5Error("V5 29 strokes and both brush sizes are not confirmed.")
    if len(ordered) == 2 and (
        counts != [28,1] or (
            not strict_slider_witness and (
                sorted(set(ordered[0]["observed_brush_radii"])) != [10]
                or sorted(set(ordered[1]["observed_brush_radii"])) != [expected_last]
            )
        )
    ):
        raise Fill001V5Error("V5 two-run brush switch split is inconsistent.")
    if expected_pointer_down_client is not None:
        if (not isinstance(expected_pointer_down_client, list)
                or len(expected_pointer_down_client) != 29
                or (not strict_slider_witness and len(all_pointer_downs) != 29)):
            raise Fill001V5Error("V5 29 planned pointer-down events are not proven.")
        if strict_slider_witness:
            cursor = 0
            excluded = 0
            for down, metric in zip(all_pointer_downs, all_metric_rows):
                ex, ey = down.get("clientX"), down.get("clientY")
                if type(ex) not in (int, float) or type(ey) not in (int, float):
                    raise Fill001V5Error("V5 pointer coordinates are missing.")
                planned = expected_pointer_down_client[cursor] if cursor < 29 else None
                if planned is not None and abs(ex-planned[0]) <= 3 and abs(ey-planned[1]) <= 3:
                    actual_radius = down.get("board", {}).get("currentRadius")
                    expected_radius = 10 if cursor < 28 else expected_last
                    if actual_radius != expected_radius:
                        raise Fill001V5Error("V5 drawing radius differs from frozen width sequence.")
                    if (type(metric.get("point_count_delta")) is not int
                            or metric["point_count_delta"] <= 0
                            or metric.get("point_count_delta_matches_updates") is not True):
                        raise Fill001V5Error("V5 drawing stroke has no matched exact point delta.")
                    cursor += 1
                    continue
                # Only a zero-point control action in the CONFIRMED slider
                # corridor may be excluded; an accidental touch on the board
                # or an unknown UI button must invalidate CHALK binding.
                r = slider_client_corridor
                if (not (r["left"] <= ex <= r["right"] and r["top"] <= ey <= r["bottom"])
                        or metric.get("point_count_delta") != 0
                        or metric.get("point_update_event_count") != 0):
                    raise Fill001V5Error("Unexpected off-plan pointer event; exact V5 CHALK BLOCKED.")
                excluded += 1
            if cursor != 29 or excluded != sum(run["non_consuming_stroke_candidate_count"] for run in ordered):
                raise Fill001V5Error("V5 planned strokes or slider-only inputs are not uniquely bound.")
        else:
            for index, (event, (x,y)) in enumerate(zip(all_pointer_downs,expected_pointer_down_client)):
                ex, ey = event.get("clientX"), event.get("clientY")
                if (type(ex) not in (int,float) or type(ey) not in (int,float)
                        or abs(ex-x) > 3 or abs(ey-y) > 3):
                    raise Fill001V5Error(
                        f"V5 pointer-down {index+1} differs from frozen planned start; "
                        "unexpected user/game input or geometry drift."
                    )
    return {
        "status": "EXACT_RUN_BOUND",
        "session_id": session_id,
        "run_ids": run_ids,
        "stroke_count": 29,
        "bridge_run_stroke_counts": counts,
        "observed_brush_radii": [10, expected_last] if strict_slider_witness else sorted(set(radii)),
        "excluded_zero_point_slider_drags": (sum(run["non_consuming_stroke_candidate_count"] for run in ordered)
                                             if strict_slider_witness else 0),
        "pre_pointCount": expected_pre,
        "post_pointCount": last_post,
        "exact_chalk": last_post-expected_pre,
        "maxPoints": maximum,
        "method": "post.pointCount - pre.pointCount across continuous exact runs",
    }


def finalize_v5_stage6_attempt(
    *, bridge_root: Path, request: dict, baseline_files: set[str],
    summary: dict, pre_png: Path, post_png: Path,
    timeout_seconds: float = 12.0,
    post_capture_callback: Callable[[int], Path] | None = None,
) -> dict:
    """Conservatively bind new Bridge runs; preserve failures as evidence."""
    if summary.get("status") != "completed" or summary.get("completed_strokes") != 29:
        raise Fill001V5Error("Stage6 did not complete all 29 V5 strokes.")
    if not pre_png.is_file() or not post_png.is_file():
        raise Fill001V5Error("Missing original before/after V5 PNG.")
    sid=request["session_id"]
    folder=Path(bridge_root)/sid
    if not folder.is_dir():
        raise Fill001V5Error("Missing authenticated V5 Bridge session folder.")
    expected = request.get("expected_pointer_down_client")
    if not isinstance(expected, list) or len(expected) != 29:
        raise Fill001V5Error(
            "V5 finalization requires all 29 independent planned pointer-down positions."
        )
    deadline=time.monotonic()+timeout_seconds
    last_error=None
    while time.monotonic()<deadline:
        files=sorted(p for p in folder.glob("game-monitor-run-*.json")
                     if p.name not in baseline_files)
        try:
            runs=[json.loads(p.read_text(encoding="utf-8")) for p in files]
            binding=validate_v5_bridge_runs(
                runs,session_id=sid,candidate_id=request["candidate_id"],
                expected_pointer_down_client=expected,
                expected_board_client_rect=request.get("board_client_rect"),
                slider_client_corridor=request.get("slider_client_corridor"),
            )
            binding["bridge_run_paths"]=[str(p) for p in files]
            break
        except (Fill001V5Error,OSError,ValueError) as exc:
            last_error=str(exc)
            time.sleep(.3)
    else:
        raise Fill001V5Error(
            "V5 exact CHALK cannot be bound to a complete 29-stroke Bridge run: "
            + str(last_error)
        )
    # Exact CHALK from the closed run is logically separate from PNG quality.
    # A screenshot failure must not discard an independently verified counter.
    result = {
        "binding": binding,
        "screen_mask_v2": None,
        "quality_gate": "NOT_EVALUATED",
        "quality_policy_id": POLICY,
        "status": "EXACT_RUN_BOUND_PNG_AUDIT_PENDING",
    }
    try:
        from fill001_screen_mask_v2 import audit_screen_mask_v2
        if post_capture_callback is None:
            raise Fill001V5Error("Settled post-run PNG capture was not requested.")
        settled_png = Path(post_capture_callback(binding["post_pointCount"]))
        if not settled_png.is_file() or settled_png == post_png:
            raise Fill001V5Error("Post-run settled PNG capture is missing or reused.")
        mapping=request.get("mapping")
        if not isinstance(mapping, dict) or not isinstance(mapping.get("board_screen_corners"),dict):
            raise Fill001V5Error("No run-bound independent screen geometry for V5 quality.")
        geometry={
            "run_id":request["attempt_id"],
            "coordinate_system":"desktop_screen_css_pixels",
            "validation_status":"valid",
            "independent_screen_mapping":True,
            "same_run":True,
            "board_screen_corners":mapping["board_screen_corners"],
            "evidence_sha256":mapping["passive_samples_sha256"],
        }
        quality=audit_screen_mask_v2(
            "rectangle",pre_png,settled_png,
            run_id=request["attempt_id"],screen_roi=request["screen_roi"],
            geometry=geometry,quality_policy=POLICY,
        )
        result["screen_mask_v2"] = quality
        result["quality_gate"] = quality["active_quality_gate"]
        result["status"] = "RUN_BOUND_SCREEN_AUDITED_NOT_INDEPENDENT_E5"
    except Exception as exc:
        result["quality_error"] = f"{type(exc).__name__}: {exc}"
        result["status"] = "EXACT_RUN_BOUND_PNG_AUDIT_BLOCKED"
    return result
