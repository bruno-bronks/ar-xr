"""Resolucao de marker/QR sem vazamento entre organizacoes (SPEC-003 / Z-003 / REQ-MNT-001)."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Found:
    equipment_id: str


@dataclass(frozen=True)
class NotFound:
    """Resultado unico para marker desconhecido e para marker de outra organizacao."""


NOT_FOUND = NotFound()

Resolution = Found | NotFound


class Registry:
    """Z: Registry. `marker_of` e funcao parcial injetiva; todo equipamento marcado tem dono."""

    def __init__(self, marker_of: Mapping[str, str], owner: Mapping[str, str]) -> None:
        if len(set(marker_of.values())) != len(marker_of):
            raise ValueError("marker_of must be injective: one marker per equipment")
        missing = set(marker_of.values()) - set(owner)
        if missing:
            raise ValueError(f"equipment without owner: {sorted(missing)}")
        self._marker_of = MappingProxyType(dict(marker_of))
        self._owner = MappingProxyType(dict(owner))

    @property
    def marker_of(self) -> Mapping[str, str]:
        return self._marker_of

    @property
    def owner(self) -> Mapping[str, str]:
        return self._owner

    def resolve(self, marker_id: str, caller_org: str) -> Resolution:
        """O conteudo do marker e so uma chave opaca; nunca confiado nem interpretado."""
        equipment_id = self._marker_of.get(marker_id)
        if equipment_id is not None and self._owner[equipment_id] == caller_org:
            return Found(equipment_id)
        return NOT_FOUND
