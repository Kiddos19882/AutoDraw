from __future__ import annotations

import pytest

from renderer_geometry import (
    RendererGeometryError,
    detect_board_bounds_from_screenshots,
    derive_live_board_screen_transform,
)


def evidence():
    return {
        "provenance": {"same_screen_as_live_capture": True},
        "screen": {"width": 1920, "height": 1080, "windows_scale_percent": 100, "device_pixel_ratio": 1},
        "board": {"logical_width": 460, "logical_height": 240},
        "renderer": {
            "canvas_scale_x": 3, "canvas_scale_y": 3,
            "stage": {"width": 1314, "height": 600},
            "canvas": {
                "rect": {"left": 0, "top": -0.5, "width": 1920, "height": 878},
                "css_matrix": {"a": 0.487062, "b": 0, "c": 0, "d": 0.487778, "tx": 0, "ty": 0},
                "transform_origin": {"x": 0, "y": 0},
            },
            "board_stage_corners": {
                "top_left": {"x": 340.7916660308838, "y": 72},
                "bottom_right": {"x": 800.7916660308838, "y": 312},
            },
        },
    }


def report():
    events = []
    for sx in range(527, 1111, 2):
        bx = (sx - 497.95204087569135) / 1.4612139902690628
        events.append({"type": "MOUSE_MOVE_SAMPLE", "screenX": sx, "clientX": sx,
                       "screenY": 442, "clientY": 279, "boardX": bx, "boardY": 119})
    return {"record_type": "autodraw_game_monitor_run", "events": events}


def test_independent_transform_uses_monitor_x_and_inspect_y():
    result = derive_live_board_screen_transform(report(), evidence(),
        {"x": 496, "y": 265, "width": 674, "height": 355}, (1920, 1080))
    assert result["board_to_screen"]["origin_x"] == pytest.approx(497.952, abs=0.01)
    assert result["board_to_screen"]["origin_y"] == pytest.approx(267.860, abs=0.01)
    assert result["board_to_screen"]["scale_x"] == pytest.approx(1.461214, abs=1e-5)
    assert result["board_to_screen"]["scale_y"] == pytest.approx(1.463334, abs=1e-6)
    assert result["screen_offset_from_client"] == {"x": 0, "y": 163, "sample_count": 292}
    assert result["roi_alignment"]["board_origin_in_roi"]["x"] == pytest.approx(1.952, abs=0.01)
    assert result["roi_alignment"]["board_origin_in_roi"]["y"] == pytest.approx(2.860, abs=0.01)


def test_screenshot_bounds_are_detected_and_verified_before_after():
    import numpy as np
    import cv2

    before = np.full((1080, 1920, 3), (233, 252, 255), dtype=np.uint8)
    cv2.rectangle(before, (498, 268), (1169, 618), (238, 238, 238), thickness=-1)
    after = before.copy()
    cv2.line(after, (519, 442), (1117, 442), (27, 27, 27), thickness=15)

    result = detect_board_bounds_from_screenshots(
        before, after, {"x": 496, "y": 265, "width": 674, "height": 355},
    )
    assert result["bounds"] == {"x": 498, "y": 268, "width": 672, "height": 351}
    assert result["before_component"]["fill_fraction"] >= 0.995
    assert result["after_component"]["fill_fraction"] >= 0.90
    assert result["scale_px_per_logical_px"]["x"] == pytest.approx(672 / 460)
    assert result["scale_px_per_logical_px"]["y"] == pytest.approx(351 / 240)


def test_screenshot_bounds_reject_board_movement_between_captures():
    import numpy as np
    import cv2

    before = np.full((1080, 1920, 3), (233, 252, 255), dtype=np.uint8)
    cv2.rectangle(before, (498, 268), (1169, 618), (238, 238, 238), thickness=-1)
    after = np.full_like(before, (233, 252, 255))
    cv2.rectangle(after, (500, 268), (1171, 618), (238, 238, 238), thickness=-1)
    with pytest.raises(RendererGeometryError, match="bounds changed"):
        detect_board_bounds_from_screenshots(
            before, after, {"x": 496, "y": 265, "width": 674, "height": 355},
        )


def test_transform_uses_screenshot_y_and_cross_checks_monitor_and_inspect():
    bounds = {"x": 498, "y": 268, "width": 672, "height": 351}
    result = derive_live_board_screen_transform(
        report(), evidence(),
        {"x": 496, "y": 265, "width": 674, "height": 355}, (1920, 1080),
        screenshot_board_bounds=bounds,
    )
    assert result["method"] == "same_run_monitor_x_fit_plus_screenshot_board_bounds_y"
    assert result["board_to_screen"]["origin_x"] == pytest.approx(497.952, abs=0.01)
    assert result["board_to_screen"]["origin_y"] == pytest.approx(268.0, abs=1e-9)
    assert result["board_to_screen"]["scale_x"] == pytest.approx(1.461214, abs=1e-5)
    assert result["board_to_screen"]["scale_y"] == pytest.approx(351 / 240, abs=1e-9)
    assert result["vertical_sample_residual_px"] == pytest.approx(0.0375, abs=1e-6)
    assert result["screenshot_bounds_cross_check"]["monitor_x_origin_difference_px"] == pytest.approx(-0.048, abs=0.01)


def test_transform_rejects_screenshot_bounds_that_disagree_with_inspect():
    with pytest.raises(RendererGeometryError, match="Inspect Y origin"):
        derive_live_board_screen_transform(
            report(), evidence(),
            {"x": 496, "y": 265, "width": 674, "height": 355}, (1920, 1080),
            screenshot_board_bounds={"x": 498, "y": 270, "width": 672, "height": 351},
        )


def _axis_report(points):
    events = []
    scale_x = 672 / 460
    scale_y = 351 / 240
    for board_x, board_y in points:
        screen_x = 498 + board_x * scale_x
        screen_y = 268 + board_y * scale_y
        events.append({
            "type": "MOUSE_MOVE_SAMPLE",
            "screenX": screen_x, "clientX": screen_x,
            "screenY": screen_y, "clientY": screen_y - 163,
            "boardX": board_x, "boardY": board_y,
        })
    return {"record_type": "autodraw_game_monitor_run", "events": events}


def test_vertical_trajectory_fits_y_from_monitor_and_x_from_screenshot():
    points = [(230, 20 + index * 5) for index in range(40)]
    result = derive_live_board_screen_transform(
        _axis_report(points), evidence(),
        {"x": 496, "y": 265, "width": 674, "height": 355}, (1920, 1080),
        screenshot_board_bounds={"x": 498, "y": 268, "width": 672, "height": 351},
    )
    assert result["method"] == "same_run_monitor_y_fit_plus_screenshot_board_bounds_x"
    assert result["axis_sources"] == {
        "x": "same_run_full_screen_board_bounds",
        "y": "same_run_monitor_fit",
    }
    assert result["horizontal_fit"] is None
    assert result["vertical_fit"]["sample_count"] == 40
    assert result["board_to_screen"]["origin_x"] == pytest.approx(498)
    assert result["board_to_screen"]["origin_y"] == pytest.approx(268)
    assert result["board_to_screen"]["scale_x"] == pytest.approx(672 / 460)
    assert result["board_to_screen"]["scale_y"] == pytest.approx(351 / 240)
    assert result["axis_max_abs_residual_px"]["x"] == pytest.approx(0, abs=1e-9)
    assert result["axis_max_abs_residual_px"]["y"] == pytest.approx(0, abs=1e-9)


def test_diagonal_trajectory_fits_both_axes_from_monitor():
    points = [(20 + index * 10, 20 + index * 5) for index in range(40)]
    result = derive_live_board_screen_transform(
        _axis_report(points), evidence(),
        {"x": 496, "y": 265, "width": 674, "height": 355}, (1920, 1080),
        screenshot_board_bounds={"x": 498, "y": 268, "width": 672, "height": 351},
    )
    assert result["method"] == "same_run_monitor_xy_fit"
    assert result["axis_sources"] == {
        "x": "same_run_monitor_fit",
        "y": "same_run_monitor_fit",
    }
    assert result["horizontal_fit"]["sample_count"] == 40
    assert result["vertical_fit"]["sample_count"] == 40
    assert result["board_to_screen"]["origin_x"] == pytest.approx(498)
    assert result["board_to_screen"]["origin_y"] == pytest.approx(268)
    assert result["board_to_screen"]["scale_x"] == pytest.approx(672 / 460)
    assert result["board_to_screen"]["scale_y"] == pytest.approx(351 / 240)


def test_rejects_unstable_screen_offset_and_unsupported_skew():
    bad_report = report()
    bad_report["events"][0]["screenY"] += 1
    with pytest.raises(RendererGeometryError, match="offset changed"):
        derive_live_board_screen_transform(bad_report, evidence(),
            {"x": 496, "y": 265, "width": 674, "height": 355}, (1920, 1080))
    bad_inspect = evidence()
    bad_inspect["renderer"]["canvas"]["css_matrix"]["b"] = 0.01
    with pytest.raises(RendererGeometryError, match="axis-aligned"):
        derive_live_board_screen_transform(report(), bad_inspect,
            {"x": 496, "y": 265, "width": 674, "height": 355}, (1920, 1080))
