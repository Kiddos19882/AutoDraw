from __future__ import annotations

"""Independent board-to-screen transform from Game Monitor + inspect evidence."""

from math import isfinite
from statistics import median
from typing import Any


class RendererGeometryError(ValueError):
    """Evidence is insufficient or internally inconsistent."""


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise RendererGeometryError(f"{label} must be a finite number.")
    return float(value)


def _fit(source: list[float], target: list[float]) -> dict[str, float]:
    if len(source) != len(target) or len(source) < 3:
        raise RendererGeometryError("At least three paired samples are required.")
    mx, my = sum(source) / len(source), sum(target) / len(target)
    variance = sum((x - mx) ** 2 for x in source)
    if variance <= 1e-9:
        raise RendererGeometryError("Horizontal samples do not span the board.")
    scale = sum((x - mx) * (y - my) for x, y in zip(source, target)) / variance
    origin = my - scale * mx
    residuals = [y - (origin + scale * x) for x, y in zip(source, target)]
    return {
        "scale": scale, "origin": origin,
        "rmse_px": (sum(r * r for r in residuals) / len(residuals)) ** 0.5,
        "max_abs_residual_px": max(abs(r) for r in residuals),
        "sample_count": float(len(source)),
    }


def derive_live_board_screen_transform(
    monitor_report: dict[str, Any],
    inspect_evidence: dict[str, Any],
    screen_roi: dict[str, int],
    screenshot_size: tuple[int, int],
) -> dict[str, Any]:
    """Fit X from same-run pointer telemetry; derive Y from an attested axis-aligned inspect."""
    if monitor_report.get("record_type") != "autodraw_game_monitor_run":
        raise RendererGeometryError("A complete Game Monitor run report is required.")
    if inspect_evidence.get("provenance", {}).get("same_screen_as_live_capture") is not True:
        raise RendererGeometryError("inspect evidence is not attested for this screen.")
    screen, board, renderer = (
        inspect_evidence.get("screen", {}), inspect_evidence.get("board", {}),
        inspect_evidence.get("renderer", {}),
    )
    if (board.get("logical_width"), board.get("logical_height")) != (460, 240):
        raise RendererGeometryError("Expected a 460×240 logical board.")
    screen_size = (int(screen.get("width", 0)), int(screen.get("height", 0)))
    if tuple(screenshot_size) != screen_size:
        raise RendererGeometryError("Screenshot and desktop screen dimensions differ.")
    if screen.get("windows_scale_percent") != 100 or screen.get("device_pixel_ratio") != 1:
        raise RendererGeometryError("Screen-to-screenshot identity requires Windows scale 100% and DPR 1.")

    stage, canvas = renderer.get("stage", {}), renderer.get("canvas", {})
    rect, css, origin = canvas.get("rect", {}), canvas.get("css_matrix", {}), canvas.get("transform_origin", {})
    corners = renderer.get("board_stage_corners", {})
    tl, br = corners.get("top_left", {}), corners.get("bottom_right", {})
    a, b, c, d = (_finite(css.get(k), f"css_matrix.{k}") for k in ("a", "b", "c", "d"))
    tx, ty = (_finite(css.get(k), f"css_matrix.{k}") for k in ("tx", "ty"))
    ox, oy = (_finite(origin.get(k), f"transform_origin.{k}") for k in ("x", "y"))
    if abs(b) > 1e-9 or abs(c) > 1e-9 or a <= 0 or d <= 0 or abs(ox) > 1e-9 or abs(oy) > 1e-9:
        raise RendererGeometryError("Only positive axis-aligned CSS transforms with origin (0,0) are supported.")
    if abs(tx) > 1e-9 or abs(ty) > 1e-9:
        raise RendererGeometryError("CSS translation needs an independently validated content quad.")

    sx_inspect = _finite(renderer.get("canvas_scale_x"), "canvas_scale_x") * a
    sy = _finite(renderer.get("canvas_scale_y"), "canvas_scale_y") * d
    stage_w, stage_h = _finite(stage.get("width"), "stage.width"), _finite(stage.get("height"), "stage.height")
    rect_left, rect_top = _finite(rect.get("left"), "canvas.rect.left"), _finite(rect.get("top"), "canvas.rect.top")
    if abs(_finite(rect.get("width"), "canvas.rect.width") - stage_w * sx_inspect) > 1:
        raise RendererGeometryError("Canvas width disagrees with Stage/CSS scale.")
    if abs(_finite(rect.get("height"), "canvas.rect.height") - stage_h * sy) > 1:
        raise RendererGeometryError("Canvas height disagrees with Stage/CSS scale.")
    stage_left, stage_top = _finite(tl.get("x"), "board.top_left.x"), _finite(tl.get("y"), "board.top_left.y")
    stage_right, stage_bottom = _finite(br.get("x"), "board.bottom_right.x"), _finite(br.get("y"), "board.bottom_right.y")
    if abs(stage_right - stage_left - 460) > 1e-6 or abs(stage_bottom - stage_top - 240) > 1e-6:
        raise RendererGeometryError("Board stage corners do not match 460×240 logical dimensions.")

    samples = [
        e for e in monitor_report.get("events", [])
        if isinstance(e, dict) and e.get("type") == "MOUSE_MOVE_SAMPLE"
        and all(isinstance(e.get(k), (int, float)) and not isinstance(e.get(k), bool)
                for k in ("screenX", "screenY", "clientX", "clientY", "boardX", "boardY"))
    ]
    if len(samples) < 3:
        raise RendererGeometryError("At least three same-run mouse samples are required.")
    dx = [float(e["screenX"] - e["clientX"]) for e in samples]
    dy = [float(e["screenY"] - e["clientY"]) for e in samples]
    if max(dx) - min(dx) > 0.01 or max(dy) - min(dy) > 0.01:
        raise RendererGeometryError("Client-to-screen offset changed during the run.")
    offset_x, offset_y = median(dx), median(dy)

    fit_x = _fit([float(e["boardX"]) for e in samples], [float(e["screenX"]) for e in samples])
    inspect_x_origin = rect_left + stage_left * sx_inspect + offset_x
    if abs(fit_x["origin"] - inspect_x_origin) > 0.5:
        raise RendererGeometryError("Monitor horizontal origin disagrees with inspect.")
    if abs(fit_x["scale"] - sx_inspect) / sx_inspect > 0.002:
        raise RendererGeometryError("Monitor horizontal scale disagrees with inspect.")

    y_origin = rect_top + stage_top * sy + offset_y
    if len({round(float(e["boardY"]), 6) for e in samples}) != 1:
        raise RendererGeometryError("This audit expects a horizontal run; add a separately validated Y fit.")
    sample = samples[len(samples) // 2]
    y_residual = y_origin + float(sample["boardY"]) * sy - float(sample["screenY"])
    if abs(y_residual) > 0.75:
        raise RendererGeometryError("Inspect-derived Y transform does not reproduce the live sample.")

    x, y, width, height = (int(screen_roi[k]) for k in ("x", "y", "width", "height"))
    if width < 2 or height < 2:
        raise RendererGeometryError("ROI must be at least 2×2 pixels.")
    right = fit_x["origin"] + fit_x["scale"] * 460
    bottom = y_origin + sy * 240
    matrix = [[fit_x["scale"] / 3, 0.0, fit_x["origin"] - x],
              [0.0, sy / 3, y_origin - y]]
    return {
        "coordinate_system": "primary_screen_screenshot_pixels",
        "method": "same_run_monitor_x_fit_plus_inspect_css_y_transform",
        "validation_status": "X_and_client_screen_offset_cross_checked; Y_scale_inspect_only",
        "board_to_screen": {
            "origin_x": fit_x["origin"], "origin_y": y_origin,
            "scale_x": fit_x["scale"], "scale_y": sy,
            "corners": {
                "top_left": [fit_x["origin"], y_origin],
                "bottom_right": [right, bottom],
            },
        },
        "screen_offset_from_client": {"x": offset_x, "y": offset_y, "sample_count": len(samples)},
        "horizontal_fit": fit_x,
        "vertical_scale_source": "inspect_css_transform_single_horizontal_trajectory",
        "vertical_sample_residual_px": y_residual,
        "roi": {"x": x, "y": y, "width": width, "height": height},
        "roi_alignment": {
            "board_origin_in_roi": {"x": fit_x["origin"] - x, "y": y_origin - y},
            "board_size_px": {"width": right - fit_x["origin"], "height": bottom - y_origin},
            "roi_scale": {"x": (width - 1) / 460, "y": (height - 1) / 240},
            "board_edge_overrun_px": {"right": right - (x + width), "bottom": bottom - (y + height)},
        },
        "inspect_scale": {"x": sx_inspect, "y": sy},
        "inspect_x_origin": inspect_x_origin,
        "inspect_x_origin_difference_px": fit_x["origin"] - inspect_x_origin,
        "matrix_source_raster_to_roi": matrix,
        "source_raster_scale": 3,
    }
