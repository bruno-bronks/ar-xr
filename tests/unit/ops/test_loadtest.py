"""SPEC-012 · REQ-OPS-006: teste de carga controlado, calculo dos SLIs e conferencia com as metricas do servidor."""

import itertools
import threading

import pytest
from spatial_ops.loadtest import (
    Request,
    Sample,
    SloTarget,
    compare_with_server,
    evaluate,
    parse_prometheus,
    percentile,
    run_load,
)

# --- percentil (nearest-rank, sem interpolar: o numero reportado e uma medicao real) ----------------


def test_percentile_uses_nearest_rank() -> None:
    values = [float(v) for v in range(1, 101)]

    assert percentile(values, 0.50) == 50.0
    assert percentile(values, 0.95) == 95.0
    assert percentile(values, 0.99) == 99.0
    assert percentile(values, 1.0) == 100.0


def test_percentile_of_a_single_value_and_of_nothing() -> None:
    assert percentile([0.2], 0.99) == 0.2
    with pytest.raises(ValueError, match="empty"):
        percentile([], 0.5)


# --- SLIs ------------------------------------------------------------------------------------------


def _sample(status: int, latency: float, route: str = "/r") -> Sample:
    return Sample(route=route, status=status, latency_s=latency)


def test_availability_counts_only_5xx_as_failures() -> None:
    samples = [_sample(200, 0.01)] * 90 + [_sample(401, 0.01)] * 8 + [_sample(503, 0.01)] * 2

    report = evaluate(samples, SloTarget(), duration_s=10.0)

    assert report["total"] == 100
    assert report["status_class"] == {"2xx": 90, "4xx": 8, "5xx": 2}
    assert report["availability"] == pytest.approx(0.98)
    assert report["slo"]["availability"]["met"] is False  # 98 % < 99,5 %


def test_slo_is_met_when_errors_and_latency_are_within_the_budget() -> None:
    samples = [_sample(200, 0.02)] * 996 + [_sample(500, 0.02)] * 4  # 0,4 % de erro

    report = evaluate(samples, SloTarget(), duration_s=10.0)

    assert report["slo"]["availability"]["met"] is True
    assert report["slo"]["latency"]["met"] is True
    assert report["slo"]["all_met"] is True


def test_latency_slo_uses_the_fraction_under_the_threshold() -> None:
    samples = [_sample(200, 0.1)] * 90 + [_sample(200, 0.9)] * 10  # 90 % rapidas < 95 %

    report = evaluate(samples, SloTarget(), duration_s=10.0)

    assert report["slo"]["latency"]["fraction_fast"] == pytest.approx(0.9)
    assert report["slo"]["latency"]["met"] is False
    assert report["slo"]["all_met"] is False


def test_report_includes_percentiles_and_throughput() -> None:
    samples = [_sample(200, v / 1000) for v in range(1, 101)]

    report = evaluate(samples, SloTarget(), duration_s=5.0)

    assert report["latency_ms"]["p50"] == pytest.approx(50.0)
    assert report["latency_ms"]["p95"] == pytest.approx(95.0)
    assert report["latency_ms"]["max"] == pytest.approx(100.0)
    assert report["achieved_rps"] == pytest.approx(20.0)


def test_evaluate_refuses_to_report_on_no_data() -> None:
    with pytest.raises(ValueError, match="no samples"):
        evaluate([], SloTarget(), duration_s=1.0)


# --- gerador de carga ---------------------------------------------------------------------------------


class FakeClock:
    """Tempo simulado: `sleep` avanca o relogio, sem esperar de verdade."""

    def __init__(self) -> None:
        self.now = 0.0
        self.lock = threading.Lock()

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        with self.lock:
            self.now += max(seconds, 0.0)


def test_run_load_sends_at_the_target_rate_and_records_every_response() -> None:
    clock = FakeClock()
    sent: list[str] = []

    def send(path: str, token: str | None) -> int:
        sent.append(path)
        return 200

    mix = [Request("/a", "/a", "t", 1.0)]
    samples = run_load(
        send, mix, duration_s=2.0, rps=10.0, workers=1, seed=1, clock=clock, sleep=clock.sleep
    )

    assert 19 <= len(samples) <= 21  # 10 req/s por 2 s
    assert len(samples) == len(sent)
    assert {s.status for s in samples} == {200}


def test_run_load_follows_the_request_weights_deterministically() -> None:
    mix = [Request("heavy", "/heavy", None, 9.0), Request("light", "/light", None, 1.0)]

    def run() -> list[str]:
        clock = FakeClock()
        samples = run_load(
            lambda path, token: 200, mix, duration_s=20.0, rps=50.0, workers=1, seed=7,
            clock=clock, sleep=clock.sleep,
        )  # fmt: skip
        return [s.route for s in samples]

    first, second = run(), run()

    assert first == second  # mesma semente => mesma sequencia
    assert 0.85 <= first.count("heavy") / len(first) <= 0.95


def test_run_load_measures_latency_from_the_intended_send_time() -> None:
    """Se o servidor engasga, as requisicoes seguintes saem atrasadas e isso aparece na latencia
    (evita a 'omissao coordenada' que esconderia a cauda)."""
    clock = FakeClock()
    calls = itertools.count()

    def slow_first(path: str, token: str | None) -> int:
        if next(calls) == 0:
            clock.sleep(1.0)  # a 1a resposta demora 1 s; as proximas estavam agendadas para antes
        return 200

    samples = run_load(
        slow_first, [Request("/a", "/a", None, 1.0)], duration_s=1.0, rps=10.0, workers=1, seed=1,
        clock=clock, sleep=clock.sleep,
    )  # fmt: skip

    delayed = [s.latency_s for s in samples[1:] if s.latency_s > 0.05]
    assert samples[0].latency_s >= 1.0
    assert delayed, "as requisicoes atrasadas pelo engasgo deveriam ter latencia > 0"


def test_a_failing_transport_is_recorded_as_status_zero_not_raised() -> None:
    clock = FakeClock()

    def broken(path: str, token: str | None) -> int:
        raise OSError("connection refused")

    samples = run_load(
        broken, [Request("/a", "/a", None, 1.0)], duration_s=0.5, rps=10.0, workers=1, seed=1,
        clock=clock, sleep=clock.sleep,
    )  # fmt: skip

    assert samples
    assert {s.status for s in samples} == {0}
    assert evaluate(samples, SloTarget(), duration_s=0.5)["status_class"]["5xx"] == len(samples)


# --- conferencia com as metricas do servidor --------------------------------------------------------------

BEFORE = """\
# HELP http_requests_total HTTP requests handled.
# TYPE http_requests_total counter
http_requests_total{route="/api/v1/equipment",method="GET",status_class="2xx"} 10
http_requests_total{route="/health/live",method="GET",status_class="2xx"} 500
"""
AFTER = """\
http_requests_total{route="/api/v1/equipment",method="GET",status_class="2xx"} 15
http_requests_total{route="/api/v1/equipment",method="GET",status_class="4xx"} 2
http_requests_total{route="/health/live",method="GET",status_class="2xx"} 540
"""


def test_parse_prometheus_reads_names_labels_and_values() -> None:
    parsed = parse_prometheus(BEFORE)

    key = (
        "http_requests_total",
        (("method", "GET"), ("route", "/api/v1/equipment"), ("status_class", "2xx")),
    )
    assert parsed[key] == 10.0
    assert len(parsed) == 2  # comentarios ignorados


def test_parse_prometheus_handles_escaped_label_values() -> None:
    parsed = parse_prometheus('m{a="x\\"y\\\\z"} 3\n')

    assert parsed[("m", (("a", 'x"y\\z'),))] == 3.0


def test_compare_with_server_matches_the_deltas_per_route_and_status_class() -> None:
    samples = [_sample(200, 0.01, "/api/v1/equipment")] * 5 + [
        _sample(401, 0.01, "/api/v1/equipment")
    ] * 2

    mismatches = compare_with_server(samples, parse_prometheus(BEFORE), parse_prometheus(AFTER))

    assert (
        mismatches == {}
    )  # /health/live (healthcheck do Docker) nao faz parte da carga e e ignorado


def test_compare_with_server_reports_lost_or_extra_requests() -> None:
    samples = [_sample(200, 0.01, "/api/v1/equipment")] * 6  # cliente diz 6, servidor viu 5

    mismatches = compare_with_server(samples, parse_prometheus(BEFORE), parse_prometheus(AFTER))

    assert mismatches["/api/v1/equipment|2xx"] == {"client": 6, "server": 5}
    assert mismatches["/api/v1/equipment|4xx"] == {"client": 0, "server": 2}


def test_report_breaks_latency_down_by_route_to_locate_a_slow_endpoint() -> None:
    samples = [_sample(200, 0.01, "/fast")] * 10 + [_sample(200, 0.9, "/slow")] * 10

    report = evaluate(samples, SloTarget(), duration_s=1.0)

    assert report["per_route"]["/fast"]["p95_ms"] == pytest.approx(10.0)
    assert report["per_route"]["/slow"]["p95_ms"] == pytest.approx(900.0)
    assert report["per_route"]["/slow"]["count"] == 10
