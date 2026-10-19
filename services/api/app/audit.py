"""Auditoria de acesso a dados (REQ-SEC-004). Nunca registra token, corpo ou marker consultado."""

import logging
import re

from spatial_common.logging_json import correlation_id_var

from app.auth import Principal

_audit = logging.getLogger("app.audit")
_SAFE_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")


def audit(principal: Principal, action: str, resource: str, outcome: str) -> None:
    _audit.info(
        "access",
        extra={
            "user_id": principal.user_id,
            "org_id": principal.org_id,
            "action": action,
            "resource": resource,
            "outcome": outcome,
            "correlation_id": correlation_id_var.get(),
        },
    )


def resource_id(kind: str, raw: str) -> str:
    """`equipment/EQ-001`; ids malformados viram `equipment/<invalid>` (nao ecoa entrada hostil)."""
    return f"{kind}/{raw}" if _SAFE_ID.fullmatch(raw) else f"{kind}/<invalid>"
