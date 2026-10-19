"""Dublê em memoria do repositorio, para testes rapidos sem Docker.

NAO e usado em producao. A suite de contrato (`tests/unit/storage`) roda o mesmo conjunto de
testes contra esta classe e contra o `PostgresRepository` para garantir semantica identica.
"""

import threading
from dataclasses import replace
from datetime import datetime, timedelta

from spatial_domain.telemetry import TelemetryEvent

from spatial_storage.repository import (
    EquipmentRecord,
    RecordOutcome,
    SensorProfile,
    StoredReading,
    UnknownEquipmentError,
)
from spatial_storage.seed_data import SEED, SeedData


class InMemoryRepository:
    def __init__(self, seed: SeedData = SEED) -> None:
        self._lock = threading.Lock()
        self._equipment = {
            e.id: EquipmentRecord(
                id=e.id,
                org_id=e.org_id,
                name=e.name,
                type=e.type,
                location=e.location,
                marker_id=e.marker_id,
                offline_after=timedelta(seconds=e.offline_after_seconds),
                last_seen_at=None,
            )
            for e in seed.equipment
        }
        self._profiles = {e.id: {p.sensor_type: p for p in e.profile} for e in seed.equipment}
        self._events: dict[tuple[str, str], StoredReading] = {}
        self._latest: dict[tuple[str, str], StoredReading] = {}

    def list_equipment(self, org_id: str) -> list[EquipmentRecord]:
        with self._lock:
            return sorted(
                (e for e in self._equipment.values() if e.org_id == org_id), key=lambda e: e.id
            )

    def get_equipment(self, org_id: str, equipment_id: str) -> EquipmentRecord | None:
        with self._lock:
            found = self._equipment.get(equipment_id)
            return found if found is not None and found.org_id == org_id else None

    def get_equipment_by_marker(self, org_id: str, marker_id: str) -> EquipmentRecord | None:
        with self._lock:
            for equipment in self._equipment.values():
                if equipment.marker_id == marker_id and equipment.org_id == org_id:
                    return equipment
            return None

    def latest_readings(self, org_id: str, equipment_id: str) -> list[StoredReading]:
        with self._lock:
            equipment = self._equipment.get(equipment_id)
            if equipment is None or equipment.org_id != org_id:
                return []
            return sorted(
                (r for (eq, _), r in self._latest.items() if eq == equipment_id),
                key=lambda r: r.sensor_type,
            )

    def get_profile(self, equipment_id: str) -> dict[str, SensorProfile] | None:
        with self._lock:
            profile = self._profiles.get(equipment_id)
            return dict(profile) if profile is not None else None

    def record(self, event: TelemetryEvent, received_at: datetime) -> RecordOutcome:
        with self._lock:
            if event.sensor_type not in self._profiles.get(event.equipment_id, {}):
                raise UnknownEquipmentError(f"{event.equipment_id}/{event.sensor_type}")
            key = (event.source, event.event_id)
            if key in self._events:
                return RecordOutcome.DUPLICATE
            reading = StoredReading(
                equipment_id=event.equipment_id,
                sensor_type=event.sensor_type,
                value=event.value,
                unit=event.unit,
                observed_at=event.observed_at,
                received_at=received_at,
                quality=event.quality,
                source=event.source,
                event_id=event.event_id,
            )
            self._events[key] = reading
            equipment = self._equipment[event.equipment_id]
            if equipment.last_seen_at is None or event.observed_at > equipment.last_seen_at:
                self._equipment[event.equipment_id] = replace(
                    equipment, last_seen_at=event.observed_at
                )
            slot = (event.equipment_id, event.sensor_type)
            current = self._latest.get(slot)
            if current is None or event.observed_at >= current.observed_at:
                self._latest[slot] = reading
                return RecordOutcome.ACCEPTED
            return RecordOutcome.ACCEPTED_HISTORY_ONLY

    def event_count(self, equipment_id: str) -> int:
        with self._lock:
            return sum(1 for r in self._events.values() if r.equipment_id == equipment_id)
