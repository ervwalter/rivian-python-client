"""Typed decoding for Rivian Parallax telemetry payloads."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from google.protobuf.message import DecodeError, Message

from .exceptions import ParallaxDecodeError
from .proto import parallax_pb2


@dataclass(frozen=True, slots=True)
class ParallaxMessage:
    """One raw message from the Parallax GraphQL subscription."""

    rvm: str
    timestamp_ms: int | None
    payload: bytes


@dataclass(frozen=True, slots=True)
class HighVoltageBatteryState:
    """High-voltage battery telemetry."""

    soc_percent: float | None
    capacity_kwh: float | None
    range_km: float | None
    cell_average_c: float | None
    cell_max_c: float | None
    cell_min_c: float | None
    power_output_code: int | None
    requires_calibration: bool | None
    cold_weather_state_code: int | None

    @property
    def pack_kwh(self) -> float | None:
        """Return the deprecated capacity field alias."""
        return self.capacity_kwh


@dataclass(frozen=True, slots=True)
class VehicleRange:
    """Vehicle range telemetry."""

    distance_km: int | None


@dataclass(frozen=True, slots=True)
class VehicleOdometer:
    """Vehicle odometer telemetry."""

    distance_km: int | None


@dataclass(frozen=True, slots=True)
class VehicleGnss:
    """Vehicle GNSS position telemetry."""

    latitude: float | None
    longitude: float | None
    altitude_m: float | None
    timestamp_ms: int | None
    gps_timestamp_ms: int | None


@dataclass(frozen=True, slots=True)
class VehiclePowerState:
    """Vehicle power state as its wire-level numeric code."""

    state_code: int | None


@dataclass(frozen=True, slots=True)
class VehicleGear:
    """Selected vehicle gear as its wire-level numeric code."""

    state_code: int | None


@dataclass(frozen=True, slots=True)
class VehicleDriveMode:
    """Selected drive mode as its wire-level numeric code."""

    mode_code: int | None


@dataclass(frozen=True, slots=True)
class TireState:
    """One tire's pressure and status telemetry."""

    position_code: int | None
    status_code: int | None
    pressure_bar: float | None
    validity_code: int | None
    timestamp_ms: int | None


@dataclass(frozen=True, slots=True)
class TireStates:
    """Vehicle tire telemetry."""

    monitor_status_code: int | None
    tires: tuple[TireState, ...]


@dataclass(frozen=True, slots=True)
class BodyState:
    """One closure, lock, or window state record."""

    position_code: int | None
    state_code: int | None


@dataclass(frozen=True, slots=True)
class BodyStates:
    """Closure, lock, or window state records."""

    states: tuple[BodyState, ...]


@dataclass(frozen=True, slots=True)
class CabinPreconditioningStatus:
    """Cabin preconditioning state and type codes."""

    status_code: int | None
    type_code: int | None


@dataclass(frozen=True, slots=True)
class CabinTemperatures:
    """Cabin temperature telemetry."""

    interior_c: float | None


@dataclass(frozen=True, slots=True)
class ChargingSessionStatus:
    """Charging connection and display status codes."""

    plug_connection_status_code: int | None
    display_status_code: int | None
    evse_type_code: int | None


@dataclass(frozen=True, slots=True)
class ChargingTimeEstimation:
    """Charging time estimates."""

    estimated_minutes_remaining: int | None


@dataclass(frozen=True, slots=True)
class ChargingSessionLiveData:
    """Live charging energy and rate telemetry."""

    total_kwh: float | None
    pack_kwh: float | None
    thermal_kwh: float | None
    outlets_kwh: float | None
    system_kwh: float | None
    session_duration_minutes: int | None
    time_remaining_minutes: int | None
    range_added_km: int | None
    current_power_kw: float | None
    current_range_km_per_hour: int | None
    is_free_session: bool | None
    charging_state_code: int | None


@dataclass(frozen=True, slots=True)
class ChargingGraphBar:
    """One interval in a charging graph."""

    soc: int | None
    power_kw: float | None
    start_time_ms: int | None
    end_time_ms: int | None
    time_estimation_validity_code: int | None
    charging_state_code: int | None
    context_code: int | None


@dataclass(frozen=True, slots=True)
class ChargingGraphGlobal:
    """Charging graph intervals."""

    bars: tuple[ChargingGraphBar, ...]


ParallaxData = (
    HighVoltageBatteryState
    | VehicleRange
    | VehicleOdometer
    | VehicleGnss
    | VehiclePowerState
    | VehicleGear
    | VehicleDriveMode
    | TireStates
    | BodyStates
    | CabinPreconditioningStatus
    | CabinTemperatures
    | ChargingSessionStatus
    | ChargingTimeEstimation
    | ChargingSessionLiveData
    | ChargingGraphGlobal
)

_MessageT = TypeVar("_MessageT", bound=Message)


def _parse(payload: bytes, message_type: type[_MessageT]) -> _MessageT:
    message = message_type()
    try:
        message.ParseFromString(payload)
    except DecodeError as err:
        raise ParallaxDecodeError("Malformed Parallax protobuf payload") from err
    return message


def _optional(message: Message, field: str) -> Any | None:
    return getattr(message, field) if message.HasField(field) else None


def _gps_to_unix_timestamp_ms(timestamp_ms: int | None) -> int | None:
    """Convert a current GPS-epoch timestamp to the Unix epoch in UTC."""
    if timestamp_ms is None:
        return None
    return timestamp_ms + 315_964_800_000 - 18_000


def decode_high_voltage_battery_state(payload: bytes) -> HighVoltageBatteryState:
    """Decode ``energy.high_voltage.battery_state``."""
    message = _parse(payload, parallax_pb2.HighVoltageBatteryState)
    charge_state = message.charge_state if message.HasField("charge_state") else None
    temperature_state = (
        message.temperature_state if message.HasField("temperature_state") else None
    )
    return HighVoltageBatteryState(
        soc_percent=_optional(charge_state, "soc_percent") if charge_state else None,
        capacity_kwh=(
            _optional(charge_state, "capacity_kwh") if charge_state else None
        ),
        range_km=_optional(charge_state, "range_km") if charge_state else None,
        cell_average_c=(
            _optional(temperature_state, "cell_average_c")
            if temperature_state
            else None
        ),
        cell_max_c=(
            _optional(temperature_state, "cell_max_c") if temperature_state else None
        ),
        cell_min_c=(
            _optional(temperature_state, "cell_min_c") if temperature_state else None
        ),
        power_output_code=_optional(message, "power_output_code"),
        requires_calibration=_optional(message, "requires_calibration"),
        cold_weather_state_code=_optional(message, "cold_weather_state_code"),
    )


def decode_vehicle_range(payload: bytes) -> VehicleRange:
    """Decode ``dynamics.vehicle.range``."""
    message = _parse(payload, parallax_pb2.VehicleRange)
    return VehicleRange(
        distance_km=_optional(message, "distance_km"),
    )


def decode_vehicle_odometer(payload: bytes) -> VehicleOdometer:
    """Decode ``dynamics.vehicle.odometer``."""
    message = _parse(payload, parallax_pb2.VehicleOdometer)
    return VehicleOdometer(distance_km=_optional(message, "distance_km"))


def decode_vehicle_gnss(payload: bytes) -> VehicleGnss:
    """Decode ``dynamics.vehicle.gnss``."""
    message = _parse(payload, parallax_pb2.VehicleGnss)
    gps_timestamp_ms = _optional(message, "gps_timestamp_ms")
    return VehicleGnss(
        latitude=_optional(message, "latitude"),
        longitude=_optional(message, "longitude"),
        altitude_m=_optional(message, "altitude_m"),
        timestamp_ms=_gps_to_unix_timestamp_ms(gps_timestamp_ms),
        gps_timestamp_ms=gps_timestamp_ms,
    )


def decode_vehicle_power_state(payload: bytes) -> VehiclePowerState:
    """Decode ``vehicle.power.state``."""
    message = _parse(payload, parallax_pb2.VehiclePowerState)
    return VehiclePowerState(state_code=_optional(message, "state_code"))


def decode_vehicle_gear(payload: bytes) -> VehicleGear:
    """Decode ``dynamics.vehicle.gear``."""
    message = _parse(payload, parallax_pb2.VehicleGear)
    return VehicleGear(state_code=_optional(message, "state_code"))


def decode_vehicle_drive_mode(payload: bytes) -> VehicleDriveMode:
    """Decode ``dynamics.vehicle.drive_mode``."""
    message = _parse(payload, parallax_pb2.VehicleDriveMode)
    return VehicleDriveMode(mode_code=_optional(message, "mode_code"))


def decode_tire_states(payload: bytes) -> TireStates:
    """Decode ``dynamics.tires.state``."""
    message = _parse(payload, parallax_pb2.TireStates)
    return TireStates(
        monitor_status_code=_optional(message, "monitor_status_code"),
        tires=tuple(
            TireState(
                position_code=_optional(tire, "position_code"),
                status_code=_optional(tire, "status_code"),
                pressure_bar=_optional(tire, "pressure_bar"),
                validity_code=_optional(tire, "validity_code"),
                timestamp_ms=_optional(tire, "timestamp_ms"),
            )
            for tire in message.tires
        ),
    )


def decode_body_states(payload: bytes) -> BodyStates:
    """Decode a body closures or locks state payload."""
    message = _parse(payload, parallax_pb2.BodyStates)
    return BodyStates(
        states=tuple(
            BodyState(
                position_code=_optional(state, "position_code"),
                state_code=_optional(state, "state_code"),
            )
            for state in message.states
        )
    )


def decode_cabin_preconditioning_status(
    payload: bytes,
) -> CabinPreconditioningStatus:
    """Decode ``comfort.cabin.cabin_preconditioning_status``."""
    message = _parse(payload, parallax_pb2.CabinPreconditioningStatus)
    return CabinPreconditioningStatus(
        status_code=_optional(message, "status_code"),
        type_code=_optional(message, "type_code"),
    )


def decode_cabin_temperatures(payload: bytes) -> CabinTemperatures:
    """Decode ``comfort.cabin.cabin_temperatures``."""
    message = _parse(payload, parallax_pb2.CabinTemperatures)
    return CabinTemperatures(
        interior_c=_optional(message, "interior_c"),
    )


def decode_charging_session_status(payload: bytes) -> ChargingSessionStatus:
    """Decode ``charging.session.status``."""
    message = _parse(payload, parallax_pb2.ChargingSessionStatus)
    return ChargingSessionStatus(
        plug_connection_status_code=_optional(message, "plug_connection_status_code"),
        display_status_code=_optional(message, "display_status_code"),
        evse_type_code=_optional(message, "evse_type_code"),
    )


def decode_charging_time_estimation(payload: bytes) -> ChargingTimeEstimation:
    """Decode ``charging.session.time_estimation``."""
    message = _parse(payload, parallax_pb2.ChargingTimeEstimation)
    return ChargingTimeEstimation(
        estimated_minutes_remaining=_optional(message, "estimated_minutes_remaining"),
    )


def decode_charging_session_live_data(payload: bytes) -> ChargingSessionLiveData:
    """Decode ``energy_edge_compute.graphs.charge_session_breakdown``."""
    message = _parse(payload, parallax_pb2.ChargingSessionLiveData)
    return ChargingSessionLiveData(
        total_kwh=_optional(message, "total_kwh"),
        pack_kwh=_optional(message, "pack_kwh"),
        thermal_kwh=_optional(message, "thermal_kwh"),
        outlets_kwh=_optional(message, "outlets_kwh"),
        system_kwh=_optional(message, "system_kwh"),
        session_duration_minutes=_optional(message, "session_duration_minutes"),
        time_remaining_minutes=_optional(message, "time_remaining_minutes"),
        range_added_km=_optional(message, "range_added_km"),
        current_power_kw=_optional(message, "current_power_kw"),
        current_range_km_per_hour=_optional(message, "current_range_km_per_hour"),
        is_free_session=_optional(message, "is_free_session"),
        charging_state_code=_optional(message, "charging_state_code"),
    )


def decode_charging_graph_global(payload: bytes) -> ChargingGraphGlobal:
    """Decode ``energy_edge_compute.graphs.charging_graph_global``."""
    message = _parse(payload, parallax_pb2.ChargingGraph)
    return ChargingGraphGlobal(
        bars=tuple(
            ChargingGraphBar(
                soc=_optional(bar, "soc_percent"),
                power_kw=_optional(bar, "power_kw"),
                start_time_ms=_optional(bar, "start_time_ms"),
                end_time_ms=_optional(bar, "end_time_ms"),
                time_estimation_validity_code=_optional(
                    bar, "time_estimation_validity_code"
                ),
                charging_state_code=_optional(bar, "charging_state_code"),
                context_code=_optional(bar, "context_code"),
            )
            for bar in message.bars
        )
    )


_DECODERS: dict[str, Callable[[bytes], ParallaxData]] = {
    "energy.high_voltage.battery_state": decode_high_voltage_battery_state,
    "dynamics.vehicle.range": decode_vehicle_range,
    "dynamics.vehicle.odometer": decode_vehicle_odometer,
    "dynamics.vehicle.gnss": decode_vehicle_gnss,
    "vehicle.power.state": decode_vehicle_power_state,
    "dynamics.vehicle.gear": decode_vehicle_gear,
    "dynamics.vehicle.drive_mode": decode_vehicle_drive_mode,
    "dynamics.tires.state": decode_tire_states,
    "body.closures.states": decode_body_states,
    "body.locks.states": decode_body_states,
    "comfort.cabin.cabin_preconditioning_status": (decode_cabin_preconditioning_status),
    "comfort.cabin.cabin_temperatures": decode_cabin_temperatures,
    "charging.session.status": decode_charging_session_status,
    "charging.session.time_estimation": decode_charging_time_estimation,
    "energy_edge_compute.graphs.charge_session_breakdown": (
        decode_charging_session_live_data
    ),
    "energy_edge_compute.graphs.charging_graph_global": (decode_charging_graph_global),
}


def decode_parallax_payload(rvm: str, payload: bytes) -> ParallaxData:
    """Decode a supported Parallax payload by RVM topic."""
    try:
        decoder = _DECODERS[rvm]
    except KeyError as err:
        raise ParallaxDecodeError(f"Unsupported Parallax RVM: {rvm}") from err
    return decoder(payload)


def decode_parallax_message(message: ParallaxMessage) -> ParallaxData:
    """Decode a supported raw Parallax message."""
    return decode_parallax_payload(message.rvm, message.payload)
