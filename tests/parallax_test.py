"""Tests for Parallax protobuf telemetry decoding."""

from __future__ import annotations

import base64
import math
import struct

import pytest
from rivian import (
    CabinPreconditioningStatus,
    CabinVentilationSetting,
    ClimateHoldSetting,
    DefrostDefogStatus,
    HvacSettingsStatus,
    ParallaxDecodeError,
    ParallaxMessage,
    PetModeStatus,
    decode_body_states,
    decode_cabin_preconditioning_status,
    decode_cabin_temperatures,
    decode_cabin_ventilation_setting,
    decode_charging_graph_global,
    decode_charging_session_live_data,
    decode_charging_session_status,
    decode_charging_time_estimation,
    decode_climate_hold_setting,
    decode_climate_hold_status,
    decode_defrost_defog_status,
    decode_high_voltage_battery_state,
    decode_hvac_settings_status,
    decode_navigation_trip_info,
    decode_navigation_trip_progress,
    decode_parallax_message,
    decode_parallax_payload,
    decode_pet_mode_status,
    decode_seat_conditioning_states,
    decode_tire_states,
    decode_vehicle_drive_mode,
    decode_vehicle_gear,
    decode_vehicle_gnss,
    decode_vehicle_odometer,
    decode_vehicle_power_state,
    decode_vehicle_range,
)


def payload(encoded: str) -> bytes:
    """Decode a captured base64 protobuf fixture."""
    return base64.b64decode(encoded)


def test_decode_high_voltage_battery_state() -> None:
    """Decode observed SOC, capacity, temperature, and state fields."""
    state = decode_high_voltage_battery_state(
        payload("ChIJAAAAoJmZVUARAAAAoEfhVkASDw00M/tBFWdm/kEdNDPrQRoAIAEwBA==")
    )
    assert math.isclose(state.soc_percent or 0, 86.4, rel_tol=1e-5)
    assert math.isclose(state.capacity_kwh or 0, 91.52, rel_tol=1e-5)
    assert state.pack_kwh == state.capacity_kwh
    assert state.range_km is None
    assert math.isclose(state.cell_average_c or 0, 31.4, rel_tol=1e-5)
    assert math.isclose(state.cell_max_c or 0, 31.8, rel_tol=1e-5)
    assert math.isclose(state.cell_min_c or 0, 29.4, rel_tol=1e-5)
    assert state.power_output_code == 1
    assert state.requires_calibration is None
    assert state.cold_weather_state_code == 4


def test_decode_vehicle_dynamics() -> None:
    """Decode range, odometer, GNSS, power, gear, and drive mode."""
    assert decode_vehicle_range(payload("CNMDEAEYAQ==")).distance_km == 467
    assert decode_vehicle_odometer(payload("CPIB")).distance_km == 242

    gnss = decode_vehicle_gnss(
        payload("CQAAAAAAAERAEQAAAAAAwFLAGQAAAAAA4F5AJQAA3EEtAAA0wlCA0JX/vDE=")
    )
    assert math.isclose(gnss.latitude or 0, 40.0)
    assert math.isclose(gnss.longitude or 0, -75.0)
    assert math.isclose(gnss.altitude_m or 0, 123.5)
    assert math.isclose(gnss.speed_m_s or 0, 27.5)
    assert math.isclose(gnss.heading_deg or 0, -45.0)
    assert gnss.gps_timestamp_ms == 1_700_000_000_000
    assert gnss.timestamp_ms == 2_015_964_782_000
    assert decode_vehicle_power_state(payload("CAM=")).state_code == 3
    assert decode_vehicle_gear(payload("CAE=")).state_code == 1
    assert decode_vehicle_drive_mode(payload("CAI=")).mode_code == 2


def test_decode_navigation() -> None:
    """Decode verified active-route progress, motion, destination, and ETA."""
    progress = decode_navigation_trip_progress(
        payload(
            "IQAAAACAHMhAKQAAAAAAIIxAMiUKEgkAAAAAAABEQBEAAAAAAMBSwBUAANxBHQAANMIogNCV/7wx"
        )
    )
    assert progress.remaining_distance_m == 12_345
    assert progress.remaining_drive_time_s == 900
    assert progress.motion is not None
    assert progress.motion.latitude == 40
    assert progress.motion.longitude == -75
    assert progress.motion.speed_m_s == 27.5
    assert progress.motion.heading_deg == -45
    assert progress.motion.timestamp_ms == 1_700_000_000_000

    info = decode_navigation_trip_info(
        payload("CgZ0cmlwLTEaIBoeChwKEgkAAAAAAABEQBEAAAAAAMBSwBgCIgRIb21lMgYIhOnPqgY=")
    )
    assert info.trip_id == "trip-1"
    assert info.destination_name == "Home"
    assert info.destination_latitude == 40
    assert info.destination_longitude == -75
    assert info.eta_timestamp_ms == 1_700_000_900_000

    empty_progress = decode_navigation_trip_progress(b"")
    empty_info = decode_navigation_trip_info(b"")
    assert empty_progress.remaining_distance_m is None
    assert empty_progress.motion is None
    assert empty_info.trip_id is None
    assert empty_info.destination_name is None


def test_decode_tires() -> None:
    """Decode all observed tire records with double pressure values."""
    states = decode_tire_states(
        payload(
            "CAESFggBEAEZXI/C9ShcB0AgASj/25PA9zMSFggCEAEZXI/C9ShcB0AgASjTwJPA9zMSFggDEAEZpHA9CtejBkAgASjn8o7A9zMSFggEEAEZMzMzMzMzB0AgASiDu5jA9zM="
        )
    )
    assert states.monitor_status_code == 1
    assert [tire.position_code for tire in states.tires] == [1, 2, 3, 4]
    assert [round(tire.pressure_bar or 0, 2) for tire in states.tires] == [
        2.92,
        2.92,
        2.83,
        2.9,
    ]
    assert all(tire.validity_code == 1 for tire in states.tires)


def test_decode_body_and_climate() -> None:
    """Decode observed lock, preconditioning, and cabin temperature payloads."""
    locks = decode_body_states(
        payload("CgQIARABCgQIAhABCgQIAxABCgQIBBABCgQIBRABCgQIBxAB")
    )
    assert [(state.position_code, state.state_code) for state in locks.states] == [
        (1, 1),
        (2, 1),
        (3, 1),
        (4, 1),
        (5, 1),
        (7, 1),
    ]
    assert decode_body_states(b"").states == ()
    assert decode_cabin_preconditioning_status(payload("CAIQAQ==")) == (
        CabinPreconditioningStatus(status_code=2, type_code=1)
    )
    assert math.isclose(
        decode_cabin_temperatures(payload("HWZm3kE=")).interior_c or 0,
        27.8,
        rel_tol=1e-5,
    )


def test_decode_observed_comfort_topics() -> None:
    """Decode captured read-only comfort settings and status payloads."""
    assert decode_hvac_settings_status(payload("DQAAvEE=")) == HvacSettingsStatus(
        target_temperature_c=23.5
    )
    assert decode_pet_mode_status(payload("CAI=")) == PetModeStatus(
        state_code=2,
        temperature_status_code=None,
    )
    assert decode_pet_mode_status(payload("GAI=")) == PetModeStatus(
        state_code=None,
        temperature_status_code=2,
    )
    assert decode_cabin_ventilation_setting(payload("CAE=")) == (
        CabinVentilationSetting(setting_code=1)
    )
    assert decode_climate_hold_setting(payload("CKA4")) == ClimateHoldSetting(
        duration_seconds=7200
    )
    assert decode_defrost_defog_status(payload("CAQ=")) == DefrostDefogStatus(
        status_code=4
    )

    hold_status = decode_climate_hold_status(payload("IgYIhOnPqgY="))
    assert hold_status.status_code is None
    assert hold_status.availability_code is None
    assert hold_status.unavailability_reason_code is None
    assert hold_status.hold_end_timestamp_ms == 1_700_000_900_000

    seats = decode_seat_conditioning_states(
        payload("CgQIARABCgQIBRABCgQIBRACCgQIBxABCgQIBxACCgQICBABCgQIChAB")
    )
    assert [
        (state.component_code, state.conditioning_type_code) for state in seats.states
    ] == [
        (1, 1),
        (5, 1),
        (5, 2),
        (7, 1),
        (7, 2),
        (8, 1),
        (10, 1),
    ]


_CLOSED_CLOSURES_PAYLOAD = (
    "CgYIARACIAEKBggCEAIgAQoGCAMQAiABCgYIBBACIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
    "CAwQAiABCgYIDRACIAEKBggOEAIgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAE="
)

_OPEN_CLOSURE_PAYLOADS = (
    (
        1,
        "CgYIARABIAEKBggCEAIgAQoGCAMQAiABCgYIBBACIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
        "CAwQAiABCgYIDRACIAEKBggOEAIgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAE=",
    ),
    (
        2,
        "CgYIARACIAEKBggCEAEgAQoGCAMQAiABCgYIBBACIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
        "CAwQAiABCgYIDRACIAEKBggOEAIgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAE=",
    ),
    (
        3,
        "CgYIARACIAEKBggCEAIgAQoGCAMQASABCgYIBBACIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
        "CAwQAiABCgYIDRACIAEKBggOEAIgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAE=",
    ),
    (
        4,
        "CgYIARACIAEKBggCEAIgAQoGCAMQAiABCgYIBBABIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
        "CAwQAiABCgYIDRACIAEKBggOEAIgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAE=",
    ),
    (
        5,
        "CgYIARACIAEKBggCEAIgAQoGCAMQAiABCgYIBBACIAEKCAgFEAEgAzAJCggIBxACIAE4AQoG"
        "CAwQAiABCgYIDRACIAEKBggOEAIgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAE=",
    ),
    (
        7,
        "CgYIARACIAEKBggCEAIgAQoGCAMQAiABCgYIBBACIAEKCAgFEAIgAzAJCggIBxABIAE4AgoG"
        "CAwQAiABCgYIDRACIAEKBggOEAIgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAE=",
    ),
    (
        12,
        "CgYIARACIAEKBggCEAIgAQoGCAMQAiABCgYIBBACIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
        "CAwQASABCgYIDRACIAEKBggOEAIgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAI=",
    ),
    (
        13,
        "CgYIARACIAEKBggCEAIgAQoGCAMQAiABCgYIBBACIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
        "CAwQAiABCgYIDRABIAEKBggOEAIgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAI=",
    ),
    (
        14,
        "CgYIARACIAEKBggCEAIgAQoGCAMQAiABCgYIBBACIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
        "CAwQAiABCgYIDRACIAEKBggOEAEgAQoGCA8QAiABCgYIEBACIAEKBwiQTiABKAI=",
    ),
    (
        15,
        "CgYIARACIAEKBggCEAIgAQoGCAMQAiABCgYIBBACIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
        "CAwQAiABCgYIDRACIAEKBggOEAIgAQoGCA8QASABCgYIEBACIAEKBwiQTiABKAI=",
    ),
    (
        16,
        "CgYIARACIAEKBggCEAIgAQoGCAMQAiABCgYIBBACIAEKCAgFEAIgAzAJCggIBxACIAE4AQoG"
        "CAwQAiABCgYIDRACIAEKBggOEAIgAQoGCA8QAiABCgYIEBABIAEKBwiQTiABKAE=",
    ),
)


def test_decode_captured_closed_closure_positions() -> None:
    """Decode every position from a captured all-closed closure payload."""
    states = decode_body_states(payload(_CLOSED_CLOSURES_PAYLOAD)).states

    assert [(state.position_code, state.state_code) for state in states] == [
        (1, 2),
        (2, 2),
        (3, 2),
        (4, 2),
        (5, 2),
        (7, 2),
        (12, 2),
        (13, 2),
        (14, 2),
        (15, 2),
        (16, 2),
        (10000, None),
    ]


@pytest.mark.parametrize(
    ("open_position", "encoded"),
    _OPEN_CLOSURE_PAYLOADS,
    ids=lambda value: f"position-{value}" if isinstance(value, int) else None,
)
def test_decode_captured_open_closure_positions(
    open_position: int, encoded: str
) -> None:
    """Preserve the raw position and state codes from captured transitions."""
    states = decode_body_states(payload(encoded)).states
    decoded = {state.position_code: state.state_code for state in states}

    assert decoded[open_position] == 1
    assert all(
        state_code == 2
        for position_code, state_code in decoded.items()
        if position_code not in (open_position, 10000)
    )


@pytest.mark.parametrize(
    ("state_code", "encoded"),
    (
        (1, "CgQIARABCgQIAhABCgQIAxABCgQIBBABCgQIBRABCgQIBxAB"),
        (2, "CgQIARACCgQIAhACCgQIAxACCgQIBBACCgQIBRACCgQIBxAC"),
    ),
)
def test_decode_captured_lock_states(state_code: int, encoded: str) -> None:
    """Decode both captured lock-state codes for every observed position."""
    states = decode_body_states(payload(encoded)).states

    assert [(state.position_code, state.state_code) for state in states] == [
        (position_code, state_code) for position_code in (1, 2, 3, 4, 5, 7)
    ]


@pytest.mark.parametrize(
    ("state_code", "encoded"),
    ((1, "CAE="), (2, "CAI="), (3, "CAM="), (4, "CAQ=")),
)
def test_decode_captured_vehicle_gear_codes(state_code: int, encoded: str) -> None:
    """Decode every captured gear code as an unlabelled wire integer."""
    assert decode_vehicle_gear(payload(encoded)).state_code == state_code


@pytest.mark.parametrize(
    ("mode_code", "encoded"),
    (
        (2, "CAI="),
        (4, "CAQ="),
        (8, "CAg="),
        (9, "CAk="),
        (11, "CAs="),
        (12, "CAw="),
        (15, "CA8="),
    ),
)
def test_decode_captured_vehicle_drive_mode_codes(mode_code: int, encoded: str) -> None:
    """Decode every captured drive-mode code as an unlabelled wire integer."""
    assert decode_vehicle_drive_mode(payload(encoded)).mode_code == mode_code


def test_unknown_state_integers_are_preserved() -> None:
    """Do not discard wire integers that are not present in captured enums."""
    body = decode_body_states(bytes.fromhex("0a040865104d"))

    assert [(state.position_code, state.state_code) for state in body.states] == [
        (101, 77)
    ]
    assert decode_vehicle_gear(bytes.fromhex("0863")).state_code == 99
    assert decode_vehicle_drive_mode(bytes.fromhex("087b")).mode_code == 123


def test_decode_charging_status_and_time() -> None:
    """Decode observed charging status and timing payloads."""
    status = decode_charging_session_status(payload("CAIQAxgB"))
    assert status.plug_connection_status_code == 2
    assert status.display_status_code == 3
    assert status.evse_type_code == 1
    assert (
        decode_charging_time_estimation(payload("EFw=")).estimated_minutes_remaining
        == 92
    )


def test_decode_charging_session_live_data_preserves_presence() -> None:
    """Keep omitted values distinct from encoded zero and false values."""
    live = decode_charging_session_live_data(
        payload("Dc3MzD0VzczMPTABOFtNMzMrQVA7WgBgAWgD")
    )
    assert math.isclose(live.total_kwh or 0, 0.1, rel_tol=1e-5)
    assert math.isclose(live.pack_kwh or 0, 0.1, rel_tol=1e-5)
    assert live.thermal_kwh is None
    assert live.session_duration_minutes == 1
    assert live.time_remaining_minutes == 91
    assert math.isclose(live.current_power_kw or 0, 10.7, rel_tol=1e-5)
    assert live.current_range_km_per_hour == 59
    assert live.is_free_session is True
    assert live.charging_state_code == 3

    encoded_defaults = decode_charging_session_live_data(
        bytes.fromhex("0d000000006000")
    )
    assert encoded_defaults.total_kwh == 0.0
    assert encoded_defaults.is_free_session is False
    assert encoded_defaults.pack_kwh is None


def test_decode_charging_graph_global() -> None:
    """Decode observed charging graph bars."""
    graph = decode_charging_graph_global(
        payload("ChcIVRUzMyNBGJCg9uD3MyDw9Png9zMwAw==")
    )
    assert len(graph.bars) == 1
    bar = graph.bars[0]
    assert bar.soc == 85
    assert math.isclose(bar.power_kw or 0, 10.2, rel_tol=1e-5)
    assert bar.start_time_ms == 1784493740048
    assert bar.end_time_ms == 1784493800048
    assert bar.time_estimation_validity_code is None
    assert bar.charging_state_code == 3
    assert bar.context_code is None


def test_decode_parallax_dispatch_and_errors() -> None:
    """Dispatch supported topics and report unsupported or malformed payloads."""
    message = ParallaxMessage(
        rvm="vehicle.power.state", timestamp_ms=1, payload=payload("CAE=")
    )
    assert decode_parallax_message(message).state_code == 1
    assert decode_parallax_payload("vehicle.power.state", b"").state_code is None
    with pytest.raises(ParallaxDecodeError, match="Unsupported"):
        decode_parallax_payload("unknown.topic", b"")
    with pytest.raises(ParallaxDecodeError, match="Unsupported"):
        decode_parallax_payload("body.windows.states", b"")
    with pytest.raises(ParallaxDecodeError, match="Malformed"):
        decode_vehicle_power_state(b"\x80")


def test_unknown_top_level_field_is_ignored() -> None:
    """A future top-level field does not hide a known field."""
    unknown_field_99 = b"\x98\x06\x7b"

    decoded = decode_vehicle_power_state(b"\x08\x01" + unknown_field_99)

    assert decoded.state_code == 1


def test_unknown_nested_field_is_ignored() -> None:
    """A future nested field does not hide a known nested field."""
    unknown_field_99 = b"\x98\x06\x7b"
    charge_state = b"\x09" + struct.pack("<d", 86.4) + unknown_field_99
    encoded = b"\x0a" + bytes([len(charge_state)]) + charge_state

    decoded = decode_high_voltage_battery_state(encoded)

    assert math.isclose(decoded.soc_percent or 0, 86.4, rel_tol=1e-5)
    assert decoded.capacity_kwh is None
