"""A28.6 shared Stage6 contract tests (never use a live browser or mouse)."""
import ast
import json
import tempfile
import threading
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT/"source/preparation", ROOT/"source/executor"):
    sys.path.insert(0,str(directory))

from engine001_a285_native import (
    ALLOWED_OPS, READ_ONLY_SCRIPT, Blocked, NativeLiveReplay,
    color_plan, desktop_plan, outside_roi, path_error, slider_calibration,
    observe_native_stroke,
)


def paths():
    return [dict(strokeId="a",width=1,colorRgb=0xEEEEEE,
                 points=[dict(x=10,y=20),dict(x=20,y=30),dict(x=40,y=30)]),
            dict(strokeId="b",width=10,colorRgb=0x535353,
                 points=[dict(x=100,y=100),dict(x=110,y=100)]),
            dict(strokeId="c",width=3,colorRgb=0xEEEEEE,
                 points=[dict(x=50,y=50),dict(x=70,y=50)])]


ROI = dict(x=500,y=200,width=920,height=480)
def mapped_plan(p):
    # Shape of the existing FILL-001 BoardPane preflight output.
    return dict(coordinate_system="local_canvas_pixels",
                canvas=dict(width=ROI["width"],height=ROI["height"]),
                strokes=[dict(s, points=[dict(x=q["x"]*2,y=q["y"]*2)
                                        for q in s["points"]]) for s in p])


class Contracts(unittest.TestCase):
    def test_color_order_rgb_and_width_preserved(self):
        p=paths()
        result=color_plan(p)
        self.assertEqual([s["name"] for s in result["strokes"]],["a","b","c"])
        self.assertEqual([s["color"]["palette_index"] for s in result["strokes"]],[0,1,0])
        self.assertEqual([s["color"]["hex"] for s in result["strokes"]],["#EEEEEE","#535353","#EEEEEE"])
        self.assertEqual([s["metadata"]["brush_value"] for s in result["strokes"]],["1","10","3"])
        self.assertEqual([s["points"] for s in result["strokes"]],[s["points"] for s in p])

    def test_native_mapping_and_no_endpoint_expansion(self):
        p=paths()
        plan=desktop_plan(p,mapped_plan(p),ROI)
        self.assertEqual([s.name for s in plan.strokes],["a","b","c"])
        for original,stroke in zip(p,plan.strokes):
            self.assertEqual([(q.x,q.y) for q in stroke.points],
                             [(q["x"]*2,q["y"]*2) for q in original["points"]])
            self.assertFalse(stroke.closed)
            self.assertEqual(stroke.metadata["line_extension_px_override"],"0")
            self.assertEqual(stroke.metadata["brush_value"],str(original["width"]))

    def test_no_clipping_or_collapsed_path(self):
        p=paths()
        p[0]["points"]=[dict(x=459.99,y=0),dict(x=459.9,y=1)]
        with self.assertRaises(Blocked): desktop_plan(p,mapped_plan(p),ROI)
        p=paths()
        p[0]["points"]=[dict(x=10,y=10),dict(x=10.01,y=10.01)]
        with self.assertRaises(Blocked): desktop_plan(p,mapped_plan(p),ROI)

    def test_slider_uses_calibrated_physical_control(self):
        screen=SimpleNamespace(width=1920,height=1080)
        control=dict(x_at_min=1450,x_at_max=1200,y=801,initial_value=30,
                     screen_width=1920,screen_height=1080,confirmed=True)
        c=slider_calibration(control,20,screen,ROI)
        self.assertEqual(c.coordinate_for_value(30),1200)
        self.assertEqual(c.coordinate_for_value(1),1450)
        self.assertEqual(c.initial_value,20)
        self.assertEqual(c.y,801)
        with self.assertRaises(ValueError):
            slider_calibration(dict(control,screen_width=100,screen_height=100),20,screen,ROI)
        with self.assertRaises(ValueError):
            slider_calibration(dict(control,confirmed=False),20,screen,ROI)
        crossing=dict(control,x_at_min=400,x_at_max=1500,y=400)
        with self.assertRaises((Blocked,ValueError)): slider_calibration(crossing,20,screen,ROI)
        self.assertFalse(outside_roi(700,300,ROI))
        self.assertTrue(outside_roi(1500,300,ROI))

    def test_no_browser_setters_even_if_called(self):
        for forbidden in ("b.setRadius(", "b.setColor(", "b.setSmooth(", "pushPoint(",
                          "dispatchEvent(", ".clear(", ".less=", ".max="):
            self.assertNotIn(forbidden,READ_ONLY_SCRIPT)
        self.assertNotIn("selectBrush",ALLOWED_OPS)
        driver=Mock()
        worker=NativeLiveReplay(driver,Path("unused"),None,None,profile={},brush_control={})
        with self.assertRaises(Blocked): worker.read("selectBrush",{})
        with self.assertRaises(Blocked): worker.draw({}, {})
        driver.execute_script.assert_not_called()

    def test_polyline_interpolation_evidence(self):
        p=paths()[0]["points"]
        self.assertAlmostEqual(path_error(dict(x=15,y=25),p),0)
        self.assertAlmostEqual(path_error(dict(x=30,y=32),p),2)
        self.assertGreater(path_error(dict(x=30,y=35),p),2)

    @staticmethod
    def stroke_state(slot, count, *, active=False, empty=True):
        return dict(slot=slot, active=active, empty=empty,
                    snapshot=dict(isExact=True, validationStatus="valid",
                                  pointCount=count, maxPoints=6000, remainingPoints=6000-count))

    def test_rejected_click_is_logged_and_next_stroke_can_be_verified(self):
        a,b,_=paths()
        before=self.stroke_state(10,100)
        rejected=self.stroke_state(10,100)
        reader=Mock()
        row=observe_native_stroke(a,before,rejected,reader)
        self.assertFalse(row["verified"])
        self.assertEqual(row["chalk"],0)
        self.assertIn("no new slot",row["warnings"][0])
        reader.assert_not_called()
        reader.return_value=dict(points=b["points"],width=b["width"],
                                 colorRgb=b["colorRgb"],smooth=False)
        row2=observe_native_stroke(b,rejected,self.stroke_state(11,102),reader)
        self.assertTrue(row2["verified"])
        self.assertEqual(row2["chalk"],2)
        reader.assert_called_once_with(10)

    def test_post_stroke_mismatch_and_path_error_are_warnings(self):
        plan=paths()[0]
        before=self.stroke_state(10,100)
        post=self.stroke_state(11,103)
        actual=dict(points=[dict(x=200,y=200)], width=1,colorRgb=0xEEEEEE,smooth=False)
        row=observe_native_stroke(plan,before,post,lambda slot:actual)
        self.assertFalse(row["verified"])
        self.assertEqual(row["chalk"],3)
        self.assertEqual(len(row["warnings"]),2)

    def test_unsafe_board_still_blocks(self):
        plan=paths()[0]
        before=self.stroke_state(10,100)
        for state in (self.stroke_state(11,101,active=True),
                      self.stroke_state(11,101,empty=False),
                      self.stroke_state(12,102), self.stroke_state(9,100),
                      self.stroke_state(10,99)):
            with self.assertRaises(Blocked):
                observe_native_stroke(plan,before,state,Mock())

    def test_run_keeps_order_and_marks_warning_result_diagnostic_only(self):
        planned=paths()[:2]
        current=self.stroke_state(10,100)
        current.update(width=1,colorRgb=planned[0]["colorRgb"],smooth=False)
        logs=[]
        attempted=[]
        class Config:
            def __init__(self,**kwargs): self.fields=kwargs
            def to_dict(self): return self.fields
        class Worker:
            def __init__(self,*args,**kwargs): pass
            def execute(self,plan,x,y,*,progress,preflight,before_stroke,after_stroke):
                nonlocal current
                preflight(self)
                for index,p in enumerate(planned,1):
                    current.update(width=p["width"],colorRgb=p["colorRgb"])
                    before_stroke(self,index,p)
                    attempted.append(p["strokeId"])
                    if index==2:
                        current=dict(self_state(11,102),width=p["width"],
                                     colorRgb=p["colorRgb"],smooth=False)
                    after_stroke(self,index,p)
                return SimpleNamespace(status="completed",mouse_release_succeeded=True,error=None,
                                       to_dict=lambda cfg:{"status":"completed"})
        self_state=self.stroke_state
        hooks=SimpleNamespace(targets={},preflight=lambda worker:None,
                              before_stroke=lambda *args:None,to_report=lambda:{})
        modules={
            "drawing.color_plan_execution":SimpleNamespace(ColorPlanExecutionHooks=lambda *a,**k:hooks),
            "drawing.mouse_executor":SimpleNamespace(ExecutorConfig=Config,MouseExecutor=Worker),
            "fill001_v5_live_gate":SimpleNamespace(verify_v5_live_gate=Mock()),
            "fill001_series_stage6_execution":SimpleNamespace(QUOTA_SAFETY_MARGIN=300),
        }
        with tempfile.TemporaryDirectory() as tmp:
            replay=NativeLiveReplay(Mock(),Path(tmp),threading.Event(),logs.append,
                                    profile={},brush_control={},native_mouse=Mock())
            replay.bridge_witness={"roi":ROI,"mapping":{"boardpane_mapping_sha256":"fixture"}}
            replay.preflight=lambda paths:(dict(current),{})
            replay.verify_bridge=Mock()
            replay.check=lambda state:state
            replay.capture=lambda name:{"name":name}
            def read(op="read",options=None):
                if op=="stroke":
                    p=planned[1]
                    return dict(points=p["points"],width=p["width"],colorRgb=p["colorRgb"],smooth=False)
                return dict(current)
            replay.read=read
            replay.driver.execute_script.side_effect=lambda *_:dict(current["snapshot"],pointCountMatches=True)
            with patch.dict(sys.modules,modules), \
                 patch("engine001_a285_native.desktop_plan",return_value=object()), \
                 patch("engine001_a285_native.slider_calibration",return_value=object()), \
                 patch("engine001_a285_native.time.sleep"):
                result=replay.run(planned)
            rows=[json.loads(line) for line in (Path(tmp)/"strokes.jsonl").read_text().splitlines()]
            self.assertEqual(attempted,["a","b"])
            self.assertEqual([r["verified"] for r in rows],[False,True])
            self.assertEqual(result["attempted_strokes"],2)
            self.assertEqual(result["completed_strokes"],1)
            self.assertEqual(result["unverified_strokes"],1)
            self.assertEqual(result["observed_CHALK"],2)
            self.assertIsNone(result["exact_CHALK"])
            self.assertEqual(result["status"],"REPLAY_COMPLETE_WITH_WARNINGS",result.get("reason"))
            self.assertTrue(any("WARNING" in line for line in logs))

    def test_current_worker_uses_native_replay_and_stage6(self):
        source=(ROOT/"source/preparation/engine001_a285_native.py").read_text(encoding="utf-8")
        parsed=ast.parse(source)
        calls=[ast.unparse(n.func) for n in ast.walk(parsed) if isinstance(n,ast.Call)]
        self.assertIn("ColorPlanExecutionHooks",calls)
        self.assertIn("worker.execute",calls)
        self.assertIn("hooks.before_stroke",calls)
        self.assertNotIn("self.actions",calls)
        ui=(ROOT/"source/preparation/chalk_fill_ui.py").read_text(encoding="utf-8")
        self.assertIn("self.on_a28_run(",ui)
        self.assertNotIn("replay = NativeLiveReplay(",ui)
        self.assertIn("palette_targets(paths, profile)",ui)
        self.assertIn("MouseExecutor",calls)
        self.assertNotIn("GuardedExecutor",calls)
        stage6=(ROOT/"source/executor/stage6_execute_plan.py").read_text(encoding="utf-8")
        self.assertIn("replay = NativeLiveReplay(",stage6)
        self.assertIn("_read_brush_slider_calibration(check_area=False)",stage6)
        self.assertIn("self.mapped_probe_plan",source)

    def test_mapped_identity_and_canvas_are_not_silently_changed(self):
        p=paths()
        mapped=mapped_plan(p)
        mapped["strokes"][0]["colorRgb"]=0
        with self.assertRaises(Blocked): desktop_plan(p,mapped,ROI)
        mapped=mapped_plan(p)
        mapped["canvas"]["width"]+=1
        with self.assertRaises(Blocked): desktop_plan(p,mapped,ROI)


if __name__ == "__main__":
    unittest.main()
