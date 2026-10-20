"""Autenticacao (SPEC-006; REQ-SEC-003). Modo demo explicito, fail closed em producao (D-009)."""

import hmac
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, Request


@dataclass(frozen=True)
class Principal:
    user_id: str
    org_id: str
    scopes: frozenset[str] = field(default_factory=frozenset)  # ex.: hacc:read (D-027)


class Authenticator(Protocol):
    def authenticate(self, token: str) -> Principal | None: ...


class DemoAuthenticator:
    """Tokens FICTICIOS e publicos (estao no repositorio). Somente fora de producao."""

    _TOKENS: dict[str, Principal] = {  # noqa: RUF012
        "demo-operator-a": Principal("user-a", "org-a"),
        "demo-operator-b": Principal("user-b", "org-b"),
        "demo-nurse-a": Principal("nurse-a", "org-a", frozenset({"hacc:read"})),
        "demo-nurse-b": Principal("nurse-b", "org-b", frozenset({"hacc:read"})),
    }

    def authenticate(self, token: str) -> Principal | None:
        candidate = token.encode("utf-8", "replace")
        match: Principal | None = None
        for (
            known,
            principal,
        ) in self._TOKENS.items():  # percorre todos: tempo independente do acerto
            if hmac.compare_digest(candidate, known.encode()):
                match = principal
        return match


def build_authenticator(auth_mode: str, environment: str) -> Authenticator:
    if auth_mode == "oidc":
        raise RuntimeError("AUTH_MODE=oidc is not implemented yet (requires an approved IdP)")
    if auth_mode == "demo":
        if environment == "production":
            raise RuntimeError("demo authentication is refused in production")
        return DemoAuthenticator()
    raise RuntimeError(f"unknown AUTH_MODE: {auth_mode!r}")


def require_principal(request: Request) -> Principal:
    """Dependencia FastAPI: 401 uniforme para qualquer credencial ausente ou invalida."""
    unauthorized = HTTPException(
        status_code=401, detail="not authenticated", headers={"WWW-Authenticate": "Bearer"}
    )
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise unauthorized
    authenticator: Authenticator = request.app.state.authenticator
    principal = authenticator.authenticate(token)
    if principal is None:
        raise unauthorized
    return principal


def require_scope(scope: str) -> Callable[..., Principal]:
    """Dependencia FastAPI: autenticado E com o escopo; senao 403 uniforme (REQ-HACC-004)."""

    def dependency(principal: Annotated[Principal, Depends(require_principal)]) -> Principal:
        if scope not in principal.scopes:
            from app.audit import audit  # import tardio: audit importa Principal deste modulo

            audit(principal, "hacc.access", "hacc", "forbidden")
            raise HTTPException(status_code=403, detail="forbidden")
        return principal

    return dependency
