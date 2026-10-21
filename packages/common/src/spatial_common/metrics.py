"""Metricas no formato de texto Prometheus, sem dependencia externa (SPEC-012, REQ-OPS-005).

Decisoes (D-046):
- Os rotulos devem ser de BAIXA cardinalidade e sem dados pessoais: rota (modelo, nao a URL),
  classe de status, desfecho. Cada metrica tem teto de series; o excedente e descartado e contado
  em `metrics_series_dropped_total`, em vez de crescer sem limite na memoria.
- Valores de rotulo sao escapados: um valor hostil nao forja amostras.
- Um coletor que falha nao derruba a coleta; so incrementa `metrics_collector_errors_total` (a
  mensagem da excecao nunca sai).
"""

import itertools
import logging
import re
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("spatial_common.metrics")

_NAME = re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:]*")
_LABEL = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


def _number(value: float) -> str:
    return format(value, ".10g")


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _escape_help(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n")


def _labelled(names: tuple[str, ...], values: tuple[str, ...], extra: str = "") -> str:
    pairs = [f'{n}="{_escape_label(v)}"' for n, v in zip(names, values, strict=True)]
    if extra:
        pairs.append(extra)
    return "{" + ",".join(pairs) + "}" if pairs else ""


class _Metric:
    kind = ""

    def __init__(
        self, registry: "Registry", name: str, help_text: str, labels: tuple[str, ...]
    ) -> None:
        if not _NAME.fullmatch(name):
            raise ValueError(f"invalid metric name: {name!r}")
        for label in labels:
            if not _LABEL.fullmatch(label) or label == "le":
                raise ValueError(f"invalid label name: {label!r}")
        self._registry = registry
        self.name = name
        self.help = help_text
        self.labels = labels

    def _key(self, labels: dict[str, str]) -> tuple[str, ...]:
        if set(labels) != set(self.labels):
            raise ValueError(f"labels must be exactly {list(self.labels)}")
        return tuple(labels[name] for name in self.labels)

    def _lines(self) -> list[str]:  # pragma: no cover - implementado nas subclasses
        raise NotImplementedError


class Counter(_Metric):
    kind = "counter"

    def __init__(self, registry: "Registry", name: str, help_text: str, labels: tuple[str, ...]):
        super().__init__(registry, name, help_text, labels)
        self._values: dict[tuple[str, ...], float] = {}

    def inc(self, amount: float = 1, **labels: str) -> None:
        if amount < 0:
            raise ValueError("a counter cannot take a negative increment")
        key = self._key(labels)
        with self._registry.lock:
            if key not in self._values and not self._registry.admit(len(self._values)):
                return
            self._values[key] = self._values.get(key, 0.0) + amount

    def _lines(self) -> list[str]:
        return [
            f"{self.name}{_labelled(self.labels, key)} {_number(value)}"
            for key, value in self._values.items()
        ]


class Gauge(_Metric):
    kind = "gauge"

    def __init__(self, registry: "Registry", name: str, help_text: str, labels: tuple[str, ...]):
        super().__init__(registry, name, help_text, labels)
        self._values: dict[tuple[str, ...], float] = {}

    def set(self, value: float, **labels: str) -> None:
        key = self._key(labels)
        with self._registry.lock:
            if key not in self._values and not self._registry.admit(len(self._values)):
                return
            self._values[key] = float(value)

    def _lines(self) -> list[str]:
        return [
            f"{self.name}{_labelled(self.labels, key)} {_number(value)}"
            for key, value in self._values.items()
        ]


class Histogram(_Metric):
    kind = "histogram"

    def __init__(
        self,
        registry: "Registry",
        name: str,
        help_text: str,
        buckets: tuple[float, ...],
        labels: tuple[str, ...],
    ) -> None:
        super().__init__(registry, name, help_text, labels)
        if not buckets or any(b <= a for a, b in itertools.pairwise(buckets)):
            raise ValueError("histogram buckets must be strictly increasing")
        self.buckets = buckets
        # chave -> ([contagem por balde, nao cumulativa, +Inf no fim], soma)
        self._series: dict[tuple[str, ...], tuple[list[int], list[float]]] = {}

    def observe(self, value: float, **labels: str) -> None:
        key = self._key(labels)
        with self._registry.lock:
            if key not in self._series:
                if not self._registry.admit(len(self._series)):
                    return
                self._series[key] = ([0] * (len(self.buckets) + 1), [0.0])
            counts, total = self._series[key]
            index = next((i for i, upper in enumerate(self.buckets) if value <= upper), None)
            counts[len(self.buckets) if index is None else index] += 1
            total[0] += value

    def _lines(self) -> list[str]:
        lines: list[str] = []
        for key, (counts, total) in self._series.items():
            running = 0
            for upper, count in zip(self.buckets, counts, strict=False):
                running += count
                le = f'le="{float(upper)!r}"'
                lines.append(f"{self.name}_bucket{_labelled(self.labels, key, le)} {running}")
            running += counts[-1]
            inf = 'le="+Inf"'
            lines.append(f"{self.name}_bucket{_labelled(self.labels, key, inf)} {running}")
            lines.append(f"{self.name}_sum{_labelled(self.labels, key)} {_number(total[0])}")
            lines.append(f"{self.name}_count{_labelled(self.labels, key)} {running}")
        return lines


class Registry:
    def __init__(self, max_series: int = 200) -> None:
        self.lock = threading.RLock()
        self._max_series = max_series
        self._metrics: dict[str, _Metric] = {}
        self._collectors: list[Callable[[], Any]] = []
        self._dropped = 0
        self._collector_errors = 0

    def admit(self, current_series: int) -> bool:
        """Chamado COM o lock: decide se uma nova serie cabe sob o teto da metrica."""
        if current_series >= self._max_series:
            self._dropped += 1
            return False
        return True

    def _register(self, metric: _Metric) -> None:
        with self.lock:
            if metric.name in self._metrics:
                raise ValueError(f"metric already registered: {metric.name}")
            self._metrics[metric.name] = metric

    def counter(self, name: str, help_text: str, labels: tuple[str, ...] = ()) -> Counter:
        metric = Counter(self, name, help_text, labels)
        self._register(metric)
        return metric

    def gauge(self, name: str, help_text: str, labels: tuple[str, ...] = ()) -> Gauge:
        metric = Gauge(self, name, help_text, labels)
        self._register(metric)
        return metric

    def histogram(
        self,
        name: str,
        help_text: str,
        buckets: tuple[float, ...] = DEFAULT_BUCKETS,
        labels: tuple[str, ...] = (),
    ) -> Histogram:
        metric = Histogram(self, name, help_text, buckets, labels)
        self._register(metric)
        return metric

    def add_collector(self, collector: Callable[[], Any]) -> None:
        """Roda a cada coleta, antes da renderizacao (ex.: gauges calculados na hora)."""
        self._collectors.append(collector)

    def render(self) -> str:
        for collector in list(self._collectors):
            try:
                collector()
            except Exception as error:
                self._collector_errors += 1
                logger.warning(
                    "metrics collector failed", extra={"error_type": type(error).__name__}
                )
        out: list[str] = []
        with self.lock:
            for metric in self._metrics.values():
                out.append(f"# HELP {metric.name} {_escape_help(metric.help)}")
                out.append(f"# TYPE {metric.name} {metric.kind}")
                out.extend(metric._lines())
            out += [
                "# HELP metrics_series_dropped_total Series discarded by the per-metric cap.",
                "# TYPE metrics_series_dropped_total counter",
                f"metrics_series_dropped_total {self._dropped}",
                "# HELP metrics_collector_errors_total Scrape-time collectors that raised.",
                "# TYPE metrics_collector_errors_total counter",
                f"metrics_collector_errors_total {self._collector_errors}",
            ]
        return "\n".join(out) + "\n"
