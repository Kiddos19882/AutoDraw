import json
import tempfile
import unittest
from pathlib import Path

from game_monitor_bridge_server import RunRecorder, exact_snapshot, summarize_intervals, valid_origin


class BridgeRecorderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.recorder = RunRecorder(self.output, "session-test", 2.5)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_chalk_delta_and_run_export(self):
        before = {"maxPoints": 6000, "remainingPoints": 5999, "pointCount": 1, "isExact": True}
        after = {"maxPoints": 6000, "remainingPoints": 5947, "pointCount": 53, "isExact": True}
        self.recorder.event({"type": "DRAW_START", "t": 10, "before": before}, 1.0)
        self.recorder.event({"type": "DRAW_SAMPLE", "t": 20, "strokeId": "s1",
                             "pointDelta": 1, "acceptedPoint": {"x": 10, "y": 10}}, 1.1)
        self.recorder.event({"type": "DRAW_END", "t": 30, "strokeId": "s1",
                             "after": after}, 1.2)
        path = self.recorder.finalize("completed")
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["chalk"]["status"], "exact")
        self.assertEqual(data["chalk"]["consumed_points"], 52)
        self.assertEqual(data["brush_radius"], None)

    def test_coalesced_samples_mark_path_as_incomplete(self):
        before = {"maxPoints": 6000, "remainingPoints": 6000, "pointCount": 0, "isExact": True}
        self.recorder.event({"type": "DRAW_START", "t": 1, "before": before}, 1.0)
        self.recorder.event({"type": "DRAW_SAMPLE", "t": 2, "strokeId": "s1",
                             "pointDelta": 3, "acceptedPoint": {"x": 3, "y": 4}}, 1.1)
        self.assertEqual(self.recorder.current["interpretation"]["path_length_status"], "incomplete_samples")

    def test_only_completed_runs_are_finalized_after_idle(self):
        before = {"maxPoints": 6000, "remainingPoints": 6000, "pointCount": 0, "isExact": True}
        self.recorder.event({"type": "DRAW_START", "t": 1, "before": before}, 1.0)
        self.recorder.event({"type": "DRAW_END", "t": 2, "after": before}, 1.1)
        self.recorder.heartbeat({}, 4.0)
        self.assertIsNone(self.recorder.current)

    def test_snapshot_validation(self):
        self.assertTrue(exact_snapshot({"maxPoints": 10, "remainingPoints": 8, "pointCount": 2, "isExact": True}))
        self.assertFalse(exact_snapshot({"maxPoints": 10, "remainingPoints": 8, "pointCount": 3, "isExact": True}))

    def test_frame_summary(self):
        result = summarize_intervals([16.67] * 60)
        self.assertEqual(result["status"], "measured")
        self.assertAlmostEqual(result["median_fps"], 59.988, places=2)

    def test_origin_validation(self):
        self.assertTrue(valid_origin("https://game.example"))
        self.assertFalse(valid_origin("http://game.example"))
        self.assertFalse(valid_origin("https://game.example/path"))


if __name__ == "__main__":
    unittest.main()
