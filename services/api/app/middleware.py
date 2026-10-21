"""Middleware ASGI: correlation ID e log de acesso (REQ-ENG-004)."""

import logging
import re
import time
import uuid
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.logging_config import correlation_id_var

CORRELATION_HEADER = "X-Correlation-ID"
_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_access_log = logging.getLogger("app.access")


def normalize_correlation_id(raw: str | None) -> str:
    """Aceita IDs seguros; qualquer outro valor (inclusive hostil) vira um UUID novo."""
    if raw is not None and _VALID_ID.fullmatch(raw):
        return raw
    return str(uuid.uuid4())


_PANEL_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


class SecurityHeadersMiddleware:
    """`nosniff` em tudo, `no-store` em API/health e CSP estrita no painel (SPEC-006/007)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope["path"]

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-content-type-options", b"nosniff"))
                if path.startswith(("/api/", "/health", "/metrics")):
                    headers.append((b"cache-control", b"no-store"))
                if path.startswith("/panel"):
                    headers.append((b"content-security-policy", _PANEL_CSP.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers: dict[bytes, bytes] = dict(scope["headers"])
        incoming = headers.get(CORRELATION_HEADER.lower().encode())
        correlation_id = normalize_correlation_id(
            incoming.decode("latin-1") if incoming is not None else None
        )
        token = correlation_id_var.set(correlation_id)
        started = time.perf_counter()
        status = 500

        async def send_with_header(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (CORRELATION_HEADER.lower().encode(), correlation_id.encode()),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            extra: dict[str, Any] = {
                "correlation_id": correlation_id,
                "method": scope["method"],
                "path": scope["path"],  # sem query string: pode conter segredos
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            _access_log.info("request", extra=extra)
            correlation_id_var.reset(token)
