"""Fixtures compartilhadas.

Testes com PostgreSQL real exigem `TEST_DATABASE_URL` (URL de um servidor onde o usuario pode criar
bancos, ex.: o `db` do Compose). Sem ela, esses testes sao PULADOS (nunca "passam" sem banco).
Cada sessao de teste cria um banco descartavel `spatial_t_<hex>` e o remove ao final.
"""

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

requires_postgres = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="TEST_DATABASE_URL nao definido (PostgreSQL real indisponivel)",
)


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    """Cria um banco descartavel, aplica as migracoes e o remove no final."""
    if TEST_DATABASE_URL is None:
        pytest.skip("TEST_DATABASE_URL nao definido")
    from spatial_storage.migrate import upgrade

    base = make_url(TEST_DATABASE_URL)
    name = f"spatial_t_{uuid.uuid4().hex[:12]}"
    admin = create_engine(base, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = base.set(database=name).render_as_string(hide_password=False)
    try:
        upgrade(url)
        yield url
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def pg_engine(pg_url: str) -> Iterator[Engine]:
    """Engine limpa: tabelas truncadas e seed reaplicado antes de cada teste."""
    from spatial_storage.postgres import apply_seed, truncate_all
    from spatial_storage.seed_data import SEED

    engine = create_engine(pg_url, pool_size=10)
    truncate_all(engine)
    apply_seed(engine, SEED)
    yield engine
    engine.dispose()
