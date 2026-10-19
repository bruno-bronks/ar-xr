"""Composition root da API."""

import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from spatial_common.logging_json import configure_logging
from spatial_storage.postgres import PostgresRepository
from spatial_storage.repository import Repository
from sqlalchemy import create_engine
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import build_authenticator
from app.config import Settings
from app.health import Check, build_router, check_broker, check_database
from app.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.ratelimit import FixedWindowLimiter
from app.routes import router as api_router


def _find_panel_dir(configured: str | None, module_file: Path = Path(__file__)) -> Path | None:
    parents = module_file.resolve().parents
    checkout = parents[3] / "clients" / "web-fallback" if len(parents) > 3 else None  # repo local
    candidates = [
        Path(configured) if configured else None,
        Path(os.environ["PANEL_DIR"]) if "PANEL_DIR" in os.environ else None,
        checkout,
        Path("/srv/panel"),  # imagem Docker
    ]
    return next((c for c in candidates if c is not None and (c / "index.html").is_file()), None)


def create_app(
    *,
    checks: Mapping[str, Check] | None = None,
    settings: Settings | None = None,
    repo: Repository | None = None,
    clock: Callable[[], datetime] | None = None,
    marker_rate_limit: int | None = None,
) -> FastAPI:
    """Sem `settings`, `checks` e `repo` precisam ser injetados (composicao de testes)."""
    if settings is None and (checks is None or repo is None):
        settings = Settings()
    environment = settings.environment if settings else "test"
    authenticator = build_authenticator(settings.auth_mode if settings else "demo", environment)

    if repo is None:
        if settings is None:
            raise RuntimeError("settings required to build the repository")
        engine = create_engine(
            settings.database_url.get_secret_value(), pool_pre_ping=True, pool_size=5
        )
        repo = PostgresRepository(engine)
    if checks is None:
        if settings is None:
            raise RuntimeError("settings required to build health checks")
        database_url, mqtt_host, mqtt_port = (
            settings.database_url.get_secret_value(),
            settings.mqtt_host,
            settings.mqtt_port,
        )
        checks = {
            "database": lambda: check_database(database_url),
            "broker": lambda: check_broker(mqtt_host, mqtt_port),
        }

    is_production = environment == "production"
    app = FastAPI(
        title="Spatial AI Platform API",
        version="0.2.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None,
        openapi_url=None if is_production else "/openapi.json",
    )
    app.state.repo = repo
    app.state.authenticator = authenticator
    app.state.clock = clock or (lambda: datetime.now(UTC))
    limit = marker_rate_limit or (settings.marker_rate_limit if settings else 30)
    app.state.marker_limiter = FixedWindowLimiter(limit, 60.0, app.state.clock)

    @app.exception_handler(StarletteHTTPException)
    async def uniform_not_found(request: Request, exc: StarletteHTTPException) -> Response:
        if exc.status_code == 404:  # rota inexistente e recurso inexistente/alheio: mesmo corpo
            return JSONResponse(status_code=404, content={"detail": "not found"})
        return await http_exception_handler(request, exc)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(build_router(checks))
    app.include_router(api_router)

    panel_dir = _find_panel_dir(settings.panel_dir if settings else None)
    if panel_dir is not None:
        app.mount("/panel", StaticFiles(directory=panel_dir, html=True), name="panel")
    return app


def get_app() -> FastAPI:
    """Factory para o uvicorn (`--factory`): configuracao e logging so ao iniciar o servidor."""
    settings = Settings()
    configure_logging(settings.log_level)
    return create_app(settings=settings)
