"""SPEC-011 · REQ-IOT-003: broker ENDURECIDO (Mosquitto REAL em contentor proprio, porta aleatoria).

Usa os MESMOS arquivos do compose.secure.yaml (mosquitto.secure.conf + secure.acl + passwd gerado por
scripts/gen_broker_users.py). Exige apenas Docker (nao depende da pilha do Compose).
"""

import importlib.util
import shutil
import subprocess
import threading
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.enums import CallbackAPIVersion

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "eclipse-mosquitto:2.0.18"
DEVICE_A, DEVICE_B = "EQ-T01", "EQ-T02"
TOPIC = "spatial/v1/equipment/{}/telemetry"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker indisponivel"),
]


@dataclass(frozen=True)
class Broker:
    port: int
    passwords: dict[str, str]


def _generate_users(out: Path) -> dict[str, str]:
    spec = importlib.util.spec_from_file_location(
        "gen_broker_users", ROOT / "scripts" / "gen_broker_users.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate(out, [DEVICE_A, DEVICE_B])
    values = dict(
        line.split("=", 1) for line in (out / "credentials.env").read_text("utf-8").split()
    )
    return {
        "worker": values["MQTT_WORKER_PASSWORD"],
        "simulator": values["MQTT_SIMULATOR_PASSWORD"],
        "health": values["MQTT_HEALTH_PASSWORD"],
        DEVICE_A: values["MQTT_DEVICE_PASSWORD_EQ_T01"],
        DEVICE_B: values["MQTT_DEVICE_PASSWORD_EQ_T02"],
    }


@pytest.fixture(scope="module")
def broker(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Broker]:
    work = tmp_path_factory.mktemp("secure-broker")
    passwords = _generate_users(work)
    shutil.copy(ROOT / "platform/mosquitto/mosquitto.secure.conf", work / "mosquitto.conf")
    shutil.copy(ROOT / "platform/mosquitto/secure.acl", work / "acl")
    name = f"it-broker-{uuid.uuid4().hex[:8]}"
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "docker", "run", "-d", "--rm", "--name", name, "-p", "127.0.0.1::1883",
            "-v", f"{work / 'mosquitto.conf'}:/mosquitto/config/mosquitto.conf:ro",
            "-v", f"{work / 'passwd'}:/mosquitto/config/passwd:ro",
            "-v", f"{work / 'acl'}:/mosquitto/config/acl:ro",
            IMAGE,
        ],
        check=True, capture_output=True, text=True, timeout=120,
    )  # fmt: skip
    try:
        state = subprocess.run(  # noqa: S603
            ["docker", "inspect", "-f", "{{.State.Running}}", name],  # noqa: S607
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()  # fmt: skip
        if state != "true":
            logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True).stdout  # noqa: S603, S607
            raise AssertionError(f"broker endurecido saiu ao iniciar:\n{logs[-800:]}")
        out = subprocess.run(  # noqa: S603
            ["docker", "port", name, "1883/tcp"],  # noqa: S607
            check=True, capture_output=True, text=True, timeout=30,
        ).stdout.strip().splitlines()[0]  # fmt: skip
        port = int(out.rsplit(":", 1)[1])
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if _connect("health", passwords["health"], port)[1] == 0:
                break
            time.sleep(0.5)
        else:
            logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True).stdout  # noqa: S603, S607
            raise AssertionError(f"broker endurecido nao subiu:\n{logs[-800:]}")
        yield Broker(port, passwords)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)  # noqa: S603, S607


def _client(user: str | None, password: str | None) -> mqtt.Client:
    client = mqtt.Client(
        CallbackAPIVersion.VERSION2, client_id=f"t-{uuid.uuid4().hex[:8]}", protocol=mqtt.MQTTv5
    )
    if user is not None:
        client.username_pw_set(user, password)
    return client


def _connect(user: str | None, password: str | None, port: int) -> tuple[mqtt.Client | None, int]:
    """Devolve (cliente conectado | None, codigo de retorno do CONNACK; 0 = aceito)."""
    client = _client(user, password)
    done = threading.Event()
    result: dict[str, int] = {}

    def on_connect(_c: Any, _u: Any, _f: Any, reason_code: Any, _p: Any) -> None:
        result["code"] = int(reason_code.value)
        done.set()

    client.on_connect = on_connect
    try:
        client.connect("127.0.0.1", port, keepalive=10)
    except OSError:
        return None, -1
    client.loop_start()
    if not done.wait(8) or result.get("code") != 0:
        client.loop_stop()
        client.disconnect()
        return None, result.get("code", -1)
    return client, 0


def _publish_code(client: mqtt.Client, topic: str, payload: bytes = b"{}") -> int:
    """Codigo do PUBACK (MQTT 5): 0 = aceito; 135 (0x87) = nao autorizado."""
    done = threading.Event()
    result: dict[str, int] = {}

    def on_publish(_c: Any, _u: Any, _mid: Any, reason_code: Any, _p: Any) -> None:
        result["code"] = int(reason_code.value)
        done.set()

    client.on_publish = on_publish
    client.publish(topic, payload, qos=1)
    assert done.wait(8), "sem PUBACK"
    return result["code"]


def _subscribe_codes(client: mqtt.Client, topic: str) -> list[int]:
    done = threading.Event()
    result: dict[str, list[int]] = {}

    def on_subscribe(_c: Any, _u: Any, _mid: Any, reason_codes: Any, _p: Any) -> None:
        result["codes"] = [int(rc.value) for rc in reason_codes]
        done.set()

    client.on_subscribe = on_subscribe
    client.subscribe(topic, qos=1)
    assert done.wait(8), "sem SUBACK"
    return result["codes"]


PUBACK_OK = (0, 16)  # 0 = aceito; 16 (0x10) = aceito, sem assinantes


def _listen(client: mqtt.Client) -> list[tuple[str, bytes]]:
    """Registra as mensagens que o broker REALMENTE entrega a este cliente."""
    received: list[tuple[str, bytes]] = []
    client.on_message = lambda _c, _u, msg: received.append((msg.topic, msg.payload))
    return received


def _close(*clients: mqtt.Client | None) -> None:
    for c in clients:
        if c is not None:
            c.loop_stop()
            c.disconnect()


def test_anonymous_wrong_password_and_unknown_user_are_refused(broker: Broker) -> None:
    anonymous, anon_code = _connect(None, None, broker.port)
    wrong, wrong_code = _connect(DEVICE_A, "senha-errada", broker.port)
    unknown, unknown_code = _connect("intruso", broker.passwords[DEVICE_A], broker.port)

    assert (anonymous, wrong, unknown) == (None, None, None)
    assert anon_code != 0
    assert wrong_code != 0
    assert unknown_code != 0


def test_device_publishes_to_its_own_topic_and_the_worker_receives_it(broker: Broker) -> None:
    worker, _ = _connect("worker", broker.passwords["worker"], broker.port)
    device, code = _connect(DEVICE_A, broker.passwords[DEVICE_A], broker.port)
    assert worker is not None
    assert device is not None
    assert code == 0
    received: list[bytes] = []
    worker.on_message = lambda _c, _u, msg: received.append(msg.payload)
    assert _subscribe_codes(worker, "spatial/v1/equipment/+/telemetry") == [1]  # QoS 1 concedido

    publish_code = _publish_code(device, TOPIC.format(DEVICE_A), b'{"ok": true}')

    assert publish_code == 0
    deadline = time.monotonic() + 5
    while not received and time.monotonic() < deadline:
        time.sleep(0.1)
    _close(worker, device)
    assert received == [b'{"ok": true}']


def test_device_cannot_publish_to_another_equipments_topic(broker: Broker) -> None:
    worker, _ = _connect("worker", broker.passwords["worker"], broker.port)
    device, _ = _connect(DEVICE_A, broker.passwords[DEVICE_A], broker.port)
    assert worker is not None
    assert device is not None
    received: list[bytes] = []
    worker.on_message = lambda _c, _u, msg: received.append(msg.payload)
    _subscribe_codes(worker, "spatial/v1/equipment/+/telemetry")

    code = _publish_code(device, TOPIC.format(DEVICE_B), b'{"forjado": true}')

    time.sleep(1.0)
    _close(worker, device)
    assert code == 135  # nao autorizado
    assert received == []


@pytest.mark.parametrize(
    "topic",
    [
        "spatial/v1/equipment/EQ-T01/command",  # nao existe canal de comando (sem atuacao)
        "spatial/v1/equipment/EQ-T01/telemetry/extra",
        "spatial/v1/equipment/EQ-T01",
        "$SYS/broker/uptime",
        "outro/namespace",
    ],
)
def test_device_cannot_publish_outside_its_telemetry_topic(broker: Broker, topic: str) -> None:
    device, _ = _connect(DEVICE_A, broker.passwords[DEVICE_A], broker.port)
    assert device is not None

    code = _publish_code(device, topic)

    _close(device)
    assert code == 135


@pytest.mark.parametrize(
    "topic", ["spatial/v1/equipment/EQ-T01/telemetry", "spatial/v1/equipment/+/telemetry", "#"]
)
def test_device_never_receives_any_telemetry_even_if_the_subscribe_is_acknowledged(
    broker: Broker, topic: str
) -> None:
    """O Mosquitto pode responder SUBACK 'concedido', mas a ACL impede a ENTREGA: e isso que vale."""
    device, _ = _connect(DEVICE_A, broker.passwords[DEVICE_A], broker.port)
    simulator, _ = _connect("simulator", broker.passwords["simulator"], broker.port)
    assert device is not None
    assert simulator is not None
    received = _listen(device)
    _subscribe_codes(device, topic)

    _publish_code(simulator, TOPIC.format(DEVICE_A), b'{"segredo": 1}')
    _publish_code(simulator, TOPIC.format(DEVICE_B), b'{"segredo": 2}')
    time.sleep(1.5)

    _close(device, simulator)
    assert received == []


def test_worker_reads_but_cannot_publish_and_simulator_publishes_for_any_equipment(
    broker: Broker,
) -> None:
    worker, _ = _connect("worker", broker.passwords["worker"], broker.port)
    simulator, _ = _connect("simulator", broker.passwords["simulator"], broker.port)
    assert worker is not None
    assert simulator is not None

    worker_code = _publish_code(worker, TOPIC.format(DEVICE_A))
    simulator_a = _publish_code(simulator, TOPIC.format(DEVICE_A))
    simulator_b = _publish_code(simulator, TOPIC.format(DEVICE_B))
    simulator_cmd = _publish_code(simulator, "spatial/v1/equipment/EQ-T01/command")

    _close(worker, simulator)
    assert worker_code == 135
    assert simulator_a in PUBACK_OK
    assert simulator_b in PUBACK_OK
    assert simulator_cmd == 135


def test_health_user_reads_broker_stats_only(broker: Broker) -> None:
    health, _ = _connect("health", broker.passwords["health"], broker.port)
    simulator, _ = _connect("simulator", broker.passwords["simulator"], broker.port)
    assert health is not None
    assert simulator is not None
    received = _listen(health)
    _subscribe_codes(health, "$SYS/broker/uptime")
    _subscribe_codes(health, "spatial/v1/equipment/+/telemetry")

    publish = _publish_code(health, TOPIC.format(DEVICE_A))
    _publish_code(simulator, TOPIC.format(DEVICE_A), b'{"segredo": 3}')
    deadline = time.monotonic() + 15
    while (
        not any(topic == "$SYS/broker/uptime" for topic, _ in received)
        and time.monotonic() < deadline
    ):
        time.sleep(0.2)

    _close(health, simulator)
    assert publish == 135
    assert any(topic == "$SYS/broker/uptime" for topic, _ in received)  # le as estatisticas
    assert not any(topic.startswith("spatial/") for topic, _ in received)  # nunca a telemetria


def test_default_dev_broker_config_stays_anonymous_and_secure_one_does_not() -> None:
    dev = (ROOT / "platform/mosquitto/mosquitto.conf").read_text("utf-8")
    secure = (ROOT / "platform/mosquitto/mosquitto.secure.conf").read_text("utf-8")

    assert "allow_anonymous true" in dev
    assert "allow_anonymous false" in secure
    assert "password_file" in secure
    assert "acl_file" in secure
