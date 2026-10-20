"""Verificacao de fundamentacao (SPEC-009, REQ-AI-003/005). LEXICAL, nao semantica.

Uma resposta so e aceita se cada numero aparece nos trechos citados (ou na pergunta/contexto) e se
quase todos os termos de conteudo tem suporte. Parafrase enganosa com as mesmas palavras passa:
limite declarado na SPEC-009.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from spatial_assistant.text import prep, terms

MAX_ANSWER_CHARS = 1500
MAX_UNSUPPORTED_RATIO = 0.15
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_MARKERS = re.compile(r"\[\d+\]|[A-Za-z0-9._-]+#\d+")


@dataclass(frozen=True)
class Grounding:
    ok: bool
    unsupported_numbers: tuple[str, ...]
    unsupported_ratio: float


def is_verbatim(excerpt: str, chunk_text: str) -> bool:
    """O trecho exibido e uma subcadeia contigua e nao vazia do trecho aprovado."""
    return bool(excerpt.strip()) and excerpt in chunk_text


def check_grounding(
    answer: str, cited_texts: Sequence[str], context: Sequence[str] = ()
) -> Grounding:
    body = _MARKERS.sub(" ", answer)
    if not body.strip() or len(answer) > MAX_ANSWER_CHARS:
        return Grounding(False, (), 1.0)

    support = [*cited_texts, *context]
    supported_numbers = {n for text in support for n in _numbers(text)}
    unsupported_numbers = tuple(
        dict.fromkeys(n for n in _numbers(body) if n not in supported_numbers)
    )

    supported_terms = {t for text in support for t in terms(text)}
    content = {t for t in terms(body) if len(t) >= 4 and not t.isdigit()}
    unsupported = content - supported_terms
    ratio = len(unsupported) / len(content) if content else 0.0
    return Grounding(
        ok=not unsupported_numbers and ratio <= MAX_UNSUPPORTED_RATIO,
        unsupported_numbers=unsupported_numbers,
        unsupported_ratio=ratio,
    )


def _numbers(text: str) -> list[str]:
    return [n.replace(",", ".") for n in _NUMBER.findall(prep(text))]
