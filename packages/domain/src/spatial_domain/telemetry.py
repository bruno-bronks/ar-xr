"""Parser estrito de eventos de telemetria v1 (SPEC-004/SPEC-005; REQ-MNT-003, REQ-MNT-004).

Mesmas regras do JSON Schema `packages/contracts/telemetry-event.v1.schema.json`; um teste
diferencial (Hypothesis) garante a concordancia. Funcao pura: sem I/O.
"""

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, NoReturn

from spatial_domain.status import Quality

SCHEMA_VERSION = 1
SENSOR_TYPES = frozenset({"temperature", "vibration"})
FUTURE_TOLERANCE = timedelta(minutes=5)  # D-007

_ID = re.compile(r"[A-Za-z0-9._:-]+")
_TOPIC = re.compile(r"spatial/v1/equipment/([A-Za-z0-9._:-]{1,64})/telemetry")
_RFC3339 = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})",
    re.IGNORECASE,
)
_REQUIRED = frozenset(
    {
        "schema_version",
        "event_id",
        "source",
        "equipment_id",
        "sensor_type",
        "value",
        "unit",
        "observed_at",
        "quality",
    }
)


class RejectReason(StrEnum):
    INVALID_ENCODING = "INVALID_ENCODING"
    INVALID_JSON = "INVALID_JSON"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    TOPIC_MISMATCH = "TOPIC_MISMATCH"
    UNKNOWN_EQUIPMENT = "UNKNOWN_EQUIPMENT"
    UNKNOWN_SENSOR = "UNKNOWN_SENSOR"
    TIMESTAMP_IN_FUTURE = "TIMESTAMP_IN_FUTURE"


class TelemetryRejected(Exception):
    def __init__(self, reason: RejectReason, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else str(reason))
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class TelemetryEvent:
    event_id: str
    source: str
    equipment_id: str
    sensor_type: str
    value: float
    unit: str
    observed_at: datetime  # sempre UTC
    quality: Quality


def equipment_id_from_topic(topic: str) -> str | None:
    match = _TOPIC.fullmatch(topic)
    return match.group(1) if match else None


def _violation(detail: str) -> NoReturn:
    raise TelemetryRejected(RejectReason.SCHEMA_VIOLATION, detail)


def _reject_constant(name: str) -> NoReturn:
    raise ValueError(f"non-finite constant {name}")


def _identifier(data: dict[str, Any], field: str, max_len: int) -> str:
    value = data[field]
    if not isinstance(value, str) or not (1 <= len(value) <= max_len) or not _ID.fullmatch(value):
        _violation(field)
    return value


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        _violation("observed_at")
    match = _RFC3339.fullmatch(value)
    if match is None:
        _violation("observed_at")
    year, month, day, hour, minute, second, fraction, zone = match.groups()
    try:
        if zone.upper() == "Z":
            offset = timedelta(0)
        else:
            sign = -1 if zone[0] == "-" else 1
            off_h, off_m = int(zone[1:3]), int(zone[4:6])
            if off_h > 23 or off_m > 59:
                _violation("observed_at")
            offset = sign * timedelta(hours=off_h, minutes=off_m)
        micro = int((fraction or ".0")[1:7].ljust(6, "0"))
        local = datetime(
            int(year), int(month), int(day), int(hour), int(minute), int(second), micro, tzinfo=UTC
        )
        return local - offset
    except (ValueError, OverflowError):
        _violation("observed_at")


def parse_payload(raw: bytes) -> TelemetryEvent:
    """Decodifica e valida o payload. Levanta somente `TelemetryRejected`."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TelemetryRejected(RejectReason.INVALID_ENCODING) from exc
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        raise TelemetryRejected(RejectReason.INVALID_JSON) from exc

    if not isinstance(data, dict):
        _violation("payload must be an object")
    keys = set(data)
    if keys != _REQUIRED:
        _violation(f"fields: missing={sorted(_REQUIRED - keys)} extra={sorted(keys - _REQUIRED)}")

    version = data["schema_version"]
    if type(version) not in (int, float) or version != SCHEMA_VERSION:
        _violation("schema_version")
    event_id = _identifier(data, "event_id", 128)
    source = _identifier(data, "source", 64)
    equipment_id = _identifier(data, "equipment_id", 64)

    sensor_type = data["sensor_type"]
    if not isinstance(sensor_type, str) or sensor_type not in SENSOR_TYPES:
        _violation("sensor_type")

    raw_value = data["value"]
    if type(raw_value) not in (int, float):
        _violation("value")
    try:
        value = float(raw_value)
    except OverflowError:
        _violation("value")
    if not math.isfinite(value):
        _violation("value")

    unit = data["unit"]
    if not isinstance(unit, str) or not (1 <= len(unit) <= 16):
        _violation("unit")

    quality_raw = data["quality"]
    if not isinstance(quality_raw, str) or quality_raw not in {q.value for q in Quality}:
        _violation("quality")

    return TelemetryEvent(
        event_id=event_id,
        source=source,
        equipment_id=equipment_id,
        sensor_type=sensor_type,
        value=value,
        unit=unit,
        observed_at=_parse_timestamp(data["observed_at"]),
        quality=Quality(quality_raw),
    )


def reject_future(
    event: TelemetryEvent, received_at: datetime, tolerance: timedelta = FUTURE_TOLERANCE
) -> None:
    """D-007: `observed_at` ate `tolerance` no futuro e aceito; alem disso e rejeitado."""
    if event.observed_at - received_at > tolerance:
        raise TelemetryRejected(RejectReason.TIMESTAMP_IN_FUTURE, str(event.observed_at))
