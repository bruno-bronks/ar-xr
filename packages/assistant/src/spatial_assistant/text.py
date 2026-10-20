"""Normalizacao e tokenizacao de texto (SPEC-009). Funcoes puras."""

import re
import unicodedata

_STOPWORDS = frozenset(
    """a o as os um uma uns umas de do da dos das em no na nos nas por pelo pela pelos pelas para
    pra com sem sob sobre entre ate ao aos e ou mas que qual quais quem como quando onde porque
    porquê se so ja nao sim ha ser sao foi esta estao estou esta estamos esse essa isso isto este
    aquele aquela meu minha seu sua eu voce me te lhe nos eles elas ele ela tem ter foi era fica
    ficar pode podem deve devo devem faz fazer feito mais muito muita bem tambem apos antes
    entao pois cada todo toda todos todas the of and to is it""".split()  # noqa: SIM905
)
_TOKEN = re.compile(r"[a-z0-9]+")
_CONTROL_CODES = (
    *range(0x00, 0x09),
    *range(0x0B, 0x20),
    *range(0x7F, 0xA0),
    *range(0x200B, 0x2010),
    *range(0x2028, 0x202F),
    *range(0x2060, 0x2065),
    0xFEFF,
)  # controles C0/C1 (preserva tab e quebra de linha), largura zero e separadores Unicode
_CONTROL = re.compile("[" + "".join(re.escape(chr(c)) for c in _CONTROL_CODES) + "]")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def normalize_text(text: str) -> str:
    """NFKC, remove controles/largura zero e colapsa espacos."""
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def fold(text: str) -> str:
    """Minusculas e sem acentos (NFKC antes, para neutralizar variantes tipograficas)."""
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", text).lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def prep(text: str) -> str:
    """Forma comparavel de um texto: dobrado (sem acento/caixa) e sem controles/largura zero."""
    return _CONTROL.sub("", fold(text))


def _stem(token: str) -> str:
    if len(token) > 3 and token.endswith("s"):
        token = token[:-1]
    return token[:6]


def terms(text: str) -> list[str]:
    """Termos de conteudo (sem stopwords), com radical por prefixo; mantem a ordem e repeticoes."""
    return [_stem(t) for t in _TOKEN.findall(prep(text)) if t not in _STOPWORDS]


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Intervalos [inicio, fim) das frases em `text` (cada uma e substring literal)."""
    spans: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_END.finditer(text):
        spans.append((start, match.start()))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return [(a, b) for a, b in spans if text[a:b].strip()]
