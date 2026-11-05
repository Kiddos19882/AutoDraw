from __future__ import annotations

import pytest

from game_monitor_bridge_server import render_bridge_snippet


TEMPLATE = (
    'const TOKEN = "__AUTODRAW_BRIDGE_TOKEN__";\n'
    'const ENDPOINT = "ws://127.0.0.1:8765";\n'
    'const ENABLE = "__AUTODRAW_INPUT_TELEMETRY_ENABLED__" === "true";\n'
)


@pytest.mark.parametrize("enabled,expected", [(False, "false"), (True, "true")])
def test_render_bridge_snippet_sets_telemetry_opt_in(enabled: bool, expected: str) -> None:
    result = render_bridge_snippet(
        TEMPLATE, "one-time-test-token", 8766,
        enable_input_telemetry=enabled,
    )
    assert "one-time-test-token" in result
    assert "ws://127.0.0.1:8766" in result
    assert f'=== "{expected}"' in result
    assert "__AUTODRAW_BRIDGE_TOKEN__" not in result
    assert "__AUTODRAW_INPUT_TELEMETRY_ENABLED__" not in result


def test_render_bridge_snippet_fails_closed_on_unresolved_or_missing_placeholders() -> None:
    with pytest.raises(ValueError, match="token placeholder"):
        render_bridge_snippet(
            TEMPLATE.replace("__AUTODRAW_BRIDGE_TOKEN__", "already-replaced"),
            "token", 8765,
        )
    with pytest.raises(ValueError, match="telemetry placeholder"):
        render_bridge_snippet(
            TEMPLATE.replace("__AUTODRAW_INPUT_TELEMETRY_ENABLED__", "false"),
            "token", 8765,
        )


@pytest.mark.parametrize("port", [True, 0, 65536, "8765"])
def test_render_bridge_snippet_rejects_invalid_ports(port) -> None:
    with pytest.raises(ValueError):
        render_bridge_snippet(TEMPLATE, "token", port)


def test_render_bridge_snippet_rejects_non_boolean_telemetry_flag() -> None:
    with pytest.raises(TypeError, match="boolean"):
        render_bridge_snippet(TEMPLATE, "token", 8765, enable_input_telemetry=1)
