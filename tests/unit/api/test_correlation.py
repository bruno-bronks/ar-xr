"""SPEC-001 · REQ-ENG-004 (correlation ID e logs estruturados)."""

import json
import logging
import re
import uuid

import pytest
from app.logging_config import JsonFormatter
from app.main import create_app
from app.middleware import CORRELATION_HEADER, normalize_correlation_id
from fastapi.testclient import TestClient

VALID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _client() -> TestClient:
    return TestClient(create_app(checks={"database": lambda: True, "broker": lambda: True}))


def test_header_name_is_x_correlation_id() -> None:
    assert CORRELATION_HEADER == "X-Correlation-ID"


def test_generates_uuid_when_header_missing() -> None:
    response = _client().get("/health/live")

    generated = response.headers[CORRELATION_HEADER]
    assert str(uuid.UUID(generated)) == generated


def test_echoes_valid_incoming_id() -> None:
    response = _client().get("/health/live", headers={CORRELATION_HEADER: "req-123.abc_X"})

    assert response.headers[CORRELATION_HEADER] == "req-123.abc_X"


@pytest.mark.parametrize(
    "hostile",
    [
        "a b",  # espaco
        "x" * 65,  # comprimento
        'id"}, "level": "CRITICAL',  # injecao de campo JSON
        "<script>",
        "",
    ],
)
def test_replaces_invalid_incoming_id(hostile: str) -> None:
    response = _client().get("/health/live", headers={CORRELATION_HEADER: hostile})

    returned = response.headers[CORRELATION_HEADER]
    assert returned != hostile
    assert uuid.UUID(returned)


def test_id_present_on_503_response_too() -> None:
    client = TestClient(create_app(checks={"database": lambda: False, "broker": lambda: True}))

    response = client.get("/health/ready", headers={CORRELATION_HEADER: "abc"})

    assert response.status_code == 503
    assert response.headers[CORRELATION_HEADER] == "abc"


def test_each_request_without_header_gets_distinct_id() -> None:
    client = _client()

    first = client.get("/health/live").headers[CORRELATION_HEADER]
    second = client.get("/health/live").headers[CORRELATION_HEADER]

    assert first != second


@pytest.mark.parametrize(("raw", "keep"), [("ok-1", True), (None, False), ("bad value", False)])
def test_normalize_correlation_id(raw: str | None, keep: bool) -> None:
    result = normalize_correlation_id(raw)

    assert VALID.match(result) or uuid.UUID(result)
    assert (result == raw) is keep


def test_access_log_carries_correlation_id_without_query_string(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="app.access"):
        _client().get("/health/live?token=SEGREDO", headers={CORRELATION_HEADER: "trace-9"})

    records = [r for r in caplog.records if r.name == "app.access"]
    assert len(records) == 1
    record = records[0]
    assert record.__dict__["correlation_id"] == "trace-9"
    assert record.__dict__["method"] == "GET"
    assert record.__dict__["path"] == "/health/live"
    assert record.__dict__["status"] == 200
    assert isinstance(record.__dict__["duration_ms"], float)
    assert "SEGREDO" not in caplog.text


def test_json_formatter_emits_one_json_object_with_required_fields() -> None:
    record = logging.LogRecord("app.access", logging.INFO, __file__, 1, "request", None, None)
    record.correlation_id = "abc"
    record.status = 200

    line = JsonFormatter().format(record)
    payload = json.loads(line)

    assert "\n" not in line
    assert {"timestamp", "level", "logger", "message", "correlation_id"} <= payload.keys()
    assert payload["correlation_id"] == "abc"
    assert payload["status"] == 200
    assert payload["level"] == "INFO"


def test_json_formatter_defaults_correlation_id_when_absent() -> None:
    record = logging.LogRecord("x", logging.WARNING, __file__, 1, "msg", None, None)

    assert json.loads(JsonFormatter().format(record))["correlation_id"] == "-"
