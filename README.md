# Spatial AI Platform

Plataforma de IA espacial com duas verticais: **AR Maintenance AI** (primeiro MVP) e **HACC Spatial** (segunda integração, somente dados simulados). Plano completo: [SPATIAL_AI_ANTIGRAVITY_MASTER_PLAN.md](SPATIAL_AI_ANTIGRAVITY_MASTER_PLAN.md).

> **Estado: Fases 0–1 em `main`. Fase 2 (AR Android) PARCIAL no PR #2 (rascunho): núcleo C# testado na CI; cola Unity NÃO compilada; AR NÃO validada em aparelho (falta hardware).**
> Fase 1 (vertical industrial, sem AR nativa): Fluxo real e testado:
> simulador → Mosquitto → worker (valida, deduplica, persiste) → PostgreSQL → API autenticada → **painel web 2D**.
> **Fase 3 (IA assistiva):** `POST /api/v1/assistant/questions` responde com **trechos literais de documentos aprovados**, fontes, confiança e revisão humana; recusa pedidos de ação física/contorno de segurança; funciona **offline** (LLM é opcional e desligado). A base de conhecimento é **fictícia**. Limites medidos: [docs/evidence/phase-3/eval-report.md](docs/evidence/phase-3/eval-report.md).
> **Não existe ainda:** HACC (Fase 4), visão computacional/IoT real (Fase 5), cloud (Fase 6). A AR (Fase 2) não foi validada em aparelho.
> Autenticação é **demo** (tokens fictícios; a API recusa iniciar assim em produção). Detalhes, evidências e limitações: [docs/agent/CURRENT_STATE.md](docs/agent/CURRENT_STATE.md).

## Pré-requisitos
Git, Python ≥ 3.12 (testado com 3.13), Docker Desktop com Compose v2. Opcionais: Microsoft Edge (testes E2E), JDK + CZT (typecheck das specs Z).

## Demonstração (critério do marco)

PowerShell (Windows):
```powershell
docker compose up --build --wait      # db, broker, migrate, api, worker, simulator
start http://127.0.0.1:8088/panel/    # painel 2D: escolha "Organização A (demo)"
curl.exe -s -H "Authorization: Bearer demo-operator-a" http://127.0.0.1:8088/api/v1/equipment
docker compose down -v                # para e remove o volume do banco de dev
```

Shell (Linux/macOS/Git Bash):
```sh
docker compose up --build --wait
curl -s -H "Authorization: Bearer demo-operator-a" http://127.0.0.1:8088/api/v1/equipment
docker compose down -v
```

O simulador percorre um ciclo de ~4 min: **EQ-001** estável (`NORMAL`); **EQ-002** sobe de `NORMAL` → `WARNING` → `CRITICAL` e volta (gera alertas); **EQ-003** silencia e vira `OFFLINE`. Reenvia duplicatas de propósito (o worker as descarta).

| Serviço | Host (somente 127.0.0.1) | Observação |
|---|---|---|
| API + painel | `8088` | `/panel/` · `/api/v1/*` (Bearer demo) · `/health/*` · `/docs` (fora de produção) |
| PostgreSQL | `55432` | usuário/senha de **desenvolvimento** fictícios (ver `.env.example`) |
| Mosquitto | `1883` | anônimo — **apenas dev** (ver threat model S-02) |

Assistente (extrativo, sem custo):
```powershell
$body = '{"equipment_id":"EQ-001","question":"Por que a temperatura do compressor está alta?"}'
curl.exe -s -X POST -H "Authorization: Bearer demo-operator-a" -H "Content-Type: application/json" -d $body http://127.0.0.1:8088/api/v1/assistant/questions
```

Tokens demo: `demo-operator-a` (org-a: EQ-001…003) e `demo-operator-b` (org-b: EQ-B01, sentinela de isolamento). QR de teste: `QR-EQ-001/002/003` via `GET /api/v1/spatial/markers/{id}`.

## Testes e gates

```powershell
.\scripts\dev-setup.ps1        # cria .venv e instala dependências
.\scripts\check.ps1            # ruff, ruff format, mypy strict, pytest (sem Docker), pip-audit x3
.\scripts\smoke.ps1            # sobe o Compose e roda integração + latência + E2E contra a pilha REAL
.\scripts\verify-z.ps1         # parse + typecheck das specs Z com o CZT (exige JDK+CZT)
```
```sh
./scripts/dev-setup.sh && ./scripts/check.sh && ./scripts/smoke.sh   # equivalentes
```

Sem `TEST_DATABASE_URL`/`BASE_URL` os testes que precisam de PostgreSQL/pilha aparecem como **skipped** (nunca como aprovados) — ver [runbook](docs/runbooks/local-dev.md).

## Mapa do repositório

| Caminho | Conteúdo |
|---|---|
| `docs/requirements/` | Catálogo de requisitos (REQ, decisões D-001…011) e `traceability.csv` |
| `docs/outcomes/metrics.md` | Outcomes, metas e resultados medidos (com metodologia) |
| `docs/architecture/`, `docs/adr/` | C4 (Mermaid), threat model STRIDE, ADR-0001/0002 |
| `docs/decisions/tool-evaluation.md` | Ferramentas (JDK, CZT, Graphify), Dreaming e limitações |
| `docs/evidence/phase-0/`, `phase-1/` | Saídas reais de testes, Compose, latência, capturas do painel, typecheck Z |
| `specs/functional/` | SPEC-001…008 |
| `specs/formal-z/` | Z-002…004 (**typecheck CZT ok; teoremas não provados**) |
| `specs/contracts/`, `packages/contracts/` | OpenAPI 3.1, AsyncAPI 3, JSON Schema |
| `packages/domain/` | Domínio puro: avaliação de estado, marker, parser de telemetria |
| `packages/storage/` | Modelos, repositórios (Postgres + dublê), migrações Alembic, seed |
| `packages/common/` | Logging JSON com correlation ID |
| `services/api/` · `telemetry-worker/` · `equipment-simulator/` | Os três deployables |
| `clients/web-fallback/` | Painel web 2D (HTML/JS/CSS estáticos) |
| `clients/ar-unity/` | Cliente AR (Fase 2): núcleo C# testado + cola Unity **não compilada** — ver o README da pasta |
| `tests/csharp/` | xUnit do núcleo C# (rodam na **CI**; o proxy do dev bloqueia NuGet) e fixtures geradas pela API real |
| `graph/` | Índice auxiliar (Graphify): arestas verificadas e cruzamento |
| `tests/` | `unit`, `contract`, `integration`, `e2e`, `performance` |

Instruções para agentes: [AGENTS.md](AGENTS.md).
