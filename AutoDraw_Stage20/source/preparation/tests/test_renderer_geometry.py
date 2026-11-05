from __future__ import annotations

import numpy as np
import pytest

from renderer_geometry import (
    crop_mask_to_board_bounds,
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



def _same_run_geometry_fixture():
    geometry = {
        "inspectionMode": "read_only", "engineVersion": "5.4.1", "renderMode": "webgl",
        "windowGeometry": {"screenWidth": 1920, "screenHeight": 1080, "innerWidth": 1920, "innerHeight": 877},
        "canvasScaleFactor": 2, "canvasScaleX": 3, "canvasScaleY": 3,
        "devicePixelRatio": 1, "visualViewportScale": 1,
        "playerCount": 1,
        "players": [{
            "playerFound": True, "playerMatchesStage": True,
            "stage": {"width": 1314, "height": 600},
            "canvas": {
                "rect": {"left": 0, "top": -0.5, "width": 1920, "height": 878},
                "style": {
                    "computedTransform": "matrix(0.487062, 0, 0, 0.487778, 0, 0)",
                    "computedTransformOrigin": "0px 0px",
                },
            },
            "boardStageCorners": {
                "topLeft": {"x": 340.7916660308838, "y": 72},
                "bottomRight": {"x": 800.7916660308838, "y": 312},
            },
        }],
        "boardDetected": True, "boardLogicalSize": {"width": 460, "height": 240},
    }
    experiment = {
        "experiment_id": "exp-vertical", "test_case": "paired_renderer_vertical_single_stroke",
        "game_monitor_summary": {
            "run_id": "run-vertical", "session_id": "session-vertical",
            "autodraw_experiment_id": "exp-vertical",
        },
        "phases": {
            "before_draw": {"screen_size": {"width": 1920, "height": 1080}},
            "after_draw": {"screen_size": {"width": 1920, "height": 1080}},
        },
    }
    monitor = {
        "record_type": "autodraw_game_monitor_run",
        "run_id": "run-vertical", "session_id": "session-vertical",
        "autodraw_experiment_id": "exp-vertical",
        "renderer_geometry_at_start": geometry, "renderer_geometry_at_end": geometry,
        "renderer_geometry_updated_at_start_utc": "2026-11-05T16:24:11.865+00:00",
        "renderer_geometry_updated_at_end_utc": "2026-11-05T16:24:11.865+00:00",
        "renderer_geometry_updates": [], "renderer_geometry_update_overflow_count": 0,
        "events": [],
    }
    return experiment, monitor


def test_same_run_geometry_audit_input_builds_from_exact_monitor_snapshot():
    from renderer_geometry import build_same_run_geometry_audit_input

    experiment, monitor = _same_run_geometry_fixture()
    audit = build_same_run_geometry_audit_input(experiment, monitor, (1920, 1080))
    assert audit["source_run"] == {
        "experiment_id": "exp-vertical", "run_id": "run-vertical", "session_id": "session-vertical",
    }
    assert audit["provenance"]["same_run"] is True
    assert audit["screen"]["screenshot_pixel_mapping"]["verified"] is True
    assert audit["renderer"]["stage"] == {"width": 1314, "height": 600}
    assert audit["renderer"]["canvas"]["css_matrix"]["a"] == pytest.approx(0.487062)
    assert audit["renderer"]["board_stage_corners"]["bottom_right"] == {"x": 800.7916660308838, "y": 312}


def test_same_run_geometry_audit_rejects_wrong_run_or_session():
    from renderer_geometry import build_same_run_geometry_audit_input

    experiment, monitor = _same_run_geometry_fixture()
    monitor["run_id"] = "other-run"
    with pytest.raises(RendererGeometryError, match="run/session"):
        build_same_run_geometry_audit_input(experiment, monitor, (1920, 1080))


def test_same_run_geometry_audit_rejects_changed_geometry_and_updates():
    from renderer_geometry import build_same_run_geometry_audit_input

    experiment, monitor = _same_run_geometry_fixture()
    monitor["renderer_geometry_at_end"] = dict(monitor["renderer_geometry_at_start"])
    monitor["renderer_geometry_at_end"]["windowGeometry"] = {"screenWidth": 1280, "screenHeight": 720}
    with pytest.raises(RendererGeometryError, match="changed"):
        build_same_run_geometry_audit_input(experiment, monitor, (1920, 1080))

    experiment, monitor = _same_run_geometry_fixture()
    monitor["renderer_geometry_updates"] = [{"updated_at_utc": "later"}]
    with pytest.raises(RendererGeometryError, match="updates occurred"):
        build_same_run_geometry_audit_input(experiment, monitor, (1920, 1080))


def test_same_run_geometry_audit_rejects_screen_size_mismatch():
    from renderer_geometry import build_same_run_geometry_audit_input

    experiment, monitor = _same_run_geometry_fixture()
    with pytest.raises(RendererGeometryError, match="PNG dimensions"):
        build_same_run_geometry_audit_input(experiment, monitor, (1600, 900))


def test_same_run_screen_metrics_can_attest_pixel_mapping_without_os_scale_profile():
    evidence_without_os_scale = evidence()
    evidence_without_os_scale["screen"].pop("windows_scale_percent")
    evidence_without_os_scale["screen"]["screenshot_pixel_mapping"] = {
        "verified": True,
        "method": "same_run_window_screen_metrics_equal_full_screen_png_dimensions",
        "scale_x": 1.0, "scale_y": 1.0,
        "screenshot_width_px": 1920, "screenshot_height_px": 1080,
    }
    result = derive_live_board_screen_transform(
        report(), evidence_without_os_scale,
        {"x": 496, "y": 265, "width": 674, "height": 355}, (1920, 1080),
    )
    assert result["board_to_screen"]["scale_x"] == pytest.approx(1.461214, abs=1e-5)



def test_board_renderer_comparison_excludes_pixels_outside_detected_board_bounds():
    full_screen = np.zeros((1080, 1920), dtype=bool)
    full_screen[268:619, 498:1170] = True
    full_screen[619, 592:609] = True  # 17 changed pixels below the BoardPane, inside the larger ROI.

    board_mask, outside_roi_mask = crop_mask_to_board_bounds(
        full_screen,
        {"x": 498, "y": 268, "width": 672, "height": 351},
        {"x": 496, "y": 265, "width": 674, "height": 355},
    )

    assert board_mask.shape == (351, 672)
    assert int(board_mask.sum()) == 672 * 351
    assert outside_roi_mask.shape == (355, 674)
    assert int(outside_roi_mask.sum()) == 17


def test_board_renderer_comparison_rejects_bounds_outside_roi_or_screen():
    mask = np.zeros((1080, 1920), dtype=bool)
    with pytest.raises(RendererGeometryError, match="contained"):
        crop_mask_to_board_bounds(
            mask,
            {"x": 495, "y": 268, "width": 672, "height": 351},
            {"x": 496, "y": 265, "width": 674, "height": 355},
        )
    with pytest.raises(RendererGeometryError, match="exceeds"):
        crop_mask_to_board_bounds(
            mask,
            {"x": 1800, "y": 268, "width": 672, "height": 351},
            {"x": 496, "y": 265, "width": 674, "height": 355},
        )



def test_board_renderer_comparison_crops_roi_local_diagnostic_mask():
    roi_mask = np.zeros((355, 674), dtype=np.uint8)
    roi_mask[3:354, 2:674] = 255

    board_mask, outside_roi_mask = crop_mask_to_board_bounds(
        roi_mask,
        {"x": 2, "y": 3, "width": 672, "height": 351},
        {"x": 0, "y": 0, "width": 674, "height": 355},
    )

    assert board_mask.shape == (351, 672)
    assert int(board_mask.sum()) == 255 * 672 * 351
    assert int(outside_roi_mask.sum()) == 0

def test_browser_compositor_transform_uses_independent_board_to_screen_not_inspect_css():
    from renderer_geometry import build_browser_compositor_transform

    points = [(230, 20 + index * 5) for index in range(40)]
    geometry = derive_live_board_screen_transform(
        _axis_report(points), evidence(),
        {"x": 496, "y": 265, "width": 674, "height": 355}, (1920, 1080),
        screenshot_board_bounds={"x": 498, "y": 268, "width": 672, "height": 351},
    )
    compositor = build_browser_compositor_transform(geometry)

    assert compositor["source"] == "independent_board_to_screen"
    assert compositor["source_raster_scale"] == 3
    assert compositor["board_origin_screen_px"]["x"] == pytest.approx(498)
    assert compositor["board_origin_screen_px"]["y"] == pytest.approx(268)
    assert compositor["css_matrix"]["a"] == pytest.approx((672 / 460) / 3)
    assert compositor["css_matrix"]["b"] == 0.0
    assert compositor["css_matrix"]["c"] == 0.0
    assert compositor["css_matrix"]["d"] == pytest.approx((351 / 240) / 3)
    assert compositor["css_matrix"]["tx"] == 0.0
    assert compositor["css_matrix"]["ty"] == 0.0
    assert compositor["board_origin_screen_px"]["x"] != pytest.approx(geometry["inspect_origin"]["x"])
    assert compositor["css_matrix"]["a"] != pytest.approx(evidence()["renderer"]["canvas"]["css_matrix"]["a"])


@pytest.mark.parametrize("geometry", [
    {},
    {"board_to_screen": {}, "source_raster_scale": 3},
    {"board_to_screen": {"origin_x": 1, "origin_y": 2, "scale_x": 0, "scale_y": 1}, "source_raster_scale": 3},
    {"board_to_screen": {"origin_x": 1, "origin_y": 2, "scale_x": 1, "scale_y": 1}, "source_raster_scale": 0},
])
def test_browser_compositor_transform_rejects_incomplete_or_invalid_geometry(geometry):
    from renderer_geometry import build_browser_compositor_transform

    with pytest.raises(RendererGeometryError):
        build_browser_compositor_transform(geometry)


def test_browser_compositor_html_uses_eager_static_overlay_image(tmp_path):
    import importlib.util
    from pathlib import Path

    script_path = Path(__file__).resolve().parents[3] / "tests" / "compare_live_renderer_reference.py"
    spec = importlib.util.spec_from_file_location("compare_live_renderer_reference_test_module", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    html = module._browser_composite_html(
        tmp_path / "baseline capture.png",
        tmp_path / "offline raster.png",
        (1920, 1080),
        {"x": 498.0, "y": 268.0},
        {"a": 0.487, "b": 0.0, "c": 0.0, "d": 0.4875, "tx": 0.0, "ty": 0.0},
    )

    assert '<canvas id="board-overlay"' in html
    assert '<img id="offline-source"' in html
    assert 'loading="eager"' in html
    assert 'decoding="sync"' in html
    assert 'onload="const canvas=' in html
    assert 'context.drawImage(this,0,0,1380,720)' in html
    assert "transform:matrix(0.487,0,0,0.4875,0,0)" in html
    assert ".decode()" not in html
    assert "requestAnimationFrame" not in html
