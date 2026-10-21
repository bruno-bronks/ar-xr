"""`/metrics` (Prometheus) e instrumentacao HTTP (SPEC-012, REQ-OPS-005; D-046).

- Habilitado somente com `METRICS_TOKEN` (>= 16 caracteres); sem ele a rota nao existe (404 uniforme).
- O token de metricas e DISTINTO dos tokens de usuario: um nao abre o outro.
- Rotulo `route` e o MODELO da rota (`/api/v1/equipment/{equipment_id}`), nunca a URL real; caminhos
  desconhecidos (scanners) colapsam em `unmatched`. Nenhum id, usuario, organizacao ou token vira rotulo.
"""

import hmac
import time
from collections.abc import Mapping

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from spatial_common.metrics import CONTENT_TYPE, Registry
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.health import Check

_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


def route_label(scope: Scope) -> str:
    route = scope.get("route")
    template = getattr(route, "path", None)
    if isinstance(template, str):
        return template
    if str(scope.get("path", "")).startswith("/panel"):
        return "/panel"
    return "unmatched"


class MetricsMiddleware:
    def __init__(self, app: ASGIApp, registry: Registry) -> None:
        self.app = app
        self._requests = registry.counter(
            "http_requests_total", "HTTP requests handled.", ("route", "method", "status_class")
        )
        self._duration = registry.histogram(
            "http_request_duration_seconds", "HTTP request latency.", _BUCKETS, ("route",)
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = 500

        async def capture(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture)
        finally:
            route = route_label(scope)
            method = scope["method"] if scope["method"] in _METHODS else "OTHER"
            self._requests.inc(route=route, method=method, status_class=f"{status // 100}xx")
            self._duration.observe(time.perf_counter() - started, route=route)


_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})


def build_metrics_router(registry: Registry, token: str, checks: Mapping[str, Check]) -> APIRouter:
    router = APIRouter()
    dependency = registry.gauge(
        "dependency_up", "1 if the readiness check of the dependency passes.", ("dependency",)
    )

    def probe() -> None:
        for name, check in checks.items():
            try:
                up = bool(check())
            except Exception:  # a causa nunca sai (pode conter host/credencial)
                up = False
            dependency.set(1 if up else 0, dependency=name)

    registry.add_collector(probe)
    expected = token.encode()

    @router.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
    def scrape(request: Request) -> PlainTextResponse:
        scheme, _, presented = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(presented.encode(), expected):
            raise HTTPException(
                status_code=401, detail="not authenticated", headers={"WWW-Authenticate": "Bearer"}
            )
        return PlainTextResponse(registry.render(), media_type=CONTENT_TYPE)

    return router
