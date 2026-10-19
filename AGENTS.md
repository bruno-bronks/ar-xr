# AGENTS.md — instruções para agentes de código neste repositório

Plano mestre: [SPATIAL_AI_ANTIGRAVITY_MASTER_PLAN.md](SPATIAL_AI_ANTIGRAVITY_MASTER_PLAN.md). Estado atual: [docs/agent/CURRENT_STATE.md](docs/agent/CURRENT_STATE.md) (leia primeiro; é a memória determinística do projeto).

## Regras inegociáveis
1. **Não avance de fase sem aprovação explícita do usuário.** Fase atual: ver `CURRENT_STATE.md`.
2. Não faça push, merge, instale ferramentas ambíguas (Graphify/Dreaming/etc.), conecte dados hospitalares reais nem contrate serviços cloud sem autorização.
3. **HACC é sistema independente:** nunca alterar seus repositórios nem compartilhar seu banco. Dados hospitalares aqui são **somente simulados**.
4. Nenhuma ação física automática; IA apenas assistiva, com fontes e incerteza.
5. Nunca imprimir/commitar segredos. `.env` é ignorado; só `.env.example` (valores fictícios).
6. Não declarar nada como "validado/verificado/passou" sem ter **executado** e registrado a evidência (`docs/evidence/`). Limitações vão para o relatório, não para debaixo do tapete.

## Fluxo Spec-Driven (por feature)
`OUTCOME → REQ → SPEC → Z/INVARIANT → ADR → CONTRACT → TEST → CODE → TELEMETRY`

1. Registrar/atualizar REQ em `docs/requirements/requirements.md` e a linha em `traceability.csv`.
2. Escrever SPEC em `specs/functional/` e, quando houver invariantes, Z em `specs/formal-z/`.
3. Declarar o contrato em `specs/contracts/` (marcar `x-implementation: planned` até existir).
4. **Testes primeiro** (Red → Green → Refactor); todo teste cita o `REQ-…` na docstring.
5. Implementar, instrumentar (correlation ID, logs), rodar os gates, atualizar `CURRENT_STATE.md`.

`tests/unit/repo/test_traceability.py` quebra o build se a matriz mentir (caminho inexistente, REQ sem linha, teste que não cita o REQ).

## Comandos
| Ação | PowerShell | Shell |
|---|---|---|
| Setup | `.\scripts\dev-setup.ps1` | `./scripts/dev-setup.sh` |
| Gates locais (ruff, mypy strict, pytest sem Docker, pip-audit x3) | `.\scripts\check.ps1` | `./scripts/check.sh` |
| Pilha real: integração + latência + E2E (`-Quick`/`--quick` = só smoke) | `.\scripts\smoke.ps1` | `./scripts/smoke.sh` |
| Typecheck das specs Z (CZT) | `.\scripts\verify-z.ps1` | `./scripts/verify-z.sh` |
| Regenerar arestas verificadas / cruzar com o grafo | `python scripts/trace_edges.py` · `graphify update .` · `python scripts/graph_crosscheck.py` | idem |

## Convenções
- Identificadores de código/APIs em **inglês**; documentos de negócio em **português**.
- `packages/domain` é puro (sem I/O/frameworks). A API compõe em `services/api/app/main.py`.
- Sem abstrações prematuras: Strategy/Repository/Adapter só quando houver segunda implementação real ou persistência real (ver `docs/architecture/components.md`).
- Valide entradas externas (QR, MQTT, HTTP) como não confiáveis; mensagens de erro não vazam detalhes internos.
- Ruff (`E,F,I,UP,B,SIM,S,C4,PT,RUF`, linha 100) e mypy `strict` precisam passar.
- Verificação formal: as specs Z **passam parse+typecheck no CZT** (`verify-z`), mas **nenhum teorema foi provado**. Nunca escrever "provado"; os invariantes são checados por Hypothesis.
- Testes que mexem na pilha (`tests/integration`, `e2e`, `performance`) **param/reiniciam** simulator/db/broker do Compose; rodar um por vez.
- Gráfico de conhecimento: Graphify é **índice auxiliar**; a matriz `traceability.csv` e o Git são a fonte oficial. `graphify-out/` não é versionado.
- Memória de agentes: `docs/agent/CURRENT_STATE.md` (validada por `test_agent_memory.py`). **Dreaming ainda não adotado** (serviço de nuvem pago/restrito); saída de qualquer mecanismo de memória entra só por PR.

## Ambiente conhecido (Windows)
- Portas do host: API `8088`, PostgreSQL `55432`, MQTT `1883` (5432/8000 já ocupadas por outros projetos).
- Auth da API é **demo** (tokens fictícios em `app/auth.py`); `ENVIRONMENT=production` + demo = a API não inicia.
- TLS corporativo interceptado: `uv` não baixa pacotes; use `pip` (usa o repositório de certificados do sistema). **Não desabilite verificação de certificado.**
- Heredocs bash com `\` e aspas aninhadas são frágeis; prefira editar arquivos com as ferramentas de edição.
