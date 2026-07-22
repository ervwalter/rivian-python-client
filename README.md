# Python: Rivian API Client

Currently a Work In Progress

## Dependencies

[uv](https://docs.astral.sh/uv/)

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

Install project dependencies into the uv virtual environment and run pre-commit

```
uv sync --all-extras
pre-commit install
```

## Run Tests

```
uv run pytest
```

## Parallax protobuf schemas

Parallax telemetry payloads use protobuf. The repository includes a minimal,
locally maintained schema containing only fields confirmed by observed traffic,
plus the generated Python modules used at runtime.

Regenerate the checked-in modules after changing the schema:

```
uv run python scripts/generate_proto.py
```

Verify that generated files are current without modifying the working tree:

```
uv run python scripts/generate_proto.py --check
```

## Parallax telemetry

Parallax is Rivian's protobuf-over-GraphQL transport for newer vehicle
telemetry. Subscriptions require an explicit, nonempty RVM topic list and return
raw messages so callers can retain unknown or newly added topics:

```python
from rivian import ParallaxMessage, Rivian, decode_parallax_message


async def receive(message: ParallaxMessage) -> None:
    telemetry = decode_parallax_message(message)
    print(message.rvm, message.timestamp_ms, telemetry)


unsubscribe = await client.subscribe_for_parallax_messages(
    vehicle_id,
    [
        "energy.high_voltage.battery_state",
        "charging.session.status",
    ],
    receive,
)
```

`ParallaxMessage` contains only `rvm`, `timestamp_ms`, and decoded payload
bytes. Typed decoding is a separate opt-in step and raises
`ParallaxDecodeError` for malformed or unsupported payloads. Numeric state and
position codes remain integers where live transitions have not established
stable enum labels.

The typed decoders include direct GNSS speed and heading as well as active-trip
destination, estimated arrival, remaining distance, remaining drive time, and
the higher-frequency position carried by navigation progress. These values are
exposed with their wire units and timestamps; the client does not derive trip
efficiency or Home Assistant state semantics.
