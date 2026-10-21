# Runbook — backup, restauração e recuperação de desastre

Spec: [SPEC-012](../../specs/functional/SPEC-012-cloud-and-operations.md) §3 · Metas e medições: [disaster-recovery.md](../ops/disaster-recovery.md).

## Comandos
```powershell
python scripts/backup.py create  --env homolog [--keep 14]   # pg_dump -Fc + manifesto (SHA-256, contagens antes/depois)
python scripts/backup.py list    --env homolog
python scripts/backup.py verify  --env homolog               # ENSAIO: restaura num banco temporário e compara contagens (não destrutivo)
python scripts/backup.py restore --env homolog --yes         # DESTRUTIVO: para api/worker/simulador, recria o banco, reinicia
```
Arquivos em `.deploy/backups/<env>/` (ignorado pelo Git): `spatial-<timestamp>.dump` + `.manifest.json`.

## Rotina (systemd, modelo)
`spatial-backup.timer` (diário 03:15) · `spatial-backup-verify.timer` (domingo 04:30, ensaio do último dump). **Um backup nunca ensaiado não conta como backup**: acompanhe o resultado do ensaio.

## Recuperação de desastre (passo a passo)
1. **Declare o incidente** e anote a hora. Pare quem escreve: `docker compose -p <proj> stop simulator worker api` (o `restore` já faz isso).
2. Escolha o dump (o mais recente cujo `verify` passou): `backup.py list`.
3. `backup.py verify --env E --file <dump>` (confere SHA-256 e restaura num banco temporário). Se reprovar, tente o anterior.
4. `backup.py restore --env E --yes [--file <dump>]`.
5. Confirme: `curl http://<api>/health/ready` = 200 e `GET /api/v1/equipment` com um token válido.
6. Registre **RPO real** (hora do dump → hora do incidente) e **RTO real** (declaração → API saudável).

## O que o ensaio garante (e o que não)
- Garante: o dump existe, bate com o SHA-256 do manifesto, restaura sem erro numa instância PostgreSQL 16 e cada tabela tem `antes ≤ restaurado ≤ depois` linhas.
- **Não** garante: integridade semântica dos dados, restauração em outra versão maior do PostgreSQL, nem que o dump esteja fora do host (por padrão está no mesmo disco — **copie para fora do host** para proteger de perda do servidor; destino é decisão sua).

## Cuidados
- Dumps contêm dados da aplicação (nesta fase, simulados). Em dados reais: criptografe em repouso, restrinja acesso e defina retenção conforme a política.
- `restore` derruba e recria o banco: nunca rode sem `--yes` consciente e nunca contra o VPS sem pedido explícito.
- Trocar de versão maior do PostgreSQL exige `pg_upgrade` ou dump/restore entre versões; não testado.
