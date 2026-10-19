# ADR-0002 — Pacote de persistência compartilhado e autenticação demo

## Status
Proposto (aguarda aprovação). Data: 2026-10-19. Complementa o [ADR-0001](0001-modular-first.md).

## Contexto
API e worker leem/escrevem o mesmo esquema PostgreSQL. Duplicar modelos em dois serviços cria divergência; criar um "serviço de dados" viola o ADR-0001 (microserviço sem necessidade medida). O plano exige autenticação com "dev mock explícito, nunca exposto em produção".

## Decisão
1. `packages/storage` (SQLAlchemy 2, Alembic, repositórios) é uma **biblioteca** consumida por `api` e `telemetry-worker`; o contexto de build Docker é a raiz do repo e cada Dockerfile copia só os pacotes de que precisa.
2. Acesso a dados via `Repository` (Protocol) com duas implementações: `PostgresRepository` (produção) e `InMemoryRepository` (dublê para testes sem Docker). **A mesma suíte de contrato roda nas duas** para impedir divergência de semântica.
3. Migrações Alembic rodam em um contêiner one-shot (`migrate`) antes de `api`/`worker` (`service_completed_successfully`); seed em dev é upsert idempotente.
4. Autenticação: interface `Authenticator` → `Principal(user_id, org_id)`. Implementação `DemoAuthenticator` (tokens fictícios) só é construída se `ENVIRONMENT != production`; `AUTH_MODE=oidc` falha ao iniciar até haver IdP aprovado. Autorização é sempre por `org_id` no repositório (nunca só na camada HTTP).
5. Painel web servido pela própria API em `/panel/` (arquivos estáticos): evita um quarto deployable e problemas de CORS.

## Consequências
- (+) Um esquema, uma fonte de migrações, testes rápidos sem Docker + garantia de paridade com Postgres real.
- (−) Dublê em memória é código a manter; mitigado pela suíte de contrato parametrizada.
- (−) Acoplamento de API e worker ao mesmo esquema: mudanças de coluna exigem deploy coordenado (aceitável com Alembic e um único time).

## Alternativas rejeitadas
- Testcontainers/Postgres em todo teste: lento e indisponível sem Docker.
- SQLite como dublê: semântica diferente de `ON CONFLICT`/`timestamptz`, mascararia bugs.
- Serviço de dados separado: viola ADR-0001.
