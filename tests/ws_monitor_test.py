"""Tests for WebSocket monitor robustness."""

from __future__ import annotations

import asyncio
import json
import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from aiohttp import WSMsgType
from rivian.ws_monitor import WebSocketMonitor


class FakeAccount:
    """Minimal account used by WebSocketMonitor tests."""

    request_timeout = 1

    def __init__(self, session: Any = None) -> None:
        self._session = session


class RecordingWebSocket:
    """A connected socket that records sent protocol frames."""

    closed = False

    def __init__(self, messages: list[SimpleNamespace] | None = None) -> None:
        self.messages = list(messages or [])
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, message: dict[str, Any]) -> None:
        """Record an outgoing frame."""
        self.sent.append(message)

    async def receive(self, timeout: int) -> SimpleNamespace:
        """Return the next scripted frame or wait to be cancelled."""
        if not self.messages:
            await asyncio.Future()
        message = self.messages.pop(0)
        if message.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            self.closed = True
        return message

    async def close(self) -> None:
        """Close the socket."""
        self.closed = True


class FakeSession:
    """Return a supplied WebSocket and observe connection setup."""

    def __init__(
        self, websocket: RecordingWebSocket, monitor: WebSocketMonitor
    ) -> None:
        self.websocket = websocket
        self.monitor = monitor

    async def ws_connect(self, **kwargs: Any) -> RecordingWebSocket:
        """Assert stale acknowledgement state was cleared before connecting."""
        assert not self.monitor.connection_ack.is_set()
        return self.websocket


class IdleThenClosedWebSocket:
    """A socket that is idle once before closing."""

    closed = False

    def __init__(self) -> None:
        self.receive_count = 0

    async def receive(self, timeout: int) -> SimpleNamespace:
        """Return one timeout followed by a closed message."""
        self.receive_count += 1
        if self.receive_count == 1:
            raise asyncio.TimeoutError
        self.closed = True
        return SimpleNamespace(type=WSMsgType.CLOSED, extra=None, data=None)


class BlockingCompleteWebSocket(RecordingWebSocket):
    """Hold a complete frame so a concurrent resubscribe can race it."""

    def __init__(self) -> None:
        super().__init__()
        self.complete_started = asyncio.Event()
        self.release_complete = asyncio.Event()

    async def send_json(self, message: dict[str, Any]) -> None:
        """Block while sending a complete frame."""
        self.sent.append(message)
        if message.get("type") == "complete":
            self.complete_started.set()
            await self.release_complete.wait()


class BlockingSubscribeWebSocket(RecordingWebSocket):
    """Hold a subscribe frame so cancellation can interrupt its send."""

    def __init__(self) -> None:
        super().__init__()
        self.subscribe_started = asyncio.Event()
        self.release_subscribe = asyncio.Event()

    async def send_json(self, message: dict[str, Any]) -> None:
        """Block while sending a subscribe frame."""
        self.sent.append(message)
        if message.get("type") == "subscribe":
            self.subscribe_started.set()
            await self.release_subscribe.wait()


async def test_idle_timeout_does_not_resubscribe() -> None:
    """A sleeping vehicle's idle socket must not duplicate subscription IDs."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    websocket = IdleThenClosedWebSocket()
    monitor._ws = websocket  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor._resubscribe_all = AsyncMock()  # type: ignore[method-assign]  # pylint: disable=protected-access

    await monitor._receiver()  # pylint: disable=protected-access

    assert websocket.receive_count == 2
    monitor._resubscribe_all.assert_not_awaited()  # pylint: disable=protected-access


async def test_subscriptions_unsubscribe_independently() -> None:
    """Completing one subscription leaves all other subscriptions active."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    websocket = RecordingWebSocket()
    monitor._ws = websocket  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor.connection_ack.set()
    first_unsubscribe = await monitor.start_subscription(
        {"operationName": "first"}, lambda message: None
    )
    second_unsubscribe = await monitor.start_subscription(
        {"operationName": "second"}, lambda message: None
    )
    assert first_unsubscribe is not None
    assert second_unsubscribe is not None
    subscription_ids = tuple(monitor._subscriptions)  # pylint: disable=protected-access

    await first_unsubscribe()

    assert tuple(monitor._subscriptions) == (  # pylint: disable=protected-access
        subscription_ids[1],
    )
    assert websocket.sent[-1] == {"id": subscription_ids[0], "type": "complete"}


async def test_failed_initial_send_does_not_retain_subscription() -> None:
    """A failed initial send must not leave a ghost subscription to restore."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    websocket = RecordingWebSocket()
    websocket.send_json = AsyncMock(side_effect=RuntimeError("send failed"))  # type: ignore[method-assign]
    monitor._ws = websocket  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor.connection_ack.set()

    with pytest.raises(RuntimeError, match="send failed"):
        await monitor.start_subscription({}, lambda message: None)

    assert monitor._subscriptions == {}  # pylint: disable=protected-access


async def test_cancelled_initial_send_does_not_retain_subscription() -> None:
    """Cancellation during the initial send cannot create a ghost subscription."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    websocket = BlockingSubscribeWebSocket()
    monitor._ws = websocket  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor.connection_ack.set()

    task = asyncio.create_task(monitor.start_subscription({}, lambda message: None))
    await websocket.subscribe_started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert monitor._subscriptions == {}  # pylint: disable=protected-access


async def test_subscription_uses_the_acknowledged_replacement_socket() -> None:
    """A reconnect between acknowledgement and send cannot receive early traffic."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    original = RecordingWebSocket()
    replacement = RecordingWebSocket()
    monitor._ws = original  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor.connection_ack.set()
    await monitor._connection_lock.acquire()  # pylint: disable=protected-access

    task = asyncio.create_task(monitor.start_subscription({}, lambda message: None))
    await asyncio.sleep(0)
    monitor._ws = replacement  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor.connection_ack.clear()
    monitor._connection_lock.release()  # pylint: disable=protected-access
    await asyncio.sleep(0)

    assert original.sent == []
    assert replacement.sent == []
    monitor.connection_ack.set()
    unsubscribe = await task

    assert unsubscribe is not None
    assert [message["type"] for message in replacement.sent] == ["subscribe"]


async def test_reconnect_resubscribes_all_existing_ids() -> None:
    """A replacement acknowledged socket restores every active subscription."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    websocket = RecordingWebSocket()
    monitor._ws = websocket  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor._subscriptions = {  # pylint: disable=protected-access
        "one": (lambda message: None, {"operationName": "first"}),
        "two": (lambda message: None, {"operationName": "second"}),
    }
    monitor.connection_ack.set()

    await monitor._resubscribe_all()  # pylint: disable=protected-access

    assert websocket.sent == [
        {
            "id": "one",
            "payload": {"operationName": "first"},
            "type": "subscribe",
        },
        {
            "id": "two",
            "payload": {"operationName": "second"},
            "type": "subscribe",
        },
    ]


async def test_resubscribe_uses_stable_subscription_snapshot() -> None:
    """Subscription changes during restoration do not invalidate iteration."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    monitor._ws = RecordingWebSocket()  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor._subscriptions = {  # pylint: disable=protected-access
        "one": (lambda message: None, {"operationName": "first"}),
        "two": (lambda message: None, {"operationName": "second"}),
    }
    monitor.connection_ack.set()
    restored: list[str] = []

    async def subscribe(subscription_id: str, payload: dict[str, Any]) -> None:
        restored.append(subscription_id)
        if subscription_id == "one":
            monitor._subscriptions.pop("two")  # pylint: disable=protected-access

    monitor._subscribe = subscribe  # type: ignore[method-assign]  # pylint: disable=protected-access

    await monitor._resubscribe_all()  # pylint: disable=protected-access

    assert restored == ["one", "two"]


async def test_resubscribe_cannot_replay_after_complete() -> None:
    """A removed subscription is not restored after its complete frame."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    websocket = BlockingCompleteWebSocket()
    monitor._ws = websocket  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor.connection_ack.set()
    unsubscribe = await monitor.start_subscription({}, lambda message: None)
    assert unsubscribe is not None
    websocket.sent.clear()
    monitor.connection_ack.set()

    unsubscribe_task = asyncio.create_task(unsubscribe())
    await websocket.complete_started.wait()
    resubscribe_task = asyncio.create_task(
        monitor._resubscribe_all()  # pylint: disable=protected-access
    )
    await asyncio.sleep(0)
    websocket.release_complete.set()
    await asyncio.gather(unsubscribe_task, resubscribe_task)

    assert [message["type"] for message in websocket.sent] == ["complete"]
    assert monitor._subscriptions == {}  # pylint: disable=protected-access


async def test_monitor_retries_after_resubscribe_failure() -> None:
    """A restore failure remains inside reconnect/backoff monitoring."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    sockets: list[RecordingWebSocket] = []
    reconnect_count = 0

    async def new_connection(start_monitor: bool = False) -> None:
        websocket = RecordingWebSocket()
        sockets.append(websocket)
        monitor._ws = websocket  # type: ignore[assignment]  # pylint: disable=protected-access

    async def resubscribe_all() -> None:
        nonlocal reconnect_count
        reconnect_count += 1
        if reconnect_count == 1:
            raise RuntimeError("temporary send failure")
        monitor._disconnect = True  # pylint: disable=protected-access
        assert monitor._ws  # pylint: disable=protected-access
        monitor._ws.closed = True

    monitor.new_connection = new_connection  # type: ignore[method-assign]
    monitor._resubscribe_all = resubscribe_all  # type: ignore[method-assign]  # pylint: disable=protected-access

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())
        await monitor._monitor()  # pylint: disable=protected-access

    assert reconnect_count == 2
    assert len(sockets) == 2
    assert sockets[0].closed


async def test_callbacks_are_isolated_and_do_not_log_secrets(caplog: Any) -> None:
    """One failed callback must not stop other sync or async subscriptions."""
    frames = [
        SimpleNamespace(
            type=WSMsgType.TEXT,
            data=json.dumps({"type": "next", "id": subscription_id}),
            extra=None,
        )
        for subscription_id in ("bad", "sync", "async")
    ]
    frames.append(SimpleNamespace(type=WSMsgType.CLOSED, data=None, extra=None))
    websocket = RecordingWebSocket(frames)
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    monitor._ws = websocket  # type: ignore[assignment]  # pylint: disable=protected-access
    received: list[str] = []
    secret = "synthetic-auth-token"

    def failing_callback(message: dict[str, Any]) -> None:
        raise RuntimeError(f"headers={{'u-sess': '{secret}'}}")

    def sync_callback(message: dict[str, Any]) -> None:
        received.append("sync")

    async def async_callback(message: dict[str, Any]) -> None:
        received.append("async")

    monitor._subscriptions = {  # pylint: disable=protected-access
        "bad": (failing_callback, {}),
        "sync": (sync_callback, {}),
        "async": (async_callback, {}),
    }

    with caplog.at_level(logging.ERROR, logger="rivian.ws_monitor"):
        await monitor._receiver()  # pylint: disable=protected-access

    assert received == ["sync", "async"]
    assert "Web socket subscription callback failed (RuntimeError)" in caplog.text
    assert secret not in caplog.text


async def test_new_connection_clears_stale_ack_before_connecting() -> None:
    """A replacement socket cannot inherit acknowledgement from the old one."""
    monitor = WebSocketMonitor(FakeAccount(), "wss://example", AsyncMock())  # type: ignore[arg-type]
    websocket = RecordingWebSocket()
    session = FakeSession(websocket, monitor)
    monitor._account = FakeAccount(session)  # type: ignore[assignment]  # pylint: disable=protected-access
    monitor.connection_ack.set()

    await monitor.new_connection()

    assert not monitor.connection_ack.is_set()
    await monitor.close()
