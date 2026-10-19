# Runbook — desenvolvimento local

## Primeira vez
```powershell
.\scripts\dev-setup.ps1
.\scripts\check.ps1
docker compose up --build --wait
```

## Fluxo completo (Fase 1)
```powershell
docker compose up --build --wait        # db, broker, migrate, api, worker, simulator
start http://127.0.0.1:8088/panel/      # painel 2D (escolha a organizacao demo)
curl.exe -s -H "Authorization: Bearer demo-operator-a" http://127.0.0.1:8088/api/v1/equipment
.\scripts\smoke.ps1                      # sobe e roda integracao + performance + E2E contra a pilha real
```
Documentacao interativa da API: http://127.0.0.1:8088/docs (somente fora de producao).

## Testes que dependem de infraestrutura
| Variavel | Habilita |
|---|---|
| `TEST_DATABASE_URL=postgresql+psycopg://spatial:spatial-dev-only@127.0.0.1:55432/spatial` | contrato do repositorio e bateria da API contra **PostgreSQL real**, migracoes (cria/derruba bancos `spatial_t_*`/`spatial_m_*`) |
| `BASE_URL=http://127.0.0.1:8088` (+ a de cima) | fluxo, resiliencia, latencia e E2E do painel contra a **pilha Compose** |

Sem elas esses testes aparecem como **skipped** (nunca como aprovados). Os testes de resiliencia **param e reiniciam** `simulator`, `db` e `broker` do Compose; os E2E usam o **Microsoft Edge** instalado (`E2E_BROWSER_CHANNEL=msedge`, padrao).

## Verificacao das specs Z
```powershell
.\scripts\verify-z.ps1      # exige JDK + czt.jar (veja docs/decisions/tool-evaluation.md)
```

## Grafo (Graphify)
```powershell
graphify update .            # AST local, sem custo
.\.venv\Scripts\python.exe scripts\graph_crosscheck.py
```

## Problemas conhecidos

| Sintoma | Causa | Ação |
|---|---|---|
| `bind: address already in use` ao subir | 5432/8000 ocupadas por outros projetos | Já evitado (55432/8088). Se ainda colidir, mude `DB_PORT`/`API_PORT`/`MQTT_PORT` no `.env`. |
| `invalid peer certificate: UnknownIssuer` no `uv` | Proxy TLS corporativo | Use `pip` (certificados do sistema). Não desabilite a verificação. |
| API `unhealthy` logo após o `up` | Banco ainda iniciando | `docker compose logs api db`; o `depends_on` espera `healthy`, mas confira o log. |
| `/health/ready` = 503 | Dependência fora do ar | Corpo indica qual (`database`/`broker`); detalhes só nos logs da API (`docker compose logs api`). |
| Testes de integração `skipped` | `BASE_URL`/`TEST_DATABASE_URL` ausentes | Use `.\scripts\smoke.ps1` ou defina as variáveis (tabela acima). |
| Banco `spatial_t_*` sobrando no Postgres de dev | execução de teste interrompida | `docker compose exec db psql -U spatial -d spatial -c "DROP DATABASE \"spatial_t_xxx\" WITH (FORCE)"` |
| Painel mostra erro 401 | token inválido selecionado (opção de teste) | escolha *Organização A/B (demo)* |
| API não sobe: `demo authentication is refused in production` | `ENVIRONMENT=production` com `AUTH_MODE=demo` | comportamento intencional (fail closed) |

## Diagnóstico rápido
```powershell
docker compose ps
docker compose logs api --no-color | Select-Object -Last 20     # JSON, uma linha por evento
curl.exe -s -i -H "X-Correlation-ID: debug-1" http://127.0.0.1:8088/health/ready
```
Filtre os logs por `correlation_id` para seguir uma requisição.

## Reset total do ambiente local
```powershell
docker compose down -v        # remove containers e o volume do banco de dev
```
