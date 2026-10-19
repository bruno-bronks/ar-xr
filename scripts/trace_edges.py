"""Gera arestas VERIFICADAS de rastreabilidade a partir de docs/requirements/traceability.csv.

A matriz (e o Git) sao a fonte oficial; o grafo do Graphify e apenas indice auxiliar (plano §9).
Uso:  python scripts/trace_edges.py            # grava graph/mappings/traceability-edges.json
      python scripts/trace_edges.py --check    # falha se o arquivo estiver desatualizado
"""

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/requirements/traceability.csv"
OUTPUT = ROOT / "graph/mappings/traceability-edges.json"

# coluna da matriz -> (relacao, direcao). "out": REQ -> alvo ; "in": alvo -> REQ
RELATIONS: dict[str, tuple[str, str]] = {
    "spec": ("SPECIFIED_BY", "out"),
    "z_spec": ("FORMALIZED_BY", "out"),
    "adr": ("DECIDED_BY", "out"),
    "contract": ("CONTRACTED_BY", "out"),
    "tests": ("TESTED_BY", "out"),
    "code": ("IMPLEMENTS", "in"),  # arquivo de codigo IMPLEMENTS requisito
    "outcome_id": ("SERVES", "out"),
}


def _cells(value: str) -> list[str]:
    return [c.strip() for c in value.split("|") if c.strip()]


def _is_gap(cell: str) -> bool:
    return cell.startswith(("n/a:", "pending:"))


def build_edges(matrix: Path = MATRIX) -> list[dict[str, str]]:
    edges: set[tuple[str, str, str]] = set()
    with matrix.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            req = row["req_id"]
            for column, (relation, direction) in RELATIONS.items():
                for cell in _cells(row[column]):
                    if _is_gap(cell):
                        continue  # lacunas declaradas nao viram aresta
                    edges.add(
                        (req, relation, cell) if direction == "out" else (cell, relation, req)
                    )
    return [
        {
            "source": s,
            "relation": r,
            "target": t,
            "status": "VERIFIED",
            "origin": "traceability.csv",
        }
        for s, r, t in sorted(edges)
    ]


def render(edges: list[dict[str, str]]) -> str:
    document: dict[str, Any] = {
        "generated_from": "docs/requirements/traceability.csv",
        "note": "Arestas VERIFICADAS (a matriz e testada por tests/unit/repo/test_traceability.py).",
        "edge_count": len(edges),
        "edges": edges,
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    edges = build_edges()
    content = render(edges)
    if "--check" in argv:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            print(
                "graph/mappings/traceability-edges.json desatualizado; rode scripts/trace_edges.py"
            )
            return 1
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)}: {len(edges)} arestas verificadas")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
