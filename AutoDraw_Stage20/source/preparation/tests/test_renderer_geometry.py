from __future__ import annotations

import pytest

from renderer_geometry import RendererGeometryError, derive_live_board_screen_transform


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
