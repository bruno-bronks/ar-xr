# Revisão de segurança da Fase 6 (risco e cadeia de suprimentos)

Spec: [SPEC-012](../../specs/functional/SPEC-012-cloud-and-operations.md) §6 · REQ-OPS-007 · Decisão D-048 · Evidência: [docs/evidence/phase-6/](../evidence/phase-6/) (`trivy/`, `sbom/`, `semgrep.json`).

> **Isto NÃO é um pentest.** São varreduras automatizadas (SBOM, vulnerabilidades de imagens, SAST) mais testes de abuso escritos por quem escreveu o código, com **triagem de cada achado**. Um pentest profissional independente é recomendado antes de qualquer uso com dados reais ou exposição pública. Datas: varreduras de 2026-10-20/21; o banco de vulnerabilidades muda todo dia — repita antes de qualquer release.

## Ferramentas e escopo
| Verificação | Ferramenta | Escopo | Resultado arquivado |
|---|---|---|---|
| SBOM | CycloneDX (`cyclonedx-bom` 7.5) — spec 1.6 | dependências Python de `api` (23 componentes), `telemetry-worker` (12), `equipment-simulator` (8) | `sbom/*.cdx.json` |
| Vulnerabilidades de imagem | Trivy 0.58.1 (banco baixado na hora), severidade HIGH/CRITICAL | `spatial-ai-{api,worker,simulator}`, `postgres`, `eclipse-mosquitto`, `prom/prometheus` — antes **e depois** das correções | `trivy/*.json` |
| SAST | Semgrep (regras `p/python` + `p/security-audit`, 211 regras, 121 arquivos de `services/ packages/ scripts/ platform/ deploy/`) | código de runtime e ferramental (sem `tests/`) | `semgrep.json` |
| Segredos | gitleaks (CI, já existente) | histórico Git | CI |
| Dependências | `pip-audit` (CI, já existente) | `services/*/requirements.txt` | CI |
| Abuso | testes automatizados (abaixo) | ferramental de operação, `/metrics`, GitOps | `tests/unit/...` |

O SBOM cobre **dependências Python declaradas**, não os pacotes do sistema das imagens (esses aparecem no relatório do Trivy).

## Achados e triagem
Legenda: **Corrigido** = mudei algo e revalidei · **Aceito (temporário)** = sem correção disponível/aplicável hoje, com justificativa e gatilho de revisão · **Não aplicável**.

| # | Achado | Gravidade | Triagem | Ação / justificativa |
|---|---|---|---|---|
| F-01 | `postgres:16.4-alpine`: OpenSSL (`libcrypto3`/`libssl3`, ex. CVE-2026-31789), libxml2, musl, xz, zlib — **3 CRITICAL + 26 HIGH** no SO; base Alpine 3.20.3 **sem suporte** (EOSL) | Crítica/Alta | **Corrigido** | Atualizado para `postgres:16.15-alpine` (Alpine 3.24.2): **0** achados no SO. Aplicar o mesmo no VPS é redeploy (não feito). |
| F-02 | `gosu` (binário Go 1.24.6) dentro da imagem do PostgreSQL: **1 CRITICAL + 24 HIGH** (stdlib, ex. CVE-2025-68121) | Crítica/Alta | **Aceito (temporário)** | Artefato da imagem oficial; `gosu` só roda na inicialização do contêiner para rebaixar privilégio e não escuta rede; a porta do banco só está em `127.0.0.1`. Revisar ao sair nova imagem 16.x. |
| F-03 | `eclipse-mosquitto:2.0.18`: musl CVE-2025-26519 (**2 HIGH**), Alpine 3.18.9 EOSL | Alta | **Corrigido** | `eclipse-mosquitto:2.0.22` (Alpine 3.23.6): **0** achados; os 14 testes do broker endurecido (`test_broker_auth.py`, Mosquitto real) passam na nova versão. |
| F-04 | `prom/prometheus:v2.55.1`: 58 HIGH/CRITICAL (Go stdlib, `grpc`, `x/crypto`, `x/net`…) | Crítica/Alta | **Corrigido (parcial)** | `v3.15.0`: restam **5 HIGH** (CVE-2026-42154 no próprio Prometheus; `x/net` CVE-2026-78669; stdlib Go CVE-2026-78667/78669/97031) com correção publicada **depois** da imagem. Perfil opcional, porta só em `127.0.0.1`. Revisar no próximo release. Regras e config revalidadas na 3.15 (`promtool`, ao vivo). |
| F-05 | Imagens da aplicação (`python:3.12-slim` = Debian 13.7): **44 HIGH** idênticos nas 3 imagens — `util-linux`/`mount`/`login` (CVE-2026-76642, -78408/9/10), `ncurses` (CVE-2025-69720), `libacl1`, `libsystemd0`/`libudev1`, `perl-base` | Alta | **Aceito (temporário)** | Todos **sem versão corrigida** disponível na varredura (`fix: -`). Dependências Python: **0** achados. O processo roda como UID 10001, sem shell exposto, sem executar `mount`/`login`/`perl`. Mitigação: recompilar a cada release (o workflow de release roda o Trivy antes de publicar), considerar imagem distroless/`-slim` mais enxuta. |
| F-06 | Semgrep `dynamic-urllib-use-detected` em `llm_anthropic.py:31` | Aviso | **Não aplicável** | O código já recusa tudo que não seja `https://`. |
| F-07 | Semgrep `dynamic-urllib-use-detected` em `spatial_ops/deploy.py` (sonda de smoke) | Aviso | **Corrigido** | A URL vem do `.env` do operador e já era validada por regex, mas agora a sonda também recusa esquemas ≠ http(s) (teste `test_the_default_http_probe_refuses_non_http_schemes`). |
| F-08 | Semgrep `dynamic-urllib-use-detected` em `scripts/load_test.py` | Aviso | **Corrigido** | `--base-url` do operador: passou a recusar esquemas ≠ http(s). |
| F-09 | `OPS_COMPOSE_FILES` aceitava caminhos arbitrários (`../../x`, absolutos) vindos do `.env` | Média (achado por revisão de abuso, não pelas ferramentas) | **Corrigido** | Só `.yml/.yaml` relativos, sem `..`; testes parametrizados. |
| F-10 | Regra de alerta de frescor nunca casava (`le="5"` × `"5.0"`) | Operacional (alerta cego) | **Corrigido** | Ver [slo.md](slo.md); teste de contrato regras↔exposição. |

## Testes de abuso (automatizados)
- **`/metrics`**: desligado sem token (404 uniforme); 401 sem/errado/outro esquema; token de usuário **não** abre `/metrics` e token de métricas **não** abre a API; token ≥ 16 caracteres; nunca impresso (`SecretStr`). *(tests/unit/api/test_metrics_endpoint.py, test_config.py)*
- **Cardinalidade e vazamento**: 50 caminhos de scanner viram **uma** série `unmatched`; ids, usuário, organização, token e correlation ID **nunca** aparecem no texto; valor de rótulo hostil (`"`, `\`, quebra de linha) é escapado e não forja amostras; teto de séries por métrica. *(test_metrics_endpoint.py, tests/unit/common/test_metrics.py)*
- **Falhas que não vazam**: checagem de dependência que lança exceção com `password=…` vira `dependency_up 0` sem a mensagem; coletor que falha só incrementa contador. *(idem)*
- **Estado desejado do GitOps (dado não confiável)**: JSON inválido, campo desconhecido (`command`), tag com `; rm -rf /` ou `../..`, tipos errados ⇒ rejeitado inteiro e **nunca ecoado**. *(tests/unit/ops/test_gitops.py)*
- **Git**: ref/remoto/caminho hostis (`-evil`, `a; b`, `..`, absolutos) recusados; sem shell; falha do Git não vaza saída (credenciais em URL). *(idem)*
- **Ambiente e deploy**: nome de ambiente com `../`; `OPS_PROJECT`/`OPS_REGISTRY`/tag hostis; `OPS_COMPOSE_FILES` fora do repositório; `IMAGE_TAG`/`IMAGE_REGISTRY` no `.env` **não** sobrepõem a tag verificada; segredo não aparece no log/argv. *(test_deploy.py, test_backup.py)*
- **Concorrência**: duas reconciliações simultâneas ⇒ a segunda é recusada; trava de execução morta é retomada. *(test_gitops.py)*
- **Backup**: dump adulterado reprova pelo SHA-256 antes de restaurar; nome de banco validado; `restore` exige `--yes`. *(test_backup.py)*

## Riscos residuais (honestos)
1. **Sem pentest**; nenhuma exposição pública foi testada (TLS, proxy reverso, WAF).
2. **Autenticação continua sendo demo** (tokens fictícios); a API recusa iniciar em produção com ela. OIDC depende de IdP aprovado.
3. O reconciliador confia no que está na `main`: **sem verificação de assinatura de commit**. A proteção é a revisão de PR e a branch protegida.
4. Senha do PostgreSQL e `METRICS_TOKEN` ficam em arquivo `.env` no host; sem gerenciador de segredos.
5. Imagens da aplicação carregam 44 CVEs de SO sem correção (F-05) até o Debian publicar correções.
6. `/health/ready` abre conexão nova a cada chamada: é um ponto de abuso de recursos se exposto; está sob o mesmo processo e sem *rate limit* próprio.
7. Backups ficam no mesmo host por padrão e sem criptografia em repouso.

## Recomendações (ordem sugerida)
1. Pentest independente antes de dados reais ou exposição pública.
2. Atualizar o VPS para `postgres:16.15-alpine` quando você autorizar um redeploy (hoje roda a versão com F-01).
3. Cópia externa e criptografada dos backups.
4. Assinatura de commits/tags e verificação no reconciliador.
5. Rodar Trivy/Semgrep/gitleaks no CI a cada PR e na tag de release (o job de release já executa o Trivy; falta o gate no CI de PR).
