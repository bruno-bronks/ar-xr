"""Politica de recusa e deteccao de injecao (SPEC-009, D-020). HEURISTICA, nao exaustiva.

A defesa principal e estrutural (nada executa acao; so texto aprovado sai). Estas regras apenas
recusam cedo os pedidos obviamente inseguros e removem instrucoes embutidas da base.
"""

import re
from enum import StrEnum

from spatial_assistant.text import fold

_INVISIBLE = re.compile("[" + "".join(map(chr, (*range(0x200B, 0x2010), 0x2060, 0xFEFF))) + "]")
_ACTION = (
    "desligar|ligar|religar|reiniciar|resetar|parar|acionar|abrir|fechar|ajustar|alterar|mudar|"
    "aumentar|reduzir|diminuir|ativar|desativar|desabilitar|habilitar|executar|iniciar|disparar"
)
_IMPERATIVE = (
    "desligue|ligue|religue|reinicie|resete|pare|acione|abra|feche|ajuste|altere|mude|aumente|"
    "reduza|diminua|ative|desative|desabilite|habilite|execute|inicie|dispare"
)
_PROTECTION = "alarme|alerta|limite|protecao|intertravamento|bloqueio|loto|trip"

_PHYSICAL = re.compile(
    rf"\b(?:{_IMPERATIVE})\b"
    rf"|\b(?:pode|consegue|poderia|vai|podes)\s+(?:{_ACTION})\b"
    rf"|\bquero\s+que\s+(?:voce\s+)?(?:{_IMPERATIVE}|{_ACTION})\b"
    r"|\b(?:faca|fazer)\s+(?:o\s+|um\s+)?(?:reset|desligamento|reinicio|bypass)\b"
)
_BYPASS = re.compile(
    rf"\b(?:ignore|ignora|contorne|burle|desative|silencie|desabilite|iniba)\b.{{0,40}}\b(?:{_PROTECTION})\b"
    rf"|\b(?:como|quero|preciso|gostaria\s+de|vou|queremos|precisamos)\b.{{0,30}}\b(?:ignorar|contornar|burlar|desativar|silenciar|desabilitar|inibir|bypassar)\b.{{0,40}}\b(?:{_PROTECTION})\b"
    r"|\bbypass\b"
    r"|\bsem\s+(?:bloquear|bloqueio|etiquet\w+|loto|desenergizar|desligar\s+a\s+energia)\b"
    r"|\b(?:aumente|aumentar|eleve|elevar|suba|subir)\s+(?:o\s+)?limite\b"
)
_INJECTION = re.compile(
    r"\b(?:ignore|ignora|ignorem|desconsidere|esqueca|disregard|forget|override)\s+(?:todas?\s+|all\s+)?"
    r"(?:as\s+|suas\s+|the\s+|your\s+|any\s+)?(?:previous\s+|prior\s+|above\s+|anteriores\s+)?"
    r"(?:instrucoes|instrucao|regras|ordens|instructions|rules|prompts?)\b"
    r"|\b(?:system\s+prompt|prompt\s+do\s+sistema|suas\s+instrucoes|your\s+instructions|developer\s+message)\b"
    r"|\b(?:voce\s+agora\s+e|you\s+are\s+now|finja\s+ser|aja\s+como|act\s+as|jailbreak|dan\s+mode)\b"
    r"|\b(?:you\s+are\s+now\s+dan)\b"
    r"|\b(?:revele|mostre|imprima|reveal|print|show)\b.{0,30}\b(?:prompt|instrucoes|chave|senha|token|api\s*key|secret)\b"
    r"|</?\s*(?:system|assistant|instructions?)\s*>|\[/?inst\]|<\|"
)


class RefusalReason(StrEnum):
    PHYSICAL_ACTION = "physical_action"
    SAFETY_BYPASS = "safety_bypass"
    PROMPT_INJECTION = "prompt_injection"


def contains_injection(text: str) -> bool:
    """Texto (de documento ou pergunta) com instrucao dirigida ao sistema."""
    return _INJECTION.search(_prepare(text)) is not None


def check_question(question: str) -> RefusalReason | None:
    """Motivo da recusa ou None. Ordem: injecao > contorno de seguranca > acao fisica."""
    folded = _prepare(question)
    if _INJECTION.search(folded):
        return RefusalReason.PROMPT_INJECTION
    if _BYPASS.search(folded):
        return RefusalReason.SAFETY_BYPASS
    if _PHYSICAL.search(folded):
        return RefusalReason.PHYSICAL_ACTION
    return None


def _prepare(text: str) -> str:
    # NFKC + minusculas + sem acentos; remove largura zero antes de casar (evasao por caractere invisivel)
    return _INVISIBLE.sub("", fold(text))
