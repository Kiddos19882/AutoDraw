"""A28 isolated Firefox live replay. Never calls Stage6 or writes quota/points."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import time
import zipfile
from datetime import datetime, timezone

from firefox_monitor_session import GAME_ORIGIN, MONITOR_VERSION

ARCHIVE_SHA = "a17074538f9ba1015d7495cce6a9adc22567081f836d29c0457f4bff1874f583"
PLAN_SHA = "08fd735c86bb8403fe797f8bdbcceab344e6a2635bd4b4bed391211480be6bb8"
BASE_SHA = "f33791afe82dee25d88c8fc0aef521b27c550861"
SOURCE_RUN = "45704720111"
BOARD = (460, 240)
PLAN_MEMBER = "stage3-small-plan.json.gz"
WAIT = 0.06  # hold each CSS point for native ENTER_FRAME sampling; not CHALK
BATCH = 8     # bound stop latency; game quota remains authoritative


class Blocked(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise Blocked(reason)


def error_summary(exc):
    # WebDriver stack traces may include the login token in the game iframe URL.
    first = str(exc).splitlines()[0] if str(exc) else ""
    first = re.sub(r"https?://[^\s]+", "[URL REDACTED]", first)
    first = re.sub(r"(?i)token=[^\s&]+", "token=[REDACTED]", first)
    return f"{type(exc).__name__}: {first[:1000]}"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def finite(v):
    return type(v) in (int, float) and math.isfinite(v)


def validate_plan(paths):
    require(isinstance(paths, list) and len(paths) == 3270, "Wrong frozen A27 stroke count")
    ids = set()
    count = 0
    for p in paths:
        require(isinstance(p, dict) and isinstance(p.get("strokeId"), str)
                and p["strokeId"] not in ids, "Invalid/duplicate stroke")
        ids.add(p["strokeId"])
        require(type(p.get("width")) is int and 1 <= p["width"] <= 10
                and type(p.get("colorRgb")) is int and 0 <= p["colorRgb"] <= 0xffffff,
                "Invalid brush")
        require(isinstance(p.get("points"), list) and len(p["points"]) >= 2, "Invalid polyline")
        for q in p["points"]:
            require(isinstance(q, dict) and finite(q.get("x")) and finite(q.get("y"))
                    and 0 <= q["x"] < BOARD[0] and 0 <= q["y"] < BOARD[1], "Out-of-board vertex")
            count += 1
    require(count == 72128, "Wrong frozen A27 vertex count")
    return paths


def load_plan(archive):
    data = Path(archive).read_bytes()
    require(digest(data) == ARCHIVE_SHA, "Wrong A27 Joined archive SHA-256")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(z.testzip() is None, "A27 archive CRC failure")
        packed = z.read(PLAN_MEMBER)
        require(digest(packed) == PLAN_SHA, "Wrong final A27 plan hash")
        report = json.loads(z.read("a27-results.json"))
        require(report["sha"] == BASE_SHA and report["run"] == SOURCE_RUN
                and report["contour"] == "joined" and report["case"] == "illustration", "Wrong A27 provenance")
        paths = validate_plan(json.loads(gzip.decompress(packed)))
        contour = json.loads(gzip.decompress(z.read("stage1-contour-plan.json.gz")))
        require(len(contour) == 1164 and paths[:1164] == contour, "Frozen contour prefix changed")
        return paths, z.read("stage3-small.png"), z.read("projected-target.png")


def rect(corners):
    require(isinstance(corners, dict), "Missing BoardPane corners")
    pts = [corners.get(k, {}) for k in ("topLeft", "topRight", "bottomRight", "bottomLeft")]
    require(all(isinstance(p, dict) and finite(p.get("x")) and finite(p.get("y")) for p in pts), "Invalid corners")
    a, b, c, d = [(p["x"], p["y"]) for p in pts]
    require(c[0] > a[0] and c[1] > a[1] and all(abs(v-w) < 1e-5 for v,w in
            ((b[0],c[0]),(b[1],a[1]),(d[0],a[0]),(d[1],c[1]))), "Non-axis-aligned mapping")
    return (*a, *c)


def mapping(geo):
    require(geo.get("boardLogicalSize") == dict(width=460,height=240)
            and geo.get("engineVersion") == "5.4.1" and geo.get("renderMode") == "webgl"
            and geo.get("playerCount") == 1 and len(geo.get("players", [])) == 1, "Wrong live renderer")
    p = geo["players"][0]
    require(p.get("playerMatchesStage") is True and p.get("boardClientMappingMethod") in
            ("getBoxQuads_content", "validated_axis_aligned_rect"), "Unverified board mapping")
    a,b,c,d = rect(p.get("boardClientCorners"))
    s,t,u,v = rect(p.get("boardStageCorners"))
    require(abs(u-s-460) < 1e-5 and abs(v-t-240) < 1e-5, "Wrong stage board extent")
    sx,sy = (c-a)/460,(d-b)/240
    require(min(sx,sy) >= 1 and abs(sx-sy)/max(sx,sy) <= .01,
            "CSS resolution too low or nonuniform; enlarge Firefox/board")
    return a,b,c,d


def verify_canvas_rects(bounds, monitor_rect, candidates):
    """The BoardPane, not the full renderer canvas, must be onscreen.

    Candidate rectangles are CSS client coordinates in the verified game frame.
    Reject missing/ambiguous canvases and any mismatch with Monitor geometry.
    Never clip or shift a board/vertex to make this gate pass.
    """
    a,b,c,d = bounds
    require(isinstance(monitor_rect,dict), "Missing Monitor canvas rectangle")
    expected = tuple(monitor_rect.get(k) for k in ("left","top","right","bottom"))
    require(all(finite(v) for v in expected), "Invalid Monitor canvas rectangle")
    matches=[]
    for i,r in enumerate(candidates):
        require(isinstance(r,(list,tuple)) and len(r)==6 and all(finite(v) for v in r),
                "Invalid live canvas rectangle")
        left,top,right,bottom,vw,vh=r
        if (0 <= a < c <= vw and 0 <= b < d <= vh
                and left <= a < c <= right and top <= b < d <= bottom):
            matches.append(i)
    require(len(matches)==1, "Missing/ambiguous canvas containing fully visible BoardPane")
    i=matches[0]
    require(all(abs(x-y)<=1e-5 for x,y in zip(candidates[i][:4],expected)),
            "Live canvas differs from Monitor canvas rectangle")
    return i


def css_point(q, bounds):
    a,b,c,d = bounds
    x,y = round(a+q["x"]*(c-a)/460),round(b+q["y"]*(d-b)/240)
    require(a <= x < c and b <= y < d, "Rounded CSS point outside board (no clipping)")
    return x,y


def exact(snapshot):
    require(snapshot.get("isExact") is True and snapshot.get("validationStatus") == "valid"
            and type(snapshot.get("pointCount")) is int and type(snapshot.get("maxPoints")) is int
            and type(snapshot.get("remainingPoints")) is int and
            0 <= snapshot["pointCount"] <= snapshot["maxPoints"]
            and snapshot["pointCount"] + snapshot["remainingPoints"] == snapshot["maxPoints"],
            "Exact game resource unavailable")
    return snapshot["pointCount"]


# Read-only discovery of the original BoardPane. Only selectBrush calls setters,
# on its current EMPTY stroke slot. Never call onDrawing, atom.pushPoint or clear.
BOARD_SCRIPT = """
const op=arguments[0], id=arguments[1], options=arguments[2];
// Unbind is independent of rediscovery: the board may have disappeared.
if(location.origin!==arguments[3])throw Error('Wrong game frame');
if(op==='unbind'){
 const saved=window.__autodrawA28;
 if(!saved)return null;
 if(saved.id!==id)throw Error('A28 session identity changed');
 window.removeEventListener('mousemove',saved.listener,false);
 delete window.__autodrawA28;
 return null;
}
const cls=window.com?.magnetjoy?.pet?.ui?.board?.BoardPane;
const stage=window.egret?.MainContext?.instance?.stage;
const m=window.AutoDrawGameMonitor;
const status=m?.status();
if(!stage||!status||status.version!==arguments[4]||!status.active||
 !status.boardDetected||!status.inputTelemetryEnabled)throw Error('FILL-001 Monitor not ready');
// Mirror the Monitor's structural recognition and child traversal. Constructor
// identity is a diagnostic, not a prerequisite (bundled constructors may differ).
const stack=[stage], seen=new Set(), eligible=[], owned=[], candidates=[];
let candidateCount=0, constructorMatches=0, structuralMatches=0;
const finite=v=>typeof v==='number'&&Number.isFinite(v);
function visibleOnStage(n){
 const chain=new Set();
 for(let p=n;p;p=p.$parent||p.parent){
  if(chain.has(p)||p.visible===false||(finite(p.alpha)&&p.alpha<=0))return false;
  if(p===stage)return n.stage===stage;
  chain.add(p);
 }
 return false;
}
while(stack.length){
 const n=stack.pop(); if(!n||typeof n!=='object'||seen.has(n))continue; seen.add(n);
 if(seen.size>50000)return {discovery:{error:'Stage scan limit',visited:seen.size}};
 const ctor=typeof cls==='function'&&n instanceof cls;
 const structural=!!n.atom&&Array.isArray(n.atom.points)&&
  ['onDrawStart','onDrawing','onDrawingEnd'].every(k=>typeof n[k]==='function');
 if(ctor||structural){
  candidateCount++;
  if(ctor)constructorMatches++;
  if(structural)structuralMatches++;
  const visible=visibleOnStage(n);
  const controls=['setRadius','setColor','setSmooth','updateLess','localToGlobal'].every(k=>typeof n[k]==='function');
  const ready=structural&&controls&&visible&&n.width===460&&n.height===240;
  const monitorOwned=['onDrawStart','onDrawing','onDrawingEnd','setRadius','updateLess'].every(k=>
   Object.prototype.hasOwnProperty.call(n,k)&&n[k]?.__autoDrawMonitorWrapped===true);
  if(ready)eligible.push(n);
  if(ready&&monitorOwned)owned.push(n);
  if(candidates.length<64)candidates.push({
   constructorMatch:ctor,structural,controls,visible,
   width:finite(n.width)?n.width:null,height:finite(n.height)?n.height:null,
   onStage:n.stage===stage,eligible:ready,monitorOwned
  });
 }
 const children=Array.isArray(n.$children)?n.$children:
  Array.isArray(n.children)?n.children:Array.isArray(n._children)?n._children:[];
 for(const ch of children)stack.push(ch);
}
const discovery={visited:seen.size,constructorAvailable:typeof cls==='function',
 candidateCount,constructorMatches,structuralMatches,eligibleCount:eligible.length,monitorOwnedCount:owned.length,
 candidates,candidatesTruncated:candidateCount>candidates.length};
if(owned.length!==1){
 discovery.error='Expected exactly one visible 460x240 BoardPane already owned by FILL-001 Monitor';
 return {discovery};
}
if(op==='discover')return {discovery};
const b=owned[0], a=b.atom;
const ins=m.inspect(), snap=ins.snapshot;
const corners=ins.renderer?.players?.[0]?.boardStageCorners;
const expected={topLeft:[0,0],topRight:[460,0],bottomRight:[460,240],bottomLeft:[0,240]};
if(!ins.boardDetected||!snap||snap.pointCount!==b.max-b.less||!corners||
 !Object.entries(expected).every(([k,xy])=>{
  const p=b.localToGlobal(...xy),q=corners[k];
  return q&&Math.abs(p.x-q.x)<1e-5&&Math.abs(p.y-q.y)<1e-5;
 }))throw Error('Monitor board mismatch');
if(op==='bind'){
 if(window.__autodrawA28)throw Error('Existing A28 session');
 // Never reattach: the shared Monitor/Bridge session owns this board.
 const state={id,board:b,last:null};
 state.listener=e=>{state.last={x:e.clientX,y:e.clientY,buttons:e.buttons,
  trusted:e.isTrusted,canvas:e.target instanceof HTMLCanvasElement};};
 window.addEventListener('mousemove',state.listener,false);
 window.__autodrawA28=state;
}
const state=window.__autodrawA28;
if(!state||state.id!==id||state.board!==b||!b.stage)throw Error('Board/session changed');
const k=a.points.length-1;
if(!Array.isArray(a.points[k])||a.total!==a.points.length)throw Error('Unexpected atom structure');
if(op==='selectBrush'){
 if(b._isStart||a.points[k].length!==0)throw Error('Active/nonempty stroke slot');
 b.setRadius(options.width);b.setColor(options.colorRgb);b.setSmooth(false);
}
if(op==='stroke'){
 const i=options.index;
 if(i<0||i>=k)throw Error('Missing closed stroke');
 return {points:a.points[i].map(p=>({x:p.x,y:p.y})),
  width:a.radius[i],colorRgb:a.colors[i],smooth:a.options[i]};
}
return {discovery,snapshot:snap,geometry:ins.renderer,slot:k,empty:a.points[k].length===0,
 active:b._isStart, width:a.radius[k],colorRgb:a.colors[k],smooth:a.options[k],
 witness:state.last,blank:k<=1?a.points.slice(0,k).map((p,i)=>[p.length,a.radius[i],a.colors[i]]):null,
 viewport:{width:innerWidth,height:innerHeight}};
"""


class LiveReplay:
    legacy_pointer_witness = True
    def __init__(self, driver, run_dir, stop, log, *, bridge_root=None, session_id=None, native_mouse=None):
        self.driver, self.out, self.stop, self.log = driver, run_dir, stop, log
        self.id = run_dir.name
        self.bounds = None
        self.bound = False
        self.bridge_root, self.session_id, self.native_mouse = bridge_root, session_id, native_mouse
        self.bridge_witness = None
        self.capture_reference = None
        self.probe_plan = None
        self.mapped_probe_plan = None
        self.canvas_diagnostics = None
        self.bridge_checked = 0.0
        self.discovery = None
        self.max_points = None

    def read(self, op="read", options=None):
        result = self.driver.execute_script(BOARD_SCRIPT, op, self.id, options, GAME_ORIGIN, MONITOR_VERSION)
        if isinstance(result, dict) and "discovery" in result:
            self.discovery = result["discovery"]
            require(not self.discovery.get("error"), self.discovery.get("error"))
        return result

    def check(self, state):
        require(mapping(state["geometry"]) == self.bounds, "Board geometry changed")
        if self.capture_reference is not None:
            from fill001_monitor_diagnostic import _boardpane_mapping_fingerprint
            require(_boardpane_mapping_fingerprint(state["geometry"]) ==
                    self.capture_reference["boardpane_mapping_sha256"],
                    "BoardPane desktop projection changed")
        exact(state["snapshot"])
        require(self.max_points is None or state["snapshot"]["maxPoints"] == self.max_points, "Game quota changed")
        return state

    def actions(self):
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        return ActionBuilder(self.driver, duration=0)

    def release(self):
        # W3C release all input state even on transport or Stop error.
        self.actions().clear_actions()

    def canvas(self, state):
        from selenium.webdriver.common.by import By
        elements=self.driver.find_elements(By.CSS_SELECTOR, "canvas")
        rects=[self.driver.execute_script(
            "const r=arguments[0].getBoundingClientRect();"
            "return [r.left,r.top,r.right,r.bottom,innerWidth,innerHeight]", el
        ) for el in elements]
        monitor_rect=state["geometry"]["players"][0].get("canvas",{}).get("rect")
        self.canvas_diagnostics={"board_bounds_css":self.bounds,"monitor_canvas_rect":monitor_rect,
                                 "dom_canvas_rects":rects}
        index=verify_canvas_rects(self.bounds,monitor_rect,rects)
        self.canvas_diagnostics["selected_index"]=index
        return elements[index],rects[index]

    def probe_roi(self):
        from fill001_firefox_auto_probe import _collect_verified_boardpane_roi
        from firefox_foreground_witness import firefox_foreground_witness
        require(not self.stop.is_set(), "Stopped before passive ROI check")
        self.mapped_probe_plan, witness, roi = _collect_verified_boardpane_roi(
            self.driver, self.bridge_root, self.session_id, self.probe_plan,
            native_mouse=self.native_mouse,now_utc=lambda:datetime.now(timezone.utc),
            firefox_foreground_checker=lambda: (
                not self.stop.is_set() and firefox_foreground_witness(self.driver)),
        )
        return witness, roi

    def capture(self, name):
        # Reuse FILL-001's authenticated native screenshot path. Element
        # screenshots can clip the oversized renderer canvas at the viewport,
        # invalidating crop coordinates even when the BoardPane is visible.
        from PIL import ImageGrab
        from fill001_series_engine001_clear import capture_same_boardpane_roi
        require(self.capture_reference is not None, "No calibrated FILL-001 capture reference")
        start=self.check(self.read())
        require(not start["active"] and start["empty"], "Cannot capture active stroke")
        self.canvas(start)
        witness,roi=self.probe_roi()
        self.verify_bridge(force=True)
        state=self.check(self.read())
        self.canvas(state)
        require(state["slot"]==start["slot"] and exact(state["snapshot"])==exact(start["snapshot"])
                and not state["active"] and state["empty"], "Board changed during capture probe")
        physical=self.native_mouse.size()
        screen_size={"width":int(physical.width),"height":int(physical.height)}
        crop=capture_same_boardpane_roi(
            roi=roi,reference_metadata=self.capture_reference,session_id=self.session_id,
            mapping_sha256=witness["boardpane_mapping_sha256"],screen_size=screen_size,
            grab_screen=ImageGrab.grab,
        )
        self.verify_bridge(force=True)
        final=self.check(self.read())
        self.canvas(final)
        require(final["slot"]==start["slot"] and exact(final["snapshot"])==exact(start["snapshot"])
                and not final["active"] and final["empty"], "Board changed during capture")
        crop.save(self.out/name)
        return dict(sha256=digest((self.out/name).read_bytes()),size=list(crop.size),
                    capture_method="FILL001_VERIFIED_NATIVE_ROI",roi=roi,
                    mapping_sha256=witness["boardpane_mapping_sha256"],session_id=self.session_id)

    def verify_bridge(self, *, force=False):
        from brush_radius_feedback import read_active_bridge_geometry
        from firefox_foreground_witness import firefox_foreground_witness
        from firefox_monitor_session import write_bridge_diagnostic, bridge_session_diagnostic
        ready = None
        foreground = None
        actual_bounds = None
        actual_fingerprint = None
        try:
            require(self.session_id and self.bridge_root is not None, "FILL-001 Bridge required")
            foreground = firefox_foreground_witness(self.driver)
            require(foreground, "Firefox lost native foreground")
            if force or time.monotonic()-self.bridge_checked >= 2:
                ready=read_active_bridge_geometry(self.bridge_root)
                same_session = isinstance(ready,dict) and ready.get("session_id")==self.session_id
                unique_board = same_session and ready.get("board_detected") and not ready.get("board_ambiguous")
                if unique_board:
                    actual_bounds = mapping(ready["renderer_geometry"])
                require(unique_board and actual_bounds==self.bounds,
                        "FILL-001 Bridge session/geometry drift")
                if self.capture_reference is not None:
                    from fill001_monitor_diagnostic import _boardpane_mapping_fingerprint
                    actual_fingerprint = _boardpane_mapping_fingerprint(ready["renderer_geometry"])
                    require(actual_fingerprint == self.capture_reference["boardpane_mapping_sha256"],
                            "Bridge desktop projection changed")
                self.bridge_checked=time.monotonic()
        except Exception as exc:
            write_bridge_diagnostic(self.out / "bridge-runtime.jsonl", "runtime_gate_blocked",
                error_type=type(exc).__name__, foreground=foreground, expected_session_id=self.session_id,
                selected_session_id=ready.get("session_id") if isinstance(ready,dict) else None,
                selected_board_detected=ready.get("board_detected") if isinstance(ready,dict) else None,
                selected_board_ambiguous=ready.get("board_ambiguous") if isinstance(ready,dict) else None,
                expected_bounds=self.bounds, actual_bounds=actual_bounds,
                expected_mapping=self.capture_reference.get("boardpane_mapping_sha256") if self.capture_reference else None,
                actual_mapping=actual_fingerprint,
                collector_sessions=bridge_session_diagnostic(self.bridge_root) if self.bridge_root is not None else [])
            raise

    def preflight(self, paths):
        require(self.session_id and self.bridge_root is not None, "Launch via FILL-001")
        self.read("discover")
        self.bound=True  # cleanup even if bind partially succeeds
        s=self.read("bind")
        self.bounds=mapping(s["geometry"])
        self.max_points=s["snapshot"]["maxPoints"]
        self.canvas(s)
        self.verify_bridge(force=True)
        require(s["empty"] and not s["active"] and (s["blank"]==[] or s["blank"]==[[1,0,16777215]]),
                "Test board must be blank (no automatic Clear)")
        require(exact(s["snapshot"]) == (1 if s["blank"] else 0),"Nonblank board")
        # Validate every rounded point before sending ANY press.
        for p in paths:
            for q in p["points"]:
                css_point(q,self.bounds)
        self.probe_plan={"coordinate_system":"logical_board_pixels","canvas":{"width":460,"height":240},
                         "strokes":paths}
        witness,roi=self.probe_roi()
        self.bridge_witness={"mapping":witness,"roi":roi}
        physical=self.native_mouse.size()
        self.capture_reference={
            "source":"verified_boardpane_native_probe","user_confirmed_blank":True,
            "session_id":self.session_id,"boardpane_mapping_sha256":witness["boardpane_mapping_sha256"],
            "board_region":roi,"screen_size":{"width":int(physical.width),"height":int(physical.height)},
        }
        self.verify_bridge(force=True)
        a,b,c,d=self.bounds
        witnesses=[]
        for fx,fy in (((.25,.25),(.5,.5),(.75,.75)) if self.legacy_pointer_witness else ()):
            require(not self.stop.is_set(),"Stopped during calibration")
            self.verify_bridge()
            x,y=round(a+(c-a)*fx),round(b+(d-b)*fy)
            ac=self.actions();ac.pointer_action.move_to_location(x,y);ac.perform()
            time.sleep(.15)
            sample=self.check(self.read())
            w=sample.get("witness") or {}
            require(w==dict(x=x,y=y,buttons=0,trusted=True,canvas=True),"Passive browser pointer mismatch")
            require(exact(sample["snapshot"])==exact(s["snapshot"]),"Board changed during passive probes")
            witnesses.append(w)
        diag=self.driver.execute_script("return AutoDrawGameMonitor.diagnosticSnapshot()")
        require(diag.get("pointCountMatches") is True and exact(diag)==exact(s["snapshot"]),"Pre-counter mismatch")
        s=self.check(self.read())
        return s,witnesses

    def draw(self, stroke, prior):
        if self.stop.is_set():
            return None
        self.verify_bridge()
        current=self.check(self.read())
        require(current["slot"]==prior["slot"] and exact(current["snapshot"])==exact(prior["snapshot"])
                and current["empty"] and not current["active"], "Board drift before brush selection")
        s=self.check(self.read("selectBrush",{"width":stroke["width"],"colorRgb":stroke["colorRgb"]}))
        require(s["slot"]==prior["slot"] and exact(s["snapshot"])==exact(prior["snapshot"])
                and s["empty"] and not s["active"] and s["smooth"] is False
                and s["width"]==stroke["width"] and s["colorRgb"]==stroke["colorRgb"],"Brush/board drift")
        pts=[css_point(q,self.bounds) for q in stroke["points"]]
        if self.stop.is_set():
            return None
        attempted=0
        try:
            ac=self.actions();ac.pointer_action.move_to_location(*pts[0]);ac.pointer_action.pointer_down()
            ac.pointer_action.pause(WAIT);ac.perform();attempted=1
            for i in range(1,len(pts),BATCH):
                if self.stop.is_set():break
                self.verify_bridge()
                current=self.check(self.read())
                require(current["active"] and current["slot"]==s["slot"] and current["smooth"] is False
                        and current["width"]==stroke["width"] and current["colorRgb"]==stroke["colorRgb"],
                        "Active stroke identity/brush changed")
                if current["snapshot"]["remainingPoints"]==0:break
                ac=self.actions()
                for x,y in pts[i:i+BATCH]:
                    ac.pointer_action.move_to_location(x,y);ac.pointer_action.pause(WAIT)
                ac.perform();attempted+=len(pts[i:i+BATCH])
        finally:
            self.release()
        time.sleep(.1)
        post=self.check(self.read())
        require(not post["active"] and post["empty"] and post["slot"]==s["slot"]+1,"Stroke did not close uniquely")
        actual=self.read("stroke",{"index":s["slot"]})
        delta=exact(post["snapshot"])-exact(s["snapshot"])
        try:
            require(delta>0 and delta==len(actual["points"]) and actual["smooth"] is False
                    and actual["width"]==stroke["width"] and actual["colorRgb"]==stroke["colorRgb"],"Accepted stroke/counter mismatch")
            # Reject unrelated input; mouse sample rounding is measured, not corrected.
            planned=stroke["points"][:attempted]
            max_error=max(min(math.hypot(p["x"]-q["x"],p["y"]-q["y"]) for q in planned) for p in actual["points"])
            require(max_error<=2,"Accepted point outside intended sampled path")
        except Exception:
            (self.out/"failed-stroke.json").write_text(json.dumps(
                dict(stroke_id=stroke["strokeId"],attempted_vertices=attempted,actual=actual,
                     pre=s,post=post),ensure_ascii=False,allow_nan=False),encoding="utf-8")
            raise
        return post,dict(stroke_id=stroke["strokeId"],attempted_vertices=attempted,planned_vertices=len(pts),
                         chalk=delta,actual=actual,max_vertex_error_logical=max_error)

    def run(self, paths):
        report=dict(schema="ENGINE001_S5_A28_LIVE_V1",run_id=self.id,started=utc(),
                    baseline_sha=BASE_SHA,baseline_run=SOURCE_RUN,archive_sha256=ARCHIVE_SHA,
                    runner_sha256=digest(Path(__file__).read_bytes()),
                    plan_sha256=PLAN_SHA,mode="normal",smooth=False,planned_strokes=len(paths),
                    planned_vertices=72128,point_hold_seconds=WAIT,points_per_batch=BATCH,
                    status="BLOCKED",exact_CHALK=None,evidence_level="E4_PENDING",completed_strokes=0,
                    startup="FILL001_SHARED_FIREFOX_MONITOR_BRIDGE",bridge_session_id=self.session_id)
        before=post=None
        observed=0
        try:
            before,witnesses=self.preflight(paths)
            post=before
            report.update(pre=before,passive_witnesses=witnesses,board_bounds_css=self.bounds,
                          bridge_passive_preflight=self.bridge_witness,
                          before_png=self.capture("before.png"))
            with (self.out/"strokes.jsonl").open("x",encoding="utf-8") as f:
                for i,stroke in enumerate(paths):
                    if self.stop.is_set():
                        report["status"]="STOPPED";break
                    if post["snapshot"]["remainingPoints"]==0:
                        report["status"]="QUOTA_LIMITED";break
                    result=self.draw(stroke,post)
                    if result is None:
                        report["status"]="STOPPED";break
                    post,row=result
                    f.write(json.dumps(row,allow_nan=False)+"\n");f.flush()
                    observed+=row["chalk"]
                    if row["attempted_vertices"]==row["planned_vertices"] and post["snapshot"]["remainingPoints"]>0:
                        report["completed_strokes"]+=1
                    self.log(f"{i+1}/{len(paths)}; CHALK={observed}; остаток {post['snapshot']['remainingPoints']}")
                    if self.stop.is_set() or post["snapshot"]["remainingPoints"]==0:
                        report["status"]="STOPPED" if self.stop.is_set() else "QUOTA_LIMITED";break
                else:
                    report["status"]="REPLAY_COMPLETE_NOT_VISUALLY_VALIDATED"
            time.sleep(.4)
            final=self.check(self.read())
            diag=self.driver.execute_script("return AutoDrawGameMonitor.diagnosticSnapshot()")
            require(diag.get("pointCountMatches") is True and exact(diag)==exact(final["snapshot"])
                    and exact(final["snapshot"])==exact(post["snapshot"])
                    and final["slot"]==post["slot"] and not final["active"]
                    and exact(final["snapshot"])-exact(before["snapshot"])==observed,"Run counter binding failed")
            report.update(post=final,post_diagnostic=diag)
            if self.stop.is_set():
                # A fresh native capture needs passive cursor movements.
                # Honor Stop: keep counter evidence, do not move again or
                # promote an incomplete capture to the exact-CHALK result.
                report.update(status="STOPPED",capture_skipped="Operator Stop before final ROI probe")
            else:
                report["after_png"]=self.capture("after.png")
                require(exact(self.check(self.read())["snapshot"])==exact(final["snapshot"]),"Counter changed during capture")
                if self.session_id: self.verify_bridge(force=True)
                report.update(exact_CHALK=observed,evidence_level="E4_CAPTURE_REQUIRES_REVIEW")
        except Exception as exc:
            report.update(status="BLOCKED",reason=error_summary(exc),exact_CHALK=None)
            if self.bound:
                try:
                    self.release()
                    report["failure_snapshot"]=self.read()
                    if self.capture_reference is not None and not self.stop.is_set():
                        report["failure_png"]=self.capture("failure.png")
                except Exception as capture_error:
                    report["failure_capture_error"]=type(capture_error).__name__
        finally:
            # Shared Firefox worker owns Monitor/Bridge lifetime. Only release A28 input.
            if self.bound:
                failures=[]
                try: self.release()
                except Exception as exc: failures.append(error_summary(exc))
                try: self.read("unbind")
                except Exception as exc: failures.append(error_summary(exc))
                if failures:
                    report.update(status="BLOCKED",exact_CHALK=None,cleanup_error=failures)
            if self.discovery is not None:
                report["board_discovery"]=self.discovery
            if self.bridge_witness is not None:
                report["bridge_passive_preflight"]=self.bridge_witness
            if self.canvas_diagnostics is not None:
                report["canvas_discovery"]=self.canvas_diagnostics
            report["finished"]=utc()
            with (self.out/"report.json").open("x",encoding="utf-8") as f:
                json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
        return report

