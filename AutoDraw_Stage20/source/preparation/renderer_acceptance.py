from __future__ import annotations

"""Fail-closed acceptance for paired live/offline renderer captures."""

from math import ceil, isfinite
from typing import Any

EXPECTED_PAIRED_AXIS_SOURCES = {
    "paired_renderer_single_stroke": {
        "x": "same_run_monitor_fit",
        "y": "same_run_full_screen_board_bounds",
    },
    "paired_renderer_vertical_single_stroke": {
        "x": "same_run_full_screen_board_bounds",
        "y": "same_run_monitor_fit",
    },
    "paired_renderer_diagonal_single_stroke": {
        "x": "same_run_monitor_fit",
        "y": "same_run_monitor_fit",
    },
}

EXPECTED_EXECUTOR_CONFIG = {
    "point_step_px": 2,
    "line_extension_px": 0,
    "point_delay_ms": 10,
    "after_mouse_up_ms": 20,
    "before_mouse_down_ms": 20,
    "after_mouse_down_ms": 40,
    "end_hold_ms": 50,
    "countdown_seconds": 5,
}

RENDERER_ACCEPTANCE_THRESHOLDS = {
    "alpha_threshold": 24,
    "iou_min": 0.92,
    "precision_min": 0.92,
    "recall_min": 0.92,
    # Consistent upper bound for symmetric-difference/live pixels when
    # IoU, precision and recall are each at least 0.92 (rounded upward).
    "symmetric_difference_fraction_max": 0.087,
    # Bounding-box edge tolerance scales with the smaller compared extent.
    "bbox_edge_difference_fraction_max": 0.08,
    "bbox_edge_difference_min_px": 1,
}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if isfinite(value) else None


def _point(value: Any) -> tuple[float, float] | None:
    if isinstance(value, dict):
        x, y = _number(value.get("x")), _number(value.get("y"))
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        x, y = _number(value[0]), _number(value[1])
    else:
        return None
    return (x, y) if x is not None and y is not None else None


def _points_equal(left: list[Any], right: list[Any], tolerance: float = 1e-6) -> bool:
    if len(left) != len(right):
        return False
    for left_item, right_item in zip(left, right):
        a, b = _point(left_item), _point(right_item)
        if a is None or b is None or abs(a[0] - b[0]) > tolerance or abs(a[1] - b[1]) > tolerance:
            return False
    return True


def _result(checks: dict[str, dict[str, Any]], failures: list[str]) -> dict[str, Any]:
    return {
        "status": "PASS" if not failures else "FAIL",
        "passed": not failures,
        "checks": checks,
        "failed_checks": failures,
    }


def validate_paired_capture(
    experiment: dict[str, Any],
    monitor_report: dict[str, Any],
    plan: dict[str, Any],
    renderer_fixture: dict[str, Any],
) -> dict[str, Any]:
    """Validate capture provenance, exact CHALK, stroke identity and full point replay."""
    checks: dict[str, dict[str, Any]] = {}
    failures: list[str] = []

    def check(name: str, passed: bool, actual: Any = None, expected: Any = None) -> None:
        item: dict[str, Any] = {"passed": bool(passed)}
        if actual is not None:
            item["actual"] = actual
        if expected is not None:
            item["expected"] = expected
        checks[name] = item
        if not passed:
            failures.append(name)

    if not all(isinstance(item, dict) for item in (experiment, monitor_report, plan, renderer_fixture)):
        check("all_inputs_are_objects", False)
        return _result(checks, failures)

    scenario = experiment.get("test_case")
    expected_axes = EXPECTED_PAIRED_AXIS_SOURCES.get(scenario)
    check("known_paired_scenario", expected_axes is not None, actual=scenario)

    experiment_id = experiment.get("experiment_id")
    summary = experiment.get("game_monitor_summary")
    summary = summary if isinstance(summary, dict) else {}
    monitor_capture = experiment.get("monitor_capture")
    monitor_capture = monitor_capture if isinstance(monitor_capture, dict) else {}
    execution = experiment.get("execution_report")
    execution = execution if isinstance(execution, dict) else {}
    generation = plan.get("generation")
    generation = generation if isinstance(generation, dict) else {}
    contract = generation.get("paired_renderer_capture")
    contract = contract if isinstance(contract, dict) else {}
    phases = experiment.get("phases")
    phases = phases if isinstance(phases, dict) else {}

    run_id, session_id = summary.get("run_id"), summary.get("session_id")
    check(
        "experiment_binding",
        bool(experiment_id)
        and summary.get("autodraw_experiment_id") == experiment_id
        and monitor_report.get("autodraw_experiment_id") == experiment_id
        and generation.get("experiment_id") == experiment_id,
        actual={
            "experiment_id": experiment_id,
            "summary": summary.get("autodraw_experiment_id"),
            "monitor": monitor_report.get("autodraw_experiment_id"),
            "plan": generation.get("experiment_id"),
        },
    )
    check(
        "run_session_binding",
        bool(run_id and session_id)
        and monitor_report.get("run_id") == run_id
        and monitor_report.get("session_id") == session_id
        and monitor_capture.get("run_id") == run_id
        and monitor_capture.get("session_id") == session_id,
        actual={"run_id": run_id, "session_id": session_id},
    )

    observed_radii = summary.get("observed_brush_radii")
    check(
        "brush_radius",
        experiment.get("brush_value_requested") == 10
        and generation.get("requested_brush_value") == 10
        and summary.get("brush_radius") == 10
        and observed_radii == [10]
        and summary.get("brush_radius_status") == "single"
        and monitor_report.get("brush_radius") == 10,
        actual={
            "experiment": experiment.get("brush_value_requested"),
            "plan": generation.get("requested_brush_value"),
            "observed": observed_radii,
            "status": summary.get("brush_radius_status"),
        },
        expected=10,
    )

    actual_config = execution.get("executor_config")
    actual_config = actual_config if isinstance(actual_config, dict) else {}
    config_ok = all(actual_config.get(key) == value for key, value in EXPECTED_EXECUTOR_CONFIG.items())
    check("frozen_executor_profile", config_ok, actual=actual_config, expected=EXPECTED_EXECUTOR_CONFIG)
    check(
        "executor_completed_one_stroke",
        execution.get("status") == "completed"
        and execution.get("completed_strokes") == 1
        and execution.get("total_strokes") == 1
        and execution.get("error") is None
        and execution.get("stop_reason") is None
        and isinstance(execution.get("mouse_release"), dict)
        and execution["mouse_release"].get("succeeded") is True,
        actual={key: execution.get(key) for key in ("status", "completed_strokes", "total_strokes", "error", "stop_reason")},
    )

    strokes = plan.get("strokes")
    check(
        "drawing_plan_contract",
        generation.get("test_case") == scenario
        and contract.get("schema_version") == 1
        and contract.get("scenario_id") == scenario
        and contract.get("requested_radius") == 10
        and contract.get("expected_strokes") == 1
        and contract.get("renderer_path_mode") == "smooth"
        and contract.get("executor_parameters") == EXPECTED_EXECUTOR_CONFIG
        and isinstance(strokes, list) and len(strokes) == 1,
    )
    check(
        "renderer_fixture_binding",
        renderer_fixture.get("sourceRunId") == run_id
        and renderer_fixture.get("mode") == "smooth"
        and _number(renderer_fixture.get("lineWidth")) == 10.0,
        actual={
            "sourceRunId": renderer_fixture.get("sourceRunId"),
            "mode": renderer_fixture.get("mode"),
            "lineWidth": renderer_fixture.get("lineWidth"),
        },
    )

    before_clear = phases.get("before_clear")
    before_clear = before_clear if isinstance(before_clear, dict) else {}
    before_draw = phases.get("before_draw")
    before_draw = before_draw if isinstance(before_draw, dict) else {}
    after_draw = phases.get("after_draw")
    after_draw = after_draw if isinstance(after_draw, dict) else {}
    before_files = before_draw.get("files") if isinstance(before_draw.get("files"), dict) else {}
    after_files = after_draw.get("files") if isinstance(after_draw.get("files"), dict) else {}
    before_size, after_size = before_draw.get("screen_size"), after_draw.get("screen_size")
    check(
        "clean_board_preflight",
        before_clear.get("status") == "restored_within_pixel_tolerance"
        and isinstance(before_draw.get("clear_check"), dict)
        and before_draw["clear_check"].get("status") == "restored_within_pixel_tolerance",
        actual={
            "before_clear": before_clear.get("status"),
            "before_draw": (before_draw.get("clear_check") or {}).get("status"),
        },
    )
    check(
        "same_screen_before_after_capture",
        isinstance(before_size, dict) and before_size == after_size
        and bool(before_files.get("full_screen")) and bool(after_files.get("full_screen"))
        and before_draw.get("captured_at_utc") is not None
        and after_draw.get("captured_at_utc") is not None,
        actual={"before": before_size, "after": after_size},
    )

    pre, post = monitor_report.get("pre_test_snapshot"), monitor_report.get("post_test_snapshot")
    pre = pre if isinstance(pre, dict) else {}
    post = post if isinstance(post, dict) else {}
    pre_count, post_count = pre.get("pointCount"), post.get("pointCount")
    count_types_ok = (
        isinstance(pre_count, int) and not isinstance(pre_count, bool)
        and isinstance(post_count, int) and not isinstance(post_count, bool)
    )
    chalk_delta = post_count - pre_count if count_types_ok else None
    snapshot_ok = (
        count_types_ok and post_count > pre_count
        and pre.get("validationStatus") == post.get("validationStatus") == "valid"
        and pre.get("isExact") is True and post.get("isExact") is True
        and pre.get("logicalWidth") == post.get("logicalWidth") == 460
        and pre.get("logicalHeight") == post.get("logicalHeight") == 240
        and pre.get("currentRadius") == post.get("currentRadius") == 10
    )
    check(
        "exact_pre_post_point_count",
        snapshot_ok,
        actual={
            "before": pre_count, "after": post_count,
            "before_validation": pre.get("validationStatus"),
            "after_validation": post.get("validationStatus"),
        },
    )

    chalk = summary.get("chalk")
    chalk = chalk if isinstance(chalk, dict) else {}
    check(
        "summary_exact_chalk_matches_point_count",
        chalk_delta is not None
        and chalk.get("status") == "exact"
        and chalk.get("pre_point_count") == pre_count
        and chalk.get("post_point_count") == post_count
        and chalk.get("consumed_points") == chalk_delta
        and summary.get("sampled_point_delta_total") == chalk_delta
        and summary.get("point_delta_matches_chalk") is True,
        actual={"chalk": chalk, "sampled_point_delta_total": summary.get("sampled_point_delta_total")},
    )

    events = monitor_report.get("events")
    events = events if isinstance(events, list) else []
    positive_quota = [
        event for event in events
        if isinstance(event, dict) and event.get("type") == "POINT_QUOTA_UPDATE"
        and (_number(event.get("pointDelta")) or 0) > 0
    ]
    positive_draw = [
        event for event in events
        if isinstance(event, dict) and event.get("type") == "DRAW_SAMPLE"
        and event.get("source") in {"onDrawing_wrapper", "state_poll"}
        and (_number(event.get("pointDelta")) or 0) > 0
    ]
    quota_points = [event.get("acceptedPoint") for event in positive_quota]
    draw_points = [event.get("acceptedPoint") for event in positive_draw]
    fixture_points = renderer_fixture.get("points")
    fixture_points = fixture_points if isinstance(fixture_points, list) else []
    quota_deltas = [_number(event.get("pointDelta")) for event in positive_quota]
    draw_deltas = [_number(event.get("pointDelta")) for event in positive_draw]
    point_stream_ok = (
        chalk_delta is not None
        and len(positive_quota) == chalk_delta
        and len(positive_draw) == chalk_delta
        and all(delta == 1.0 for delta in quota_deltas)
        and all(delta == 1.0 for delta in draw_deltas)
        and all(_point(point) is not None for point in quota_points)
        and all(_point(point) is not None for point in draw_points)
        and _points_equal(quota_points, draw_points)
        and _points_equal(quota_points, fixture_points)
    )
    check(
        "complete_accepted_point_stream",
        point_stream_ok,
        actual={
            "exact_chalk": chalk_delta,
            "positive_quota_updates": len(positive_quota),
            "positive_draw_samples": len(positive_draw),
            "fixture_points": len(fixture_points),
        },
    )

    stroke_ids = {
        event.get("strokeId")
        for event in events
        if isinstance(event, dict)
        and event.get("type") in {
            "POINTER_DOWN_CANDIDATE", "POINTER_UP_CANDIDATE",
            "POINT_QUOTA_UPDATE", "DRAW_SAMPLE", "MOUSE_MOVE_SAMPLE",
        }
        and event.get("strokeId")
    }
    pointer_down = sum(1 for event in events if isinstance(event, dict) and event.get("type") == "POINTER_DOWN_CANDIDATE")
    pointer_up = sum(1 for event in events if isinstance(event, dict) and event.get("type") == "POINTER_UP_CANDIDATE")
    check(
        "single_stroke_identity",
        len(stroke_ids) == 1
        and pointer_down == 1 and pointer_up == 1
        and monitor_report.get("stroke_count") == 1
        and monitor_report.get("stroke_candidate_count") == 1
        and monitor_report.get("non_consuming_stroke_candidate_count") == 0
        and summary.get("stroke_count") == 1
        and monitor_capture.get("stroke_count") == 1
        and monitor_capture.get("expected_stroke_count") == 1,
        actual={
            "stroke_ids": sorted(stroke_ids),
            "pointer_down": pointer_down, "pointer_up": pointer_up,
            "stroke_count": monitor_report.get("stroke_count"),
            "stroke_candidates": monitor_report.get("stroke_candidate_count"),
            "non_consuming_candidates": monitor_report.get("non_consuming_stroke_candidate_count"),
        },
    )

    integrity_keys = (
        "dropped_events", "monitor_dropped_events",
        "monitor_buffer_dropped_events_start", "monitor_buffer_dropped_events_end",
        "monitor_buffer_dropped_events_delta", "monitor_error_count_start",
        "monitor_error_count_end", "monitor_error_count_delta",
        "bridge_send_failures_start", "bridge_send_failures_end", "bridge_send_failures_delta",
        "collector_sequence_gap_count", "monitor_error_count",
    )
    integrity = all(monitor_report.get(key) == 0 for key in integrity_keys)
    summary_integrity = all(summary.get(key) == 0 for key in (
        "dropped_events", "monitor_dropped_events", "monitor_buffer_dropped_events_delta",
        "monitor_error_count_delta", "bridge_send_failures_delta",
        "collector_sequence_gap_count", "monitor_error_count",
    ))
    check(
        "monitor_bridge_integrity",
        integrity and monitor_report.get("monitor_errors") == [] and summary_integrity,
        actual={key: monitor_report.get(key) for key in integrity_keys},
    )
    check(
        "bridge_capture_accepted",
        monitor_capture.get("status") == "saved"
        and monitor_capture.get("chalk_status") == "exact"
        and monitor_capture.get("chalk_counter_consistent") is True
        and monitor_capture.get("point_delta_matches_chalk") is True
        and monitor_capture.get("brush_radius_status") == "single"
        and monitor_capture.get("stroke_count") == 1
        and monitor_capture.get("expected_stroke_count") == 1,
    )

    mouse_samples = [
        event for event in events
        if isinstance(event, dict) and event.get("type") == "MOUSE_MOVE_SAMPLE"
        and _number(event.get("boardX")) is not None and _number(event.get("boardY")) is not None
    ]
    xs = [_number(event["boardX"]) for event in mouse_samples]
    ys = [_number(event["boardY"]) for event in mouse_samples]
    span_x = max(xs) - min(xs) if xs else 0.0
    span_y = max(ys) - min(ys) if ys else 0.0
    span_ok = expected_axes is not None and (
        (span_x >= 20 if expected_axes["x"] == "same_run_monitor_fit" else span_x < 20)
        and (span_y >= 20 if expected_axes["y"] == "same_run_monitor_fit" else span_y < 20)
    )
    check(
        "input_telemetry_axis_coverage",
        span_ok and len(mouse_samples) >= 3,
        actual={"sample_count": len(mouse_samples), "span_x_logical_px": span_x, "span_y_logical_px": span_y},
        expected=expected_axes,
    )

    return _result(checks, failures)


def validate_transform_geometry(geometry: dict[str, Any], scenario: str) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    failures: list[str] = []

    def check(name: str, passed: bool, actual: Any = None, expected: Any = None) -> None:
        item: dict[str, Any] = {"passed": bool(passed)}
        if actual is not None:
            item["actual"] = actual
        if expected is not None:
            item["expected"] = expected
        checks[name] = item
        if not passed:
            failures.append(name)

    expected_axes = EXPECTED_PAIRED_AXIS_SOURCES.get(scenario)
    actual_axes = geometry.get("axis_sources") if isinstance(geometry, dict) else None
    check("scenario_axis_sources", expected_axes is not None and actual_axes == expected_axes,
          actual=actual_axes, expected=expected_axes)
    check(
        "both_axes_cross_checked",
        geometry.get("validation_status") == "both_axes_cross_checked_with_inspect_and_same_run_screenshot_bounds",
        actual=geometry.get("validation_status"),
    )

    offsets = geometry.get("screen_offset_range_px", {})
    for axis in ("x", "y"):
        value = _number(offsets.get(axis)) if isinstance(offsets, dict) else None
        check(f"client_screen_offset_range_{axis}", value is not None and value <= 0.01,
              actual=value, expected="<= 0.01 px")

    residuals = geometry.get("axis_max_abs_residual_px", {})
    inspect_origin = geometry.get("inspect_origin", {})
    inspect_scale = geometry.get("inspect_scale", {})
    cross = geometry.get("screenshot_bounds_cross_check", {})
    fits = {"x": geometry.get("horizontal_fit"), "y": geometry.get("vertical_fit")}
    for axis in ("x", "y"):
        residual = _number(residuals.get(axis)) if isinstance(residuals, dict) else None
        check(f"axis_{axis}_max_residual", residual is not None and residual <= 0.75,
              actual=residual, expected="<= 0.75 screen px")
        origin_diff = _number(cross.get(f"inspect_{axis}_origin_difference_px")) if isinstance(cross, dict) else None
        scale_diff = _number(cross.get(f"inspect_{axis}_scale_relative_difference")) if isinstance(cross, dict) else None

        if expected_axes and expected_axes[axis] == "same_run_monitor_fit":
            fit = fits.get(axis)
            fit_origin = _number(fit.get("origin")) if isinstance(fit, dict) else None
            fit_scale = _number(fit.get("scale")) if isinstance(fit, dict) else None
            fit_residual = _number(fit.get("max_abs_residual_px")) if isinstance(fit, dict) else None
            insp_origin = _number(inspect_origin.get(axis)) if isinstance(inspect_origin, dict) else None
            insp_scale = _number(inspect_scale.get(axis)) if isinstance(inspect_scale, dict) else None
            monitor_origin_diff = abs(fit_origin - insp_origin) if fit_origin is not None and insp_origin is not None else None
            monitor_scale_diff = abs(fit_scale / insp_scale - 1) if fit_scale is not None and insp_scale not in (None, 0) else None
            screenshot_origin_diff = _number(cross.get(f"monitor_{axis}_origin_difference_px"))
            screenshot_scale_diff = _number(cross.get(f"monitor_{axis}_scale_relative_difference"))
            check(f"monitor_{axis}_fit_exists", isinstance(fit, dict))
            check(f"monitor_{axis}_fit_residual", fit_residual is not None and fit_residual <= 0.75,
                  actual=fit_residual, expected="<= 0.75 screen px")
            check(f"monitor_{axis}_vs_inspect_origin", monitor_origin_diff is not None and monitor_origin_diff <= 0.5,
                  actual=monitor_origin_diff, expected="<= 0.5 px")
            check(f"monitor_{axis}_vs_inspect_scale", monitor_scale_diff is not None and monitor_scale_diff <= 0.002,
                  actual=monitor_scale_diff, expected="<= 0.2%")
            check(f"monitor_{axis}_vs_screenshot_origin", screenshot_origin_diff is not None and abs(screenshot_origin_diff) <= 1.0,
                  actual=screenshot_origin_diff, expected="absolute difference <= 1.0 px")
            check(f"monitor_{axis}_vs_screenshot_scale", screenshot_scale_diff is not None and abs(screenshot_scale_diff) <= 0.002,
                  actual=screenshot_scale_diff, expected="absolute relative difference <= 0.2%")
        else:
            check(f"screenshot_{axis}_vs_inspect_origin", origin_diff is not None and abs(origin_diff) <= 1.0,
                  actual=origin_diff, expected="absolute difference <= 1.0 px")
            check(f"screenshot_{axis}_vs_inspect_scale", scale_diff is not None and abs(scale_diff) <= 0.002,
                  actual=scale_diff, expected="absolute relative difference <= 0.2%")

    return _result(checks, failures)


def validate_renderer_comparison(
    metrics: dict[str, Any],
    live_changed_pixels: int,
    *,
    metric_suffix: str = "alpha_24",
) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    failures: list[str] = []

    def check(name: str, passed: bool, actual: Any = None, expected: Any = None) -> None:
        item: dict[str, Any] = {"passed": bool(passed)}
        if actual is not None:
            item["actual"] = actual
        if expected is not None:
            item["expected"] = expected
        checks[name] = item
        if not passed:
            failures.append(name)

    for key in ("iou", "precision", "recall"):
        value = _number(metrics.get(key)) if isinstance(metrics, dict) else None
        threshold = float(RENDERER_ACCEPTANCE_THRESHOLDS[f"{key}_min"])
        check(f"{key}_{metric_suffix}", value is not None and value >= threshold,
              actual=value, expected=f">= {threshold}")

    diff = _number(metrics.get("symmetric_difference_pixels")) if isinstance(metrics, dict) else None
    observed = _number(live_changed_pixels)
    ratio = diff / observed if diff is not None and observed is not None and observed > 0 else None
    maximum_ratio = float(RENDERER_ACCEPTANCE_THRESHOLDS["symmetric_difference_fraction_max"])
    check(f"symmetric_difference_fraction_{metric_suffix}", ratio is not None and ratio <= maximum_ratio,
          actual=ratio, expected=f"<= {maximum_ratio} of live changed pixels")

    def inclusive_edges(box: Any) -> list[int] | None:
        if not isinstance(box, list) or len(box) != 4:
            return None
        if any(isinstance(value, bool) or not isinstance(value, int) for value in box):
            return None
        x, y, width, height = box
        if width < 1 or height < 1:
            return None
        return [x, y, x + width - 1, y + height - 1]

    live_edges = inclusive_edges(metrics.get("observed_bbox_xywh")) if isinstance(metrics, dict) else None
    expected_edges = inclusive_edges(metrics.get("expected_bbox_xywh")) if isinstance(metrics, dict) else None
    edge_differences = (
        [abs(left - right) for left, right in zip(live_edges, expected_edges)]
        if live_edges is not None and expected_edges is not None else None
    )
    edge_fraction = float(RENDERER_ACCEPTANCE_THRESHOLDS["bbox_edge_difference_fraction_max"])
    edge_minimum = int(RENDERER_ACCEPTANCE_THRESHOLDS["bbox_edge_difference_min_px"])
    edge_tolerances = None
    if live_edges is not None and expected_edges is not None:
        compared_width = min(metrics["observed_bbox_xywh"][2], metrics["expected_bbox_xywh"][2])
        compared_height = min(metrics["observed_bbox_xywh"][3], metrics["expected_bbox_xywh"][3])
        x_tolerance = max(edge_minimum, ceil(compared_width * edge_fraction))
        y_tolerance = max(edge_minimum, ceil(compared_height * edge_fraction))
        edge_tolerances = [x_tolerance, y_tolerance, x_tolerance, y_tolerance]
    edges_pass = (
        edge_differences is not None
        and edge_tolerances is not None
        and all(delta <= tolerance for delta, tolerance in zip(edge_differences, edge_tolerances))
    )
    check(
        f"bbox_edges_{metric_suffix}",
        edges_pass,
        actual=edge_differences,
        expected=f"per-edge tolerance <= {edge_fraction:.1%} of the smaller compared bbox extent (minimum {edge_minimum} px)",
    )

    return {
        **_result(checks, failures),
        "thresholds": dict(RENDERER_ACCEPTANCE_THRESHOLDS),
        "bbox_edge_differences_px": edge_differences,
        "bbox_edge_tolerances_px": edge_tolerances,
        "symmetric_difference_fraction": ratio,
    }


def evaluate_per_run_acceptance(
    capture: dict[str, Any],
    transform: dict[str, Any],
    renderer: dict[str, Any],
) -> dict[str, Any]:
    passed = all(
        isinstance(item, dict) and item.get("passed") is True
        for item in (capture, transform, renderer)
    )
    return {
        "status": "PASS_PER_RUN" if passed else "REJECTED_PER_RUN",
        "passed": passed,
        "scope": "One unique capture only; orientation series acceptance requires three valid runs.",
        "capture": capture,
        "transform": transform,
        "renderer": renderer,
    }


def summarize_multi_axis_series(
    reports: list[dict[str, Any]],
    *,
    required_repeats: int = 3,
) -> dict[str, Any]:
    if isinstance(required_repeats, bool) or not isinstance(required_repeats, int) or required_repeats < 1:
        raise ValueError("required_repeats must be a positive integer.")

    scenarios = ("paired_renderer_vertical_single_stroke", "paired_renderer_diagonal_single_stroke")
    result = {
        scenario: {
            "required_valid_repeats": required_repeats,
            "accepted_runs": [],
            "rejected_runs": [],
            "duplicate_run_ids": [],
            "missing_valid_repeats": required_repeats,
            "status": "PENDING",
        }
        for scenario in scenarios
    }
    seen = {scenario: set() for scenario in scenarios}

    for report in reports:
        if not isinstance(report, dict):
            continue
        scenario = report.get("scenario_id")
        if scenario not in result:
            continue
        run_id = report.get("run_id")
        experiment_id = report.get("experiment_id")
        if not isinstance(run_id, str) or not run_id:
            result[scenario]["rejected_runs"].append({
                "run_id": None, "experiment_id": experiment_id, "reason": "missing_run_id",
            })
            continue
        if run_id in seen[scenario]:
            result[scenario]["duplicate_run_ids"].append(run_id)
            continue
        seen[scenario].add(run_id)
        formal = report.get("formal_acceptance")
        status = formal.get("status") if isinstance(formal, dict) else None
        item = {"run_id": run_id, "experiment_id": experiment_id}
        if status == "PASS_PER_RUN":
            result[scenario]["accepted_runs"].append(item)
        else:
            item["reason"] = status or "missing_formal_acceptance"
            result[scenario]["rejected_runs"].append(item)

    complete = True
    for item in result.values():
        count = len(item["accepted_runs"])
        item["missing_valid_repeats"] = max(0, required_repeats - count)
        item["status"] = "PASS" if count >= required_repeats else "PENDING"
        complete = complete and item["status"] == "PASS"

    return {
        "schema_version": 1,
        "status": "PASS" if complete else "PENDING",
        "required_valid_repeats_per_orientation": required_repeats,
        "orientations": result,
        "interpretation": (
            "Series acceptance requires three unique per-run PASS captures for both vertical and diagonal scenarios. "
            "Rejected attempts remain visible and do not count toward the required repeats."
        ),
    }
