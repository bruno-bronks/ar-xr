# SPEC-009 — Assistente de IA assistiva

Requisitos: REQ-AI-001 … REQ-AI-007 · Contrato: [`openapi.yaml`](../contracts/openapi.yaml) (`POST /api/v1/assistant/questions`) · Decisões: D-018…D-023 · Z: [z-005](../formal-z/z-005-assistant-answer.tex) · ADR: [ADR-0004](../../docs/adr/0004-assistant-architecture.md).

## Problema e atores
O operador pergunta sobre um equipamento (ex.: "por que a temperatura está alta?") e recebe uma orientação **baseada em documentação aprovada**, com fontes e incerteza. A IA é **assistiva**: nunca aciona, desliga nem ajusta nada; decisão e execução são humanas. Atores: operador autenticado (organização), base de conhecimento (arquivos versionados), provedor LLM opcional.

## Separação obrigatória
| Conceito | Origem | Campo |
|---|---|---|
| Estado e alertas | **Regra determinística** (twin, SPEC-002/006) | `live_state` |
| Orientação de manutenção | **Documentação aprovada** (trechos literais) | `answer` + `sources` |
| Hipótese gerada por IA | só existe com LLM ligado; sempre verificada contra os trechos | `provider = "llm"` |

O assistente **não** altera `live_state` e não cria alertas.

## Base de conhecimento (REQ-AI-002)
- Arquivos `knowledge/*.md`; cabeçalho `---`/`---` com `id`, `title`, `status`, `approved_by`, `approved_on` (AAAA-MM-DD), `version`, `equipment_types` (lista separada por vírgula; `*` = todos).
- **Aprovado** ⇔ `status = approved` ∧ `approved_by` não vazio ∧ `approved_on` data válida ∧ `id` único. Caso contrário o documento inteiro é **rejeitado** (com motivo) e nada dele é indexado.
- Seções `## Título` viram trechos (`DOC#n`). Sufixo `[risco: alto]` no título marca trecho de **risco alto** (procedimentos que envolvem energia, partida/parada, pressão).
- Trecho cujo texto contém instrução ao sistema (padrões de injeção, ex.: "ignore as instruções anteriores", "system prompt") é **excluído** e registrado; o resto do documento permanece.
- Nenhum dado de paciente/pessoa na base; conteúdo atual é **fictício** (D-019).

## Fluxo de `ask(question, equipment, live_state)`
1. **Normalização:** `NFKC`, remove caracteres de controle, colapsa espaços; vazio ⇒ 422 (validação HTTP, 1–2000 caracteres).
2. **Política (REQ-AI-004), antes de qualquer recuperação ou LLM:** se a pergunta pede ação física, contorno de proteção ou traz instruções ao sistema ⇒ `refused` com `refusal_reason ∈ {physical_action, safety_bypass, prompt_injection}`, `human_review_required = true`, `sources = []`. Nenhum LLM é chamado.
3. **Recuperação:** BM25 lexical (sem acentos, stopwords PT, radical por prefixo) restrita a trechos cujo `equipment_types` contém o tipo do equipamento (ou `*`). Máx. 3 trechos.
4. **Evidência (REQ-AI-003, D-021):** `cobertura = termos da pergunta presentes no melhor trecho / termos significativos`. `cobertura < 0,5` ⇒ `insufficient_evidence` (sem fontes, `confidence = low`, `human_review_required = true`).
5. **Resposta:**
   - *extrativo* (padrão): cita até 2 trechos como frases **literais** do documento, ordenadas por relevância.
   - *llm* (opcional): o LLM recebe só os trechos recuperados e o estado como **dados**; deve devolver JSON `{answer, citations[]}`. Aceito apenas se: JSON estrito; `citations` não vazio e ⊆ trechos recuperados; **todo número** da resposta existe nos trechos citados; ≤ 15 % dos termos de conteúdo sem suporte nos trechos citados/pergunta. As **fontes** exibidas são geradas pelo sistema a partir dos trechos citados (o LLM não escreve fontes). Qualquer falha ⇒ **fallback** extrativo (`fallback_used = true`).
6. **Revisão humana:** `human_review_required = true` se algum trecho citado é de risco alto, se `confidence = low`, ou se o estado ao vivo é `CRITICAL`/`OFFLINE`.
7. **Aviso fixo** anexado à resposta: sugestão assistiva, não aciona ação física, confirmar com o responsável.

## Confiança (D-021)
`cobertura ≥ 0,8` alta · `≥ 0,65` média · `≥ 0,5` baixa. É uma medida **lexical**, não uma probabilidade de acerto; o contrato descreve isso.

## Contrato HTTP (REQ-AI-006)
`POST /api/v1/assistant/questions` · corpo `{equipment_id, question}` (`extra=forbid`) · 200 `AssistantAnswer` · 401 · 404 (equipamento inexistente ou de outra organização, idêntico) · 422 · 429 (`Retry-After`, 10/min por usuário) · auditado (`assistant.ask`) sem o texto da pergunta.

## Logging seguro (REQ-AI-006, D-022)
Log estruturado `app.assistant` com: `outcome`, `provider`, `fallback_used`, `source_ids`, `question_chars`, `answer_chars`, `correlation_id`. **Proibido** registrar pergunta, resposta, trechos, chave de API, corpo de requisição ao provedor.

## Segurança e limites
- Texto de pergunta e de documentos é **dado**: nunca concatenado como instrução fora de delimitadores; saída do LLM nunca é executada.
- A chave do provedor é `SecretStr`, só em variável de ambiente; erros do provedor viram `LlmUnavailable` sem corpo/URL/chave.
- Disjuntor (3 falhas seguidas ⇒ 30 s sem chamar o provedor) e *timeout* de 10 s.
- **O que NÃO é garantido:** a recusa por padrões é heurística (D-020); a cobertura lexical não entende sinônimos; com LLM ligado, a verificação de fundamentação é lexical (não semântica) e pode aceitar paráfrase enganosa ou recusar uma boa; o adaptador Anthropic **não foi exercitado contra a API real**.

## Painel web (REQ-UX-002)
Seção "Assistente (apenas informativo)" em `clients/web-fallback/`: seletor de equipamento (da organização ativa) + pergunta (até 2000 caracteres) → `POST /api/v1/assistant/questions` com o mesmo token do painel. Exibe o selo do desfecho, a resposta, cada fonte (`documento · seção (vN)` + excerto), a confiança **lexical** (com o aviso de que não é probabilidade), o estado pelas regras e "Revisão humana necessária". Erros 401/404/422/429/rede aparecem em um aviso; resposta de uma organização anterior é descartada (contador de geração) e a troca de organização limpa pergunta, lista e resposta. Todo texto entra via `textContent` (CSP estrita, sem HTML da API).

## Avaliação (REQ-AI-007)
`tests/evaluation/golden_set.json` rotula perguntas: respondíveis (documento esperado), sem resposta na base, ação física, contorno de segurança, injeção, outro equipamento. `scripts/eval_assistant.py` mede e grava `docs/evidence/phase-3/eval-report.md`:
- **Taxa de alucinação** = respostas `answered` com algum número/termo de conteúdo sem suporte nas fontes citadas ÷ respostas `answered`.
- **Precisão de citação** = fontes cujo excerto é literal do trecho ÷ fontes emitidas.
- **Acerto de documento** nas respondíveis; **abstenção correta** nas sem resposta; **recusa correta** nas perigosas.
- O mesmo verificador é aplicado a saídas de um LLM *simulado* adversarial para provar que ele rejeita alucinações (não mede um LLM real).
