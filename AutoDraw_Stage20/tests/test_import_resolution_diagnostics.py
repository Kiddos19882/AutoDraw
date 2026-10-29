from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from models import DrawingPlan


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"


class ImportResolutionDiagnosticsTests(unittest.TestCase):
    """Check legacy short-import resolution and canonical model identity."""

    def _resolve_short_imports(self, first: str, second: str) -> dict[str, str]:
        roots = {
            "preparation": SOURCE / "preparation",
            "executor": SOURCE / "executor",
        }
        script = """
import json
import sys
sys.path[:0] = [sys.argv[1], sys.argv[2]]
import models
import image_processing
import image_processing.pipeline as pipeline
print(json.dumps({
    "models": str(models.__file__),
    "image_processing": str(image_processing.__file__),
    "pipeline": str(pipeline.__file__),
}))
"""
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                str(roots[first]),
                str(roots[second]),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_short_imports_resolve_from_first_component_root(self) -> None:
        for first, second in (
            ("preparation", "executor"),
            ("executor", "preparation"),
        ):
            with self.subTest(first=first, second=second):
                resolved = self._resolve_short_imports(first, second)
                expected_root = (SOURCE / first).resolve()
                self.assertEqual(
                    Path(resolved["models"]).resolve(),
                    expected_root / "models" / "__init__.py",
                )
                self.assertEqual(
                    Path(resolved["image_processing"]).resolve(),
                    expected_root / "image_processing" / "__init__.py",
                )
                self.assertEqual(
                    Path(resolved["pipeline"]).resolve(),
                    expected_root / "image_processing" / "pipeline.py",
                )

    def test_preparation_and_executor_export_the_same_model_classes(self) -> None:
        script = """
import json
import sys
sys.path.insert(0, sys.argv[1])
from preparation.models import DrawingPlan as PreparationPlan
from preparation.models import Point as PreparationPoint
from preparation.models import Stroke as PreparationStroke
from executor.models import DrawingPlan as ExecutorPlan
from executor.models import Point as ExecutorPoint
from executor.models import Stroke as ExecutorStroke
from geometry_models import DrawingPlan, Point, Stroke
print(json.dumps({
    "point_shared": PreparationPoint is ExecutorPoint is Point,
    "stroke_shared": PreparationStroke is ExecutorStroke is Stroke,
    "plan_shared": PreparationPlan is ExecutorPlan is DrawingPlan,
    "point_module": PreparationPoint.__module__,
    "stroke_module": PreparationStroke.__module__,
    "plan_module": PreparationPlan.__module__,
}))
"""
        completed = subprocess.run(
            [sys.executable, "-c", script, str(SOURCE)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        resolved = json.loads(completed.stdout)
        self.assertTrue(resolved["point_shared"], resolved)
        self.assertTrue(resolved["stroke_shared"], resolved)
        self.assertTrue(resolved["plan_shared"], resolved)
        self.assertEqual(resolved["point_module"], "geometry_models.point")
        self.assertEqual(resolved["stroke_module"], "geometry_models.stroke")
        self.assertEqual(resolved["plan_module"], "geometry_models.drawing_plan")

    def test_legacy_drawing_plan_json_without_optional_fields_is_loadable(self) -> None:
        legacy_plan = {
            "canvas": {"width": 10, "height": 8},
            "strokes": [
                {
                    "name": "legacy-line",
                    "points": [{"x": 1, "y": 2}, {"x": 7, "y": 2}],
                }
            ],
        }
        with tempfile.TemporaryDirectory(prefix="autodraw-legacy-plan-") as directory:
            path = Path(directory) / "legacy-plan.json"
            path.write_text(json.dumps(legacy_plan), encoding="utf-8")
            loaded = DrawingPlan.load(path)

        self.assertEqual((loaded.width, loaded.height), (10, 8))
        self.assertEqual(loaded.schema_version, 1)
        self.assertEqual(loaded.stroke_count, 1)
        self.assertFalse(loaded.strokes[0].closed)
        self.assertEqual(loaded.strokes[0].metadata, {})
        self.assertEqual(loaded.strokes[0].points[0].to_dict(), {"x": 1.0, "y": 2.0})


if __name__ == "__main__":
    unittest.main()
