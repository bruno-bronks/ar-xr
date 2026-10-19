"""Cruza a matriz de rastreabilidade (FONTE OFICIAL) com o grafo de codigo do Graphify (INDICE AUXILIAR).

Para cada requisito com testes e codigo, pergunta ao grafo: "ha caminho de dependencia (imports/chamadas)
entre o arquivo de teste e o arquivo de codigo declarados?". O resultado NAO altera a matriz; ele aponta
(a) testes declarados que nao tocam o codigo declarado e (b) arestas que dependem de inferencia.

Pre-requisito:  graphify update .      (gera graphify-out/graph.json; sem LLM)
Uso:            python scripts/graph_crosscheck.py [--max-depth 4]
Saida:          graph/mappings/crosscheck.md
"""

import csv
import json
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "graphify-out/graph.json"
MATRIX = ROOT / "docs/requirements/traceability.csv"
REPORT = ROOT / "graph/mappings/crosscheck.md"

# testes que exercitam o sistema por HTTP/MQTT/Docker: a analise estatica nao enxerga essa ligacao
BLACK_BOX_PREFIXES = ("tests/integration/", "tests/e2e/", "tests/performance/")

# arestas que representam dependencia real de execucao (nao 'rationale_for', que e documentacao)
DEPENDENCY_RELATIONS = {
    "imports",
    "imports_from",
    "calls",
    "indirect_call",
    "uses",
    "references",
    "inherits",
}


def _cells(value: str) -> list[str]:
    return [
        c.strip() for c in value.split("|") if c.strip() and not c.startswith(("n/a:", "pending:"))
    ]


def load_graph(
    path: Path = GRAPH,
) -> tuple[dict[str, dict[str, str]], dict[str, list[tuple[str, str]]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in data["nodes"]}
    adjacency: dict[str, list[tuple[str, str]]] = {}
    contains: dict[str, list[str]] = {}
    for link in data["links"]:
        source, target = link["source"], link["target"]
        if link["relation"] == "contains":
            contains.setdefault(source, []).append(target)
            adjacency.setdefault(source, []).append((target, "EXTRACTED"))
            adjacency.setdefault(target, []).append((source, "EXTRACTED"))
        elif link["relation"] in DEPENDENCY_RELATIONS:
            confidence = link.get("confidence", "EXTRACTED")
            adjacency.setdefault(source, []).append((target, confidence))
            adjacency.setdefault(target, []).append((source, confidence))
    return nodes, adjacency


def nodes_of(nodes: dict[str, dict[str, str]], source_file: str) -> list[str]:
    return [
        i for i, n in nodes.items() if n.get("source_file", "").replace("\\", "/") == source_file
    ]


def connected(
    nodes: dict[str, dict[str, str]],
    adjacency: dict[str, list[tuple[str, str]]],
    test_file: str,
    code_file: str,
    max_depth: int,
) -> tuple[str, int] | None:
    """BFS entre os nos dos dois arquivos, SEM atravessar nos externos. (pior confianca, saltos) ou None."""
    starts, goals = nodes_of(nodes, test_file), set(nodes_of(nodes, code_file))
    if not starts or not goals:
        return None
    queue: deque[tuple[str, int, bool]] = deque((s, 0, False) for s in starts)
    seen = set(starts)
    while queue:
        node, depth, inferred = queue.popleft()
        if node in goals:
            return ("INFERRED" if inferred else "EXTRACTED", depth)
        if depth >= max_depth:
            continue
        for neighbour, confidence in adjacency.get(node, []):
            # nos externos (pytest, datetime, ...) conectam tudo com tudo: nao sao evidencia de cobertura
            if neighbour not in seen and nodes[neighbour].get("source_file"):
                seen.add(neighbour)
                queue.append((neighbour, depth + 1, inferred or confidence != "EXTRACTED"))
    return None


def main(argv: list[str]) -> int:
    max_depth = int(argv[argv.index("--max-depth") + 1]) if "--max-depth" in argv else 4
    if not GRAPH.exists():
        print("graphify-out/graph.json ausente; rode: graphify update .")
        return 2
    nodes, adjacency = load_graph()
    lines = [
        "# Cruzamento matriz x grafo (Graphify)",
        "",
        "> Gerado por `scripts/graph_crosscheck.py`. **Informativo**: a matriz e o Git continuam a fonte oficial;",
        "> o grafo e um indice auxiliar. `EXTRACTED` = aresta lida do codigo (AST); `INFERRED` = aresta inferida.",
        f"> Profundidade maxima de busca: {max_depth} saltos.",
        "",
        "| REQ | Teste | Codigo | Resultado | Saltos |",
        "|---|---|---|---|---|",
    ]
    counts = {
        "CONFIRMED (EXTRACTED)": 0,
        "CONFIRMED (INFERRED)": 0,
        "NOT CONFIRMED (black-box)": 0,
        "NOT CONFIRMED": 0,
        "NOT IN GRAPH": 0,
    }
    with MATRIX.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for test in (t for t in _cells(row["tests"]) if t.endswith(".py")):
                for code in (c for c in _cells(row["code"]) if c.endswith(".py")):
                    hops = "-"
                    if not nodes_of(nodes, test) or not nodes_of(nodes, code):
                        verdict = "NOT IN GRAPH"
                    else:
                        found = connected(nodes, adjacency, test, code, max_depth)
                        if found is not None:
                            verdict = f"CONFIRMED ({found[0]})"
                        elif test.startswith(BLACK_BOX_PREFIXES):
                            verdict = "NOT CONFIRMED (black-box)"
                        else:
                            verdict = "NOT CONFIRMED"
                        hops = "-" if found is None else str(found[1])
                    counts[verdict] += 1
                    lines.append(f"| {row['req_id']} | `{test}` | `{code}` | {verdict} | {hops} |")
    lines += ["", "## Resumo", ""] + [f"- {k}: **{v}**" for k, v in counts.items()]
    lines += [
        "",
        "- `NOT CONFIRMED (black-box)`: teste de integracao/E2E/performance; exercita o codigo por HTTP/MQTT/Docker,",
        "  o que a analise estatica nao enxerga (esperado).",
        "- `NOT CONFIRMED`: teste unitario/contrato SEM caminho de dependencia ate o codigo declarado -> revisar a",
        "  matriz (o teste declarado pode nao cobrir esse arquivo). Nao e erro automatico: o teste pode ler artefatos",
        "  (ex.: `.env.example`) em vez de importar o codigo.",
        "- `NOT IN GRAPH`: o Graphify nao indexa o arquivo (ex.: scripts fora do pacote analisado).",
        "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{REPORT.relative_to(ROOT)}: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
