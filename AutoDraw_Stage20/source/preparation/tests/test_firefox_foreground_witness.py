"""Strict foreground PID validation for a dedicated Selenium Firefox session."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from firefox_foreground_witness import (
    FirefoxForegroundError, active_window_process_id, firefox_foreground_witness,
)


def test_matching_real_firefox_browser_pid_can_pass():
    driver = SimpleNamespace(capabilities={"browserName": "firefox", "moz:processID": 5421})
    assert firefox_foreground_witness(driver, active_pid_provider=lambda: 5421)
    assert not firefox_foreground_witness(driver, active_pid_provider=lambda: 5422)


@pytest.mark.parametrize("capabilities", [
    {}, {"browserName": "chrome", "moz:processID": 5421},
    {"browserName": "firefox"},
    {"browserName": "firefox", "moz:processID": True},
    {"browserName": "firefox", "moz:processID": "5421"},
    {"browserName": "firefox", "moz:processID": -1},
])
def test_untrusted_browser_identity_never_accepts_matching_foreground(capabilities):
    driver = SimpleNamespace(capabilities=capabilities)
    assert not firefox_foreground_witness(driver, active_pid_provider=lambda: 5421)


def test_native_foreground_lookup_failure_blocks():
    driver = SimpleNamespace(capabilities={"browserName": "firefox", "moz:processID": 5421})
    assert not firefox_foreground_witness(
        driver,
        active_pid_provider=lambda: (_ for _ in ()).throw(
            FirefoxForegroundError("blocked")
        ),
    )


def test_non_integer_process_id_rejected():
    driver = SimpleNamespace(capabilities={"browserName": "firefox", "moz:processID": 5421})
    assert not firefox_foreground_witness(driver, active_pid_provider=lambda: True)
    assert not firefox_foreground_witness(driver, active_pid_provider=lambda: "5421")
