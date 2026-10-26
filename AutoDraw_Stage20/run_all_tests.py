from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREPARATION_ROOT = ROOT / "source" / "preparation"
EXECUTOR_ROOT = ROOT / "source" / "executor"
SUITES = (
    ("Unified application and packaging", ROOT),
    ("Stage 13 preparation", PREPARATION_ROOT),
    ("Stage 14/20 executor", EXECUTOR_ROOT),
)


def main() -> int:
    # Each suite runs in a separate process. Explicitly provide both source folders so
    # executor color-plan tests can import the shared Stage 18/19 preparation modules
    # when run from build_windows.bat without a hand-configured PYTHONPATH.
    env = os.environ.copy()
    paths = [str(PREPARATION_ROOT), str(EXECUTOR_ROOT)]
    existing = env.get("PYTHONPATH", "")
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)

    for name, workdir in SUITES:
        print(f"\n{'=' * 16} {name} {'=' * 16}", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=workdir,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            print(f"\nFAILED: {name}")
            return result.returncode
    print("\nALL TEST SUITES PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
