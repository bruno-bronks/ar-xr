"""Executa migracoes Alembic programaticamente. Uso: `python -m spatial_storage.migrate`."""

import logging
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from spatial_storage.postgres import apply_seed
from spatial_storage.seed_data import SEED

logger = logging.getLogger("spatial_storage.migrate")


def _config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def upgrade(url: str, revision: str = "head") -> None:
    command.upgrade(_config(url), revision)


def downgrade(url: str, revision: str = "base") -> None:
    command.downgrade(_config(url), revision)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    url = os.environ.get("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL nao definido")
        return 2
    upgrade(url)
    logger.info("migrations applied")
    if os.environ.get("SEED_DEV_DATA") == "1":
        engine = create_engine(url)
        apply_seed(engine, SEED)
        engine.dispose()
        logger.info("dev seed applied (%d equipment)", len(SEED.equipment))
    return 0


if __name__ == "__main__":
    sys.exit(main())
