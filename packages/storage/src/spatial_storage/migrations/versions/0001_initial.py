"""initial schema: organizations, equipment, threshold_profiles, telemetry_events, telemetry_latest

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_FINITE = "value = value AND value > '-Infinity'::float8 AND value < 'Infinity'::float8"
_QUALITY = "quality IN ('GOOD', 'BAD')"
_PROFILE_FK = (
    ["equipment_id", "sensor_type"],
    ["threshold_profiles.equipment_id", "threshold_profiles.sensor_type"],
)


def _reading_columns() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("equipment_id", sa.Text, nullable=False),
        sa.Column("sensor_type", sa.Text, nullable=False),
        sa.Column("value", sa.Double, nullable=False),
        sa.Column("unit", sa.Text, nullable=False),
        sa.Column("observed_at", TIMESTAMP(timezone=True), nullable=False),
        sa.Column("received_at", TIMESTAMP(timezone=True), nullable=False),
        sa.Column("quality", sa.Text, nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
    )
    op.create_table(
        "equipment",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("org_id", sa.Text, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("location", sa.Text, nullable=False),
        sa.Column("marker_id", sa.Text, unique=True),
        sa.Column("offline_after_seconds", sa.Integer, nullable=False),
        sa.Column("last_seen_at", TIMESTAMP(timezone=True)),
        sa.CheckConstraint("offline_after_seconds > 0", name="ck_equipment_offline_after_positive"),
    )
    op.create_table(
        "threshold_profiles",
        sa.Column("equipment_id", sa.Text, sa.ForeignKey("equipment.id"), nullable=False),
        sa.Column("sensor_type", sa.Text, nullable=False),
        sa.Column("unit", sa.Text, nullable=False),
        sa.Column("warn", sa.Double, nullable=False),
        sa.Column("crit", sa.Double, nullable=False),
        sa.PrimaryKeyConstraint("equipment_id", "sensor_type"),
        sa.CheckConstraint("warn <= crit", name="ck_threshold_warn_le_crit"),
    )
    op.create_table(
        "telemetry_events",
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("event_id", sa.Text, nullable=False),
        *_reading_columns(),
        sa.PrimaryKeyConstraint("source", "event_id"),
        sa.ForeignKeyConstraint(*_PROFILE_FK),
        sa.CheckConstraint(_FINITE, name="ck_events_value_finite"),
        sa.CheckConstraint(_QUALITY, name="ck_events_quality"),
    )
    op.create_index(
        "ix_events_equipment_observed", "telemetry_events", ["equipment_id", "observed_at"]
    )
    op.create_table(
        "telemetry_latest",
        *_reading_columns(),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("event_id", sa.Text, nullable=False),
        sa.PrimaryKeyConstraint("equipment_id", "sensor_type"),
        sa.ForeignKeyConstraint(*_PROFILE_FK),
        sa.CheckConstraint(_FINITE, name="ck_latest_value_finite"),
        sa.CheckConstraint(_QUALITY, name="ck_latest_quality"),
    )


def downgrade() -> None:
    op.drop_table("telemetry_latest")
    op.drop_index("ix_events_equipment_observed", table_name="telemetry_events")
    op.drop_table("telemetry_events")
    op.drop_table("threshold_profiles")
    op.drop_table("equipment")
    op.drop_table("organizations")
