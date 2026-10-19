# SPEC-001 — Fundação: saúde, correlação e ambiente local

Requisitos: REQ-ENG-001, REQ-ENG-002, REQ-ENG-003, REQ-ENG-004, REQ-SEC-001, REQ-SEC-002.
Contrato: [`openapi.yaml`](../contracts/openapi.yaml) (`/health/live`, `/health/ready`).

## Atores
Desenvolvedor (sobe o ambiente), orquestrador de containers (healthchecks), operador de observabilidade (logs).

## Comportamento

### Liveness — `GET /health/live`
- 200 `{"status":"alive"}`. Não acessa banco nem broker. Falha de dependência **não** altera a resposta.

### Readiness — `GET /health/ready`
- Executa as verificações `database` (`SELECT 1`) e `broker` (conexão TCP) com timeout curto.
- Todas OK → 200 `{"status":"ready","checks":{"database":"ok","broker":"ok"}}`.
- Qualquer falha ou exceção → 503 `{"status":"not_ready","checks":{...,"<dep>":"fail"}}`.
- O corpo contém apenas `ok`/`fail`. Detalhes da exceção vão **somente** ao log do servidor (sem credenciais).

### Correlation ID
- Cabeçalho `X-Correlation-ID`. Aceito se casar `^[A-Za-z0-9._-]{1,64}$`; caso contrário substituído por UUID4 (evita log injection).
- Presente em toda resposta e em todo log de requisição (`correlation_id`).

### Logs
- JSON, uma linha por evento, campos mínimos: `timestamp`, `level`, `logger`, `message`, `correlation_id`; requisição registra `method`, `path`, `status`, `duration_ms`.

### Ambiente local
- `docker compose up --build` sobe `db`, `broker`, `api`. `api` só inicia após `db` e `broker` saudáveis. Serviços possuem healthcheck.
- Portas publicadas apenas em `127.0.0.1` (D-004).
- Configuração por variáveis de ambiente (12-factor); valores sensíveis como `SecretStr`; `.env.example` fictício.

## Critérios de aceitação
| # | Critério | Teste |
|---|---|---|
| A1 | live = 200 mesmo com dependências falhando | `test_health.py::test_live_*` |
| A2 | ready = 200 com deps OK; 503 se qualquer uma falha ou lança exceção | `test_health.py::test_ready_*` |
| A3 | ready não vaza strings de conexão/exceção | `test_health.py::test_ready_does_not_leak_*` |
| A4 | Correlation ID gerado/propagado/sanitizado e logado | `test_correlation.py` |
| A5 | Config não expõe segredo em `repr` | `test_config.py` |
| A6 | Compose: portas só em loopback; `.env` ignorado | `test_hygiene.py` |
| A7 | Stack real sobe e responde saudável | `tests/integration/test_compose_smoke.py` |

## Não funcionais
- Imagem da API roda como usuário não-root; sem curl/ferramentas desnecessárias.
- Tempo de resposta do `ready` limitado por timeouts (≤ 2 s por verificação).

## Riscos
- Mosquitto de desenvolvimento permite conexão anônima → mitigado por bind em loopback; autenticação/TLS obrigatórios fora de dev (ver [threat model](../../docs/architecture/threat-model.md)).
