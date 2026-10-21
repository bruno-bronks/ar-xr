# Estado desejado (GitOps)

Cada ambiente tem um arquivo `deploy/desired/<ambiente>.json`; o reconciliador (`scripts/gitops_reconcile.py`)
le **este arquivo do commit remoto** e converge a pilha para ele. Para promover uma release: abra um PR
alterando `tag`; o merge e a aprovacao.

```json
{"tag": "v0.6.0", "backup": true, "note": "texto livre (opcional, ate 200 caracteres)"}
```

- `tag` (obrigatoria): tag de imagem (`[A-Za-z0-9][A-Za-z0-9._-]{0,63}`).
- `backup` (opcional, padrao `false`): faz backup + ensaio de restauracao ANTES de subir (use quando a release traz migracoes).
- **Qualquer outro campo reprova a leitura inteira** (nada e ignorado em silencio, nada vira comando).

Nao existe `vps.json` de proposito: o VPS so entra no GitOps por pedido explicito do usuario.
