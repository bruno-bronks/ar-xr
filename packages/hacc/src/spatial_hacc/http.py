"""Adaptador HTTP SOMENTE LEITURA do HACC (SPEC-010, REQ-HACC-002, D-026). Opcional e desligado.

Contrato ASSUMIDO (`specs/contracts/hacc-readonly.yaml`), NAO verificado contra o HACC real. Exerce
apenas `GET` em dois caminhos fixos; host em lista permitida; https (ou http so em loopback); sem
redirecionamentos; timeout; corpo limitado; JSON estrito. Erros nunca carregam corpo/URL/credencial.
"""

import re
import urllib.error
import urllib.request
from collections.abc import Sequence
from urllib.parse import urlsplit

from pydantic import TypeAdapter, ValidationError

from spatial_hacc.models import BedRecord, WardRecord
from spatial_hacc.source import HaccUnavailable

MAX_BYTES = 1_000_000
MAX_ITEMS = 1000
_WARD_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")
_LOOPBACK = {"127.0.0.1", "localhost"}
_WARDS = TypeAdapter(list[WardRecord])
_BEDS = TypeAdapter(list[BedRecord])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None  # a resposta 3xx vira HTTPError e e tratada como indisponivel


_OPENER = urllib.request.build_opener(_NoRedirect)


def _validate_base_url(base_url: str, allowed_hosts: Sequence[str]) -> str:
    parts = urlsplit(base_url)
    host = parts.hostname or ""
    if parts.scheme not in {"https", "http"} or not host:
        raise ValueError("HACC base URL must be http(s) with a host")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("HACC base URL must not carry credentials, query or fragment")
    if host not in allowed_hosts:
        raise ValueError("HACC host is not in the allow-list")
    if parts.scheme == "http" and host not in _LOOPBACK:
        raise ValueError("HACC over plain http is only allowed for loopback")
    return base_url.rstrip("/")


class HttpHaccSource:
    def __init__(
        self,
        base_url: str,
        *,
        allowed_hosts: Sequence[str],
        timeout_s: float = 5.0,
        max_bytes: int = MAX_BYTES,
    ) -> None:
        self._base = _validate_base_url(base_url, allowed_hosts)
        self._timeout = timeout_s
        self._max_bytes = max_bytes

    def list_wards(self) -> list[WardRecord]:
        return self._parse(_WARDS, self._get("/v1/wards"))

    def list_beds(self, ward_id: str) -> list[BedRecord]:
        if not _WARD_ID.fullmatch(ward_id):
            raise HaccUnavailable("invalid ward id")
        return self._parse(_BEDS, self._get(f"/v1/wards/{ward_id}/beds"))

    def _get(self, path: str) -> bytes:
        request = urllib.request.Request(self._base + path, method="GET")  # noqa: S310
        try:
            with _OPENER.open(request, timeout=self._timeout) as response:
                if response.status != 200:
                    raise HaccUnavailable("unexpected status")
                body: bytes = response.read(self._max_bytes + 1)
        except HaccUnavailable:
            raise
        except (urllib.error.URLError, OSError, ValueError):
            raise HaccUnavailable("source unreachable or refused") from None
        if len(body) > self._max_bytes:
            raise HaccUnavailable("response too large")
        return body

    @staticmethod
    def _parse[T](adapter: TypeAdapter[list[T]], body: bytes) -> list[T]:
        try:
            items = adapter.validate_json(body)
        except ValidationError:
            raise HaccUnavailable("invalid payload") from None
        if len(items) > MAX_ITEMS:
            raise HaccUnavailable("too many items")
        return items
