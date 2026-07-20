"""Tests for the Parallax GraphQL subscription API."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock

import pytest
from rivian import ParallaxMessage, Rivian
from rivian.ws_monitor import WebSocketMonitor


class FakeWebSocketMonitor:
    """Capture subscriptions without opening a network connection."""

    def __init__(self) -> None:
        self.connection_ack = asyncio.Event()
        self.connection_ack.set()
        self.subscriptions: list[
            tuple[dict[str, Any], Callable[[dict[str, Any]], Awaitable[None]]]
        ] = []

    @property
    def payload(self) -> dict[str, Any] | None:
        """Return the most recently captured subscription payload."""
        return self.subscriptions[-1][0] if self.subscriptions else None

    @property
    def callback(self) -> Callable[[dict[str, Any]], Awaitable[None]] | None:
        """Return the most recently captured subscription callback."""
        return self.subscriptions[-1][1] if self.subscriptions else None

    async def start_subscription(
        self,
        payload: dict[str, Any],
        callback: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """Capture the subscription request."""
        self.subscriptions.append((payload, callback))

        async def unsubscribe() -> None:
            return None

        return unsubscribe


class ConcurrentWebSocket:
    """Minimal socket that remains open until the client closes it."""

    def __init__(self) -> None:
        self.closed = False
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, message: dict[str, Any]) -> None:
        """Record connection initialization."""
        self.sent.append(message)

    async def receive(self, timeout: int) -> Any:
        """Remain idle until the receiver task is cancelled."""
        await asyncio.Future()

    async def close(self) -> None:
        """Mark the fake socket closed."""
        self.closed = True


class ConcurrentSession:
    """Count deliberately overlapping websocket connection attempts."""

    def __init__(self) -> None:
        self.websocket = ConcurrentWebSocket()
        self.connect_count = 0

    async def ws_connect(self, **kwargs: Any) -> ConcurrentWebSocket:
        """Yield once so an unlocked client would establish two sockets."""
        self.connect_count += 1
        await asyncio.sleep(0)
        return self.websocket


class RacingSession:
    """Hold a reconnect open while subscription setup enters the same path."""

    def __init__(self) -> None:
        self.websocket = ConcurrentWebSocket()
        self.connect_count = 0
        self.connect_started = asyncio.Event()
        self.release_connect = asyncio.Event()
        self.monitor: WebSocketMonitor | None = None

    async def ws_connect(self, **kwargs: Any) -> ConcurrentWebSocket:
        """Pause connection establishment until both callers are active."""
        self.connect_count += 1
        self.connect_started.set()
        await self.release_connect.wait()
        assert self.monitor
        self.monitor.connection_ack.set()
        return self.websocket


async def test_subscribe_for_parallax_messages() -> None:
    """Build the canonical operation and deliver decoded transport fields."""
    client = Rivian()
    monitor = FakeWebSocketMonitor()
    client._ws_monitor = monitor  # type: ignore[assignment]  # pylint: disable=protected-access
    client._ws_connect = AsyncMock()  # type: ignore[method-assign]  # pylint: disable=protected-access
    received: list[ParallaxMessage] = []

    async def callback(message: ParallaxMessage) -> None:
        received.append(message)

    unsubscribe = await client.subscribe_for_parallax_messages(
        "vehicle-id",
        ["vehicle.power.state", "vehicle.power.state", "dynamics.vehicle.range"],
        callback,
    )

    assert unsubscribe is not None
    assert monitor.payload == {
        "operationName": "ParallaxMessages",
        "query": "subscription ParallaxMessages($vehicleId: String!, $rvms: [String!]) { parallaxMessages(vehicleId: $vehicleId, rvms: $rvms) { payload timestamp rvm } }",
        "variables": {
            "vehicleId": "vehicle-id",
            "rvms": ["vehicle.power.state", "dynamics.vehicle.range"],
        },
    }
    assert monitor.callback is not None
    await monitor.callback(
        {
            "payload": {
                "data": {
                    "parallaxMessages": {
                        "rvm": "vehicle.power.state",
                        "timestamp": "1234",
                        "payload": "CAE=",
                    }
                }
            }
        }
    )
    assert received == [
        ParallaxMessage(
            rvm="vehicle.power.state", timestamp_ms=1234, payload=b"\x08\x01"
        )
    ]


async def test_parallax_subscription_skips_malformed_frames() -> None:
    """A malformed base64 frame must not stop subsequent telemetry."""
    client = Rivian()
    monitor = FakeWebSocketMonitor()
    client._ws_monitor = monitor  # type: ignore[assignment]  # pylint: disable=protected-access
    client._ws_connect = AsyncMock()  # type: ignore[method-assign]  # pylint: disable=protected-access
    received: list[ParallaxMessage] = []
    await client.subscribe_for_parallax_messages(
        "vehicle-id", ["vehicle.power.state"], received.append
    )
    assert monitor.callback is not None

    await monitor.callback(
        {
            "payload": {
                "data": {
                    "parallaxMessages": {
                        "rvm": "vehicle.power.state",
                        "timestamp": "invalid",
                        "payload": "not base64",
                    }
                }
            }
        }
    )
    await monitor.callback(
        {
            "payload": {
                "data": {
                    "parallaxMessages": {
                        "rvm": "vehicle.power.state",
                        "timestamp": "invalid",
                        "payload": "",
                    }
                }
            }
        }
    )
    assert received == [
        ParallaxMessage(rvm="vehicle.power.state", timestamp_ms=None, payload=b"")
    ]


async def test_multiple_vehicles_share_one_monitor() -> None:
    """One client can multiplex independent vehicle subscriptions."""
    client = Rivian()
    monitor = FakeWebSocketMonitor()
    client._ws_monitor = monitor  # type: ignore[assignment]  # pylint: disable=protected-access
    client._ws_connect = AsyncMock()  # type: ignore[method-assign]  # pylint: disable=protected-access

    await client.subscribe_for_parallax_messages(
        "vehicle-one", ["vehicle.power.state"], lambda message: None
    )
    await client.subscribe_for_parallax_messages(
        "vehicle-two", ["dynamics.vehicle.range"], lambda message: None
    )

    assert [subscription[0]["variables"] for subscription in monitor.subscriptions] == [
        {"vehicleId": "vehicle-one", "rvms": ["vehicle.power.state"]},
        {"vehicleId": "vehicle-two", "rvms": ["dynamics.vehicle.range"]},
    ]


async def test_legacy_and_parallax_subscriptions_share_one_monitor() -> None:
    """Legacy and Parallax operations coexist as independent subscriptions."""
    client = Rivian()
    monitor = FakeWebSocketMonitor()
    client._ws_monitor = monitor  # type: ignore[assignment]  # pylint: disable=protected-access
    client._ws_connect = AsyncMock()  # type: ignore[method-assign]  # pylint: disable=protected-access

    legacy_unsubscribe = await client.subscribe_for_vehicle_updates(
        "vehicle-one", lambda message: None, {"batteryLevel"}
    )
    parallax_unsubscribe = await client.subscribe_for_parallax_messages(
        "vehicle-two", ["vehicle.power.state"], lambda message: None
    )

    assert legacy_unsubscribe is not None
    assert parallax_unsubscribe is not None
    assert [
        subscription[0]["operationName"] for subscription in monitor.subscriptions
    ] == ["VehicleState", "ParallaxMessages"]
    assert monitor.subscriptions[0][0]["variables"] == {"vehicleID": "vehicle-one"}
    assert monitor.subscriptions[1][0]["variables"] == {
        "vehicleId": "vehicle-two",
        "rvms": ["vehicle.power.state"],
    }


async def test_concurrent_connections_share_one_websocket() -> None:
    """Concurrent subscription setup establishes one shared socket."""
    session = ConcurrentSession()
    client = Rivian(session=session)  # type: ignore[arg-type]

    first, second = await asyncio.gather(client._ws_connect(), client._ws_connect())  # pylint: disable=protected-access

    assert first is second is session.websocket
    assert session.connect_count == 1
    await client.close()


async def test_reconnect_racing_subscription_shares_one_websocket() -> None:
    """Monitor reconnect and subscription setup cannot replace each other's socket."""
    session = RacingSession()
    client = Rivian(session=session)  # type: ignore[arg-type]

    async def connection_init(websocket: Any) -> None:
        return None

    monitor = WebSocketMonitor(client, "wss://example", connection_init)
    session.monitor = monitor
    client._ws_monitor = monitor  # pylint: disable=protected-access

    reconnect_task = asyncio.create_task(monitor.new_connection())
    await session.connect_started.wait()
    subscription_task = asyncio.create_task(
        client.subscribe_for_parallax_messages(
            "vehicle-id", ["vehicle.power.state"], lambda message: None
        )
    )
    await asyncio.sleep(0)
    session.release_connect.set()
    unsubscribe, _ = await asyncio.gather(subscription_task, reconnect_task)

    assert unsubscribe is not None
    assert session.connect_count == 1
    assert [message["type"] for message in session.websocket.sent] == ["subscribe"]
    await client.close()


@pytest.mark.parametrize("rvms", [[], "vehicle.power.state", [""]])
async def test_parallax_subscription_requires_explicit_topics(
    rvms: Any,
) -> None:
    """Reject missing or malformed topic collections before connecting."""
    with pytest.raises(ValueError, match="rvms"):
        await Rivian().subscribe_for_parallax_messages(
            "vehicle-id", rvms, lambda message: None
        )
