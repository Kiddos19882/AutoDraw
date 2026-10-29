from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"


class ImportResolutionDiagnosticsTests(unittest.TestCase):
    """Document how short imports resolve when both component roots are present.

    This is a baseline diagnostic, not a proposed architecture: it intentionally
    records the current order-dependent behavior before any package moves.
    """

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

    def test_preparation_and_executor_models_are_identical_blobs_today(self) -> None:
        # Keep this test explicit: the current duplicate files are a known
        # compatibility risk if either copy changes independently.
        preparation = SOURCE / "preparation" / "models"
        executor = SOURCE / "executor" / "models"
        for filename in ("point.py", "stroke.py", "drawing_plan.py"):
            with self.subTest(filename=filename):
                self.assertEqual(
                    (preparation / filename).read_bytes(),
                    (executor / filename).read_bytes(),
                    f"Model copies diverged: {filename}",
                )


if __name__ == "__main__":
    unittest.main()
