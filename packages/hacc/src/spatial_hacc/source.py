"""Porta SOMENTE LEITURA do HACC (SPEC-010, REQ-HACC-002, D-026). Nao existe operacao de escrita."""

from typing import Protocol

from spatial_hacc.models import BedRecord, WardRecord


class HaccUnavailable(Exception):
    """Fonte indisponivel ou payload inutilizavel. A mensagem nunca carrega corpo, URL ou credencial."""


class HaccSource(Protocol):
    def list_wards(self) -> list[WardRecord]: ...

    def list_beds(self, ward_id: str) -> list[BedRecord]: ...
