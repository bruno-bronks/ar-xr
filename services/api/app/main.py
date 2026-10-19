"""Composition root da API."""

from collections.abc import Mapping

from fastapi import FastAPI

from app.config import Settings
from app.health import Check, build_router, check_broker, check_database
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware


def create_app(
    checks: Mapping[str, Check] | None = None, settings: Settings | None = None
) -> FastAPI:
    """`checks` permite injetar verificacoes (testes); sem ele usa banco e broker reais."""
    if checks is None:
        settings = settings or Settings()
        database_url = settings.database_url.get_secret_value()
        checks = {
            "database": lambda: check_database(database_url),
            "broker": lambda: check_broker(settings.mqtt_host, settings.mqtt_port),
        }
    if settings is not None:
        configure_logging(settings.log_level)

    is_production = settings is not None and settings.environment == "production"
    app = FastAPI(
        title="Spatial AI Platform API",
        version="0.1.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None,
        openapi_url=None if is_production else "/openapi.json",
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(build_router(checks))
    return app


def get_app() -> FastAPI:
    """Factory para o uvicorn (`--factory`): configuracao so e lida ao iniciar o servidor."""
    return create_app()
