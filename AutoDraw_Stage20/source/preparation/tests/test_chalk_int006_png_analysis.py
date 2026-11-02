from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
import cv2
import numpy as np

APP_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(APP_ROOT / "tests"))
import chalk_int006_png_analysis as analysis

class Int006PngAnalysisTests(unittest.TestCase):
    def make_run(self, root: Path, *, gap: bool = False, parallel: bool = False, cursor: bool = False,
                 name: str = "experiment-test", series_id: str = "series-test") -> Path:
        folder = root / name
        folder.mkdir()
        before = np.full((240, 460, 3), 236, np.uint8)
        after = before.copy()
        if parallel:
            strokes = [
                {"name":"a", "closed":False, "points":[{"x":20,"y":30},{"x":180,"y":30}]},
                {"name":"b", "closed":False, "points":[{"x":20,"y":150},{"x":180,"y":150}]},
            ]
            cv2.line(after, (20,30), (180,30), (20,20,20), 15)
            cv2.line(after, (20,150), (180,150), (20,20,20), 15)
        else:
            strokes = [{"name":"line", "closed":False, "points":[{"x":20,"y":30},{"x":180,"y":90}]}]
            if gap:
                cv2.line(after, (20,30), (80,52), (20,20,20), 15)
                cv2.line(after, (115,66), (180,90), (20,20,20), 15)
            else:
                cv2.line(after, (20,30), (180,90), (20,20,20), 15)
        if cursor:
            cv2.fillPoly(after, [np.asarray([[178,88],[188,108],[190,100],[198,104]], np.int32)], (255,255,255))
        cv2.imwrite(str(folder / "before_clear-board.png"), before)
        cv2.imwrite(str(folder / "after_draw-board.png"), after)
        n = len(strokes)
        manifest = {
            "experiment_id":name,
            "chalk_experiment_matrix":{"series_id":series_id,"phase_id":"V1","scenario_id":"int006_diagonals","repeat_index":1,
                "expected_strokes":n,"requested_radius":10,"planned_strokes":strokes,
                "executor_parameters":{"point_step_px":2,"point_delay_ms":10}},
            "execution_report":{"status":"completed","completed_strokes":n},
            "monitor_capture":{"status":"saved"},
            "game_monitor_summary":{"chalk":{"status":"exact","consumed_points":10},
                "point_delta_matches_chalk":True,"observed_brush_radii":[10],
                "dropped_events":0,"monitor_dropped_events":0,"monitor_buffer_dropped_events_delta":0,
                "monitor_error_count_delta":0,"bridge_send_failures_delta":0,"collector_sequence_gap_count":0},
        }
        monitor = {"pre_test_snapshot":{"logicalWidth":460,"logicalHeight":240,"isExact":True,"pointCount":1},
            "post_test_snapshot":{"logicalWidth":460,"logicalHeight":240,"isExact":True,"pointCount":11}}
        (folder / "experiment.json").write_text(json.dumps(manifest), encoding="utf-8")
        (folder / "monitor_report.json").write_text(json.dumps(monitor), encoding="utf-8")
        return folder

    def test_continuous_stroke_metrics_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=self.make_run(root)
            result=analysis.analyse_capture(folder, root/"out")
            self.assertTrue(result["capture_valid"])
            self.assertGreater(result["strokes"][0]["coverage_fraction"], .98)
            self.assertEqual(result["strokes"][0]["max_gap_logical"], 0)
            self.assertTrue((root/"out"/"synthetic-run_overlay.png").exists())

    def test_gap_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=self.make_run(root, gap=True)
            stroke=analysis.analyse_capture(folder, root/"out")["strokes"][0]
            self.assertGreater(stroke["max_gap_logical"], 5)
            self.assertLess(stroke["coverage_fraction"], .98)

    def test_cursor_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=self.make_run(root, cursor=True)
            result=analysis.analyse_capture(folder, root/"out")
            self.assertTrue(result["cursor_detected_near_final_endpoint"])
            self.assertGreater(result["strokes"][0]["cursor_excluded_path_samples"], 0)

    def test_parallel_pair_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=self.make_run(root, parallel=True)
            pairs=analysis.analyse_capture(folder, root/"out")["parallel_pairs"]
            self.assertEqual(len(pairs), 1)
            self.assertAlmostEqual(pairs[0]["axis_separation_logical"], 120, delta=1)
            self.assertFalse(pairs[0]["assigned_ink_masks_touch_or_merge"])

    def test_repeated_endpoints_infer_closed_contour(self):
        stroke = {"name":"loop", "closed":False, "points":[
            {"x":10,"y":10}, {"x":40,"y":10}, {"x":40,"y":40}, {"x":10,"y":40}, {"x":10,"y":10}]}
        result = analysis.geometry(stroke, 1.0, 1.0)
        self.assertTrue(result["closed"])
        self.assertAlmostEqual(result["length"], 120.0)

    def test_batch_writes_csv_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.make_run(root)
            report=analysis.run(root, root/"out", expected_runs=1)
            self.assertEqual(report["analysed_runs"], 1)
            self.assertTrue((root/"out"/"summary.json").exists())
            self.assertTrue((root/"out"/"per_stroke_metrics.csv").exists())
            self.assertTrue((root/"out"/"parallel_pair_metrics.csv").exists())

    def test_same_matrix_cells_in_different_series_are_not_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.make_run(root, name="original-run", series_id="original-series")
            self.make_run(root, name="followup-run", series_id="followup-series")
            report=analysis.run(root, root/"out", expected_runs=2)
            self.assertEqual(report["series_count"], 2)
            self.assertEqual(report["duplicate_matrix_cells"], [])
            self.assertEqual(report["discovered_runs"], 2)

if __name__ == "__main__":
    unittest.main()
