"""Ensure series ROI uses the *existing* V5 passive probe without pointer input.

No Selenium session or mouse required in this synthetic test.
"""
import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from fill001_series_runner import SeriesBlocked, build_manifest
from fill001_series_handoff import build_series_source_plan
from fill001_firefox_auto_probe import collect_verified_series_firefox_roi


def _manifest():
    return build_manifest(
        cycles=1, figures_per_cycle=1, shapes=["wide_irregular"],
        methods=["spaced_scanlines"], radii=[10], series_id="series-probe"
    )


def test_signed_series_plan_delegates_existing_passive_probe():
    m = _manifest()
    plan = build_series_source_plan(m, m["tasks"][0]["task_id"])
    expected = ({"mapped": True}, {"mapping": True}, {"roi": True})
    with patch("fill001_firefox_auto_probe._collect_verified_boardpane_roi", return_value=expected) as probe:
        result = collect_verified_series_firefox_roi(
            m, "driver", "bridge", "sid", plan,
            native_mouse="native", now_utc="clock",
            firefox_foreground_checker=lambda: True,
        )
    assert result == expected
    probe.assert_called_once()


def test_tampered_series_plan_blocked_before_any_browser_action():
    m = _manifest()
    plan = build_series_source_plan(m, m["tasks"][0]["task_id"])
    plan["strokes"][0]["points"][0]["x"] = 9999.0
    with patch("fill001_firefox_auto_probe._collect_verified_boardpane_roi") as probe:
        with pytest.raises(SeriesBlocked):
            collect_verified_series_firefox_roi(
                m, "driver", "bridge", "sid", plan,
                native_mouse="native", now_utc="clock",
            )
        probe.assert_not_called()

def test_series_firefox_mode_does_not_depend_on_v5_trim_candidate():
    """Source contract: both modes share Selenium, but series skips V5 trim."""
    source = (Path(__file__).resolve().parents[1] / "chalk_fill_ui.py").read_text(
        encoding="utf-8"
    )
    module = ast.parse(source)
    tab = next(node for node in module.body
               if isinstance(node, ast.ClassDef) and node.name == "Fill001Tab")
    worker = next(node for node in tab.body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == "_firefox_worker")
    series_branches = [
        node for node in ast.walk(worker) if isinstance(node, ast.If)
        and isinstance(node.test, ast.Attribute)
        and node.test.attr == "_firefox_execute_series"
    ]
    assert len(series_branches) == 1
    series = series_branches[0]
    assert any(isinstance(node, ast.Return)
               for part in series.body for node in ast.walk(part))

    def calls(name):
        return [node for node in ast.walk(worker)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id == name]

    # Both paths still use the existing WebDriver and Monitor attachment.
    assert len(calls("open_firefox")) == 1
    assert len(calls("attach_monitor_after_confirmation")) == 1
    assert calls("open_firefox")[0].lineno < series.lineno
    assert calls("attach_monitor_after_confirmation")[0].lineno < series.lineno
    # The V5-only 29-stroke fixture must not gate the signed series path.
    assert len(calls("build_fill001_v5_source_plan")) == 1
    assert calls("build_fill001_v5_source_plan")[0].lineno > series.end_lineno
    assert len(calls("collect_verified_v5_firefox_roi")) == 1
    assert calls("collect_verified_v5_firefox_roi")[0].lineno > series.end_lineno
