# CURRENT_STATE â€” memÃ³ria determinÃ­stica do projeto

Atualizado: 2026-10-19 Â· Branch: `feature/spatial-ai-foundation` (local; **sem push/merge**) Â· **Fase 1 concluÃ­da â€” aguardando aprovaÃ§Ã£o para a Fase 2.**

> Este arquivo Ã© validado por `tests/unit/repo/test_agent_memory.py` (links, caminhos e REQs citados precisam existir).
> Fases anteriores aprovadas pelo usuÃ¡rio: Fase 0 (decisÃµes D-001, D-003/D-004, ADR-0001, Z via CZT, Graphify/Dreaming "devem ser instalados e usados", inÃ­cio da Fase 1).

## O que existe (verificado por execuÃ§Ã£o)
- **Fluxo ponta a ponta:** `equipment-simulator` â†’ Mosquitto â†’ `telemetry-worker` (valida, deduplica, persiste, ack manual) â†’ PostgreSQL â†’ `api` (FastAPI, Bearer **demo**) â†’ painel 2D em `/panel/`.
- **ContÃªineres (Compose, 6 serviÃ§os):** `db`, `broker`, `migrate` (Alembic + seed dev), `api`, `worker`, `simulator`; portas sÃ³ em `127.0.0.1` (8088/55432/1883).
- **DomÃ­nio puro:** `packages/domain/src/spatial_domain/status.py` (SPEC-002), `packages/domain/src/spatial_domain/markers.py` (SPEC-003), `packages/domain/src/spatial_domain/telemetry.py` (parser estrito = JSON Schema, teste diferencial).
- **PersistÃªncia:** `packages/storage/` â€” modelos, migraÃ§Ã£o `0001_initial`, `PostgresRepository`, dublÃª em memÃ³ria, seed (EQ-001â€¦003 em org-a + sentinela EQ-B01 em org-b).
- **API:** equipamentos, telemetria, twin, alertas derivados, markers (rate limit 30/min), auditoria, CSP no painel â€” contrato em `specs/contracts/openapi.yaml` (8 operaÃ§Ãµes `implemented`; sÃ³ o assistente de IA segue `planned`).
- **Specs:** SPEC-001â€¦007; Z-002â€¦004 **typecheck no CZT** ([evidÃªncia](../evidence/phase-1/z-typecheck.txt)); ADR-0001/0002; threat model atualizado.
- **Ferramentas instaladas e usadas:** Eclipse Temurin JDK 21 + CZT 1.6-SNAPSHOT (SHA-256 verificados) e Graphify 0.9.91 â€” ver [tool-evaluation](../decisions/tool-evaluation.md) e [graph/README.md](../../graph/README.md).

## EvidÃªncias executadas (`docs/evidence/phase-1/`)
| EvidÃªncia | Resultado |
|---|---|
| `docs/evidence/phase-1/01-full-suite.txt` | pytest completo com pilha real + PostgreSQL real + E2E (Edge): **528 passed, 0 failed, 0 errors, 0 skipped** (448 s) |
| `docs/evidence/phase-1/02-compose-cold-start.txt` | `down -v` + `up --build --wait`: 5 serviÃ§os longos saudÃ¡veis + `migrate` concluÃ­do; build+up ≈ 214 s (imagens base em cache; inclui pip nas 3 imagens) |
| `docs/evidence/phase-1/latency.json` | publicarâ†’visÃ­vel na API: p50 0.1159 s Â· p95 0.2761 s Â· mÃ¡x 0.37 s (n=100; 1 mÃ¡quina, loopback) â€” meta < 3 s: **atendida neste ambiente** |
| `docs/evidence/phase-1/z-typecheck.txt` | 3 specs Z: `0 warnings and errors`; erro de tipo injetado Ã© rejeitado |
| `docs/evidence/phase-1/panel-critical-alert.png` e outras `panel-*` | capturas reais do painel (alerta crÃ­tico, offline, erro, 360 px) |
| `docs/evidence/phase-1/graph-report.md`, `docs/evidence/phase-1/graph-crosscheck.md` | Graphify: 1203 nós · 2752 arestas · 86% EXTRACTED; cruzamento: 57 confirmados, 24 caixa-preta, 3 sem caminho (explicados) |
| `docs/evidence/phase-1/03-resilience-worker-logs.txt` | logs reais do worker: falha de infraestrutura â†’ sem ack â†’ reconexÃ£o |

## Defeitos encontrados DURANTE a Fase 1 (e corrigidos)
1. Spec: leitura GOOD *antiga* sustentava o estado de outro sensor vivo â†’ leitura vÃ¡lida = GOOD âˆ§ fresca; `NORMAL` exige cobertura total do perfil (D-003, D-006).
2. Z escrito Ã  mÃ£o tinha erros de sintaxe/tipo â€” achados sÃ³ ao rodar o CZT (Fase 0 dizia "nÃ£o verificado").
3. DublÃª em memÃ³ria vs PostgreSQL divergiam (`rowcount` do upsert) â€” achado pela suÃ­te de contrato; uso de `RETURNING`.
4. `_find_panel_dir` quebrava na imagem Docker (poucos nÃ­veis de diretÃ³rio) â€” achado ao subir o contÃªiner; teste de regressÃ£o.
5. Backoff de reconexÃ£o do worker nunca crescia â€” extraÃ­do e testado (`next_backoff`).
6. **Painel:** resposta em voo da org A era desenhada apÃ³s trocar para a org B â€” achado pelo E2E; corrigido por *geraÃ§Ã£o*; teste detecta o defeito (verificado por mutaÃ§Ã£o).
7. Cruzamento matrizÃ—grafo "confirmava" tudo via nÃ³s externos â€” corrigido e testado.
8. Primeira mediÃ§Ã£o de latÃªncia incluÃ­a o handshake MQTT do teste (â‰ˆ1 s) â€” refeita com publicador persistente.
9. Fixture de limpeza de testes vazava bancos `spatial_t_*` apÃ³s queda de banco â€” `pool_pre_ping`.

## O que NÃƒO foi feito / nÃ£o estÃ¡ verificado
- **Nenhum teorema Z foi provado.** O CZT valida sintaxe e tipos; invariantes seguem validados por Hypothesis.
- **Dreaming NÃƒO foi instalado/usado:** Ã© um serviÃ§o de nuvem (Managed Agents) em *research preview*, com acesso sob solicitaÃ§Ã£o, API key e cobranÃ§a por tokens â€” nada para instalar localmente. Aguarda sua decisÃ£o (ver relatÃ³rio / [tool-evaluation](../decisions/tool-evaluation.md)).
- **CI nÃ£o executada** em runner GitHub (sem remoto). Gitleaks, Semgrep, Trivy, SBOM, Schemathesis: nÃ£o executados. `pip-audit` executado localmente nos 3 serviÃ§os.
- **Unity/AR, cÃ¢mera, QR por cÃ¢mera, celular fÃ­sico:** nada validado (Fase 2). O painel foi testado no **Edge desktop** e em viewport emulado de 360 px.
- **AutenticaÃ§Ã£o Ã© demo** (tokens pÃºblicos); OIDC e RBAC por papel nÃ£o existem. Mosquitto anÃ´nimo (dev). Rate limit/auditoria em memÃ³ria/log de processo Ãºnico.
- Python 3.12 nÃ£o obtido localmente (proxy TLS): suÃ­te local roda em 3.13; as imagens Docker (3.12) passaram nos testes de pilha.
- LatÃªncia: 1 mÃ¡quina, loopback, sem carga concorrente â€” **nÃ£o** representa produÃ§Ã£o. Sem teste de carga.
- Sem histÃ³rico persistente de alertas (derivados na consulta); sem retenÃ§Ã£o/particionamento de telemetria.
- EvidÃªncia "Red" (testes falhando antes do cÃ³digo) da Fase 1 **nÃ£o foi arquivada** como na Fase 0 (a ordem foi seguida, mas sÃ³ a Fase 0 tem o log).
- Warning conhecido: `StarletteDeprecationWarning` (TestClient com `httpx`).

## DecisÃµes pendentes de aprovaÃ§Ã£o
D-007â€¦D-011 em [requirements.md](../requirements/requirements.md) (skew +5 min; sentinela EQ-B01; auth demo; alertas derivados; pacote `storage`) e as opÃ§Ãµes do **Dreaming** no relatÃ³rio.

## PrÃ³ximo passo (somente apÃ³s aprovaÃ§Ã£o)
Fase 2 â€” AR Android: projeto Unity, leitura de QR (`GET /api/v1/spatial/markers/{id}`), overlay ancorado, estados offline e checklist em aparelho fÃ­sico. **Depende de hardware:** Android com ARCore + cabo/depuraÃ§Ã£o USB + Unity LTS instalado.

Gates locais (scripts/check.ps1, sem infraestrutura): ruff ✔ · format ✔ · mypy strict (76 arquivos) ✔ · 409 passed + 119 skipped (dependem de PostgreSQL/pilha) · pip-audit ×3 sem vulnerabilidades conhecidas — ver [04-local-gates.txt](../evidence/phase-1/04-local-gates.txt).
