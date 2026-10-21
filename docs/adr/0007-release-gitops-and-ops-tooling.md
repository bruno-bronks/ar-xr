# ADR-0007 — Release por tag, GitOps pull e ferramental de operação em Python/Compose

## Status
Proposto (aguarda aprovação). Data: 2026-10-20. Complementa os ADR-0001…0006.

## Contexto
A Fase 6 pede IaC, GitOps, homologação, observabilidade, SLO, backup/restore, DR e verificação de segurança, com "deploy reproduzível, rollback testado e custos estimados". Restrições do projeto: nenhum serviço de nuvem pago sem autorização, o VPS compartilhado só muda a pedido, sem Kubernetes/cluster disponível, rede corporativa com TLS interceptado e tamanho atual da pilha (6 contêineres, 1 host).

## Decisão
1. **Release = imagem versionada por tag** (`IMAGE_TAG`/`IMAGE_REGISTRY` no Compose). Deploy **por tag**, com verificação (imagens em execução + *smoke*) e **rollback automático**; estado por ambiente em arquivo. Migrações são só para frente: rollback troca imagens; releases com migração pedem backup verificado antes.
2. **GitOps pull** com um reconciliador pequeno em Python (`spatial_ops.gitops`) disparado por timer systemd: o estado desejado é um JSON por ambiente **lido do objeto Git remoto**, validado por contrato estrito. Detecta *drift* comparando com as imagens realmente em execução e não repete em laço uma tag que já falhou.
3. **Ferramental em Python stdlib** (`packages/ops`, `scripts/*.py`), com `Runner`/`Store`/`Git` injetáveis: a lógica é testada com falsos e o comportamento real, com Docker de verdade (e2e opt-in `OPS_E2E=1`).
4. **IaC = Compose + cloud-init + units systemd.** Terraform/OpenTofu não foi escrito: sem provedor/credenciais não seria verificável (D-043).
5. **Observabilidade sem dependência nova:** exposição de métricas em texto Prometheus escrita à mão (`spatial_common.metrics`) com teto de séries e escape de rótulos; Prometheus como perfil opcional; regras de SLO por *burn rate* testadas com `promtool`.
6. **Backup lógico** (`pg_dump -Fc`) com manifesto e **ensaio de restauração automatizado**; RTO medido; RPO = intervalo entre backups.
7. **Homologação = Docker local** com portas e projeto próprios; registry = `registry:2` local; publicação no GHCR por workflow em tag `v*` (escrito, não executado).

## Consequências
- (+) Deploy, rollback, drift e desastre foram exercitados de verdade (release defeituosa, `TRUNCATE` da telemetria, pilha derrubada).
- (+) Poucas dependências novas: nenhuma no runtime; o ferramental roda onde há Python e Docker.
- (+) Cada peça é substituível: o `Reconciler` fala com um `GitSource` e um `Deployer`, não com o Compose diretamente.
- (−) Reimplementa um pouco do que Argo CD/Flux/Terraform dão prontos; só compensa nesta escala. Com mais de um host ou um cluster, **reavaliar** (ADR própria).
- (−) Sem replicação nem PITR: RPO de horas, RTO de minutos para um banco pequeno — **medidos só com dados minúsculos**.
- (−) Sem Alertmanager: alertas aparecem na UI do Prometheus; ninguém é notificado.
- (−) Nada foi provado num provedor real; custos são estimativa com preços de terceiros.
- (−) Sem verificação de assinatura de commit no reconciliador.

## Alternativas rejeitadas
- **Kubernetes + Argo CD/Flux:** sem cluster; complexidade desproporcional a 6 contêineres.
- **Terraform sem provedor aprovado:** código que ninguém consegue validar.
- **`prometheus_client` / OpenTelemetry:** viável e razoável mais adiante; hoje, uma dependência a mais por pouco ganho. Trocar é local (`spatial_common.metrics`).
- **Deploy empurrado por SSH a partir do computador do desenvolvedor:** não reproduzível, depende da máquina de quem faz.
- **`pg_basebackup`/WAL archiving:** melhor RPO, mas exige armazenamento externo e configuração que não podemos validar sem provedor.
