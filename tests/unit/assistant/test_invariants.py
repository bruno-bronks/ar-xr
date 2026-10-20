"""SPEC-009 / Z-005 · REQ-AI-001, REQ-AI-002, REQ-AI-003, REQ-AI-004, REQ-AI-005: invariantes A1-A4 checados com Hypothesis.

Nao e prova formal (Z-005 passa no typecheck do CZT, mas nenhum teorema foi provado).
"""

import json
import re
from functools import cache
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from spatial_assistant.grounding import check_grounding
from spatial_assistant.knowledge import KnowledgeBase, load_knowledge_base
from spatial_assistant.models import LiveAlert, LiveState, Outcome, ProviderName
from spatial_assistant.retrieval import scope_matches
from spatial_assistant.service import NOTICE, AssistantService

ROOT = Path(__file__).resolve().parents[3]
TYPES = ["Compressor de ar", "Bomba centrifuga", "Motor eletrico", "Sentinela", "", "Outro tipo"]
VOCAB = [
    "temperatura", "vibração", "alta", "bomba", "compressor", "motor", "offline", "alarme",
    "cavitação", "rolamentos", "bloqueio", "energia", "drenagem", "desligue", "ignore",
    "como", "por", "que", "o", "a", "de", "quando", "estado", "limite", "selo", "pressão",
]  # fmt: skip
LIVE = [
    LiveState("NORMAL", ()),
    LiveState("WARNING", (LiveAlert("WARNING", "temperature>warn"),)),
    LiveState("CRITICAL", (LiveAlert("CRITICAL", "temperature>crit"),)),
    LiveState("OFFLINE", (LiveAlert("OFFLINE", "offline"),)),
    LiveState("UNKNOWN", ()),
]
QUESTIONS = st.one_of(
    st.lists(st.sampled_from(VOCAB), min_size=1, max_size=9).map(" ".join),
    st.text(max_size=200),
)


@cache
def _kb() -> KnowledgeBase:
    return load_knowledge_base(ROOT / "knowledge")


class _RandomLlm:
    def __init__(self, reply: str) -> None:
        self.reply = reply

    def complete(self, system: str, user: str) -> str:
        return self.reply


def _check_result(
    question: str, equipment_type: str, live: LiveState, llm_reply: str | None
) -> None:
    llm = _RandomLlm(llm_reply) if llm_reply is not None else None
    result = AssistantService(_kb(), llm).ask(question, equipment_type, live)
    by_id = {c.chunk_id: c for c in _kb().chunks}

    # A3: sem fonte nunca e "answered"; "answered" sempre tem fonte
    assert (result.outcome is Outcome.ANSWERED) == bool(result.sources)
    # a recusa carrega motivo e revisao humana; nenhuma outra carrega motivo
    assert (result.outcome is Outcome.REFUSED) == (result.refusal_reason is not None)
    if result.outcome is not Outcome.ANSWERED:
        assert result.human_review_required
        assert result.sources == ()
    for source in result.sources:
        chunk = by_id[source.chunk_id]  # A1: so existe chunk aprovado carregado
        assert source.excerpt in chunk.text  # literal
        assert scope_matches(chunk, equipment_type)  # A2: escopo do tipo
        if chunk.high_risk:
            assert result.human_review_required
    if result.outcome is Outcome.ANSWERED and live.status in {"CRITICAL", "OFFLINE"}:
        assert result.human_review_required
    if result.provider is ProviderName.LLM:
        assert result.outcome is Outcome.ANSWERED
        body = result.answer.replace(NOTICE, "")
        cited = [by_id[s.chunk_id].text for s in result.sources]
        assert check_grounding(body, cited, [question, live.status]).ok
    if llm is None:
        assert result.provider is ProviderName.EXTRACTIVE
        assert result.fallback_used is False


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    question=QUESTIONS,
    equipment_type=st.sampled_from(TYPES),
    live=st.sampled_from(LIVE),
)
def test_invariants_hold_for_the_extractive_provider(
    question: str, equipment_type: str, live: LiveState
) -> None:
    _check_result(question, equipment_type, live, None)


CITATION_POOL = [c.chunk_id for c in load_knowledge_base(ROOT / "knowledge").chunks] + ["X#1"]
LLM_REPLIES = st.one_of(
    st.text(max_size=300),
    st.builds(
        lambda answer, cites: json.dumps({"answer": answer, "citations": cites}),
        st.one_of(
            st.lists(st.sampled_from(VOCAB), min_size=1, max_size=30).map(" ".join),
            st.text(min_size=1, max_size=300),
        ),
        st.lists(st.sampled_from(CITATION_POOL), min_size=0, max_size=3),
    ),
)


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    question=QUESTIONS,
    equipment_type=st.sampled_from(TYPES),
    live=st.sampled_from(LIVE),
    reply=LLM_REPLIES,
)
def test_invariants_hold_for_any_llm_output(
    question: str, equipment_type: str, live: LiveState, reply: str
) -> None:
    """Qualquer lixo que o LLM devolva: ou passa na fundamentacao ou cai no extrativo."""
    _check_result(question, equipment_type, live, reply)


def test_notice_is_never_empty_and_has_no_digits() -> None:
    assert NOTICE
    assert not re.search(r"\d", NOTICE)
