"""Utilitarios para testes contra a pilha Docker Compose real (BASE_URL + broker + banco no host)."""

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.enums import CallbackAPIVersion
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get("BASE_URL")
MQTT_HOST = os.environ.get("MQTT_HOST_TEST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

TOKEN_A = "demo-operator-a"
TOKEN_B = "demo-operator-b"

requires_stack = pytest.mark.skipif(
    BASE_URL is None or DATABASE_URL is None,
    reason="BASE_URL/TEST_DATABASE_URL nao definidos (pilha Compose nao informada)",
)


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["docker", "compose", *args],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=check,
        timeout=180,
    )


def api(
    path: str, token: str | None = TOKEN_A, headers: dict[str, str] | None = None
) -> tuple[int, Any]:
    assert BASE_URL is not None
    request_headers = dict(headers or {})
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE_URL + path, headers=request_headers)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def wait_until[T](
    probe: Callable[[], T | bool | None], timeout: float, interval: float = 0.5, what: str = ""
) -> T:
    deadline = time.monotonic() + timeout
    last: object = None
    while time.monotonic() < deadline:
        try:
            last = probe()
        except Exception as exc:  # a pilha pode estar reiniciando
            last = exc
        else:
            if last:
                return last  # type: ignore[return-value]
        time.sleep(interval)
    raise AssertionError(f"timeout ({timeout}s) esperando: {what or probe}; ultimo valor: {last!r}")


def db_engine() -> Engine:
    assert DATABASE_URL is not None
    return create_engine(DATABASE_URL)


def event_count(event_id: str) -> int:
    with db_engine().connect() as conn:
        return int(
            conn.execute(
                text("SELECT count(*) FROM telemetry_events WHERE event_id = :e"), {"e": event_id}
            ).scalar_one()
        )


def new_id(prefix: str = "it") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def event(
    equipment: str,
    sensor: str,
    value: float,
    *,
    event_id: str | None = None,
    observed_at: datetime | None = None,
    source: str = "integration-test",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_id": event_id or new_id(),
        "source": source,
        "equipment_id": equipment,
        "sensor_type": sensor,
        "value": value,
        "unit": "celsius" if sensor == "temperature" else "mm/s",
        "observed_at": iso(observed_at or datetime.now(UTC)),
        "quality": "GOOD",
    }


def publish(topic: str, payload: bytes | dict[str, Any], qos: int = 1) -> None:
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"it-{uuid.uuid4().hex[:8]}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    client.loop_start()
    try:
        info = client.publish(topic, body, qos=qos)
        info.wait_for_publish(timeout=10)
        assert info.is_published(), "broker nao confirmou a publicacao"
    finally:
        client.loop_stop()
        client.disconnect()


def publish_event(payload: dict[str, Any]) -> None:
    publish(f"spatial/v1/equipment/{payload['equipment_id']}/telemetry", payload)


def feed_equipment(equipment: str, temperature: float, vibration: float = 1.0) -> datetime:
    """Publica as duas leituras do equipamento agora e devolve o instante usado."""
    now = datetime.now(UTC)
    publish_event(event(equipment, "temperature", temperature, observed_at=now))
    publish_event(
        event(equipment, "vibration", vibration, observed_at=now + timedelta(milliseconds=1))
    )
    return now


def latest_value(equipment: str, sensor: str, token: str = TOKEN_A) -> float | None:
    status, body = api(f"/api/v1/equipment/{equipment}/telemetry/latest", token)
    if status != 200:
        return None
    return next((r["value"] for r in body if r["sensor_type"] == sensor), None)


def equipment_status(equipment: str, token: str = TOKEN_A) -> str | None:
    status, body = api(f"/api/v1/equipment/{equipment}", token)
    return body["status"] if status == 200 else None
