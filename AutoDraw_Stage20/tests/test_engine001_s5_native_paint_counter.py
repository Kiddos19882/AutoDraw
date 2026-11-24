"""Targeted S5 native simulation paint-counter regression (isolated Egret)."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

# The existing S5 native harness expects RUNNER_TEMP on import.
if "RUNNER_TEMP" not in os.environ:
    import tempfile
    os.environ["RUNNER_TEMP"] = tempfile.gettempdir()

import run_engine001_s5_wv_full_native as native
import run_engine001_s5_native_adaptive_a3 as a3


class NativePaintCounterTest(unittest.TestCase):
    def test_counter_and_unlimited_replay(self):
        previous_out = native.OUT
        with TemporaryDirectory(prefix="s5-native-paint-counter-") as directory:
            native.OUT = Path(directory)
            try:
                with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
                    driver.set_script_timeout(480)
                    points = native.segment(200, 100, 12, 0)
                    control = [native.stroke(points, 4, 0, 0)]
                    original = native.render(driver, "reference-original", control)
                    driver.execute_script(a3.fixture(native))

                    def capture(name, paths, expected):
                        rgba = native.render(driver, name, paths)
                        data = json.loads((native.OUT / (name + ".json")).read_text("utf8"))
                        counter = data["paintCounter"]
                        self.assertEqual(counter["pointCountBefore"], 0)
                        self.assertEqual(counter["pointCountAfter"], expected)
                        self.assertEqual(counter["atomPointCount"], expected)
                        self.assertEqual(counter["used"], expected)
                        self.assertIs(counter["unlimited"], True)
                        self.assertIsNone(counter["budget"])
                        self.assertEqual(counter["exactGameChalk"], "NOT_RUN")
                        label = driver.execute_script(
                            'return document.getElementById("autodraw-sim-paint-counter").textContent;')
                        self.assertIn(str(expected), label)
                        return rgba

                    self.assertFalse(capture("blank", [], 0)[:, :, 3].any())
                    self.assertTrue(np.array_equal(original, capture("reference-metered", control, 2)))
                    for width in range(1, 11):
                        capture(f"width-{width}", [native.stroke(points, width, 0, 0)], 2)
                    repeat = [native.stroke(points, 4, 0, i) for i in range(2)]
                    capture("overpaint", repeat, 4)
                    # Former adapter caps: 3000 strokes, 5900 points, 6000 board quota.
                    many = [native.stroke(points, 1, 0, i) for i in range(3101)]
                    capture("over-6000", many, 6202)
                    # The A3 fixture also lifts the historical 128-vertex cap.
                    poly = [dict(x=190+i%2, y=110) for i in range(130)]
                    capture("over-128-vertices", [native.stroke(poly, 1, 0, 0)], 130)
                    self.assertFalse(capture("reset", [], 0)[:, :, 3].any())
                    summary = json.loads((native.OUT / "paint-counter-summary.json").read_text("utf8"))
                    self.assertEqual(summary["over-6000"]["used"], 6202)
                    self.assertEqual(summary["reset"]["used"], 0)
            finally:
                native.OUT = previous_out


if __name__ == "__main__":
    unittest.main()
