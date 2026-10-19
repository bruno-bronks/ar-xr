"""Esquema relacional (SQLAlchemy Core). A migracao `0001_initial` e escrita explicitamente e um teste
(`test_models_match_migrations`) garante que as duas descricoes nao divergem."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Double,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP

metadata = MetaData()

_FINITE = "value = value AND value > '-Infinity'::float8 AND value < 'Infinity'::float8"
_QUALITY = "quality IN ('GOOD', 'BAD')"


def _tz() -> TIMESTAMP:
    return TIMESTAMP(timezone=True)


organizations = Table(
    "organizations",
    metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
)

equipment = Table(
    "equipment",
    metadata,
    Column("id", Text, primary_key=True),
    Column("org_id", Text, ForeignKey("organizations.id"), nullable=False),
    Column("name", Text, nullable=False),
    Column("type", Text, nullable=False),
    Column("location", Text, nullable=False),
    Column("marker_id", Text, unique=True),
    Column("offline_after_seconds", Integer, nullable=False),
    Column("last_seen_at", _tz()),
    CheckConstraint("offline_after_seconds > 0", name="ck_equipment_offline_after_positive"),
)

threshold_profiles = Table(
    "threshold_profiles",
    metadata,
    Column("equipment_id", Text, ForeignKey("equipment.id"), nullable=False),
    Column("sensor_type", Text, nullable=False),
    Column("unit", Text, nullable=False),
    Column("warn", Double, nullable=False),
    Column("crit", Double, nullable=False),
    PrimaryKeyConstraint("equipment_id", "sensor_type"),
    CheckConstraint("warn <= crit", name="ck_threshold_warn_le_crit"),
)

_READING_COLUMNS = (
    Column("equipment_id", Text, nullable=False),
    Column("sensor_type", Text, nullable=False),
    Column("value", Double, nullable=False),
    Column("unit", Text, nullable=False),
    Column("observed_at", _tz(), nullable=False),
    Column("received_at", _tz(), nullable=False),
    Column("quality", Text, nullable=False),
)

telemetry_events = Table(
    "telemetry_events",
    metadata,
    Column("source", Text, nullable=False),
    Column("event_id", Text, nullable=False),
    *(c._copy() for c in _READING_COLUMNS),
    PrimaryKeyConstraint("source", "event_id"),
    ForeignKeyConstraint(
        ["equipment_id", "sensor_type"],
        ["threshold_profiles.equipment_id", "threshold_profiles.sensor_type"],
    ),
    CheckConstraint(_FINITE, name="ck_events_value_finite"),
    CheckConstraint(_QUALITY, name="ck_events_quality"),
    Index("ix_events_equipment_observed", "equipment_id", "observed_at"),
)

telemetry_latest = Table(
    "telemetry_latest",
    metadata,
    *(c._copy() for c in _READING_COLUMNS),
    Column("source", Text, nullable=False),
    Column("event_id", Text, nullable=False),
    PrimaryKeyConstraint("equipment_id", "sensor_type"),
    ForeignKeyConstraint(
        ["equipment_id", "sensor_type"],
        ["threshold_profiles.equipment_id", "threshold_profiles.sensor_type"],
    ),
    CheckConstraint(_FINITE, name="ck_latest_value_finite"),
    CheckConstraint(_QUALITY, name="ck_latest_quality"),
)
