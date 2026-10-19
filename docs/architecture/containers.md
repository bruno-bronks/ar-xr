# C4 — Nível 2: Contêineres

```mermaid
flowchart TB
  subgraph Fase0["Implementado na Fase 0"]
    API["api<br/>FastAPI · /health/live · /health/ready"]
    DB[("PostgreSQL 16<br/>(db)")]
    MQ["Mosquitto 2<br/>(broker)"]
  end
  subgraph Fase1["Fase 1 — NÃO implementado"]
    SIM["equipment-simulator"]
    WRK["telemetry-worker"]
    WEB["web-fallback 2D"]
  end
  API -->|"SELECT 1 (readiness)"| DB
  API -->|"TCP (readiness)"| MQ
  SIM -.->|"MQTT QoS1"| MQ
  MQ -.-> WRK
  WRK -.-> DB
  WEB -.->|HTTP| API
```

| Contêiner | Fase | Tecnologia | Porta host (127.0.0.1) | Healthcheck |
|---|---|---|---|---|
| api | 0 | Python 3.12, FastAPI, SQLAlchemy, psycopg | 8088 → 8000 | `GET /health/live` |
| db | 0 | postgres:16.4-alpine | 55432 → 5432 | `pg_isready` |
| broker | 0 | eclipse-mosquitto:2.0.18 | 1883 → 1883 | `mosquitto_sub` em `$SYS` |
| telemetry-worker | 1 | Python, paho/aiomqtt | — | — |
| equipment-simulator | 1 | Python | — | — |
| web-fallback | 1 | HTML/JS (painel 2D) | — | — |

Decisão estrutural: [ADR-0001](../adr/0001-modular-first.md). Linhas tracejadas = planejado.
