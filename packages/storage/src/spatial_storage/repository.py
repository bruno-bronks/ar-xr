"""Porta de persistencia (ADR-0002). Duas implementacoes: Postgres (real) e memoria (dublê de teste)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from spatial_domain.status import Quality
from spatial_domain.telemetry import TelemetryEvent


class UnknownEquipmentError(Exception):
    """Equipamento (ou par equipamento/sensor) nao cadastrado."""


class RecordOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"  # novo evento; passou a ser a leitura vigente
    ACCEPTED_HISTORY_ONLY = "ACCEPTED_HISTORY_ONLY"  # novo evento atrasado; vigente preservada
    DUPLICATE = "DUPLICATE"  # (source, event_id) ja visto; nada mudou


@dataclass(frozen=True)
class EquipmentRecord:
    id: str
    org_id: str
    name: str
    type: str
    location: str
    marker_id: str | None
    offline_after: timedelta
    last_seen_at: datetime | None


@dataclass(frozen=True)
class SensorProfile:
    sensor_type: str
    unit: str
    warn: float
    crit: float


@dataclass(frozen=True)
class StoredReading:
    equipment_id: str
    sensor_type: str
    value: float
    unit: str
    observed_at: datetime
    received_at: datetime
    quality: Quality
    source: str
    event_id: str


class Repository(Protocol):
    # --- leitura (sempre filtrada por organizacao) ---
    def list_equipment(self, org_id: str) -> list[EquipmentRecord]: ...

    def get_equipment(self, org_id: str, equipment_id: str) -> EquipmentRecord | None: ...

    def get_equipment_by_marker(self, org_id: str, marker_id: str) -> EquipmentRecord | None: ...

    def latest_readings(self, org_id: str, equipment_id: str) -> list[StoredReading]: ...

    # --- uso interno do worker/twin (sem filtro de organizacao; o chamador ja autorizou) ---
    def get_profile(self, equipment_id: str) -> dict[str, SensorProfile] | None: ...

    def record(self, event: TelemetryEvent, received_at: datetime) -> RecordOutcome: ...

    def event_count(self, equipment_id: str) -> int: ...
