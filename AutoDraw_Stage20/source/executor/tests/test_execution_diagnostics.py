from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from drawing.execution_diagnostics import (
    build_crash_summary,
    build_execution_report,
    canonical_sha256,
    validate_target_area,
    write_execution_report,
)
from models import DrawingPlan, Point, Stroke


class ExecutionDiagnosticsTests(unittest.TestCase):
    def make_plan(self):
        return DrawingPlan(20, 20, [Stroke("line", [Point(1, 1), Point(10, 1)])], name="fixture")

    def test_hash_ignores_object_key_order_but_detects_changes(self):
        self.assertEqual(canonical_sha256({"a": 1, "b": 2}), canonical_sha256({"b": 2, "a": 1}))
        self.assertNotEqual(canonical_sha256({"a": 1}), canonical_sha256({"a": 2}))

    def test_report_includes_plan_hash_and_execution_context(self):
        plan = self.make_plan()
        report = build_execution_report(
            stage=14,
            source_plan_path="plan.json",
            source_plan=plan,
            executed_plan=plan,
            target_area={"x": 10, "y": 20, "width": 20, "height": 20},
            fit_info=None,
            summary={"status": "completed"},
            config={"point_step_px": 2.0},
            status="completed",
        )
        self.assertEqual(report["source_plan_sha256"], canonical_sha256(plan.to_dict()))
        self.assertEqual(report["executed_plan"]["sha256"], canonical_sha256(plan.to_dict()))
        self.assertEqual(report["status"], "completed")
        self.assertIn("python_version", report["environment"])

    def test_crash_summary_marks_mouse_state_as_unconfirmed(self):
        summary = build_crash_summary("RuntimeError: setup failed")
        self.assertEqual(summary["status"], "failed")
        self.assertFalse(summary["mouse_release"]["succeeded"])
        self.assertEqual(summary["stop_reason"], "worker_exception")

    def test_report_is_written_as_valid_unique_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = {"schema_version": 2, "status": "stopped", "text": "Тест"}
            one = write_execution_report(temp_dir, report)
            two = write_execution_report(temp_dir, report)
            self.assertNotEqual(one.name, two.name)
            self.assertEqual(json.loads(one.read_text(encoding="utf-8")), report)
            self.assertEqual(json.loads(two.read_text(encoding="utf-8")), report)
            self.assertEqual(sorted(path.suffix for path in Path(temp_dir).iterdir()), [".json", ".json"])

    def test_nan_is_rejected_in_hash_or_report(self):
        with self.assertRaises(ValueError):
            canonical_sha256({"bad": float("nan")})

    def test_target_area_inside_screen_is_accepted(self):
        validate_target_area(10, 20, 800, 600, 1920, 1080)

    def test_target_area_outside_current_screen_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "выходит за границы экрана"):
            validate_target_area(1900, 0, 100, 400, 1920, 1080)

    def test_target_area_too_small_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "не меньше 50"):
            validate_target_area(0, 0, 49, 100, 1920, 1080)


if __name__ == "__main__":
    unittest.main(verbosity=2)
