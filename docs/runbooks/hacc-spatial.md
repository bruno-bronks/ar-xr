# Runbook — HACC Spatial (Fase 4, dados SIMULADOS)

Spec: [SPEC-010](../../specs/functional/SPEC-010-hacc-spatial.md) · Decisão: [ADR-0005](../adr/0005-hacc-adapter-and-scopes.md) · Contrato assumido: [hacc-readonly.yaml](../../specs/contracts/hacc-readonly.yaml).

> **O HACC real não foi lido, contatado nem alterado.** O contrato acima é uma suposição minha. Tudo aqui roda contra uma fonte **simulada**.

## Usar (padrão: fonte simulada, sem rede externa)
```powershell
docker compose up --build --wait
start http://127.0.0.1:8088/panel/   # escolha "Enfermagem A (demo · leitos)" na caixa de organização
curl.exe -s -H "Authorization: Bearer demo-nurse-a" http://127.0.0.1:8088/api/v1/hacc/wards
curl.exe -s -H "Authorization: Bearer demo-nurse-a" http://127.0.0.1:8088/api/v1/hacc/wards/WARD-A1/beds
```
- `demo-nurse-a` / `demo-nurse-b` têm o escopo `hacc:read` (organizações A e B). `demo-operator-*` **não** têm: recebem 403.
- Ala de outra organização ou inexistente: 404 idêntico. Fonte indisponível: 503 `hacc source unavailable`.
- A simulação roda um ciclo de 60 s: alarme de saída, bomba de infusão, chamada e limpeza se alternam; o leito `A1-06` nunca tem leitura (`UNKNOWN`) e o `U-03` fica mudo (`OFFLINE`).

## Estados do leito (regra, sem leitura clínica)
`OFFLINE` (leitura > 30 s) > `ALERT` (saída de leito ocupado, bomba de infusão) > `ATTENTION` (chamada, limpeza) > `NORMAL`; sem leitura = `UNKNOWN`. O painel não recalcula: exibe o que a API devolve.

## Ligar o adaptador HTTP (somente leitura; **não** validado contra o HACC real)
Exige o contrato REAL do HACC, análise LGPD e autorização. Só então:
```
HACC_SOURCE=http
HACC_BASE_URL=https://<host-do-hacc>
HACC_ALLOWED_HOSTS=<host-do-hacc>
```
O cliente só envia `GET /v1/wards` e `GET /v1/wards/{id}/beds`, sem redirecionamentos, timeout 5 s, corpo ≤ 1 MB; payload com campo fora do esquema é rejeitado por inteiro. **Antes de usar com fonte real:** adicionar rate limit e disjuntor aos endpoints `/hacc`, mapear o contrato real e revisar o `tenant_id` (D-030).

## Operação e limites
- Log `app.hacc` só com contagens; auditoria `hacc.*` com usuário, organização, ala e desfecho — nunca estado ou rótulo de leito.
- Nenhum banco, tabela ou migração foi adicionado: não há cópia de dados do HACC.
- RBAC parcial (um escopo); overlay só 2D no painel — o cliente AR não foi estendido.

## Integração com o HACC real (D-054)
Fonte `hacc`, **desligada por padrão**. Pré-requisito: o HACC precisa da rota `GET /integration/v1/beds` (patch em `docs/integration/hacc-patch/`, a aplicar pelo dono do HACC) e de `HACC_INTEGRATION_TOKEN` (≥ 16 caracteres, fora do Git) no ambiente dele.
```powershell
# lado AR_XR (API): variaveis de ambiente (nunca no Git)
$env:HACC_SOURCE = "hacc"; $env:HACC_BASE_URL = "http://127.0.0.1:8000"   # http so em loopback; fora disso, https
$env:HACC_ALLOWED_HOSTS = "127.0.0.1"; $env:HACC_API_TOKEN = "<o mesmo token>"; $env:HACC_TENANT_ID = "org-a"
```
- Mostra ocupado/livre/**Bloqueado** (HACC `unavailable`); alarmes de leito **não existem** nessa fonte. As alas vêm do perfil (`ICU`, `Emergency`, `Ward`).
- A API do AR_XR em contêiner **não** alcança `127.0.0.1` do host: para testar localmente rode a API no host, ou use HTTPS com host em lista. Falha da fonte ⇒ 503 uniforme e a vista fica marcada como desatualizada.
- Teste contra um HACC em execução (cópia isolada, nunca com dados reais de pessoas): `HACC_REAL_URL=... HACC_REAL_TOKEN=... python -m pytest tests/integration/test_hacc_real.py`.
- Nenhum dado de paciente é lido ou armazenado; se o HACC passar a devolver campo novo na rota, a resposta é rejeitada (503) até o contrato ser revisado.

## HACC (cópia) na VPS — teste online (D-055)
`deploy/vps/hacc/` sobe uma **cópia isolada** do HACC na VPS (dados do simulador; não é o HACC do usuário) em `/opt/hacc-copy`, ligada à API do AR_XR pela rede interna do Docker. A API usa `HACC_SOURCE=hacc`, `HACC_BASE_URL=http://hacc-backend:8000`, `HACC_ALLOWED_HOSTS=hacc-backend`, `HACC_ALLOW_PLAIN_HTTP=true` (http só em rede privada) e o token em `HACC_API_TOKEN` (gerado no servidor). Ver `deploy/vps/hacc/README.md`.
- **Ver:** painel público → "Enfermagem A (demo · leitos)" → alas `HACC-ICU`, `HACC-ER`, `HACC-WARD`, em 2D e 3D. Um leito indisponível aparece como **Bloqueado**.
- **Provocar um leito bloqueado/livre na cópia (no servidor):** `POST http://127.0.0.1:28000/events/` com `{"event_type":"bed_unavailable","bed_id":"WARD-03"}`.
- **Desfazer:** `cd /opt/hacc-copy && docker compose down -v`; remover as variáveis `HACC_*` de `/opt/ar-xr/.env` (há cópia em `.env.bak-pre-hacc`) e `docker compose up -d api` (volta à fonte simulada). Rollback da imagem: `spatial-ai-api:hacc-pre`.
