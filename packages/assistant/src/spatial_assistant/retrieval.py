"""Recuperacao lexical (BM25 + cobertura) restrita ao tipo de equipamento (SPEC-009, D-021)."""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from spatial_assistant.knowledge import Chunk
from spatial_assistant.text import fold, terms

_K1 = 1.5
_B = 0.75


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float  # BM25 (desempate)
    coverage: float  # fracao dos termos distintos da pergunta presentes no trecho
    topic_matches: int  # termos casados que NAO sao o nome do equipamento (evidencia do assunto)


def scope_matches(chunk: Chunk, equipment_type: str) -> bool:
    return "*" in chunk.equipment_types or fold(equipment_type).strip() in chunk.equipment_types


def retrieve(chunks: Sequence[Chunk], query: str, equipment_type: str, limit: int = 3) -> list[Hit]:
    scoped = [c for c in chunks if scope_matches(c, equipment_type)]
    query_terms = list(dict.fromkeys(terms(query)))
    equipment_terms = set(terms(equipment_type))
    if not scoped or not query_terms:
        return []

    docs = {c.chunk_id: Counter(terms(f"{c.section} {c.text}")) for c in scoped}
    lengths = {cid: sum(tf.values()) for cid, tf in docs.items()}
    avg_len = (sum(lengths.values()) / len(docs)) or 1.0
    df = {t: sum(1 for tf in docs.values() if t in tf) for t in query_terms}

    hits: list[Hit] = []
    for chunk in scoped:
        tf = docs[chunk.chunk_id]
        matched = [t for t in query_terms if t in tf]
        if not matched:
            continue
        score = 0.0
        for t in matched:
            idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
            norm = tf[t] + _K1 * (1 - _B + _B * lengths[chunk.chunk_id] / avg_len)
            score += idf * tf[t] * (_K1 + 1) / norm
        topic = sum(1 for t in matched if t not in equipment_terms)
        hits.append(Hit(chunk, score, len(matched) / len(query_terms), topic))

    hits.sort(key=lambda h: (-h.coverage, -h.score, h.chunk.chunk_id))
    return hits[:limit]
