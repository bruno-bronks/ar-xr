# C4 — Nível 3: Componentes

## Pacotes e módulos (estado real da Fase 1)

```mermaid
flowchart TB
  subgraph domain["packages/domain · spatial_domain (puro, sem I/O)"]
    status["status.py<br/>evaluate_status — SPEC-002"]
    markers["markers.py<br/>Registry.resolve — SPEC-003 (modelo de referência)"]
    telemetry["telemetry.py<br/>parse_payload — SPEC-004/005"]
  end
  subgraph storage["packages/storage · spatial_storage"]
    repo["repository.py<br/>Protocol Repository"]
    pg["postgres.py<br/>PostgresRepository"]
    mem["memory.py<br/>InMemoryRepository (dublê de teste)"]
    models["models.py + migrations/"]
    seed["seed_data.py"]
  end
  subgraph common["packages/common · spatial_common"]
    log["logging_json.py"]
  end
  subgraph api["services/api/app"]
    main["main.py (composition root)"]
    auth["auth.py (demo, fail closed)"]
    routes["routes.py"]
    twin["twin.py"]
    audit["audit.py + ratelimit.py"]
    mw["middleware.py"]
    health["health.py"]
  end
  subgraph worker["services/telemetry-worker/worker"]
    handler["handler.py (pipeline)"]
    consumer["consumer.py (ack manual)"]
    wmain["main.py (reconexão)"]
  end
  sim["services/equipment-simulator/simulator"]
  panel["clients/web-fallback (HTML/JS/CSS)"]

  routes --> twin --> status
  routes --> repo
  routes --> audit
  main --> auth & routes & health & mw
  pg -.implementa.-> repo
  mem -.implementa.-> repo
  handler --> telemetry & repo
  consumer --> handler
  wmain --> consumer & pg
  sim --> seed
  api -.-> log
  worker -.-> log
  panel -->|HTTP| routes
```

`markers.Registry` é o **modelo de referência** da spec Z-003; a API usa `Repository.get_equipment_by_marker` e um
teste de contrato verifica que ambos concordam.

## Padrões em uso (e por quê)
| Padrão | Onde | Justificativa |
|---|---|---|
| Repository (porta + 2 implementações) | `spatial_storage` | Postgres real em produção; dublê em memória para testes rápidos. A **mesma suíte de contrato** roda nos dois ([ADR-0002](../adr/0002-shared-storage-package-and-demo-auth.md)). |
| Composition root + injeção | `create_app(checks, repo, clock, ...)` | Testa sem Docker, relógio controlável, dependências substituíveis. |
| Idempotência via restrição de banco | `ON CONFLICT DO NOTHING` / upsert condicional | Correto sob concorrência (corrida de 8 threads testada); mais simples e seguro que dedup em memória. |
| Ack manual + redelivery | `worker/consumer.py` | Garante at-least-once sem perder evento em falha de banco. |
| Fail closed | `build_authenticator`, `Settings` | Demo auth nunca sobe em produção. |

Evitados deliberadamente (sem necessidade demonstrada): Strategy para regras de sensor (uma só regra), Factory de twin, Outbox, Event Sourcing, CQRS, Saga, Circuit Breaker (dependências críticas têm timeout curto e o worker reconecta com backoff).

## Regras de fronteira (verificadas hoje por revisão; teste automático pendente)
- `spatial_domain` não importa FastAPI, SQLAlchemy nem I/O (hoje verdadeiro — ver o grafo do Graphify).
- API e worker só falam com o banco via `Repository`.
