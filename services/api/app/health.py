"""Liveness/readiness (SPEC-001; REQ-ENG-002, REQ-ENG-003).

O corpo das respostas contem apenas `ok`/`fail`; detalhes de excecao nunca saem do processo.
"""

import logging
import socket
from collections.abc import Callable, Mapping
from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

logger = logging.getLogger("app.health")

Check = Callable[[], bool]


class Live(BaseModel):
    status: Literal["alive"]


class ReadyChecks(BaseModel):
    database: Literal["ok", "fail"]
    broker: Literal["ok", "fail"]


class Ready(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: ReadyChecks


def check_database(url: str, timeout: int = 2) -> bool:
    """`SELECT 1` com timeout curto. Nunca propaga excecao nem registra a URL."""
    engine = None
    try:
        engine = create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": timeout})
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("database check failed", extra={"error_type": type(exc).__name__})
        return False
    finally:
        if engine is not None:
            engine.dispose()


def check_broker(host: str, port: int, timeout: float = 2.0) -> bool:
    """Conexao TCP ao broker MQTT."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError as exc:
        logger.warning("broker check failed", extra={"error_type": type(exc).__name__})
        return False


def build_router(checks: Mapping[str, Check]) -> APIRouter:
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live", response_model=Live)
    def live() -> Live:
        return Live(status="alive")

    @router.get("/ready", response_model=Ready, responses={503: {"model": Ready}})
    def ready() -> JSONResponse:
        results: dict[str, str] = {}
        for name, check in checks.items():
            try:
                results[name] = "ok" if check() else "fail"
            except Exception as exc:
                logger.warning(
                    f"readiness check failed: {name}", extra={"error_type": type(exc).__name__}
                )
                results[name] = "fail"
        if any(value == "fail" for value in results.values()):
            logger.warning(f"readiness degraded: {results}")
        is_ready = all(value == "ok" for value in results.values())
        return JSONResponse(
            status_code=200 if is_ready else 503,
            content={"status": "ready" if is_ready else "not_ready", "checks": results},
        )

    return router
