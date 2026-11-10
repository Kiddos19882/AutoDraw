"""Strict foreground PID validation for a dedicated Selenium Firefox session."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from firefox_foreground_witness import (
    FirefoxForegroundError, active_window_process_id, firefox_foreground_witness,
    establish_firefox_foreground,
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


class _FakeSwitch:
    def __init__(self, callback):
        self.callback = callback
        self.calls = []
    def window(self, handle):
        self.calls.append(handle)
        self.callback()


class _FakeDriver:
    def __init__(self, before_focus, on_focus=lambda: None, expected=5421):
        self.capabilities = {"browserName": "firefox", "moz:processID": expected}
        self.current_window_handle = "owned-firefox-window"
        self.switch_to = _FakeSwitch(on_focus)


def test_foreground_already_matches_requires_no_focus():
    driver = _FakeDriver(True)
    establish_firefox_foreground(
        driver, active_pid_provider=lambda: 5421,
        sleep_fn=lambda seconds: (_ for _ in ()).throw(
            AssertionError("No focus delay needed")
        ),
    )
    assert driver.switch_to.calls == []


def test_safe_webdriver_focus_must_be_verified_against_native_pid():
    state = {"active_pid": 1001, "sleep_calls": []}
    driver = _FakeDriver(
        False, on_focus=lambda: state.update(active_pid=5421),
    )
    establish_firefox_foreground(
        driver, active_pid_provider=lambda: state["active_pid"],
        sleep_fn=lambda seconds: state["sleep_calls"].append(seconds),
    )
    assert driver.switch_to.calls == ["owned-firefox-window"]
    assert state["sleep_calls"] == [0.4]


def test_focus_request_does_not_bypass_pid_mismatch():
    driver = _FakeDriver(False)
    with pytest.raises(
        FirefoxForegroundError,
        match="expected PID=5421; before PID=1001; after WebDriver PID=1001; after native PID=1001",
    ):
        establish_firefox_foreground(
            driver, active_pid_provider=lambda: 1001,
            sleep_fn=lambda _: None,
            native_focus_request=lambda pid: False,
        )
    assert driver.switch_to.calls == ["owned-firefox-window"]


def test_missing_gecko_pid_never_requests_browser_focus():
    driver = _FakeDriver(False, expected="5421")
    with pytest.raises(FirefoxForegroundError, match="valid Firefox browser PID"):
        establish_firefox_foreground(
            driver, active_pid_provider=lambda: 5421,
            sleep_fn=lambda _: None,
            native_focus_request=lambda pid: False,
        )
    assert driver.switch_to.calls == []


def test_native_foreground_failure_stays_fail_closed():
    driver = _FakeDriver(False)
    with pytest.raises(FirefoxForegroundError, match="after native PID=None"):
        establish_firefox_foreground(
            driver,
            active_pid_provider=lambda: (_ for _ in ()).throw(
                FirefoxForegroundError("Cannot inspect foreground window")
            ),
            sleep_fn=lambda _: None,
        )


def test_owned_win32_focus_request_must_recheck_pid():
    state = {"pid": 932, "requested": []}
    driver = _FakeDriver(False)
    def request(pid):
        state["requested"].append(pid)
        state["pid"] = 5372
        return True
    driver.capabilities["moz:processID"] = 5372
    establish_firefox_foreground(
        driver, active_pid_provider=lambda: state["pid"],
        native_focus_request=request, sleep_fn=lambda _: None,
    )
    assert state["requested"] == [5372]
    assert driver.switch_to.calls == ["owned-firefox-window"]


def test_win32_focus_refusal_stays_fail_closed():
    driver = _FakeDriver(False, expected=5372)
    with pytest.raises(FirefoxForegroundError, match="native focus request accepted=False"):
        establish_firefox_foreground(
            driver, active_pid_provider=lambda: 932,
            native_focus_request=lambda pid: False, sleep_fn=lambda _: None,
        )
    assert driver.switch_to.calls == ["owned-firefox-window"]


def test_wrong_native_pid_after_accepted_focus_still_blocks():
    driver = _FakeDriver(False, expected=5372)
    with pytest.raises(FirefoxForegroundError, match="after native PID=932"):
        establish_firefox_foreground(
            driver, active_pid_provider=lambda: 932,
            native_focus_request=lambda pid: True, sleep_fn=lambda _: None,
        )
