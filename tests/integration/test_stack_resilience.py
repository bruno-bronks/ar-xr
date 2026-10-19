"""SPEC-005 A3/A4/A6: idempotencia, ordem, rejeicao, falha de banco, queda do broker e offline REAIS.

Requisitos: REQ-MNT-003, REQ-MNT-004, REQ-MNT-005, REQ-MNT-002, REQ-ENG-003.

O simulador e PARADO durante os testes (para que so os eventos do teste existam) e religado ao fim.
"""

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from tests.integration._stack import (
    api,
    compose,
    equipment_status,
    event,
    event_count,
    feed_equipment,
    latest_value,
    new_id,
    publish,
    publish_event,
    requires_stack,
    wait_until,
)

pytestmark = [pytest.mark.integration, requires_stack]


@pytest.fixture(scope="module", autouse=True)
def quiet_simulator() -> Iterator[None]:
    compose("stop", "simulator")
    yield
    compose("start", "simulator")


def _worker_logs(since: str = "120s") -> str:
    return compose("logs", "worker", "--no-color", "--since", since).stdout


def test_duplicate_event_is_stored_once_and_first_value_wins() -> None:
    event_id = new_id("dup")
    now = datetime.now(UTC)
    publish_event(event("EQ-001", "temperature", 61.0, event_id=event_id, observed_at=now))
    wait_until(lambda: event_count(event_id) == 1, 15, what="primeira gravacao")

    publish_event(event("EQ-001", "temperature", 99.0, event_id=event_id, observed_at=now))
    publish_event(event("EQ-001", "temperature", 99.0, event_id=event_id, observed_at=now))
    time.sleep(3)

    assert event_count(event_id) == 1
    assert latest_value("EQ-001", "temperature") == 61.0


def test_out_of_order_event_does_not_regress_latest_but_is_kept_in_history() -> None:
    now = datetime.now(UTC)
    newer, older = new_id("new"), new_id("old")
    publish_event(event("EQ-002", "temperature", 70.0, event_id=newer, observed_at=now))
    wait_until(
        lambda: latest_value("EQ-002", "temperature") == 70.0, 15, what="vigente = mais novo"
    )

    publish_event(
        event(
            "EQ-002", "temperature", 10.0, event_id=older, observed_at=now - timedelta(seconds=20)
        )
    )
    wait_until(lambda: event_count(older) == 1, 15, what="evento atrasado no historico")

    assert latest_value("EQ-002", "temperature") == 70.0


def test_invalid_messages_are_rejected_with_reason_and_do_not_stop_the_worker() -> None:
    marker = datetime.now(UTC) - timedelta(seconds=1)
    publish("spatial/v1/equipment/EQ-001/telemetry", b"{not json")
    publish("spatial/v1/equipment/EQ-001/telemetry", b'{"value": NaN}')
    publish("spatial/v1/equipment/EQ-001/telemetry", b'{"schema_version": 1}')
    publish(
        "spatial/v1/equipment/EQ-002/telemetry",
        __import__("json").dumps(event("EQ-001", "temperature", 1.0)).encode(),
    )
    publish_event(event("EQ-NOPE", "temperature", 1.0))
    publish_event(
        event("EQ-001", "temperature", 1.0, observed_at=datetime.now(UTC) + timedelta(hours=2))
    )

    wait_until(
        lambda: "TIMESTAMP_IN_FUTURE" in _worker_logs("60s"), 20, what="rejeicoes registradas"
    )
    logs = _worker_logs("60s")
    for reason in (
        "INVALID_JSON",
        "SCHEMA_VIOLATION",
        "TOPIC_MISMATCH",
        "UNKNOWN_EQUIPMENT",
        "TIMESTAMP_IN_FUTURE",
    ):
        assert reason in logs, reason

    good = new_id("good")
    publish_event(event("EQ-001", "temperature", 55.5, event_id=good))
    wait_until(lambda: event_count(good) == 1, 15, what="worker segue aceitando apos rejeicoes")
    assert marker < datetime.now(UTC)


def test_database_outage_loses_no_event_and_recovers_exactly_once() -> None:
    event_id = new_id("dbdown")
    compose("stop", "db")
    try:
        publish_event(event("EQ-003", "temperature", 66.6, event_id=event_id))
        time.sleep(4)  # worker tenta gravar, falha e NAO confirma (sem ack)
    finally:
        compose("start", "db")

    wait_until(
        lambda: event_count(event_id) == 1,
        90,
        interval=1.0,
        what="evento recuperado apos o banco voltar",
    )
    time.sleep(3)

    assert event_count(event_id) == 1  # exatamente uma vez, mesmo com redelivery
    wait_until(lambda: api("/health/ready")[0] == 200, 60, what="api pronta de novo")


def test_broker_restart_is_survived_and_new_events_flow_again() -> None:
    compose("restart", "broker")
    wait_until(
        lambda: api("/health/ready", token=None)[0] == 200,
        90,
        interval=1.0,
        what="ready apos broker",
    )

    event_id = new_id("brk")

    def after_restart() -> bool:
        try:
            publish_event(event("EQ-001", "temperature", 44.4, event_id=event_id))
        except Exception:
            return False
        return event_count(event_id) == 1

    wait_until(after_restart, 90, interval=2.0, what="worker reconectou e gravou")
    assert compose("ps", "worker", "--format", "{{.Health}}").stdout.strip() == "healthy"


def test_equipment_goes_offline_when_data_stops_and_critical_value_does_not_mask_it() -> None:
    feed_equipment("EQ-001", temperature=500.0)  # valor critico
    wait_until(
        lambda: equipment_status("EQ-001") == "CRITICAL", 15, what="CRITICAL com dado fresco"
    )
    status, alerts = api("/api/v1/equipment/EQ-001/alerts")
    assert status == 200
    assert {a["severity"] for a in alerts} == {"CRITICAL"}

    # sem novos eventos: apos offline_after (30 s) o estado deve ser OFFLINE, nao CRITICAL nem NORMAL
    wait_until(
        lambda: equipment_status("EQ-001") == "OFFLINE",
        60,
        interval=1.0,
        what="OFFLINE por silencio",
    )
    _, alerts = api("/api/v1/equipment/EQ-001/alerts")
    assert [(a["severity"], a["rule"]) for a in alerts] == [("OFFLINE", "offline")]
