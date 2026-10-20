"""Estatistica da comparacao (SPEC-011, REQ-CV-003): intervalo de Wilson e McNemar exato."""

import math
from dataclasses import dataclass


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson (95 % por padrao) para uma proporcao; (0, 1) se total == 0."""
    if total < 0 or not 0 <= successes <= total:
        raise ValueError("require 0 <= successes <= total")
    if total == 0:
        return (0.0, 1.0)
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """p-valor bilateral exato do teste de McNemar (binomial com p = 0,5) sobre os discordantes."""
    if only_a < 0 or only_b < 0:
        raise ValueError("counts must be non-negative")
    n = only_a + only_b
    if n == 0:
        return 1.0
    k = min(only_a, only_b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return float(min(1.0, 2 * tail))


@dataclass(frozen=True)
class Rate:
    successes: int
    total: int

    @property
    def value(self) -> float:
        return self.successes / self.total if self.total else float("nan")

    @property
    def interval(self) -> tuple[float, float]:
        return wilson_interval(self.successes, self.total)

    def text(self) -> str:
        if not self.total:
            return "—"
        lo, hi = self.interval
        return f"{self.value:.0%} ({self.successes}/{self.total}; IC95 {lo:.0%} a {hi:.0%})"


def paired_verdict(only_a: int, only_b: int, name_a: str, name_b: str, alpha: float = 0.05) -> str:
    """Frase honesta sobre a diferenca pareada: so afirma superioridade com p < alpha."""
    p = mcnemar_exact(only_a, only_b)
    if p >= alpha:
        return f"sem diferença detectável entre {name_a} e {name_b} (discordantes {only_a}/{only_b}; p={p:.3f})"
    better = name_a if only_a > only_b else name_b
    return f"{better} é melhor (discordantes {only_a}/{only_b}; McNemar exato p={p:.3g})"
