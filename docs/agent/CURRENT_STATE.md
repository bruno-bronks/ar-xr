# CURRENT_STATE — memória determinística do projeto

Atualizado: 2026-10-19 · Branch: `feature/spatial-ai-foundation` (local; **sem push/merge**) · **Fase 0 concluída — aguardando aprovação para a Fase 1.**

## O que existe (verificado)
- API FastAPI (`services/api`): `GET /health/live`, `GET /health/ready`, correlation ID (`X-Correlation-ID`), logs JSON, config 12-factor com `SecretStr`.
- Compose: `db` (postgres:16.4-alpine), `broker` (eclipse-mosquitto:2.0.18), `api`; healthchecks; portas só em `127.0.0.1` (8088/55432/1883).
- Domínio puro (`packages/domain`): `evaluate_status` (SPEC-002) e `Registry.resolve` (SPEC-003) como modelos executáveis das specs.
- Contratos: OpenAPI 3.1 (9 operações do MVP; só 2 `implemented`), AsyncAPI 3 + JSON Schema do evento de telemetria.
- Docs: visão, outcomes, REQ (13), SPEC-001…004, Z-002…004, ADR-0001, C4 (3 níveis), threat model STRIDE, avaliação de ferramentas, runbook.
- CI (`.github/workflows/ci.yml`): quality, secrets (gitleaks), compose-smoke.

## Evidências executadas (ver `docs/evidence/phase-0/`)
| Evidência | Resultado |
|---|---|
| `01-red.txt` | 6 módulos de teste falharam na coleta antes da implementação (TDD Red) |
| `02-green-local-gates.txt` | ruff ✔ · ruff format ✔ · mypy strict (26 arquivos) ✔ · pytest **156 passed, 4 skipped** · pip-audit: nenhuma vulnerabilidade conhecida |
| `03-compose-integration.txt` | `down -v` → `compose up --build` do zero: 3 serviços `healthy`; 4/4 testes de integração passaram (~22 s com imagens em cache) |
| `04-dependency-degradation.txt` | broker parado → `live=200`, `ready=503` (broker=fail); db parado → `ready=503` (database=fail); recuperação automática → 200; senha de dev ausente dos logs |

Distribuição dos 156 testes: api 39 · domínio 55 (inclui Hypothesis: I1–I7 e M1–M2) · repo (rastreabilidade/higiene) 20 · contratos 42. Os 4 *skipped* são os de integração, que só rodam com `BASE_URL`.

## O que NÃO foi feito / não está verificado
- **Z Notation não foi typecheckada nem provada** (sem Java/fuzz/CZT/LaTeX). Invariantes validados só por property-based tests — isso não é prova formal.
- CI **não executada** em runner GitHub (sem remoto). Gitleaks, Semgrep, Trivy, SBOM CycloneDX, Schemathesis, Playwright: **não executados/instalados**.
- Python 3.12 não obtido localmente (TLS corporativo); testes rodaram em 3.13. A imagem Docker usa 3.12 e a suíte de integração passou contra ela, mas a suíte unitária **não** foi rodada em 3.12.
- Alembic/migrações: não criadas (não há tabelas na Fase 0).
- Idempotência, ordenação, reconexão MQTT, falha de banco no worker, evento duplicado/fora de ordem: apenas **especificados** (Z-004/SPEC-004); implementação e testes são da Fase 1.
- Sem autenticação/autorização nos endpoints (só health existe). Mosquitto anônimo (dev, loopback).
- Nenhuma métrica de desempenho medida (OUT-MNT-002 p95 < 3 s: **não medido**).
- Warning conhecido nos testes: `StarletteDeprecationWarning` (TestClient com `httpx` → sugere `httpx2`); inofensivo hoje, revisar ao atualizar dependências.

## Decisões pendentes de aprovação
Ver [requirements.md](../requirements/requirements.md#decisões-de-default-explícitas-precisam-de-aprovação) (D-001…D-006) e o relatório final. Resumo: limiar estrito `>`; leitura válida = GOOD ∧ fresca; `NORMAL` exige cobertura total do perfil; portas alternativas; raiz do repo = `AR_XR`.

## Próximo passo (somente após aprovação)
Fase 1 mínima: seeds de 3 equipamentos, simulador MQTT, `telemetry-worker` (dedup por `(source,event_id)`), persistência + Alembic, endpoints `equipment/*`, autenticação demo, painel web 2D com alerta. Escrever specs/testes antes (cenários: duplicado, fora de ordem, offline, limiar exato, reconexão, falha de banco).
