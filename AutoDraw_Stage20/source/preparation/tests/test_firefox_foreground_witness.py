"""Strict foreground PID validation for a dedicated Selenium Firefox session."""
from __future__ import annotations

from types import SimpleNamespace
import threading

import pytest

from firefox_foreground_witness import (
    FirefoxForegroundError, active_window_process_id, firefox_foreground_witness,
    wait_for_operator_firefox_foreground,
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


class _FakeDriver:
    def __init__(self, expected=5421):
        self.capabilities = {"browserName": "firefox", "moz:processID": expected}
        self.focus_calls = 0

def _virtual_clock_pid_provider(sequence):
    state = {"now": 0.0, "index": 0}
    def clock():
        return state["now"]
    def sleep(seconds):
        state["now"] += seconds
    def pid():
        value = sequence[min(state["index"], len(sequence) - 1)]
        state["index"] += 1
        return value
    return clock, sleep, pid, state


def test_operator_activation_requires_three_consecutive_native_pid_matches():
    driver = _FakeDriver(expected=5372)
    clock, sleep, pid, state = _virtual_clock_pid_provider(
        [932, 5372, 932, 5372, 5372, 5372]
    )
    wait_for_operator_firefox_foreground(
        driver, cancel_event=threading.Event(),
        timeout_seconds=5, poll_seconds=.1,
        active_pid_provider=pid, monotonic_fn=clock, sleep_fn=sleep,
    )
    assert state["index"] == 6
    assert driver.focus_calls == 0


def test_operator_activation_timeout_blocks_without_focus_or_input():
    driver = _FakeDriver(expected=5372)
    clock, sleep, pid, _ = _virtual_clock_pid_provider([932])
    with pytest.raises(FirefoxForegroundError, match="manually activated"):
        wait_for_operator_firefox_foreground(
            driver, cancel_event=threading.Event(),
            timeout_seconds=.5, poll_seconds=.1,
            active_pid_provider=pid, monotonic_fn=clock, sleep_fn=sleep,
        )
    assert driver.focus_calls == 0


def test_operator_activation_cancellation_is_fail_closed():
    driver = _FakeDriver(expected=5372)
    stop = threading.Event()
    stop.set()
    clock, sleep, pid, _ = _virtual_clock_pid_provider([5372])
    with pytest.raises(FirefoxForegroundError, match="cancelled"):
        wait_for_operator_firefox_foreground(
            driver, cancel_event=stop, timeout_seconds=5,
            active_pid_provider=pid, monotonic_fn=clock, sleep_fn=sleep,
        )
    assert driver.focus_calls == 0


def test_operator_activation_rejects_invalid_geckodriver_pid_before_poll():
    driver = _FakeDriver(expected="5372")
    clock, sleep, pid, _ = _virtual_clock_pid_provider([5372])
    with pytest.raises(FirefoxForegroundError, match="valid Firefox browser PID"):
        wait_for_operator_firefox_foreground(
            driver, cancel_event=threading.Event(),
            active_pid_provider=pid, monotonic_fn=clock, sleep_fn=sleep,
        )
    assert driver.focus_calls == 0
