"""OUT-MNT-002 / REQ-MNT-003: latencia publicacao MQTT -> visivel na API (pilha Compose real).

Metodologia (registrada em docs/evidence/phase-1/latency.json):
  - simulador parado; N eventos sequenciais em EQ-001/temperature com valores unicos;
  - publicador MQTT persistente (conectado ANTES de medir); t_pub = instante imediatamente antes de
    `client.publish` (QoS 1);
  - t_vis = primeiro instante em que GET /telemetry/latest devolve o valor (polling a cada 50 ms);
  - latencia = t_vis - t_pub  (inclui broker, worker, PostgreSQL, API e o proprio polling).
O numero NAO representa producao: loopback, uma maquina Windows com Docker Desktop, um usuario.
"""

import json
import platform
import statistics
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.enums import CallbackAPIVersion

from tests.integration._stack import (
    MQTT_HOST,
    MQTT_PORT,
    api,
    compose,
    event,
    latest_value,
    requires_stack,
    wait_until,
)

pytestmark = [pytest.mark.integration, requires_stack]

EVIDENCE = Path(__file__).resolve().parents[2] / "docs/evidence/phase-1/latency.json"
SAMPLES = 100
POLL_S = 0.05
BUDGET_S = 3.0  # meta proposta: p95 < 3 s
PANEL_POLL_S = 2.0  # intervalo de atualizacao do painel web (SPEC-007)


@pytest.fixture(scope="module", autouse=True)
def quiet_simulator() -> Iterator[None]:
    compose("stop", "simulator")
    yield
    compose("start", "simulator")


@pytest.fixture(scope="module")
def publisher() -> Iterator[mqtt.Client]:
    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"latency-{uuid.uuid4().hex[:8]}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    yield client
    client.loop_stop()
    client.disconnect()


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered) + 0.5) - 1))
    return ordered[index]


def test_publish_to_api_latency_p95_is_below_budget(publisher: mqtt.Client) -> None:
    wait_until(lambda: api("/health/ready", token=None)[0] == 200, 30, what="pilha pronta")
    latencies: list[float] = []

    for i in range(SAMPLES):
        value = 1000.0 + i + 0.5  # unico por amostra
        payload = event("EQ-001", "temperature", value)
        start = time.perf_counter()
        publisher.publish("spatial/v1/equipment/EQ-001/telemetry", json.dumps(payload), qos=1)
        while True:
            if latest_value("EQ-001", "temperature") == value:
                latencies.append(time.perf_counter() - start)
                break
            if time.perf_counter() - start > 10:
                pytest.fail(f"amostra {i} nao ficou visivel em 10 s")
            time.sleep(POLL_S)
        time.sleep(0.1)

    p50, p95, p99 = (_percentile(latencies, p) for p in (50, 95, 99))
    summary = {
        "measured_at": datetime.now(UTC).isoformat(),
        "samples": SAMPLES,
        "poll_interval_s": POLL_S,
        "latency_s": {
            "min": round(min(latencies), 4),
            "mean": round(statistics.fmean(latencies), 4),
            "p50": round(p50, 4),
            "p95": round(p95, 4),
            "p99": round(p99, 4),
            "max": round(max(latencies), 4),
        },
        "panel_poll_interval_s": PANEL_POLL_S,
        "panel_perceived_p95_upper_bound_s": round(p95 + PANEL_POLL_S, 4),
        "budget_s": BUDGET_S,
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "docker_compose": compose("version", "--short").stdout.strip(),
            "topology": "loopback; db+broker+api+worker em containers (Docker Desktop); cliente de teste no host",
        },
        "caveats": [
            "uma maquina, um usuario, sem carga concorrente; nao representa producao",
            "latencia de pipeline medida por polling de 50 ms (resolucao do metodo)",
            "o painel web atualiza a cada 2 s: a latencia percebida no painel e ate 'pipeline + 2 s'",
        ],
        "result": "PASS" if p95 < BUDGET_S else "FAIL",
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    assert p95 < BUDGET_S, summary
