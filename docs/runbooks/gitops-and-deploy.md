# Runbook — release, deploy, rollback e GitOps

Escopo: **homologação local** (Docker) e, **somente a pedido explícito**, o VPS. Nada aqui contrata nuvem. Spec: [SPEC-012](../../specs/functional/SPEC-012-cloud-and-operations.md).

## 1. Registry local e ambiente de homologação
```powershell
docker run -d --name spatial-registry -p 127.0.0.1:5000:5000 registry:2     # use 127.0.0.1, não "localhost" (IPv6)
python scripts/deploy.py build --tag v0.6.0 --registry 127.0.0.1:5000/ --push
python scripts/deploy.py deploy --env homolog --tag v0.6.0                 # portas 18088/55433/11883, projeto spatial-homolog
python scripts/deploy.py status --env homolog
```
- `deploy/envs/homolog.env` não tem segredo (valores de dev). Para o VPS: copie `vps.env.example` para `deploy/envs/vps.env` (ignorado pelo Git) e defina `POSTGRES_PASSWORD` no servidor.
- Docker Desktop: o daemon só alcança registry em **porta fixa** publicada em `127.0.0.1` (porta dinâmica falha com *connection refused*).

## 2. Deploy
`deploy` faz: (`--backup`: backup + ensaio de restauração) → `pull` → `up -d --no-build --wait` → confere as imagens em execução → *smoke*. Se **qualquer** etapa falhar, volta sozinho para a tag anterior e sai com código 1 (2 se o rollback também falhar: intervenção manual). Use `--backup` quando a release trouxer **migração** (migrações não são desfeitas pelo rollback).

## 3. Rollback manual
```powershell
python scripts/deploy.py rollback --env homolog     # volta para `previous` e verifica
```
Se a migração da release nova já rodou e a anterior não a suporta: restaure o backup (ver [backup-restore](backup-restore.md)), não só troque a imagem.

## 4. GitOps (pull)
O estado desejado é `deploy/desired/<env>.json` na `main` (ver `deploy/desired/README.md`). Promover = PR trocando `tag`.
```powershell
python scripts/gitops_reconcile.py --env homolog                # uma rodada (o timer systemd faz isso a cada 5 min)
python scripts/gitops_reconcile.py --env homolog --retry-failed # depois de corrigir a causa de uma tag que falhou
```
Saídas JSON: `in-sync` · `applied` · `drift-corrected` · `failed` (voltou à tag boa) · `skipped-failed` (tag já falhou; **não** repete) · `error` (Git/estado inválido; nada muda) · `locked`. Códigos: 0 ok · 1 falhou/pulou · 2 erro de leitura · 3 outra rodada em andamento.

**Pré-requisito:** o clone em `/opt/ar-xr` precisa conseguir `git fetch` sem pedir senha (repositório público ou *deploy key* somente-leitura). Credenciais nunca vão para o repositório.

## 5. Release no GHCR (escrito, não executado)
`.github/workflows/release.yml` constrói e publica as 3 imagens quando uma **tag `v*`** é criada. Criar a tag é uma ação externa (publica artefatos): faça só quando decidir. Imagens em repositório privado exigem token de pull no servidor.

## 6. Provisionar um host (modelo, não executado)
`deploy/cloud-init/user-data.yaml` (preencher chave SSH e URL do repositório) + `deploy/systemd/*`. Validar sem servidor: `python scripts/verify_host.py`. O `POSTGRES_PASSWORD` é gerado no host no primeiro boot.

## Solução de problemas
| Sintoma | Causa provável | Ação |
|---|---|---|
| `pull failed; running stack untouched` | tag inexistente no registry / registry inacessível | publique a tag; confira `OPS_REGISTRY` |
| `verify-images` | outra imagem ainda em execução (container preso) | `docker compose -p <proj> ps`; recrie |
| `smoke` com `/health/ready` 503 | banco/broker fora ou release defeituosa | já houve rollback; veja `docker compose logs api` |
| `skipped-failed` | a tag desejada já falhou | corrija e use outra tag (imutável) ou `--retry-failed` |
| `locked` | outra rodada em andamento (ou morreu há < 30 min) | aguarde; trava velha > 30 min é retomada |
