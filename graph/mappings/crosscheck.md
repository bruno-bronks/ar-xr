# Cruzamento matriz x grafo (Graphify)

> Gerado por `scripts/graph_crosscheck.py`. **Informativo**: a matriz e o Git continuam a fonte oficial;
> o grafo e um indice auxiliar. `EXTRACTED` = aresta lida do codigo (AST); `INFERRED` = aresta inferida.
> Profundidade maxima de busca: 4 saltos.

| REQ | Teste | Codigo | Resultado | Saltos |
|---|---|---|---|---|
| REQ-ENG-002 | `tests/unit/api/test_health.py` | `services/api/app/health.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-ENG-002 | `tests/contract/test_openapi_contract.py` | `services/api/app/health.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-ENG-003 | `tests/unit/api/test_health.py` | `services/api/app/health.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-ENG-003 | `tests/contract/test_openapi_contract.py` | `services/api/app/health.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-ENG-003 | `tests/integration/test_compose_smoke.py` | `services/api/app/health.py` | NOT CONFIRMED (black-box) | - |
| REQ-ENG-003 | `tests/integration/test_stack_resilience.py` | `services/api/app/health.py` | NOT CONFIRMED (black-box) | - |
| REQ-ENG-004 | `tests/unit/api/test_correlation.py` | `services/api/app/middleware.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-ENG-004 | `tests/unit/api/test_correlation.py` | `packages/common/src/spatial_common/logging_json.py` | CONFIRMED (INFERRED) | 1 |
| REQ-ENG-004 | `tests/integration/test_compose_smoke.py` | `services/api/app/middleware.py` | NOT CONFIRMED (black-box) | - |
| REQ-ENG-004 | `tests/integration/test_compose_smoke.py` | `packages/common/src/spatial_common/logging_json.py` | NOT CONFIRMED (black-box) | - |
| REQ-ENG-008 | `tests/unit/repo/test_trace_edges.py` | `scripts/trace_edges.py` | NOT CONFIRMED | - |
| REQ-ENG-008 | `tests/unit/repo/test_trace_edges.py` | `scripts/graph_crosscheck.py` | NOT CONFIRMED | - |
| REQ-SEC-001 | `tests/unit/repo/test_hygiene.py` | `services/api/app/config.py` | NOT CONFIRMED | - |
| REQ-SEC-001 | `tests/unit/api/test_config.py` | `services/api/app/config.py` | CONFIRMED (INFERRED) | 1 |
| REQ-SEC-003 | `tests/unit/api/test_auth_config.py` | `services/api/app/auth.py` | CONFIRMED (INFERRED) | 1 |
| REQ-SEC-003 | `tests/unit/api/test_auth_config.py` | `services/api/app/config.py` | CONFIRMED (INFERRED) | 1 |
| REQ-SEC-003 | `tests/unit/api/test_auth_config.py` | `services/api/app/routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-SEC-003 | `tests/unit/api/test_equipment_api.py` | `services/api/app/auth.py` | CONFIRMED (INFERRED) | 3 |
| REQ-SEC-003 | `tests/unit/api/test_equipment_api.py` | `services/api/app/config.py` | CONFIRMED (INFERRED) | 3 |
| REQ-SEC-003 | `tests/unit/api/test_equipment_api.py` | `services/api/app/routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-SEC-003 | `tests/integration/test_stack_flow.py` | `services/api/app/auth.py` | NOT CONFIRMED (black-box) | - |
| REQ-SEC-003 | `tests/integration/test_stack_flow.py` | `services/api/app/config.py` | NOT CONFIRMED (black-box) | - |
| REQ-SEC-003 | `tests/integration/test_stack_flow.py` | `services/api/app/routes.py` | NOT CONFIRMED (black-box) | - |
| REQ-SEC-004 | `tests/unit/api/test_equipment_api.py` | `services/api/app/audit.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-SEC-004 | `tests/unit/api/test_equipment_api.py` | `services/api/app/ratelimit.py` | CONFIRMED (INFERRED) | 3 |
| REQ-MNT-001 | `tests/unit/domain/test_markers.py` | `packages/domain/src/spatial_domain/markers.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-001 | `tests/unit/domain/test_markers.py` | `packages/storage/src/spatial_storage/postgres.py` | CONFIRMED (INFERRED) | 4 |
| REQ-MNT-001 | `tests/unit/domain/test_markers.py` | `services/api/app/routes.py` | CONFIRMED (INFERRED) | 4 |
| REQ-MNT-001 | `tests/unit/storage/test_repository_contract.py` | `packages/domain/src/spatial_domain/markers.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-001 | `tests/unit/storage/test_repository_contract.py` | `packages/storage/src/spatial_storage/postgres.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-001 | `tests/unit/storage/test_repository_contract.py` | `services/api/app/routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-001 | `tests/unit/api/test_equipment_api.py` | `packages/domain/src/spatial_domain/markers.py` | CONFIRMED (INFERRED) | 3 |
| REQ-MNT-001 | `tests/unit/api/test_equipment_api.py` | `packages/storage/src/spatial_storage/postgres.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-001 | `tests/unit/api/test_equipment_api.py` | `services/api/app/routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-001 | `tests/integration/test_stack_flow.py` | `packages/domain/src/spatial_domain/markers.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-001 | `tests/integration/test_stack_flow.py` | `packages/storage/src/spatial_storage/postgres.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-001 | `tests/integration/test_stack_flow.py` | `services/api/app/routes.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-002 | `tests/unit/domain/test_status.py` | `packages/domain/src/spatial_domain/status.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-MNT-002 | `tests/unit/domain/test_status.py` | `services/api/app/twin.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-MNT-002 | `tests/unit/api/test_equipment_api.py` | `packages/domain/src/spatial_domain/status.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-002 | `tests/unit/api/test_equipment_api.py` | `services/api/app/twin.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-002 | `tests/integration/test_stack_resilience.py` | `packages/domain/src/spatial_domain/status.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-002 | `tests/integration/test_stack_resilience.py` | `services/api/app/twin.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-003 | `tests/contract/test_telemetry_schema.py` | `packages/domain/src/spatial_domain/telemetry.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-MNT-003 | `tests/contract/test_telemetry_schema.py` | `packages/storage/src/spatial_storage/postgres.py` | CONFIRMED (EXTRACTED) | 4 |
| REQ-MNT-003 | `tests/contract/test_telemetry_schema.py` | `services/telemetry-worker/worker/handler.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-MNT-003 | `tests/unit/domain/test_telemetry.py` | `packages/domain/src/spatial_domain/telemetry.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-MNT-003 | `tests/unit/domain/test_telemetry.py` | `packages/storage/src/spatial_storage/postgres.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-003 | `tests/unit/domain/test_telemetry.py` | `services/telemetry-worker/worker/handler.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-MNT-003 | `tests/unit/storage/test_repository_contract.py` | `packages/domain/src/spatial_domain/telemetry.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-003 | `tests/unit/storage/test_repository_contract.py` | `packages/storage/src/spatial_storage/postgres.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-003 | `tests/unit/storage/test_repository_contract.py` | `services/telemetry-worker/worker/handler.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-003 | `tests/integration/test_stack_resilience.py` | `packages/domain/src/spatial_domain/telemetry.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-003 | `tests/integration/test_stack_resilience.py` | `packages/storage/src/spatial_storage/postgres.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-003 | `tests/integration/test_stack_resilience.py` | `services/telemetry-worker/worker/handler.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-004 | `tests/unit/domain/test_telemetry.py` | `packages/domain/src/spatial_domain/telemetry.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-MNT-004 | `tests/unit/domain/test_telemetry.py` | `services/telemetry-worker/worker/handler.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-MNT-004 | `tests/unit/worker/test_handler.py` | `packages/domain/src/spatial_domain/telemetry.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-004 | `tests/unit/worker/test_handler.py` | `services/telemetry-worker/worker/handler.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-004 | `tests/integration/test_stack_resilience.py` | `packages/domain/src/spatial_domain/telemetry.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-004 | `tests/integration/test_stack_resilience.py` | `services/telemetry-worker/worker/handler.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-005 | `tests/unit/worker/test_consumer.py` | `services/telemetry-worker/worker/consumer.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-005 | `tests/unit/worker/test_consumer.py` | `services/telemetry-worker/worker/main.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-005 | `tests/integration/test_stack_resilience.py` | `services/telemetry-worker/worker/consumer.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-005 | `tests/integration/test_stack_resilience.py` | `services/telemetry-worker/worker/main.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-006 | `tests/unit/api/test_equipment_api.py` | `services/api/app/routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-006 | `tests/unit/api/test_equipment_api.py` | `services/api/app/twin.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-006 | `tests/unit/api/test_equipment_api.py` | `services/api/app/schemas.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-MNT-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/routes.py` | CONFIRMED (INFERRED) | 3 |
| REQ-MNT-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/twin.py` | CONFIRMED (INFERRED) | 3 |
| REQ-MNT-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/schemas.py` | CONFIRMED (INFERRED) | 4 |
| REQ-MNT-006 | `tests/integration/test_stack_flow.py` | `services/api/app/routes.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-006 | `tests/integration/test_stack_flow.py` | `services/api/app/twin.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-006 | `tests/integration/test_stack_flow.py` | `services/api/app/schemas.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-007 | `tests/integration/test_migrations.py` | `packages/storage/src/spatial_storage/seed_data.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-007 | `tests/integration/test_migrations.py` | `packages/storage/src/spatial_storage/migrate.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-007 | `tests/integration/test_migrations.py` | `packages/storage/src/spatial_storage/postgres.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-007 | `tests/unit/storage/test_repository_contract.py` | `packages/storage/src/spatial_storage/seed_data.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-MNT-007 | `tests/unit/storage/test_repository_contract.py` | `packages/storage/src/spatial_storage/migrate.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-MNT-007 | `tests/unit/storage/test_repository_contract.py` | `packages/storage/src/spatial_storage/postgres.py` | CONFIRMED (INFERRED) | 1 |
| REQ-SIM-001 | `tests/unit/simulator/test_scenarios.py` | `services/equipment-simulator/simulator/scenarios.py` | CONFIRMED (INFERRED) | 1 |
| REQ-SIM-001 | `tests/unit/simulator/test_scenarios.py` | `services/equipment-simulator/simulator/main.py` | CONFIRMED (INFERRED) | 2 |
| REQ-SIM-001 | `tests/integration/test_stack_flow.py` | `services/equipment-simulator/simulator/scenarios.py` | NOT CONFIRMED (black-box) | - |
| REQ-SIM-001 | `tests/integration/test_stack_flow.py` | `services/equipment-simulator/simulator/main.py` | NOT CONFIRMED (black-box) | - |

## Resumo

- CONFIRMED (EXTRACTED): **18**
- CONFIRMED (INFERRED): **39**
- NOT CONFIRMED (black-box): **24**
- NOT CONFIRMED: **3**
- NOT IN GRAPH: **0**

- `NOT CONFIRMED (black-box)`: teste de integracao/E2E/performance; exercita o codigo por HTTP/MQTT/Docker,
  o que a analise estatica nao enxerga (esperado).
- `NOT CONFIRMED`: teste unitario/contrato SEM caminho de dependencia ate o codigo declarado -> revisar a
  matriz (o teste declarado pode nao cobrir esse arquivo). Nao e erro automatico: o teste pode ler artefatos
  (ex.: `.env.example`) em vez de importar o codigo.
- `NOT IN GRAPH`: o Graphify nao indexa o arquivo (ex.: scripts fora do pacote analisado).
