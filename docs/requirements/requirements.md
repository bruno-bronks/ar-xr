# Catálogo de requisitos

Fonte única dos requisitos. A rastreabilidade completa (REQ → SPEC → Z → ADR → contrato → teste → código → telemetria) está em [`traceability.csv`](traceability.csv) e é validada por `tests/unit/repo/test_traceability.py`.

Cadeia: `OUTCOME → REQ → SPEC → Z/INVARIANT → ADR → CONTRACT → TEST → CODE → TELEMETRY`.

Legenda de **Fase**: quando o requisito é implementado. Requisitos de fases futuras são registrados aqui para manter a cadeia, mas **não** estão implementados.

## Engenharia e plataforma

| ID | Requisito | Outcome | Fase |
|---|---|---|---|
| REQ-ENG-001 | `docker compose up --build` inicia API, PostgreSQL e Mosquitto no Windows; todos os serviços chegam a `healthy`. | OUT-ENG-001 | 0 |
| REQ-ENG-002 | `GET /health/live` responde 200 enquanto o processo estiver de pé, **sem** consultar dependências. | OUT-ENG-001 | 0 |
| REQ-ENG-003 | `GET /health/ready` responde 200 somente se banco e broker respondem; caso contrário 503. A resposta nunca expõe strings de conexão, credenciais ou texto de exceção. | OUT-ENG-001 | 0 |
| REQ-ENG-004 | Toda requisição possui correlation ID: reaproveita `X-Correlation-ID` se válido, senão gera um; o ID volta na resposta e aparece nos logs estruturados. Valores inválidos (injeção de log) são descartados. | OUT-ENG-001 | 0 |
| REQ-ENG-005 | A CI executa lint, tipagem, testes, scan de segredos e auditoria de dependências, e bloqueia merge em falha de gate crítico. | OUT-ENG-001 | 0 |
| REQ-ENG-006 | Todo requisito do catálogo possui linha na matriz de rastreabilidade; testes e artefatos citados existem. | OUT-ENG-001 | 0 |
| REQ-ENG-007 | As specs Z passam por parse + typecheck com ferramenta real (CZT) e o resultado é reproduzível por script; um erro de tipo injetado é rejeitado. | OUT-ENG-001 | 1 |
| REQ-ENG-008 | A matriz de rastreabilidade gera arestas **verificadas** (`IMPLEMENTS`, `TESTED_BY`, `DECIDED_BY`, `SPECIFIED_BY`, `FORMALIZED_BY`, `CONTRACT`) e o grafo de código (Graphify) é usado como índice auxiliar, com arestas inferidas separadas das verificadas. Git e a matriz continuam a fonte oficial. | OUT-ENG-001 | 1 |

## Segurança

| ID | Requisito | Outcome | Fase |
|---|---|---|---|
| REQ-SEC-001 | Nenhum segredo real versionado; `.env` ignorado pelo Git; `.env.example` contém apenas valores fictícios; configuração sensível não aparece em `repr`/logs. | OUT-ENG-001 | 0 |
| REQ-SEC-002 | Portas publicadas pelo Compose escutam apenas em `127.0.0.1`. | OUT-ENG-001 | 0 |
| REQ-SEC-003 | Endpoints `/api/v1/*` exigem autenticação. Modo **demo** (tokens fictícios) é explícito, só vale fora de produção e a aplicação **recusa iniciar** com `ENVIRONMENT=production` + demo, ou com modo OIDC ainda não implementado (fail closed). Toda consulta é restrita à organização do principal. | OUT-HACC-001 | 1 |
| REQ-SEC-004 | Acessos a dados de equipamento geram log de auditoria (usuário, organização, ação, recurso, resultado, correlation ID) sem segredos; resolução de marker tem rate limit por principal. | OUT-MNT-001 | 1 |

## Manutenção industrial (vertical A)

| ID | Requisito | Outcome | Fase |
|---|---|---|---|
| REQ-MNT-001 | Resolução de marker/QR: um marker válido retorna somente o equipamento da organização do chamador; marker desconhecido e marker de outra organização são **indistinguíveis** (sem vazamento). | OUT-MNT-001 | modelo: 0 · API: 1 |
| REQ-MNT-002 | Avaliação de estado do equipamento (`NORMAL/WARNING/CRITICAL/OFFLINE/UNKNOWN`) determinística; dado ausente/atrasado nunca resulta em `NORMAL`; `OFFLINE` tem precedência; limiar exato não dispara alarme (decisão D-001). | OUT-MNT-003 | modelo: 0 · worker/API: 1 |
| REQ-MNT-003 | Contrato do evento de telemetria (`spatial/v1/equipment/{id}/telemetry`): schema versionado, rejeição de payload inválido; **ingestão idempotente** por (origem, `event_id`) e a "última leitura" nunca regride por evento atrasado/fora de ordem (o histórico mantém todos os eventos aceitos). | OUT-MNT-002 | contrato: 0 · ingestão: 1 |
| REQ-MNT-004 | O worker valida cada mensagem (UTF-8, JSON estrito sem NaN/Infinity, schema, `equipment_id` = tópico, equipamento e sensor cadastrados, `observed_at` não mais que 5 min no futuro). Mensagem inválida é **rejeitada com motivo**, contada, não altera estado e não derruba o worker. | OUT-MNT-003 | 1 |
| REQ-MNT-005 | Resiliência do worker: reconexão MQTT com backoff e sessão persistente; mensagem só é confirmada (ack) após persistir ou rejeitar; falha de banco **não perde** evento (redelivery). | OUT-MNT-002 | 1 |
| REQ-MNT-006 | API de leitura por equipamento: lista, detalhe, telemetria mais recente, twin (estado conforme SPEC-002 com `now` do servidor) e alertas determinísticos por regra (separados de hipóteses de IA). Equipamento de outra organização ≡ inexistente (404 idêntico). | OUT-MNT-003 | 1 |
| REQ-MNT-007 | Seed de 3 equipamentos fictícios com perfis de limiar por equipamento e 3 markers/QR de teste; migrações Alembic reproduzíveis; seed idempotente. | OUT-MNT-001 | 1 |
| REQ-SIM-001 | O simulador publica telemetria dos 3 equipamentos de forma determinística (semente fixa): um equipamento escala até alerta, um silencia (offline), um permanece normal; reenvia duplicatas configuráveis. | OUT-MNT-003 | 1 |
| REQ-UX-001 | Painel web 2D (fallback sem AR) mostra, por equipamento, estado, leituras e alertas, atualiza automaticamente e exibe `OFFLINE`/`UNKNOWN` explicitamente (nunca "normal" por dado ausente). | OUT-MNT-002 | 1 |

## Planejados (fases futuras — sem implementação)

| ID | Requisito | Outcome | Fase |
|---|---|---|---|
| REQ-AI-001 | Toda sugestão de manutenção da IA cita documentação aprovada, expressa incerteza e nunca aciona ação física. | OUT-MNT-003 | 3 |
| REQ-HACC-001 | Visualização de leitos usa apenas dados **simulados**; acesso não autorizado é bloqueado; HACC original preservado. | OUT-HACC-001 | 4 |

## Decisões de default explícitas (precisam de aprovação)

| ID | Decisão | Justificativa | Reversível? |
|---|---|---|---|
| D-001 | Limiar é excedido quando `valor > limite` (estrito). Valor exatamente no limite **não** alarma. | Alinha ao predicado ilustrativo do plano mestre (`>`). Alternativa mais conservadora: `>=`. | Sim — muda 1 operador + testes |
| D-002 | Leitura com `quality = BAD` não participa da avaliação de limiares; se não houver leitura válida, o estado é `UNKNOWN`. | Sensor defeituoso não pode gerar nem mascarar alarme. | Sim |
| D-003 | Frescor do equipamento usa o `observed_at` mais recente entre **todas** as leituras (inclusive `BAD`); `OFFLINE` se `now - last_seen > offline_after`. Além disso, a leitura de um sensor só é **válida** se for `GOOD` **e** fresca (`idade ≤ offline_after`). | Distingue "equipamento mudo" de "sensor ruim/mudo" e impede que valor velho de um sensor sustente um estado. | Sim |
| D-006 | `NORMAL` exige leitura válida de **todos** os sensores do perfil do equipamento; evidência de alarme (WARNING/CRITICAL) prevalece sobre cobertura incompleta; cobertura incompleta sem alarme = `UNKNOWN`. | "Dado ausente não é normalidade" aplicado por sensor. Consequência: perfil deve listar só sensores que o equipamento realmente reporta. | Sim |
| D-004 | Portas do host: API `8088`, PostgreSQL `55432`, MQTT `1883`, todas em `127.0.0.1`. | 5432 e 8000 já estão em uso por outros projetos nesta máquina. | Sim (variáveis no `.env`) |
| D-005 | Raiz do repositório = a pasta `AR_XR` (workspace novo, separado do HACC). | O plano pede workspace novo; a pasta já estava vazia. | Sim |
| D-007 | `observed_at` até 5 min no futuro (skew de relógio) é aceito; além disso a mensagem é rejeitada (`TIMESTAMP_IN_FUTURE`). Eventos antigos são aceitos (só histórico se não avançam a "última leitura"). | Evita relógio quebrado "congelar" um equipamento no futuro. | Sim |
| D-008 | Seed: 3 equipamentos na organização `org-a` (EQ-001 compressor, EQ-002 bomba, EQ-003 motor) + 1 equipamento sentinela `EQ-B01` na `org-b` apenas para demonstrar/testar isolamento entre organizações. | O plano pede 3 máquinas; o 4º item é só fixture de segurança. | Sim |
| D-009 | Autenticação demo: tokens Bearer fictícios fixos (`demo-operator-a`, `demo-operator-b`), válidos somente em `ENVIRONMENT` ≠ `production`. | Dev mock explícito exigido pelo plano; OIDC fica para fase posterior (aprovação de IdP). | Sim |
| D-010 | Alertas são **derivados** do twin no momento da consulta (sem tabela de histórico de alertas); `OFFLINE` surge por passagem de tempo sem precisar de job. Histórico de alertas fica para fase posterior. | Evita scheduler/estado extra; atende "mudança de estado" via twin. | Sim |
| D-011 | Pacote compartilhado `packages/storage` (modelos SQLAlchemy, repositórios, migrações) usado por API e worker; contexto de build Docker passa a ser a raiz do repo. | API e worker precisam do mesmo esquema; evita duplicação e serviço extra (ver ADR-0002). | Sim |
