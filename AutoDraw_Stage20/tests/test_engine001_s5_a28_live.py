"""E2 contracts only: no game, driver, or runtime claims."""
import os
import subprocess
from pathlib import Path
import tempfile
import threading
import json
from unittest.mock import patch
import unittest
from run_engine001_s5_a28_live import (
    Blocked, css_point, exact, load_plan, mapping, validate_plan, LiveReplay, BOARD_SCRIPT, error_summary,
)


def corners(x,y,w,h):
    return {k:dict(x=a,y=b) for k,a,b in [
        ("topLeft",x,y),("topRight",x+w,y),("bottomRight",x+w,y+h),("bottomLeft",x,y+h)]}


def geometry():
    return dict(boardLogicalSize=dict(width=460,height=240), engineVersion="5.4.1",
                renderMode="webgl",playerCount=1,players=[dict(playerMatchesStage=True,
                boardClientMappingMethod="getBoxQuads_content",
                boardClientCorners=corners(20,40,920,480),boardStageCorners=corners(0,0,460,240))])


def snap(count):
    return dict(isExact=True,validationStatus="valid",pointCount=count,maxPoints=6000,remainingPoints=6000-count)


class Contracts(unittest.TestCase):
    def test_mapping_and_css(self):
        self.assertEqual(mapping(geometry()),(20,40,940,520))
        self.assertEqual(css_point(dict(x=155.25,y=100.5),mapping(geometry())),(330,241))
        with self.assertRaises(Blocked):
            css_point(dict(x=459.99,y=239.99),mapping(geometry()))

    def test_mapping_fails_closed(self):
        for key,value in [("renderMode","canvas"),("playerCount",2),("engineVersion","unknown")]:
            g=geometry();g[key]=value
            with self.assertRaises(Blocked):mapping(g)
        for replacement in [corners(0,0,459,240),corners(0,0,920,240),corners(0,0,0,240)]:
            g=geometry();g["players"][0]["boardClientCorners"]=replacement
            with self.assertRaises(Blocked):mapping(g)
        g=geometry();g["players"][0]["boardClientCorners"]["bottomLeft"]["x"]+=1
        with self.assertRaises(Blocked):mapping(g)

    def test_counter(self):
        self.assertEqual(exact(snap(20))-exact(snap(1)),19)
        for patch in [dict(isExact=False),dict(pointCount=2.5),dict(remainingPoints=0),dict(pointCount=True)]:
            with self.assertRaises(Blocked):exact(dict(snap(20),**patch))

    def test_wrong_archive_rejected_before_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"wrong.zip";p.write_bytes(b"bad")
            with self.assertRaises(Blocked):load_plan(p)

    def test_frozen_plan_when_archive_available(self):
        path=os.environ.get("AUTODRAW_A27_ARCHIVE")
        if not path:self.skipTest("Pinned A27 artifact not supplied")
        paths,ref,target=load_plan(path)
        self.assertEqual(len(paths),3270)
        self.assertTrue(ref.startswith(b"\x89PNG"))
        self.assertTrue(target.startswith(b"\x89PNG"))
        for replacement in [dict(width=0),dict(colorRgb=-1),dict(points=[dict(x=float("nan"),y=2),dict(x=1,y=2)]),
                            dict(strokeId=paths[1]["strokeId"])]:
            broken=[dict(paths[0],**replacement),*paths[1:]]
            with self.assertRaises(Blocked):validate_plan(broken)

    def test_geometry_drift(self):
        r=LiveReplay(None,Path("test"),None,None);r.bounds=mapping(geometry())
        g=geometry();g["players"][0]["boardClientCorners"]=corners(21,40,920,480)
        with self.assertRaises(Blocked):r.check(dict(geometry=g,snapshot=snap(0)))
        r.max_points=6000
        with self.assertRaises(Blocked):
            r.check(dict(geometry=geometry(),snapshot=dict(snap(0),maxPoints=7000,remainingPoints=7000)))

    def test_stop_before_brush(self):
        class Stop:
            def is_set(self):return True
        r=LiveReplay(None,Path("test"),Stop(),None)
        self.assertIsNone(r.draw({},{}))

    def test_run_binding_and_counter_drift(self):
        class Driver:
            def execute_script(self, script):
                return dict(snap(3),pointCountMatches=True)
        class Replay(LiveReplay):
            def preflight(self, paths):
                self.bounds=mapping(geometry())
                self.max_points=6000
                return self.state(1,0),[]
            def state(self, count, slot):
                return dict(geometry=geometry(),snapshot=snap(count),slot=slot,active=False)
            def capture(self, name):
                return {"sha256":"test"}
            def draw(self, stroke, prior):
                return self.state(3,1),dict(chalk=2,attempted_vertices=2,planned_vertices=2)
            def read(self, *a):
                return self.state(3,1)
        for drift in (False,True):
            with tempfile.TemporaryDirectory() as d, patch("run_engine001_s5_a28_live.time.sleep"):
                r=Replay(Driver(),Path(d),threading.Event(),lambda _:None)
                if drift:r.driver.execute_script=lambda s:dict(snap(4),pointCountMatches=True)
                report=r.run([{}])
                self.assertEqual(report["exact_CHALK"],None if drift else 2)
                self.assertEqual(report["status"],"BLOCKED" if drift else "REPLAY_COMPLETE_NOT_VISUALLY_VALIDATED")
                self.assertEqual(json.loads((Path(d)/"report.json").read_text())["status"],report["status"])

    def test_discovery_actual_js_and_cleanup(self):
        # Execute the real Selenium script using Node, with a minimal synthetic
        # Egret stage. No game or live renderer outcome is implied.
        fixture = r"""
const assert=require('node:assert/strict');
const script=new Function(process.argv[1]);
global.window=global;global.location={origin:'test'};
global.innerWidth=1000;global.innerHeight=800;
const listeners=new Set();
window.addEventListener=(k,fn)=>listeners.add(fn);
window.removeEventListener=(k,fn)=>listeners.delete(fn);
class ArchivedBoard {}
window.com={magnetjoy:{pet:{ui:{board:{BoardPane:ArchivedBoard}}}}};
let stage={children:[]};window.egret={MainContext:{instance:{stage}}};
let monitored=null;
window.AutoDrawGameMonitor={
 status:()=>({version:'v'}),
 attach:b=>{monitored=b;},
 inspect:()=>({boardDetected:!!monitored,snapshot:{pointCount:monitored.max-monitored.less},renderer:{}})
};
function makeBoard(parent,visible=true,width=460){
 const b={$parent:parent,stage,width,height:240,visible,alpha:1,max:6000,less:6000,
  atom:{points:[[]],radius:[1],colors:[0],options:[false],total:1},_isStart:false};
 for(const key of ['onDrawStart','onDrawing','onDrawingEnd','setRadius','setColor','setSmooth','updateLess','localToGlobal'])b[key]=()=>{};
 return b;
}
function call(op){return script(op,'run',null,'test','v');}
assert.equal(call('discover').discovery.eligibleCount,0);
const panel={$parent:stage,stage,_children:[]};
stage.children=[panel];
const real=makeBoard(panel);
const wrong=makeBoard(panel,true,320);
const hiddenParent={$parent:panel,stage,visible:false,children:[]};
const hidden=makeBoard(hiddenParent);
hiddenParent.children=[hidden];panel._children=[real,wrong,hiddenParent];
const d=call('discover').discovery;
assert.equal(d.candidateCount,3);
assert.equal(d.structuralMatches,3);
assert.equal(d.constructorMatches,0);
assert.equal(d.eligibleCount,1);
assert.equal(call('bind').slot,0);
assert.equal(monitored,real);
assert.equal(listeners.size,1);
const second=makeBoard(panel);
panel._children.push(second);
const ambiguous=call('read').discovery;
assert.equal(ambiguous.eligibleCount,2);
assert.ok(ambiguous.error);
assert.ok(call('discover').discovery.error);
stage.children=[];
assert.equal(call('unbind'),null);
assert.equal(listeners.size,0);
assert.equal(call('unbind'),null);
// Never attach or configure an ambiguous/absent board.
window.com=undefined;
assert.equal(call('discover').discovery.constructorAvailable,false);
assert.ok(call('bind').discovery.error);
"""
        result=subprocess.run(["node","-e",fixture,BOARD_SCRIPT],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_report_preserves_discovery_and_stops_owned_monitor_on_failed_bind(self):
        calls=[]
        class Driver:
            def execute_script(self, script, *args):
                calls.append(script)
                return None
        class Replay(LiveReplay):
            def preflight(self, paths):
                self.monitor_owned=True
                self.discovery={"eligibleCount":0,"candidateCount":2,"error":"not unique"}
                raise Blocked("not unique")
            def read(self, op="read", options=None):
                calls.append(op)
        with tempfile.TemporaryDirectory() as d:
            r=Replay(Driver(),Path(d),threading.Event(),lambda _:None)
            report=r.run([{}])
            self.assertEqual(report["status"],"BLOCKED")
            self.assertEqual(report["completed_strokes"],0)
            self.assertIsNone(report["exact_CHALK"])
            self.assertEqual(report["board_discovery"]["candidateCount"],2)
            self.assertIn("unbind",calls)
            self.assertTrue(any("AutoDrawGameMonitor.stop()" in c for c in calls))
            self.assertNotIn("cleanup_error",report)

    def test_error_redaction(self):
        reason=error_summary(RuntimeError("https://example.test/?token=secret\nStacktrace: private-secret"))
        self.assertNotIn("secret",reason)
        self.assertNotIn("https://",reason)

    def test_browser_script_does_not_inject_points_clear_or_quota(self):
        for forbidden in ("pushPoint(", ".onDrawing(", ".onDrawStart(", ".clear(", ".less=", ".max=", "dispatchEvent("):
            self.assertNotIn(forbidden,BOARD_SCRIPT)
        self.assertIn("b.setSmooth(false)",BOARD_SCRIPT)


if __name__=="__main__":
    unittest.main()
