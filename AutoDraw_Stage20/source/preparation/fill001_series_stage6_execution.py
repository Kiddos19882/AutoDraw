"""Experimental single-figure FILL001-SERIES-001 Stage6 execution.

Reuses V5's native MouseExecutor, slider feedback, off-ROI cursor parking,
fresh BoardPane gate, closed Bridge accounting, and screen-mask policy.
No batch invocation is exported here. The caller must opt in separately for
each isolated series and own the current Firefox/Bridge session.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable

from drawing.color_plan_execution import BrushSliderCalibration
from drawing.mouse_executor import ExecutorConfig, MouseExecutor
from models import DrawingPlan
from firefox_foreground_witness import firefox_foreground_witness
from fill001_v5_live_gate import verify_v5_live_gate
from fill001_v5_stage6_execution import (
    CONFIG as V5_EXPERIMENTAL_CONFIG,
    V5BrushSliderController,
    park_v5_cursor_for_png,
)
from fill001_series_handoff import validate_series_source_plan
from fill001_series_run_binding import validate_series_bridge_runs
from fill001_series_runner import SeriesBlocked
from fill001_screen_mask_v2 import audit_screen_mask_v2
from fill001_v5_handoff import POLICY

SCHEMA = "FILL001_SERIES_STAGE6_SINGLE_RUN_RESULT_V1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute_series_single_stage6(
    *, manifest: dict, task_id: str, source: dict, mapped: dict,
    request: dict, bridge_root: Path, driver: Any,
    slider_calibration: dict, stop_event: Any, native_mouse: Any,
    output_dir: Path,
    progress: Callable[[int,int,str],None] | None = None,
) -> dict:
    """Perform ONE previously preflighted task using normal game controls."""
    generation = validate_series_source_plan(manifest, source)
    if generation["task_id"] != task_id:
        raise SeriesBlocked("Source task is not the requested series task")
    if (not isinstance(request,dict)
            or request.get("schema") != "FILL001_SERIES_STAGE6_SINGLE_TASK_PREFLIGHT_V1"
            or request.get("task_id") != task_id
            or request.get("series_id") != manifest["series_id"]
            or request.get("source_strokes_sha256") != generation["source_strokes_sha256"]
            or request.get("execution_allowed") is not False
            or request.get("planned_strokes") != len(source["strokes"])
            or request.get("expected_brush_radii") !=
                [generation["brush_radius"]]*len(source["strokes"])):
        raise SeriesBlocked("Missing fresh task-scoped Stage6 request")
    sid=request["session_id"]
    mapping=request["mapping"]
    roi=request["screen_roi"]
    gate_sha=request["mapping_sha256"]
    if (mapping.get("session_id") != sid
            or mapping.get("boardpane_mapping_sha256") != gate_sha
            or mapping.get("screen_roi") != roi
            or mapping.get("no_fallback") is not True):
        raise SeriesBlocked("Stage6 active session or BoardPane mapping changed")
    def current_gate(*, blank: bool=False) -> dict:
        if firefox_foreground_witness(driver) is not True:
            raise SeriesBlocked("Firefox lost authenticated foreground")
        return verify_v5_live_gate(
            bridge_root, session_id=sid,
            expected_mapping_sha256=gate_sha, require_blank=blank,
        )
    startup=current_gate(blank=True)
    if startup["currentRadius"] != request["initial_snapshot"]["currentRadius"]:
        raise SeriesBlocked("Brush radius changed since single-task preflight")
    plan=DrawingPlan.from_dict(mapped)
    plan.validate_bounds()
    if (plan.width,plan.height)!=(roi["width"],roi["height"]):
        raise SeriesBlocked("Stage6 DrawingPlan canvas/ROI changed")
    if len(plan.strokes) != len(source["strokes"]):
        raise SeriesBlocked("Stage6 stroke count changed")
    for actual, frozen in zip(plan.strokes,source["strokes"]):
        if actual.metadata != frozen["metadata"]:
            raise SeriesBlocked("Stage6 stroke metadata differs from source")
    calibration=BrushSliderCalibration.from_dict(slider_calibration)
    calibration.validate(native_mouse.size(),roi)
    if calibration.initial_value != startup["currentRadius"]:
        raise SeriesBlocked("Brush calibration stale at execution entry")
    target_radius=generation["brush_radius"]
    def radius_provider(*,after_utc=None):
        g=current_gate()
        stamp=g["heartbeat_at_utc"]
        if after_utc:
            observed=datetime.fromisoformat(stamp.replace("Z","+00:00"))
            after=datetime.fromisoformat(after_utc.replace("Z","+00:00"))
            if observed <= after:
                return None
        return {"radius":g["currentRadius"],"session_id":sid,
                "observed_at_utc":stamp}
    controller=V5BrushSliderController(
        calibration,roi,current_screen_size_provider=native_mouse.size,
        monitor_radius_provider=radius_provider,
    )
    cfg=ExecutorConfig(**V5_EXPERIMENTAL_CONFIG)
    worker=MouseExecutor(stop_event,cfg)
    attempt=request["attempt_id"]
    directory=Path(output_dir)/("series-"+attempt)
    directory.mkdir(parents=True,exist_ok=False)
    before=directory/"before.png"
    after=directory/"after.png"
    settled=directory/"after_settled.png"
    report_file=directory/"report.json"
    folder=Path(bridge_root)/sid
    baseline={p.name for p in folder.glob("game-monitor-run-*.json")}
    result={
        "schema":SCHEMA,
        "request":request,
        "task_id":task_id,"session_id":sid,
        "status":"BLOCKED","started_at_utc":datetime.now(timezone.utc).isoformat(),
        "stage6_summary":None,"actual_chalk":None,
        "monitor_binding":"NOT_EVALUATED","game_png_quality":"NOT_EVALUATED",
        "before_png":None,"after_png":None,
        "after_settled_png":None,"binding":None,"png_audit":None,
    }
    def save_png(path: Path):
        native_mouse.screenshot(region=(
            roi["x"],roi["y"],roi["width"],roi["height"]
        )).save(path)
        return {"file":str(path),"sha256":_sha(path)}
    def preflight(executor):
        pre=current_gate(blank=True)
        controller.validate()
        result["before_cursor_parking"]=park_v5_cursor_for_png(
            native_mouse=native_mouse,roi=roi,
            exact_gate=lambda:current_gate(blank=True),
            expected_point_count=pre["pointCount"],
        )
        result["before_png"]=save_png(before)
        result["pre_pointCount"]=pre["pointCount"]
        controller.select_value(executor,target_radius)
        switched=current_gate(blank=True)
        if switched["currentRadius"] != target_radius:
            raise SeriesBlocked("Brush was not confirmed without drawing")
        return "Series current-game blank/brush preflight PASS"
    def before_stroke(executor,index,stroke):
        current=current_gate(blank=(index == 1))
        if current["remainingPoints"] < 300:
            raise SeriesBlocked("Exact game remaining quota below 300-point safety margin")
        if (not 1 <= index <= len(source["strokes"])
                or stroke.metadata != source["strokes"][index-1]["metadata"]
                or int(stroke.metadata["brush_value"]) != target_radius):
            raise SeriesBlocked("Unexpected series stroke or brush")
        controller.select_value(executor,target_radius)
        current=current_gate(blank=(index == 1))
        if current["currentRadius"] != target_radius:
            raise SeriesBlocked("Game brush changed before Stage6 stroke")
        return "Verified series brush and exact game session"
    try:
        summary=worker.execute(plan,roi["x"],roi["y"],
                               progress=progress,preflight=preflight,
                               before_stroke=before_stroke)
        result["stage6_summary"]=summary.to_dict(cfg)
        result["status"]=summary.status
        if before.is_file():
            result["after_png"]=save_png(after)
        if summary.status != "completed" or summary.completed_strokes != len(plan.strokes):
            raise SeriesBlocked("Stage6 did not complete the entire series figure")
        if not summary.mouse_release_succeeded:
            raise SeriesBlocked("Stage6 mouse release not proven")
        if not before.is_file() or not after.is_file():
            raise SeriesBlocked("Stage6 original PNG evidence missing")
        deadline=time.monotonic()+15
        last_error="no new complete Bridge run"
        binding=None
        while time.monotonic() < deadline:
            new_paths=sorted(p for p in folder.glob("game-monitor-run-*.json")
                             if p.name not in baseline)
            try:
                raw=[json.loads(p.read_text(encoding="utf-8")) for p in new_paths]
                binding=validate_series_bridge_runs(
                    raw,session_id=sid,task_id=task_id,
                    expected_pointer_down_client=request["expected_pointer_down_client"],
                    expected_brush_radii=request["expected_brush_radii"],
                    board_client_rect=request["board_client_rect"],
                    slider_client_corridor=request["slider_client_corridor"],
                    expected_pre=result["pre_pointCount"],
                )
                binding["bridge_run_paths"]=[str(p) for p in new_paths]
                break
            except (ValueError,OSError) as exc:
                last_error=str(exc)
                time.sleep(.3)
        if binding is None:
            raise SeriesBlocked("No closed exact Stage6 Bridge binding: "+last_error)
        result["binding"]=binding
        result["actual_chalk"]=binding["exact_chalk"]
        result["monitor_binding"]="EXACT_RUN_BOUND"
        result["post_settled_pointCount"]=binding["post_pointCount"]
        end=current_gate()
        if end["pointCount"] != binding["post_pointCount"]:
            raise SeriesBlocked("Game board changed after exact closed run")
        result["settled_cursor_parking"]=park_v5_cursor_for_png(
            native_mouse=native_mouse,roi=roi,
            exact_gate=current_gate,
            expected_point_count=binding["post_pointCount"],
        )
        result["after_settled_png"]=save_png(settled)
        geometry={
            "run_id":attempt,
            "coordinate_system":"desktop_screen_css_pixels",
            "validation_status":"valid",
            "independent_screen_mapping":True,
            "same_run":True,
            "board_screen_corners":mapping["board_screen_corners"],
            "evidence_sha256":mapping["passive_samples_sha256"],
        }
        quality=audit_screen_mask_v2(
            generation["shape_id"],before,settled,
            run_id=attempt,screen_roi=roi,geometry=geometry,
            quality_policy=POLICY,
        )
        result["png_audit"]=quality
        result["game_png_quality"]=quality["active_quality_gate"]
    except Exception as exc:
        result["error"]=f"{type(exc).__name__}: {exc}"
        if result["status"]!="completed":
            result["status"]="BLOCKED"
    finally:
        if controller.last_no_response is not None:
            result["brush_slider_no_response"]=controller.last_no_response
        result["finished_at_utc"]=datetime.now(timezone.utc).isoformat()
        with report_file.open("x",encoding="utf-8") as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False)
            stream.write("\n")
    return result


def normalized_series_run(task: dict, result: dict) -> dict:
    """Convert a completed, run-bound isolated result into the series contract."""
    request=result.get("request",{})
    binding=result.get("binding")
    summary=result.get("stage6_summary")
    quality=result.get("png_audit")
    if (result.get("status")!="completed"
            or request.get("task_id") != task["task_id"]
            or result.get("monitor_binding")!="EXACT_RUN_BOUND"
            or result.get("game_png_quality") not in ("PASS","FAIL")
            or not isinstance(binding,dict) or binding.get("status")!="EXACT_RUN_BOUND"
            or not isinstance(summary,dict) or summary.get("status")!="completed"
            or not isinstance(quality,dict)
            or result.get("before_png") is None
            or result.get("after_settled_png") is None
            or not summary.get("mouse_release",{}).get("succeeded") is True):
        raise SeriesBlocked("Stage6 report lacks complete run-bound result and screen evidence")
    run_ids=binding.get("run_ids")
    if not isinstance(run_ids,list) or not run_ids:
        raise SeriesBlocked("No exact bridge run ID")
    return {
        "task_id":task["task_id"], "session_id":request["session_id"],
        "run_id":"+".join(run_ids), "bridge_run_ids":run_ids,
        "execution_status":"completed",
        "monitor_binding":"EXACT_RUN_BOUND",
        "quality_gate":result["game_png_quality"],
        "mouse_release_succeeded":True,
        "pre_pointCount":binding["pre_pointCount"],
        "post_pointCount":binding["post_pointCount"],
        "actual_chalk":binding["exact_chalk"],
        "before_png_sha256":result["before_png"]["sha256"],
        "after_settled_png_sha256":result["after_settled_png"]["sha256"],
        "stage6_summary":{
            "completed_strokes":summary["completed_strokes"],
            "duration_seconds":summary["duration_seconds"],
        },
        "monitor_summary":{
            "event_count":binding["monitor_event_count"],
            "excluded_zero_point_slider_drags":binding["excluded_zero_point_slider_drags"],
        },
        "quality_metrics":{
            "coverage_fraction":quality["coverage_fraction"],
            "leakage_pixels":quality["leakage_pixels"],
            "leakage_pixels_beyond_allowed_halo":
                quality["active_quality_metrics"]["leakage_pixels_beyond_allowed_halo"],
            "max_perimeter_overshoot_logical_px":
                quality["active_quality_metrics"]["max_perimeter_overshoot_logical_px"],
        },
    }
