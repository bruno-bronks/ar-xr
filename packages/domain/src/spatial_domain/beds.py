"""Estado operacional do leito (SPEC-010 / Z-006 / REQ-HACC-005). Funcao pura e deterministica.

Somente sinalizadores OPERACIONAIS (alarme de saida, bomba de infusao, chamada, limpeza). Nenhuma
interpretacao clinica, sinal vital ou identificacao de pessoa: o modelo nao tem esses campos (D-028).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

OFFLINE_AFTER = timedelta(seconds=30)  # D-029


class BedStatus(StrEnum):
    NORMAL = "NORMAL"
    ATTENTION = "ATTENTION"
    ALERT = "ALERT"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


def _require_aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class BedFlags:
    bed_exit_alarm: bool = False
    iv_pump_alarm: bool = False
    call_button: bool = False
    cleaning_due: bool = False


@dataclass(frozen=True)
class BedReading:
    occupied: bool
    flags: BedFlags
    observed_at: datetime | None  # None = nenhuma leitura recebida

    def __post_init__(self) -> None:
        if self.observed_at is not None:
            _require_aware("observed_at", self.observed_at)


@dataclass(frozen=True)
class BedAlert:
    severity: str  # ALERT | ATTENTION | OFFLINE
    rule: str


def _is_stale(reading: BedReading, now: datetime, offline_after: timedelta) -> bool:
    assert reading.observed_at is not None  # noqa: S101 - chamado so com leitura
    age = max(now - reading.observed_at, timedelta(0))  # relogio adiantado => idade 0
    return age > offline_after


def _check(now: datetime, offline_after: timedelta) -> None:
    _require_aware("now", now)
    if offline_after <= timedelta(0):
        raise ValueError("offline_after must be positive")


def _effective_alert_flags(reading: BedReading) -> list[BedAlert]:
    f = reading.flags
    alerts: list[BedAlert] = []
    if f.bed_exit_alarm and reading.occupied:  # saida de leito vazio nao e alarme
        alerts.append(BedAlert("ALERT", "bed_exit_alarm"))
    if f.iv_pump_alarm:
        alerts.append(BedAlert("ALERT", "iv_pump_alarm"))
    if f.call_button:
        alerts.append(BedAlert("ATTENTION", "call_button"))
    if f.cleaning_due:
        alerts.append(BedAlert("ATTENTION", "cleaning_due"))
    return alerts


def evaluate_bed(
    reading: BedReading, now: datetime, offline_after: timedelta = OFFLINE_AFTER
) -> BedStatus:
    """sem leitura -> UNKNOWN; leitura velha -> OFFLINE (precedencia); alarme -> ALERT;
    chamada/limpeza -> ATTENTION; senao NORMAL. Limite estrito (`>`), como D-001."""
    _check(now, offline_after)
    if reading.observed_at is None:
        return BedStatus.UNKNOWN
    if _is_stale(reading, now, offline_after):
        return BedStatus.OFFLINE
    severities = {a.severity for a in _effective_alert_flags(reading)}
    if "ALERT" in severities:
        return BedStatus.ALERT
    if "ATTENTION" in severities:
        return BedStatus.ATTENTION
    return BedStatus.NORMAL


def bed_alerts(
    reading: BedReading, now: datetime, offline_after: timedelta = OFFLINE_AFTER
) -> list[BedAlert]:
    """Alertas por REGRA (nao sao hipoteses de IA nem recomendacoes clinicas)."""
    _check(now, offline_after)
    if reading.observed_at is None:
        return []
    if _is_stale(reading, now, offline_after):
        return [BedAlert("OFFLINE", "offline")]
    return _effective_alert_flags(reading)


_SEVERITY_ORDER = {
    BedStatus.ALERT: 4,
    BedStatus.OFFLINE: 3,
    BedStatus.UNKNOWN: 2,
    BedStatus.ATTENTION: 1,
    BedStatus.NORMAL: 0,
}


def worst_status(statuses: Iterable[BedStatus]) -> BedStatus:
    """Pior estado de um conjunto. Vazio => UNKNOWN (ala sem leitos nunca e 'normal')."""
    return max(statuses, key=_SEVERITY_ORDER.__getitem__, default=BedStatus.UNKNOWN)
