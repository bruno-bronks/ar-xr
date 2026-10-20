"""Emulador de DISPOSITIVO ESP32 (software) — SPEC-011, REQ-IOT-002. NAO e hardware nem firmware.

Faz o que o firmware futuro deve fazer: monta o evento no esquema `telemetry-event.v1`, VALIDA com o
mesmo parser estrito do worker antes de publicar e publica em QoS 1 no PROPRIO topico, com credencial
opcional (broker endurecido). `publish_raw` existe so para testes de rejeicao (payload/topico ruins).

Uso: python -m simulator.device_emulator --equipment EQ-001 --sensor temperature --value 55 --count 3
"""

import argparse
import json
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from pydantic import SecretStr
from spatial_common.mqtt_auth import apply_credentials
from spatial_domain.telemetry import parse_payload

SOURCE = "esp32-emulator"
_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")
_UNITS = {"temperature": "celsius", "vibration": "mm/s"}


def topic_for(equipment_id: str) -> str:
    if not _ID.fullmatch(equipment_id):
        raise ValueError("invalid equipment id")
    return f"spatial/v1/equipment/{equipment_id}/telemetry"


def build_event(
    equipment_id: str,
    sensor: str,
    value: float,
    now: datetime,
    *,
    source: str = SOURCE,
    event_id: str | None = None,
    quality: str = "GOOD",
) -> dict[str, Any]:
    if sensor not in _UNITS:
        raise ValueError(f"unknown sensor: {sensor}")
    return {
        "schema_version": 1,
        "event_id": event_id or f"{source}-{uuid.uuid4().hex[:12]}",
        "source": source,
        "equipment_id": equipment_id,
        "sensor_type": sensor,
        "value": value,
        "unit": _UNITS[sensor],
        "observed_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "quality": quality,
    }


class DeviceEmulator:
    def __init__(
        self,
        equipment_id: str,
        *,
        host: str = "127.0.0.1",
        port: int = 1883,
        username: str | None = None,
        password: SecretStr | None = None,
        timeout_s: float = 10.0,
    ) -> None:
        self.equipment_id = equipment_id
        self.topic = topic_for(equipment_id)
        self._host, self._port, self._timeout = host, port, timeout_s
        self._username, self._password = username, password

    def publish_reading(
        self, sensor: str, value: float, now: datetime | None = None, event_id: str | None = None
    ) -> str:
        """Valida com o parser do worker e publica no proprio topico. Devolve o event_id."""
        event = build_event(
            self.equipment_id, sensor, value, now or datetime.now(UTC), event_id=event_id
        )
        payload = json.dumps(event).encode()
        # firmware que envia o que o worker rejeitaria e defeito: falha antes de publicar
        parse_payload(payload)
        self.publish_raw(self.topic, payload)
        return str(event["event_id"])

    def publish_raw(self, topic: str, payload: bytes) -> None:
        """Publica sem validar (testes de rejeicao). Levanta se o broker nao confirmar (QoS 1)."""
        client = mqtt.Client(
            CallbackAPIVersion.VERSION2, client_id=f"emulator-{uuid.uuid4().hex[:8]}"
        )
        apply_credentials(
            client, self._username, self._password.get_secret_value() if self._password else None
        )
        client.connect(self._host, self._port, keepalive=10)
        client.loop_start()
        try:
            info = client.publish(topic, payload, qos=1)
            info.wait_for_publish(timeout=self._timeout)
            if not info.is_published():
                raise TimeoutError("broker did not acknowledge the publish")
        finally:
            client.loop_stop()
            client.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--equipment", required=True)
    parser.add_argument("--sensor", default="temperature", choices=sorted(_UNITS))
    parser.add_argument("--value", type=float, default=50.0)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument(
        "--username", default=None, help="padrao: usuario = id do equipamento, se houver senha"
    )
    parser.add_argument(
        "--password-env", default="MQTT_PASSWORD", help="variavel de ambiente com a senha"
    )
    args = parser.parse_args()

    import os

    secret = os.environ.get(args.password_env)
    emulator = DeviceEmulator(
        args.equipment,
        host=args.host,
        port=args.port,
        username=(args.username or args.equipment) if secret else None,
        password=SecretStr(secret) if secret else None,
    )
    for i in range(args.count):
        event_id = emulator.publish_reading(args.sensor, args.value)
        print(f"publicado {event_id}")
        if i + 1 < args.count:
            time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
