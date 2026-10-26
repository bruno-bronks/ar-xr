"""Modelos de resposta da API (espelham specs/contracts/openapi.yaml)."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

Status = Literal["NORMAL", "WARNING", "CRITICAL", "OFFLINE", "UNKNOWN"]
Quality = Literal["GOOD", "BAD"]


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_serializer("*", when_used="json", check_fields=False)
    def _utc(self, value: object) -> object:
        # PostgreSQL devolve datetimes no fuso da sessao; a API sempre responde em UTC ("Z").
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return value


class EquipmentOut(_Out):
    id: str
    name: str
    type: str
    location: str
    last_seen_at: datetime | None
    status: Status


class TelemetryReadingOut(_Out):
    equipment_id: str
    sensor_type: str
    value: float
    unit: str
    observed_at: datetime
    received_at: datetime
    quality: Quality
    event_id: str


class SensorOut(_Out):
    sensor_type: str
    unit: str
    value: float | None
    observed_at: datetime | None
    quality: Quality | None
    warn: float
    crit: float
    valid: bool


class TwinOut(_Out):
    equipment_id: str
    status: Status
    evaluated_at: datetime
    offline_after_seconds: int
    sensors: list[SensorOut]


class AlertOut(_Out):
    equipment_id: str
    severity: Literal["WARNING", "CRITICAL", "OFFLINE"]
    rule: str
    raised_at: datetime
    sensor_type: str | None = None
    value: float | None = None
    limit: float | None = None


class ErrorOut(_Out):
    detail: str


class AssistantAskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equipment_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")
    question: str = Field(min_length=1, max_length=2000)


class AssistantSourceOut(_Out):
    document_id: str
    chunk_id: str
    title: str
    section: str
    version: str
    excerpt: str


class AssistantLiveAlertOut(_Out):
    severity: Literal["WARNING", "CRITICAL", "OFFLINE"]
    rule: str


class AssistantLiveStateOut(_Out):
    status: Status
    alerts: list[AssistantLiveAlertOut]


class AssistantAnswerOut(_Out):
    outcome: Literal["answered", "insufficient_evidence", "refused"]
    answer: str
    confidence: Literal["low", "medium", "high"]
    sources: list[AssistantSourceOut]
    human_review_required: bool
    provider: Literal["extractive", "llm"]
    fallback_used: bool
    refusal_reason: Literal["physical_action", "safety_bypass", "prompt_injection"] | None
    live_state: AssistantLiveStateOut


BedStatusLit = Literal["NORMAL", "ATTENTION", "ALERT", "BLOCKED", "OFFLINE", "UNKNOWN"]


class HaccAlertOut(_Out):
    severity: Literal["ALERT", "ATTENTION", "OFFLINE"]
    rule: str


class HaccWardSummaryOut(_Out):
    ward_id: str
    name: str
    bed_count: int
    status: BedStatusLit
    alert_count: int


class HaccBedOut(_Out):
    bed_id: str
    label: str
    x: int
    y: int
    occupied: bool
    status: BedStatusLit
    observed_at: datetime | None
    alerts: list[HaccAlertOut]


class HaccWardInfoOut(_Out):
    ward_id: str
    name: str
    width: int
    height: int


class HaccWardBedsOut(_Out):
    ward: HaccWardInfoOut
    evaluated_at: datetime
    status: BedStatusLit
    beds: list[HaccBedOut]
