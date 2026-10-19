# Runbook — desenvolvimento local

## Primeira vez
```powershell
.\scripts\dev-setup.ps1
.\scripts\check.ps1
docker compose up --build --wait
```

## Problemas conhecidos

| Sintoma | Causa | Ação |
|---|---|---|
| `bind: address already in use` ao subir | 5432/8000 ocupadas por outros projetos | Já evitado (55432/8088). Se ainda colidir, mude `DB_PORT`/`API_PORT`/`MQTT_PORT` no `.env`. |
| `invalid peer certificate: UnknownIssuer` no `uv` | Proxy TLS corporativo | Use `pip` (certificados do sistema). Não desabilite a verificação. |
| API `unhealthy` logo após o `up` | Banco ainda iniciando | `docker compose logs api db`; o `depends_on` espera `healthy`, mas confira o log. |
| `/health/ready` = 503 | Dependência fora do ar | Corpo indica qual (`database`/`broker`); detalhes só nos logs da API (`docker compose logs api`). |
| Testes de integração `skipped` | `BASE_URL` ausente | Use `.\scripts\smoke.ps1` ou `$env:BASE_URL="http://127.0.0.1:8088"`. |

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
