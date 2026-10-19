# Threat model (STRIDE) — versão inicial

Escopo: alvo do MVP (API, broker, banco, cliente AR/web, assistente IA, adapter HACC). **Estado dos controles** distingue o que existe hoje (Fase 0) do que está planejado. Nada aqui é uma garantia de segurança: é a lista de riscos e do que falta.

Referências: OWASP ASVS, OWASP API Security Top 10, LGPD (dados hospitalares).

## Ativos
Telemetria e estado de equipamentos · documentação de manutenção aprovada · identidade e organização do usuário · (futuro) dados de leitos — **somente simulados** · segredos de infraestrutura.

## Ameaças e controles

| ID | Cat. | Ameaça | Controle previsto | Estado |
|---|---|---|---|---|
| S-01 | Spoofing | QR/marker adulterado ou falsificado para obter dados de outro equipamento | Marker é chave opaca; resolução só dentro da organização autenticada; desconhecido ≡ de outra organização (SPEC-003, M1/M2); rate limit | Modelo + testes (Fase 0); API/rate limit: Fase 1 |
| S-02 | Spoofing | Publicador MQTT falso (spoofing de equipamento) | ACL por equipamento e credenciais por dispositivo, TLS; tópico **não** é autorização | **Aberto** — Mosquitto dev é anônimo, mitigado só por bind em 127.0.0.1 |
| S-03 | Spoofing | Identidade de usuário forjada | OIDC/OAuth2 corporativo; dev mock explícito, bloqueado em `production` | Planejado (Fase 1/2) |
| T-01 | Tampering | Payload de telemetria malformado/adulterado | JSON Schema estrito, `additionalProperties:false`, rejeição de NaN, `equipment_id` = tópico | Schema testado (Fase 0); verificação no worker: Fase 1 |
| T-02 | Tampering | Replay / duplicação de eventos | Idempotência `(source, event_id)`; janela de timestamp | Especificado (Z-004); implementação: Fase 1 |
| T-03 | Tampering | **Injeção de prompt** via documentação/pergunta | Conteúdo recuperado tratado como dado; saída com fontes; recusa de ações inseguras; revisão humana | Planejado (Fase 3) |
| T-04 | Tampering | Log injection via cabeçalhos | `X-Correlation-ID` validado por regex, senão substituído | **Mitigado e testado** (REQ-ENG-004) |
| R-01 | Repudiation | Ação sem trilha de quem/quando | Log estruturado com correlation ID; auditoria de acesso por usuário | Parcial: correlation ID existe; auditoria por usuário: Fase 1 |
| I-01 | Info. disclosure | Vazamento de credenciais/strings de conexão em respostas e logs | `SecretStr`; `/health/ready` só `ok/fail`; log só com tipo de exceção | **Mitigado e testado** (REQ-ENG-003, REQ-SEC-001) |
| I-02 | Info. disclosure | Vazamento entre organizações (IDOR) | Filtro por organização em toda consulta; 404 indistinguível | Modelo testado; API: Fase 1 |
| I-03 | Info. disclosure | Vazamento de documentação proprietária ao LLM | Minimização, allow-list de fontes, modo mock, DPA com provedor | Planejado (Fase 3) |
| I-04 | Info. disclosure | Dado clínico real/identificável exposto | **Somente dados simulados**; LGPD, minimização, autorização e validação clínica antes de qualquer piloto | Regra de projeto; teste de não vazamento: Fase 4 |
| I-05 | Info. disclosure | Dispositivo AR perdido com sessão ativa | Tokens curtos, revogação, sem dados persistidos no aparelho | Planejado (Fase 2) |
| D-01 | Denial of service | Inundação de MQTT/HTTP | Rate limit, limites de payload, backpressure no worker | Planejado (Fase 1) |
| D-02 | Denial of service | Falha de dependência derruba API | Liveness independente de dependências; readiness com timeout curto | **Implementado e testado** (REQ-ENG-002/003) |
| E-01 | Elevation | Acesso além do perfil (RBAC/ABAC) | Autorização central por organização e papel | Planejado (Fase 1) |
| E-02 | Elevation | IA aciona ação física | Nenhuma ação física automática no MVP; IA apenas assistiva | Regra de projeto (REQ-AI-001) |
| X-01 | Supply chain | Dependência/imagem comprometida | Versões pinadas, `pip-audit`, Gitleaks, Trivy, SBOM CycloneDX, imagens fixadas por tag | Parcial: pins + `pip-audit` local; Trivy/SBOM/Semgrep **não executados** |
| X-02 | Config | Portas expostas na rede | Publicação só em `127.0.0.1`; container não-root | **Implementado e testado** (REQ-SEC-002) |

## Riscos residuais assumidos na Fase 0
1. Mosquitto anônimo (S-02) e Postgres com senha de desenvolvimento — aceitável **somente** em máquina local; bloqueante para qualquer ambiente compartilhado.
2. Sem autenticação nos endpoints (apenas health existe).
3. Scan SAST/imagem/SBOM ainda não executados.
