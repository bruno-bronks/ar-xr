"""SPEC-004 / SPEC-005 · REQ-MNT-003 e REQ-MNT-004: parser estrito de telemetria.

Inclui teste diferencial: o parser de dominio deve concordar com o JSON Schema do contrato.
"""

import contextlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from jsonschema import Draft202012Validator, FormatChecker
from spatial_domain.status import Quality
from spatial_domain.telemetry import (
    TelemetryRejected,
    equipment_id_from_topic,
    parse_payload,
    reject_future,
)

from tests.contract.telemetry_cases import INVALID_EVENTS, VALID, VALID_EVENTS, with_

SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "packages/contracts/telemetry-event.v1.schema.json"
)
VALIDATOR = Draft202012Validator(
    json.loads(SCHEMA_PATH.read_text("utf-8")), format_checker=FormatChecker()
)


def _raw(event: dict[str, Any]) -> bytes:
    return json.dumps(event).encode()


def _reason(raw: bytes) -> str:
    with pytest.raises(TelemetryRejected) as info:
        parse_payload(raw)
    return str(info.value.reason)


# --- exemplos -----------------------------------------------------------------------------


def test_parses_valid_event_into_typed_value() -> None:
    event = parse_payload(_raw(VALID))

    assert event.event_id == "sim-0001"
    assert event.source == "equipment-simulator"
    assert event.equipment_id == "EQ-001"
    assert event.sensor_type == "temperature"
    assert event.value == 72.4
    assert event.unit == "celsius"
    assert event.quality is Quality.GOOD
    assert event.observed_at == datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


def test_offset_timestamps_are_normalised_to_utc() -> None:
    event = parse_payload(_raw(with_(observed_at="2026-10-19T09:00:00-03:00")))

    assert event.observed_at == datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    assert event.observed_at.utcoffset() == timedelta(0)


@pytest.mark.parametrize("event", VALID_EVENTS)
def test_all_contract_valid_events_parse(event: dict[str, Any]) -> None:
    parse_payload(_raw(event))


@pytest.mark.parametrize("event", INVALID_EVENTS)
def test_all_contract_invalid_events_are_rejected_as_schema_violation(
    event: dict[str, Any],
) -> None:
    assert _reason(_raw(event)) == "SCHEMA_VIOLATION"


def test_invalid_utf8_is_invalid_encoding() -> None:
    assert _reason(b"\xff\xfe{}") == "INVALID_ENCODING"


@pytest.mark.parametrize("raw", [b"", b"not json", b"{", b"[1,2", b"nul"])
def test_malformed_json_is_invalid_json(raw: bytes) -> None:
    assert _reason(raw) == "INVALID_JSON"


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_json_constants_are_invalid_json(token: str) -> None:
    raw = json.dumps(VALID).replace("72.4", token).encode()

    assert _reason(raw) == "INVALID_JSON"


@pytest.mark.parametrize("raw", [b"[]", b'"x"', b"123", b"null", b"true"])
def test_non_object_json_is_schema_violation(raw: bytes) -> None:
    assert _reason(raw) == "SCHEMA_VIOLATION"


def test_integer_too_large_for_float_is_schema_violation_not_crash() -> None:
    raw = json.dumps(VALID).replace("72.4", "1" + "0" * 400).encode()

    assert _reason(raw) == "SCHEMA_VIOLATION"


def test_duplicate_json_keys_last_wins_and_still_validated() -> None:
    raw = b'{"quality":"BAD",' + json.dumps(VALID)[1:].encode()

    assert parse_payload(raw).quality is Quality.GOOD


def test_very_deeply_nested_json_does_not_crash() -> None:
    raw = b"[" * 100_000 + b"]" * 100_000

    assert _reason(raw) in {"INVALID_JSON", "SCHEMA_VIOLATION"}


# --- topico -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("topic", "expected"),
    [
        ("spatial/v1/equipment/EQ-001/telemetry", "EQ-001"),
        ("spatial/v1/equipment/a.b_c:d-9/telemetry", "a.b_c:d-9"),
        ("spatial/v1/equipment//telemetry", None),
        ("spatial/v2/equipment/EQ-001/telemetry", None),
        ("spatial/v1/equipment/EQ-001/telemetry/extra", None),
        ("spatial/v1/equipment/EQ/001/telemetry", None),
        ("spatial/v1/equipment/EQ-001", None),
        ("other/v1/equipment/EQ-001/telemetry", None),
        ("spatial/v1/equipment/" + "x" * 65 + "/telemetry", None),
        ("", None),
    ],
)
def test_equipment_id_from_topic(topic: str, expected: str | None) -> None:
    assert equipment_id_from_topic(topic) == expected


# --- skew de relogio (D-007) ----------------------------------------------------------------


def test_future_timestamp_beyond_tolerance_is_rejected() -> None:
    received = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    event = parse_payload(_raw(with_(observed_at="2026-10-19T12:05:01Z")))

    with pytest.raises(TelemetryRejected) as info:
        reject_future(event, received)

    assert str(info.value.reason) == "TIMESTAMP_IN_FUTURE"


def test_future_timestamp_within_tolerance_is_accepted_boundary_inclusive() -> None:
    received = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)

    reject_future(parse_payload(_raw(with_(observed_at="2026-10-19T12:05:00Z"))), received)
    reject_future(parse_payload(_raw(with_(observed_at="2020-01-01T00:00:00Z"))), received)


# --- teste diferencial parser x JSON Schema -------------------------------------------------

json_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**6), max_value=10**6),
    st.floats(allow_nan=False, allow_infinity=False, width=32),
    st.text(max_size=12),
)
field_values: dict[str, st.SearchStrategy[Any]] = {
    "schema_version": st.sampled_from([1, 1.0, 2, 0, "1", None, True]),
    "event_id": st.sampled_from(["e1", "a:b.c-d_e", "", "a b", "x" * 128, "x" * 129, "é", 5]),
    "source": st.sampled_from(["sim", "", "x" * 64, "x" * 65, "a/b", None]),
    "equipment_id": st.sampled_from(["EQ-001", "", "EQ/1", "EQ+", "x" * 64, "x" * 65, 1]),
    "sensor_type": st.sampled_from(["temperature", "vibration", "pressure", "", None]),
    "value": json_scalars,
    "unit": st.sampled_from(["c", "", "x" * 16, "x" * 17, None, 3]),
    "observed_at": st.sampled_from(
        [
            "2026-10-19T12:00:00Z",
            "2026-10-19T12:00:00z",
            "2026-10-19t12:00:00Z",
            "2026-10-19T12:00:00+00:00",
            "2026-10-19T12:00:00-03:30",
            "2026-10-19T12:00:00.5Z",
            "2026-10-19T12:00:00",
            "2026-10-19 12:00:00Z",
            "2026-10-19T24:00:00Z",
            "2026-13-19T12:00:00Z",
            "2026-02-30T12:00:00Z",
            "2026-10-19T12:00:60Z",
            "2026-10-19",
            "",
            None,
            20261019,
        ]
    ),
    "quality": st.sampled_from(["GOOD", "BAD", "good", "", None]),
}


@st.composite
def mutated_events(draw: st.DrawFn) -> dict[str, Any]:
    """Poucas mutacoes por caso, para cobrir bem a fronteira valido/invalido."""
    event = dict(VALID)
    for field in draw(st.lists(st.sampled_from(sorted(field_values)), unique=True, max_size=2)):
        event[field] = draw(field_values[field])
    if draw(st.integers(0, 9)) == 0:
        event.pop(draw(st.sampled_from(sorted(VALID))), None)
    if draw(st.integers(0, 9)) == 0:
        event[draw(st.sampled_from(["extra", "received_at"]))] = draw(json_scalars)
    return event


@settings(max_examples=400, deadline=None)
@given(mutated_events())
def test_parser_agrees_with_json_schema(event: dict[str, Any]) -> None:
    schema_valid = VALIDATOR.is_valid(event)

    try:
        parse_payload(_raw(event))
        parser_valid = True
    except TelemetryRejected:
        parser_valid = False

    assert parser_valid == schema_valid, event


@settings(max_examples=200, deadline=None)
@given(st.binary(max_size=200))
def test_parser_never_raises_anything_but_rejection(raw: bytes) -> None:
    with contextlib.suppress(TelemetryRejected):
        parse_payload(raw)
