"""Repositorio PostgreSQL (SQLAlchemy Core). Idempotencia via `ON CONFLICT` (SPEC-005, Z-004)."""

from datetime import datetime, timedelta

from spatial_domain.status import Quality
from spatial_domain.telemetry import TelemetryEvent
from sqlalchemy import Engine, Row, delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import DataError, IntegrityError

from spatial_storage import models as m
from spatial_storage.repository import (
    EquipmentRecord,
    RecordOutcome,
    SensorProfile,
    StoredReading,
    UnknownEquipmentError,
)
from spatial_storage.seed_data import SeedData


def _equipment(row: Row[tuple[object, ...]]) -> EquipmentRecord:
    r = row._mapping
    return EquipmentRecord(
        id=r["id"],
        org_id=r["org_id"],
        name=r["name"],
        type=r["type"],
        location=r["location"],
        marker_id=r["marker_id"],
        offline_after=timedelta(seconds=r["offline_after_seconds"]),
        last_seen_at=r["last_seen_at"],
    )


class PostgresRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_equipment(self, org_id: str) -> list[EquipmentRecord]:
        stmt = select(m.equipment).where(m.equipment.c.org_id == org_id).order_by(m.equipment.c.id)
        with self._engine.connect() as conn:
            return [_equipment(row) for row in conn.execute(stmt)]

    def get_equipment(self, org_id: str, equipment_id: str) -> EquipmentRecord | None:
        stmt = select(m.equipment).where(
            m.equipment.c.id == equipment_id, m.equipment.c.org_id == org_id
        )
        return self._one(stmt)

    def get_equipment_by_marker(self, org_id: str, marker_id: str) -> EquipmentRecord | None:
        if "\x00" in marker_id:  # PostgreSQL nao aceita NUL em texto
            return None
        stmt = select(m.equipment).where(
            m.equipment.c.marker_id == marker_id, m.equipment.c.org_id == org_id
        )
        try:
            return self._one(stmt)
        except DataError:
            return None

    def _one(self, stmt: object) -> EquipmentRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(stmt).first()  # type: ignore[call-overload]
        return _equipment(row) if row is not None else None

    def latest_readings(self, org_id: str, equipment_id: str) -> list[StoredReading]:
        stmt = (
            select(m.telemetry_latest)
            .join(m.equipment, m.equipment.c.id == m.telemetry_latest.c.equipment_id)
            .where(m.equipment.c.id == equipment_id, m.equipment.c.org_id == org_id)
            .order_by(m.telemetry_latest.c.sensor_type)
        )
        with self._engine.connect() as conn:
            return [
                StoredReading(
                    equipment_id=r["equipment_id"],
                    sensor_type=r["sensor_type"],
                    value=r["value"],
                    unit=r["unit"],
                    observed_at=r["observed_at"],
                    received_at=r["received_at"],
                    quality=Quality(r["quality"]),
                    source=r["source"],
                    event_id=r["event_id"],
                )
                for r in (row._mapping for row in conn.execute(stmt))
            ]

    def get_profile(self, equipment_id: str) -> dict[str, SensorProfile] | None:
        with self._engine.connect() as conn:
            exists = conn.execute(
                select(m.equipment.c.id).where(m.equipment.c.id == equipment_id)
            ).first()
            if exists is None:
                return None
            rows = conn.execute(
                select(m.threshold_profiles).where(
                    m.threshold_profiles.c.equipment_id == equipment_id
                )
            )
            return {
                r["sensor_type"]: SensorProfile(r["sensor_type"], r["unit"], r["warn"], r["crit"])
                for r in (row._mapping for row in rows)
            }

    def record(self, event: TelemetryEvent, received_at: datetime) -> RecordOutcome:
        values = {
            "equipment_id": event.equipment_id,
            "sensor_type": event.sensor_type,
            "value": event.value,
            "unit": event.unit,
            "observed_at": event.observed_at,
            "received_at": received_at,
            "quality": event.quality.value,
        }
        try:
            with self._engine.begin() as conn:
                inserted = conn.execute(
                    pg_insert(m.telemetry_events)
                    .values(source=event.source, event_id=event.event_id, **values)
                    .on_conflict_do_nothing(index_elements=["source", "event_id"])
                    .returning(m.telemetry_events.c.event_id)
                )
                if inserted.first() is None:
                    return RecordOutcome.DUPLICATE

                upsert = pg_insert(m.telemetry_latest).values(
                    source=event.source, event_id=event.event_id, **values
                )
                advanced = conn.execute(
                    upsert.on_conflict_do_update(
                        index_elements=["equipment_id", "sensor_type"],
                        set_={
                            "source": upsert.excluded.source,
                            "event_id": upsert.excluded.event_id,
                            "value": upsert.excluded.value,
                            "unit": upsert.excluded.unit,
                            "observed_at": upsert.excluded.observed_at,
                            "received_at": upsert.excluded.received_at,
                            "quality": upsert.excluded.quality,
                        },
                        where=m.telemetry_latest.c.observed_at <= upsert.excluded.observed_at,
                    ).returning(m.telemetry_latest.c.event_id)
                )
                conn.execute(
                    update(m.equipment)
                    .where(m.equipment.c.id == event.equipment_id)
                    .values(
                        last_seen_at=func.greatest(
                            func.coalesce(m.equipment.c.last_seen_at, event.observed_at),
                            event.observed_at,
                        )
                    )
                )
                return (
                    RecordOutcome.ACCEPTED
                    if advanced.first() is not None
                    else RecordOutcome.ACCEPTED_HISTORY_ONLY
                )
        except IntegrityError as exc:
            # FK (equipment_id, sensor_type) -> threshold_profiles: nao cadastrado
            raise UnknownEquipmentError(f"{event.equipment_id}/{event.sensor_type}") from exc

    def event_count(self, equipment_id: str) -> int:
        stmt = select(func.count()).where(m.telemetry_events.c.equipment_id == equipment_id)
        with self._engine.connect() as conn:
            return int(conn.execute(stmt).scalar_one())


def apply_seed(engine: Engine, seed: SeedData) -> None:
    """Upsert idempotente do seed de desenvolvimento. Nao toca em telemetria."""
    with engine.begin() as conn:
        for org_id, name in seed.organizations:
            conn.execute(
                pg_insert(m.organizations)
                .values(id=org_id, name=name)
                .on_conflict_do_update(index_elements=["id"], set_={"name": name})
            )
        for eq in seed.equipment:
            fields = {
                "org_id": eq.org_id,
                "name": eq.name,
                "type": eq.type,
                "location": eq.location,
                "marker_id": eq.marker_id,
                "offline_after_seconds": eq.offline_after_seconds,
            }
            conn.execute(
                pg_insert(m.equipment)
                .values(id=eq.id, **fields)
                .on_conflict_do_update(index_elements=["id"], set_=fields)
            )
            for p in eq.profile:
                pfields = {"unit": p.unit, "warn": p.warn, "crit": p.crit}
                conn.execute(
                    pg_insert(m.threshold_profiles)
                    .values(equipment_id=eq.id, sensor_type=p.sensor_type, **pfields)
                    .on_conflict_do_update(
                        index_elements=["equipment_id", "sensor_type"], set_=pfields
                    )
                )


def truncate_all(engine: Engine) -> None:
    """Uso exclusivo de testes: limpa todas as tabelas de dados."""
    with engine.begin() as conn:
        conn.execute(delete(m.telemetry_latest))
        conn.execute(delete(m.telemetry_events))
        conn.execute(delete(m.threshold_profiles))
        conn.execute(delete(m.equipment))
        conn.execute(delete(m.organizations))
        conn.execute(text("SELECT 1"))
