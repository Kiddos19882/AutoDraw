"""Single-run FILL-001 V5 execution adapter for the EXISTING Stage6 MouseExecutor.

The routine never executes without a fresh, current-session BoardPane mapping,
exact clean-board counter, independently verified slider calibration, native
Firefox focus, and a frozen immutable two-candidate V5 source.
Production executor config and ordinary Stage6 loader are unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
from typing import Any, Callable

from drawing.color_plan_execution import BrushSliderCalibration, BrushSliderController
from drawing.mouse_executor import ExecutorConfig, MouseExecutor
from models import DrawingPlan
from brush_radius_feedback import read_active_bridge_radius
from firefox_foreground_witness import firefox_foreground_witness
from fill001_v5_handoff import (
    Fill001V5Error, V5BrushSequenceGuard, validate_fill001_v5_source_plan,
)
from fill001_v5_live_gate import verify_v5_live_gate

CONFIG = {
    "point_step_px": 4.0, "point_delay_ms": 5,
    "line_extension_px": 0.0,
    "before_mouse_down_ms": 20, "after_mouse_down_ms": 40,
    "after_mouse_up_ms": 20, "end_hold_ms": 50,
    "countdown_seconds": 5,
}


def prepare_v5_run(
    source: dict, mapped: dict, mapping: dict, roi: dict,
    *, bridge_root: Path, session_id: str, driver: Any,
    slider_calibration: dict, screen_size: Any,
    now_utc: datetime | None = None,
) -> dict:
    """Pure preflight: NO game input. Never reuse a calibration from another run."""
    candidate = validate_fill001_v5_source_plan(source)
    if not isinstance(mapping, dict) or (
        mapping.get("status") != "validated_preflight_input_transform_not_live_draw"
        or mapping.get("session_id") != session_id
        or mapping.get("no_fallback") is not True
        or mapping.get("screen_roi") != roi
    ):
        raise Fill001V5Error("V5 passive BoardPane mapping is not authenticated.")
    gate = verify_v5_live_gate(
        bridge_root, session_id=session_id,
        expected_mapping_sha256=mapping["boardpane_mapping_sha256"],
        require_blank=True, now_utc=now_utc,
    )
    if not firefox_foreground_witness(driver):
        raise Fill001V5Error("Firefox foreground lost before V5 Stage6 execution.")
    if (not isinstance(roi, dict) or set(roi) != {"x", "y", "width", "height"}
            or any(type(roi[x]) is not int for x in roi)
            or roi["x"] < 0 or roi["y"] < 0
            or roi["width"] < 1 or roi["height"] < 1):
        raise Fill001V5Error("Invalid V5 physical board ROI.")
    if (not isinstance(mapped, dict)
            or mapped.get("coordinate_system") != "local_canvas_pixels"
            or mapped.get("canvas") != {"width": roi["width"], "height": roi["height"]}
            or not isinstance(mapped.get("strokes"), list)
            or len(mapped["strokes"]) != 29):
        raise Fill001V5Error("V5 mapped DrawingPlan is invalid.")
    corners = mapping.get("board_screen_corners")
    if not isinstance(corners, dict):
        raise Fill001V5Error("Missing independently verified screen corners.")
    try:
        x0, y0, x1, y1 = [float(corners[k]) for k in ("left", "top", "right", "bottom")]
        from math import isfinite
        if not all(isfinite(v) for v in (x0, y0, x1, y1)):
            raise ValueError("Non-finite mapping.")
        sx = (x1 - x0) / 460
        sy = (y1 - y0) / 240
        if sx <= 0 or sy <= 0 or abs(sx-sy)/max(sx,sy) > .01:
            raise ValueError("Non-uniform mapping.")
    except (KeyError, TypeError, ValueError) as exc:
        raise Fill001V5Error("Invalid V5 BoardPane screen transform.") from exc
    for expected, actual in zip(source["strokes"], mapped["strokes"]):
        if (actual.get("metadata") != expected["metadata"]
                or len(actual.get("points", [])) != len(expected["points"])):
            raise Fill001V5Error("V5 stroke identity changed during screen transform.")
        for logical, pixel in zip(expected["points"], actual["points"]):
            target_x = x0 + logical["x"]*sx - roi["x"]
            target_y = y0 + logical["y"]*sy - roi["y"]
            if (abs(float(pixel["x"])-target_x)>1e-5
                    or abs(float(pixel["y"])-target_y)>1e-5):
                raise Fill001V5Error("V5 screen coordinates changed after passive mapping.")
    plan = DrawingPlan.from_dict(mapped)
    plan.validate_bounds()
    if (plan.width, plan.height) != (roi["width"], roi["height"]):
        raise Fill001V5Error("V5 Stage6 canvas dimensions do not match ROI.")
    calibration = BrushSliderCalibration.from_dict(slider_calibration)
    calibration.validate(screen_size, roi)
    if gate["currentRadius"] != calibration.initial_value:
        raise Fill001V5Error(
            "Live Game Monitor radius differs from slider initial calibration; "
            "recalibration required, no game input."
        )
    # Exactly one named run attempt; NEVER treat a prior passive ROI as executor-ready.
    return {
        "protocol": "FILL001_V5_STAGE6_SINGLE_RUN_V1",
        "attempt_id": str(uuid.uuid4()),
        "candidate_id": candidate,
        "session_id": session_id,
        "source_strokes_sha256": source["generation"]["source_strokes_sha256"],
        "mapping_sha256": mapping["boardpane_mapping_sha256"],
        "screen_roi": dict(roi),
        "initial_snapshot": gate,
        "brush_sequence": [10]*28 + [2 if candidate.endswith("w2") else 3],
        "actual_chalk": None,
        "game_png_quality": "NOT_EVALUATED",
        "final_validation": "PENDING",
    }


def execute_v5_with_stage6(
    *, request: dict, source: dict, mapped: dict, mapping: dict,
    bridge_root: Path, driver: Any, slider_calibration: dict,
    stop_event: Any, progress: Callable[[int, int, str], None] | None = None,
    native_mouse: Any, output_dir: Path,
) -> dict:
    """Call ONLY existing Stage6 MouseExecutor and BrushSliderController.

    Save original before/after PNGs; exact CHALK awaits verified Bridge run
    matching and is NEVER inferred merely from arbitrary session snapshots.
    """
    import pyautogui

    candidate = validate_fill001_v5_source_plan(source)
    if request.get("candidate_id") != candidate or request.get("protocol") != "FILL001_V5_STAGE6_SINGLE_RUN_V1":
        raise Fill001V5Error("Wrong V5 run identity.")
    sid = request["session_id"]
    roi = request["screen_roi"]
    mapping_sha = request["mapping_sha256"]
    # Strict revalidation on worker entry.
    plan = DrawingPlan.from_dict(mapped)
    plan.validate_bounds()
    if len(plan.strokes) != 29 or (plan.width,plan.height) != (roi["width"],roi["height"]):
        raise Fill001V5Error("V5 Stage6 plan is not exactly the mapped 29 strokes.")
    for original, converted in zip(source["strokes"], plan.strokes):
        if converted.metadata != original["metadata"]:
            raise Fill001V5Error("V5 Stage6 source stroke identity mismatch.")

    calib = BrushSliderCalibration.from_dict(slider_calibration)
    calib.validate(native_mouse.size(), roi)
    bridge = Path(bridge_root)
    def current_gate(*, blank: bool = False) -> dict:
        if not firefox_foreground_witness(driver):
            raise Fill001V5Error("Firefox lost native foreground; stop Stage6.")
        return verify_v5_live_gate(
            bridge, session_id=sid, expected_mapping_sha256=mapping_sha,
            require_blank=blank,
        )
    def radius_provider(*, after_utc=None):
        observed = read_active_bridge_radius(bridge, after_utc=after_utc)
        if not isinstance(observed, dict) or observed.get("session_id") != sid:
            raise Fill001V5Error("Brush heartbeat belongs to another/missing Bridge session.")
        current_gate()
        return observed

    controller = BrushSliderController(
        calib, roi, current_screen_size_provider=native_mouse.size,
        monitor_radius_provider=radius_provider,
    )
    guard = V5BrushSequenceGuard(source)
    cfg = ExecutorConfig(**CONFIG)
    executor = MouseExecutor(stop_event, cfg)
    directory = Path(output_dir) / f"v5-{request['attempt_id']}"
    directory.mkdir(parents=True, exist_ok=False)
    before_path = directory / "before.png"
    after_path = directory / "after.png"
    report_path = directory / "report.json"
    report = {
        "schema": "FILL001_V5_STAGE6_SINGLE_RUN_RESULT_V1",
        "request": request, "status": "BLOCKED",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "before_png": None, "after_png": None,
        "pre_pointCount": None, "post_pointCount": None,
        "verified_brush_sequence": [],
        "stage6_summary": None, "actual_chalk": None,
        "game_png_quality": "NOT_EVALUATED",
        "monitor_binding": "NOT_EVALUATED",
    }

    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def preflight(worker):
        snap = current_gate(blank=True)
        if snap["currentRadius"] != calib.initial_value:
            raise Fill001V5Error("Unexpected radius before first V5 slider action.")
        controller.validate()
        # Bind the before screenshot to the same exact one-point board state.
        native_mouse.screenshot(region=(
            roi["x"], roi["y"], roi["width"], roi["height"],
        )).save(before_path)
        report["before_png"] = {"file": str(before_path), "sha256": sha(before_path)}
        report["pre_pointCount"] = snap["pointCount"]
        if controller.current_value != 10:
            controller.select_value(worker, 10)
        checked = current_gate(blank=True)
        if checked["currentRadius"] != 10:
            raise Fill001V5Error("Brush switch failed or modified clean game board.")
        guard.preflight(controller)
        return "V5 fresh exact blank-board + brush 10 verified."

    def before_stroke(worker, index, stroke):
        snap = current_gate(blank=(index == 1))
        if index > 1 and snap["pointCount"] < 1:
            raise Fill001V5Error("V5 exact resource counter reset while drawing.")
        return guard.before_stroke(controller, worker, index, stroke)

    try:
        summary = executor.execute(
            plan, roi["x"], roi["y"],
            progress=progress, preflight=preflight, before_stroke=before_stroke,
        )
        report["stage6_summary"] = summary.to_dict(cfg)
        report["status"] = summary.status
        report["verified_brush_sequence"] = list(guard.verified_widths)
        if summary.status == "completed":
            guard.assert_complete()
        # After PNG is captured even for a partial/failed run, if possible.
        if before_path.exists():
            native_mouse.screenshot(region=(
                roi["x"], roi["y"], roi["width"], roi["height"],
            )).save(after_path)
            report["after_png"] = {"file": str(after_path), "sha256": sha(after_path)}
        try:
            post = current_gate()
            report["post_pointCount"] = post["pointCount"]
        except Exception as exc:
            report["post_gate_error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        report["status"] = "FAILED"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        # No exact CHALK claim before matching persisted run-bound Game Monitor
        # data. Even pre=1/post=N is not a run identity proof.
        with report_path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    return report
