"""Fonte de INTEGRACAO com o HACC real, somente leitura (SPEC-010, REQ-HACC-007/002, D-054).

Le UMA rota do HACC, `GET /integration/v1/beds` (contrato em `specs/contracts/hacc-integration.yaml`), com
`Authorization: Bearer`. A rota so devolve `bed_id`, `sector`, `status` e `occupied`: nunca ha paciente. Campo
fora da lista rejeita a resposta INTEIRA (mesma politica do restante do pacote). O HACC nao tem ala, grade,
posicao nem alarmes de leito: ala/posicao vem do PERFIL abaixo (configuracao NOSSA, ilustrativa) e nenhum
alarme e inventado. `observed_at` = instante do instantaneo do HACC (`generated_at`); o `tenant_id` e imposto
pela nossa configuracao (D-030), nunca pelo HACC.
"""

import json
import math
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from spatial_hacc.http import MAX_BYTES, MAX_ITEMS, _NoRedirect, _validate_base_url
from spatial_hacc.models import BedRecord, FlagsRecord, WardRecord
from spatial_hacc.source import HaccUnavailable

_PATH = "/integration/v1/beds"
_WARD_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")
MIN_TOKEN_LENGTH = 16
_OPENER = urllib.request.build_opener(_NoRedirect)
_NO_FLAGS = FlagsRecord(
    bed_exit_alarm=False, iv_pump_alarm=False, call_button=False, cleaning_due=False
)


@dataclass(frozen=True)
class SectorProfile:
    ward_id: str
    name: str
    width: int  # colunas da grade; as linhas crescem conforme o numero de leitos


# Perfil para o HACC 0.4 (setores `Emergency`, `Ward`, `ICU`). Nomes e larguras sao NOSSOS (ilustrativos).
DEFAULT_PROFILE: Mapping[str, SectorProfile] = {
    "ICU": SectorProfile("HACC-ICU", "UTI (HACC)", 3),
    "Emergency": SectorProfile("HACC-ER", "Pronto-socorro (HACC)", 5),
    "Ward": SectorProfile("HACC-WARD", "Enfermaria (HACC)", 5),
}


class _Bed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    bed_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,64}$")
    sector: str = Field(min_length=1, max_length=100)
    status: Literal["available", "occupied", "unavailable"]
    occupied: bool


class _Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    generated_at: datetime
    beds: list[_Bed]

    @field_validator("generated_at", mode="before")
    @classmethod
    def _parse(cls, value: object) -> object:
        return datetime.fromisoformat(value) if isinstance(value, str) else value

    @field_validator("generated_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        return value


class HaccIntegrationSource:
    def __init__(
        self,
        base_url: str,
        *,
        token: str,
        allowed_hosts: Sequence[str],
        tenant_id: str,
        allow_plain_http: bool = False,  # D-055: so para rede privada (ex.: rede interna do Docker)
        profile: Mapping[str, SectorProfile] = DEFAULT_PROFILE,
        timeout_s: float = 5.0,
        max_bytes: int = MAX_BYTES,
        cache_ttl_s: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if len(token.strip()) < MIN_TOKEN_LENGTH:
            raise ValueError("HACC integration token must have at least 16 characters")
        self._base = _validate_base_url(base_url, allowed_hosts, allow_plain_http=allow_plain_http)
        self._token = token
        self._tenant = tenant_id
        self._profile = dict(profile)
        self._timeout = timeout_s
        self._max_bytes = max_bytes
        self._ttl = cache_ttl_s
        self._clock = clock
        self._cached: tuple[float, _Snapshot] | None = None

    # --- porta HaccSource ---------------------------------------------------------------------------

    def list_wards(self) -> list[WardRecord]:
        wards: list[WardRecord] = []
        for sector, profile in self._profile.items():
            beds = self._sector_beds(self._snapshot(), sector)
            if beds:
                wards.append(
                    WardRecord(
                        ward_id=profile.ward_id,
                        tenant_id=self._tenant,
                        name=profile.name,
                        width=profile.width,
                        height=math.ceil(len(beds) / profile.width),
                    )
                )
        return wards

    def list_beds(self, ward_id: str) -> list[BedRecord]:
        if not _WARD_ID.fullmatch(ward_id):
            raise HaccUnavailable("invalid ward id")
        match = next(((s, p) for s, p in self._profile.items() if p.ward_id == ward_id), None)
        if match is None:
            return []
        sector, profile = match
        snapshot = self._snapshot()
        return [
            BedRecord(
                bed_id=bed.bed_id,
                ward_id=profile.ward_id,
                tenant_id=self._tenant,
                label=bed.bed_id,
                x=index % profile.width + 1,
                y=index // profile.width + 1,
                occupied=bed.occupied,
                flags=_NO_FLAGS,
                observed_at=snapshot.generated_at,
                blocked=bed.status == "unavailable",
            )
            for index, bed in enumerate(self._sector_beds(snapshot, sector))
        ]

    # --- interno ------------------------------------------------------------------------------------

    @staticmethod
    def _sector_beds(snapshot: _Snapshot, sector: str) -> list[_Bed]:
        return sorted((b for b in snapshot.beds if b.sector == sector), key=lambda b: b.bed_id)

    def _snapshot(self) -> _Snapshot:
        now = self._clock()
        if self._cached is not None and now - self._cached[0] < self._ttl:
            return self._cached[1]
        snapshot = self._parse(self._get())
        self._cached = (now, snapshot)
        return snapshot

    def _get(self) -> bytes:
        request = urllib.request.Request(  # noqa: S310 - base validada (host/esquema)
            self._base + _PATH,
            headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
            method="GET",
        )
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
    def _parse(body: bytes) -> _Snapshot:
        try:
            snapshot = _Snapshot.model_validate(json.loads(body))
        except (ValidationError, ValueError):
            raise HaccUnavailable("invalid payload") from None
        if len(snapshot.beds) > MAX_ITEMS:
            raise HaccUnavailable("too many items")
        return snapshot
