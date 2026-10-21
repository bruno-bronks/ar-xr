# Recuperação de desastre (DR) — RPO, RTO e ensaio

Spec: [SPEC-012](../../specs/functional/SPEC-012-cloud-and-operations.md) §3 · REQ-OPS-004 · Passo a passo: [backup-restore.md](../runbooks/backup-restore.md) · Evidência: [ops-e2e-timings.json](../evidence/phase-6/ops-e2e-timings.json), [ops-e2e-run.txt](../evidence/phase-6/ops-e2e-run.txt).

> **Leia primeiro.** Os tempos abaixo foram medidos com um banco **minúsculo** (dump de ≈ 11 KB, ≈ 10²–10³ linhas) numa máquina de desenvolvimento. Eles provam que o **procedimento funciona de ponta a ponta**, não que o RTO de um banco de verdade caiba em qualquer meta: o RTO cresce com o tamanho dos dados e não foi extrapolado.

## Cenários e o que cobre
| Cenário | Coberto? | Como |
|---|---|---|
| Release defeituosa em produção | **Sim, testado** (Docker real) | rollback automático; manual |
| Perda/corrupção de dados no banco (apagão lógico) | **Sim, testado** | `TRUNCATE telemetry_events` → restauração do último dump → API saudável |
| Pilha caída / imagens trocadas à mão (drift) | **Sim, testado** | reconciliador GitOps |
| Dump corrompido ou adulterado | **Sim, testado (unit)** | SHA-256 do manifesto reprova antes de restaurar |
| Perda do **host inteiro** | **Parcial** | `cloud-init` + `git clone` recria o host e os timers; **os dumps estão no mesmo host por padrão** ⇒ sem cópia externa, perdem-se os dados. Destino externo = decisão sua |
| Falha de **região/zona** do provedor | Não | sem réplica, sem multi-AZ |
| Corrupção silenciosa que o dump já capturou | Não | sem verificação semântica; sem PITR para voltar antes do erro |
| Versão maior do PostgreSQL | Não testado | exige `pg_upgrade` ou dump/restore entre versões |

## Metas propostas (a ajustar com o negócio)
| Medida | Proposta | Base |
|---|---|---|
| **RPO** (perda máxima de dados) | **24 h** com o backup diário; reduzir exige WAL/PITR (não implementado) | dump lógico: tudo que entrou depois do último dump se perde |
| **RTO** (tempo para voltar) | **≤ 30 min** para um banco pequeno | medido 24 s com dados minúsculos; a margem cobre diagnóstico humano, não só a máquina |
| Frequência do ensaio de restauração | **semanal** (`spatial-backup-verify.timer`) | backup sem ensaio não conta |

## Medições (homologação local, Docker real, 7/7 testes verdes)
| Operação | Tempo |
|---|---|
| Deploy de uma tag (pull + subir + verificar + smoke) | 28 s (v1), 28 s (v2) |
| Release **defeituosa**: detecção + rollback automático até a pilha boa estar verificada | 61 s |
| Rollback manual (verificado) | 31 s |
| Reconciliador GitOps: aplicar tag nova / corrigir *drift* | 34 s / 36 s |
| Backup (`pg_dump`) + manifesto | dump de 11 487 bytes |
| **Ensaio de restauração** (banco temporário, comparação de contagens) | 2,4 s |
| **Recuperação de desastre completa** (parar app → recriar banco → restaurar → subir → API pronta) | **23,5 s** (restauração em si: 1,7 s) |

Cenário do ensaio de desastre (`test_5`): o simulador gerou ≥ 10 eventos; criou-se o backup, que foi **verificado**; apagou-se `telemetry_events` (`TRUNCATE … CASCADE`); parou-se a aplicação; restaurou-se; confirmou-se `GET /health/ready` = 200, `GET /api/v1/equipment` = 200 e contagem de eventos ≥ a do manifesto.

## O que o ensaio automatizado compara
`antes ≤ restaurado ≤ depois` por tabela (o banco continua recebendo escritas durante o dump; as tabelas só crescem). Isso detecta dump vazio/truncado e restauração parcial; **não** detecta alteração semântica de valores.

## Pendências para chamar de "DR pronto"
1. Cópia **externa** dos dumps (outro host/bucket), criptografada e com retenção.
2. Medir RTO com volume realista de telemetria e definir **retenção/compactação** (hoje o disco cresce sem limite; ver [cost-estimate.md](../cloud/cost-estimate.md)).
3. Replicação ou WAL archiving se o RPO de 24 h for inaceitável.
4. Exercício de DR periódico com humanos (o procedimento acima, cronometrado).
5. Plano para a perda do host: DNS/TLS, segredos (`POSTGRES_PASSWORD` é gerado no host e não é recuperável sem backup do `.env`).
