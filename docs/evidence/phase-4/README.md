# Evidência da Fase 4 — HACC Spatial (2026-10-20)

Tudo abaixo foi **executado** nesta máquina (Windows 11, Python 3.13, Docker 29.8.2). A CI do GitHub **não** foi executada para esta branch.

> **O HACC real não foi lido, contatado nem alterado.** O contrato `specs/contracts/hacc-readonly.yaml` é uma **suposição** (marcada `x-verified-against-real-hacc: false`). O adaptador HTTP foi testado contra um servidor **local de teste**. Nada aqui prova compatibilidade com o HACC real.

| Verificação | Comando | Resultado |
|---|---|---|
| Lint / formato / tipos / dependências | `scripts/check.ps1` | passou (113 arquivos, mypy strict; `pip-audit` sem achados, sem dependências novas) |
| Testes sem Docker | `scripts/check.ps1` (pytest) | 747 passaram, 139 pulados (pulam sem PostgreSQL/pilha) |
| Suíte completa com PostgreSQL real (sem integração) | `pytest -m "not e2e"` com `TEST_DATABASE_URL` | 829 passaram |
| Integração + desempenho na pilha real (imagem reconstruída com `packages/hacc`) | `pytest tests/integration tests/performance` | 36 passaram (inclui 4 do HACC: `tests/integration/test_hacc_stack.py`) |
| E2E no navegador (Edge) | `pytest tests/e2e` | 21 passaram (14 anteriores + 7 de leitos: planta, UTI offline, sem escopo, org-B, HTML hostil como texto, 503 com planta desatualizada, 360 px sem violação de CSP) |
| Especificações Z | `scripts/verify-z.ps1` | 5 de 5 passam parse + typecheck no CZT (incl. `z-006`); **nenhum teorema provado** |
| Invariantes B1–B3 | Hypothesis (`tests/unit/domain/test_beds.py`) | passaram |
| Mutação (manual) | 16 alterações deliberadas (domínio, segregação, escopo, adaptador HTTP) | 16 detectadas (1 sobrevivente inicial — checagem de tamanho — era quase equivalente; o teste agora exige a mensagem e o mata) |

Capturas: [planta da ala A](panel-hacc-ward.png).

## O que foi comprovado
- **Somente leitura:** a porta só tem `list_wards`/`list_beds`; o adaptador HTTP só envia `GET` (servidor de teste grava cada requisição), sem redirecionamento, host/esquema permitidos, `ward_id` validado, timeout e limite de tamanho; erros sem corpo/URL.
- **Minimização:** a lista de campos do leito é travada por teste; qualquer campo extra (nome, CPF, prontuário, sinais vitais…) rejeita o payload inteiro; respostas e logs sem dado pessoal.
- **Autorização e segregação:** 401 sem token; 403 sem `hacc:read` (operadores); 404 idêntico para ala de outra organização ou inexistente; o `tenant_id` é imposto no nosso código mesmo que a fonte devolva registros alheios.
- **Estado por regra:** `UNKNOWN` sem leitura, `OFFLINE` com precedência, `ALERT`/`ATTENTION`; ala sem leitos ou com leito sem leitura nunca é `NORMAL`.

## Não verificado
- Qualquer chamada ao HACC real; compatibilidade do contrato assumido; dados reais; análise LGPD; validação clínica.
- Rate limit e disjuntor nos endpoints `/hacc` (não existem; necessários antes de uma fonte HTTP real).
- Celular físico (painel só em Edge/viewport emulado) e AR (o cliente Unity não foi estendido aos leitos).
- Deploy da Fase 4 no VPS (a pilha do VPS continua na versão da Fase 3).
