# Runbook — Assistente de IA assistiva (Fase 3)

Spec: [SPEC-009](../../specs/functional/SPEC-009-ai-assistant.md) · Decisão: [ADR-0004](../adr/0004-assistant-architecture.md) · Evidência: [eval-report](../evidence/phase-3/eval-report.md).

## Usar (padrão: extrativo, offline, sem custo)
```powershell
docker compose up --build --wait
$body = '{"equipment_id":"EQ-001","question":"Por que a temperatura do compressor está alta?"}'
curl.exe -s -X POST -H "Authorization: Bearer demo-operator-a" -H "Content-Type: application/json" -d $body http://127.0.0.1:8088/api/v1/assistant/questions
```
Campos de resposta: `outcome` (`answered` | `insufficient_evidence` | `refused`), `sources` (trechos literais), `confidence` (cobertura **lexical**, não probabilidade), `human_review_required`, `provider`, `fallback_used`, `live_state` (estado/alertas **por regra**, não por IA).

## Adicionar ou revisar documentos (`knowledge/`)
1. Crie `knowledge/DOC-XXX-NNN.md` com o cabeçalho (`id`, `title`, `status`, `approved_by`, `approved_on`, `version`, `equipment_types`).
2. Só `status: approved` com aprovador e data válidos é carregado. **A aprovação deve ser de uma pessoa responsável** — os documentos atuais são **fictícios** (`approved_by: demo-fixture`).
3. Marque procedimentos de energia/pressão/partida com `## Título [risco: alto]`.
4. `pytest tests/unit/assistant/test_knowledge.py` (a base entregue não pode ter rejeições) e `python scripts/eval_assistant.py` para reavaliar.
5. O log de partida da API (`knowledge base loaded`) lista trechos carregados e **rejeições com motivo**.

## Ligar o LLM (opcional; exige sua aprovação — serviço pago)
1. Em `.env` (ignorado pelo Git): `ASSISTANT_PROVIDER=llm` e `ANTHROPIC_API_KEY=...`. Sem a chave a API **não inicia**.
2. Só os trechos aprovados recuperados e a pergunta saem do ambiente. Avalie LGPD/DPA antes de usar dados reais.
3. Toda resposta do LLM passa por verificação de fundamentação; se falhar, vem o extrativo com `fallback_used: true`.
4. **O adaptador nunca foi exercitado contra a API real.** Valide com 3–5 perguntas e confira os logs (`app.assistant`: `llm output rejected` indica saída descartada) antes de confiar.

## Operação
- Rate limit: 10 perguntas/min por usuário (`ASSISTANT_RATE_LIMIT`).
- Logs: `app.assistant` (desfecho, provedor, ids de fonte, tamanhos) e `app.audit` (`assistant.ask`). **Nunca** o texto da pergunta/resposta.
- Base vazia ⇒ o assistente sempre responde `insufficient_evidence` (aviso no log).
