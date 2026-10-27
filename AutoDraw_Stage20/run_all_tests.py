from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PREPARATION_ROOT = ROOT / "source" / "preparation"
EXECUTOR_ROOT = ROOT / "source" / "executor"

# The preparation suite contains ordinary pytest functions, not only
# unittest.TestCase classes. Running it through unittest discovery silently
# skips those functions and can fail when pytest is not installed.
SUITES = (
    ("Unified application and packaging", ROOT, "unittest"),
    ("Stage 13 preparation", PREPARATION_ROOT, "pytest"),
    ("Stage 14/20 executor", EXECUTOR_ROOT, "unittest"),
)


def build_test_command(runner: str, workdir: Path) -> list[str]:
    """Return the command that actually executes every test in a suite."""
    if runner == "pytest":
        return [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-ra",
            str(workdir / "tests"),
        ]
    if runner == "unittest":
        return [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ]
    raise ValueError(f"Неизвестный тестовый runner: {runner!r}")


def main() -> int:
    # Keep the same import paths as the Windows build and the CI test jobs.
    env = os.environ.copy()
    paths = [str(ROOT), str(PREPARATION_ROOT), str(EXECUTOR_ROOT)]
    existing = env.get("PYTHONPATH", "")
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)

    for name, workdir, runner in SUITES:
        print(f"\n{'=' * 16} {name} ({runner}) {'=' * 16}", flush=True)
        command = build_test_command(runner, workdir)
        result = subprocess.run(
            command,
            cwd=workdir,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            print(f"\nFAILED: {name} (runner={runner})")
            return result.returncode

    print("\nALL TEST SUITES PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
