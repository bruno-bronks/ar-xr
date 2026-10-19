"""SPEC-004 · REQ-MNT-003: contrato do evento de telemetria (JSON Schema + AsyncAPI)."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

from tests.contract.telemetry_cases import INVALID_EVENTS, VALID, VALID_EVENTS

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "packages/contracts/telemetry-event.v1.schema.json"
SCHEMA: dict[str, Any] = json.loads(SCHEMA_PATH.read_text("utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def test_schema_itself_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_schema_examples_are_valid() -> None:
    for example in SCHEMA["examples"]:
        VALIDATOR.validate(example)


@pytest.mark.parametrize("event", VALID_EVENTS)
def test_valid_events_pass(event: dict[str, Any]) -> None:
    VALIDATOR.validate(event)


@pytest.mark.parametrize("event", INVALID_EVENTS)
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
