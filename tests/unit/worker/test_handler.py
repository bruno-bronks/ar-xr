"""SPEC-005 · REQ-MNT-004: pipeline de validacao/rejeicao do worker (sem broker nem banco real)."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from spatial_storage.memory import InMemoryRepository
from spatial_storage.repository import SensorProfile
from spatial_storage.seed_data import SEED, EquipmentSeed, SeedData
from worker.handler import Disposition, MessageHandler, Stats

from tests.contract.telemetry_cases import VALID, with_

NOW = datetime(2026, 10, 19, 12, 0, 5, tzinfo=UTC)
TOPIC = "spatial/v1/equipment/EQ-001/telemetry"


def _handler(repo: InMemoryRepository | None = None) -> tuple[MessageHandler, InMemoryRepository]:
    repo = repo or InMemoryRepository(SEED)
    return MessageHandler(repo, clock=lambda: NOW, stats=Stats()), repo


def _bytes(event: dict[str, Any]) -> bytes:
    return json.dumps(event).encode()


def test_valid_message_is_accepted_and_persisted() -> None:
    handler, repo = _handler()

    result = handler.handle(TOPIC, _bytes(VALID))

    assert result.disposition is Disposition.ACCEPTED
    assert result.reason is None
    assert repo.event_count("EQ-001") == 1
    [reading] = repo.latest_readings("org-a", "EQ-001")
    assert reading.received_at == NOW


def test_duplicate_message_is_reported_and_not_rewritten() -> None:
    handler, repo = _handler()
    handler.handle(TOPIC, _bytes(VALID))

    result = handler.handle(TOPIC, _bytes(with_(value=999.0)))

    assert result.disposition is Disposition.DUPLICATE
    assert repo.event_count("EQ-001") == 1
    [reading] = repo.latest_readings("org-a", "EQ-001")
    assert reading.value == 72.4


def test_old_event_is_history_only() -> None:
    handler, repo = _handler()
    handler.handle(TOPIC, _bytes(VALID))

    result = handler.handle(
        TOPIC, _bytes(with_(event_id="old", observed_at="2026-10-19T11:00:00Z", value=1.0))
    )

    assert result.disposition is Disposition.ACCEPTED_HISTORY_ONLY
    assert repo.event_count("EQ-001") == 2
    assert repo.latest_readings("org-a", "EQ-001")[0].value == 72.4


@pytest.mark.parametrize(
    ("topic", "payload", "reason"),
    [
        (TOPIC, b"\xff\xfe", "INVALID_ENCODING"),
        (TOPIC, b"{oops", "INVALID_JSON"),
        (TOPIC, b'{"value": NaN}', "INVALID_JSON"),
        (TOPIC, _bytes(with_(quality="MAYBE")), "SCHEMA_VIOLATION"),
        (TOPIC, b"[]", "SCHEMA_VIOLATION"),
        ("spatial/v1/equipment/EQ-002/telemetry", _bytes(VALID), "TOPIC_MISMATCH"),
        ("spatial/v1/other/EQ-001/telemetry", _bytes(VALID), "TOPIC_MISMATCH"),
        (
            "spatial/v1/equipment/EQ-NOPE/telemetry",
            _bytes(with_(equipment_id="EQ-NOPE")),
            "UNKNOWN_EQUIPMENT",
        ),
        (TOPIC, _bytes(with_(observed_at="2026-10-19T12:05:06Z")), "TIMESTAMP_IN_FUTURE"),
    ],
)
def test_invalid_messages_are_rejected_with_reason_and_do_not_write(
    topic: str, payload: bytes, reason: str
) -> None:
    handler, repo = _handler()

    result = handler.handle(topic, payload)

    assert result.disposition is Disposition.REJECTED
    assert str(result.reason) == reason
    assert repo.event_count("EQ-001") == 0
    assert repo.latest_readings("org-a", "EQ-001") == []
    assert handler.stats.counts[f"rejected:{reason}"] == 1


def test_unknown_sensor_for_a_known_equipment_is_rejected() -> None:
    limited = SeedData(
        organizations=SEED.organizations,
        equipment=(
            EquipmentSeed(
                "EQ-001",
                "org-a",
                "n",
                "t",
                "l",
                "QR-1",
                (SensorProfile("temperature", "celsius", 1, 2),),
            ),
        ),
    )
    handler, repo = _handler(InMemoryRepository(limited))

    result = handler.handle(TOPIC, _bytes(with_(sensor_type="vibration", unit="mm/s")))

    assert result.disposition is Disposition.REJECTED
    assert str(result.reason) == "UNKNOWN_SENSOR"
    assert repo.event_count("EQ-001") == 0


def test_timestamp_exactly_at_tolerance_is_accepted() -> None:
    handler, _ = _handler()

    result = handler.handle(TOPIC, _bytes(with_(observed_at="2026-10-19T12:05:05Z")))

    assert result.disposition is Disposition.ACCEPTED


def test_stats_count_every_disposition() -> None:
    handler, _ = _handler()

    handler.handle(TOPIC, _bytes(VALID))
    handler.handle(TOPIC, _bytes(VALID))
    handler.handle(TOPIC, b"junk")

    assert dict(handler.stats.counts) == {
        "accepted": 1,
        "duplicate": 1,
        "rejected:INVALID_JSON": 1,
    }


def test_repository_failure_propagates_so_the_caller_can_avoid_acking() -> None:
    class Broken(InMemoryRepository):
        def record(self, event: Any, received_at: datetime) -> Any:
            raise ConnectionError("database down")

    handler, _ = _handler(Broken(SEED))

    with pytest.raises(ConnectionError):
        handler.handle(TOPIC, _bytes(VALID))
    assert not handler.stats.counts


def test_rejection_log_never_contains_oversized_or_raw_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    handler, _ = _handler()
    secret = "A" * 5000

    with caplog.at_level("WARNING", logger="worker.handler"):
        handler.handle(TOPIC, ('{"x": "' + secret + '"').encode())

    assert "INVALID_JSON" in caplog.text
    assert secret not in caplog.text
