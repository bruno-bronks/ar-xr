# Spatial AI Platform

Plataforma de IA espacial com duas verticais: **AR Maintenance AI** (primeiro MVP) e **HACC Spatial** (segunda integração, somente dados simulados). Plano completo: [SPATIAL_AI_ANTIGRAVITY_MASTER_PLAN.md](SPATIAL_AI_ANTIGRAVITY_MASTER_PLAN.md).

> **Estado: Fase 0 (Foundation) concluída, aguardando aprovação.** Existe: API com health checks, PostgreSQL, Mosquitto, specs, contratos, modelos de domínio testados, CI e matriz de rastreabilidade. **Não existe ainda:** simulador, worker, persistência de telemetria, painel, AR, IA, integração HACC. Detalhes e evidências em [docs/agent/CURRENT_STATE.md](docs/agent/CURRENT_STATE.md).

## Pré-requisitos
Git, Python ≥ 3.12 (testado com 3.13), Docker Desktop com Compose v2.

## Subir o ambiente (critério do marco)

PowerShell (Windows):
```powershell
docker compose up --build --wait      # db, broker e api ficam "healthy"
curl.exe -s http://127.0.0.1:8088/health/ready
docker compose down -v                # para e remove o volume do banco de dev
```

Shell (Linux/macOS/Git Bash):
```sh
docker compose up --build --wait
curl -s http://127.0.0.1:8088/health/ready
docker compose down -v
```

Resposta esperada: `{"status":"ready","checks":{"database":"ok","broker":"ok"}}`.

| Serviço | Host (somente 127.0.0.1) | Observação |
|---|---|---|
| API | `8088` | `GET /health/live`, `GET /health/ready`, `/docs` (OpenAPI) |
| PostgreSQL | `55432` | usuário/senha de **desenvolvimento** fictícios (ver `.env.example`) |
| Mosquitto | `1883` | anônimo — **apenas dev** (ver threat model S-02) |

Portas e senha podem ser trocadas copiando `.env.example` para `.env`.

## Rodar os testes e gates

PowerShell:
```powershell
.\scripts\dev-setup.ps1        # cria .venv e instala dependencias
.\scripts\check.ps1            # ruff, ruff format, mypy strict, pytest, pip-audit
.\scripts\smoke.ps1            # sobe o Compose e roda tests/integration contra o ambiente real
```

Shell:
```sh
./scripts/dev-setup.sh && ./scripts/check.sh && ./scripts/smoke.sh
```

Os testes de `tests/integration` só rodam com `BASE_URL` definido (o `smoke` faz isso); sem ele aparecem como **skipped**, nunca como aprovados.

## Mapa do repositório

| Caminho | Conteúdo |
|---|---|
| `docs/requirements/` | Catálogo de requisitos e `traceability.csv` |
| `docs/outcomes/metrics.md` | Outcomes e metas (propostas, não resultados) |
| `docs/architecture/`, `docs/adr/` | C4 (Mermaid), threat model STRIDE, ADR-0001 |
| `docs/decisions/tool-evaluation.md` | Inventário de ferramentas e limitações |
| `docs/evidence/phase-0/` | Saídas reais de testes e do Compose |
| `specs/functional/`, `specs/formal-z/` | Specs (SPEC-001…004) e Z Notation (sem typecheck) |
| `specs/contracts/`, `packages/contracts/` | OpenAPI 3.1, AsyncAPI 3, JSON Schema |
| `packages/domain/` | Modelos executáveis: avaliação de estado, resolução de marker |
| `services/api/` | API FastAPI + Dockerfile |
| `tests/` | `unit`, `contract`, `integration` |

Runbook de desenvolvimento: [docs/runbooks/local-dev.md](docs/runbooks/local-dev.md). Instruções para agentes: [AGENTS.md](AGENTS.md).
