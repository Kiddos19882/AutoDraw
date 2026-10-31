from brush_radius_feedback import (
    calculate_radius_correction_target,
    monitor_radius_from_status,
)


def test_monitor_radius_prefers_current_radius_scalar():
    assert monitor_radius_from_status({
        "snapshot": {"currentRadius": 4, "radius": [30, 4]}
    }) == 4


def test_monitor_radius_supports_radius_array_fallback():
    assert monitor_radius_from_status({"snapshot": {"radius": [30, 5]}}) == 5


def test_monitor_radius_rejects_unavailable_and_invalid_values():
    assert monitor_radius_from_status({"snapshot": None}) is None
    assert monitor_radius_from_status({"snapshot": {"currentRadius": 0}}) is None
    assert monitor_radius_from_status({"snapshot": {"currentRadius": True}}) is None


def test_radius_feedback_moves_towards_30_when_observed_radius_is_too_small():
    target = calculate_radius_correction_target(
        high_point=(100, 500), high_radius=30,
        low_point=(390, 500), low_radius=4,
        requested_radius=5,
    )
    assert 100 < target[0] < 390
    assert target[0] < 390


def test_radius_feedback_moves_towards_1_when_observed_radius_is_too_large():
    target = calculate_radius_correction_target(
        high_point=(200, 500), high_radius=6,
        low_point=(390, 500), low_radius=1,
        requested_radius=5,
    )
    assert 200 < target[0] < 390


def test_radius_feedback_returns_known_endpoint_for_radius_one_or_thirty():
    assert calculate_radius_correction_target((100, 500), 30, (390, 500), 1, 30) == (100, 500)
    assert calculate_radius_correction_target((100, 500), 30, (390, 500), 1, 1) == (390, 500)


def test_radius_feedback_rejects_invalid_bracket():
    import pytest
    with pytest.raises(ValueError):
        calculate_radius_correction_target((100, 500), 4, (390, 500), 1, 5)
