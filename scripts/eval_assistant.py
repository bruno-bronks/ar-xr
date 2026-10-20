"""Avalia o assistente contra os conjuntos rotulados e grava o relatorio de evidencia.

Uso: python scripts/eval_assistant.py [--out docs/evidence/phase-3]
Requisitos: REQ-AI-007 (SPEC-009). Deterministico; nao usa rede nem LLM real.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "assistant" / "src"))

from spatial_assistant.evaluation import (  # noqa: E402
    GoldenReport,
    LlmCaseResult,
    run_golden,
    run_llm_cases,
)
from spatial_assistant.knowledge import load_knowledge_base  # noqa: E402

SETS = [
    ("conjunto de desenvolvimento (usado para ajustar)", "golden_set.json"),
    ("conjunto de reserva (escrito após o ajuste, medido uma vez)", "golden_holdout.json"),
]
CATEGORY_LABELS = {
    "answerable": "Respondíveis (doc correto citado)",
    "unanswerable": "Sem resposta na base (deve abster)",
    "wrong_equipment": "Outro tipo de equipamento (deve abster)",
    "physical_action": "Pedido de ação física (deve recusar)",
    "safety_bypass": "Contorno de segurança (deve recusar)",
    "injection": "Injeção de prompt (deve recusar)",
}
EXPECTED = {
    "good": "aceitar",
    "bad": "rejeitar",
    "known_limit": "rejeitar (mas o verificador lexical aceita)",
}


def _golden_section(report: GoldenReport) -> list[str]:
    lines = ["| Categoria | Correto / total |", "|---|---|"]
    for key, label in CATEGORY_LABELS.items():
        ok, total = report.rate(key)
        lines.append(
            f"| {label} | {ok} / {total} ({ok / total:.0%}) |" if total else f"| {label} | — |"
        )
    failures = [i for i in report.items if not i.correct]
    lines += ["", f"**Falhas ({len(failures)}):**", ""]
    lines += [
        f"- `{i.id}` [{i.category}] «{i.question}» → {i.outcome}: {i.detail}" for i in failures
    ]
    if not failures:
        lines.append("- nenhuma")
    return lines


def _llm_section(results: list[LlmCaseResult]) -> list[str]:
    def rate(kind: str, accepted: bool) -> tuple[int, int]:
        rows = [r for r in results if r.case.kind == kind]
        return sum(1 for r in rows if r.accepted == accepted), len(rows)

    bad_ok, bad_n = rate("bad", False)
    good_ok, good_n = rate("good", True)
    limit_accepted, limit_n = rate("known_limit", True)
    lines = [
        "| Medida | Resultado |",
        "|---|---|",
        f"| Saídas ruins **rejeitadas** (caem no extrativo) | {bad_ok} / {bad_n} |",
        f"| Saídas boas **aceitas** | {good_ok} / {good_n} |",
        f"| Inversões semânticas com as mesmas palavras **aceitas** (falso aceite, limite conhecido) | {limit_accepted} / {limit_n} |",
        "",
        "| Caso | Esperado | Aceito pelo verificador |",
        "|---|---|---|",
    ]
    lines += [
        f"| {r.case.name} | {EXPECTED[r.case.kind]} | {'sim' if r.accepted else 'não'} |"
        for r in results
    ]
    return lines


def render(sets: list[tuple[str, GoldenReport]], llm: list[LlmCaseResult], kb_chunks: int) -> str:
    total = sum(len(r.items) for _, r in sets)
    out = [
        "# Avaliação do assistente (Fase 3) — gerada por `scripts/eval_assistant.py`",
        "",
        "> **Escopo e limites.** Conjuntos escritos pelo próprio agente, com "
        f"{total} perguntas sobre uma base **fictícia** de {kb_chunks} trechos. "
        "Não são independentes nem estatisticamente representativos; medem este sistema nestes "
        "conjuntos, não a qualidade em produção. O LLM é **simulado** por saídas roteirizadas "
        "(nenhuma chamada real).",
        "",
    ]
    for label, report in sets:
        out += [
            f"## Provedor extrativo (padrão) — {label}",
            "",
            *_golden_section(report),
            "",
            "| Métrica estrutural | Valor |",
            "|---|---|",
            f"| Precisão de citação (excerto literal do trecho aprovado) | {report.citation_verbatim} / {report.citation_total} ({report.citation_precision:.0%}) |",
            f"| Taxa de alucinação (respostas `answered` com número/termo sem suporte nas fontes) | {report.answered_ungrounded} / {report.answered_total} ({report.hallucination_rate:.0%}) |",
            "",
        ]
    out += [
        "A taxa de alucinação do extrativo é 0 **por construção** (só devolve trechos literais); a "
        "medida existe como regressão. O ponto fraco real é a **recuperação lexical** (sinônimos, "
        "paráfrases e sobreposição acidental de palavras), visível nas falhas acima.",
        "",
        "## Verificador de fundamentação aplicado a saídas de LLM simuladas",
        "",
        *_llm_section(llm),
        "",
        "O verificador é **lexical**: barra números e termos sem suporte, citações inexistentes e "
        "formatos inválidos, mas **não** detecta uma frase que inverte o sentido usando as mesmas "
        "palavras. Por isso o LLM continua desligado por padrão e toda resposta de risco alto exige "
        "revisão humana.",
    ]
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "docs" / "evidence" / "phase-3"))
    args = parser.parse_args()

    logging.disable(logging.CRITICAL)  # saidas rejeitadas sao esperadas no cenario adversarial
    kb = load_knowledge_base(ROOT / "knowledge")
    sets: list[tuple[str, GoldenReport]] = []
    for label, name in SETS:
        items = json.loads((ROOT / "tests" / "evaluation" / name).read_text("utf-8"))["items"]
        sets.append((label, run_golden(kb, items)))
    llm = run_llm_cases(kb)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "eval-report.md").write_text(render(sets, llm, len(kb.chunks)), "utf-8", newline="\n")
    summary = {
        "sets": {
            label: {
                "items": len(report.items),
                "by_category": {k: list(report.rate(k)) for k in CATEGORY_LABELS},
                "citation_precision": report.citation_precision,
                "hallucination_rate": report.hallucination_rate,
            }
            for label, report in sets
        },
        "llm_cases": {r.case.name: r.accepted for r in llm},
    }
    (out / "eval-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", "utf-8", newline="\n"
    )
    for label, report in sets:
        print(
            label,
            json.dumps({k: list(report.rate(k)) for k in CATEGORY_LABELS}, ensure_ascii=False),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
