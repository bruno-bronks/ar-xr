# Threat model (STRIDE) — versão inicial

Escopo: alvo do MVP (API, broker, banco, cliente AR/web, assistente IA, adapter HACC). **Estado dos controles** distingue o que existe hoje (Fase 0) do que está planejado. Nada aqui é uma garantia de segurança: é a lista de riscos e do que falta.

Referências: OWASP ASVS, OWASP API Security Top 10, LGPD (dados hospitalares).

## Ativos
Telemetria e estado de equipamentos · documentação de manutenção aprovada · identidade e organização do usuário · (futuro) dados de leitos — **somente simulados** · segredos de infraestrutura.

## Ameaças e controles

| ID | Cat. | Ameaça | Controle previsto | Estado |
|---|---|---|---|---|
| S-01 | Spoofing | QR/marker adulterado ou falsificado para obter dados de outro equipamento | Marker é chave opaca; resolução só dentro da organização autenticada; desconhecido ≡ de outra organização (SPEC-003, M1/M2); rate limit | **Mitigado e testado** na API (Fase 1) e no **núcleo do cliente AR** (Fase 2): QR só aceita `[A-Za-z0-9._:-]{1,128}` e nada mais gera requisição; QR adulterado/alheio/desconhecido ≡ mesma mensagem. Câmera/ancoragem em aparelho: **não validado** |
| S-02 | Spoofing | Publicador MQTT falso (spoofing de equipamento) | ACL por equipamento e credenciais por dispositivo, TLS; tópico **não** é autorização | **Aberto** — Mosquitto dev anônimo, mitigado só por bind em 127.0.0.1. O worker valida payload/tópico/equipamento mas **não autentica o publicador** |
| S-03 | Spoofing | Identidade de usuário forjada | OIDC/OAuth2 corporativo; dev mock explícito, bloqueado em `production` | Parcial: modo **demo** com tokens fictícios (fail closed em `production`/`oidc`); o cliente AR **recusa token `demo-` e `http://` em build de release** (testado no núcleo). OIDC real pendente |
| T-01 | Tampering | Payload de telemetria malformado/adulterado | JSON Schema estrito, `additionalProperties:false`, rejeição de NaN, `equipment_id` = tópico | **Mitigado e testado** (Fase 1): parser estrito = JSON Schema (teste diferencial), tópico = payload, equipamento/sensor cadastrados, NaN/Infinity e skew de relógio rejeitados |
| T-02 | Tampering | Replay / duplicação de eventos | Idempotência `(source, event_id)`; janela de timestamp | **Mitigado e testado** (Fase 1): idempotência `(source,event_id)` no PostgreSQL (`ON CONFLICT`), incl. corrida de 8 threads e redelivery. Janela de timestamp: apenas limite superior (+5 min); eventos antigos são aceitos (só histórico) |
| T-03 | Tampering | **Injeção de prompt** via documentação/pergunta | Conteúdo recuperado tratado como dado; saída com fontes; recusa de ações inseguras; revisão humana | Planejado (Fase 3) |
| T-04 | Tampering | Log injection via cabeçalhos | `X-Correlation-ID` validado por regex, senão substituído | **Mitigado e testado** (REQ-ENG-004) |
| T-05 | Tampering | XSS no painel via nomes/valores vindos da API | `textContent` (nunca `innerHTML`) + CSP estrita (`script-src 'self'`, sem inline) | **Mitigado e testado** (E2E com nome malicioso no banco) |
| T-06 | Tampering | Resposta atrasada de uma organização exibida sob outra (painel) | descarte por *geração* + token fixado por ciclo de atualização | **Mitigado e testado** (E2E + teste de mutação); defeito encontrado e corrigido na Fase 1 |
| T-07 | Tampering | Resposta de API malformada/gigante derruba o app ou injeta valores | JSON com campos obrigatórios, status entre os 5 conhecidos, ids no alfabeto seguro, corpo ≤ 64 KiB, profundidade ≤ 16 | **Mitigado e testado** no núcleo C# (CI) |
| I-06 | Info. disclosure | Log do app vaza token, URL, texto do QR ou corpo de resposta | núcleo só emite códigos fixos (`poll:Ok`); teste varre todo o log da sessão | **Mitigado e testado** no núcleo; `adb logcat` em aparelho: **pendente** (checklist §5) |
| R-01 | Repudiation | Ação sem trilha de quem/quando | Log estruturado com correlation ID; auditoria de acesso por usuário | **Parcial**: log `app.audit` (usuário, org, ação, recurso, resultado, correlation ID) em toda consulta; sem armazenamento imutável/assinado |
| I-01 | Info. disclosure | Vazamento de credenciais/strings de conexão em respostas e logs | `SecretStr`; `/health/ready` só `ok/fail`; log só com tipo de exceção | **Mitigado e testado** (REQ-ENG-003, REQ-SEC-001) |
| I-02 | Info. disclosure | Vazamento entre organizações (IDOR) | Filtro por organização em toda consulta; 404 indistinguível | **Mitigado e testado** (Fase 1) em memória **e PostgreSQL real** e por HTTP na pilha; autorização no repositório (filtro `org_id`), não só na camada HTTP |
| I-03 | Info. disclosure | Vazamento de documentação proprietária ao LLM | Minimização, allow-list de fontes, modo mock, DPA com provedor | Planejado (Fase 3) |
| I-04 | Info. disclosure | Dado clínico real/identificável exposto | **Somente dados simulados**; LGPD, minimização, autorização e validação clínica antes de qualquer piloto | Regra de projeto; teste de não vazamento: Fase 4 |
| I-05 | Info. disclosure | Dispositivo AR perdido com sessão ativa | Tokens curtos, revogação, sem dados persistidos no aparelho | Parcial (Fase 2): o app não persiste dados do equipamento e descarta a vista ao trocar de QR/401; token demo é público. Revogação de token/MDM e teste em aparelho perdido: **pendentes** |
| D-01 | Denial of service | Inundação de MQTT/HTTP | Rate limit, limites de payload, backpressure no worker | **Parcial**: rate limit só em markers; MQTT sem limite de taxa/tamanho além do `max_packet_size` padrão do broker; worker não faz backpressure |
| D-02 | Denial of service | Falha de dependência derruba API | Liveness independente de dependências; readiness com timeout curto | **Implementado e testado** (REQ-ENG-002/003) |
| E-01 | Elevation | Acesso além do perfil (RBAC/ABAC) | Autorização central por organização e papel | **Parcial**: isolamento por organização implementado; RBAC por papel **não** (todos os principais são operadores) |
| E-02 | Elevation | IA aciona ação física | Nenhuma ação física automática no MVP; IA apenas assistiva | Regra de projeto (REQ-AI-001) |
| X-01 | Supply chain | Dependência/imagem comprometida | Versões pinadas, `pip-audit`, Gitleaks, Trivy, SBOM CycloneDX, imagens fixadas por tag | Parcial: pins + `pip-audit` local (3 serviços); imagens por tag fixa; Trivy/SBOM/Semgrep/gitleaks **não executados**; CZT/JDK baixados com SHA-256 verificado |
| X-02 | Config | Portas expostas na rede | Publicação só em `127.0.0.1`; container não-root | **Implementado e testado** (REQ-SEC-002) |

## Riscos residuais assumidos (Fases 0–1)
1. Mosquitto anônimo (S-02) e Postgres com senha de desenvolvimento — aceitável **somente** em máquina local; bloqueante para qualquer ambiente compartilhado.
2. Autenticação é **demo** (tokens públicos no repositório); proteção = fail closed em produção. OIDC/RBAC pendentes.
3. Scan SAST/imagem/SBOM e gitleaks ainda não executados.
4. Rate limit e auditoria em memória/log de processo único.
5. A **cola Unity nunca foi compilada** e a AR **nunca foi validada em aparelho**: S-01/I-05 só estão mitigados no núcleo lógico.
6. Dados são **simulados**; nenhum dado hospitalar real foi usado (I-04 permanece regra de projeto até a Fase 4).
