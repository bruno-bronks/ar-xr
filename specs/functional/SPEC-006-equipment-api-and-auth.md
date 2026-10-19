# SPEC-006 — API de equipamentos, twin, alertas, markers e autenticação demo

Requisitos: REQ-MNT-001, REQ-MNT-002, REQ-MNT-006, REQ-SEC-003, REQ-SEC-004 · Contrato: [`openapi.yaml`](../contracts/openapi.yaml) · Modelos: SPEC-002, SPEC-003.

## Autenticação e autorização
- Cabeçalho `Authorization: Bearer <token>`. Ausente/inválido ⇒ **401** `{"detail":"not authenticated"}` + `WWW-Authenticate: Bearer`.
- `AUTH_MODE=demo` (padrão fora de produção): tokens fictícios fixos (D-009): `demo-operator-a` → (`user-a`, `org-a`); `demo-operator-b` → (`user-b`, `org-b`).
- **Fail closed:** `ENVIRONMENT=production` com `AUTH_MODE=demo` ⇒ a aplicação **não inicia**. `AUTH_MODE=oidc` ⇒ não inicia (não implementado; exige IdP aprovado).
- **Isolamento por organização:** todo acesso filtra por `org_id` do principal. Recurso de outra organização e recurso inexistente ⇒ **404 idêntico** `{"detail":"not found"}` (corpo e cabeçalhos iguais, exceto correlation ID).
- IDs de path validados (`^[A-Za-z0-9._:-]{1,64}$`; marker até 128); inválido ⇒ 404 (mesmo corpo), nunca 500 nem reflexo do valor.

## Endpoints (todos `GET`, exceto os planejados)
| Endpoint | Resposta | Regras |
|---|---|---|
| `/api/v1/equipment` | lista `Equipment` (com `status`) da organização | status por SPEC-002 com `now` do servidor |
| `/api/v1/equipment/{id}` | `Equipment` | 404 uniforme |
| `/api/v1/equipment/{id}/telemetry/latest` | lista `TelemetryReading` (uma por sensor) | vazia se sem leituras (200) |
| `/api/v1/equipment/{id}/twin` | `Twin`: `status`, `evaluated_at`, `offline_after_seconds`, `sensors[]` (valor, unidade, limites, `observed_at`, `quality`, `valid`) | `valid` = GOOD ∧ fresca |
| `/api/v1/equipment/{id}/alerts` | lista `Alert` derivada do twin (D-010) | ver abaixo |
| `/api/v1/spatial/markers/{marker_id}` | `Equipment` | SPEC-003; rate limit; 404 uniforme |
| `/api/v1/assistant/questions` | — | **planejado (Fase 3)**: permanece sem rota |

### Alertas determinísticos (regra, não IA)
Para cada leitura **válida**: `value > crit` ⇒ `CRITICAL` (`rule = "<sensor>>crit"`); senão `value > warn` ⇒ `WARNING` (`rule = "<sensor>>warn"`). Equipamento `OFFLINE` ⇒ um alerta `OFFLINE` (`rule = "offline"`). `UNKNOWN`/`NORMAL` não geram alerta. `raised_at` = `observed_at` da leitura causadora (offline: último `observed_at` + `offline_after`).

## Auditoria e rate limit (REQ-SEC-004)
- Log `app.audit` por acesso a recurso: `user_id`, `org_id`, `action`, `resource`, `outcome` (`allowed`/`not_found`), `correlation_id`. Nunca token nem corpo.
- Markers: máximo **30 resoluções/min por principal** (janela fixa de 60 s); excedido ⇒ **429** `{"detail":"rate limit exceeded"}` + `Retry-After`. Limitador em memória (processo único; ver riscos).

## Painel web 2D
Servido em `/panel/` (estático, mesma origem, sem dependências externas). Detalhes na SPEC-007.

## Critérios de aceitação
| # | Critério | Onde é testado |
|---|---|---|
| A1 | Toda rota `/api/v1/*` exige autenticação (401 uniforme); `health` é público | `tests/unit/api/test_equipment_api.py` |
| A2 | Recurso de outra organização ≡ inexistente (404 idêntico, em todos os sub-recursos); IDs malformados nunca são refletidos | idem |
| A3 | Twin segue SPEC-002 (limiar estrito, `UNKNOWN` sem dado, `OFFLINE` por passagem de tempo, sensor `BAD`/velho inválido) | idem |
| A4 | Alertas determinísticos: `CRITICAL`/`WARNING`/`OFFLINE`; limiar exato e `BAD` não alertam | idem |
| A5 | Marker: 3 QR de teste → equipamento correto; desconhecido ≡ alheio; rate limit 429 + `Retry-After` por principal | idem |
| A6 | Auditoria `app.audit` sem token nem marker consultado | idem |
| A7 | Fail closed: produção+demo e `AUTH_MODE=oidc` não iniciam | `tests/unit/api/test_auth_config.py` |
| A8 | Respostas reais obedecem aos schemas do OpenAPI; nenhuma rota fora do contrato | `tests/contract/test_openapi_contract.py` |
| A9 | **A mesma bateria A1–A6 roda contra o dublê em memória e contra PostgreSQL real** (fixture parametrizada) | `tests/unit/api/test_equipment_api.py` (variante `[postgres]`) |
| A10 | Autorização e QR por HTTP na pilha Compose real | `tests/integration/test_stack_flow.py` |
| A11 | Painel servido com CSP estrita | `tests/unit/api/test_equipment_api.py`, `tests/e2e/test_panel.py` |

## Riscos
- Rate limit em memória não é compartilhado entre réplicas (aceitável com 1 réplica; substituir por Redis/gateway ao escalar).
- Tokens demo são públicos neste repositório: nunca habilitar fora de dev (garantido por fail closed).
