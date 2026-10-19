"""SPEC-005 A5 · REQ-MNT-007: migracoes Alembic e seed contra PostgreSQL real."""

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError

from tests.conftest import TEST_DATABASE_URL

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(TEST_DATABASE_URL is None, reason="TEST_DATABASE_URL nao definido"),
]

TABLES = {
    "organizations",
    "equipment",
    "threshold_profiles",
    "telemetry_events",
    "telemetry_latest",
}


@pytest.fixture
def blank_db() -> Iterator[str]:
    assert TEST_DATABASE_URL is not None
    base = make_url(TEST_DATABASE_URL)
    name = f"spatial_m_{uuid.uuid4().hex[:12]}"
    admin = create_engine(base, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    yield base.set(database=name).render_as_string(hide_password=False)
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_upgrade_creates_schema_and_downgrade_removes_it(blank_db: str) -> None:
    from spatial_storage.migrate import downgrade, upgrade

    url = blank_db
    upgrade(url)
    engine = create_engine(url)
    assert _tables(engine) == TABLES

    downgrade(url)
    assert _tables(create_engine(url)) == set()

    upgrade(url)  # reaplica sem erro
    assert _tables(create_engine(url)) == TABLES


def test_upgrade_is_idempotent(blank_db: str) -> None:
    from spatial_storage.migrate import upgrade

    upgrade(blank_db)
    upgrade(blank_db)

    assert _tables(create_engine(blank_db)) == TABLES


def test_seed_is_idempotent_and_does_not_touch_telemetry(blank_db: str) -> None:
    from spatial_storage.migrate import upgrade
    from spatial_storage.postgres import apply_seed
    from spatial_storage.seed_data import SEED

    upgrade(blank_db)
    engine = create_engine(blank_db)
    apply_seed(engine, SEED)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO telemetry_events VALUES ('s','e','EQ-001','temperature',1,'c',now(),now(),'GOOD')"
            )
        )

    apply_seed(engine, SEED)

    with engine.connect() as conn:
        counts = {
            t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()  # noqa: S608
            for t in ("organizations", "equipment", "threshold_profiles", "telemetry_events")
        }
    assert counts == {
        "organizations": 2,
        "equipment": 4,
        "threshold_profiles": 8,
        "telemetry_events": 1,
    }


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO threshold_profiles VALUES ('EQ-001','pressure','bar',10,5)",  # warn > crit
        "INSERT INTO equipment VALUES ('X','org-zzz','n','t','l',NULL,30,NULL)",  # org inexistente
        "INSERT INTO equipment VALUES ('X','org-a','n','t','l',NULL,0,NULL)",  # offline_after <= 0
        "INSERT INTO equipment VALUES ('X','org-a','n','t','l','QR-EQ-001',30,NULL)",  # marker duplicado
        "INSERT INTO telemetry_events VALUES ('s','e','EQ-001','temperature','NaN','c',now(),now(),'GOOD')",
        "INSERT INTO telemetry_events VALUES ('s','e','EQ-001','temperature','Infinity','c',now(),now(),'GOOD')",
        "INSERT INTO telemetry_events VALUES ('s','e','EQ-001','temperature',1,'c',now(),now(),'MAYBE')",
        "INSERT INTO telemetry_events VALUES ('s','e','EQ-001','pressure',1,'c',now(),now(),'GOOD')",
    ],
)
def test_database_constraints_reject_invalid_rows(pg_engine: Engine, statement: str) -> None:
    with pytest.raises(IntegrityError), pg_engine.begin() as conn:
        conn.execute(text(statement))


def test_models_match_migrations(blank_db: str) -> None:
    """Sem deriva: o que `models.py` descreve e exatamente o que a migracao cria."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from spatial_storage.migrate import upgrade
    from spatial_storage.models import metadata

    upgrade(blank_db)
    engine = create_engine(blank_db)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), metadata)

    assert diff == []
