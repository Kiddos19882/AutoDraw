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


def detect_board_bounds_from_screenshots(
    before_rgb: Any,
    after_rgb: Any,
    screen_roi: dict[str, int],
    *,
    color_tolerance: int = 4,
    search_padding: int = 40,
) -> dict[str, Any]:
    """Find the board-color component in same-run full-screen before/after captures.

    The calibrated ROI is used only as a search window. Board bounds and scale are
    measured from screenshot pixels, not inferred from the ROI dimensions.
    """
    import cv2
    import numpy as np

    before = np.asarray(before_rgb)
    after = np.asarray(after_rgb)
    if before.ndim != 3 or before.shape[2] != 3 or before.dtype != np.uint8:
        raise RendererGeometryError("Before screenshot must be an RGB uint8 image.")
    if after.shape != before.shape or after.dtype != np.uint8:
        raise RendererGeometryError("Before/after screenshots must have identical RGB uint8 dimensions.")
    if not isinstance(screen_roi, dict):
        raise RendererGeometryError("A calibrated screen ROI is required.")
    values = {}
    for key in ("x", "y", "width", "height"):
        value = screen_roi.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise RendererGeometryError(f"screen_roi.{key} must be an integer.")
        values[key] = value
    x, y, width, height = (values[key] for key in ("x", "y", "width", "height"))
    if x < 0 or y < 0 or width < 2 or height < 2:
        raise RendererGeometryError("Screen ROI must be a positive in-screen rectangle.")
    image_height, image_width = before.shape[:2]
    if x + width > image_width or y + height > image_height:
        raise RendererGeometryError("Screen ROI exceeds screenshot dimensions.")
    if isinstance(color_tolerance, bool) or not isinstance(color_tolerance, int) or not 0 <= color_tolerance <= 32:
        raise RendererGeometryError("Color tolerance must be an integer from 0 to 32.")
    if isinstance(search_padding, bool) or not isinstance(search_padding, int) or not 0 <= search_padding <= 256:
        raise RendererGeometryError("Search padding must be an integer from 0 to 256.")

    center_x, center_y = x + width // 2, y + height // 2
    seed_patch = before[center_y - 4:center_y + 5, center_x - 4:center_x + 5]
    if seed_patch.size == 0:
        raise RendererGeometryError("Board-color seed patch is outside the screenshot.")
    board_color = np.median(seed_patch.reshape(-1, 3), axis=0)
    search_left = max(0, x - search_padding)
    search_top = max(0, y - search_padding)
    search_right = min(image_width, x + width + search_padding)
    search_bottom = min(image_height, y + height + search_padding)

    def component(image: Any, seed: tuple[int, int]) -> dict[str, Any]:
        crop = image[search_top:search_bottom, search_left:search_right].astype(np.int16)
        difference = np.max(np.abs(crop - board_color), axis=2)
        mask = (difference <= color_tolerance).astype(np.uint8)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        seed_x, seed_y = seed
        label = int(labels[seed_y - search_top, seed_x - search_left])
        if label <= 0:
            raise RendererGeometryError("Screenshot seed does not belong to a board-color component.")
        left, top, box_width, box_height, area = (int(value) for value in stats[label])
        if box_width < 2 or box_height < 2:
            raise RendererGeometryError("Detected board component is too small.")
        return {
            "bounds": {
                "x": left + search_left, "y": top + search_top,
                "width": box_width, "height": box_height,
            },
            "area_pixels": area,
            "bbox_area_pixels": box_width * box_height,
            "fill_fraction": area / (box_width * box_height),
            "component_count_in_search_window": int(count),
        }

    before_component = component(before, (center_x, center_y))
    after_candidates = (
        (center_x, center_y - 30), (center_x, center_y + 30),
        (center_x - 30, center_y), (center_x + 30, center_y),
        (center_x - 30, center_y - 30), (center_x + 30, center_y + 30),
    )
    after_seed = next((
        point for point in after_candidates
        if 0 <= point[0] < image_width and 0 <= point[1] < image_height
        and np.max(np.abs(after[point[1], point[0]].astype(np.int16) - board_color)) <= color_tolerance
    ), None)
    if after_seed is None:
        raise RendererGeometryError("No unpainted board-color seed remains in the after screenshot.")
    after_component = component(after, after_seed)
    bounds = before_component["bounds"]
    if bounds != after_component["bounds"]:
        raise RendererGeometryError("Board bounds changed between before and after screenshots.")

    aspect_ratio = bounds["width"] / bounds["height"]
    expected_aspect = 460 / 240
    aspect_error = aspect_ratio / expected_aspect - 1
    if abs(aspect_error) > 0.005:
        raise RendererGeometryError("Detected board bounds disagree with the 460×240 logical aspect ratio.")
    if before_component["fill_fraction"] < 0.995:
        raise RendererGeometryError("Blank screenshot board component is fragmented.")
    if after_component["fill_fraction"] < 0.90:
        raise RendererGeometryError("After screenshot board component is too fragmented to verify.")

    return {
        "method": "same_run_blank_after_board_color_component",
        "bounds": bounds,
        "board_color_rgb": [float(value) for value in board_color],
        "color_tolerance": color_tolerance,
        "search_padding_px": search_padding,
        "before_component": before_component,
        "after_component": after_component,
        "after_seed": {"x": after_seed[0], "y": after_seed[1]},
        "logical_board_size": {"width": 460, "height": 240},
        "scale_px_per_logical_px": {
            "x": bounds["width"] / 460,
            "y": bounds["height"] / 240,
        },
        "aspect_ratio": aspect_ratio,
        "aspect_ratio_relative_error": aspect_error,
    }


def derive_live_board_screen_transform(
    monitor_report: dict[str, Any],
    inspect_evidence: dict[str, Any],
    screen_roi: dict[str, int],
    screenshot_size: tuple[int, int],
    *,
    screenshot_board_bounds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fit X from same-run telemetry; optionally derive Y from same-run screenshot bounds."""
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
    sy_inspect = _finite(renderer.get("canvas_scale_y"), "canvas_scale_y") * d
    stage_w, stage_h = _finite(stage.get("width"), "stage.width"), _finite(stage.get("height"), "stage.height")
    rect_left, rect_top = _finite(rect.get("left"), "canvas.rect.left"), _finite(rect.get("top"), "canvas.rect.top")
    if abs(_finite(rect.get("width"), "canvas.rect.width") - stage_w * sx_inspect) > 1:
        raise RendererGeometryError("Canvas width disagrees with Stage/CSS scale.")
    if abs(_finite(rect.get("height"), "canvas.rect.height") - stage_h * sy_inspect) > 1:
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

    inspect_y_origin = rect_top + stage_top * sy_inspect + offset_y
    if len({round(float(e["boardY"]), 6) for e in samples}) != 1:
        raise RendererGeometryError("This audit expects a horizontal run; add a separately validated Y fit.")
    sample = samples[len(samples) // 2]

    screenshot_cross_check = None
    if screenshot_board_bounds is None:
        y_origin = inspect_y_origin
        sy = sy_inspect
        vertical_scale_source = "inspect_css_transform_single_horizontal_trajectory"
        method = "same_run_monitor_x_fit_plus_inspect_css_y_transform"
        validation_status = "X_and_client_screen_offset_cross_checked; Y_scale_inspect_only"
    else:
        if not isinstance(screenshot_board_bounds, dict):
            raise RendererGeometryError("Screenshot board bounds must be an object.")
        bounds_x = _finite(screenshot_board_bounds.get("x"), "screenshot_board_bounds.x")
        bounds_y = _finite(screenshot_board_bounds.get("y"), "screenshot_board_bounds.y")
        bounds_width = _finite(screenshot_board_bounds.get("width"), "screenshot_board_bounds.width")
        bounds_height = _finite(screenshot_board_bounds.get("height"), "screenshot_board_bounds.height")
        if bounds_width < 2 or bounds_height < 2:
            raise RendererGeometryError("Screenshot board bounds must be at least 2×2 pixels.")
        screenshot_sx = bounds_width / 460
        screenshot_sy = bounds_height / 240
        if abs(fit_x["origin"] - bounds_x) > 1.0:
            raise RendererGeometryError("Monitor X origin disagrees with screenshot board bounds.")
        if abs(fit_x["scale"] - screenshot_sx) / screenshot_sx > 0.002:
            raise RendererGeometryError("Monitor X scale disagrees with screenshot board bounds.")
        if abs(inspect_y_origin - bounds_y) > 1.0:
            raise RendererGeometryError("Inspect Y origin disagrees with screenshot board bounds.")
        if abs(sy_inspect - screenshot_sy) / screenshot_sy > 0.002:
            raise RendererGeometryError("Inspect Y scale disagrees with screenshot board bounds.")
        y_origin = bounds_y
        sy = screenshot_sy
        vertical_scale_source = "same_run_full_screen_blank_after_board_bounds"
        method = "same_run_monitor_x_fit_plus_screenshot_board_bounds_y"
        validation_status = "X_monitor_fit_cross_checked_with_screenshot_bounds; Y_screenshot_bounds_cross_checked_with_inspect"
        screenshot_cross_check = {
            "bounds": {
                "x": bounds_x, "y": bounds_y,
                "width": bounds_width, "height": bounds_height,
            },
            "scale": {"x": screenshot_sx, "y": screenshot_sy},
            "monitor_x_origin_difference_px": fit_x["origin"] - bounds_x,
            "monitor_x_scale_relative_difference": fit_x["scale"] / screenshot_sx - 1,
            "inspect_y_origin_difference_px": inspect_y_origin - bounds_y,
            "inspect_y_scale_relative_difference": sy_inspect / screenshot_sy - 1,
        }

    y_residual = y_origin + float(sample["boardY"]) * sy - float(sample["screenY"])
    if abs(y_residual) > 0.75:
        source = "Screenshot-derived" if screenshot_board_bounds is not None else "Inspect-derived"
        raise RendererGeometryError(f"{source} Y transform does not reproduce the live sample.")

    x, y, width, height = (int(screen_roi[k]) for k in ("x", "y", "width", "height"))
    if width < 2 or height < 2:
        raise RendererGeometryError("ROI must be at least 2×2 pixels.")
    right = fit_x["origin"] + fit_x["scale"] * 460
    bottom = y_origin + sy * 240
    matrix = [[fit_x["scale"] / 3, 0.0, fit_x["origin"] - x],
              [0.0, sy / 3, y_origin - y]]
    return {
        "coordinate_system": "primary_screen_screenshot_pixels",
        "method": method,
        "validation_status": validation_status,
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
        "vertical_scale_source": vertical_scale_source,
        "vertical_sample_residual_px": y_residual,
        "screenshot_bounds_cross_check": screenshot_cross_check,
        "roi": {"x": x, "y": y, "width": width, "height": height},
        "roi_alignment": {
            "board_origin_in_roi": {"x": fit_x["origin"] - x, "y": y_origin - y},
            "board_size_px": {"width": right - fit_x["origin"], "height": bottom - y_origin},
            "roi_scale": {"x": (width - 1) / 460, "y": (height - 1) / 240},
            "board_edge_overrun_px": {"right": right - (x + width), "bottom": bottom - (y + height)},
        },
        "inspect_scale": {"x": sx_inspect, "y": sy_inspect},
        "inspect_x_origin": inspect_x_origin,
        "inspect_x_origin_difference_px": fit_x["origin"] - inspect_x_origin,
        "matrix_source_raster_to_roi": matrix,
        "source_raster_scale": 3,
    }
