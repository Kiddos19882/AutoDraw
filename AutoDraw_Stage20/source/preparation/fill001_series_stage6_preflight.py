"""Single-task preflight for FILL001-SERIES-001 generic Stage6 experiments.

Generalizes the V5 validated BoardPane geometry without executing strokes.
No OS input. The caller must authenticate live Firefox foreground and exact
same-session Bridge gate on EVERY later game action.
"""
from __future__ import annotations

import math
import uuid
from typing import Any, Callable

from fill001_series_runner import SeriesBlocked
from fill001_series_handoff import validate_series_source_plan
from drawing.color_plan_execution import BrushSliderCalibration
from models import DrawingPlan

SCHEMA = "FILL001_SERIES_STAGE6_SINGLE_TASK_PREFLIGHT_V1"


def prepare_series_stage6_preflight(
    manifest: dict, source: dict, mapped: dict, mapping: dict, roi: dict,
    *, session_id: str, calibration: dict, screen_size: tuple[int, int],
    live_exact_gate: Callable[[], dict],
    foreground_verified: Callable[[], bool],
) -> dict:
    """Generate an audited request; Stage6 executor remains separate and opt-in."""
    metadata = validate_series_source_plan(manifest, source)
    if (not isinstance(mapping, dict)
            or mapping.get("status") != "validated_preflight_input_transform_not_live_draw"
            or mapping.get("session_id") != session_id
            or mapping.get("no_fallback") is not True
            or mapping.get("screen_roi") != roi
            or not isinstance(mapping.get("boardpane_mapping_sha256"), str)
            or len(mapping["boardpane_mapping_sha256"]) != 64
            or not isinstance(mapping.get("passive_samples_sha256"), str)
            or len(mapping["passive_samples_sha256"]) != 64):
        raise SeriesBlocked("Series Stage6 lacks verified same-session passive mapping")
    if (not isinstance(roi, dict) or set(roi) != {"x","y","width","height"}
            or any(type(roi[k]) is not int for k in roi)
            or min(roi["x"],roi["y"]) < 0
            or min(roi["width"],roi["height"]) <= 0
            or not callable(foreground_verified)
            or foreground_verified() is not True):
        raise SeriesBlocked("Series Stage6 requires foreground Firefox and physical BoardPane ROI")
    if not callable(live_exact_gate):
        raise SeriesBlocked("Missing exact native Monitor preflight")
    gate=live_exact_gate()
    if (not isinstance(gate,dict) or gate.get("session_id") != session_id
            or gate.get("mapping_sha256") != mapping["boardpane_mapping_sha256"]
            or gate.get("pointCount") != 1
            or gate.get("blank_counter_confirmed") is not True
            or gate.get("exact") is not True
            or type(gate.get("currentRadius")) is not int
            or not 1 <= gate["currentRadius"] <= 30
            or type(gate.get("remainingPoints")) is not int
            or gate["remainingPoints"] < 300):
        raise SeriesBlocked("Series Stage6 exact clean-board gate not confirmed")
    if (not isinstance(mapped,dict)
            or mapped.get("coordinate_system") != "local_canvas_pixels"
            or mapped.get("canvas") != {"width":roi["width"],"height":roi["height"]}
            or not isinstance(mapped.get("strokes"),list)
            or len(mapped["strokes"]) != len(source["strokes"])):
        raise SeriesBlocked("Mapped series DrawingPlan is not the signed source")
    corners=mapping.get("board_screen_corners")
    offset=mapping.get("client_to_desktop_offset")
    if (not isinstance(corners,dict) or not isinstance(offset,dict)
            or any(type(corners.get(k)) not in (int,float) or not math.isfinite(corners[k])
                   for k in ("left","top","right","bottom"))
            or any(type(offset.get(k)) not in (int,float) or not math.isfinite(offset[k])
                   for k in ("x","y"))):
        raise SeriesBlocked("Missing real BoardPane CSS/desktop mapping")
    x0,y0,x1,y1=(corners[k] for k in ("left","top","right","bottom"))
    sx,sy=(x1-x0)/460,(y1-y0)/240
    if sx <= 0 or sy <= 0 or abs(sx-sy)/max(sx,sy) > .01:
        raise SeriesBlocked("Non-uniform or reversed BoardPane scale")
    for original, transformed in zip(source["strokes"],mapped["strokes"]):
        if (transformed.get("metadata") != original["metadata"]
                or len(transformed.get("points",[])) != len(original["points"])):
            raise SeriesBlocked("Stroke ordering/metadata changed after mapping")
        for logical,pixel in zip(original["points"],transformed["points"]):
            expected_x=x0+logical["x"]*sx-roi["x"]
            expected_y=y0+logical["y"]*sy-roi["y"]
            if (type(pixel.get("x")) not in (float,int)
                    or type(pixel.get("y")) not in (float,int)
                    or abs(pixel["x"]-expected_x)>1e-5
                    or abs(pixel["y"]-expected_y)>1e-5):
                raise SeriesBlocked("Mapped Stage6 point differs from authenticated game geometry")
    plan=DrawingPlan.from_dict(mapped)
    plan.validate_bounds()
    if (plan.width,plan.height)!=(roi["width"],roi["height"]):
        raise SeriesBlocked("Executor ROI and plan geometry disagree")
    slider=BrushSliderCalibration.from_dict(calibration)
    slider.validate(screen_size,roi)
    if slider.initial_value != gate["currentRadius"]:
        raise SeriesBlocked("Brush slider calibration no longer matches live radius")
    dx,dy=offset["x"],offset["y"]
    expected_starts=[
        [float(round(roi["x"]+stroke.points[0].x)-dx),
         float(round(roi["y"]+stroke.points[0].y)-dy)]
        for stroke in plan.strokes
    ]
    brush_sequence=[
        int(stroke.metadata["brush_value"])
        for stroke in plan.strokes
    ]
    if brush_sequence != [metadata["brush_radius"]]*len(plan.strokes):
        raise SeriesBlocked("Unexpected width switches in fixed-radius series task")
    board={"left":x0-dx,"right":x1-dx,"top":y0-dy,"bottom":y1-dy}
    slider_box={
        "left":min(slider.x_at_min,slider.x_at_max)-dx-4,
        "right":max(slider.x_at_min,slider.x_at_max)-dx+4,
        "top":slider.y-dy-4,"bottom":slider.y-dy+4
    }
    if (slider_box["left"] < board["right"] and slider_box["right"] > board["left"]
            and slider_box["top"] < board["bottom"] and slider_box["bottom"] > board["top"]):
        raise SeriesBlocked("Slider click corridor intersects game board")
    return {
        "schema": SCHEMA,
        "protocol":"FILL001_SERIES_STAGE6_SINGLE_RUN_V1",
        "attempt_id":str(uuid.uuid4()),
        "series_id":manifest["series_id"],
        "task_id":metadata["task_id"],
        "session_id":session_id,
        "source_strokes_sha256":metadata["source_strokes_sha256"],
        "mapping_sha256":mapping["boardpane_mapping_sha256"],
        "mapping":dict(mapping),
        "screen_roi":dict(roi),
        "initial_snapshot":gate,
        "expected_pointer_down_client":expected_starts,
        "expected_brush_radii":brush_sequence,
        "board_client_rect":board,
        "slider_client_corridor":slider_box,
        "planned_strokes":len(plan.strokes),
        "execution_allowed":False,
        "exact_chalk":None,
        "game_png_quality":"NOT_EVALUATED",
    }
