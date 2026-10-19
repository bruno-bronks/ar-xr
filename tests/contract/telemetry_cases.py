"""Casos de referencia do contrato de telemetria v1 (SPEC-004).

Compartilhados entre o teste do JSON Schema e o do parser de dominio, para que os dois nunca divirjam.
"""

import copy
from typing import Any

VALID: dict[str, Any] = {
    "schema_version": 1,
    "event_id": "sim-0001",
    "source": "equipment-simulator",
    "equipment_id": "EQ-001",
    "sensor_type": "temperature",
    "value": 72.4,
    "unit": "celsius",
    "observed_at": "2026-10-19T12:00:00Z",
    "quality": "GOOD",
}


def with_(**changes: Any) -> dict[str, Any]:
    event = copy.deepcopy(VALID)
    event.update(changes)
    return event


def without(field: str) -> dict[str, Any]:
    event = copy.deepcopy(VALID)
    del event[field]
    return event


VALID_EVENTS: list[dict[str, Any]] = [
    VALID,
    with_(observed_at="2026-10-19T09:00:00-03:00"),
    with_(observed_at="2026-10-19T12:00:00.123456Z"),
    with_(sensor_type="vibration", unit="mm/s", value=0),
    with_(quality="BAD", value=-5.5),
    with_(value=1e300),
]

INVALID_EVENTS: list[dict[str, Any]] = [
    *[without(field) for field in VALID],
    with_(schema_version=2),
    with_(schema_version="1"),
    with_(quality="MAYBE"),
    with_(quality="good"),
    with_(sensor_type="pressure"),
    with_(observed_at="2026-10-19T12:00:00"),  # sem offset => ambiguo
    with_(observed_at="ontem"),
    with_(observed_at=1760875200),
    with_(value="72.4"),
    with_(value=None),
    with_(value=True),
    with_(event_id=""),
    with_(event_id="a b"),
    with_(event_id="x" * 129),
    with_(source=""),
    with_(equipment_id="EQ/001"),  # separador de topico MQTT nao permitido
    with_(equipment_id="EQ-#"),  # wildcard MQTT nao permitido
    with_(equipment_id="EQ-+"),
    with_(unit=""),
    with_(unit="x" * 17),
    {**VALID, "received_at": "2026-10-19T12:00:01Z"},  # received_at e atribuido pelo worker
    {**VALID, "extra": 1},
]
