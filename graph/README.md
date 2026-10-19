# graph/ — índice auxiliar de conhecimento (Graphify)

> **O Git e [`docs/requirements/traceability.csv`](../docs/requirements/traceability.csv) são as fontes oficiais.**
> O grafo é um índice auxiliar para navegação e revisão; nada aqui altera specs, ADRs ou código.

## Ferramenta

| | |
|---|---|
| Nome / pacote | **Graphify** — pacote PyPI `graphifyy` (dois "y"), CLI `graphify` |
| Versão usada | 0.9.91 (instalada via `uv tool`; PyPI já lista 0.9.92) |
| Licença | Apache-2.0 |
| Documentação / repositório | https://docs.graphify.com · https://github.com/Graphify-Labs/graphify (PyPI) |
| Escopo de uso aqui | extração **AST local, sem LLM** (`graphify update .`): código Python + estrutura de Markdown |
| Não usado | extração semântica por LLM (exige chave de API/modelo), hooks no `settings.json`, MCP, exports Neo4j |

`graphify-out/` (HTML, `graph.json`, relatório) é **gerado e ignorado pelo Git**. Uma cópia do relatório
fica em [`docs/evidence/phase-1/graph-report.md`](../docs/evidence/phase-1/graph-report.md).

## Como usar

```powershell
graphify update .                         # (re)gera graphify-out/ — sem custo de API
graphify query "como o worker evita duplicatas"   # BFS no grafo
graphify path "MessageHandler" "PostgresRepository"
graphify explain "evaluate_status"
.\.venv\Scripts\python.exe scripts\trace_edges.py        # arestas VERIFICADAS a partir da matriz
.\.venv\Scripts\python.exe scripts\graph_crosscheck.py   # cruza matriz × grafo
```

## Duas camadas de arestas (nunca misturadas)

| Camada | Origem | Estado | Onde |
|---|---|---|---|
| **Verificadas** | `traceability.csv` (testada por `test_traceability.py`) | `VERIFIED` | [`mappings/traceability-edges.json`](mappings/traceability-edges.json) |
| **Do grafo** | Graphify (AST) | `EXTRACTED` (lida do código) ou `INFERRED` (inferida) | `graphify-out/graph.json` (não versionado) |

Vocabulário das arestas verificadas: `IMPLEMENTS` (código → REQ), `TESTED_BY`, `DECIDED_BY`, `SPECIFIED_BY`,
`FORMALIZED_BY`, `CONTRACTED_BY`, `SERVES` (REQ → outcome). `DEPENDS_ON` entre arquivos vem do grafo
(imports/chamadas), não da matriz.

## Cruzamento matriz × grafo

[`mappings/crosscheck.md`](mappings/crosscheck.md) pergunta ao grafo se o teste declarado na matriz tem
**caminho de dependência** até o código declarado (sem atravessar módulos externos como `pytest`, que
"conectariam tudo com tudo" — defeito encontrado e corrigido durante a Fase 1).

- `CONFIRMED (EXTRACTED)` — caminho feito só de arestas lidas do código.
- `CONFIRMED (INFERRED)` — o caminho usa ao menos uma aresta inferida: tratar como indício, não prova.
- `NOT CONFIRMED (black-box)` — teste de integração/E2E: exercita o sistema por HTTP/MQTT/Docker (esperado).
- `NOT CONFIRMED` — teste unitário sem ligação com o código declarado → **revisar a matriz**.

## O que o uso do grafo revelou
1. **Defeito na minha primeira versão do cruzamento:** ela "confirmava" 100% dos testes, porque o caminho passava por nós
   externos (`pytest`, `collections_abc`). Ao proibir esse atalho, o resultado passou a discriminar (teste de regressão
   em `tests/unit/repo/test_trace_edges.py`).
2. **Resultado atual** (Fase 2; ver `mappings/crosscheck.md`; o Graphify indexa Python **e C#**): 121 pares teste↔código confirmados
   (51 só com arestas extraídas, 70 com ao menos uma inferida), 24 caixa-preta (integração/E2E/performance, esperado) e
   **15 sem caminho no grafo**, em três famílias, todas explicáveis e mantidas na matriz:
   - **Acoplamento por dados, não por código** (10): `test_ar_fixtures.py` gera JSON que o núcleo C# lê; `QrRoundTripTests.cs`/`test_generate_qr.py` usam os QR
     de `scripts/generate_qr.py`. Análise estática não enxerga arquivo trocado entre linguagens.
   - **Dependência dinâmica / leitura de arquivo** (3): `test_trace_edges.py` carrega scripts por caminho (`importlib`); `test_hygiene.py` lê `.env.example`/`.gitignore`.
   - **Lacuna REAL e declarada** (2): `Assets/Scripts/QrScanner.cs` (cola Unity) consta como código do REQ-AR-001, mas **nenhum teste o toca** — coerente com
     "cola não compilada / AR não validada"; só o checklist em aparelho a cobrirá.
3. As confirmações "INFERRED" são **indício, não prova** — por isso a matriz continua a fonte oficial.
