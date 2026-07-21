from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BatteryChargeState(_message.Message):
    __slots__ = ("soc_percent", "capacity_kwh", "range_km")
    SOC_PERCENT_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_KWH_FIELD_NUMBER: _ClassVar[int]
    RANGE_KM_FIELD_NUMBER: _ClassVar[int]
    soc_percent: float
    capacity_kwh: float
    range_km: float
    def __init__(self, soc_percent: _Optional[float] = ..., capacity_kwh: _Optional[float] = ..., range_km: _Optional[float] = ...) -> None: ...

class BatteryTemperatureState(_message.Message):
    __slots__ = ("cell_average_c", "cell_max_c", "cell_min_c")
    CELL_AVERAGE_C_FIELD_NUMBER: _ClassVar[int]
    CELL_MAX_C_FIELD_NUMBER: _ClassVar[int]
    CELL_MIN_C_FIELD_NUMBER: _ClassVar[int]
    cell_average_c: float
    cell_max_c: float
    cell_min_c: float
    def __init__(self, cell_average_c: _Optional[float] = ..., cell_max_c: _Optional[float] = ..., cell_min_c: _Optional[float] = ...) -> None: ...

class HighVoltageBatteryState(_message.Message):
    __slots__ = ("charge_state", "temperature_state", "power_output_code", "requires_calibration", "cold_weather_state_code")
    CHARGE_STATE_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_STATE_FIELD_NUMBER: _ClassVar[int]
    POWER_OUTPUT_CODE_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_CALIBRATION_FIELD_NUMBER: _ClassVar[int]
    COLD_WEATHER_STATE_CODE_FIELD_NUMBER: _ClassVar[int]
    charge_state: BatteryChargeState
    temperature_state: BatteryTemperatureState
    power_output_code: int
    requires_calibration: bool
    cold_weather_state_code: int
    def __init__(self, charge_state: _Optional[_Union[BatteryChargeState, _Mapping]] = ..., temperature_state: _Optional[_Union[BatteryTemperatureState, _Mapping]] = ..., power_output_code: _Optional[int] = ..., requires_calibration: bool = ..., cold_weather_state_code: _Optional[int] = ...) -> None: ...

class VehicleRange(_message.Message):
    __slots__ = ("distance_km",)
    DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    distance_km: int
    def __init__(self, distance_km: _Optional[int] = ...) -> None: ...

class VehicleOdometer(_message.Message):
    __slots__ = ("distance_km",)
    DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    distance_km: int
    def __init__(self, distance_km: _Optional[int] = ...) -> None: ...

class VehicleGnss(_message.Message):
    __slots__ = ("latitude", "longitude", "altitude_m", "gps_timestamp_ms")
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    ALTITUDE_M_FIELD_NUMBER: _ClassVar[int]
    GPS_TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    latitude: float
    longitude: float
    altitude_m: float
    gps_timestamp_ms: int
    def __init__(self, latitude: _Optional[float] = ..., longitude: _Optional[float] = ..., altitude_m: _Optional[float] = ..., gps_timestamp_ms: _Optional[int] = ...) -> None: ...

class VehiclePowerState(_message.Message):
    __slots__ = ("state_code",)
    STATE_CODE_FIELD_NUMBER: _ClassVar[int]
    state_code: int
    def __init__(self, state_code: _Optional[int] = ...) -> None: ...

class VehicleGear(_message.Message):
    __slots__ = ("state_code",)
    STATE_CODE_FIELD_NUMBER: _ClassVar[int]
    state_code: int
    def __init__(self, state_code: _Optional[int] = ...) -> None: ...

class VehicleDriveMode(_message.Message):
    __slots__ = ("mode_code",)
    MODE_CODE_FIELD_NUMBER: _ClassVar[int]
    mode_code: int
    def __init__(self, mode_code: _Optional[int] = ...) -> None: ...

class TireState(_message.Message):
    __slots__ = ("position_code", "status_code", "pressure_bar", "validity_code", "timestamp_ms")
    POSITION_CODE_FIELD_NUMBER: _ClassVar[int]
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    PRESSURE_BAR_FIELD_NUMBER: _ClassVar[int]
    VALIDITY_CODE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    position_code: int
    status_code: int
    pressure_bar: float
    validity_code: int
    timestamp_ms: int
    def __init__(self, position_code: _Optional[int] = ..., status_code: _Optional[int] = ..., pressure_bar: _Optional[float] = ..., validity_code: _Optional[int] = ..., timestamp_ms: _Optional[int] = ...) -> None: ...

class TireStates(_message.Message):
    __slots__ = ("monitor_status_code", "tires")
    MONITOR_STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    TIRES_FIELD_NUMBER: _ClassVar[int]
    monitor_status_code: int
    tires: _containers.RepeatedCompositeFieldContainer[TireState]
    def __init__(self, monitor_status_code: _Optional[int] = ..., tires: _Optional[_Iterable[_Union[TireState, _Mapping]]] = ...) -> None: ...

class BodyState(_message.Message):
    __slots__ = ("position_code", "state_code")
    POSITION_CODE_FIELD_NUMBER: _ClassVar[int]
    STATE_CODE_FIELD_NUMBER: _ClassVar[int]
    position_code: int
    state_code: int
    def __init__(self, position_code: _Optional[int] = ..., state_code: _Optional[int] = ...) -> None: ...

class BodyStates(_message.Message):
    __slots__ = ("states",)
    STATES_FIELD_NUMBER: _ClassVar[int]
    states: _containers.RepeatedCompositeFieldContainer[BodyState]
    def __init__(self, states: _Optional[_Iterable[_Union[BodyState, _Mapping]]] = ...) -> None: ...

class CabinPreconditioningStatus(_message.Message):
    __slots__ = ("status_code", "type_code")
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    TYPE_CODE_FIELD_NUMBER: _ClassVar[int]
    status_code: int
    type_code: int
    def __init__(self, status_code: _Optional[int] = ..., type_code: _Optional[int] = ...) -> None: ...

class CabinTemperatures(_message.Message):
    __slots__ = ("interior_c",)
    INTERIOR_C_FIELD_NUMBER: _ClassVar[int]
    interior_c: float
    def __init__(self, interior_c: _Optional[float] = ...) -> None: ...

class ChargingSessionStatus(_message.Message):
    __slots__ = ("plug_connection_status_code", "display_status_code", "evse_type_code")
    PLUG_CONNECTION_STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    EVSE_TYPE_CODE_FIELD_NUMBER: _ClassVar[int]
    plug_connection_status_code: int
    display_status_code: int
    evse_type_code: int
    def __init__(self, plug_connection_status_code: _Optional[int] = ..., display_status_code: _Optional[int] = ..., evse_type_code: _Optional[int] = ...) -> None: ...

class ChargingTimeEstimation(_message.Message):
    __slots__ = ("estimated_minutes_remaining",)
    ESTIMATED_MINUTES_REMAINING_FIELD_NUMBER: _ClassVar[int]
    estimated_minutes_remaining: int
    def __init__(self, estimated_minutes_remaining: _Optional[int] = ...) -> None: ...

class ChargingSessionLiveData(_message.Message):
    __slots__ = ("total_kwh", "pack_kwh", "thermal_kwh", "outlets_kwh", "system_kwh", "session_duration_minutes", "time_remaining_minutes", "range_added_km", "current_power_kw", "current_range_km_per_hour", "is_free_session", "charging_state_code")
    TOTAL_KWH_FIELD_NUMBER: _ClassVar[int]
    PACK_KWH_FIELD_NUMBER: _ClassVar[int]
    THERMAL_KWH_FIELD_NUMBER: _ClassVar[int]
    OUTLETS_KWH_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_KWH_FIELD_NUMBER: _ClassVar[int]
    SESSION_DURATION_MINUTES_FIELD_NUMBER: _ClassVar[int]
    TIME_REMAINING_MINUTES_FIELD_NUMBER: _ClassVar[int]
    RANGE_ADDED_KM_FIELD_NUMBER: _ClassVar[int]
    CURRENT_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    CURRENT_RANGE_KM_PER_HOUR_FIELD_NUMBER: _ClassVar[int]
    IS_FREE_SESSION_FIELD_NUMBER: _ClassVar[int]
    CHARGING_STATE_CODE_FIELD_NUMBER: _ClassVar[int]
    total_kwh: float
    pack_kwh: float
    thermal_kwh: float
    outlets_kwh: float
    system_kwh: float
    session_duration_minutes: int
    time_remaining_minutes: int
    range_added_km: int
    current_power_kw: float
    current_range_km_per_hour: int
    is_free_session: bool
    charging_state_code: int
    def __init__(self, total_kwh: _Optional[float] = ..., pack_kwh: _Optional[float] = ..., thermal_kwh: _Optional[float] = ..., outlets_kwh: _Optional[float] = ..., system_kwh: _Optional[float] = ..., session_duration_minutes: _Optional[int] = ..., time_remaining_minutes: _Optional[int] = ..., range_added_km: _Optional[int] = ..., current_power_kw: _Optional[float] = ..., current_range_km_per_hour: _Optional[int] = ..., is_free_session: bool = ..., charging_state_code: _Optional[int] = ...) -> None: ...

class ChargingGraphBar(_message.Message):
    __slots__ = ("soc_percent", "power_kw", "start_time_ms", "end_time_ms", "time_estimation_validity_code", "charging_state_code", "context_code")
    SOC_PERCENT_FIELD_NUMBER: _ClassVar[int]
    POWER_KW_FIELD_NUMBER: _ClassVar[int]
    START_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    END_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    TIME_ESTIMATION_VALIDITY_CODE_FIELD_NUMBER: _ClassVar[int]
    CHARGING_STATE_CODE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_CODE_FIELD_NUMBER: _ClassVar[int]
    soc_percent: int
    power_kw: float
    start_time_ms: int
    end_time_ms: int
    time_estimation_validity_code: int
    charging_state_code: int
    context_code: int
    def __init__(self, soc_percent: _Optional[int] = ..., power_kw: _Optional[float] = ..., start_time_ms: _Optional[int] = ..., end_time_ms: _Optional[int] = ..., time_estimation_validity_code: _Optional[int] = ..., charging_state_code: _Optional[int] = ..., context_code: _Optional[int] = ...) -> None: ...

class ChargingGraph(_message.Message):
    __slots__ = ("bars",)
    BARS_FIELD_NUMBER: _ClassVar[int]
    bars: _containers.RepeatedCompositeFieldContainer[ChargingGraphBar]
    def __init__(self, bars: _Optional[_Iterable[_Union[ChargingGraphBar, _Mapping]]] = ...) -> None: ...
