"""FILL001-SERIES-001 generic exact run binding for variable-length Stage6 plans.

Generalizes the verified V5 binding rules without modifying the frozen 29-stroke
V5 binder. Use only run-bound, closed, complete raw Monitor 0.2.4 events.
Unknown inputs, silent point deltas, cross-run gaps and slider ambiguity block.
"""
from __future__ import annotations

from typing import Any
import math


class SeriesBindingBlocked(ValueError):
    pass


def _rect(box: Any, label: str) -> dict:
    if (not isinstance(box, dict) or set(box) != {"left", "right", "top", "bottom"}
            or any(type(box[k]) not in (float, int) or not math.isfinite(box[k])
                   for k in box)
            or box["left"] >= box["right"] or box["top"] >= box["bottom"]):
        raise SeriesBindingBlocked(f"Missing verified {label} CSS corridor")
    return box


def _inside(x: float, y: float, r: dict) -> bool:
    return r["left"] <= x <= r["right"] and r["top"] <= y <= r["bottom"]


def _exact(snapshot: Any) -> tuple[int, int]:
    if not isinstance(snapshot, dict) or snapshot.get("isExact") is not True:
        raise SeriesBindingBlocked("Monitor snapshot is not exact")
    point, maximum, remaining = (
        snapshot.get("pointCount"),snapshot.get("maxPoints"),snapshot.get("remainingPoints")
    )
    if (any(type(v) is not int for v in (point,maximum,remaining))
            or maximum <= 0 or not 0 <= point <= maximum
            or remaining != maximum-point):
        raise SeriesBindingBlocked("Invalid exact game point counter")
    return point, maximum


def validate_series_bridge_runs(
    runs: list[dict], *,
    session_id: str, task_id: str,
    expected_pointer_down_client: list[tuple[float,float]],
    expected_brush_radii: list[int],
    board_client_rect: dict,
    slider_client_corridor: dict,
    expected_pre: int = 1,
) -> dict:
    """Bind a full variable-length figure to closed same-session game events."""
    if (not isinstance(session_id, str) or not session_id
            or not isinstance(task_id, str) or not task_id
            or not isinstance(runs, list) or not 1 <= len(runs) <= 4
            or type(expected_pre) is not int or expected_pre != 1):
        raise SeriesBindingBlocked("Missing isolated run/session identity")
    if (not isinstance(expected_pointer_down_client, list)
            or not expected_pointer_down_client
            or not isinstance(expected_brush_radii, list)
            or len(expected_pointer_down_client) != len(expected_brush_radii)
            or len(expected_brush_radii) > 5000):
        raise SeriesBindingBlocked("Incomplete series source drawing sequence")
    planned = []
    for (p, radius) in zip(expected_pointer_down_client, expected_brush_radii):
        if (not isinstance(p, (tuple, list)) or len(p) != 2
                or any(type(v) not in (float, int) or not math.isfinite(v) for v in p)
                or type(radius) is not int or not 1 <= radius <= 30):
            raise SeriesBindingBlocked("Invalid source point or radius")
        planned.append((float(p[0]),float(p[1]),radius))
    board=_rect(board_client_rect,"board")
    slider=_rect(slider_client_corridor,"slider")
    if (slider["left"] < board["right"] and slider["right"] > board["left"]
            and slider["top"] < board["bottom"] and slider["bottom"] > board["top"]):
        raise SeriesBindingBlocked("Brush slider corridor overlaps drawing board")
    ordered=sorted(runs, key=lambda r:r.get("started_at_utc","") if isinstance(r,dict) else "")
    cursor=0
    excluded=0
    expected_post=expected_pre
    maximum=None
    seen_ids=set()
    run_ids=[]
    raw_count=0
    for run in ordered:
        if (not isinstance(run,dict) or run.get("schema_version") != 1
                or run.get("record_type") != "autodraw_game_monitor_run"
                or run.get("session_id") != session_id
                or run.get("execution_status") != "completed"
                or run.get("monitor_dropped_events") != 0
                or run.get("monitor_error_count") != 0
                or run.get("collector_sequence_gap_count") != 0
                or run.get("bridge_send_failures_delta") != 0
                or run.get("point_delta_matches_chalk") is not True
                or run.get("monitor_errors") != []):
            raise SeriesBindingBlocked("Incomplete, unrelated or corrupt Monitor run")
        rid=run.get("run_id")
        if not isinstance(rid,str) or not rid or rid in seen_ids:
            raise SeriesBindingBlocked("Missing or duplicate closed run ID")
        seen_ids.add(rid)
        run_ids.append(rid)
        pre, max_pre=_exact(run.get("pre_test_snapshot"))
        post, max_post=_exact(run.get("post_test_snapshot"))
        chalk=run.get("chalk")
        if (maximum is not None and maximum != max_pre
                or pre != expected_post
                or post < pre or max_pre != max_post
                or not isinstance(chalk,dict)
                or chalk.get("status") != "exact"
                or chalk.get("pre_point_count") != pre
                or chalk.get("post_point_count") != post
                or chalk.get("consumed_points") != post-pre
                or chalk.get("max_points") != max_pre):
            raise SeriesBindingBlocked("Game exact counters do not bind to continuous closed runs")
        maximum=max_pre
        expected_post=post
        events=run.get("events")
        if (not isinstance(events,list) or len(events) != run.get("event_count")
                or any(not isinstance(e,dict) or e.get("monitorVersion") != "0.2.4" for e in events)):
            raise SeriesBindingBlocked("Raw Monitor 0.2.4 evidence missing")
        raw_count += len(events)
        downs=[e for e in events if e.get("type") == "POINTER_DOWN_CANDIDATE"]
        metrics=run.get("per_stroke_metrics")
        if (not isinstance(metrics,list) or len(metrics) != len(downs)
                or len(downs) != run.get("stroke_candidate_count")):
            raise SeriesBindingBlocked("Incomplete per-stroke metric alignment")
        drawing_in_run=0
        slider_in_run=0
        for e,m in zip(downs,metrics):
            if (not isinstance(m,dict) or e.get("strokeId") != m.get("stroke_id")
                    or m.get("lifecycle_status") != "complete"
                    or type(e.get("clientX")) not in (float,int)
                    or type(e.get("clientY")) not in (float,int)):
                raise SeriesBindingBlocked("Stroke lifecycle or mouse position unavailable")
            x,y=e["clientX"],e["clientY"]
            expected=planned[cursor] if cursor < len(planned) else None
            if (expected is not None
                    and abs(x-expected[0]) <= 3
                    and abs(y-expected[1]) <= 3):
                if (e.get("board",{}).get("currentRadius") != expected[2]
                        or type(m.get("point_count_delta")) is not int
                        or m["point_count_delta"] <= 0
                        or m.get("point_count_delta_matches_updates") is not True):
                    raise SeriesBindingBlocked("Executed brush or exact point delta disagrees with source")
                drawing_in_run += 1
                cursor += 1
            elif (_inside(x,y,slider)
                    and m.get("point_count_delta") == 0
                    and m.get("point_update_event_count") == 0):
                excluded += 1
                slider_in_run += 1
            else:
                raise SeriesBindingBlocked("Unexpected board/UI input cannot be excluded from CHALK")
        if (run.get("stroke_count") != drawing_in_run
                or run.get("non_consuming_stroke_candidate_count") != slider_in_run):
            raise SeriesBindingBlocked("Closed run stroke accounting differs from planned inputs")
    if cursor != len(planned) or excluded > 100:
        raise SeriesBindingBlocked("Variable-length figure did not complete all planned strokes")
    return {
        "status": "EXACT_RUN_BOUND", "session_id": session_id,
        "task_id": task_id, "run_ids": run_ids,
        "stroke_count": cursor, "excluded_zero_point_slider_drags": excluded,
        "monitor_event_count": raw_count,
        "pre_pointCount": expected_pre, "post_pointCount": expected_post,
        "exact_chalk": expected_post-expected_pre,
        "maxPoints": maximum,
        "method": "post.pointCount - pre.pointCount, continuous full closed Monitor runs",
        "png_quality": "NOT_EVALUATED",
        "independent_E5": "NOT_RUN",
    }
