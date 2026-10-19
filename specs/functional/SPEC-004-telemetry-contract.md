# SPEC-004 — Contrato de telemetria, idempotência e ordenação

Requisito: REQ-MNT-003 · Outcome: OUT-MNT-002 · Formal: [`z-004-telemetry-ingestion.tex`](../formal-z/z-004-telemetry-ingestion.tex)
Contratos: [`asyncapi.yaml`](../contracts/asyncapi.yaml), [`telemetry-event.v1.schema.json`](../../packages/contracts/telemetry-event.v1.schema.json).

## Evento
Tópico `spatial/v1/equipment/{equipment_id}/telemetry`, JSON, `schema_version = 1`.

| Campo | Regra |
|---|---|
| `schema_version` | constante `1` |
| `event_id` | string 1–128 `[A-Za-z0-9._:-]` — único por `source` |
| `source` | string 1–64, identifica o publicador (simulador/gateway) |
| `equipment_id` | string 1–64; **deve coincidir com o tópico** (verificado na ingestão, Fase 1) |
| `sensor_type` | `temperature`, `vibration` (extensível por nova versão) |
| `value` | número finito (sem NaN/Infinity) |
| `unit` | string não vazia |
| `observed_at` | RFC 3339 com offset (`Z` ou `±hh:mm`) |
| `quality` | `GOOD` ou `BAD` |

`received_at` **não** vem do publicador: é atribuído pelo worker ao receber. Propriedades adicionais são rejeitadas (`additionalProperties: false`).

## Semântica de entrega (política definida)
- **QoS 1** (at-least-once) ⇒ duplicatas são esperadas ⇒ ingestão **idempotente** por `(source, event_id)`.
- **Retenção:** mensagens não retidas (`retain = false`); a última leitura vive no banco, não no broker.
- **Fora de ordem:** o estado "última leitura" só avança se `observed_at` ≥ atual; o evento atrasado continua persistido no histórico.
- **Reconexão:** cliente MQTT com backoff exponencial e sessão persistente (`clean_session = false`) — implementado na Fase 1.
- **Autorização:** tópico MQTT **não** é controle de acesso; credenciais/ACL do broker são exigidas fora de dev (threat model, S-02).
- Payload inválido: descartado e contado em métrica; nunca derruba o worker.

## Critérios de aceitação (Fase 0 — contrato)
Schema é JSON Schema 2020-12 válido; exemplos válidos passam; inválidos (campo faltante, qualidade desconhecida, timestamp sem offset, NaN, propriedade extra) são rejeitados — `tests/contract/test_telemetry_schema.py`.

## Pendente (Fase 1)
Worker, persistência, deduplicação real contra PostgreSQL, testes de fora-de-ordem e reconexão.
