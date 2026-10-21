"""Carga controlada e calculo dos SLIs (SPEC-012, REQ-OPS-006). So stdlib.

Carga em circuito ABERTO: cada worker envia em instantes agendados e mede a latencia a partir do instante
PRETENDIDO, nao do envio real; se o servidor engasga, as requisicoes seguintes saem atrasadas e isso
aparece na latencia (sem "omissao coordenada" escondendo a cauda). Falha de transporte vira status 0
(conta como indisponibilidade). A conferencia com `/metrics` compara contagens do cliente e do servidor.
"""

import math
import random
import re
import threading
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

Send = Callable[[str, str | None], int]
MetricKey = tuple[str, tuple[tuple[str, str], ...]]


@dataclass(frozen=True)
class Request:
    route: str  # modelo da rota como o servidor o rotula (para conferir com /metrics)
    path: str
    token: str | None
    weight: float


@dataclass(frozen=True)
class Sample:
    route: str
    status: int
    latency_s: float


@dataclass(frozen=True)
class SloTarget:
    availability: float = 0.995  # fracao de requisicoes sem 5xx
    latency_threshold_s: float = 0.5
    latency_ratio: float = 0.95  # fracao que precisa ficar abaixo do limiar


def percentile(values: Sequence[float], q: float) -> float:
    """Nearest-rank: o valor reportado e uma medicao real, sem interpolacao."""
    if not values:
        raise ValueError("empty sample set")
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def _status_class(status: int) -> str:
    return "5xx" if status == 0 else f"{status // 100}xx"


def _per_route(samples: Sequence[Sample]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[float]] = {}
    for sample in samples:
        grouped.setdefault(sample.route, []).append(sample.latency_s)
    return {
        route: {
            "count": len(values),
            "p50_ms": percentile(values, 0.50) * 1000,
            "p95_ms": percentile(values, 0.95) * 1000,
            "max_ms": max(values) * 1000,
        }
        for route, values in sorted(grouped.items())
    }


def evaluate(samples: Sequence[Sample], target: SloTarget, duration_s: float) -> dict[str, Any]:
    if not samples:
        raise ValueError("no samples to evaluate")
    total = len(samples)
    classes = Counter(_status_class(s.status) for s in samples)
    latencies = [s.latency_s for s in samples]
    failures = classes.get("5xx", 0)
    availability = 1 - failures / total
    fast = sum(1 for v in latencies if v <= target.latency_threshold_s) / total
    availability_met = availability >= target.availability
    latency_met = fast >= target.latency_ratio
    return {
        "total": total,
        "duration_s": duration_s,
        "achieved_rps": total / duration_s,
        "status_class": dict(sorted(classes.items())),
        "availability": availability,
        "latency_ms": {
            "p50": percentile(latencies, 0.50) * 1000,
            "p95": percentile(latencies, 0.95) * 1000,
            "p99": percentile(latencies, 0.99) * 1000,
            "max": max(latencies) * 1000,
        },
        "per_route": _per_route(samples),
        "slo": {
            "availability": {
                "target": target.availability,
                "value": availability,
                "met": availability_met,
            },
            "latency": {
                "threshold_s": target.latency_threshold_s,
                "target": target.latency_ratio,
                "fraction_fast": fast,
                "met": latency_met,
            },
            "all_met": availability_met and latency_met,
        },
    }


def run_load(
    send: Send,
    mix: Sequence[Request],
    *,
    duration_s: float,
    rps: float,
    workers: int,
    seed: int,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Sample]:
    if not mix or rps <= 0 or workers < 1 or duration_s <= 0:
        raise ValueError("invalid load profile")
    period = workers / rps
    weights = [request.weight for request in mix]
    started = clock()
    results: list[list[Sample]] = [[] for _ in range(workers)]

    def work(index: int) -> None:
        rng = random.Random(seed * 1000 + index)  # noqa: S311 - amostragem de carga, nao criptografia
        first = started + index * period / workers
        k = 0
        while (intended := first + k * period) < started + duration_s:
            wait = intended - clock()
            if wait > 0:
                sleep(wait)
            request = rng.choices(mix, weights)[0]
            try:
                status = send(request.path, request.token)
            except Exception:  # falha de transporte nao derruba a medicao
                status = 0
            results[index].append(Sample(request.route, status, clock() - intended))
            k += 1

    if workers == 1:
        work(0)
    else:
        threads = [threading.Thread(target=work, args=(i,)) for i in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    return [sample for per_worker in results for sample in per_worker]


# --- conferencia com /metrics -----------------------------------------------------------------------

_LINE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(.*)\})? (\S+)$")
_LABEL = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"')
_UNESCAPE = re.compile(r"\\(.)")


def _unescape(value: str) -> str:
    return _UNESCAPE.sub(lambda m: "\n" if m.group(1) == "n" else m.group(1), value)


def parse_prometheus(text: str) -> dict[MetricKey, float]:
    parsed: dict[MetricKey, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE.match(line)
        if match is None:
            continue
        name, raw_labels, raw_value = match.groups()
        labels = tuple(sorted((k, _unescape(v)) for k, v in _LABEL.findall(raw_labels or "")))
        try:
            parsed[(name, labels)] = float(raw_value)
        except ValueError:
            continue
    return parsed


def _server_counts(
    before: Mapping[MetricKey, float], after: Mapping[MetricKey, float]
) -> Counter[str]:
    deltas: Counter[str] = Counter()
    for (name, labels), value in after.items():
        if name != "http_requests_total":
            continue
        label_map = dict(labels)
        delta = value - before.get((name, labels), 0.0)
        deltas[f"{label_map['route']}|{label_map['status_class']}"] += round(delta)
    return deltas


def compare_with_server(
    samples: Sequence[Sample],
    before: Mapping[MetricKey, float],
    after: Mapping[MetricKey, float],
) -> dict[str, dict[str, int]]:
    """Diferencas entre o que o cliente enviou e o que o servidor contou, por rota e classe de status.

    So rotas exercitadas pela carga entram na conferencia (o healthcheck do Docker bate em
    `/health/live`, fora do mix). Falhas de transporte (status 0) nao chegaram ao servidor.
    """
    client = Counter(f"{s.route}|{_status_class(s.status)}" for s in samples if s.status != 0)
    routes = {s.route for s in samples}
    server = Counter(
        {k: v for k, v in _server_counts(before, after).items() if k.split("|")[0] in routes}
    )
    mismatches: dict[str, dict[str, int]] = {}
    for key in sorted(set(client) | set(server)):
        if client[key] != server[key]:
            mismatches[key] = {"client": client[key], "server": server[key]}
    return mismatches
