"""Metricas do worker (SPEC-012, REQ-OPS-005; D-046).

Sem autenticacao: o endpoint escuta apenas na rede interna do Compose (porta NUNCA publicada no host)
e so expoe contadores agregados. Rotulos de baixa cardinalidade: desfecho e motivo de rejeicao (enum).
"""

import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from spatial_common.metrics import CONTENT_TYPE, Registry

from worker.consumer import Consumer
from worker.handler import HandleResult, Stats

LAG_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)


class InstrumentedStats(Stats):
    """`Stats` que tambem alimenta o registro de metricas (o dicionario `counts` segue valendo)."""

    def __init__(self, registry: Registry, clock: Callable[[], float] = time.time) -> None:
        super().__init__()
        self.registry = registry
        self._clock = clock
        self._messages = registry.counter(
            "worker_messages_total", "Messages by final disposition.", ("disposition", "reason")
        )
        self._last = registry.gauge(
            "worker_last_message_timestamp_seconds",
            "Unix time of the last processed message (0 = none yet).",
        )
        self._last.set(0)
        self._lag = registry.histogram(
            "worker_ingest_lag_seconds",
            "Seconds between a reading's observed_at and its ingestion (accepted messages only).",
            LAG_BUCKETS,
        )

    def record(self, result: HandleResult) -> None:
        super().record(result)
        reason = str(result.reason) if result.reason is not None else ""
        self._messages.inc(disposition=result.disposition.value.lower(), reason=reason)
        self._last.set(self._clock())
        if result.lag_s is not None:
            self._lag.observe(result.lag_s)


def watch_consumer(registry: Registry, consumer: Consumer) -> None:
    connected = registry.gauge("worker_mqtt_connected", "1 while connected to the broker.")
    failed = registry.gauge("worker_consumer_failed", "1 after an infrastructure failure.")

    def collect() -> None:
        connected.set(1 if consumer.connected else 0)
        failed.set(1 if consumer.failed else 0)

    registry.add_collector(collect)


class MetricsServer:
    """Servidor HTTP minimo (stdlib) que responde apenas `GET /metrics`."""

    def __init__(self, registry: Registry, port: int, host: str = "0.0.0.0") -> None:  # noqa: S104
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path != "/metrics":
                    self.send_error(404)
                    return
                body = registry.render().encode()
                self.send_response(200)
                self.send_header("Content-Type", CONTENT_TYPE)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:  # silencioso: nao polui o log
                return

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
