"""Avaliacao de estado do equipamento (SPEC-002 / Z-002 / REQ-MNT-002).

Modelo executavel da especificacao: funcao pura, total e deterministica.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class Status(StrEnum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


class Quality(StrEnum):
    GOOD = "GOOD"
    BAD = "BAD"


def _require_finite(name: str, value: float) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class Threshold:
    """Limiares de um sensor: `warn <= crit` (Z: Threshold)."""

    warn: float
    crit: float

    def __post_init__(self) -> None:
        _require_finite("warn", self.warn)
        _require_finite("crit", self.crit)
        if self.warn > self.crit:
            raise ValueError(f"warn ({self.warn}) must be <= crit ({self.crit})")


@dataclass(frozen=True)
class Reading:
    """Ultima leitura de um sensor (Z: Reading)."""

    value: float
    observed_at: datetime
    quality: Quality

    def __post_init__(self) -> None:
        _require_finite("value", self.value)
        _require_aware("observed_at", self.observed_at)


def evaluate_status(
    profile: Mapping[str, Threshold],
    latest: Mapping[str, Reading],
    now: datetime,
    offline_after: timedelta,
) -> Status:
    """Estado do equipamento. Precedencia (D-001, D-002, D-003, D-006):

    sem leitura -> UNKNOWN; equipamento mudo -> OFFLINE; alarme com leitura valida
    (GOOD e fresca) -> CRITICAL/WARNING; cobertura completa e valida -> NORMAL; senao UNKNOWN.
    Um limiar e excedido apenas com `valor > limite`.
    """
    _require_aware("now", now)
    if offline_after <= timedelta(0):
        raise ValueError("offline_after must be positive")
    unknown = set(latest) - set(profile)
    if unknown:
        raise ValueError(f"readings without profile: {sorted(unknown)}")

    if not latest:
        return Status.UNKNOWN

    def age(reading: Reading) -> timedelta:
        return max(now - reading.observed_at, timedelta(0))  # relogio adiantado => idade 0

    if min(age(r) for r in latest.values()) > offline_after:
        return Status.OFFLINE

    valid = {
        sensor: reading
        for sensor, reading in latest.items()
        if reading.quality is Quality.GOOD and age(reading) <= offline_after
    }
    if any(r.value > profile[s].crit for s, r in valid.items()):
        return Status.CRITICAL
    if any(r.value > profile[s].warn for s, r in valid.items()):
        return Status.WARNING
    if set(valid) == set(profile):
        return Status.NORMAL
    return Status.UNKNOWN
