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

## Segurança

| ID | Requisito | Outcome | Fase |
|---|---|---|---|
| REQ-SEC-001 | Nenhum segredo real versionado; `.env` ignorado pelo Git; `.env.example` contém apenas valores fictícios; configuração sensível não aparece em `repr`/logs. | OUT-ENG-001 | 0 |
| REQ-SEC-002 | Portas publicadas pelo Compose escutam apenas em `127.0.0.1`. | OUT-ENG-001 | 0 |

## Manutenção industrial (vertical A)

| ID | Requisito | Outcome | Fase |
|---|---|---|---|
| REQ-MNT-001 | Resolução de marker/QR: um marker válido retorna somente o equipamento da organização do chamador; marker desconhecido e marker de outra organização são **indistinguíveis** (sem vazamento). | OUT-MNT-001 | modelo: 0 · API: 1 |
| REQ-MNT-002 | Avaliação de estado do equipamento (`NORMAL/WARNING/CRITICAL/OFFLINE/UNKNOWN`) determinística; dado ausente/atrasado nunca resulta em `NORMAL`; `OFFLINE` tem precedência; limiar exato não dispara alarme (decisão D-001). | OUT-MNT-003 | modelo: 0 · worker/API: 1 |
| REQ-MNT-003 | Contrato do evento de telemetria (`spatial/v1/equipment/{id}/telemetry`): schema versionado, rejeição de payload inválido; idempotência por (origem, `event_id`) e ordenação por `observed_at` especificadas formalmente. | OUT-MNT-002 | contrato: 0 · ingestão: 1 |

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
