"""Fail-closed runtime baseline gate, with frozen synthetic Monitor evidence."""
import json
from datetime import timedelta

import pytest

from fill001_monitor_diagnostic import _boardpane_mapping_fingerprint
from fill001_v5_handoff import Fill001V5Error
from fill001_v5_live_gate import verify_v5_live_gate
from test_fill001_v5_auto_roi import build_fixture, NOW, SID


def fixture(tmp_path, *, points=1):
    session, _, _ = build_fixture()
    session["page"] = {"origin": "https://eufbpet.hust.me"}
    session["bridge_diagnostics"]["last_message_type"] = "heartbeat"
    session["bridge_diagnostics"]["collector_sequence_gap_count"] = 0
    status = session["bridge_diagnostics"]["last_monitor_status"]
    status["snapshot"] = {
        "isExact": True, "pointCount": points, "maxPoints": 6000,
        "remainingPoints": 6000 - points, "currentRadius": 10,
    }
    mapping = _boardpane_mapping_fingerprint(session["renderer_geometry"])
    folder = tmp_path / SID
    folder.mkdir()
    path = folder / "session.json"
    path.write_text(json.dumps(session), encoding="utf-8")
    return path, mapping


def verify(tmp_path, mapping, **kwargs):
    return verify_v5_live_gate(
        tmp_path, session_id=SID, expected_mapping_sha256=mapping,
        now_utc=NOW, **kwargs,
    )


def test_clean_exact_one_current_session_can_pass(tmp_path):
    path, mapping = fixture(tmp_path)
    result = verify(tmp_path, mapping)
    assert result["pointCount"] == 1
    assert result["blank_counter_confirmed"] is True
    assert result["stage6_execution_allowed"] is False
    assert result["currentRadius"] == 10


@pytest.mark.parametrize("points", [0, 2, 3, 6000])
def test_clean_only_when_point_count_exactly_one(tmp_path, points):
    path, mapping = fixture(tmp_path, points=points)
    with pytest.raises(Fill001V5Error, match="not clean"):
        verify(tmp_path, mapping)


@pytest.mark.parametrize("change,needle", [
    ("session_id", "session"),
    ("origin", "session"),
    ("closed", "session"),
    ("telemetry", "session"),
    ("counter", "counters"),
    ("radius", "radius"),
    ("geometry", "moved"),
    ("stale", "stale"),
])
def test_gate_rejects_changed_session_telemetry_or_mapping(tmp_path, change, needle):
    path, mapping = fixture(tmp_path)
    record = json.loads(path.read_text(encoding="utf-8"))
    if change == "session_id":
        record["session_id"] = "other-session"
    elif change == "origin":
        record["page"]["origin"] = "https://wrong.example"
    elif change == "closed":
        record["bridge_diagnostics"]["connection_closed"] = True
    elif change == "telemetry":
        record["bridge_configuration"]["inputTelemetry"]["enabled"] = False
    elif change == "counter":
        record["bridge_diagnostics"]["last_monitor_status"]["snapshot"]["remainingPoints"] = 4000
    elif change == "radius":
        record["bridge_diagnostics"]["last_monitor_status"]["snapshot"]["currentRadius"] = None
    elif change == "geometry":
        record["renderer_geometry"]["players"][0]["boardClientCorners"]["topLeft"]["x"] += 10
    elif change == "stale":
        record["bridge_diagnostics"]["last_heartbeat_at_utc"] = (
            NOW - timedelta(seconds=10)
        ).isoformat()
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(Fill001V5Error, match=needle):
        verify(tmp_path, mapping)


def test_gate_requires_exact_selected_session_not_just_newest(tmp_path):
    path, mapping = fixture(tmp_path)
    with pytest.raises(Fill001V5Error, match="missing"):
        verify_v5_live_gate(
            tmp_path, session_id="another-session",
            expected_mapping_sha256=mapping, now_utc=NOW,
        )


def test_v5_recent_heartbeat_remains_valid_when_latest_message_is_stroke_event(tmp_path):
    path, mapping = fixture(tmp_path)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["bridge_diagnostics"]["last_message_type"] = "event"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert verify(tmp_path, mapping)["pointCount"] == 1


@pytest.mark.parametrize("contents,error_type", [
    (None, "FileNotFoundError"),
    ("{not-valid-json", "JSONDecodeError"),
])
def test_session_read_failure_reports_cause_but_stays_fail_closed(
        tmp_path, contents, error_type):
    path, mapping = fixture(tmp_path)
    if contents is None:
        path.unlink()
    else:
        path.write_text(contents, encoding="utf-8")
    with pytest.raises(Fill001V5Error, match="read_error=" + error_type) as exc:
        verify(tmp_path, mapping)
    assert exc.value.__cause__ is not None


def test_session_permission_error_reports_cause_without_disabling_gate(
        tmp_path, monkeypatch):
    path, mapping = fixture(tmp_path)
    real_read_text = type(path).read_text

    def deny_session_read(self, *args, **kwargs):
        if self == path:
            raise PermissionError(13, "Access denied")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(type(path), "read_text", deny_session_read)
    with pytest.raises(Fill001V5Error, match="read_error=PermissionError") as exc:
        verify(tmp_path, mapping)
    assert isinstance(exc.value.__cause__, PermissionError)


def test_temporary_bridge_permission_error_recovers_with_fresh_full_validation(
        tmp_path, monkeypatch):
    path, mapping = fixture(tmp_path)
    native_read = type(path).read_text
    calls = []
    waits = []

    def transient(self, *args, **kwargs):
        if self == path:
            calls.append(True)
            if len(calls) < 3:
                raise PermissionError(13, "Windows replace in progress")
        return native_read(self, *args, **kwargs)

    monkeypatch.setattr(type(path), "read_text", transient)
    monkeypatch.setattr("fill001_v5_live_gate.time.sleep", waits.append)
    got = verify(tmp_path, mapping)
    assert got["pointCount"] == 1
    assert len(calls) == 3
    assert waits == [0.025, 0.05]


def test_permission_retry_never_accepts_wrong_session_or_stale_heartbeat(
        tmp_path, monkeypatch):
    path, mapping = fixture(tmp_path)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["bridge_diagnostics"]["last_heartbeat_at_utc"] = (
        NOW - timedelta(seconds=10)
    ).isoformat()
    path.write_text(json.dumps(record), encoding="utf-8")
    native_read = type(path).read_text
    calls = []

    def transient(self, *args, **kwargs):
        if self == path:
            calls.append(True)
            if len(calls) == 1:
                raise PermissionError(13, "Windows replace in progress")
        return native_read(self, *args, **kwargs)

    monkeypatch.setattr(type(path), "read_text", transient)
    monkeypatch.setattr("fill001_v5_live_gate.time.sleep", lambda delay: None)
    with pytest.raises(Fill001V5Error, match="stale"):
        verify(tmp_path, mapping)
    assert len(calls) == 2


def test_persistent_permission_error_is_bounded_and_preserves_root_cause(
        tmp_path, monkeypatch):
    path, mapping = fixture(tmp_path)
    attempts = []
    waits = []

    def deny(self, *args, **kwargs):
        if self == path:
            attempts.append(True)
            raise PermissionError(13, "Access denied")
        raise AssertionError("unexpected file")

    monkeypatch.setattr(type(path), "read_text", deny)
    monkeypatch.setattr("fill001_v5_live_gate.time.sleep", waits.append)
    with pytest.raises(Fill001V5Error, match="read_error=PermissionError") as exc:
        verify(tmp_path, mapping)
    assert len(attempts) == 4
    assert waits == [0.025, 0.05, 0.1]
    assert isinstance(exc.value.__cause__, PermissionError)
