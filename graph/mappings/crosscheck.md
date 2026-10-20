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
| REQ-SEC-004 | `tests/unit/api/test_equipment_api.py` | `services/api/app/audit.py` | CONFIRMED (INFERRED) | 3 |
| REQ-SEC-004 | `tests/unit/api/test_equipment_api.py` | `services/api/app/ratelimit.py` | CONFIRMED (INFERRED) | 3 |
| REQ-MNT-001 | `tests/unit/domain/test_markers.py` | `packages/domain/src/spatial_domain/markers.py` | CONFIRMED (INFERRED) | 1 |
| REQ-MNT-001 | `tests/unit/domain/test_markers.py` | `packages/storage/src/spatial_storage/postgres.py` | CONFIRMED (EXTRACTED) | 4 |
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
| REQ-MNT-005 | `tests/unit/worker/test_consumer.py` | `services/telemetry-worker/worker/consumer.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-MNT-005 | `tests/unit/worker/test_consumer.py` | `services/telemetry-worker/worker/main.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-MNT-005 | `tests/integration/test_stack_resilience.py` | `services/telemetry-worker/worker/consumer.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-005 | `tests/integration/test_stack_resilience.py` | `services/telemetry-worker/worker/main.py` | NOT CONFIRMED (black-box) | - |
| REQ-MNT-006 | `tests/unit/api/test_equipment_api.py` | `services/api/app/routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-006 | `tests/unit/api/test_equipment_api.py` | `services/api/app/twin.py` | CONFIRMED (INFERRED) | 2 |
| REQ-MNT-006 | `tests/unit/api/test_equipment_api.py` | `services/api/app/schemas.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-MNT-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/routes.py` | CONFIRMED (INFERRED) | 3 |
| REQ-MNT-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/twin.py` | CONFIRMED (INFERRED) | 3 |
| REQ-MNT-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/schemas.py` | CONFIRMED (INFERRED) | 3 |
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
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/QrPayloadTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/QrPayload.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/QrPayloadTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/QrPayloadTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/QrPayloadTests.cs` | `clients/ar-unity/Assets/Scripts/QrScanner.cs` | NOT CONFIRMED | - |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/QrPayload.cs` | CONFIRMED (INFERRED) | 2 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Assets/Scripts/QrScanner.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/QrPayload.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Assets/Scripts/QrScanner.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/QrPayload.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Assets/Scripts/QrScanner.cs` | CONFIRMED (EXTRACTED) | 3 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/QrRoundTripTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/QrPayload.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/QrRoundTripTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (EXTRACTED) | 3 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/QrRoundTripTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-001 | `tests/csharp/Spatial.Ar.Core.Tests/QrRoundTripTests.cs` | `clients/ar-unity/Assets/Scripts/QrScanner.cs` | NOT CONFIRMED | - |
| REQ-AR-002 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-002 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/OverlayViewModel.cs` | CONFIRMED (EXTRACTED) | 3 |
| REQ-AR-002 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-002 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/OverlayViewModel.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-002 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-002 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/OverlayViewModel.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/OverlayViewModel.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/Dtos.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Assets/Scripts/SpatialArApp.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/OverlayViewModel.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/Dtos.cs` | CONFIRMED (EXTRACTED) | 3 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Assets/Scripts/SpatialArApp.cs` | CONFIRMED (INFERRED) | 2 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/OverlayViewModel.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/Dtos.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-003 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Assets/Scripts/SpatialArApp.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-003 | `tests/contract/test_ar_fixtures.py` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/OverlayViewModel.cs` | CONFIRMED (INFERRED) | 4 |
| REQ-AR-003 | `tests/contract/test_ar_fixtures.py` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/Dtos.cs` | CONFIRMED (INFERRED) | 4 |
| REQ-AR-003 | `tests/contract/test_ar_fixtures.py` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | NOT CONFIRMED | - |
| REQ-AR-003 | `tests/contract/test_ar_fixtures.py` | `clients/ar-unity/Assets/Scripts/SpatialArApp.cs` | CONFIRMED (INFERRED) | 4 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SessionDriver.cs` | CONFIRMED (INFERRED) | 2 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Assets/Scripts/UnityWebRequestTransport.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SessionDriver.cs` | CONFIRMED (INFERRED) | 2 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/OverlayViewModelTests.cs` | `clients/ar-unity/Assets/Scripts/UnityWebRequestTransport.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SessionDriver.cs` | CONFIRMED (INFERRED) | 2 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/SpatialApiClientTests.cs` | `clients/ar-unity/Assets/Scripts/UnityWebRequestTransport.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SessionDriver.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-004 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Assets/Scripts/UnityWebRequestTransport.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-004 | `tests/contract/test_ar_fixtures.py` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/MarkerSession.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-004 | `tests/contract/test_ar_fixtures.py` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SessionDriver.cs` | CONFIRMED (INFERRED) | 4 |
| REQ-AR-004 | `tests/contract/test_ar_fixtures.py` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SpatialApiClient.cs` | NOT CONFIRMED | - |
| REQ-AR-004 | `tests/contract/test_ar_fixtures.py` | `clients/ar-unity/Assets/Scripts/UnityWebRequestTransport.cs` | NOT CONFIRMED | - |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/QrPayloadTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/ClientConfig.cs` | CONFIRMED (INFERRED) | 4 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/QrPayloadTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SessionDriver.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/QrPayloadTests.cs` | `clients/ar-unity/Assets/Scripts/SpatialArApp.cs` | CONFIRMED (INFERRED) | 4 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/ClientConfigTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/ClientConfig.cs` | CONFIRMED (INFERRED) | 1 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/ClientConfigTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SessionDriver.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/ClientConfigTests.cs` | `clients/ar-unity/Assets/Scripts/SpatialArApp.cs` | CONFIRMED (INFERRED) | 2 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/ClientConfig.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SessionDriver.cs` | CONFIRMED (INFERRED) | 2 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/MarkerSessionTests.cs` | `clients/ar-unity/Assets/Scripts/SpatialArApp.cs` | CONFIRMED (INFERRED) | 2 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/ClientConfig.cs` | CONFIRMED (INFERRED) | 3 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/SessionDriver.cs` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AR-005 | `tests/csharp/Spatial.Ar.Core.Tests/SessionDriverTests.cs` | `clients/ar-unity/Assets/Scripts/SpatialArApp.cs` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AR-006 | `tests/unit/repo/test_generate_qr.py` | `scripts/generate_qr.py` | NOT CONFIRMED | - |
| REQ-AR-006 | `tests/csharp/Spatial.Ar.Core.Tests/QrRoundTripTests.cs` | `scripts/generate_qr.py` | NOT CONFIRMED | - |
| REQ-AI-001 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-001 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/models.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-001 | `tests/unit/assistant/test_service.py` | `services/api/app/assistant_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-001 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-001 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/models.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-001 | `tests/unit/assistant/test_invariants.py` | `services/api/app/assistant_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-001 | `tests/unit/api/test_assistant_api.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-001 | `tests/unit/api/test_assistant_api.py` | `packages/assistant/src/spatial_assistant/models.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-001 | `tests/unit/api/test_assistant_api.py` | `services/api/app/assistant_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-001 | `tests/integration/test_assistant_stack.py` | `packages/assistant/src/spatial_assistant/service.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-001 | `tests/integration/test_assistant_stack.py` | `packages/assistant/src/spatial_assistant/models.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-001 | `tests/integration/test_assistant_stack.py` | `services/api/app/assistant_routes.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-002 | `tests/unit/assistant/test_knowledge.py` | `packages/assistant/src/spatial_assistant/knowledge.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-002 | `tests/unit/assistant/test_knowledge.py` | `packages/assistant/src/spatial_assistant/policy.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-002 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/knowledge.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-002 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/policy.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-002 | `tests/integration/test_assistant_stack.py` | `packages/assistant/src/spatial_assistant/knowledge.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-002 | `tests/integration/test_assistant_stack.py` | `packages/assistant/src/spatial_assistant/policy.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-003 | `tests/unit/assistant/test_text_retrieval.py` | `packages/assistant/src/spatial_assistant/retrieval.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-003 | `tests/unit/assistant/test_text_retrieval.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_text_retrieval.py` | `packages/assistant/src/spatial_assistant/text.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-003 | `tests/unit/assistant/test_text_retrieval.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_grounding_llm.py` | `packages/assistant/src/spatial_assistant/retrieval.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-003 | `tests/unit/assistant/test_grounding_llm.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-003 | `tests/unit/assistant/test_grounding_llm.py` | `packages/assistant/src/spatial_assistant/text.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_grounding_llm.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/retrieval.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/text.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-003 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/retrieval.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-003 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-003 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/text.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-003 | `tests/unit/assistant/test_evaluation.py` | `packages/assistant/src/spatial_assistant/retrieval.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_evaluation.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_evaluation.py` | `packages/assistant/src/spatial_assistant/text.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-003 | `tests/unit/assistant/test_evaluation.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-004 | `tests/unit/assistant/test_policy.py` | `packages/assistant/src/spatial_assistant/policy.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-004 | `tests/unit/assistant/test_policy.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-004 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/policy.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-004 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-004 | `tests/unit/api/test_assistant_api.py` | `packages/assistant/src/spatial_assistant/policy.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-004 | `tests/unit/api/test_assistant_api.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-004 | `tests/integration/test_assistant_stack.py` | `packages/assistant/src/spatial_assistant/policy.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-004 | `tests/integration/test_assistant_stack.py` | `packages/assistant/src/spatial_assistant/service.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-005 | `tests/unit/assistant/test_grounding_llm.py` | `packages/assistant/src/spatial_assistant/llm.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-005 | `tests/unit/assistant/test_grounding_llm.py` | `packages/assistant/src/spatial_assistant/llm_anthropic.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-005 | `tests/unit/assistant/test_grounding_llm.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-005 | `tests/unit/assistant/test_grounding_llm.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-005 | `tests/unit/assistant/test_grounding_llm.py` | `services/api/app/config.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-005 | `tests/unit/assistant/test_grounding_llm.py` | `services/api/app/main.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-005 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/llm.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-005 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/llm_anthropic.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-005 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-005 | `tests/unit/assistant/test_service.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-005 | `tests/unit/assistant/test_service.py` | `services/api/app/config.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-005 | `tests/unit/assistant/test_service.py` | `services/api/app/main.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-005 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/llm.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-005 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/llm_anthropic.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-005 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-005 | `tests/unit/assistant/test_invariants.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-005 | `tests/unit/assistant/test_invariants.py` | `services/api/app/config.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-005 | `tests/unit/assistant/test_invariants.py` | `services/api/app/main.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-005 | `tests/unit/api/test_config.py` | `packages/assistant/src/spatial_assistant/llm.py` | CONFIRMED (INFERRED) | 4 |
| REQ-AI-005 | `tests/unit/api/test_config.py` | `packages/assistant/src/spatial_assistant/llm_anthropic.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-005 | `tests/unit/api/test_config.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (INFERRED) | 4 |
| REQ-AI-005 | `tests/unit/api/test_config.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-005 | `tests/unit/api/test_config.py` | `services/api/app/config.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-005 | `tests/unit/api/test_config.py` | `services/api/app/main.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-005 | `tests/unit/api/test_assistant_api.py` | `packages/assistant/src/spatial_assistant/llm.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-005 | `tests/unit/api/test_assistant_api.py` | `packages/assistant/src/spatial_assistant/llm_anthropic.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-005 | `tests/unit/api/test_assistant_api.py` | `packages/assistant/src/spatial_assistant/grounding.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-005 | `tests/unit/api/test_assistant_api.py` | `packages/assistant/src/spatial_assistant/service.py` | CONFIRMED (INFERRED) | 1 |
| REQ-AI-005 | `tests/unit/api/test_assistant_api.py` | `services/api/app/config.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-005 | `tests/unit/api/test_assistant_api.py` | `services/api/app/main.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-006 | `tests/unit/api/test_assistant_api.py` | `services/api/app/assistant_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-AI-006 | `tests/unit/api/test_assistant_api.py` | `services/api/app/schemas.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-006 | `tests/unit/api/test_assistant_api.py` | `services/api/app/main.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-006 | `tests/unit/api/test_assistant_api.py` | `services/api/app/ratelimit.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/assistant_routes.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-AI-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/schemas.py` | CONFIRMED (INFERRED) | 3 |
| REQ-AI-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/main.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-AI-006 | `tests/contract/test_openapi_contract.py` | `services/api/app/ratelimit.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-AI-006 | `tests/integration/test_assistant_stack.py` | `services/api/app/assistant_routes.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-006 | `tests/integration/test_assistant_stack.py` | `services/api/app/schemas.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-006 | `tests/integration/test_assistant_stack.py` | `services/api/app/main.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-006 | `tests/integration/test_assistant_stack.py` | `services/api/app/ratelimit.py` | NOT CONFIRMED (black-box) | - |
| REQ-AI-007 | `tests/unit/assistant/test_evaluation.py` | `packages/assistant/src/spatial_assistant/evaluation.py` | CONFIRMED (EXTRACTED) | 1 |
| REQ-AI-007 | `tests/unit/assistant/test_evaluation.py` | `scripts/eval_assistant.py` | CONFIRMED (EXTRACTED) | 2 |
| REQ-HACC-001 | `tests/unit/api/test_hacc_api.py` | `packages/hacc/src/spatial_hacc/simulated.py` | CONFIRMED (INFERRED) | 1 |
| REQ-HACC-001 | `tests/unit/api/test_hacc_api.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-001 | `tests/unit/api/test_hacc_api.py` | `services/api/app/main.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-001 | `tests/unit/hacc/test_models_simulated.py` | `packages/hacc/src/spatial_hacc/simulated.py` | CONFIRMED (INFERRED) | 1 |
| REQ-HACC-001 | `tests/unit/hacc/test_models_simulated.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-001 | `tests/unit/hacc/test_models_simulated.py` | `services/api/app/main.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-001 | `tests/integration/test_hacc_stack.py` | `packages/hacc/src/spatial_hacc/simulated.py` | NOT CONFIRMED (black-box) | - |
| REQ-HACC-001 | `tests/integration/test_hacc_stack.py` | `services/api/app/hacc_routes.py` | NOT CONFIRMED (black-box) | - |
| REQ-HACC-001 | `tests/integration/test_hacc_stack.py` | `services/api/app/main.py` | NOT CONFIRMED (black-box) | - |
| REQ-HACC-002 | `tests/unit/hacc/test_http_source.py` | `packages/hacc/src/spatial_hacc/source.py` | CONFIRMED (INFERRED) | 1 |
| REQ-HACC-002 | `tests/unit/hacc/test_http_source.py` | `packages/hacc/src/spatial_hacc/http.py` | CONFIRMED (INFERRED) | 1 |
| REQ-HACC-002 | `tests/unit/hacc/test_http_source.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-002 | `tests/unit/api/test_hacc_api.py` | `packages/hacc/src/spatial_hacc/source.py` | CONFIRMED (INFERRED) | 1 |
| REQ-HACC-002 | `tests/unit/api/test_hacc_api.py` | `packages/hacc/src/spatial_hacc/http.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-002 | `tests/unit/api/test_hacc_api.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-002 | `tests/contract/test_openapi_contract.py` | `packages/hacc/src/spatial_hacc/source.py` | CONFIRMED (INFERRED) | 1 |
| REQ-HACC-002 | `tests/contract/test_openapi_contract.py` | `packages/hacc/src/spatial_hacc/http.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-002 | `tests/contract/test_openapi_contract.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-003 | `tests/unit/hacc/test_models_simulated.py` | `packages/hacc/src/spatial_hacc/models.py` | CONFIRMED (INFERRED) | 1 |
| REQ-HACC-003 | `tests/unit/hacc/test_models_simulated.py` | `packages/hacc/src/spatial_hacc/simulated.py` | CONFIRMED (INFERRED) | 1 |
| REQ-HACC-003 | `tests/unit/hacc/test_http_source.py` | `packages/hacc/src/spatial_hacc/models.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-003 | `tests/unit/hacc/test_http_source.py` | `packages/hacc/src/spatial_hacc/simulated.py` | CONFIRMED (INFERRED) | 3 |
| REQ-HACC-003 | `tests/integration/test_hacc_stack.py` | `packages/hacc/src/spatial_hacc/models.py` | NOT CONFIRMED (black-box) | - |
| REQ-HACC-003 | `tests/integration/test_hacc_stack.py` | `packages/hacc/src/spatial_hacc/simulated.py` | NOT CONFIRMED (black-box) | - |
| REQ-HACC-004 | `tests/unit/api/test_hacc_api.py` | `services/api/app/auth.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-HACC-004 | `tests/unit/api/test_hacc_api.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-004 | `tests/contract/test_openapi_contract.py` | `services/api/app/auth.py` | CONFIRMED (EXTRACTED) | 3 |
| REQ-HACC-004 | `tests/contract/test_openapi_contract.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-004 | `tests/integration/test_hacc_stack.py` | `services/api/app/auth.py` | NOT CONFIRMED (black-box) | - |
| REQ-HACC-004 | `tests/integration/test_hacc_stack.py` | `services/api/app/hacc_routes.py` | NOT CONFIRMED (black-box) | - |
| REQ-HACC-005 | `tests/unit/domain/test_beds.py` | `packages/domain/src/spatial_domain/beds.py` | CONFIRMED (INFERRED) | 1 |
| REQ-HACC-005 | `tests/unit/domain/test_beds.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-005 | `tests/unit/api/test_hacc_api.py` | `packages/domain/src/spatial_domain/beds.py` | CONFIRMED (INFERRED) | 3 |
| REQ-HACC-005 | `tests/unit/api/test_hacc_api.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-005 | `tests/contract/test_openapi_contract.py` | `packages/domain/src/spatial_domain/beds.py` | CONFIRMED (INFERRED) | 3 |
| REQ-HACC-005 | `tests/contract/test_openapi_contract.py` | `services/api/app/hacc_routes.py` | CONFIRMED (INFERRED) | 2 |
| REQ-HACC-005 | `tests/integration/test_hacc_stack.py` | `packages/domain/src/spatial_domain/beds.py` | NOT CONFIRMED (black-box) | - |
| REQ-HACC-005 | `tests/integration/test_hacc_stack.py` | `services/api/app/hacc_routes.py` | NOT CONFIRMED (black-box) | - |

## Resumo

- CONFIRMED (EXTRACTED): **89**
- CONFIRMED (INFERRED): **145**
- NOT CONFIRMED (black-box): **44**
- NOT CONFIRMED: **10**
- NOT IN GRAPH: **0**

- `NOT CONFIRMED (black-box)`: teste de integracao/E2E/performance; exercita o codigo por HTTP/MQTT/Docker,
  o que a analise estatica nao enxerga (esperado).
- `NOT CONFIRMED`: teste unitario/contrato SEM caminho de dependencia ate o codigo declarado -> revisar a
  matriz (o teste declarado pode nao cobrir esse arquivo). Nao e erro automatico: o teste pode ler artefatos
  (ex.: `.env.example`) em vez de importar o codigo.
- `NOT IN GRAPH`: o Graphify nao indexa o arquivo (ex.: scripts fora do pacote analisado).
