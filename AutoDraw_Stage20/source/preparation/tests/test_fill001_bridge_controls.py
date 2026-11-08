from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import chalk_fill_ui as module
from chalk_fill_ui import Fill001Tab


class Variable:
    def __init__(self):
        self.value = ""

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


def make_tab(tmp_path, *, protocol="FILL001_SMOOTH_AB_V3"):
    calls = []

    class Brush:
        bridge_input_telemetry_requested = True

        def start_game_monitor_bridge(self, **kwargs):
            calls.append(("start", kwargs))
            return True

        def copy_game_monitor_source(self):
            calls.append(("monitor", None))

        def copy_game_monitor_bridge_snippet(self):
            calls.append(("snippet", None))

    tab = Fill001Tab.__new__(Fill001Tab)
    tab.root = object()
    tab.output_dir = tmp_path / "fill001"
    tab.brush_tab = Brush()
    tab.bridge_status_var = Variable()
    tab._selected_task = lambda: {"task_id": "test-v3", "experiment_protocol": protocol}
    return tab, calls


def test_fill001_buttons_force_v3_telemetry_and_reuse_existing_copy_methods(tmp_path):
    tab, calls = make_tab(tmp_path)
    tab.start_fill001_bridge()
    tab.copy_fill001_monitor()
    tab.copy_fill001_bridge_snippet()
    assert calls == [
        ("start", {"require_input_telemetry": True}),
        ("monitor", None), ("snippet", None),
    ]
    assert "Telemetry ON" in tab.bridge_status_var.get()


def test_fill001_bridge_start_does_not_claim_success_on_rejection(tmp_path):
    tab, _ = make_tab(tmp_path)
    tab.brush_tab.start_game_monitor_bridge = lambda **_: False
    tab.start_fill001_bridge()
    assert "не запущен" in tab.bridge_status_var.get()


def test_connection_check_rejects_missing_v3_telemetry_before_preflight(tmp_path, monkeypatch):
    tab, _ = make_tab(tmp_path)
    tab.brush_tab.bridge_input_telemetry_requested = False
    monkeypatch.setattr(module, "inspect_diagnostic_preflight",
                        lambda *args: pytest.fail("No inspect on wrong Bridge mode"))
    tab.check_fill001_bridge()
    assert "BLOCKED" in tab.bridge_status_var.get()


def test_connection_check_uses_live_bridge_session_and_reports_only_actual_readiness(tmp_path, monkeypatch):
    tab, _ = make_tab(tmp_path)
    session_file = tmp_path / "session.json"
    session_file.write_text(json.dumps({
        "bridge_configuration": {"inputTelemetry": {"requested": True, "enabled": True}},
        "bridge_diagnostics": {"last_monitor_status": {
            "inputTelemetryEnabled": True,
        }},
    }), encoding="utf-8")
    roots = []

    def ready(root, task):
        roots.append((root, task["task_id"]))
        return {"session_id": "authenticated-session", "session_file": str(session_file)}

    monkeypatch.setattr(module, "inspect_diagnostic_preflight", ready)
    tab.check_fill001_bridge()
    assert roots == [(tmp_path / "game_monitor_bridge", "test-v3")]
    assert "ГОТОВО" in tab.bridge_status_var.get()
    assert "authenticated-session" in tab.bridge_status_var.get()

    session_file.write_text(json.dumps({
        "bridge_configuration": {"inputTelemetry": {"requested": True, "enabled": False}},
        "bridge_diagnostics": {"last_monitor_status": {"inputTelemetryEnabled": False}},
    }), encoding="utf-8")
    tab.check_fill001_bridge()
    assert "BLOCKED" in tab.bridge_status_var.get()


def test_connection_check_reports_no_manifest_or_stale_session(tmp_path, monkeypatch):
    tab, _ = make_tab(tmp_path)
    tab._selected_task = lambda: None
    tab.check_fill001_bridge()
    assert "Сначала создайте" in tab.bridge_status_var.get()
    tab._selected_task = lambda: {"task_id": "test-v3",
                                  "experiment_protocol": "FILL001_SMOOTH_AB_V3"}
    def stale(*args):
        raise ValueError("Heartbeat устарел")
    monkeypatch.setattr(module, "inspect_diagnostic_preflight", stale)
    tab.check_fill001_bridge()
    assert "НЕ ГОТОВО" in tab.bridge_status_var.get()
    assert "Heartbeat устарел" in tab.bridge_status_var.get()
