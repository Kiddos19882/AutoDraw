"""Conservative Windows foreground witness for an owned Selenium Firefox session.

The Firefox process ID is supplied by GeckoDriver's moz:processID capability.
The active top-level window must belong to that exact browser process.
No keyboard or mouse operations are performed.
"""
from __future__ import annotations

import sys
from typing import Any, Callable


class FirefoxForegroundError(ValueError):
    pass


def active_window_process_id() -> int:
    """Read the actual native Win32 foreground window's process ID."""
    if sys.platform != "win32":
        raise FirefoxForegroundError("Native foreground evidence requires Windows.")
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        raise FirefoxForegroundError("No foreground window.")
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    process_id = wintypes.DWORD(0)
    if not user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id)):
        raise FirefoxForegroundError("Win32 foreground PID lookup failed.")
    if process_id.value <= 0:
        raise FirefoxForegroundError("No valid foreground process.")
    return int(process_id.value)


def firefox_foreground_witness(
    driver: Any,
    *,
    active_pid_provider: Callable[[], int] = active_window_process_id,
) -> bool:
    """Return True ONLY when the OS foreground belongs to GeckoDriver Firefox.

    A missing moz:processID, wrong browser, forged/non-integer PID, or Win32
    failure all safely return False; never trust a window title or CSS focus.
    """
    caps = getattr(driver, "capabilities", None)
    if not isinstance(caps, dict) or caps.get("browserName") != "firefox":
        return False
    browser_pid = caps.get("moz:processID")
    if type(browser_pid) is not int or browser_pid <= 0:
        return False
    try:
        active_pid = active_pid_provider()
    except (OSError, RuntimeError, FirefoxForegroundError, ValueError):
        return False
    return type(active_pid) is int and active_pid == browser_pid
