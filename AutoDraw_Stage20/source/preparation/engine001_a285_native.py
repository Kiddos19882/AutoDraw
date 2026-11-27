"""A28.6: frozen A27 adapter for shared Stage6 and FILL-001 execution."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from engine001_a28_live import (
    ARCHIVE_SHA, BASE_SHA, BOARD_SCRIPT, PLAN_SHA, SOURCE_RUN,
    Blocked, LiveReplay, digest, error_summary, exact, require, utc,
)

SCHEMA = "ENGINE001_S5_A286_NATIVE_STAGE6_V1"
SETTERS = """if(op==='selectBrush'){
 if(b._isStart||a.points[k].length!==0)throw Error('Active/nonempty stroke slot');
 b.setRadius(options.width);b.setColor(options.colorRgb);b.setSmooth(false);
}"""
require(BOARD_SCRIPT.count(SETTERS) == 1, "A28 observer source drift")
READ_ONLY_SCRIPT = BOARD_SCRIPT.replace(SETTERS, "")
ALLOWED_OPS = frozenset(("discover", "bind", "read", "stroke", "unbind"))


def color_plan(paths):
    """Adapt metadata only; keep A27 path order, points, exact RGB and widths."""
    values = list(dict.fromkeys(p["colorRgb"] for p in paths))
    palette = [
        dict(id=f"a27-{v:06X}", name=f"#{v:06X}", hex=f"#{v:06X}",
             rgb=[v >> 16, (v >> 8) & 255, v & 255])
        for v in values
    ]
    indexes = {v: i for i, v in enumerate(values)}
    return dict(
        schema_version=1, plan_type="autodraw_geometry_color_plan",
        name="A27 Joined frozen", canvas=dict(width=460, height=240),
        palette=palette, summary=dict(stroke_count=len(paths)),
        strokes=[dict(name=p["strokeId"], points=p["points"], closed=False,
                      color=dict(palette[indexes[p["colorRgb"]]],
                                 palette_index=indexes[p["colorRgb"]]),
                      metadata=dict(brush_value=str(p["width"]))) for p in paths],
    )


def palette_targets(paths, profile):
    from drawing.color_plan_execution import build_palette_targets
    return build_palette_targets(color_plan(paths), profile)


def desktop_plan(paths, mapped, roi):
    """Use the FILL-001 authenticated transform; adapt only A27 stroke metadata."""
    from models import DrawingPlan, Point, Stroke
    require(mapped.get("coordinate_system") == "local_canvas_pixels"
            and mapped.get("canvas") == {"width": roi["width"], "height": roi["height"]},
            "Missing FILL-001 mapped plan")
    frozen = mapped.get("strokes", [])
    require(len(frozen) == len(paths), "FILL-001 mapped stroke count changed")
    values = list(dict.fromkeys(p["colorRgb"] for p in paths))
    indexes = {v: i for i, v in enumerate(values)}
    rows = []
    for p, converted in zip(paths, frozen):
        require(all(converted.get(k) == p[k] for k in ("strokeId", "width", "colorRgb"))
                and len(converted["points"]) == len(p["points"]), "Mapped A27 identity changed")
        pts = [Point(q["x"], q["y"]) for q in converted["points"]]
        require(all(0 <= q.x < roi["width"] and 0 <= q.y < roi["height"]
                    and 0 <= round(q.x) < roi["width"] and 0 <= round(q.y) < roi["height"]
                    for q in pts), "A27 desktop vertex outside calibrated ROI")
        require(len({(round(q.x), round(q.y)) for q in pts}) >= 2,
                "A27 path collapses to one desktop pixel; no implicit expansion")
        rows.append(Stroke(name=p["strokeId"], points=pts, closed=False,
                           metadata=dict(palette_index=str(indexes[p["colorRgb"]]),
                                         brush_value=str(p["width"]),
                                         line_extension_px_override="0")))
    plan = DrawingPlan(width=roi["width"], height=roi["height"], strokes=rows,
                       name="A27 Joined desktop", created_at=utc(), schema_version=1)
    plan.validate_bounds()
    return plan


def outside_roi(x, y, roi):
    return not (roi["x"] <= x < roi["x"]+roi["width"]
                and roi["y"] <= y < roi["y"]+roi["height"])


def slider_calibration(control, initial, screen, roi):
    """Consume the already-normalized, confirmed Stage6 track, not raw tab-9 clicks."""
    from drawing.color_plan_execution import BrushSliderCalibration
    cfg = BrushSliderCalibration.from_dict(dict(control, initial_value=initial))
    cfg.validate(screen, roi)
    # A28 requires the entire continuous drag corridor to remain off BoardPane.
    require(not (roi["y"] <= cfg.y < roi["y"]+roi["height"]
                 and min(cfg.x_at_min,cfg.x_at_max) < roi["x"]+roi["width"]
                 and max(cfg.x_at_min,cfg.x_at_max) >= roi["x"]), "Slider intersects BoardPane")
    return cfg


def path_error(point, path):
    """Logical distance to a source polyline (Stage6 may interpolate segments)."""
    x,y = point["x"],point["y"]
    best = math.inf
    for a,b in zip(path, path[1:]):
        dx,dy = b["x"]-a["x"],b["y"]-a["y"]
        length2 = dx*dx+dy*dy
        t = max(0.,min(1.,((x-a["x"])*dx+(y-a["y"])*dy)/length2)) if length2 else 0.
        best = min(best, math.hypot(x-a["x"]-t*dx,y-a["y"]-t*dy))
    return best


def observe_native_stroke(planned, previous, post, read_stroke):
    """Record rejected/partial input without aborting a safe, idle board.

    A live stroke, unexpected slot advance or decreasing game counter still
    means the next click cannot safely be bound to the same board.
    """
    delta = exact(post["snapshot"]) - exact(previous["snapshot"])
    slot_delta = post["slot"] - previous["slot"]
    require(not post["active"] and post["empty"] and slot_delta in (0, 1),
            "Native stroke did not close safely")
    require(delta >= 0, "Game point counter decreased")
    warnings = []
    actual = None
    max_error = None
    if slot_delta == 0:
        warnings.append("Native stroke not accepted (no new slot)")
        if delta != 0:
            warnings.append("Native accepted stroke/counter mismatch")
    else:
        actual = read_stroke(previous["slot"])
        points = actual["points"]
        if (delta <= 0 or delta != len(points)
                or actual["width"] != planned["width"]
                or actual["colorRgb"] != planned["colorRgb"]
                or actual["smooth"] is not False):
            warnings.append("Native accepted stroke/counter mismatch")
        if points:
            max_error = max(path_error(q, planned["points"]) for q in points)
            if max_error > 2:
                warnings.append("Native accepted point outside intended polyline")
    return dict(stroke_id=planned["strokeId"], chalk=delta, actual=actual,
                slot_delta=slot_delta, verified=not warnings, warnings=warnings,
                max_vertex_error_logical=max_error)


class QuotaLimited(Blocked):
    pass


class NativeLiveReplay(LiveReplay):
    """Reuse A28.4 observation/capture; never invoke the old drawing or setter path."""
    legacy_pointer_witness = False

    def __init__(self, *args, profile, brush_control, raw_brush_control=None, progress_callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile, self.brush_control = profile, brush_control
        self.raw_brush_control = raw_brush_control
        self.progress_callback = progress_callback

    def read(self, op="read", options=None):
        require(op in ALLOWED_OPS, "A28.6 browser mutation forbidden")
        from firefox_monitor_session import GAME_ORIGIN, MONITOR_VERSION
        result = self.driver.execute_script(READ_ONLY_SCRIPT, op, self.id, options,
                                            GAME_ORIGIN, MONITOR_VERSION)
        if isinstance(result, dict) and "discovery" in result:
            self.discovery = result["discovery"]
            require(not self.discovery.get("error"), self.discovery.get("error"))
        return result

    def draw(self, *_args, **_kwargs):
        raise Blocked("A28.4 Selenium drawing disabled in A28.6")

    def run(self, paths):
        from drawing.color_plan_execution import ColorPlanExecutionHooks
        from drawing.mouse_executor import ExecutorConfig, MouseExecutor
        from fill001_v5_live_gate import verify_v5_live_gate
        from fill001_series_stage6_execution import QUOTA_SAFETY_MARGIN
        report = dict(schema=SCHEMA, run_id=self.id, started=utc(),
                      baseline_sha=BASE_SHA, baseline_run=SOURCE_RUN,
                      archive_sha256=ARCHIVE_SHA, plan_sha256=PLAN_SHA,
                      runner_sha256=digest(Path(__file__).read_bytes()),
                      observer_sha256=digest(Path(__file__).with_name("engine001_a28_live.py").read_bytes()),
                      bridge_session_id=self.session_id, startup="FILL001_SHARED_FIREFOX_MONITOR_BRIDGE",
                      input_transport="STAGE6_PYAUTOGUI", smooth=False, mode="normal",
                      planned_strokes=len(paths), planned_vertices=sum(len(p["points"]) for p in paths),
                      quota_reserve=QUOTA_SAFETY_MARGIN, status="BLOCKED", exact_CHALK=None,
                      slider_calibration_source="TAB2_CONFIRMED_STAGE6",
                      slider_track=self.brush_control, raw_tab9_endpoints=self.raw_brush_control,
                      completed_strokes=0, attempted_strokes=0, unverified_strokes=0,
                      observed_CHALK=0, evidence_level="E4_PENDING")
        before = last = selected = None
        verified = 0
        attempted = 0
        observed = 0
        quota_limited = False
        worker_called = False
        try:
            before,witnesses = self.preflight(paths)
            last = before
            report.update(pre=before, passive_witnesses=witnesses,
                          bridge_passive_preflight=self.bridge_witness, board_bounds_css=self.bounds,
                          live_initial_radius=before["width"])
            require(before["smooth"] is False, "Disable game smoothing manually before A28.6")
            roi = self.bridge_witness["roi"]
            proof = self.bridge_witness["mapping"]
            plan = desktop_plan(paths, self.mapped_probe_plan, roi)
            screen = self.native_mouse.size()
            cfg = slider_calibration(self.brush_control, before["width"], screen, roi)

            def radius_provider(*, after_utc=None):
                self.verify_bridge(force=True)
                g = verify_v5_live_gate(self.bridge_root, session_id=self.session_id,
                    expected_mapping_sha256=proof["boardpane_mapping_sha256"], require_blank=False)
                stamp = g["heartbeat_at_utc"]
                if after_utc:
                    from datetime import datetime
                    if datetime.fromisoformat(stamp.replace("Z","+00:00")) <= datetime.fromisoformat(after_utc):
                        return None
                return dict(radius=g["currentRadius"], session_id=self.session_id, observed_at_utc=stamp)

            hooks = ColorPlanExecutionHooks(color_plan(paths), self.profile,
                current_screen_size_provider=self.native_mouse.size,
                brush_slider_calibration=cfg, brush_target_area=roi,
                brush_monitor_radius_provider=radius_provider)
            for target in hooks.targets.values():
                require(outside_roi(target.screen_x,target.screen_y,roi),
                        "Palette swatch intersects BoardPane; no click permitted")
            # Only explicit experimental configuration: preserve path, no extension.
            # Stage6 interpolation/physical timing is distinct from A28.4 W3C sampling.
            config = ExecutorConfig(point_step_px=2.0,line_extension_px=0,
                point_delay_ms=60,after_mouse_up_ms=100,before_mouse_down_ms=100,
                after_mouse_down_ms=100,end_hold_ms=100,countdown_seconds=1)
            report.update(executor_config=config.to_dict(),
                required_colors=sorted(f"#{p:06X}" for p in {s["colorRgb"] for s in paths}),
                before_png=self.capture("before.png"))

            last_guard = 0.
            def safety_check():
                nonlocal last_guard
                # The same Stage6 loop invokes this during controls and mouse movement.
                if time.monotonic()-last_guard >= .25:
                    self.verify_bridge()
                    state = self.check(self.read())
                    if selected is not None:
                        require(state["width"]==selected["width"]
                                and state["colorRgb"]==selected["colorRgb"]
                                and state["smooth"] is False, "Native stroke tool drift")
                    last_guard = time.monotonic()

            def preflight(worker):
                self.verify_bridge(force=True)
                s = self.check(self.read())
                require(exact(s["snapshot"])==exact(before["snapshot"]) and s["slot"]==before["slot"]
                        and s["empty"] and not s["active"] and s["smooth"] is False,
                        "Board changed before Stage6")
                return hooks.preflight(worker)

            def before_stroke(worker,index,stroke):
                nonlocal selected,quota_limited
                self.verify_bridge(force=True)
                state = self.check(self.read())
                require(state["slot"]==last["slot"] and exact(state["snapshot"])==exact(last["snapshot"])
                        and state["empty"] and not state["active"], "Board drift before native control")
                if state["snapshot"]["remainingPoints"] < QUOTA_SAFETY_MARGIN:
                    quota_limited=True
                    raise QuotaLimited("FILL-001 300-point quota reserve")
                selected = None
                detail = hooks.before_stroke(worker,index,stroke)
                p = paths[index-1]
                state = self.check(self.read())
                require(state["slot"]==last["slot"] and exact(state["snapshot"])==exact(last["snapshot"])
                        and state["empty"] and not state["active"], "Control click consumed a stroke")
                require(state["width"]==p["width"] and state["colorRgb"]==p["colorRgb"]
                        and state["smooth"] is False, "Native UI tool selection mismatch")
                selected=p
                self.verify_bridge(force=True)
                return detail

            with (self.out/"strokes.jsonl").open("x",encoding="utf-8") as f:
                def after_stroke(worker,index,stroke):
                    nonlocal last,selected,verified,attempted,observed
                    require(index == attempted+1, "Unexpected Stage6 stroke completion")
                    time.sleep(.1)  # allow game mouse-up/atom closure to settle
                    self.verify_bridge(force=True)
                    post=self.check(self.read())
                    p=paths[index-1]
                    row=observe_native_stroke(
                        p,last,post,lambda slot:self.read("stroke",{"index":slot}))
                    row["attempt_index"]=index
                    f.write(json.dumps(row,allow_nan=False)+"\n");f.flush()
                    attempted+=1
                    observed+=row["chalk"]
                    verified+=int(row["verified"])
                    last=post; selected=None
                    report.update(completed_strokes=verified, attempted_strokes=attempted,
                                  unverified_strokes=attempted-verified,
                                  observed_CHALK=observed)
                    if row["warnings"]:
                        self.log(f"WARNING: штрих {index} ({p['strokeId']}): "
                                 + "; ".join(row["warnings"]) + ". Продолжаем.")
                    self.log(f"{attempted}/{len(paths)}; проверено {verified}; "
                             f"CHALK={observed}; остаток {post['snapshot']['remainingPoints']}")

                def progress(current,total,detail):
                    if callable(self.progress_callback):
                        self.progress_callback(current,total,detail)
                    if current == 0:
                        self.log(detail)

                worker=MouseExecutor(self.stop,config,safety_check=safety_check)
                worker_called=True
                summary=worker.execute(plan,roi["x"],roi["y"],progress=progress,
                    preflight=preflight,before_stroke=before_stroke,after_stroke=after_stroke)
            report.update(stage6_summary=summary.to_dict(config),tool_selection=hooks.to_report())
            require(summary.mouse_release_succeeded, "Native mouse release not confirmed")
            if self.stop.is_set() or summary.status=="stopped":
                report.update(status="STOPPED",capture_skipped="Operator Stop / native failsafe")
            else:
                require(quota_limited or (summary.status=="completed" and attempted==len(paths)),
                        summary.error or "Stage6 failed")
                final=self.check(self.read())
                diag=self.driver.execute_script("return AutoDrawGameMonitor.diagnosticSnapshot()")
                require(diag.get("pointCountMatches") is True
                        and exact(diag)==exact(final["snapshot"])==exact(last["snapshot"])
                        and final["slot"]==last["slot"] and final["empty"] and not final["active"]
                        and exact(final["snapshot"])-exact(before["snapshot"])==observed,
                        "Native run counter binding failed")
                report.update(post=final,post_diagnostic=diag)
                report["after_png"]=self.capture("after.png")
                require(exact(self.check(self.read())["snapshot"])==exact(final["snapshot"]),
                        "Counter changed during final capture")
                if attempted != verified:
                    report.update(status="QUOTA_LIMITED_WITH_WARNINGS" if quota_limited else
                                  "REPLAY_COMPLETE_WITH_WARNINGS", exact_CHALK=None,
                                  evidence_level="E4_DIAGNOSTIC_ONLY")
                else:
                    report.update(status="QUOTA_LIMITED" if quota_limited else "REPLAY_COMPLETE_NOT_VISUALLY_VALIDATED",
                                  exact_CHALK=observed,evidence_level="E4_CAPTURE_REQUIRES_REVIEW")
        except Exception as exc:
            report.update(status="STOPPED" if self.stop.is_set() else "BLOCKED",
                          reason=error_summary(exc),exact_CHALK=None)
            if self.bound:
                try:
                    if worker_called:
                        self.native_mouse.mouseUp()
                    report["failure_snapshot"]=self.read()
                    if self.capture_reference is not None and not self.stop.is_set():
                        report["failure_png"]=self.capture("failure.png")
                except Exception as capture_error:
                    report["failure_capture_error"]=error_summary(capture_error)
        finally:
            if self.bound:
                try:
                    if worker_called:
                        self.native_mouse.mouseUp()
                    self.read("unbind")
                except Exception as exc:
                    report.update(status="BLOCKED",exact_CHALK=None,cleanup_error=error_summary(exc))
            report.update(board_discovery=self.discovery,canvas_discovery=self.canvas_diagnostics,
                          bridge_passive_preflight=self.bridge_witness,finished=utc())
            with (self.out/"report.json").open("x",encoding="utf-8") as f:
                json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
        return report
