# SPEC-005 — Ingestão de telemetria e persistência

Requisitos: REQ-MNT-003, REQ-MNT-004, REQ-MNT-005, REQ-MNT-007, REQ-ENG-007 · Formal: [Z-004](../formal-z/z-004-telemetry-ingestion.tex) · Contratos: [AsyncAPI](../contracts/asyncapi.yaml), [JSON Schema](../../packages/contracts/telemetry-event.v1.schema.json) · Complementa [SPEC-004](SPEC-004-telemetry-contract.md).

## Modelo de dados (PostgreSQL, Alembic `0001_initial`)

| Tabela | Chave | Colunas principais |
|---|---|---|
| `organizations` | `id` | `name` |
| `equipment` | `id` | `org_id`→organizations, `name`, `type`, `location`, `marker_id` (UNIQUE, nulo permitido), `offline_after_seconds` (>0), `last_seen_at` |
| `threshold_profiles` | `(equipment_id, sensor_type)` | `unit`, `warn`, `crit` (CHECK `warn <= crit`) |
| `telemetry_events` (histórico) | `(source, event_id)` | `equipment_id`, `sensor_type`, `value`, `unit`, `observed_at`, `received_at`, `quality` |
| `telemetry_latest` | `(equipment_id, sensor_type)` | cópia da leitura vigente (+ `source`, `event_id`) |

Todos os tempos `timestamptz` (UTC). `value` é `double precision` finito (CHECK).

## Pipeline do worker (cada mensagem, nesta ordem)
1. **Decodificar** UTF-8 estrito → `INVALID_ENCODING`.
2. **JSON estrito** (rejeita `NaN`/`Infinity`, duplicatas não importam) → `INVALID_JSON`.
3. **Validar schema v1** (mesmas regras do JSON Schema) → `SCHEMA_VIOLATION`.
4. **Tópico = payload**: `equipment_id` do tópico `spatial/v1/equipment/{id}/telemetry` igual ao do payload → `TOPIC_MISMATCH`.
5. **Equipamento e sensor cadastrados** (existe perfil de limiar) → `UNKNOWN_EQUIPMENT` / `UNKNOWN_SENSOR`.
6. **Skew**: `observed_at ≤ received_at + 5 min` (D-007) → `TIMESTAMP_IN_FUTURE`.
7. **Gravar numa transação**: `INSERT ... ON CONFLICT (source,event_id) DO NOTHING`.
   - 0 linhas ⇒ `DUPLICATE` (nada mais muda — T1 do Z-004).
   - 1 linha ⇒ `UPSERT telemetry_latest ... WHERE EXCLUDED.observed_at >= telemetry_latest.observed_at`; resultado `ACCEPTED` (avançou a vigente) ou `ACCEPTED_HISTORY_ONLY` (evento atrasado; T2). `equipment.last_seen_at` só avança (`GREATEST`).
8. **Ack** ao broker somente depois de gravar (ou rejeitar). Falha de banco ⇒ **sem ack**, desconexão e reconexão com backoff ⇒ redelivery (sessão persistente) ⇒ gravação idempotente.

Mensagem rejeitada: log estruturado (`reason`, `topic`, sem payload bruto além de 200 caracteres escapados), contador por motivo, nenhuma escrita.

## Reconexão e entrega
`client_id` fixo, `clean_session=False`, assinatura `spatial/v1/equipment/+/telemetry` QoS 1, `reconnect_delay_set(1s..30s)`. Healthcheck do worker: arquivo de heartbeat atualizado enquanto conectado (idade < 30 s).

## Seeds (REQ-MNT-007, D-008)
| Org | Equipamento | Tipo | Marker (QR) | Sensores (warn / crit) |
|---|---|---|---|---|
| org-a | EQ-001 | Compressor de ar | `QR-EQ-001` | temperature 85/100 °C · vibration 5/8 mm/s |
| org-a | EQ-002 | Bomba centrífuga | `QR-EQ-002` | temperature 70/90 °C · vibration 4/7 mm/s |
| org-a | EQ-003 | Motor elétrico | `QR-EQ-003` | temperature 80/95 °C · vibration 6/9 mm/s |
| org-b | EQ-B01 | Sentinela (isolamento) | `QR-EQ-B01` | temperature 80/95 °C · vibration 6/9 mm/s |

`offline_after_seconds = 30` para todos. O seed é um upsert idempotente (rodar 2× não duplica nem altera telemetria).

## Critérios de aceitação
| # | Critério | Onde é testado |
|---|---|---|
| A1 | Parser rejeita todos os payloads inválidos do contrato e aceita os válidos (mesmos casos do JSON Schema) | `tests/unit/domain/test_telemetry.py` |
| A2 | Cada motivo de rejeição é produzido e não grava | `tests/unit/worker/test_handler.py` |
| A3 | Evento duplicado não altera histórico nem vigente | `tests/integration/test_repository_postgres.py` + `tests/unit/storage/test_repository_contract.py` |
| A4 | Evento fora de ordem entra no histórico sem regredir a vigente | idem |
| A5 | Migrações aplicam em banco vazio; seed idempotente | `tests/integration/test_migrations.py` |
| A6 | Falha de banco não perde evento; reconexão MQTT recupera | `tests/integration/test_stack_resilience.py` |

## Fora de escopo (fase futura)
Retenção/particionamento de histórico, métricas Prometheus, DLQ persistente de mensagens rejeitadas.
