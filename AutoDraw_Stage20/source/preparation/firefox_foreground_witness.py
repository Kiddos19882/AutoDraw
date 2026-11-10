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
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
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



def request_owned_firefox_window_focus(expected_pid: int) -> bool:
    """Activate only one verified Firefox top-level window; never click."""
    if sys.platform != "win32" or type(expected_pid) is not int or expected_pid <= 0:
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [CALLBACK, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    windows: list[int] = []

    @CALLBACK
    def visit(hwnd: int, _param: int) -> bool:
        pid = wintypes.DWORD(0)
        if (user32.IsWindowVisible(hwnd)
                and not user32.GetWindow(hwnd, 4)  # GW_OWNER
                and user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                and pid.value == expected_pid):
            windows.append(hwnd)
        return True

    if not user32.EnumWindows(visit, 0) or len(windows) != 1:
        return False
    # SW_RESTORE and SetForegroundWindow do not produce game input.
    hwnd = windows[0]
    user32.ShowWindow(hwnd, 9)
    return bool(user32.SetForegroundWindow(hwnd))


def establish_firefox_foreground(
    driver: Any,
    *,
    active_pid_provider: Callable[[], int] = active_window_process_id,
    sleep_seconds: float = 0.4,
    sleep_fn: Callable[[float], None] | None = None,
    native_focus_request: Callable[[int], bool] | None = None,
) -> None:
    """Verify or focus the *owned* Firefox window without desktop input.

    A WebDriver window switch is the only permitted focus attempt.  After
    that switch a fresh Win32 foreground PID check is still mandatory.  No
    fallback to matching titles, guessing window positions or clicking the
    canvas is allowed.
    """
    caps = getattr(driver, "capabilities", None)
    expected = caps.get("moz:processID") if isinstance(caps, dict) else None
    if (not isinstance(caps, dict) or caps.get("browserName") != "firefox"
            or type(expected) is not int or expected <= 0):
        raise FirefoxForegroundError(
            "BLOCKED: GeckoDriver did not provide a valid Firefox browser PID."
        )

    def foreground_pid() -> int | None:
        try:
            value = active_pid_provider()
        except (OSError, RuntimeError, ValueError, TypeError):
            return None
        return value if type(value) is int and value > 0 else None

    before = foreground_pid()
    if before == expected:
        return

    try:
        # WebDriver's own window activation does not touch the game canvas.
        driver.switch_to.window(driver.current_window_handle)
    except Exception as exc:
        raise FirefoxForegroundError(
            f"BLOCKED: Firefox focus request failed; expected PID={expected}; "
            f"previous foreground PID={before}."
        ) from exc

    if sleep_fn is None:
        import time
        sleep_fn = time.sleep
    sleep_fn(sleep_seconds)
    after = foreground_pid()
    if after != expected:
        if native_focus_request is None:
            native_focus_request = request_owned_firefox_window_focus
        try:
            requested = native_focus_request(expected) is True
        except (OSError, RuntimeError, ValueError, TypeError):
            requested = False
        if requested:
            sleep_fn(sleep_seconds)
        after_native = foreground_pid()
        if after_native != expected:
            raise FirefoxForegroundError(
                f"BLOCKED: Firefox is not proven to be the foreground window; "
                f"expected PID={expected}; before PID={before}; "
                f"after WebDriver PID={after}; after native PID={after_native}; "
                f"native focus request accepted={requested}. "
                "No mouse movement permitted."
            )


def wait_for_operator_firefox_foreground(
    driver: Any, *,
    cancel_event: Any,
    timeout_seconds: float = 90.0,
    poll_seconds: float = 0.2,
    required_consecutive_matches: int = 3,
    active_pid_provider: Callable[[], int] = active_window_process_id,
    monotonic_fn: Callable[[], float] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> None:
    """Wait for USER-initiated foreground activation; never focus or click.

    GeckoDriver's exact Firefox PID and Win32 GetForegroundWindow owner must
    match repeatedly.  The operator clicks Firefox chrome outside the canvas.
    The caller must subsequently recheck the foreground before EVERY move.
    """
    import time

    caps = getattr(driver, "capabilities", None)
    expected = caps.get("moz:processID") if isinstance(caps, dict) else None
    if (not isinstance(caps, dict) or caps.get("browserName") != "firefox"
            or type(expected) is not int or expected <= 0):
        raise FirefoxForegroundError(
            "BLOCKED: GeckoDriver did not provide a valid Firefox browser PID."
        )
    if (not 0 < timeout_seconds <= 600 or not 0 < poll_seconds <= 5
            or type(required_consecutive_matches) is not int
            or required_consecutive_matches < 2):
        raise FirefoxForegroundError("BLOCKED: Invalid foreground wait policy.")
    if monotonic_fn is None:
        monotonic_fn = time.monotonic
    if sleep_fn is None:
        sleep_fn = time.sleep
    deadline = monotonic_fn() + timeout_seconds
    matches = 0
    last_pid: int | None = None
    while monotonic_fn() < deadline:
        if cancel_event.is_set():
            raise FirefoxForegroundError(
                "BLOCKED: Operator cancelled Firefox foreground confirmation."
            )
        try:
            current = active_pid_provider()
        except (OSError, RuntimeError, ValueError, TypeError):
            current = None
        last_pid = current if type(current) is int and current > 0 else None
        if last_pid == expected:
            matches += 1
            if matches >= required_consecutive_matches:
                return
        else:
            matches = 0
        sleep_fn(poll_seconds)
    raise FirefoxForegroundError(
        f"BLOCKED: Firefox was not manually activated within {timeout_seconds:g}s; "
        f"expected PID={expected}; last foreground PID={last_pid}. "
        "No mouse movement permitted."
    )
