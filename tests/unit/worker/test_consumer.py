"""SPEC-005 · REQ-MNT-005: ack somente apos persistir/rejeitar; falha de banco => sem ack + reconexao."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
from spatial_storage.memory import InMemoryRepository
from spatial_storage.seed_data import SEED
from worker.consumer import Consumer
from worker.handler import MessageHandler, Stats

from tests.contract.telemetry_cases import VALID, with_

NOW = datetime(2026, 10, 19, 12, 0, 5, tzinfo=UTC)
TOPIC = "spatial/v1/equipment/EQ-001/telemetry"


@dataclass
class FakeMessage:
    topic: str
    payload: bytes
    mid: int = 1
    qos: int = 1


@dataclass
class FakeClient:
    acked: list[tuple[int, int]] = field(default_factory=list)
    disconnects: int = 0
    subscribed: list[tuple[str, int]] = field(default_factory=list)

    def ack(self, mid: int, qos: int) -> None:
        self.acked.append((mid, qos))

    def disconnect(self) -> None:
        self.disconnects += 1

    def subscribe(self, topic: str, qos: int = 0) -> None:
        self.subscribed.append((topic, qos))


def _consumer(repo: InMemoryRepository | None = None) -> tuple[Consumer, InMemoryRepository]:
    repo = repo or InMemoryRepository(SEED)
    return Consumer(MessageHandler(repo, lambda: NOW, Stats())), repo


def _msg(event: dict[str, Any], mid: int = 1) -> FakeMessage:
    return FakeMessage(TOPIC, json.dumps(event).encode(), mid)


def test_acks_after_successful_persistence() -> None:
    consumer, repo = _consumer()
    client = FakeClient()

    consumer.on_message(client, None, _msg(VALID, mid=7))

    assert client.acked == [(7, 1)]
    assert repo.event_count("EQ-001") == 1


def test_acks_duplicates_and_rejections_because_they_are_final() -> None:
    consumer, _ = _consumer()
    client = FakeClient()

    consumer.on_message(client, None, _msg(VALID, mid=1))
    consumer.on_message(client, None, _msg(VALID, mid=2))  # duplicata
    consumer.on_message(client, None, FakeMessage(TOPIC, b"garbage", 3))  # rejeitada

    assert client.acked == [(1, 1), (2, 1), (3, 1)]
    assert client.disconnects == 0


def test_database_failure_does_not_ack_and_forces_reconnect() -> None:
    class Broken(InMemoryRepository):
        def record(self, event: Any, received_at: datetime) -> Any:
            raise ConnectionError("database down")

    consumer, _ = _consumer(Broken(SEED))
    client = FakeClient()

    consumer.on_message(client, None, _msg(VALID, mid=5))

    assert client.acked == []
    assert client.disconnects == 1
    assert consumer.failed is True


def test_after_a_failure_further_messages_are_neither_processed_nor_acked() -> None:
    class Flaky(InMemoryRepository):
        calls = 0

        def record(self, event: Any, received_at: datetime) -> Any:
            Flaky.calls += 1
            if Flaky.calls == 1:
                raise ConnectionError("down")
            return super().record(event, received_at)

    consumer, repo = _consumer(Flaky(SEED))
    client = FakeClient()

    consumer.on_message(client, None, _msg(VALID, mid=1))
    consumer.on_message(client, None, _msg(with_(event_id="e2"), mid=2))

    assert client.acked == []
    assert repo.event_count("EQ-001") == 0
    assert Flaky.calls == 1


def test_redelivery_after_reconnect_is_processed_exactly_once() -> None:
    class Flaky(InMemoryRepository):
        calls = 0

        def record(self, event: Any, received_at: datetime) -> Any:
            Flaky.calls += 1
            if Flaky.calls == 1:
                raise ConnectionError("down")
            return super().record(event, received_at)

    consumer, repo = _consumer(Flaky(SEED))
    client = FakeClient()
    consumer.on_message(client, None, _msg(VALID, mid=1))  # falha

    consumer.on_connect(client, None, None, 0, None)  # reconectou
    consumer.on_message(client, None, _msg(VALID, mid=1))  # redelivery
    consumer.on_message(client, None, _msg(VALID, mid=1))  # redelivery duplicado do broker

    assert client.acked == [(1, 1), (1, 1)]
    assert repo.event_count("EQ-001") == 1


@pytest.mark.parametrize("bad_mid", [0])
def test_unexpected_handler_error_is_treated_like_a_failure(bad_mid: int) -> None:
    consumer, _ = _consumer()
    consumer.handler = None  # type: ignore[assignment]
    client = FakeClient()

    consumer.on_message(client, None, _msg(VALID, mid=bad_mid))

    assert client.acked == []
    assert client.disconnects == 1


def test_on_connect_subscribes_with_qos1_and_clears_failure_state() -> None:
    consumer, _ = _consumer()
    consumer.failed = True
    client = FakeClient()

    consumer.on_connect(client, None, None, 0, None)

    assert client.subscribed == [("spatial/v1/equipment/+/telemetry", 1)]
    assert consumer.failed is False


def test_failed_connect_does_not_subscribe() -> None:
    consumer, _ = _consumer()
    client = FakeClient()

    consumer.on_connect(client, None, None, 5, None)  # 5 = not authorized

    assert client.subscribed == []


@pytest.mark.parametrize(
    ("current", "failed", "expected"),
    [(1.0, True, 2.0), (2.0, True, 4.0), (16.0, True, 30.0), (30.0, True, 30.0), (8.0, False, 1.0)],
)
def test_reconnect_backoff_grows_on_failures_and_resets_on_clean_disconnects(
    current: float, failed: bool, expected: float
) -> None:
    from worker.consumer import next_backoff

    assert next_backoff(current, failed=failed) == expected
