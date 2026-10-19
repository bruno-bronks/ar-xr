# Graph Report - AR_XR  (2026-10-19)

## Corpus Check
- 166 files · ~71,028 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 38 file(s) not represented in the graph (top: .pgm 8, (none) 7, .asmdef 3)

## Summary
- 1705 nodes · 4080 edges · 110 communities (73 shown, 37 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 554 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `90d889d7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_status.py
- test_health.py
- Communities (70 total, 30 thin omitted)
- Registry
- test_equipment_api.py
- Catálogo de requisitos
- SPATIAL AI PLATFORM — Plano mestre de execução no Antigravity
- pytest
- test_hygiene.py
- Comportamento
- Repository
- ADR-0001 — Monolito modular primeiro; três deployables no MVP
- SPEC-002 — Avaliação de estado do equipamento
- Avaliação de ferramentas
- SPEC-005 — Ingestão de telemetria e persistência
- json
- C4 — Nível 1: Contexto
- test_traceability.py
- check.sh script
- dev-setup.sh script
- smoke.sh
- spatial-ai-platform
- test_telemetry_schema.py
- _stack.py
- test_telemetry.py
- worker/main.py
- routes.py
- test_scenarios.py
- test_handler.py
- app/main.py
- test_architecture.py
- test_correlation.py
- test_compose_smoke.py
- app.js
- collections_abc
- health.py
- Fact
- graph_crosscheck.py
- trace_edges.py
- pathlib
- 12. Roadmap com critérios de conclusão
- Graph Report - AR_XR  (2026-10-19)
- AGENTS.md — instruções para agentes de código neste repositório
- system
- Runbook — desenvolvimento local
- CURRENT_STATE.md
- Spatial AI Platform
- SPEC-007 — Simulador de equipamentos e painel web 2D
- SpatialApiClient
- graph/ — índice auxiliar de conhecimento (Graphify)
- 9. Graphify, Dreaming, Cloud e Outcome
- Cruzamento matriz × grafo (Graphify)
- verify-z.sh script
- OverlayViewModel
- Packages/manifest.json
- test_panel.py
- SessionDriver
- Task
- telemetry.py
- test_generate_qr.py
- test_consumer.py
- ClientConfigTests
- SPEC-008 — Cliente AR Android (Unity)
- handler.py
- SpatialArApp
- QrScanner
- sqlalchemy
- test_latency.py
- .TryParse
- pathlib
- .__call__
- test_formal_z.py
- Spatial.Ar.Core.Tests.csproj
- ADR-0003 — Arquitetura do cliente AR: núcleo C# puro testável + cola Unity fina
- generate_qr.py
- api
- IClientLog
- package.json
- SensorDto
- Checklist de validação do cliente AR em aparelho físico
- SessionOptions
- StatusColor
- CURRENT_STATE â€” memÃ³ria determinÃ­stica do projeto
- TransportError
- next_backoff
- mutated_events
- Metodologia de medição (modelo)
- qr/manifest.json

## God Nodes (most connected - your core abstractions)
1. `Communities (74 total, 29 thin omitted)` - 46 edges
2. `Repository` - 45 edges
3. `Status` - 39 edges
4. `make_client()` - 38 edges
5. `MarkerSession` - 37 edges
6. `MarkerSessionTests` - 36 edges
7. `Quality` - 32 edges
8. `auth()` - 32 edges
9. `InMemoryRepository` - 31 edges
10. `_eval()` - 27 edges

## Surprising Connections (you probably didn't know these)
- `Ameaças e controles` --references--> `audit()`  [INFERRED]
  docs/architecture/threat-model.md → services/api/app/audit.py
- `Metodologia de medição (modelo)` --references--> `publish()`  [INFERRED]
  docs/outcomes/metrics.md → tests/integration/_stack.py
- `Readiness — `GET /health/ready`` --references--> `ok()`  [INFERRED]
  specs/functional/SPEC-001-foundation.md → tests/unit/api/_app.py
- `C4 — Nível 2: Contêineres` --references--> `worker()`  [INFERRED]
  docs/architecture/containers.md → tests/unit/storage/test_repository_contract.py
- `Decisão` --references--> `OverlayViewModel`  [INFERRED]
  docs/adr/0003-ar-client-architecture.md → clients/ar-unity/Packages/com.spatial.ar.core/Runtime/OverlayViewModel.cs

## Import Cycles
- None detected.

## Communities (110 total, 37 thin omitted)

### Community 0 - "test_status.py"
Cohesion: 0.09
Nodes (52): God Nodes (most connected - your core abstractions), Suggested Questions, evaluate_status(), Quality, Reading, _require_aware(), _require_finite(), Status (+44 more)

### Community 1 - "test_health.py"
Cohesion: 0.15
Nodes (14): _boom(), _client(), _fail(), _ok(), test_check_database_false_and_silent_on_unreachable(), test_live_does_not_execute_checks(), test_live_ignores_failing_dependencies(), test_live_returns_200() (+6 more)

### Community 2 - "Communities (70 total, 30 thin omitted)"
Cohesion: 0.04
Nodes (46): Communities (74 total, 29 thin omitted), Community 0 - "test_status.py", Community 10 - "Repository", Community 11 - "ADR-0001 — Monolito modular primeiro; três deployables no MVP", Community 12 - "SPEC-002 — Avaliação de estado do equipamento", Community 13 - "Avaliação de ferramentas", Community 14 - "SPEC-005 — Ingestão de telemetria e persistência", Community 15 - "json" (+38 more)

### Community 3 - "Registry"
Cohesion: 0.11
Nodes (22): Found, NotFound, Registry, Invariantes, Pendente (Fase 1), Problema, Regras, SPEC-003 — Resolução de marker/QR (+14 more)

### Community 4 - "test_equipment_api.py"
Cohesion: 0.05
Nodes (62): _dump(), _generate(), test_ar_fixtures_match_what_the_real_api_returns(), test_fixture_semantics_are_what_the_client_tests_assume(), test_no_orphan_fixture_files(), _app(), _operations(), populated() (+54 more)

### Community 5 - "Catálogo de requisitos"
Cohesion: 0.25
Nodes (7): Catálogo de requisitos, Cliente AR (Fase 2), Decisões de default explícitas (precisam de aprovação), Engenharia e plataforma, Manutenção industrial (vertical A), Planejados (fases futuras — sem implementação), Segurança

### Community 6 - "SPATIAL AI PLATFORM — Plano mestre de execução no Antigravity"
Cohesion: 0.14
Nodes (14): 0. Regras operacionais, 10. Design patterns com justificativa, 11. Testes e quality gates, 13. Primeira execução — instrução exata ao agente, 14. Critério de sucesso do primeiro marco, 1. Visão e outcomes, 2. Stack de referência, 3. Arquitetura lógica (+6 more)

### Community 7 - "pytest"
Cohesion: 0.16
Nodes (14): Settings, ok(), test_demo_mode_is_allowed_outside_production(), test_oidc_mode_fails_closed_until_an_idp_is_approved(), test_production_with_demo_auth_is_refused_by_settings(), test_production_with_demo_auth_is_refused_even_if_settings_validation_is_bypassed(), test_settings_default_to_demo_outside_production(), _env() (+6 more)

### Community 8 - "test_hygiene.py"
Cohesion: 0.21
Nodes (6): _compose(), test_ci_workflow_runs_all_required_gates(), test_compose_has_expected_services(), test_compose_images_are_pinned_and_not_privileged(), test_compose_published_ports_bind_loopback_only(), test_compose_services_have_healthchecks_and_api_waits_for_dependencies()

### Community 9 - "Comportamento"
Cohesion: 0.11
Nodes (16): Ameaças e controles, Ativos, Riscos residuais assumidos (Fases 0–1), Threat model (STRIDE) — versão inicial, ready(), Ambiente local, Atores, Comportamento (+8 more)

### Community 10 - "Repository"
Cohesion: 0.06
Nodes (41): Decisão, O que existe (verificado por execuÃ§Ã£o), C4 — Nível 3: Componentes, Pacotes e módulos (estado real da Fase 1), Padrões em uso (e por quê), Regras de fronteira (verificadas hoje por revisão; teste automático pendente), TelemetryEvent, InMemoryRepository (+33 more)

### Community 11 - "ADR-0001 — Monolito modular primeiro; três deployables no MVP"
Cohesion: 0.10
Nodes (18): ADR-0001 — Monolito modular primeiro; três deployables no MVP, Alternativas rejeitadas, Consequências, Contexto, Critérios para extrair um microserviço (todos exigidos), Decisão, Status, ADR-0002 — Pacote de persistência compartilhado e autenticação demo (+10 more)

### Community 12 - "SPEC-002 — Avaliação de estado do equipamento"
Cohesion: 0.25
Nodes (7): Cenários obrigatórios do plano cobertos, Entradas, Invariantes (verificados por Hypothesis no modelo), Problema, Regras (ordem de precedência), Riscos, SPEC-002 — Avaliação de estado do equipamento

### Community 13 - "Avaliação de ferramentas"
Cohesion: 0.25
Nodes (8): Ainda não instaladas (aguardam necessidade/aprovação), Avaliação de ferramentas, Dreaming — ainda NÃO instalado/usado (decisão sua), Graphify — como foi usado (e limites), Instaladas e usadas, Inventário do ambiente (2026-10-19, Windows 11), Rede corporativa: o que está bloqueado (e o que NÃO foi contornado), Resultado real do CZT

### Community 14 - "SPEC-005 — Ingestão de telemetria e persistência"
Cohesion: 0.14
Nodes (12): Critérios de aceitação (Fase 0 — contrato), Evento, Pendente (Fase 1), Semântica de entrega (política definida), SPEC-004 — Contrato de telemetria, idempotência e ordenação, Critérios de aceitação, Fora de escopo (fase futura), Modelo de dados (PostgreSQL, Alembic `0001_initial`) (+4 more)

### Community 15 - "json"
Cohesion: 0.18
Nodes (6): test_duplicate_json_keys_last_wins_and_still_validated(), _load(), test_crosscheck_never_walks_through_external_nodes(), test_declared_gaps_do_not_become_edges(), test_edge_vocabulary_matches_the_plan(), test_every_edge_is_verified_and_points_to_an_existing_artifact_or_requirement()

### Community 17 - "test_traceability.py"
Cohesion: 0.30
Nodes (11): _cells(), _is_marker(), _rows(), test_each_listed_test_file_mentions_its_requirement(), test_every_outcome_exists_in_metrics(), test_every_path_column_is_filled_or_explicitly_marked(), test_every_requirement_in_catalog_has_exactly_one_row(), test_partial_rows_explain_what_is_pending() (+3 more)

### Community 22 - "smoke.sh"
Cohesion: 0.50
Nodes (3): BASE_URL, smoke.sh script, TEST_DATABASE_URL

### Community 27 - "test_telemetry_schema.py"
Cohesion: 0.16
Nodes (3): test_invalid_events_are_rejected(), test_non_finite_numbers_are_not_valid_json_numbers(), test_valid_events_pass()

### Community 35 - "_stack.py"
Cohesion: 0.22
Nodes (18): controlled_data(), equipment_status(), event(), event_count(), feed_equipment(), iso(), new_id(), publish() (+10 more)

### Community 36 - "test_telemetry.py"
Cohesion: 0.17
Nodes (16): _raw(), _reason(), test_all_contract_invalid_events_are_rejected_as_schema_violation(), test_all_contract_valid_events_parse(), test_equipment_id_from_topic(), test_future_timestamp_within_tolerance_is_accepted_boundary_inclusive(), test_integer_too_large_for_float_is_schema_violation_not_crash(), test_invalid_utf8_is_invalid_encoding() (+8 more)

### Community 37 - "worker/main.py"
Cohesion: 0.15
Nodes (5): main(), SimulatorSettings, _heartbeat_loop(), main(), WorkerSettings

### Community 38 - "routes.py"
Cohesion: 0.06
Nodes (42): audit(), resource_id(), Authenticator, build_authenticator(), DemoAuthenticator, Principal, require_principal(), FixedWindowLimiter (+34 more)

### Community 39 - "test_scenarios.py"
Cohesion: 0.13
Nodes (19): Message, _noise(), sensor_value(), SimConfig, Simulation, _compress(), test_config_rejects_non_positive_values(), test_dropout_equipment_goes_offline_and_comes_back() (+11 more)

### Community 40 - "test_handler.py"
Cohesion: 0.18
Nodes (14): Disposition, with_(), without(), _bytes(), _handler(), test_duplicate_message_is_reported_and_not_rewritten(), test_invalid_messages_are_rejected_with_reason_and_do_not_write(), test_old_event_is_history_only() (+6 more)

### Community 41 - "app/main.py"
Cohesion: 0.15
Nodes (5): Defeitos encontrados DURANTE a Fase 1 (e corrigidos), check_database(), create_app(), _find_panel_dir(), get_app()

### Community 42 - "test_architecture.py"
Cohesion: 0.24
Nodes (7): _imports(), _package_imports(), test_api_never_touches_table_definitions_directly(), test_common_package_has_no_domain_or_framework_dependencies(), test_domain_is_pure_no_frameworks_no_io_libraries_no_other_internal_package(), test_services_do_not_depend_on_each_other_or_on_foreign_stacks(), test_storage_depends_only_on_domain_and_never_on_services()

### Community 43 - "test_correlation.py"
Cohesion: 0.10
Nodes (13): configure_logging(), JsonFormatter, normalize_correlation_id(), _client(), test_access_log_carries_correlation_id_without_query_string(), test_each_request_without_header_gets_distinct_id(), test_echoes_valid_incoming_id(), test_generates_uuid_when_header_missing() (+5 more)

### Community 44 - "test_compose_smoke.py"
Cohesion: 0.27
Nodes (6): _get(), _lower(), test_correlation_id_round_trip(), test_live(), test_ready_body_contains_no_connection_details(), test_ready_with_real_postgres_and_mosquitto()

### Community 45 - "app.js"
Cohesion: 0.28
Nodes (12): ageSeconds(), api(), el(), els, formatValue(), markStale(), refresh(), renderAlerts() (+4 more)

### Community 46 - "collections_abc"
Cohesion: 0.12
Nodes (8): pg_engine(), pg_url(), blank_db(), _tables(), test_database_constraints_reject_invalid_rows(), test_models_match_migrations(), test_upgrade_creates_schema_and_downgrade_removes_it(), test_upgrade_is_idempotent()

### Community 47 - "health.py"
Cohesion: 0.16
Nodes (8): build_router(), live(), check_broker(), Live, Ready, ReadyChecks, test_check_broker_false_when_port_closed(), test_check_broker_true_when_port_open()

### Community 48 - "Fact"
Cohesion: 0.06
Nodes (56): ApiOutcome, BadResponse, InvalidInput, NetworkError, NotFound, Ok, RateLimited, ServerError (+48 more)

### Community 49 - "graph_crosscheck.py"
Cohesion: 0.16
Nodes (8): equipment_id_from_topic(), _cells(), connected(), load_graph(), main(), nodes_of(), HandleResult, test_header_has_expected_columns()

### Community 50 - "trace_edges.py"
Cohesion: 0.39
Nodes (5): build_edges(), _cells(), _is_gap(), main(), render()

### Community 51 - "pathlib"
Cohesion: 0.27
Nodes (7): _backticked(), test_every_backticked_path_in_state_exists(), test_every_markdown_link_in_state_resolves(), test_requirements_and_decisions_cited_in_state_exist_in_the_catalog(), test_state_declares_date_branch_and_phase(), test_service_dockerfiles_run_as_non_root(), test_adr_files_have_status_and_decision_sections()

### Community 52 - "12. Roadmap com critérios de conclusão"
Cohesion: 0.25
Nodes (8): 12. Roadmap com critérios de conclusão, Fase 0 — Foundation, Fase 1 — Industrial vertical (sem AR nativa), Fase 2 — AR Android, Fase 3 — IA assistiva, Fase 4 — HACC Spatial, Fase 5 — Computer Vision e IoT real, Fase 6 — Cloud e escala

### Community 53 - "Graph Report - AR_XR  (2026-10-19)"
Cohesion: 0.25
Nodes (8): Community Hubs (Navigation), Corpus Check, Graph Freshness, Graph Report - AR_XR  (2026-10-19), Import Cycles, Knowledge Gaps, Summary, Surprising Connections (you probably didn't know these)

### Community 54 - "AGENTS.md — instruções para agentes de código neste repositório"
Cohesion: 0.33
Nodes (6): AGENTS.md — instruções para agentes de código neste repositório, Ambiente conhecido (Windows), Comandos, Convenções, Fluxo Spec-Driven (por feature), Regras inegociáveis

### Community 55 - "system"
Cohesion: 0.10
Nodes (6): ProjectSetup, Spatial.Ar.Core.Tests, Spatial.Ar.Unity.Editor, Spatial.Ar.Unity, Spatial.Ar.Core, Fixtures

### Community 56 - "Runbook — desenvolvimento local"
Cohesion: 0.22
Nodes (9): Diagnóstico rápido, Fluxo completo (Fase 1), Grafo (Graphify), Primeira vez, Problemas conhecidos, Reset total do ambiente local, Runbook — desenvolvimento local, Testes que dependem de infraestrutura (+1 more)

### Community 58 - "Spatial AI Platform"
Cohesion: 0.40
Nodes (5): Demonstração (critério do marco), Mapa do repositório, Pré-requisitos, Spatial AI Platform, Testes e gates

### Community 59 - "SPEC-007 — Simulador de equipamentos e painel web 2D"
Cohesion: 0.40
Nodes (4): Critérios de aceitação, Painel (`clients/web-fallback`), Simulador (`services/equipment-simulator`), SPEC-007 — Simulador de equipamentos e painel web 2D

### Community 60 - "SpatialApiClient"
Cohesion: 0.09
Nodes (17): UnityWebRequestTransport, AlertDto, EquipmentId, Limit, RaisedAt, Rule, SensorType, Severity (+9 more)

### Community 61 - "graph/ — índice auxiliar de conhecimento (Graphify)"
Cohesion: 0.33
Nodes (6): Como usar, Cruzamento matriz × grafo, Duas camadas de arestas (nunca misturadas), Ferramenta, graph/ — índice auxiliar de conhecimento (Graphify), O que o uso do grafo revelou

### Community 70 - "9. Graphify, Dreaming, Cloud e Outcome"
Cohesion: 0.40
Nodes (5): 9. Graphify, Dreaming, Cloud e Outcome, Cloud, Dreaming, Graphify, Outcome

### Community 74 - "OverlayViewModel"
Cohesion: 0.13
Nodes (15): EquipmentStatus, Critical, Normal, Offline, Unknown, Warning, OverlayViewModel, AlertLines (+7 more)

### Community 75 - "Packages/manifest.json"
Cohesion: 0.09
Nodes (21): dependencies, com.unity.modules.androidjni, com.unity.modules.imgui, com.unity.modules.jsonserialize, com.unity.modules.physics, com.unity.modules.ui, com.unity.modules.unitywebrequest, com.unity.nuget.newtonsoft-json (+13 more)

### Community 76 - "test_panel.py"
Cohesion: 0.16
Nodes (13): browser(), page(), quiet_simulator(), _shot(), test_hostile_equipment_name_is_rendered_as_text_and_never_executes(), test_invalid_token_shows_visible_error_and_no_data(), test_late_response_from_previous_org_is_discarded_after_switching(), test_panel_is_usable_on_a_360px_phone_without_horizontal_scroll() (+5 more)

### Community 77 - "SessionDriver"
Cohesion: 0.30
Nodes (5): SessionDriver, State, Rig, SessionDriverTests, FakeClock

### Community 79 - "telemetry.py"
Cohesion: 0.17
Nodes (9): _identifier(), parse_payload(), _parse_timestamp(), _reject_constant(), reject_future(), RejectReason, TelemetryRejected, _violation() (+1 more)

### Community 80 - "test_generate_qr.py"
Cohesion: 0.14
Nodes (9): _load(), _manifest(), out(), test_committed_qr_assets_are_up_to_date(), test_every_case_has_png_pgm_and_manifest_entry(), test_generation_is_deterministic(), test_opencv_independently_decodes_every_pgm_to_its_exact_content(), test_output_never_contains_secrets() (+1 more)

### Community 81 - "test_consumer.py"
Cohesion: 0.22
Nodes (15): _consumer(), FakeClient, FakeMessage, _msg(), test_acks_after_successful_persistence(), test_acks_duplicates_and_rejections_because_they_are_final(), test_after_a_failure_further_messages_are_neither_processed_nor_acked(), record() (+7 more)

### Community 82 - "ClientConfigTests"
Cohesion: 0.17
Nodes (7): ClientConfig, BaseUrl, IsDevelopmentBuild, Token, Regras que a cola NÃO pode quebrar, Segurança (REQ-AR-005), ClientConfigTests

### Community 83 - "SPEC-008 — Cliente AR Android (Unity)"
Cohesion: 0.13
Nodes (11): Arquitetura do cliente (duas camadas), Critérios de aceitação, Estado de apresentação (REQ-AR-003, D-017), Fluxo, Geração dos QR de teste (REQ-AR-006), Problema e atores, Rede em desenvolvimento, Riscos (+3 more)

### Community 84 - "handler.py"
Cohesion: 0.18
Nodes (4): Consumer, MqttClient, MessageHandler, Stats

### Community 86 - "QrScanner"
Cohesion: 0.13
Nodes (7): QrScanner, QrPayload, Cliente AR (Unity) — Fase 2, Estrutura, Montagem (primeira vez, ~30 min) — no PC com Unity Hub, Testes do núcleo, Versões (D-012, conferidas em `packages.unity.com`)

### Community 87 - "sqlalchemy"
Cohesion: 0.19
Nodes (3): _reading_columns(), upgrade(), _tz()

### Community 88 - "test_latency.py"
Cohesion: 0.21
Nodes (7): compose(), latest_value(), quiet_simulator(), _percentile(), publisher(), quiet_simulator(), test_publish_to_api_latency_p95_is_below_budget()

### Community 90 - "pathlib"
Cohesion: 0.21
Nodes (6): _config(), downgrade(), main(), upgrade(), apply_seed(), test_seed_is_idempotent_and_does_not_touch_telemetry()

### Community 92 - "test_formal_z.py"
Cohesion: 0.26
Nodes (6): _find_java(), test_a_syntax_error_is_rejected(), test_an_injected_type_error_is_rejected(), test_spec_parses_and_typechecks_with_zero_warnings_and_errors(), _typecheck(), test_no_env_file_is_tracked_by_git()

### Community 93 - "Spatial.Ar.Core.Tests.csproj"
Cohesion: 0.17
Nodes (10): net10.0, netstandard2.1, Microsoft.NET.Test.Sdk (17.12.0), xunit (2.9.2), xunit.runner.visualstudio (2.8.2), ZXing.Net (0.16.9), Newtonsoft.Json (13.0.3), Microsoft.NET.Sdk (+2 more)

### Community 94 - "ADR-0003 — Arquitetura do cliente AR: núcleo C# puro testável + cola Unity fina"
Cohesion: 0.24
Nodes (6): ADR-0003 — Arquitetura do cliente AR: núcleo C# puro testável + cola Unity fina, Alternativas rejeitadas, Consequências, Contexto, Decisão, Status

### Community 95 - "generate_qr.py"
Cohesion: 0.27
Nodes (3): generate(), main(), _pgm()

### Community 96 - "api"
Cohesion: 0.33
Nodes (7): api(), test_authorization_is_enforced_over_real_http(), test_simulator_data_reaches_the_api_fresh_and_complete(), fresh(), test_steady_equipment_is_normal_and_states_are_all_valid(), settled(), test_the_three_test_qr_codes_resolve_over_real_http()

### Community 97 - "IClientLog"
Cohesion: 0.31
Nodes (4): UnityLog, IClientLog, NullClientLog, RecordingLog

### Community 98 - "package.json"
Cohesion: 0.22
Nodes (8): dependencies, com.unity.nuget.newtonsoft-json, description, displayName, com.unity.nuget.newtonsoft-json, name, unity, version

### Community 99 - "SensorDto"
Cohesion: 0.22
Nodes (9): SensorDto, Crit, ObservedAt, Quality, SensorType, Unit, Valid, Value (+1 more)

### Community 100 - "Checklist de validação do cliente AR em aparelho físico"
Cohesion: 0.25
Nodes (8): 0. Preparação (uma vez), 1. Cenários funcionais, 2. Degradação (REQ-AR-004), 3. Câmera e ancoragem, 4. Medições (por aparelho — REQ-AR-007), 5. Segurança, Assinatura da execução, Checklist de validação do cliente AR em aparelho físico

### Community 101 - "SessionOptions"
Cohesion: 0.29
Nodes (7): SessionOptions, FailuresBeforeNoConnection, MessageDisplay, PollHangTimeout, PollInterval, QrDebounce, StaleAfter

### Community 102 - "StatusColor"
Cohesion: 0.29
Nodes (7): StatusColor, Amber, Gray, Green, None, Purple, Red

### Community 103 - "CURRENT_STATE â€” memÃ³ria determinÃ­stica do projeto"
Cohesion: 0.40
Nodes (5): CURRENT_STATE â€” memÃ³ria determinÃ­stica do projeto, DecisÃµes pendentes de aprovaÃ§Ã£o, EvidÃªncias executadas (`docs/evidence/phase-1/`), O que NÃƒO foi feito / nÃ£o estÃ¡ verificado, PrÃ³ximo passo (somente apÃ³s aprovaÃ§Ã£o)

### Community 104 - "TransportError"
Cohesion: 0.50
Nodes (4): TransportError, Network, None, Timeout

## Knowledge Gaps
- **119 isolated node(s):** `Ok`, `InvalidInput`, `NotFound`, `Unauthorized`, `RateLimited` (+114 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 640 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `audit()` connect `routes.py` to `Comportamento`, `Graph Report - AR_XR  (2026-10-19)`?**
  _High betweenness centrality (0.369) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `Repository` (e.g. with `Decisão` and `Regras de fronteira (verificadas hoje por revisão; teste automático pendente)`) actually correct?**
  _`Repository` has 35 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Ok`, `InvalidInput`, `NotFound` to the rest of the system?**
  _119 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_status.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08756756756756756 - nodes in this community are weakly interconnected._
- **Why does `Endpoints (todos `GET`, exceto os planejados)` connect `routes.py` to `Fact`?**
  _High betweenness centrality (0.355) - this node is a cross-community bridge._
- **Should `Communities (70 total, 30 thin omitted)` be split into smaller, more focused modules?**
  _Cohesion score 0.043478260869565216 - nodes in this community are weakly interconnected._
- **Should `Registry` be split into smaller, more focused modules?**
  _Cohesion score 0.10953058321479374 - nodes in this community are weakly interconnected._