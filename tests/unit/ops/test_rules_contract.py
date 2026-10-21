"""SPEC-012 · REQ-OPS-005: contrato entre as regras de SLO e o que o codigo REALMENTE expoe.

Achado ao vivo (Fase 6): a regra usava `le="5"` e o Prometheus rotula `le="5.0"`, entao nunca casaria; o teste
de regras com series sinteticas nao pega isso. Aqui, todo seletor `metrica{...}` e todo `le="X"` das regras
precisam existir no texto de `/metrics` da API e do worker.
"""

import re
from pathlib import Path

from app.main import create_app
from fastapi.testclient import TestClient
from spatial_common.metrics import Registry
from spatial_domain.telemetry import RejectReason
from worker.consumer import Consumer
from worker.handler import Disposition, HandleResult, MessageHandler
from worker.metrics import InstrumentedStats, watch_consumer

from tests.unit.api._app import Clock, new_repo, ok

RULES = Path(__file__).resolve().parents[3] / "platform" / "prometheus" / "rules" / "slo.rules.yml"
TOKEN = "metrics-contract-token-123"  # valor ficticio de teste


def _exposition() -> str:
    app = create_app(
        checks={"database": ok, "broker": ok},
        repo=new_repo(),
        clock=Clock(),
        metrics_token=TOKEN,
    )
    client = TestClient(app)
    client.get("/health/live")
    api = str(client.get("/metrics", headers={"Authorization": f"Bearer {TOKEN}"}).text)
    registry = Registry()
    stats = InstrumentedStats(registry)
    stats.record(HandleResult(Disposition.ACCEPTED, lag_s=0.3))
    stats.record(HandleResult(Disposition.REJECTED, RejectReason.SCHEMA_VIOLATION))
    watch_consumer(registry, Consumer(MessageHandler(new_repo(), Clock(), stats)))
    return api + registry.render()


def test_every_metric_name_used_by_the_rules_is_exposed() -> None:
    text = _exposition()
    used = set(
        re.findall(
            r"\b((?:http_|worker_|dependency_)[a-z_]+?)(?:\{|\[|\s|\))", RULES.read_text("utf-8")
        )
    )

    assert used
    missing = sorted(name for name in used if f"{name} " not in text and f"{name}{{" not in text)
    assert not missing, missing


def test_every_le_bucket_selector_matches_a_rendered_bucket_bound() -> None:
    text = _exposition()
    selectors = re.findall(r'(\w+_bucket)\{[^}]*le="([^"]+)"', RULES.read_text("utf-8"))

    assert selectors
    for metric, bound in selectors:
        assert f"{metric}{{" in text
        assert re.search(rf'{metric}\{{[^}}]*le="{re.escape(bound)}"', text), (metric, bound)
