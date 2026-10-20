"""Modelos estritos do HACC (SPEC-010, REQ-HACC-003, D-028).

`extra="forbid"` + `strict`: qualquer campo fora da lista permitida (nome, CPF, prontuario, sinais
vitais...) rejeita o payload INTEIRO. Nao ha campo de identificacao de pessoa neste modelo.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

Id = Annotated[str, Field(pattern=r"^[A-Za-z0-9._:-]{1,64}$")]
Cell = Annotated[int, Field(ge=1, le=100)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class FlagsRecord(_Strict):
    bed_exit_alarm: bool
    iv_pump_alarm: bool
    call_button: bool
    cleaning_due: bool


class WardRecord(_Strict):
    ward_id: Id
    tenant_id: Id
    name: Annotated[str, Field(min_length=1, max_length=120)]
    width: Cell
    height: Cell


class BedRecord(_Strict):
    bed_id: Id
    ward_id: Id
    tenant_id: Id
    label: Annotated[str, Field(min_length=1, max_length=40)]
    x: Cell
    y: Cell
    occupied: bool
    flags: FlagsRecord
    observed_at: datetime | None

    @field_validator("observed_at")
    @classmethod
    def _aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("observed_at must be timezone-aware")
        return value
