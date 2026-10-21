"""SPEC-012 · REQ-OPS-005: metricas do worker (desfecho das mensagens, frescor, conexao ao broker)."""

import urllib.error
import urllib.request
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from spatial_common.metrics import Registry
from spatial_domain.telemetry import RejectReason
from spatial_storage.memory import InMemoryRepository
from spatial_storage.seed_data import SEED
from worker.consumer import Consumer
from worker.handler import Disposition, HandleResult, MessageHandler
from worker.metrics import InstrumentedStats, MetricsServer, watch_consumer

NOW = datetime(2026, 10, 19, 12, 0, 30, tzinfo=UTC)


def _stats(clock: float = 1000.0) -> tuple[InstrumentedStats, Consumer]:
    registry = Registry()
    stats = InstrumentedStats(registry, clock=lambda: clock)
    consumer = Consumer(MessageHandler(InMemoryRepository(SEED), lambda: NOW, stats))
    watch_consumer(registry, consumer)
    return stats, consumer


def _render(stats: InstrumentedStats) -> str:
    return stats.registry.render()


def test_each_disposition_is_counted_with_a_bounded_reason_label() -> None:
    stats, _ = _stats()

    stats.record(HandleResult(Disposition.ACCEPTED))
    stats.record(HandleResult(Disposition.ACCEPTED))
    stats.record(HandleResult(Disposition.DUPLICATE))
    stats.record(HandleResult(Disposition.REJECTED, RejectReason.SCHEMA_VIOLATION))

    text = _render(stats)
    assert 'worker_messages_total{disposition="accepted",reason=""} 2' in text
    assert 'worker_messages_total{disposition="duplicate",reason=""} 1' in text
    assert 'worker_messages_total{disposition="rejected",reason="SCHEMA_VIOLATION"} 1' in text


def test_the_existing_counter_dictionary_keeps_working_for_the_log_line() -> None:
    stats, _ = _stats()

    stats.record(HandleResult(Disposition.REJECTED, RejectReason.TOPIC_MISMATCH))

    assert stats.counts["rejected:TOPIC_MISMATCH"] == 1


def test_last_message_timestamp_is_exported_for_freshness_alerts() -> None:
    stats, _ = _stats(clock=1234.5)

    assert "worker_last_message_timestamp_seconds 0" in _render(stats)
    stats.record(HandleResult(Disposition.ACCEPTED))

    assert "worker_last_message_timestamp_seconds 1234.5" in _render(stats)


def test_broker_connection_is_a_scrape_time_gauge() -> None:
    stats, consumer = _stats()

    assert "worker_mqtt_connected 0" in _render(stats)
    consumer.connected = True
    assert "worker_mqtt_connected 1" in _render(stats)


def test_a_consumer_in_failed_state_is_reported() -> None:
    stats, consumer = _stats()
    consumer.failed = True

    assert "worker_consumer_failed 1" in _render(stats)


@pytest.fixture
def server() -> Iterator[tuple[MetricsServer, str]]:
    stats, _ = _stats()
    stats.record(HandleResult(Disposition.ACCEPTED))
    running = MetricsServer(stats.registry, port=0, host="127.0.0.1")
    running.start()
    try:
        yield running, f"http://127.0.0.1:{running.port}"
    finally:
        running.stop()


def test_metrics_endpoint_serves_prometheus_text(server: tuple[MetricsServer, str]) -> None:
    _, base = server

    with urllib.request.urlopen(f"{base}/metrics", timeout=5) as response:  # noqa: S310
        body = response.read().decode()
        content_type = response.headers["Content-Type"]

    assert content_type.startswith("text/plain; version=0.0.4")
    assert "# TYPE worker_messages_total counter" in body


def test_other_paths_and_methods_are_refused(server: tuple[MetricsServer, str]) -> None:
    _, base = server

    with pytest.raises(urllib.error.HTTPError) as not_found:
        urllib.request.urlopen(f"{base}/admin", timeout=5)  # noqa: S310
    post = urllib.request.Request(f"{base}/metrics", data=b"x", method="POST")  # noqa: S310
    with pytest.raises(urllib.error.HTTPError) as not_allowed:
        urllib.request.urlopen(post, timeout=5)  # noqa: S310

    assert not_found.value.code == 404
    assert not_allowed.value.code in (405, 501)


def test_ingest_lag_histogram_feeds_the_freshness_slo() -> None:
    stats, _ = _stats()

    stats.record(HandleResult(Disposition.ACCEPTED, lag_s=0.4))
    stats.record(HandleResult(Disposition.ACCEPTED, lag_s=3.0))
    stats.record(HandleResult(Disposition.ACCEPTED, lag_s=45.0))
    stats.record(HandleResult(Disposition.DUPLICATE))  # sem lag: nao entra

    text = _render(stats)
    assert 'worker_ingest_lag_seconds_bucket{le="0.5"} 1' in text
    assert 'worker_ingest_lag_seconds_bucket{le="5.0"} 2' in text
    assert 'worker_ingest_lag_seconds_bucket{le="+Inf"} 3' in text
    assert "worker_ingest_lag_seconds_count 3" in text
