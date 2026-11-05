from __future__ import annotations

"""Independent board-to-screen transform from Game Monitor + inspect evidence."""

from math import isfinite
from statistics import median
import re
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



def _parse_css_matrix(value: Any) -> dict[str, float]:
    if not isinstance(value, str):
        raise RendererGeometryError("Same-run computed CSS transform must be a matrix() string.")
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    pattern = r"\s*matrix\(\s*" + r"\s*,\s*".join([f"({number})"] * 6) + r"\s*\)\s*"
    match = re.fullmatch(pattern, value)
    if not match:
        raise RendererGeometryError("Only a six-value CSS matrix() transform is supported.")
    a, b, c, d, tx, ty = (float(item) for item in match.groups())
    if not all(isfinite(item) for item in (a, b, c, d, tx, ty)):
        raise RendererGeometryError("CSS matrix() values must be finite.")
    return {"a": a, "b": b, "c": c, "d": d, "tx": tx, "ty": ty}


def _parse_css_transform_origin(value: Any) -> dict[str, float]:
    if not isinstance(value, str):
        raise RendererGeometryError("Same-run computed transform-origin must be a CSS string.")
    matches = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value)
    if len(matches) < 2:
        raise RendererGeometryError("Computed transform-origin must expose two coordinates.")
    return {"x": float(matches[0]), "y": float(matches[1])}


def build_same_run_geometry_audit_input(
    experiment: dict[str, Any],
    monitor_report: dict[str, Any],
    screenshot_size: tuple[int, int],
) -> dict[str, Any]:
    """Normalize the exact run-bound Game Monitor renderer snapshot for audit."""
    summary = experiment.get("game_monitor_summary", {})
    run_id, session_id = summary.get("run_id"), summary.get("session_id")
    experiment_id = experiment.get("experiment_id")
    if not all(isinstance(value, str) and value for value in (run_id, session_id, experiment_id)):
        raise RendererGeometryError("Experiment run/session/experiment provenance is incomplete.")
    if monitor_report.get("record_type") != "autodraw_game_monitor_run":
        raise RendererGeometryError("A complete Game Monitor run report is required.")
    if monitor_report.get("run_id") != run_id or monitor_report.get("session_id") != session_id:
        raise RendererGeometryError("Game Monitor report is not bound to this experiment run/session.")
    if monitor_report.get("autodraw_experiment_id") != experiment_id:
        raise RendererGeometryError("Game Monitor report is not bound to this experiment ID.")

    geometry_start = monitor_report.get("renderer_geometry_at_start")
    geometry_end = monitor_report.get("renderer_geometry_at_end")
    if not isinstance(geometry_start, dict) or not isinstance(geometry_end, dict):
        raise RendererGeometryError("Same-run renderer geometry snapshots are missing.")
    if geometry_start != geometry_end:
        raise RendererGeometryError("Renderer geometry changed between run start and end.")
    if monitor_report.get("renderer_geometry_updates") != []:
        raise RendererGeometryError("Renderer geometry updates occurred during the run.")
    if monitor_report.get("renderer_geometry_update_overflow_count") != 0:
        raise RendererGeometryError("Renderer geometry update telemetry overflowed.")
    updated_start = monitor_report.get("renderer_geometry_updated_at_start_utc")
    updated_end = monitor_report.get("renderer_geometry_updated_at_end_utc")
    if not isinstance(updated_start, str) or not updated_start or updated_start != updated_end:
        raise RendererGeometryError("Renderer geometry snapshot timestamps are missing or inconsistent.")
    if geometry_start.get("inspectionMode") != "read_only":
        raise RendererGeometryError("Renderer geometry must come from a read-only inspect snapshot.")
    if geometry_start.get("engineVersion") != "5.4.1" or geometry_start.get("renderMode") != "webgl":
        raise RendererGeometryError("Unexpected live renderer engine/version/mode.")
    if geometry_start.get("boardDetected") is not True:
        raise RendererGeometryError("Game Monitor did not detect the BoardPane.")

    players = geometry_start.get("players")
    if geometry_start.get("playerCount") != 1 or not isinstance(players, list) or len(players) != 1:
        raise RendererGeometryError("Exactly one game renderer player is required.")
    player = players[0]
    if player.get("playerFound") is not True or player.get("playerMatchesStage") is not True:
        raise RendererGeometryError("Game renderer player does not match the inspected Stage.")

    window = geometry_start.get("windowGeometry", {})
    screen_width, screen_height = window.get("screenWidth"), window.get("screenHeight")
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0
           for value in (screen_width, screen_height)):
        raise RendererGeometryError("Same-run window.screen dimensions are unavailable.")
    if screenshot_size != (screen_width, screen_height):
        raise RendererGeometryError("Full-screen PNG dimensions differ from same-run window.screen metrics.")
    phases = experiment.get("phases", {})
    expected_size = {"width": screen_width, "height": screen_height}
    if phases.get("before_draw", {}).get("screen_size") != expected_size:
        raise RendererGeometryError("Experiment before-draw screen metadata differs from same-run window.screen.")
    if phases.get("after_draw", {}).get("screen_size") != expected_size:
        raise RendererGeometryError("Experiment after-draw screen metadata differs from same-run window.screen.")

    dpr = _finite(geometry_start.get("devicePixelRatio"), "devicePixelRatio")
    viewport_scale = _finite(geometry_start.get("visualViewportScale"), "visualViewportScale")
    if abs(dpr - 1.0) > 1e-9 or abs(viewport_scale - 1.0) > 1e-9:
        raise RendererGeometryError("Screen pixel mapping requires devicePixelRatio and visualViewportScale equal to 1.")
    scale_x = _finite(geometry_start.get("canvasScaleX"), "canvasScaleX")
    scale_y = _finite(geometry_start.get("canvasScaleY"), "canvasScaleY")
    if abs(scale_x - 3.0) > 1e-9 or abs(scale_y - 3.0) > 1e-9:
        raise RendererGeometryError("Expected the paired renderer's 3× logical raster scale.")
    if geometry_start.get("canvasScaleFactor") != 2:
        raise RendererGeometryError("Unexpected Egret canvas scale factor.")

    logical = geometry_start.get("boardLogicalSize", {})
    if logical != {"width": 460, "height": 240}:
        raise RendererGeometryError("Same-run BoardPane logical bounds must be 460×240.")
    corners = player.get("boardStageCorners", geometry_start.get("boardStageCorners", {}))
    top_left, bottom_right = corners.get("topLeft"), corners.get("bottomRight")
    if not isinstance(top_left, dict) or not isinstance(bottom_right, dict):
        raise RendererGeometryError("Same-run BoardPane stage corners are missing.")
    stage = player.get("stage", {})
    canvas = player.get("canvas", {})
    rect = canvas.get("rect", {})
    style = canvas.get("style", {})
    matrix = _parse_css_matrix(style.get("computedTransform"))
    transform_origin = _parse_css_transform_origin(
        style.get("computedTransformOrigin", style.get("transformOrigin"))
    )

    return {
        "schema_version": 1,
        "record_type": "autodraw_board_screen_geometry_audit_input",
        "provenance": {
            "inspect_source": "renderer_geometry_at_start from the exact Game Monitor run",
            "same_screen_as_live_capture": True,
            "same_run": True,
            "session_binding": "exact experiment_id/run_id/session_id match; start/end geometry snapshots identical; zero geometry updates and overflow",
            "geometry_snapshot_updated_at_utc": updated_start,
        },
        "source_run": {"experiment_id": experiment_id, "run_id": run_id, "session_id": session_id},
        "screen": {
            "width": screen_width,
            "height": screen_height,
            "device_pixel_ratio": dpr,
            "visual_viewport_scale": viewport_scale,
            "screenshot_pixel_mapping": {
                "verified": True,
                "method": "same_run_window_screen_metrics_equal_full_screen_png_dimensions",
                "scale_x": 1.0,
                "scale_y": 1.0,
                "screenshot_width_px": screenshot_size[0],
                "screenshot_height_px": screenshot_size[1],
            },
        },
        "board": {"logical_width": logical["width"], "logical_height": logical["height"]},
        "renderer": {
            "canvas_scale_x": scale_x,
            "canvas_scale_y": scale_y,
            "stage": {"width": stage.get("width"), "height": stage.get("height")},
            "canvas": {
                "rect": {key: rect.get(key) for key in ("left", "top", "width", "height")},
                "css_matrix": matrix,
                "transform_origin": transform_origin,
            },
            "board_stage_corners": {
                "top_left": {"x": top_left.get("x"), "y": top_left.get("y")},
                "bottom_right": {"x": bottom_right.get("x"), "y": bottom_right.get("y")},
            },
        },
    }


def derive_live_board_screen_transform(
    monitor_report: dict[str, Any],
    inspect_evidence: dict[str, Any],
    screen_roi: dict[str, int],
    screenshot_size: tuple[int, int],
    *,
    screenshot_board_bounds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive each board axis from same-run telemetry when it spans that axis.

    Screenshot-derived board bounds provide an independent fallback for an axis
    that the trajectory does not span (horizontal runs do not span Y; vertical
    runs do not span X). Inspect geometry is retained as a cross-check, not as a
    substitute for missing same-run axis evidence when screenshot bounds exist.
    """
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
    if screen.get("device_pixel_ratio") != 1:
        raise RendererGeometryError("Screen-to-screenshot identity requires DPR 1.")
    if screen.get("windows_scale_percent") != 100:
        mapping = screen.get("screenshot_pixel_mapping", {})
        mapping_ok = (
            isinstance(mapping, dict)
            and mapping.get("verified") is True
            and mapping.get("method") == "same_run_window_screen_metrics_equal_full_screen_png_dimensions"
            and mapping.get("scale_x") == 1.0
            and mapping.get("scale_y") == 1.0
            and mapping.get("screenshot_width_px") == screen_size[0]
            and mapping.get("screenshot_height_px") == screen_size[1]
        )
        if not mapping_ok:
            raise RendererGeometryError(
                "Screen-to-screenshot identity requires Windows scale 100% or verified same-run 1:1 screen/PNG dimensions."
            )

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

    board_x = [float(e["boardX"]) for e in samples]
    board_y = [float(e["boardY"]) for e in samples]
    screen_x = [float(e["screenX"]) for e in samples]
    screen_y = [float(e["screenY"]) for e in samples]
    # A trajectory must span at least 20 logical pixels to independently fit an axis.
    fit_x = _fit(board_x, screen_x) if max(board_x) - min(board_x) >= 20 else None
    fit_y = _fit(board_y, screen_y) if max(board_y) - min(board_y) >= 20 else None

    inspect_x_origin = rect_left + stage_left * sx_inspect + offset_x
    inspect_y_origin = rect_top + stage_top * sy_inspect + offset_y

    bounds = None
    screenshot_sx = screenshot_sy = None
    if screenshot_board_bounds is not None:
        if not isinstance(screenshot_board_bounds, dict):
            raise RendererGeometryError("Screenshot board bounds must be an object.")
        bounds = {
            key: _finite(screenshot_board_bounds.get(key), f"screenshot_board_bounds.{key}")
            for key in ("x", "y", "width", "height")
        }
        if bounds["width"] < 2 or bounds["height"] < 2:
            raise RendererGeometryError("Screenshot board bounds must be at least 2×2 pixels.")
        screenshot_sx = bounds["width"] / 460
        screenshot_sy = bounds["height"] / 240
        if abs(inspect_x_origin - bounds["x"]) > 1.0:
            raise RendererGeometryError("Inspect X origin disagrees with screenshot board bounds.")
        if abs(inspect_y_origin - bounds["y"]) > 1.0:
            raise RendererGeometryError("Inspect Y origin disagrees with screenshot board bounds.")
        if abs(sx_inspect - screenshot_sx) / screenshot_sx > 0.002:
            raise RendererGeometryError("Inspect X scale disagrees with screenshot board bounds.")
        if abs(sy_inspect - screenshot_sy) / screenshot_sy > 0.002:
            raise RendererGeometryError("Inspect Y scale disagrees with screenshot board bounds.")

    def resolve_axis(
        axis: str,
        fit: dict[str, float] | None,
        inspect_origin: float,
        inspect_scale: float,
        screenshot_origin: float | None,
        screenshot_scale: float | None,
    ) -> tuple[float, float, str, dict[str, float] | None]:
        if fit is not None:
            if abs(fit["origin"] - inspect_origin) > 0.5:
                raise RendererGeometryError(f"Monitor {axis} origin disagrees with inspect.")
            if abs(fit["scale"] - inspect_scale) / inspect_scale > 0.002:
                raise RendererGeometryError(f"Monitor {axis} scale disagrees with inspect.")
            if screenshot_origin is not None and abs(fit["origin"] - screenshot_origin) > 1.0:
                raise RendererGeometryError(f"Monitor {axis} origin disagrees with screenshot board bounds.")
            if screenshot_scale is not None and abs(fit["scale"] - screenshot_scale) / screenshot_scale > 0.002:
                raise RendererGeometryError(f"Monitor {axis} scale disagrees with screenshot board bounds.")
            if fit["max_abs_residual_px"] > 0.75:
                raise RendererGeometryError(f"Monitor {axis} fit residual exceeds 0.75 screen pixels.")
            return fit["origin"], fit["scale"], "same_run_monitor_fit", fit
        if screenshot_origin is not None and screenshot_scale is not None:
            return screenshot_origin, screenshot_scale, "same_run_full_screen_board_bounds", None
        if axis == "Y":
            return inspect_origin, inspect_scale, "inspect_css_transform_unfitted_axis", None
        raise RendererGeometryError(
            f"Monitor {axis} trajectory does not span the axis and screenshot board bounds are unavailable."
        )

    origin_x, scale_x, source_x, fit_x = resolve_axis(
        "X", fit_x, inspect_x_origin, sx_inspect,
        bounds["x"] if bounds else None, screenshot_sx,
    )
    origin_y, scale_y, source_y, fit_y = resolve_axis(
        "Y", fit_y, inspect_y_origin, sy_inspect,
        bounds["y"] if bounds else None, screenshot_sy,
    )

    residuals_x = [origin_x + value * scale_x - observed for value, observed in zip(board_x, screen_x)]
    residuals_y = [origin_y + value * scale_y - observed for value, observed in zip(board_y, screen_y)]
    max_residual_x = max(abs(value) for value in residuals_x)
    max_residual_y = max(abs(value) for value in residuals_y)
    if fit_x is None and max_residual_x > 0.75:
        raise RendererGeometryError("Screenshot-derived X transform does not reproduce the live samples.")
    if fit_y is None and max_residual_y > 0.75:
        raise RendererGeometryError("Screenshot-derived Y transform does not reproduce the live samples.")

    x, y, width, height = (int(screen_roi[k]) for k in ("x", "y", "width", "height"))
    if width < 2 or height < 2:
        raise RendererGeometryError("ROI must be at least 2×2 pixels.")
    right = origin_x + scale_x * 460
    bottom = origin_y + scale_y * 240
    matrix = [[scale_x / 3, 0.0, origin_x - x],
              [0.0, scale_y / 3, origin_y - y]]

    if source_x == "same_run_monitor_fit" and source_y == "same_run_monitor_fit":
        method = "same_run_monitor_xy_fit"
    elif source_x == "same_run_monitor_fit":
        method = (
            "same_run_monitor_x_fit_plus_screenshot_board_bounds_y"
            if source_y == "same_run_full_screen_board_bounds"
            else "same_run_monitor_x_fit_plus_inspect_css_y_transform"
        )
    elif source_y == "same_run_monitor_fit":
        method = "same_run_monitor_y_fit_plus_screenshot_board_bounds_x"
    else:
        method = "same_run_screenshot_board_bounds"

    return {
        "coordinate_system": "primary_screen_screenshot_pixels",
        "method": method,
        "validation_status": "both_axes_cross_checked_with_inspect_and_same_run_screenshot_bounds"
        if bounds else "monitor_fit_axes_cross_checked_with_inspect; unfitted_Y_uses_inspect",
        "board_to_screen": {
            "origin_x": origin_x, "origin_y": origin_y,
            "scale_x": scale_x, "scale_y": scale_y,
            "corners": {
                "top_left": [origin_x, origin_y],
                "bottom_right": [right, bottom],
            },
        },
        "screen_offset_from_client": {"x": offset_x, "y": offset_y, "sample_count": len(samples)},
        "screen_offset_range_px": {"x": max(dx) - min(dx), "y": max(dy) - min(dy)},
        "horizontal_fit": fit_x,
        "vertical_fit": fit_y,
        "vertical_scale_source": source_y,
        "vertical_sample_residual_px": max_residual_y,
        "axis_sources": {"x": source_x, "y": source_y},
        "axis_max_abs_residual_px": {"x": max_residual_x, "y": max_residual_y},
        "screenshot_bounds_cross_check": {
            "bounds": bounds,
            "scale": {"x": screenshot_sx, "y": screenshot_sy} if bounds else None,
            "monitor_x_origin_difference_px": fit_x["origin"] - bounds["x"] if fit_x and bounds else None,
            "monitor_x_scale_relative_difference": fit_x["scale"] / screenshot_sx - 1 if fit_x and screenshot_sx else None,
            "monitor_y_origin_difference_px": fit_y["origin"] - bounds["y"] if fit_y and bounds else None,
            "monitor_y_scale_relative_difference": fit_y["scale"] / screenshot_sy - 1 if fit_y and screenshot_sy else None,
            "inspect_x_origin_difference_px": inspect_x_origin - bounds["x"] if bounds else None,
            "inspect_y_origin_difference_px": inspect_y_origin - bounds["y"] if bounds else None,
            "inspect_x_scale_relative_difference": sx_inspect / screenshot_sx - 1 if screenshot_sx else None,
            "inspect_y_scale_relative_difference": sy_inspect / screenshot_sy - 1 if screenshot_sy else None,
        },
        "roi": {"x": x, "y": y, "width": width, "height": height},
        "roi_alignment": {
            "board_origin_in_roi": {"x": origin_x - x, "y": origin_y - y},
            "board_size_px": {"width": right - origin_x, "height": bottom - origin_y},
            "roi_scale": {"x": (width - 1) / 460, "y": (height - 1) / 240},
            "board_edge_overrun_px": {"right": right - (x + width), "bottom": bottom - (y + height)},
        },
        "inspect_scale": {"x": sx_inspect, "y": sy_inspect},
        "inspect_origin": {"x": inspect_x_origin, "y": inspect_y_origin},
        "inspect_x_origin": inspect_x_origin,
        "inspect_x_origin_difference_px": origin_x - inspect_x_origin,
        "matrix_source_raster_to_roi": matrix,
        "source_raster_scale": 3,
    }
