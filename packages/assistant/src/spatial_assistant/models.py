"""Tipos de dados do assistente (SPEC-009). Sem I/O."""

from dataclasses import dataclass
from enum import StrEnum

from spatial_assistant.policy import RefusalReason


class Outcome(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REFUSED = "refused"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProviderName(StrEnum):
    EXTRACTIVE = "extractive"
    LLM = "llm"


@dataclass(frozen=True)
class LiveAlert:
    severity: str
    rule: str


@dataclass(frozen=True)
class LiveState:
    """Estado por REGRA determinística (twin). O assistente apenas le; nunca altera."""

    status: str
    alerts: tuple[LiveAlert, ...]


@dataclass(frozen=True)
class SourceRef:
    document_id: str
    chunk_id: str
    title: str
    section: str
    version: str
    excerpt: str


@dataclass(frozen=True)
class AssistantResult:
    outcome: Outcome
    answer: str
    confidence: Confidence
    sources: tuple[SourceRef, ...]
    human_review_required: bool
    provider: ProviderName
    fallback_used: bool
    refusal_reason: RefusalReason | None
