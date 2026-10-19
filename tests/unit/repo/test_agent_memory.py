"""Memoria deterministica dos agentes (docs/agent/CURRENT_STATE.md) nao pode ficar OBSOLETA.

Plano §9 (Dreaming): memoria gerada nunca altera specs/ADRs/codigo sem revisao, e ate haver um
mecanismo aprovado a memoria e este arquivo versionado. Este teste e a defesa contra o problema
que o Dreaming resolve: entradas que citam arquivos/requisitos que nao existem mais.
Requisito: REQ-ENG-006.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "docs/agent/CURRENT_STATE.md"
TEXT = STATE.read_text("utf-8")
PATH_LIKE = re.compile(
    r"^[\w.\-/\\]+\.(md|py|yaml|yml|csv|json|tex|ps1|sh|toml|html|js|css|txt|conf|xml|png)$"
)


def _backticked() -> set[str]:
    return {m for m in re.findall(r"`([^`\n]+)`", TEXT) if PATH_LIKE.match(m) and "*" not in m}


def test_state_declares_date_branch_and_phase() -> None:
    assert re.search(r"Atualizado: \d{4}-\d{2}-\d{2}", TEXT)
    assert re.search(r"`feature/[\w.-]+`", TEXT), "o estado deve citar a branch de trabalho"
    assert re.search(r"Fase \d", TEXT)


def test_every_markdown_link_in_state_resolves() -> None:
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", TEXT):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        assert (STATE.parent / target).resolve().exists(), f"link quebrado: {target}"


def test_every_backticked_path_in_state_exists() -> None:
    missing = [p for p in sorted(_backticked()) if not (ROOT / p.replace("\\", "/")).exists()]

    assert not missing, f"memoria cita arquivos inexistentes: {missing}"


def test_requirements_and_decisions_cited_in_state_exist_in_the_catalog() -> None:
    catalog = (ROOT / "docs/requirements/requirements.md").read_text("utf-8")

    for ref in set(re.findall(r"\b(REQ-[A-Z]+-\d{3}|D-\d{3})\b", TEXT)):
        assert ref in catalog, f"{ref} citado em CURRENT_STATE.md mas ausente do catalogo"
