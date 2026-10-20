"""SPEC-011 · REQ-IOT-002: o emulador de dispositivo contra a pilha REAL (broker anonimo de dev + worker + PostgreSQL).

Valores validos sao persistidos (e visiveis na API); payload invalido ou topico alheio e rejeitado
pelo worker e NUNCA e persistido. A verificacao e feita no banco (nao em "ultima leitura") porque o
simulador do Compose continua publicando.
"""

import json
from datetime import UTC, datetime

import pytest
from simulator.device_emulator import DeviceEmulator, build_event
from sqlalchemy import text

from tests.integration._stack import (
    MQTT_HOST,
    MQTT_PORT,
    compose,
    db_engine,
    event_count,
    requires_stack,
    wait_until,
)

pytestmark = [pytest.mark.integration, requires_stack]


def _emulator(equipment: str) -> DeviceEmulator:
    return DeviceEmulator(equipment, host=MQTT_HOST, port=MQTT_PORT)


def _rows_with_value(value: float) -> int:
    with db_engine().connect() as conn:
        return int(
            conn.execute(
                text("SELECT count(*) FROM telemetry_events WHERE value = :v"), {"v": value}
            ).scalar_one()
        )


def _rejections() -> int:
    return compose("logs", "--no-color", "worker").stdout.count("message rejected")


def test_valid_emulated_reading_is_persisted_once_with_its_source_and_event_id() -> None:
    event_id = _emulator("EQ-002").publish_reading("temperature", 61.37)

    wait_until(lambda: event_count(event_id) == 1, 30, what="leitura emulada persistida")
    with db_engine().connect() as conn:
        row = conn.execute(
            text("SELECT source, equipment_id, value FROM telemetry_events WHERE event_id = :e"),
            {"e": event_id},
        ).one()
    assert tuple(row) == ("esp32-emulator", "EQ-002", 61.37)


def test_duplicate_event_from_the_device_is_stored_only_once() -> None:
    emulator = _emulator("EQ-002")
    event_id = emulator.publish_reading("vibration", 1.11, event_id="esp32-dup-fixed-1")
    wait_until(lambda: event_count(event_id) == 1, 30, what="primeira entrega")

    emulator.publish_reading("vibration", 1.11, event_id="esp32-dup-fixed-1")

    wait_until(lambda: _rejections() >= 0, 5, what="log")
    assert event_count(event_id) == 1


def test_invalid_payloads_are_rejected_by_the_worker_and_never_persisted() -> None:
    bad_value = 987654.321
    before = _rejections()
    emulator = _emulator("EQ-001")
    now = datetime.now(UTC)
    bad_events = [
        {**build_event("EQ-001", "temperature", bad_value, now), "sensor_type": "pressure"},
        {**build_event("EQ-001", "temperature", bad_value, now), "extra": "campo"},
        {
            **build_event("EQ-001", "temperature", bad_value, now),
            "equipment_id": "EQ-003",
        },  # != topico
    ]

    for event in bad_events:
        emulator.publish_raw(emulator.topic, json.dumps(event).encode())
    emulator.publish_raw(emulator.topic, b"nao e json")

    wait_until(lambda: _rejections() >= before + 4, 30, what="4 rejeicoes novas no log do worker")
    assert _rows_with_value(bad_value) == 0


def test_event_claiming_another_equipment_on_this_devices_topic_is_rejected() -> None:
    bad_value = 123456.789
    before = _rejections()
    emulator = _emulator("EQ-001")
    forged = build_event("EQ-002", "temperature", bad_value, datetime.now(UTC))

    emulator.publish_raw(
        emulator.topic, json.dumps(forged).encode()
    )  # diz ser o EQ-002, no topico do EQ-001

    wait_until(lambda: _rejections() >= before + 1, 30, what="rejeicao")
    assert _rows_with_value(bad_value) == 0
