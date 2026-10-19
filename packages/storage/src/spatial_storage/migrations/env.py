"""Ambiente Alembic: URL vem de `sqlalchemy.url` (definida por spatial_storage.migrate)."""

from alembic import context
from spatial_storage.models import metadata
from sqlalchemy import create_engine, pool

config = context.config


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if url is None:
        raise RuntimeError("sqlalchemy.url nao configurada")
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
