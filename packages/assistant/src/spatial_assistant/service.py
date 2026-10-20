"""Orquestracao do assistente (SPEC-009): politica -> recuperacao -> evidencia -> resposta."""

import logging
from dataclasses import replace

from spatial_assistant.grounding import check_grounding
from spatial_assistant.knowledge import Chunk, KnowledgeBase
from spatial_assistant.llm import LlmProvider, build_prompt, parse_llm_output
from spatial_assistant.models import (
    AssistantResult,
    Confidence,
    LiveState,
    Outcome,
    ProviderName,
    SourceRef,
)
from spatial_assistant.policy import RefusalReason, check_question
from spatial_assistant.retrieval import Hit, retrieve
from spatial_assistant.text import normalize_text, sentence_spans, terms

logger = logging.getLogger("spatial_assistant")

NOTICE = (
    "Sugestão assistiva baseada em documentação aprovada; não aciona nenhuma ação física. "
    "Confirme com o responsável de manutenção antes de agir."
)
MIN_COVERAGE = 0.5
HIGH_COVERAGE = 0.8
MEDIUM_COVERAGE = 0.65
RETRIEVE_LIMIT = 3
MAX_SOURCES = 2
MAX_EXCERPT_CHARS = 600
_REVIEW_STATES = frozenset({"CRITICAL", "OFFLINE"})

_REFUSALS = {
    RefusalReason.PHYSICAL_ACTION: (
        "Não posso acionar, desligar, reiniciar nem ajustar equipamentos: o assistente é apenas "
        "informativo. A decisão e a execução são do responsável de manutenção."
    ),
    RefusalReason.SAFETY_BYPASS: (
        "Não posso orientar a ignorar, silenciar ou contornar alarmes, limites ou proteções. "
        "Escale para o responsável de manutenção e o supervisor."
    ),
    RefusalReason.PROMPT_INJECTION: (
        "A pergunta contém instruções dirigidas ao próprio sistema, que eu não sigo. "
        "Reformule perguntando apenas sobre o equipamento."
    ),
}
_INSUFFICIENT = (
    "Não encontrei, na documentação aprovada para este equipamento, informação suficiente para "
    "responder. Consulte o responsável de manutenção."
)


def _confidence(coverage: float) -> Confidence:
    if coverage >= HIGH_COVERAGE:
        return Confidence.HIGH
    if coverage >= MEDIUM_COVERAGE:
        return Confidence.MEDIUM
    return Confidence.LOW


def excerpt_for(chunk: Chunk, question: str) -> str:
    """Janela contigua de frases (substring LITERAL do trecho) que melhor casa com a pergunta."""
    spans = sentence_spans(chunk.text)
    if not spans:
        return chunk.text
    wanted = set(terms(question))
    best = max(
        range(len(spans)),
        key=lambda i: (len(wanted & set(terms(chunk.text[spans[i][0] : spans[i][1]]))), -i),
    )
    start, end = spans[best]
    for _, next_end in spans[best + 1 :]:
        if next_end - start > MAX_EXCERPT_CHARS:
            break
        end = next_end
    return chunk.text[start:end]


def _source(chunk: Chunk, question: str) -> SourceRef:
    return SourceRef(
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        title=chunk.title,
        section=chunk.section,
        version=chunk.version,
        excerpt=excerpt_for(chunk, question),
    )


class AssistantService:
    def __init__(self, kb: KnowledgeBase, llm: LlmProvider | None = None) -> None:
        self._kb = kb
        self._llm = llm

    def ask(self, question: str, equipment_type: str, live: LiveState) -> AssistantResult:
        q = normalize_text(question)
        reason = check_question(q)
        if reason is not None:
            return AssistantResult(
                Outcome.REFUSED, _REFUSALS[reason], Confidence.LOW, (), True,
                ProviderName.EXTRACTIVE, False, reason,
            )  # fmt: skip

        hits = [
            h
            for h in retrieve(self._kb.chunks, q, equipment_type, RETRIEVE_LIMIT)
            if h.coverage >= MIN_COVERAGE and h.topic_matches >= 1
        ]
        if not hits:
            return AssistantResult(
                Outcome.INSUFFICIENT_EVIDENCE, _INSUFFICIENT, Confidence.LOW, (), True,
                ProviderName.EXTRACTIVE, False, None,
            )  # fmt: skip

        confidence = _confidence(hits[0].coverage)
        if self._llm is not None:
            proposed = self._try_llm(q, hits, live, confidence)
            if proposed is not None:
                return proposed
        result = self._extractive(q, hits, live, confidence)
        return replace(result, fallback_used=self._llm is not None)

    def _extractive(
        self, q: str, hits: list[Hit], live: LiveState, confidence: Confidence
    ) -> AssistantResult:
        used = hits[:MAX_SOURCES]
        sources = tuple(_source(h.chunk, q) for h in used)
        body = "\n".join(f"{s.excerpt} [{i}]" for i, s in enumerate(sources, start=1))
        return AssistantResult(
            Outcome.ANSWERED, f"{body}\n\n{NOTICE}", confidence, sources,
            _needs_review([h.chunk for h in used], confidence, live),
            ProviderName.EXTRACTIVE, False, None,
        )  # fmt: skip

    def _try_llm(
        self, q: str, hits: list[Hit], live: LiveState, confidence: Confidence
    ) -> AssistantResult | None:
        assert self._llm is not None  # noqa: S101 - chamado so com LLM configurado
        prompt = build_prompt(q, hits, live)
        try:
            raw = self._llm.complete(prompt.system, prompt.user)
        except Exception as error:  # qualquer falha do provedor degrada para o extrativo
            logger.warning("llm unavailable", extra={"error_type": type(error).__name__})
            return None
        proposal = parse_llm_output(raw)
        if proposal is None:
            logger.warning("llm output rejected", extra={"reason": "invalid_shape"})
            return None
        by_id = {h.chunk.chunk_id: h.chunk for h in hits}
        if not all(cid in by_id for cid in proposal.citations):
            logger.warning("llm output rejected", extra={"reason": "unknown_citation"})
            return None
        cited = [by_id[cid] for cid in dict.fromkeys(proposal.citations)]
        grounding = check_grounding(proposal.answer, [c.text for c in cited], [q, live.status])
        if not grounding.ok:
            logger.warning("llm output rejected", extra={"reason": "ungrounded"})
            return None
        sources = tuple(_source(c, q) for c in cited)
        return AssistantResult(
            Outcome.ANSWERED, f"{proposal.answer}\n\n{NOTICE}", confidence, sources,
            _needs_review(cited, confidence, live), ProviderName.LLM, False, None,
        )  # fmt: skip


def _needs_review(chunks: list[Chunk], confidence: Confidence, live: LiveState) -> bool:
    return (
        any(c.high_risk for c in chunks)
        or confidence is Confidence.LOW
        or live.status in _REVIEW_STATES
    )
