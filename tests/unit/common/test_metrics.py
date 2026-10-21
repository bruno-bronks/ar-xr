"""SPEC-012 · REQ-OPS-005: registro de metricas no formato de texto Prometheus (sem dependencia externa)."""

import re
import threading

import pytest
from spatial_common.metrics import Registry

# Linha de amostra valida do formato de texto: nome{labels} valor
_SAMPLE = re.compile(
    r'^[a-zA-Z_:][a-zA-Z0-9_:]*(\{([a-zA-Z_][a-zA-Z0-9_]*="([^"\\\n]|\\.)*",?)*\})? \S+$'
)


def _sample_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line and not line.startswith("#")]


def test_counter_renders_help_type_and_labelled_samples() -> None:
    registry = Registry()
    requests = registry.counter(
        "app_requests_total", "Requests handled.", ("route", "status_class")
    )

    requests.inc(route="/health/live", status_class="2xx")
    requests.inc(2, route="/health/live", status_class="2xx")
    requests.inc(route="/api/v1/equipment", status_class="4xx")

    text = registry.render()
    assert "# HELP app_requests_total Requests handled." in text
    assert "# TYPE app_requests_total counter" in text
    assert 'app_requests_total{route="/health/live",status_class="2xx"} 3' in text
    assert 'app_requests_total{route="/api/v1/equipment",status_class="4xx"} 1' in text
    assert all(_SAMPLE.match(line) for line in _sample_lines(text)), text


def test_counter_rejects_negative_increments_because_counters_only_go_up() -> None:
    counter = Registry().counter("things_total", "Things.")

    with pytest.raises(ValueError, match="negative"):
        counter.inc(-1)


def test_labels_must_match_the_declared_names() -> None:
    counter = Registry().counter("things_total", "Things.", ("kind",))

    with pytest.raises(ValueError, match="labels"):
        counter.inc(other="x")
    with pytest.raises(ValueError, match="labels"):
        counter.inc()


def test_label_values_are_escaped_so_a_hostile_value_cannot_forge_samples() -> None:
    registry = Registry()
    counter = registry.counter("evil_total", "Escaping.", ("v",))

    counter.inc(v='a"b\\c\nfake_metric 99')

    text = registry.render()
    assert 'v="a\\"b\\\\c\\nfake_metric 99"' in text
    assert "\nfake_metric 99" not in text
    assert all(_SAMPLE.match(line) for line in _sample_lines(text)), text


def test_gauge_can_be_set_up_and_down() -> None:
    registry = Registry()
    gauge = registry.gauge("dependency_up", "1 if the dependency answers.", ("dependency",))

    gauge.set(1, dependency="database")
    gauge.set(0, dependency="broker")
    gauge.set(0, dependency="database")

    text = registry.render()
    assert "# TYPE dependency_up gauge" in text
    assert 'dependency_up{dependency="database"} 0' in text
    assert 'dependency_up{dependency="broker"} 0' in text


def test_histogram_is_cumulative_with_inf_bucket_sum_and_count() -> None:
    registry = Registry()
    histogram = registry.histogram("latency_seconds", "Latency.", (0.1, 0.5, 1.0), ("route",))

    for value in (0.05, 0.3, 0.3, 2.0):
        histogram.observe(value, route="/x")

    text = registry.render()
    assert "# TYPE latency_seconds histogram" in text
    assert 'latency_seconds_bucket{route="/x",le="0.1"} 1' in text
    assert 'latency_seconds_bucket{route="/x",le="0.5"} 3' in text
    assert 'latency_seconds_bucket{route="/x",le="1.0"} 3' in text
    assert 'latency_seconds_bucket{route="/x",le="+Inf"} 4' in text
    assert 'latency_seconds_count{route="/x"} 4' in text
    assert 'latency_seconds_sum{route="/x"} 2.65' in text
    assert all(_SAMPLE.match(line) for line in _sample_lines(text)), text


def test_histogram_buckets_must_be_strictly_increasing() -> None:
    with pytest.raises(ValueError, match="increasing"):
        Registry().histogram("h", "H.", (0.5, 0.1))


def test_series_cardinality_is_capped_and_overflow_is_counted_not_stored() -> None:
    registry = Registry(max_series=3)
    counter = registry.counter("by_id_total", "Per id.", ("id",))

    for i in range(10):
        counter.inc(id=str(i))

    text = registry.render()
    assert len([line for line in _sample_lines(text) if line.startswith("by_id_total{")]) == 3
    assert "metrics_series_dropped_total 7" in text


def test_metric_names_are_validated_and_unique() -> None:
    registry = Registry()
    registry.counter("ok_total", "Ok.")

    with pytest.raises(ValueError, match="name"):
        registry.counter("1bad", "Bad.")
    with pytest.raises(ValueError, match="label"):
        registry.counter("x_total", "X.", ("bad-label",))
    with pytest.raises(ValueError, match="already"):
        registry.gauge("ok_total", "Dup.")


def test_concurrent_increments_do_not_lose_updates() -> None:
    registry = Registry()
    counter = registry.counter("race_total", "Race.")

    def work() -> None:
        for _ in range(2000):
            counter.inc()

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert "race_total 16000" in registry.render()


def test_collectors_run_at_scrape_time() -> None:
    registry = Registry()
    gauge = registry.gauge("age_seconds", "Age.")
    ticks = iter([5, 9])
    registry.add_collector(lambda: gauge.set(next(ticks)))

    assert "age_seconds 5" in registry.render()
    assert "age_seconds 9" in registry.render()


def test_a_failing_collector_does_not_break_the_scrape() -> None:
    registry = Registry()
    registry.counter("alive_total", "Alive.").inc()

    def boom() -> None:
        raise RuntimeError("secret detail")

    registry.add_collector(boom)

    text = registry.render()
    assert "alive_total 1" in text
    assert "metrics_collector_errors_total 1" in text
    assert "secret detail" not in text


def test_bucket_bounds_use_the_float_notation_prometheus_clients_use() -> None:
    """Achado ao vivo: o Prometheus rotula `le` como "5.0"; escrever "5" faria `le="5.0"` nunca casar."""
    registry = Registry()
    histogram = registry.histogram("h_seconds", "H.", (0.5, 5.0, 60.0))
    histogram.observe(1.0)

    text = registry.render()

    assert 'h_seconds_bucket{le="5.0"} 1' in text
    assert 'h_seconds_bucket{le="60.0"} 1' in text
    assert 'h_seconds_bucket{le="0.5"} 0' in text
