# Graph Report - AR_XR  (2026-10-19)

## Corpus Check
- 117 files · ~52,769 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 17 file(s) not represented in the graph (top: (none) 6, .in 3, .tex 3)

## Summary
- 1203 nodes · 2752 edges · 74 communities (45 shown, 29 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 393 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `35f88676`
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
- migrate.py
- health.py
- pytest
- graph_crosscheck.py
- trace_edges.py
- pathlib
- 12. Roadmap com critérios de conclusão
- Graph Report - AR_XR  (2026-10-19)
- AGENTS.md — instruções para agentes de código neste repositório
- CURRENT_STATE — memória determinística do projeto
- Runbook — desenvolvimento local
- graph/README.md
- Spatial AI Platform
- SPEC-007 — Simulador de equipamentos e painel web 2D
- graph/ — índice auxiliar de conhecimento (Graphify)
- 9. Graphify, Dreaming, Cloud e Outcome
- Cruzamento matriz × grafo (Graphify)
- verify-z.sh script

## God Nodes (most connected - your core abstractions)
1. `Repository` - 44 edges
2. `Communities (70 total, 30 thin omitted)` - 41 edges
3. `Status` - 39 edges
4. `make_client()` - 36 edges
5. `Quality` - 31 edges
6. `InMemoryRepository` - 30 edges
7. `auth()` - 30 edges
8. `evaluate_status()` - 27 edges
9. `_eval()` - 27 edges
10. `parse_payload()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Regras de fronteira (verificadas hoje por revisão; teste automático pendente)` --references--> `Repository`  [INFERRED]
  docs/architecture/components.md → packages/storage/src/spatial_storage/repository.py
- `Ameaças e controles` --references--> `audit()`  [INFERRED]
  docs/architecture/threat-model.md → services/api/app/audit.py
- `Readiness — `GET /health/ready`` --references--> `ok()`  [INFERRED]
  specs/functional/SPEC-001-foundation.md → tests/unit/api/_app.py
- `Pacotes e módulos (estado real da Fase 1)` --references--> `Registry`  [INFERRED]
  docs/architecture/components.md → packages/domain/src/spatial_domain/markers.py
- `Suggested Questions` --references--> `Registry`  [INFERRED]
  docs/evidence/phase-1/graph-report.md → packages/domain/src/spatial_domain/markers.py

## Import Cycles
- None detected.

## Communities (74 total, 29 thin omitted)

### Community 0 - "test_status.py"
Cohesion: 0.09
Nodes (50): God Nodes (most connected - your core abstractions), evaluate_status(), Quality, Reading, _require_aware(), _require_finite(), Status, Threshold (+42 more)

### Community 1 - "test_health.py"
Cohesion: 0.13
Nodes (16): check_broker(), _boom(), _client(), _fail(), _ok(), test_check_broker_false_when_port_closed(), test_check_broker_true_when_port_open(), test_live_does_not_execute_checks() (+8 more)

### Community 2 - "Communities (70 total, 30 thin omitted)"
Cohesion: 0.05
Nodes (41): Communities (70 total, 30 thin omitted), Community 0 - "test_status.py", Community 10 - "Repository", Community 11 - "ADR-0001 — Monolito modular primeiro; três deployables no MVP", Community 12 - "SPEC-002 — Avaliação de estado do equipamento", Community 13 - "Avaliação de ferramentas", Community 14 - "SPEC-005 — Ingestão de telemetria e persistência", Community 15 - "C4 — Nível 3: Componentes" (+33 more)

### Community 3 - "Registry"
Cohesion: 0.11
Nodes (21): Found, NotFound, Registry, Invariantes, Pendente (Fase 1), Problema, Regras, SPEC-003 — Resolução de marker/QR (+13 more)

### Community 4 - "test_equipment_api.py"
Cohesion: 0.06
Nodes (57): _app(), _operations(), populated(), _schema_for(), test_api_has_no_route_outside_the_contract(), test_authenticated_responses_conform_to_contract_schemas(), test_every_documented_status_code_is_a_declared_response(), test_health_responses_conform_to_contract_schemas() (+49 more)

### Community 5 - "Catálogo de requisitos"
Cohesion: 0.29
Nodes (6): Catálogo de requisitos, Decisões de default explícitas (precisam de aprovação), Engenharia e plataforma, Manutenção industrial (vertical A), Planejados (fases futuras — sem implementação), Segurança

### Community 6 - "SPATIAL AI PLATFORM — Plano mestre de execução no Antigravity"
Cohesion: 0.14
Nodes (14): 0. Regras operacionais, 10. Design patterns com justificativa, 11. Testes e quality gates, 13. Primeira execução — instrução exata ao agente, 14. Critério de sucesso do primeiro marco, 1. Visão e outcomes, 2. Stack de referência, 3. Arquitetura lógica (+6 more)

### Community 7 - "pytest"
Cohesion: 0.30
Nodes (8): Settings, _env(), test_database_url_is_required(), test_defaults(), test_invalid_environment_rejected(), test_invalid_mqtt_port_rejected(), test_reads_overrides_from_environment(), test_secret_never_appears_in_repr_or_str()

### Community 8 - "test_hygiene.py"
Cohesion: 0.11
Nodes (13): _find_java(), test_a_syntax_error_is_rejected(), test_an_injected_type_error_is_rejected(), test_spec_parses_and_typechecks_with_zero_warnings_and_errors(), _typecheck(), _compose(), test_ci_workflow_runs_all_required_gates(), test_compose_has_expected_services() (+5 more)

### Community 9 - "Comportamento"
Cohesion: 0.11
Nodes (16): Ameaças e controles, Ativos, Riscos residuais assumidos (Fases 0–1), Threat model (STRIDE) — versão inicial, ready(), Ambiente local, Atores, Comportamento (+8 more)

### Community 10 - "Repository"
Cohesion: 0.06
Nodes (38): Decisão, C4 — Nível 2: Contêineres, TelemetryEvent, InMemoryRepository, _tz(), _equipment(), PostgresRepository, EquipmentRecord (+30 more)

### Community 11 - "ADR-0001 — Monolito modular primeiro; três deployables no MVP"
Cohesion: 0.08
Nodes (20): ADR-0001 — Monolito modular primeiro; três deployables no MVP, Alternativas rejeitadas, Consequências, Contexto, Critérios para extrair um microserviço (todos exigidos), Decisão, Status, ADR-0002 — Pacote de persistência compartilhado e autenticação demo (+12 more)

### Community 12 - "SPEC-002 — Avaliação de estado do equipamento"
Cohesion: 0.25
Nodes (7): Cenários obrigatórios do plano cobertos, Entradas, Invariantes (verificados por Hypothesis no modelo), Problema, Regras (ordem de precedência), Riscos, SPEC-002 — Avaliação de estado do equipamento

### Community 13 - "Avaliação de ferramentas"
Cohesion: 0.29
Nodes (7): Ainda não instaladas (aguardam necessidade/aprovação), Avaliação de ferramentas, Dreaming — ainda NÃO instalado/usado (decisão sua), Graphify — como foi usado (e limites), Instaladas e usadas, Inventário do ambiente (2026-10-19, Windows 11), Resultado real do CZT

### Community 14 - "SPEC-005 — Ingestão de telemetria e persistência"
Cohesion: 0.14
Nodes (12): Critérios de aceitação (Fase 0 — contrato), Evento, Pendente (Fase 1), Semântica de entrega (política definida), SPEC-004 — Contrato de telemetria, idempotência e ordenação, Critérios de aceitação, Fora de escopo (fase futura), Modelo de dados (PostgreSQL, Alembic `0001_initial`) (+4 more)

### Community 15 - "json"
Cohesion: 0.15
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
Cohesion: 0.06
Nodes (47): Metodologia de medição (modelo), Outcomes e métricas, browser(), controlled_data(), page(), quiet_simulator(), _shot(), test_hostile_equipment_name_is_rendered_as_text_and_never_executes() (+39 more)

### Community 36 - "test_telemetry.py"
Cohesion: 0.08
Nodes (28): equipment_id_from_topic(), _identifier(), parse_payload(), _parse_timestamp(), _reject_constant(), reject_future(), RejectReason, TelemetryRejected (+20 more)

### Community 37 - "worker/main.py"
Cohesion: 0.07
Nodes (14): configure_logging(), JsonFormatter, main(), SimulatorSettings, Consumer, MqttClient, next_backoff(), MessageHandler (+6 more)

### Community 38 - "routes.py"
Cohesion: 0.06
Nodes (43): Suggested Questions, Surprising Connections (you probably didn't know these), audit(), resource_id(), Authenticator, DemoAuthenticator, Principal, require_principal() (+35 more)

### Community 39 - "test_scenarios.py"
Cohesion: 0.13
Nodes (19): Message, _noise(), sensor_value(), SimConfig, Simulation, _compress(), test_config_rejects_non_positive_values(), test_dropout_equipment_goes_offline_and_comes_back() (+11 more)

### Community 40 - "test_handler.py"
Cohesion: 0.09
Nodes (30): Disposition, with_(), without(), _consumer(), FakeClient, FakeMessage, _msg(), test_acks_after_successful_persistence() (+22 more)

### Community 41 - "app/main.py"
Cohesion: 0.14
Nodes (7): Padrões em uso (e por quê), build_authenticator(), check_database(), create_app(), _find_panel_dir(), get_app(), test_check_database_false_and_silent_on_unreachable()

### Community 42 - "test_architecture.py"
Cohesion: 0.24
Nodes (7): _imports(), _package_imports(), test_api_never_touches_table_definitions_directly(), test_common_package_has_no_domain_or_framework_dependencies(), test_domain_is_pure_no_frameworks_no_io_libraries_no_other_internal_package(), test_services_do_not_depend_on_each_other_or_on_foreign_stacks(), test_storage_depends_only_on_domain_and_never_on_services()

### Community 43 - "test_correlation.py"
Cohesion: 0.08
Nodes (11): normalize_correlation_id(), RequestContextMiddleware, SecurityHeadersMiddleware, _client(), test_access_log_carries_correlation_id_without_query_string(), test_each_request_without_header_gets_distinct_id(), test_echoes_valid_incoming_id(), test_generates_uuid_when_header_missing() (+3 more)

### Community 44 - "test_compose_smoke.py"
Cohesion: 0.27
Nodes (6): _get(), _lower(), test_correlation_id_round_trip(), test_live(), test_ready_body_contains_no_connection_details(), test_ready_with_real_postgres_and_mosquitto()

### Community 45 - "app.js"
Cohesion: 0.28
Nodes (12): ageSeconds(), api(), el(), els, formatValue(), markStale(), refresh(), renderAlerts() (+4 more)

### Community 46 - "migrate.py"
Cohesion: 0.06
Nodes (17): _config(), downgrade(), main(), upgrade(), _reading_columns(), upgrade(), apply_seed(), truncate_all() (+9 more)

### Community 47 - "health.py"
Cohesion: 0.21
Nodes (5): build_router(), live(), Live, Ready, ReadyChecks

### Community 48 - "pytest"
Cohesion: 0.27
Nodes (7): ok(), test_demo_mode_is_allowed_outside_production(), test_oidc_mode_fails_closed_until_an_idp_is_approved(), test_production_with_demo_auth_is_refused_by_settings(), test_production_with_demo_auth_is_refused_even_if_settings_validation_is_bypassed(), test_settings_default_to_demo_outside_production(), test_warn_greater_than_crit_rejected()

### Community 49 - "graph_crosscheck.py"
Cohesion: 0.31
Nodes (5): _cells(), connected(), load_graph(), main(), nodes_of()

### Community 50 - "trace_edges.py"
Cohesion: 0.31
Nodes (6): build_edges(), _cells(), _is_gap(), main(), render(), test_header_has_expected_columns()

### Community 51 - "pathlib"
Cohesion: 0.31
Nodes (6): _backticked(), test_every_backticked_path_in_state_exists(), test_every_markdown_link_in_state_resolves(), test_requirements_and_decisions_cited_in_state_exist_in_the_catalog(), test_state_declares_date_branch_and_phase(), test_adr_files_have_status_and_decision_sections()

### Community 52 - "12. Roadmap com critérios de conclusão"
Cohesion: 0.25
Nodes (8): 12. Roadmap com critérios de conclusão, Fase 0 — Foundation, Fase 1 — Industrial vertical (sem AR nativa), Fase 2 — AR Android, Fase 3 — IA assistiva, Fase 4 — HACC Spatial, Fase 5 — Computer Vision e IoT real, Fase 6 — Cloud e escala

### Community 53 - "Graph Report - AR_XR  (2026-10-19)"
Cohesion: 0.29
Nodes (7): Community Hubs (Navigation), Corpus Check, Graph Freshness, Graph Report - AR_XR  (2026-10-19), Import Cycles, Knowledge Gaps, Summary

### Community 54 - "AGENTS.md — instruções para agentes de código neste repositório"
Cohesion: 0.33
Nodes (6): AGENTS.md — instruções para agentes de código neste repositório, Ambiente conhecido (Windows), Comandos, Convenções, Fluxo Spec-Driven (por feature), Regras inegociáveis

### Community 55 - "CURRENT_STATE — memória determinística do projeto"
Cohesion: 0.33
Nodes (6): CURRENT_STATE — memória determinística do projeto, Decisões pendentes de aprovação, Evidências executadas (ver `docs/evidence/phase-0/`), O que existe (verificado), O que NÃO foi feito / não está verificado, Próximo passo (somente após aprovação)

### Community 56 - "Runbook — desenvolvimento local"
Cohesion: 0.22
Nodes (9): Diagnóstico rápido, Fluxo completo (Fase 1), Grafo (Graphify), Primeira vez, Problemas conhecidos, Reset total do ambiente local, Runbook — desenvolvimento local, Testes que dependem de infraestrutura (+1 more)

### Community 58 - "Spatial AI Platform"
Cohesion: 0.40
Nodes (5): Demonstração (critério do marco), Mapa do repositório, Pré-requisitos, Spatial AI Platform, Testes e gates

### Community 59 - "SPEC-007 — Simulador de equipamentos e painel web 2D"
Cohesion: 0.40
Nodes (4): Critérios de aceitação, Painel (`clients/web-fallback`), Simulador (`services/equipment-simulator`), SPEC-007 — Simulador de equipamentos e painel web 2D

### Community 61 - "graph/ — índice auxiliar de conhecimento (Graphify)"
Cohesion: 0.33
Nodes (6): Como usar, Cruzamento matriz × grafo, Duas camadas de arestas (nunca misturadas), Ferramenta, graph/ — índice auxiliar de conhecimento (Graphify), O que o grafo ajudou a descobrir

### Community 70 - "9. Graphify, Dreaming, Cloud e Outcome"
Cohesion: 0.40
Nodes (5): 9. Graphify, Dreaming, Cloud e Outcome, Cloud, Dreaming, Graphify, Outcome

## Knowledge Gaps
- **3 isolated node(s):** `spatial-ai-platform`, `BASE_URL`, `TEST_DATABASE_URL`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 440 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Graph Report - AR_XR  (2026-10-19)` connect `Graph Report - AR_XR  (2026-10-19)` to `test_status.py`, `graph/README.md`, `Communities (70 total, 30 thin omitted)`, `routes.py`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `Repository` (e.g. with `Decisão` and `Regras de fronteira (verificadas hoje por revisão; teste automático pendente)`) actually correct?**
  _`Repository` has 34 INFERRED edges - model-reasoned connections that need verification._
- **What connects `spatial-ai-platform`, `BASE_URL`, `TEST_DATABASE_URL` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_status.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09094368340943683 - nodes in this community are weakly interconnected._
- **Why does `evaluate_status()` connect `test_status.py` to `test_scenarios.py`, `routes.py`, `CURRENT_STATE — memória determinística do projeto`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Are the 36 inferred relationships involving `Status` (e.g. with `God Nodes (most connected - your core abstractions)` and `Suggested Questions`) actually correct?**
  _`Status` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Should `test_health.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12807881773399016 - nodes in this community are weakly interconnected._