"""A28.5 physical Stage6 contract tests (never use a live browser or mouse)."""
import ast
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT/"source/preparation", ROOT/"source/executor"):
    sys.path.insert(0,str(directory))

from engine001_a285_native import (
    ALLOWED_OPS, READ_ONLY_SCRIPT, Blocked, NativeLiveReplay,
    color_plan, desktop_plan, outside_roi, path_error, slider_calibration,
)


def paths():
    return [dict(strokeId="a",width=1,colorRgb=0xEEEEEE,
                 points=[dict(x=10,y=20),dict(x=20,y=30),dict(x=40,y=30)]),
            dict(strokeId="b",width=10,colorRgb=0x535353,
                 points=[dict(x=100,y=100),dict(x=110,y=100)]),
            dict(strokeId="c",width=3,colorRgb=0xEEEEEE,
                 points=[dict(x=50,y=50),dict(x=70,y=50)])]


ROI = dict(x=500,y=200,width=920,height=480)
MAPPING = dict(board_screen_corners=dict(left=500,top=200,right=1420,bottom=680))


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
        plan=desktop_plan(p,MAPPING,ROI)
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
        with self.assertRaises(Blocked): desktop_plan(p,MAPPING,ROI)
        p=paths()
        p[0]["points"]=[dict(x=10,y=10),dict(x=10.01,y=10.01)]
        with self.assertRaises(Blocked): desktop_plan(p,MAPPING,ROI)

    def test_slider_uses_calibrated_physical_control(self):
        screen=SimpleNamespace(width=1920,height=1080)
        control=dict(mode="slider",start=[1200,800],end=[1450,800],
                     screen_size=dict(width=1920,height=1080))
        c=slider_calibration(control,20,screen,ROI)
        self.assertEqual(c.coordinate_for_value(30),1200)
        self.assertEqual(c.coordinate_for_value(1),1450)
        self.assertEqual(c.initial_value,20)
        with self.assertRaises(Blocked):
            slider_calibration(dict(control,screen_size=dict(width=100,height=100)),20,screen,ROI)
        crossing=dict(control,start=[400,400],end=[1500,400])
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

    def test_current_worker_uses_native_replay_and_stage6(self):
        source=(ROOT/"source/preparation/engine001_a285_native.py").read_text(encoding="utf-8")
        parsed=ast.parse(source)
        calls=[ast.unparse(n.func) for n in ast.walk(parsed) if isinstance(n,ast.Call)]
        self.assertIn("ColorPlanExecutionHooks",calls)
        self.assertIn("worker.execute",calls)
        self.assertIn("hooks.before_stroke",calls)
        self.assertNotIn("self.actions",calls)
        ui=(ROOT/"source/preparation/chalk_fill_ui.py").read_text(encoding="utf-8")
        self.assertIn("replay = NativeLiveReplay(",ui)
        self.assertIn("palette_targets(paths, profile)",ui)


if __name__ == "__main__":
    unittest.main()
