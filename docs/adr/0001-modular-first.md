# ADR-0001 — Monolito modular primeiro; três deployables no MVP

## Status
Proposto (aguarda aprovação do usuário). Data: 2026-10-19.

## Contexto
O plano mestre define bounded contexts (Assets, Telemetry, Digital Twin, Maintenance Knowledge, Spatial Experience, Identity/Authorization) e adverte contra "microserviços vazios, abstrações prematuras e infraestrutura onerosa". A equipe é pequena, a fase atual é fundação e não há carga medida que justifique distribuição.

## Decisão
1. `api` é **um** deployable FastAPI com módulos de domínio separados por pacote (fronteiras explícitas, sem importar internals de outro contexto).
2. `telemetry-worker` e `equipment-simulator` são deployables distintos (Fase 1) porque têm ciclo de vida, escala e modo de falha diferentes da API (consumidor MQTT contínuo; gerador de carga).
3. PostgreSQL e Mosquitto são infraestrutura, não serviços de negócio.
4. Lógica de domínio pura vive em `packages/domain` (sem I/O), reutilizável por API e worker e testável por propriedades.
5. HACC permanece sistema independente, acessado por adapter e API, **sem banco compartilhado**.
6. Na Fase 0 existe apenas o `api` (saúde) + infraestrutura; worker e simulador não são criados antes da Fase 1 (sem serviços vazios).

## Critérios para extrair um microserviço (todos exigidos)
- Contrato estável e versionado (OpenAPI/AsyncAPI) com testes de contrato.
- Necessidade **medida**: escala/latência/isolamento de falha/equipe independente demonstrados em métricas.
- Observabilidade e CI próprios já funcionando para o módulo.
- Custo operacional estimado e aprovado.

## Consequências
- (+) Menos latência de integração, um único pipeline, refatoração barata.
- (+) Fronteiras modulares preservam a opção de extração.
- (−) Escalabilidade independente por contexto só após extração; mitigado por métricas por módulo.
- (−) Disciplina de fronteira depende de revisão/testes de arquitetura (a adicionar na Fase 1, ex.: teste de imports proibidos).

## Alternativas rejeitadas
- Microserviços por bounded context desde o início: custo operacional sem necessidade demonstrada.
- Kafka no lugar de MQTT: sem requisito mensurável no MVP (reavaliar com carga real).
