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

## Cliente AR (Fase 2)

| ID | Requisito | Outcome | Fase |
|---|---|---|---|
| REQ-AR-001 | O app lê um QR cujo conteúdo é **somente** o marker opaco (regex `^[A-Za-z0-9._:-]{1,128}$`) e o resolve por `GET /api/v1/spatial/markers/{id}`; o QR nunca carrega dados do equipamento. Conteúdo fora do padrão é descartado **sem** requisição. | OUT-MNT-001 | núcleo: 2 · aparelho: 2 |
| REQ-AR-002 | QR desconhecido, de outra organização ou rejeitado pelo servidor exibe a **mesma** mensagem genérica ("marcador não reconhecido") e nenhum dado; o app não distingue os casos. | OUT-MNT-001 | núcleo: 2 · aparelho: 2 |
| REQ-AR-003 | O overlay mostra estado (texto **e** cor), leituras com idade, limites e alertas, atualizados a cada 2 s. O estado vem **somente** do servidor (twin); o cliente não recalcula status. `OFFLINE`/`UNKNOWN` são exibidos como tais, nunca como normal. | OUT-MNT-002 | núcleo: 2 · aparelho: 2 |
| REQ-AR-004 | Falhas (rede, timeout, 401, 429, 5xx, resposta inválida) não derrubam o app: o último estado fica visível **marcado como desatualizado** com a idade; 429 respeita `Retry-After`; 401 pede reautenticação e remove dados. | OUT-MNT-002 | núcleo: 2 · aparelho: 2 |
| REQ-AR-005 | Segurança do cliente: modo demo/HTTP puro somente em *build* de desenvolvimento; *build* de release **recusa** token demo e `http://`; nenhum token/URL/payload é registrado em log; troca de QR descarta o estado anterior (sem vazamento entre equipamentos). | OUT-HACC-001 | núcleo: 2 · aparelho: 2 |
| REQ-AR-006 | Os 3 QR de teste (e os negativos) podem ser gerados para impressão por script reprodutível, e a decodificação com a **mesma biblioteca do app** (ZXing.Net) devolve exatamente o marker. | OUT-MNT-001 | 2 |
| REQ-AR-007 | A AR só é declarada validada com **checklist executado em aparelho Android físico**, com vídeo e métricas (latência QR→overlay, estabilidade) por dispositivo. | OUT-MNT-001, OUT-MNT-002 | 2 (depende de hardware) |

## Assistente de IA (Fase 3)

| ID | Requisito | Outcome | Fase |
|---|---|---|---|
| REQ-UX-002 | O painel web tem um campo de pergunta ao assistente: mostra desfecho, resposta, fontes, confiança, estado pelas regras e a necessidade de revisão humana; recusas e erros (401/404/422/429/rede) são visíveis; todo texto da API entra como texto (nunca HTML); troca de organização limpa a conversa. | OUT-MNT-002 | 3 |
| REQ-AI-001 | Toda resposta do assistente que dá orientação (`answered`) cita documentação aprovada, expressa a confiança e é apenas assistiva: nenhuma ação física é executada, comandada ou prometida pelo sistema. | OUT-MNT-003 | 3 |
| REQ-AI-002 | A base de conhecimento só contém documentos **aprovados** (`status: approved` + aprovador + data). Rascunhos, documentos sem aprovação e trechos com instrução embutida para o sistema (injeção de prompt) nunca são recuperados nem enviados a um LLM. | OUT-MNT-003 | 3 |
| REQ-AI-003 | Resposta `answered` tem ≥ 1 fonte, e cada trecho citado é **literal** de um trecho aprovado e recuperado para aquele equipamento. Sem evidência suficiente o assistente responde `insufficient_evidence` e não inventa. | OUT-MNT-003 | 3 |
| REQ-AI-004 | Pedidos para acionar/alterar equipamento, contornar proteção ou alarme, ou instruções dirigidas ao próprio sistema são **recusados** (`refused`) com `human_review_required`. Trechos de risco alto exigem revisão humana. | OUT-MNT-003 | 3 |
| REQ-AI-005 | O LLM é opcional e desligado por padrão. Indisponibilidade, saída inválida ou não fundamentada nos trechos citados degradam para a resposta extrativa (fallback), sem erro ao usuário e sem vazar segredo. | OUT-MNT-003 | 3 |
| REQ-AI-006 | `POST /api/v1/assistant/questions` exige autenticação, isola por organização (equipamento alheio ≡ inexistente, 404 uniforme), tem rate limit por usuário e **nunca** registra o texto da pergunta ou da resposta (apenas metadados). | OUT-MNT-003 | 3 |
| REQ-AI-007 | Um conjunto de avaliação rotulado mede alucinação (respostas com afirmações sem suporte), precisão de citação e taxa de recusa/abstenção correta; o relatório declara o tamanho e os limites do conjunto. | OUT-MNT-003 | 3 |

## HACC Spatial (Fase 4)

| ID | Requisito | Outcome | Fase |
|---|---|---|---|
| REQ-HACC-001 | Visualização de leitos usa apenas dados **simulados**; acesso não autorizado é bloqueado; HACC original preservado. | OUT-HACC-001 | 4 |
| REQ-HACC-002 | O acesso ao HACC é **somente leitura**: a porta `HaccSource` só tem operações de leitura; o adaptador HTTP só envia `GET` a caminhos permitidos, em host/esquema permitidos, sem seguir redirecionamentos, com timeout e limite de tamanho; falha do HACC vira 503 uniforme sem vazar detalhes. | OUT-HACC-001 | 4 |
| REQ-HACC-003 | Minimização: o modelo de leito não tem campo identificável de pessoa; payload com campos fora da lista permitida é **rejeitado por inteiro**; o conjunto simulado é determinístico e fictício. | OUT-HACC-001 | 4 |
| REQ-HACC-004 | Autorização e segregação: `/api/v1/hacc/*` exige autenticação **e** o escopo `hacc:read`; sem escopo ⇒ 403; ala/leito de outra organização ≡ inexistente (404 uniforme); a organização é imposta no nosso lado, nunca confiada à resposta do HACC; todo acesso é auditado sem dados de leito. | OUT-HACC-001 | 4 |
| REQ-HACC-005 | O estado do leito é por **regra determinística e operacional** (sem interpretação clínica): ausência de leitura ⇒ `UNKNOWN`, leitura velha ⇒ `OFFLINE` (precedência), alarmes ⇒ `ALERT`/`ATTENTION`; nunca `NORMAL` por dado ausente. | OUT-HACC-001 | 4 |
| REQ-HACC-006 | O painel mostra a planta 2D da ala com os leitos, estado (texto + ícone, não só cor), alertas operacionais e frescor; usuário sem escopo vê aviso explícito e nenhum dado; todo texto da API entra como texto. | OUT-HACC-001 | 4 |


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
| D-012 | Cliente AR: **Unity 6.3 LTS (6000.3)** com AR Foundation **6.3.5** e ARCore XR Plugin **6.3.5** (par que a Unity documenta para o 6000.3), Test Framework 1.4.6, Newtonsoft 3.2.1. Versões conferidas no registro oficial `packages.unity.com`; o patch exato do editor depende do que você instalar. | Evita escolher versões de memória. | Sim |
| D-013 | Leitura de QR: **ZXing.Net** (Apache-2.0) sobre a imagem da câmera (CPU), não Augmented Images do ARCore. | O plano pede QR; Augmented Images reconhece imagens, não QR. | Sim |
| D-014 | Rede do aparelho: `adb reverse tcp:8088 tcp:8088` (a API continua só em `127.0.0.1`); HTTP puro permitido apenas em build de desenvolvimento. | Não expõe a API na LAN. | Sim |
| D-015 | Projeto Unity versionado neste repositório (`clients/ar-unity/`, `Library/` ignorada). | Rastreabilidade única. | Sim |
| D-016 | **Você aprovou a Fase 2 sem responder às decisões 1–4 nem informar o modelo do aparelho**: adotei as recomendações (D-013…D-015) como defaults provisórios. | Reversíveis até existir código Unity validado. | Sim |
| D-017 | O cliente **nunca** calcula status: usa o `status` do twin do servidor. Dado é "desatualizado" no cliente após 3 s sem atualização bem-sucedida (1,5× o intervalo de 2 s). | Fonte única da verdade (SPEC-002) e evita divergência. | Sim |
| D-018 | Provedor padrão do assistente = **extrativo determinístico** (recuperação lexical + trechos literais), sem LLM e sem nuvem. LLM (Anthropic) é opcional: só com `ASSISTANT_PROVIDER=llm` + `ANTHROPIC_API_KEY` no ambiente; sua saída só vale se passar na verificação de fundamentação, senão cai no extrativo. | Plano proíbe contratar nuvem sem aprovação e exige fallback mock; é a única configuração que posso testar de ponta a ponta. | Sim |
| D-019 | Base de conhecimento = arquivos Markdown versionados em `knowledge/` com front matter. "Aprovado" = `status: approved` + `approved_by` + `approved_on`. **O conteúdo atual é FICTÍCIO, escrito pelo agente, sem revisão técnica humana** — serve só para demonstrar o mecanismo; não usar em manutenção real. | Não há manual real nem aprovador humano disponível. | Sim |
| D-020 | Recusa por regras (padrões de ação física, contorno de segurança, instrução ao sistema). É heurística e **não exaustiva**; por isso a defesa principal é estrutural (nada executa ação; saída só com trechos aprovados). | Lista de palavras nunca cobre tudo; declarar o limite. | Sim |
| D-021 | Evidência mínima: ao menos 50 % dos termos significativos da pergunta presentes no trecho recuperado (e ≥ 1 termo); abaixo disso `insufficient_evidence`. Confiança: ≥ 0,8 alta · ≥ 0,65 média · senão baixa. | Limiar a priori, avaliado no conjunto dourado (REQ-AI-007) e reportado com os erros. | Sim |
| D-022 | Texto de pergunta/resposta nunca vai para log; o log guarda comprimento, desfecho, provedor, ids de fonte e correlation ID. | Pergunta pode conter dados sensíveis; minimização. | Sim |
| D-023 | Rate limit do assistente: 10 perguntas/min por usuário (o LLM tem custo). | Evita abuso e gasto. | Sim |
| D-024 | **Aprovadas pelo usuário em 2026-10-20: D-018 a D-023** (assistente extrativo por padrão, base de conhecimento fictícia, recusa heurística, limiar de evidência, log sem texto, rate limit de 10/min). A aprovação **não** valida o conteúdo dos documentos fictícios nem o LLM, que continuam sem revisão/validação real. | Registro da decisão do usuário. | Sim |
| D-025 | Fase 4 (**você pediu "Fazer a Fase 4" sem informar como o HACC expõe dados**): construo contra um **contrato assumido, somente leitura** (`specs/contracts/hacc-readonly.yaml`, marcado como NÃO verificado contra o HACC real) e uma **fonte simulada** como padrão. Nenhum repositório, banco ou endpoint real do HACC foi lido, tocado ou conectado. | O plano proíbe integração real sem autorização/LGPD e mexer no HACC. | Sim |
| D-026 | Porta `HaccSource` com duas implementações reais (simulada, padrão; HTTP somente leitura, opcional e desligada). Troca por configuração (`HACC_SOURCE=simulated\|http`). | Strategy/Adapter só porque há segunda implementação (AGENTS.md). | Sim |
| D-027 | Autorização por **escopo**: `Principal` ganha `scopes`; novos tokens demo `demo-nurse-a` (org-a) e `demo-nurse-b` (org-b) têm `hacc:read`; `demo-operator-*` **não** têm. Endpoints de equipamento continuam sem escopo (RBAC completo segue pendente). | Menor privilégio para dados de leitos sem reescrever a Fase 1. | Sim |
| D-028 | Leito = id opaco, rótulo, posição (x, y) na planta, `occupied` (bool), sinalizadores operacionais (`bed_exit_alarm`, `iv_pump_alarm`, `call_button`, `cleaning_due`) e `observed_at`. **Sem** identificação de paciente, sinais vitais ou diagnóstico. | Minimização; nenhuma recomendação clínica. | Sim |
| D-029 | Regras de estado do leito: sem leitura ⇒ `UNKNOWN`; leitura mais velha que 30 s ⇒ `OFFLINE` (precedência); `bed_exit_alarm` (só se ocupado) ou `iv_pump_alarm` ⇒ `ALERT`; `call_button` ou `cleaning_due` ⇒ `ATTENTION`; senão `NORMAL`. | Mesma filosofia da SPEC-002: dado ausente nunca é normal. | Sim |
| D-030 | A organização do leito vem do campo `tenant_id` do registro e é comparada com a do principal **no nosso código**; registros de outro tenant são descartados mesmo que o HACC os devolva. | Segregação não pode depender do sistema externo. | Sim |
| D-031 | Overlay da Fase 4 = planta 2D no painel web. **Não** estendi o cliente AR (cola Unity ainda não compilada nem validada em aparelho). | Não declarar o que não posso validar. | Sim |
| D-032 | **Aprovadas pelo usuário em 2026-10-20: D-025 a D-031** (contrato do HACC assumido, fonte simulada padrão, escopo `hacc:read`, modelo sem dados de pessoa, regras de estado do leito, tenant imposto no nosso lado, overlay só 2D), com commit, push, PR e redeploy no VPS. A aprovação **não** valida o contrato assumido contra o HACC real nem autoriza qualquer integração real. | Registro da decisão do usuário. | Sim |
