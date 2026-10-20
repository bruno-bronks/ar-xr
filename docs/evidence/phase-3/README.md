# Evidência da Fase 3 — IA assistiva (2026-10-20)

Tudo abaixo foi **executado** nesta máquina (Windows 11, Python 3.13, Docker 29.8.2). A CI do GitHub **não** foi executada para esta branch.

| Verificação | Comando | Resultado |
|---|---|---|
| Lint / formato / tipos | `scripts/check.ps1` (ruff, ruff format, mypy strict) | passou (100 arquivos) |
| Testes sem Docker | `scripts/check.ps1` (pytest), repetido ao final | 601 passaram, 128 pulados (pulam sem PostgreSQL/pilha) |
| Testes com PostgreSQL real (unit/contract) | `pytest -m "not e2e"` com `TEST_DATABASE_URL`, sem integração | 682 passaram + 1 erro de *setup* (`ConnectionTimeout` do PostgreSQL durante uma execução de ~9 h de relógio, provavelmente suspensão da máquina); o arquivo do erro foi reexecutado: 116 passaram |
| Integração + desempenho na pilha real (Compose, imagem reconstruída com o assistente) | `pytest tests/integration tests/performance` | 32 passaram |
| Assistente na pilha real | `tests/integration/test_assistant_stack.py` | 4 passaram |
| E2E no navegador (painel, Edge) | `pytest tests/e2e` (reexecutado com o campo do assistente) | 14 passaram (8 anteriores + 6 do assistente: resposta com fontes, recusa, HTML hostil como texto, erro 429 visível, troca de organização, 360 px). Capturas: [resposta](panel-assistant-answer.png) · [recusa](panel-assistant-refused.png) |
| Auditoria de dependências | `pip-audit` (api, worker, simulador) | sem vulnerabilidades conhecidas (sem dependências novas) |
| Especificações Z | `scripts/verify-z.ps1` | 4 de 4 passam parse + typecheck no CZT (incl. `z-005`); **nenhum teorema provado** |
| Mutação (manual) | 11 alterações deliberadas na lógica do assistente | 11 detectadas pelos testes (1 lacuna achada e corrigida: limiar de evidência) |
| Avaliação | `python scripts/eval_assistant.py` | [eval-report.md](eval-report.md) · [primeira execução, antes do ajuste](eval-report-run1-before-tuning.md) |

## Resumo honesto da avaliação (conjuntos escritos pelo agente, base fictícia)
- **Primeira execução (54 perguntas, sem ajuste):** 9 falhas — 6 respostas fora de escopo onde deveria abster (inclusive uma colisão de radical *partida×participa*) e 1 pedido de contorno não recusado.
- **Ajustes (com teste primeiro):** radical de 6 letras, exigir ao menos um termo do **assunto** (não só o nome do equipamento), ampliar a regra "quero/preciso/vou + contornar…". Resultado no mesmo conjunto: 5 falhas.
- **Conjunto de reserva (27 perguntas, escrito depois do ajuste, medido uma vez):** 10/11 respondíveis corretas; abstenção correta em 6/8; recusa correta em 6/8 (as 2 falhas são paráfrases fora das regras: "alarme não disparar mais" e "ignorar as diretrizes" — viraram `insufficient_evidence`, sem ação nem resposta inventada).
- **Alucinação do extrativo: 0** (por construção: só devolve trechos literais). **Precisão de citação: 100 %.**
- **Verificador de fundamentação contra LLM *simulado*:** rejeitou 11/11 saídas ruins; aceitou 3/4 boas; **aceitou 2/2 inversões semânticas** feitas com as mesmas palavras (limite conhecido do método lexical).

## Redeploy no VPS (2026-10-20)
Imagens e `compose.yaml` atualizados; `up -d --no-build --wait` saudável; log `knowledge base loaded` com 20 trechos e `rejected: []`. Testes de fora via `https://ar-xr.bronks.ia.br`: painel com o formulário, pergunta respondida (`DOC-COMP-001`), recusa (`physical_action`), org-b 404, sem cookie 401, `GET` 403, outro `POST` 403, corpo grande 413.

## Não verificado
- Qualquer chamada a um LLM real (o adaptador Anthropic só foi testado com transporte simulado).
- Qualidade em produção, com usuários reais ou com documentação real (a base é fictícia, sem revisão humana).
- Carga/desempenho do assistente no VPS compartilhado (o servidor estava com carga média ~7,6 durante o redeploy).
