"""SPEC-009 · REQ-AI-003: recuperacao lexical restrita ao tipo do equipamento, com cobertura."""

import pytest
from spatial_assistant.knowledge import Chunk
from spatial_assistant.retrieval import retrieve
from spatial_assistant.text import fold, normalize_text, terms


def _chunk(cid: str, text: str, types: tuple[str, ...] = ("*",), section: str = "Secao") -> Chunk:
    return Chunk(
        chunk_id=cid,
        document_id=cid.split("#")[0],
        title="T",
        section=section,
        version="1.0",
        text=text,
        equipment_types=frozenset(types),
        high_risk=False,
    )


def test_normalize_text_removes_control_chars_and_collapses_whitespace() -> None:
    assert normalize_text("  Ola\x00\x07   mundo\n\n\tx  ") == "Ola mundo x"
    assert normalize_text("ﬁnal") == "final"  # NFKC


def test_fold_removes_accents_and_case() -> None:
    assert fold("VIBRAÇÃO Elétrica") == "vibracao eletrica"


def test_terms_drop_stopwords_and_stem_plurals_and_variants() -> None:
    assert terms("Por que a temperatura do compressor está alta?") == [
        "temper",
        "compre",
        "alta",
    ]
    assert terms("temperaturas") == terms("temperatura")
    assert terms("vibrações") == terms("vibração")
    assert "85" in terms("limite de 85 graus")


def test_retrieval_ranks_by_relevance_and_reports_coverage() -> None:
    chunks = [
        _chunk("D#1", "Vibração alta indica desalinhamento do eixo.", section="Vibração"),
        _chunk("D#2", "A lubrificação dos rolamentos segue o plano.", section="Lubrificação"),
    ]

    hits = retrieve(chunks, "A vibração está alta?", "qualquer", limit=3)

    assert hits[0].chunk.chunk_id == "D#1"
    assert hits[0].coverage == pytest.approx(1.0)
    assert all(h.coverage > 0 for h in hits)


def test_retrieval_is_restricted_to_the_equipment_type_or_wildcard() -> None:
    chunks = [
        _chunk("P#1", "Cavitação na bomba causa ruído.", types=("bomba centrifuga",)),
        _chunk("M#1", "Cavitação não se aplica ao motor.", types=("motor eletrico",)),
        _chunk("G#1", "Cavitação: consulte o especialista.", types=("*",)),
    ]

    ids = [h.chunk.chunk_id for h in retrieve(chunks, "cavitação", "Bomba centrífuga")]

    assert set(ids) == {"P#1", "G#1"}


def test_retrieval_returns_nothing_for_unrelated_or_empty_queries() -> None:
    chunks = [_chunk("D#1", "Vibração alta indica desalinhamento.")]

    assert retrieve(chunks, "capital da França", "x") == []
    assert retrieve(chunks, "   ?!  ", "x") == []
    assert retrieve([], "vibração", "x") == []


def test_retrieval_is_deterministic_with_ties_broken_by_chunk_id() -> None:
    chunks = [_chunk("B#1", "vibração alta"), _chunk("A#1", "vibração alta")]

    first = [h.chunk.chunk_id for h in retrieve(chunks, "vibração", "x")]
    second = [h.chunk.chunk_id for h in retrieve(list(reversed(chunks)), "vibração", "x")]

    assert first == second == ["A#1", "B#1"]


def test_limit_caps_the_number_of_hits() -> None:
    chunks = [_chunk(f"D#{i}", "vibração alta") for i in range(1, 8)]

    assert len(retrieve(chunks, "vibração", "x", limit=3)) == 3


def test_stems_do_not_collide_on_unrelated_words_sharing_a_five_letter_prefix() -> None:
    """Achado da 1a avaliacao: 'partida' casava com 'participa' (prefixo de 5)."""
    assert terms("partida") != terms("participa")
    assert terms("compressor") != terms("comprimido")


def test_hit_reports_topic_matches_excluding_the_equipment_name_terms() -> None:
    """Citar so o nome do equipamento ('motor') nao e evidencia sobre o ASSUNTO da pergunta."""
    chunks = [_chunk("M#1", "O motor deve ser lubrificado.", types=("motor eletrico",))]

    name_only = retrieve(chunks, "Quem é o fabricante do motor?", "Motor eletrico")
    topical = retrieve(chunks, "Como lubrificar o motor?", "Motor eletrico")

    assert name_only[0].topic_matches == 0
    assert topical[0].topic_matches == 1
