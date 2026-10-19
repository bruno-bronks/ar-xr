"""SPEC-004 · REQ-MNT-003: contrato do evento de telemetria (JSON Schema + AsyncAPI)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "packages/contracts/telemetry-event.v1.schema.json"
SCHEMA: dict[str, Any] = json.loads(SCHEMA_PATH.read_text("utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

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


def _with(**changes: Any) -> dict[str, Any]:
    event = copy.deepcopy(VALID)
    event.update(changes)
    return event


def _without(field: str) -> dict[str, Any]:
    event = copy.deepcopy(VALID)
    del event[field]
    return event


def test_schema_itself_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_schema_examples_are_valid() -> None:
    for example in SCHEMA["examples"]:
        VALIDATOR.validate(example)


@pytest.mark.parametrize(
    "event",
    [
        VALID,
        _with(observed_at="2026-10-19T09:00:00-03:00"),
        _with(sensor_type="vibration", unit="mm/s", value=0),
        _with(quality="BAD", value=-5.5),
    ],
)
def test_valid_events_pass(event: dict[str, Any]) -> None:
    VALIDATOR.validate(event)


@pytest.mark.parametrize(
    "event",
    [
        *[_without(field) for field in VALID],
        _with(schema_version=2),
        _with(quality="MAYBE"),
        _with(sensor_type="pressure"),
        _with(observed_at="2026-10-19T12:00:00"),  # sem offset => ambiguo
        _with(observed_at="ontem"),
        _with(value="72.4"),
        _with(value=None),
        _with(event_id=""),
        _with(event_id="a b"),
        _with(event_id="x" * 129),
        _with(equipment_id="EQ/001"),  # separador de topico MQTT nao permitido
        _with(equipment_id="EQ-#"),  # wildcard MQTT nao permitido
        _with(unit=""),
        {**VALID, "received_at": "2026-10-19T12:00:01Z"},  # received_at e do worker
        {**VALID, "extra": 1},
    ],
)
def test_invalid_events_are_rejected(event: dict[str, Any]) -> None:
    assert not VALIDATOR.is_valid(event)


def test_non_finite_numbers_are_not_valid_json_numbers() -> None:
    """NaN/Infinity nao sao JSON valido: o parser estrito do worker deve recusa-los."""
    payload = json.dumps(VALID).replace("72.4", "NaN")

    def reject_constant(name: str) -> None:
        raise ValueError(name)

    with pytest.raises(ValueError, match="NaN"):
        json.loads(payload, parse_constant=reject_constant)


ASYNCAPI_PATH = ROOT / "specs/contracts/asyncapi.yaml"
ASYNCAPI: dict[str, Any] = yaml.safe_load(ASYNCAPI_PATH.read_text("utf-8"))


def test_asyncapi_declares_versioned_topic_and_schema_reference() -> None:
    channel = ASYNCAPI["channels"]["equipmentTelemetry"]

    assert ASYNCAPI["asyncapi"].startswith("3.")
    assert channel["address"] == "spatial/v1/equipment/{equipment_id}/telemetry"
    ref = channel["messages"]["telemetryEvent"]["payload"]["$ref"]
    assert (ROOT / "specs/contracts" / ref).resolve() == SCHEMA_PATH.resolve()


def test_asyncapi_defines_qos_retention_and_dedup_policy() -> None:
    for name in ("publishTelemetry", "consumeTelemetry"):
        mqtt = ASYNCAPI["operations"][name]["bindings"]["mqtt"]
        assert mqtt["qos"] == 1
        assert mqtt["retain"] is False
    policy = ASYNCAPI["x-delivery-policy"]
    assert policy["deduplication"] == "(source, event_id)"
    assert {"reconnect", "ordering", "versioning"} <= policy.keys()
