"""A28 isolated Firefox live replay. Never calls Stage6 or writes quota/points."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import queue
import re
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source/preparation"))
from firefox_monitor_session import GAME_ORIGIN, MONITOR_VERSION, open_firefox, find_game_frame

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
if(!stage||!m||m.status().version!==arguments[4])throw Error('Wrong game stage/monitor');
// Mirror the Monitor's structural recognition and child traversal. Constructor
// identity is a diagnostic, not a prerequisite (bundled constructors may differ).
const stack=[stage], seen=new Set(), eligible=[], candidates=[];
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
  if(ready)eligible.push(n);
  if(candidates.length<64)candidates.push({
   constructorMatch:ctor,structural,controls,visible,
   width:finite(n.width)?n.width:null,height:finite(n.height)?n.height:null,
   onStage:n.stage===stage,eligible:ready
  });
 }
 const children=Array.isArray(n.$children)?n.$children:
  Array.isArray(n.children)?n.children:Array.isArray(n._children)?n._children:[];
 for(const ch of children)stack.push(ch);
}
const discovery={visited:seen.size,constructorAvailable:typeof cls==='function',
 candidateCount,constructorMatches,structuralMatches,eligibleCount:eligible.length,
 candidates,candidatesTruncated:candidateCount>candidates.length};
if(eligible.length!==1){
 discovery.error='Expected exactly one visible structurally verified 460x240 BoardPane';
 return {discovery};
}
if(op==='discover')return {discovery};
const b=eligible[0], a=b.atom;
if(op==='bind'){
 if(window.__autodrawA28)throw Error('Existing A28 session');
 // Explicitly attach the unchanged Monitor to this exact unique candidate,
 // rather than trusting the first object its automatic scan found.
 m.attach(b);
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
const ins=m.inspect(), snap=ins.snapshot;
if(!ins.boardDetected||!snap||snap.pointCount!==b.max-b.less)throw Error('Monitor board mismatch');
return {discovery,snapshot:snap,geometry:ins.renderer,slot:k,empty:a.points[k].length===0,
 active:b._isStart, width:a.radius[k],colorRgb:a.colors[k],smooth:a.options[k],
 witness:state.last,blank:k<=1?a.points.slice(0,k).map((p,i)=>[p.length,a.radius[i],a.colors[i]]):null,
 viewport:{width:innerWidth,height:innerHeight}};
"""


class LiveReplay:
    def __init__(self, driver, run_dir, stop, log):
        self.driver, self.out, self.stop, self.log = driver, run_dir, stop, log
        self.id = run_dir.name
        self.bounds = None
        self.bound = False
        self.monitor_owned = False
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
        exact(state["snapshot"])
        require(self.max_points is None or state["snapshot"]["maxPoints"] == self.max_points, "Game quota changed")
        return state

    def actions(self):
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        return ActionBuilder(self.driver, duration=0)

    def release(self):
        # W3C release all input state even on transport or Stop error.
        self.actions().clear_actions()

    def canvas(self):
        from selenium.webdriver.common.by import By
        a,b,c,d = self.bounds
        matches=[]
        for el in self.driver.find_elements(By.CSS_SELECTOR, "canvas"):
            r=self.driver.execute_script("const r=arguments[0].getBoundingClientRect();return [r.left,r.top,r.right,r.bottom,innerWidth,innerHeight]", el)
            if 0 <= r[0] <= a < c <= r[2] <= r[4] and 0 <= r[1] <= b < d <= r[3] <= r[5]:
                matches.append((el,r))
        require(len(matches)==1,"Missing/ambiguous fully visible game canvas")
        return matches[0]

    def capture(self, name):
        from PIL import Image
        el,r=self.canvas()
        img=Image.open(io.BytesIO(el.screenshot_as_png))
        a,b,c,d=self.bounds
        sx,sy=img.width/(r[2]-r[0]),img.height/(r[3]-r[1])
        crop=img.crop(tuple(round(x) for x in ((a-r[0])*sx,(b-r[1])*sy,(c-r[0])*sx,(d-r[1])*sy)))
        self.check(self.read())
        crop.save(self.out/name)
        return dict(sha256=digest((self.out/name).read_bytes()),size=list(crop.size))

    def preflight(self, paths):
        require(find_game_frame(self.driver) is not None,"Verified game iframe not found")
        monitor=(ROOT/"source/game_monitor/game_monitor.js").read_text(encoding="utf-8")
        require(not self.driver.execute_script("return !!window.AutoDrawGameMonitor"),"Use a fresh dedicated Firefox session")
        self.monitor_owned=True
        self.driver.execute_script(monitor)
        time.sleep(.5)
        self.read("discover")
        s=self.read("bind")
        self.bound=True
        self.bounds=mapping(s["geometry"])
        self.max_points=s["snapshot"]["maxPoints"]
        self.canvas()
        require(s["empty"] and not s["active"] and (s["blank"]==[] or s["blank"]==[[1,0,16777215]]),
                "Test board must be blank (no automatic Clear)")
        require(exact(s["snapshot"]) == (1 if s["blank"] else 0),"Nonblank board")
        # Validate every rounded point before sending ANY press.
        for p in paths:
            for q in p["points"]:
                css_point(q,self.bounds)
        a,b,c,d=self.bounds
        witnesses=[]
        for fx,fy in ((.25,.25),(.5,.5),(.75,.75)):
            require(not self.stop.is_set(),"Stopped during calibration")
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
                    status="BLOCKED",exact_CHALK=None,evidence_level="E4_PENDING",completed_strokes=0)
        before=post=None
        observed=0
        try:
            before,witnesses=self.preflight(paths)
            post=before
            report.update(pre=before,passive_witnesses=witnesses,board_bounds_css=self.bounds,
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
            report.update(post=final,post_diagnostic=diag,after_png=self.capture("after.png"))
            require(exact(self.check(self.read())["snapshot"])==exact(final["snapshot"]),"Counter changed during capture")
            report.update(exact_CHALK=observed,evidence_level="E4_CAPTURE_REQUIRES_REVIEW")
        except Exception as exc:
            report.update(status="BLOCKED",reason=error_summary(exc),exact_CHALK=None)
            if self.bound:
                try:
                    self.release()
                    report["failure_snapshot"]=self.read()
                    if self.bounds is not None:
                        report["failure_png"]=self.capture("failure.png")
                except Exception as capture_error:
                    report["failure_capture_error"]=type(capture_error).__name__
        finally:
            # Release and stop independently, even when binding failed before
            # a session was created. Never rediscover a board to clean up.
            if self.monitor_owned:
                failures=[]
                if self.bound:
                    try: self.release()
                    except Exception as exc: failures.append(error_summary(exc))
                try: self.read("unbind")
                except Exception as exc: failures.append(error_summary(exc))
                try: self.driver.execute_script("if(window.AutoDrawGameMonitor) AutoDrawGameMonitor.stop()")
                except Exception as exc: failures.append(error_summary(exc))
                if failures:
                    report.update(status="BLOCKED",exact_CHALK=None,cleanup_error=failures)
            if self.discovery is not None:
                report["board_discovery"]=self.discovery
            report["finished"]=utc()
            with (self.out/"report.json").open("x",encoding="utf-8") as f:
                json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
        return report


def main():
    import tkinter as tk
    from tkinter import filedialog, ttk, messagebox
    root=tk.Tk();root.title("ENGINE-001 S5 A28 — Selenium Live Test")
    root.geometry("720x320")
    events=queue.Queue()
    stop=threading.Event()
    confirm=threading.Event()
    busy=False
    archive=tk.StringVar()
    status=tk.StringVar(value="Выберите оригинальный ZIP A27 Joined.")
    outroot=ROOT/"data/results/engine001_s5_a28_live"
    ttk.Label(root,text="A28: A27 Joined • A17 R3 W1 • normal / smooth=false").pack(pady=12)
    ttk.Label(root,text="Только чистая тестовая доска. Не сохраняет рисунок в игре.").pack()
    row=ttk.Frame(root);row.pack(fill="x",padx=12,pady=12)
    ttk.Entry(row,textvariable=archive).pack(side="left",fill="x",expand=True)
    ttk.Button(row,text="ZIP…",command=lambda:archive.set(filedialog.askopenfilename(filetypes=[("A27 ZIP","*.zip")]))).pack(side="left")
    ttk.Label(root,textvariable=status,wraplength=680).pack(pady=12)
    def worker(path):
        driver=None
        run_dir=None
        failure=None
        try:
            paths,reference,target=load_plan(path)
            if stop.is_set():return
            run_dir=outroot/("a28-"+uuid.uuid4().hex)
            run_dir.mkdir(parents=True,exist_ok=False)
            (run_dir/"a27-native-reference.png").write_bytes(reference)
            (run_dir/"a27-target.png").write_bytes(target)
            driver=open_firefox()
            driver.set_script_timeout(10)
            events.put(("ready","Войдите вручную в Firefox, откройте чистую тестовую доску и подтвердите."))
            while not confirm.wait(.2):
                if stop.is_set():return
            if stop.is_set():return
            result=LiveReplay(driver,run_dir,stop,lambda msg:events.put(("status",msg))).run(paths)
            events.put(("status",f"{result['status']}; CHALK={result['exact_CHALK']}; {run_dir}"))
        except Exception as exc:
            failure=error_summary(exc)
            events.put(("status",f"BLOCKED: {failure}"))
        finally:
            if run_dir is not None and run_dir.is_dir() and not (run_dir/"report.json").exists():
                with (run_dir/"report.json").open("x",encoding="utf-8") as f:
                    json.dump(dict(schema="ENGINE001_S5_A28_LIVE_V1",run_id=run_dir.name,
                                   status="BLOCKED" if failure else "STOPPED_BEFORE_RUN",
                                   reason=failure,exact_CHALK=None,evidence_level="NOT_RUN",
                                   baseline_sha=BASE_SHA,plan_sha256=PLAN_SHA,finished=utc()),f,indent=2)
            if driver is not None:
                # Keep the final game window available for inspection until operator closes it.
                # Explicit Stop/close exits this dedicated WebDriver session only.
                if not stop.is_set():
                    events.put(("status_suffix"," Результат в Firefox; Stop — закрыть тестовую сессию."))
                    stop.wait()
                try:driver.quit()
                except Exception:pass
            events.put(("done",None))
    def start():
        nonlocal busy
        if busy or not archive.get():return
        if not messagebox.askyesno("A28","Открыть отдельный Firefox для теста? Не используйте ценную доску."):return
        busy=True;stop.clear();confirm.clear()
        start_button.config(state="disabled")
        threading.Thread(target=worker,args=(archive.get(),),daemon=True).start()
    def approve():
        if busy and not stop.is_set():
            if messagebox.askyesno("A28","Это чистая тестовая доска? После подтверждения не взаимодействуйте с игрой."):
                confirm.set();approve_button.config(state="disabled")
    def close():
        stop.set()
        if busy:root.after(250,close)
        else:root.destroy()
    buttons=ttk.Frame(root);buttons.pack()
    start_button=ttk.Button(buttons,text="Открыть Firefox",command=start);start_button.pack(side="left",padx=4)
    approve_button=ttk.Button(buttons,text="Подтвердить доску и начать",command=approve,state="disabled");approve_button.pack(side="left",padx=4)
    ttk.Button(buttons,text="Stop",command=stop.set).pack(side="left",padx=4)
    def poll():
        nonlocal busy
        try:
            while True:
                kind,value=events.get_nowait()
                if kind=="ready":
                    status.set(value);approve_button.config(state="normal")
                elif kind=="done":
                    busy=False;start_button.config(state="normal");approve_button.config(state="disabled")
                elif kind=="status_suffix":status.set(status.get()+value)
                else:status.set(value)
        except queue.Empty:pass
        root.after(100,poll)
    root.protocol("WM_DELETE_WINDOW",close);poll();root.mainloop()


if __name__=="__main__":
    main()
