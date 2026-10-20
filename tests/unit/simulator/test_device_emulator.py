"""SPEC-011 · REQ-IOT-002 e REQ-IOT-003: o emulador de dispositivo monta eventos validos e so
publica no proprio topico (sem broker: o cliente MQTT e substituido)."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import SecretStr
from simulator import device_emulator
from simulator.device_emulator import DeviceEmulator, build_event, topic_for
from spatial_domain.telemetry import TelemetryRejected, parse_payload

NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)


def test_event_matches_the_strict_worker_parser_for_every_sensor() -> None:
    for sensor, value in (("temperature", 55.5), ("vibration", 1.25)):
        event = build_event("EQ-001", sensor, value, NOW, event_id="e-1")

        parsed = parse_payload(json.dumps(event).encode())

        assert (parsed.equipment_id, parsed.sensor_type, parsed.value) == ("EQ-001", sensor, value)
        assert parsed.source == "esp32-emulator"
        assert parsed.event_id == "e-1"


def test_event_ids_are_unique_by_default_and_unknown_sensor_is_rejected() -> None:
    ids = {build_event("EQ-001", "temperature", 1.0, NOW)["event_id"] for _ in range(50)}

    assert len(ids) == 50
    with pytest.raises(ValueError, match="unknown sensor"):
        build_event("EQ-001", "pressure", 1.0, NOW)


@pytest.mark.parametrize("bad", ["", "a b", "x" * 65, "EQ/001", "EQ+001", "EQ#", "../x"])
def test_topic_is_built_only_for_safe_ids(bad: str) -> None:
    with pytest.raises(ValueError, match="invalid equipment id"):
        topic_for(bad)
    with pytest.raises(ValueError, match="invalid equipment id"):
        DeviceEmulator(bad)


def test_topic_is_the_devices_own() -> None:
    assert topic_for("EQ-007") == "spatial/v1/equipment/EQ-007/telemetry"
    assert DeviceEmulator("EQ-007").topic == "spatial/v1/equipment/EQ-007/telemetry"


class _FakePublishInfo:
    def __init__(self, ok: bool) -> None:
        self._ok = ok

    def wait_for_publish(self, timeout: float | None = None) -> None:
        return None

    def is_published(self) -> bool:
        return self._ok


class _FakeClient:
    instances: list["_FakeClient"] = []  # noqa: RUF012 - dubles de teste

    def __init__(self, *_: Any, **__: Any) -> None:
        self.published: list[tuple[str, bytes, int]] = []
        self.credentials: tuple[str, str | None] | None = None
        self.ok = True
        _FakeClient.instances.append(self)

    def username_pw_set(self, username: str, password: str | None = None) -> None:
        self.credentials = (username, password)

    def connect(self, *_: Any, **__: Any) -> None: ...
    def loop_start(self) -> None: ...
    def loop_stop(self) -> None: ...
    def disconnect(self) -> None: ...

    def publish(self, topic: str, payload: bytes, qos: int = 0) -> _FakePublishInfo:
        self.published.append((topic, payload, qos))
        return _FakePublishInfo(self.ok)


@pytest.fixture
def fake_mqtt(monkeypatch: pytest.MonkeyPatch) -> type[_FakeClient]:
    _FakeClient.instances = []
    monkeypatch.setattr("simulator.device_emulator.mqtt.Client", _FakeClient)
    return _FakeClient


def test_publish_reading_sends_qos1_to_its_own_topic_with_credentials(
    fake_mqtt: type[_FakeClient],
) -> None:
    emulator = DeviceEmulator("EQ-002", username="EQ-002", password=SecretStr("pw"))

    event_id = emulator.publish_reading("vibration", 2.5, NOW, event_id="fixed-1")

    client = fake_mqtt.instances[0]
    topic, payload, qos = client.published[0]
    assert event_id == "fixed-1"
    assert (topic, qos) == ("spatial/v1/equipment/EQ-002/telemetry", 1)
    assert json.loads(payload)["equipment_id"] == "EQ-002"
    assert client.credentials == ("EQ-002", "pw")


def test_anonymous_device_does_not_set_credentials(fake_mqtt: type[_FakeClient]) -> None:
    DeviceEmulator("EQ-001").publish_reading("temperature", 50.0, NOW)

    assert fake_mqtt.instances[0].credentials is None


def test_firmware_defect_is_caught_before_publishing(
    fake_mqtt: type[_FakeClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Se o evento montado fosse rejeitado pelo worker, o emulador falha antes de enviar."""
    monkeypatch.setattr(
        device_emulator,
        "build_event",
        lambda *a, **k: {**build_event("EQ-001", "temperature", 1.0, NOW), "value": float("nan")},
    )

    with pytest.raises((TelemetryRejected, ValueError)):
        DeviceEmulator("EQ-001").publish_reading("temperature", 1.0, NOW)

    assert fake_mqtt.instances == []


def test_unacknowledged_publish_raises(fake_mqtt: type[_FakeClient]) -> None:
    emulator = DeviceEmulator("EQ-001")
    original = fake_mqtt.__init__

    def init(self: _FakeClient, *a: Any, **k: Any) -> None:
        original(self, *a, **k)
        self.ok = False

    fake_mqtt.__init__ = init  # type: ignore[method-assign]
    try:
        with pytest.raises(TimeoutError):
            emulator.publish_raw("spatial/v1/equipment/EQ-001/telemetry", b"{}")
    finally:
        fake_mqtt.__init__ = original  # type: ignore[method-assign]


def test_publish_raw_does_not_validate_so_tests_can_send_bad_payloads(
    fake_mqtt: type[_FakeClient],
) -> None:
    DeviceEmulator("EQ-001").publish_raw("spatial/v1/equipment/EQ-999/telemetry", b"nao e json")

    assert fake_mqtt.instances[0].published[0][1] == b"nao e json"
