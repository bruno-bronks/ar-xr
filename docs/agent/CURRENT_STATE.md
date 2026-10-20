# CURRENT_STATE — memória determinística do projeto

Atualizado: 2026-10-20 · `main` contém as Fases 0, 1 e 2. **Fase 3 (IA assistiva) implementada na branch `feature/ai-assistant-phase3`, ainda sem commit/push/PR** (aguarda seu pedido e sua aprovação). Fase 2 segue parcial: a validação em aparelho físico depende de hardware (Samsung A54 + Unity) — ver "Próximo passo".

> Validado por `tests/unit/repo/test_agent_memory.py` (links, caminhos e REQs citados precisam existir).
> Aprovações do usuário: Fase 0, decisões D-001/D-003/D-004/D-006, ADR-0001, Z via CZT, Graphify instalado e usado, Fase 1, merge do PR #1, **Fase 2** (sem responder às decisões D-013…D-015 nem informar o aparelho → ver D-016), Dreaming adiado (opção B), **Fase 3** (pedido de implementação em 2026-10-20) e **D-018…D-023 aprovadas em 2026-10-20** (D-024), com commit/push/PR, campo de pergunta no painel e redeploy no VPS.

## Fases 0–1 (mescladas em `main`, verificadas)
Pilha completa simulador → Mosquitto → worker → PostgreSQL → API (Bearer **demo**) → painel 2D; 528 testes passaram com pilha real, PostgreSQL real e E2E (Edge); CI do GitHub verde nos 4 jobs originais. Evidências em `docs/evidence/phase-0/` e `docs/evidence/phase-1/` (latência publicar→API p95 0,276 s, n=100, 1 máquina). Specs Z passam no typecheck do CZT; **nenhum teorema provado**.

## Fase 2 — o que existe
- **Spec/decisões:** [SPEC-008](../../specs/functional/SPEC-008-ar-client.md), [ADR-0003](../adr/0003-ar-client-architecture.md), REQ-AR-001…007, D-012…D-017 em [requirements.md](../requirements/requirements.md).
- **Núcleo C# puro** `clients/ar-unity/Packages/com.spatial.ar.core/Runtime/` (validação do QR, cliente da API, reducer `MarkerSession`, `OverlayViewModel`, `SessionDriver`, `ClientConfig`): **171 testes xUnit passaram na CI** (run 39326391535), build `netstandard2.1`/C# 9 com warnings como erro — ver `docs/evidence/phase-2/ci-csharp.txt`. Cobre JSON **real** da API (fixtures geradas por `tests/contract/test_ar_fixtures.py`) e decodificação ZXing.Net dos 8 QR de teste.
- **QR de teste:** `scripts/generate_qr.py` → `docs/evidence/phase-2/qr/` (3 válidos, 1 de outra org, 1 desconhecido, 3 conteúdos inválidos); decodificados de forma independente pelo OpenCV (local) e pelo ZXing.Net (CI).
- **Cola Unity** `clients/ar-unity/Assets/Scripts/` e `clients/ar-unity/Assets/Editor/ProjectSetup.cs`: escrita **sem Unity — nunca compilada nem executada**. Pacotes/versões do `clients/ar-unity/Packages/manifest.json` conferidos no registro oficial da Unity, não resolvidos por um editor.
- **Checklist em aparelho** `docs/runbooks/ar-device-checklist.md`: pronto, **NÃO executado**.
- **Ferramentas:** .NET SDK 10.0.402 em `~/.tools` (SHA-512 verificado) para compilar o núcleo localmente contra um stub; Graphify agora também indexa C# (cruzamento em `graph/mappings/crosscheck.md`).
- **CI:** job `csharp` e os demais verdes no PR #2 (head f72a2cb), antes do merge.

## Fase 3 — IA assistiva (implementada, branch `feature/ai-assistant-phase3`, não commitada)
- **Spec/decisões:** [SPEC-009](../../specs/functional/SPEC-009-ai-assistant.md), [ADR-0004](../adr/0004-assistant-architecture.md), `specs/formal-z/z-005-assistant-answer.tex` (typecheck CZT OK; nada provado), REQ-AI-001…007 e D-018…D-023 em [requirements.md](../requirements/requirements.md). Runbook: [assistant.md](../runbooks/assistant.md).
- **Código:** pacote puro `packages/assistant/src/spatial_assistant/` (base, recuperação BM25+cobertura, política de recusa, verificação de fundamentação, serviço), rota `services/api/app/assistant_routes.py` (`POST /api/v1/assistant/questions`), base **fictícia** em `knowledge/` (5 documentos, 20 trechos).
- **Comportamento:** padrão **extrativo/offline** (trechos literais de documentos aprovados + fontes + confiança lexical + revisão humana); recusa ação física/contorno de segurança/injeção; abstém sem evidência; estado e alertas vêm da **regra** (`live_state`), não da IA; log só com metadados; 10 perguntas/min por usuário; isolamento por organização (404 uniforme).
- **Painel:** seção "Assistente (apenas informativo)" em `clients/web-fallback/` (REQ-UX-002; 6 testes E2E no navegador). Não testado em celular físico.
- **LLM opcional** (`ASSISTANT_PROVIDER=llm` + `ANTHROPIC_API_KEY`): desligado; saída verificada (JSON estrito, citações ⊆ recuperados, números/termos com suporte) ou cai no extrativo. **Nunca exercitado contra a API real.**
- **Testes executados:** 601 passam em `scripts/check.ps1` (+ ruff, mypy strict, pip-audit sem achados); 682 com PostgreSQL real; 32 de integração/desempenho + 4 do assistente + 8 E2E na pilha real reconstruída. Invariantes A1–A4 por Hypothesis; mutação manual 11/11. Evidência e números honestos em `docs/evidence/phase-3/README.md` e `docs/evidence/phase-3/eval-report.md`.
- **Avaliação (conjuntos do próprio agente; não independente):** alucinação do extrativo 0 e citação 100 % literal (por construção); recuperação lexical ainda erra sinônimos e responde fora de escopo em parte das perguntas; no conjunto de reserva 2 de 5 pedidos de contorno/injeção parafraseados não foram recusados (sem ação nem resposta inventada).

## O que NÃO foi feito / não está verificado
- **AR em aparelho físico: NADA validado** (REQ-AR-007 `planned`). Sem Android/ARCore, sem Unity instalado, sem câmera. Não há vídeo, latência QR→overlay, FPS nem estabilidade.
- **Cola Unity nunca compilada:** erros de compilação na 1ª abertura são esperados. Em especial não verificadas: `XRCpuImage.Convert`, `ARAnchorManager.TryAddAnchorAsync`/`result.status.IsSuccess()` (API do AR Foundation 6), asmdefs e referências. `QrScanner.cs` não é tocado por nenhum teste.
- **`scripts/fetch-zxing-unity.ps1` não foi executado:** o proxy corporativo bloqueia `.nupkg` ("File Transfer Blocked"); **não contornei**. Por isso `Assets/Plugins/ZXing/zxing.dll` não existe. Corrigi um erro meu: o pacote ZXing.Net 0.16.9 **não** tem `lib/unity` (achado na CI) — usa-se `netstandard2.1`.
- Testes C# **não rodam na máquina do desenvolvedor** (mesmo bloqueio de NuGet); só compilação local contra stub. Rodam na CI.
- **Decisões D-013…D-015 adotadas por default** (ZXing.Net, `adb reverse`, projeto no repositório) sem confirmação do usuário (D-016).
- **Dreaming:** ainda **não** instalado/usado (serviço de nuvem pago, acesso sob solicitação) — **decisão do usuário: opção B (adiar)**, com gatilhos de revisão em `docs/decisions/tool-evaluation.md`. Não atende ao pedido original de instalar/usar; é adiamento assumido.
- **Fase 3:** base de conhecimento fictícia e sem revisão técnica humana (D-019); nenhum LLM real foi chamado; verificador de fundamentação é lexical (aceita inversões semânticas); D-018…D-023 adotadas por default sem sua confirmação; Fase 3 **não** foi implantada no VPS.
- Herdado: autenticação demo, Mosquitto anônimo, rate limit em memória, sem OIDC/RBAC, CI de segurança incompleta (Semgrep/Trivy/SBOM), Python 3.12 local não obtido.

## Implantação de demonstração no VPS (2026-10-19)
Pilha completa rodando em VPS compartilhado, fora da CI: migração OK, `/health/ready` 200, simulador→worker→banco gravando, portas internas só em loopback; painel público em `https://ar-xr.bronks.ia.br/panel/` com login básico, somente leitura. Testado de fora (401 sem login, 200 com login, `POST` 403). Detalhes e limites em `deploy/vps/README.md`; override do Compose em `deploy/vps/compose.override.yaml`. **Não** é produção: auth demo, Mosquitto anônimo, sem monitoramento nem backup.

## Defeitos encontrados na Fase 2 (corrigidos)
1. Driver usava `ConfigureAwait(false)`: a próxima requisição `UnityWebRequest` rodaria fora da thread principal — removido (visto na revisão, antes da CI).
2. Teste de relógio com `AddSeconds(4.6)` truncava um tick no .NET — instantes exatos em binário.
3. Suposição minha de `lib/unity` no ZXing.Net — refutada pela CI.
4. Teste que presumia rigor de tipo do Newtonsoft (número→string) — removido.

## Próximo passo (depende de você)
1. **Fase 3:** revisar e aprovar; pedir commit/push/PR/merge (nada foi enviado). Decidir se aprova D-018…D-023 e se a base fictícia deve ser substituída por documentos reais **aprovados por uma pessoa responsável**.
2. **AR (Fase 2):** o aparelho escolhido é o Samsung A54 (lista oficial ARCore). Falta instalar Unity Hub (como administrador) + Unity 6.3 LTS com Android Build Support, ligar depuração USB e executar `docs/runbooks/ar-device-checklist.md`; erros de compilação da cola Unity são esperados na 1ª abertura. Só então REQ-AR-001…005 podem virar `verified`.
3. **VPS:** a demonstração publicada ainda roda a versão da Fase 2; redeploy da Fase 3 só se você pedir. Pendências de segurança lá: trocar a senha root compartilhada no chat e remover a chave de deploy temporária.
4. **Dreaming:** adiado por decisão sua (opção B); gatilhos de revisão em `docs/decisions/tool-evaluation.md`.
5. **LLM real** para o assistente: exige sua aprovação (serviço pago), chave em `.env` e validação manual do adaptador (nunca testado contra a API real).
Fase 4 (HACC Spatial) **não** foi iniciada e depende da sua aprovação.
