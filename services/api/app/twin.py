"""Twin e alertas derivados (SPEC-006, D-010): funcoes puras sobre o modelo de dominio (SPEC-002)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from spatial_domain.status import Quality, Reading, Status, Threshold, evaluate_status
from spatial_storage.repository import EquipmentRecord, SensorProfile, StoredReading


@dataclass(frozen=True)
class SensorView:
    sensor_type: str
    unit: str
    value: float | None
    observed_at: datetime | None
    quality: Quality | None
    warn: float
    crit: float
    valid: bool


@dataclass(frozen=True)
class TwinView:
    equipment_id: str
    status: Status
    evaluated_at: datetime
    offline_after: timedelta
    sensors: list[SensorView]


@dataclass(frozen=True)
class AlertView:
    equipment_id: str
    severity: str  # WARNING | CRITICAL | OFFLINE
    rule: str
    raised_at: datetime
    sensor_type: str | None = None
    value: float | None = None
    limit: float | None = None


def _is_valid(reading: StoredReading, now: datetime, offline_after: timedelta) -> bool:
    age = max(now - reading.observed_at, timedelta(0))
    return reading.quality is Quality.GOOD and age <= offline_after


def build_twin(
    equipment: EquipmentRecord,
    profile: dict[str, SensorProfile],
    readings: list[StoredReading],
    now: datetime,
) -> TwinView:
    by_sensor = {r.sensor_type: r for r in readings}
    status = evaluate_status(
        {s: Threshold(p.warn, p.crit) for s, p in profile.items()},
        {s: Reading(r.value, r.observed_at, r.quality) for s, r in by_sensor.items()},
        now,
        equipment.offline_after,
    )
    sensors = []
    for sensor_type in sorted(profile):
        p, r = profile[sensor_type], by_sensor.get(sensor_type)
        sensors.append(
            SensorView(
                sensor_type=sensor_type,
                unit=p.unit,
                value=r.value if r else None,
                observed_at=r.observed_at.astimezone(UTC) if r else None,
                quality=r.quality if r else None,
                warn=p.warn,
                crit=p.crit,
                valid=bool(r and _is_valid(r, now, equipment.offline_after)),
            )
        )
    return TwinView(equipment.id, status, now.astimezone(UTC), equipment.offline_after, sensors)


def derive_alerts(twin: TwinView) -> list[AlertView]:
    """Alertas por REGRA (deterministicos); nao sao hipoteses de IA."""
    if twin.status is Status.OFFLINE:
        seen = max(s.observed_at for s in twin.sensors if s.observed_at is not None)
        return [AlertView(twin.equipment_id, "OFFLINE", "offline", seen + twin.offline_after)]
    alerts: list[AlertView] = []
    for s in twin.sensors:
        if not s.valid or s.value is None or s.observed_at is None:
            continue
        if s.value > s.crit:
            alerts.append(
                AlertView(
                    twin.equipment_id,
                    "CRITICAL",
                    f"{s.sensor_type}>crit",
                    s.observed_at,
                    s.sensor_type,
                    s.value,
                    s.crit,
                )
            )
        elif s.value > s.warn:
            alerts.append(
                AlertView(
                    twin.equipment_id,
                    "WARNING",
                    f"{s.sensor_type}>warn",
                    s.observed_at,
                    s.sensor_type,
                    s.value,
                    s.warn,
                )
            )
    return alerts
