"""REQ-ENG-001 / REQ-ENG-002 / REQ-ENG-003 / REQ-ENG-004 contra o ambiente Docker Compose real.

Execucao: suba o Compose e defina BASE_URL (ex.: http://127.0.0.1:8088). Sem BASE_URL o teste
e pulado — nunca "passa" sem ambiente.
"""

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterable

import pytest

BASE_URL = os.environ.get("BASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(BASE_URL is None, reason="BASE_URL nao definido (Compose nao informado)"),
]


def _get(path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
    assert BASE_URL is not None
    request = urllib.request.Request(BASE_URL + path, headers=headers or {})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return response.status, _lower(response.headers.items()), response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, _lower(error.headers.items()), error.read().decode()


def _lower(items: Iterable[tuple[str, str]]) -> dict[str, str]:
    """Nomes de cabecalho HTTP sao case-insensitive: normaliza para minusculas."""
    return {name.lower(): value for name, value in items}


def test_live() -> None:
    status, _, body = _get("/health/live")

    assert status == 200
    assert json.loads(body) == {"status": "alive"}


def test_ready_with_real_postgres_and_mosquitto() -> None:
    status, _, body = _get("/health/ready")

    assert status == 200, body
    assert json.loads(body) == {"status": "ready", "checks": {"database": "ok", "broker": "ok"}}


def test_correlation_id_round_trip() -> None:
    _, headers, _ = _get("/health/live", {"X-Correlation-ID": "smoke-1"})

    assert headers["x-correlation-id"] == "smoke-1"


def test_ready_body_contains_no_connection_details() -> None:
    _, _, body = _get("/health/ready")

    for forbidden in ("postgresql", "password", "spatial_dev", "@db"):
        assert forbidden not in body.lower()
