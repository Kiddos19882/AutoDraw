"""Ensure series ROI uses the *existing* V5 passive probe without pointer input.

No Selenium session or mouse required in this synthetic test.
"""
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
