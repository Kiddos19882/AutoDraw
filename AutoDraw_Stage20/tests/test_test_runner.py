from __future__ import annotations

import unittest

from run_all_tests import SUITES, build_test_command


class TestRunnerConfigurationTests(unittest.TestCase):
    def test_preparation_suite_uses_pytest(self):
        runners = {name: runner for name, _workdir, runner in SUITES}
        self.assertEqual(runners["Stage 13 preparation"], "pytest")

    def test_executor_suite_remains_unittest(self):
        runners = {name: runner for name, _workdir, runner in SUITES}
        self.assertEqual(runners["Stage 14/20 executor"], "unittest")

    def test_pytest_command_targets_preparation_test_directory(self):
        _name, workdir, runner = next(
            suite for suite in SUITES if suite[0] == "Stage 13 preparation"
        )
        command = build_test_command(runner, workdir)
        self.assertEqual(command[1:5], ["-m", "pytest", "-q", "-ra"])
        self.assertEqual(command[-1], str(workdir / "tests"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
