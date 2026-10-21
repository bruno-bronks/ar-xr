# SPEC-012 — Cloud, operação e escala (Fase 6)

Requisitos: REQ-OPS-001 … REQ-OPS-009 · Decisões: D-042…D-049 · ADR: [ADR-0007](../../docs/adr/0007-release-gitops-and-ops-tooling.md) · Z: [z-007](../formal-z/z-007-deploy-and-backup.tex) · Runbooks: [gitops-and-deploy](../../docs/runbooks/gitops-and-deploy.md), [backup-restore](../../docs/runbooks/backup-restore.md), [observability](../../docs/runbooks/observability.md) · SLO: [slo.md](../../docs/ops/slo.md) · DR: [disaster-recovery.md](../../docs/ops/disaster-recovery.md) · Segurança: [security-review.md](../../docs/ops/security-review.md) · Custos: [cost-estimate.md](../../docs/cloud/cost-estimate.md).

## Limites (leia primeiro)
- **Nada foi contratado, nenhum recurso de nuvem foi criado e o VPS não foi tocado** (D-042). A "homologação" é a pilha **local em Docker** (projeto Compose `spatial-homolog`, portas próprias) com um `registry:2` local. Provar o comportamento num provedor real é trabalho futuro que depende de decisão e credenciais suas.
- Terraform/OpenTofu **não foi escrito** (D-043): sem provedor aprovado não haveria como validá-lo.
- Os arquivos de **cloud-init** e **systemd** foram validados por esquema/sintaxe com as ferramentas oficiais, **não executados** num servidor.
- A varredura de segurança **não é pentest**. SLOs foram **medidos numa máquina de desenvolvimento**, não em produção.

## 1. Release e deploy por tag (REQ-OPS-001, REQ-OPS-002)
- Imagens: `${IMAGE_REGISTRY}spatial-ai-{api,worker,simulator}:${IMAGE_TAG}` (`migrate` usa a imagem da `api`). `scripts/deploy.py build --tag T [--registry R/] [--push]`.
- Estado por ambiente em `.deploy/<env>.json`: `current`, `previous`, `history` (≤ 100 eventos), gravação atômica. Ambiente = `deploy/envs/<env>.env` (projeto Compose, registry, URL, token de smoke; `.env` reais ignorados pelo Git).
- `deploy(tag, backup=False)`: (opcional) backup + ensaio de restauração → `pull` → `up -d --no-build --wait` → confere que **todas** as imagens em execução terminam em `:tag` → *smoke* (`/health/ready` e, se houver token, `GET /api/v1/equipment` = 200). Qualquer falha ⇒ **rollback automático** para a tag registrada (verificado do mesmo jeito). Falha do backup aborta **antes** de mexer na pilha; falha do `pull` não toca a pilha em execução.
- `rollback()`: volta para `previous` (verificado) e troca `current`/`previous`. Sem `previous` ⇒ recusa.
- **Migrações são só para frente**: o rollback troca imagens, não desfaz migrações; por isso releases com migração usam `backup: true`.
- Tag/registry/segredos viajam por **variáveis de ambiente** do subprocesso, nunca no argv nem no log; comandos sem shell; tag validada por regex.
- Z-007: `current ∩ previous = ∅`; `Rollback ⨟ Rollback` devolve o estado original (conjectura, checada por teste; **não provada**).

## 2. GitOps pull (REQ-OPS-003)
`scripts/gitops_reconcile.py --env E` (timer systemd de 5 min): `git fetch` → lê `deploy/desired/E.json` **do objeto Git** `origin/main` (não do diretório de trabalho) → compara com o estado registrado **e com as imagens realmente em execução**:
`in-sync` (nada a fazer, idempotente) · `applied` (tag nova) · `drift-corrected` (imagens diferentes do registrado ou pilha caída) · `failed` (deploy falhou e voltou) · `skipped-failed` (tag que já falhou **não** é repetida em laço; `--retry-failed` força) · `error` (Git/estado inválido; nada muda).
Estado desejado = dado **não confiável**: só `tag`, `backup`, `note`; campo desconhecido reprova tudo; o conteúdo inválido nunca é ecoado. Trava por arquivo evita duas reconciliações simultâneas (trava velha > 30 min é de execução morta). Sem verificação de assinatura de commit (endurecimento futuro) — a proteção é a revisão do PR na `main`.

## 3. Backup, restauração e DR (REQ-OPS-004)
`scripts/backup.py create|verify|restore|list`: `pg_dump -Fc` por `exec` no contêiner `db`; manifesto JSON com SHA-256, tamanho, versão do servidor e **contagem de linhas por tabela antes e depois** do dump; retenção (`prune`, nunca apaga o último).
`verify` = **ensaio não destrutivo**: confere o SHA-256, restaura num banco temporário `restore_verify_<hex>` (sempre removido), compara `antes ≤ restaurado ≤ depois` por tabela (as tabelas só crescem) e mede o tempo. `restore` é **destrutivo** (recria o banco), exige `--yes`, para api/worker/simulador antes e os reinicia depois.
Limites: dump **lógico** (RPO = intervalo entre backups; sem WAL/PITR); dados mudam durante o dump (por isso o intervalo, não igualdade); o dump fica no mesmo host por padrão (cópia externa é decisão sua). Ver [disaster-recovery.md](../../docs/ops/disaster-recovery.md).

## 4. Observabilidade (REQ-OPS-005)
- **API** `GET /metrics` (texto Prometheus 0.0.4): só existe com `METRICS_TOKEN` (≥ 16 caracteres); `Authorization: Bearer`; token **distinto** dos tokens de usuário (um não abre o outro); comparação em tempo constante; 404 uniforme se desligado; `Cache-Control: no-store`.
- Métricas: `http_requests_total{route,method,status_class}`, `http_request_duration_seconds{route}` (histograma), `dependency_up{dependency}` (checagens de prontidão no momento da coleta), `metrics_series_dropped_total`, `metrics_collector_errors_total`.
- **Cardinalidade/PII**: `route` = *modelo* da rota (`/api/v1/equipment/{equipment_id}`); caminhos desconhecidos colapsam em `unmatched`; teto de séries por métrica; nenhum id, usuário, organização, token ou correlation ID vira rótulo (testado).
- **Worker** `:9100/metrics` (somente rede interna do Compose; porta nunca publicada): `worker_messages_total{disposition,reason}` (motivo = enum), `worker_last_message_timestamp_seconds`, `worker_ingest_lag_seconds` (histograma observed→banco, só mensagens aceitas e correntes), `worker_mqtt_connected`, `worker_consumer_failed`.
- **Prometheus** (perfil opcional `observability`) com regras de SLO por *burn rate* multi-janela e **testes de regras com `promtool`** (`scripts/check_prometheus.py`; inclui mutação: um limiar errado faz um teste reprovar). Sem Alertmanager: rotear alertas exige serviço externo (decisão sua).

## 5. SLOs (REQ-OPS-006)
Definidos e medidos em [slo.md](../../docs/ops/slo.md): carga controlada em circuito aberto (`scripts/load_test.py`), latência medida a partir do instante **pretendido** (sem omissão coordenada), SLIs recalculados do lado do cliente e **conferidos contra as contagens do servidor**.

## 6. Segurança e cadeia de suprimentos (REQ-OPS-007)
SBOM CycloneDX por imagem, Trivy (imagens), Semgrep (SAST) e testes de abuso, com **triagem de cada achado** em [security-review.md](../../docs/ops/security-review.md). Não substitui pentest profissional.

## 7. Custos (REQ-OPS-008) e provisionamento (REQ-OPS-009)
- `spatial_ops.cost` + `scripts/cost_model.py` geram [cost-estimate.md](../../docs/cloud/cost-estimate.md); um teste impede a doc de divergir do modelo. Preços de **terceiros**, datados, marcados "não oficial".
- `deploy/cloud-init/user-data.yaml` (modelo; segredo gerado **no host**) e `deploy/systemd/*` (timers de GitOps, backup diário, ensaio semanal; usuário sem privilégio, `ProtectSystem=strict`). `scripts/verify_host.py` roda `systemd-analyze verify` e `cloud-init schema` num contêiner descartável.

## Invariantes e falhas
- Nunca ficar com tag defeituosa em execução depois de um deploy que falhou (e2e com release realmente defeituosa).
- `restore`/`verify` nunca tocam o banco real sem `--yes` / nunca deixam o banco temporário.
- Falha de coletor de métricas, de checagem de dependência, do Git ou de backup **não** propaga detalhe interno nem derruba o serviço.
- O estado desejado vindo do Git nunca vira comando.

## Não verificado
Provedor de nuvem real; DNS/TLS/proxy reverso públicos; replicação/HA do banco; PITR; desempenho de ingestão MQTT em escala; retenção de telemetria; notificação de alertas; pentest.
