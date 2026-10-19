# CURRENT_STATE — memória determinística do projeto

Atualizado: 2026-10-19 · `main` contém as Fases 0, 1 e 2 (PR #1 e **PR #2 mesclados** a pedido explícito do usuário; merge 5aa73db; última branch de trabalho: `feature/ar-android-phase2`, já mesclada). **Fase 2 parcialmente concluída: o que dá para fazer sem aparelho está pronto; a validação em aparelho físico está BLOQUEADA por hardware — e o aparelho Android do usuário NÃO oferece ARCore** (ver "Próximo passo").

> Validado por `tests/unit/repo/test_agent_memory.py` (links, caminhos e REQs citados precisam existir).
> Aprovações do usuário: Fase 0, decisões D-001/D-003/D-004/D-006, ADR-0001, Z via CZT, Graphify instalado e usado, Fase 1, merge do PR #1, **Fase 2** (sem responder às decisões D-013…D-015 nem informar o aparelho → ver D-016).

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

## O que NÃO foi feito / não está verificado
- **AR em aparelho físico: NADA validado** (REQ-AR-007 `planned`). Sem Android/ARCore, sem Unity instalado, sem câmera. Não há vídeo, latência QR→overlay, FPS nem estabilidade.
- **Cola Unity nunca compilada:** erros de compilação na 1ª abertura são esperados. Em especial não verificadas: `XRCpuImage.Convert`, `ARAnchorManager.TryAddAnchorAsync`/`result.status.IsSuccess()` (API do AR Foundation 6), asmdefs e referências. `QrScanner.cs` não é tocado por nenhum teste.
- **`scripts/fetch-zxing-unity.ps1` não foi executado:** o proxy corporativo bloqueia `.nupkg` ("File Transfer Blocked"); **não contornei**. Por isso `Assets/Plugins/ZXing/zxing.dll` não existe. Corrigi um erro meu: o pacote ZXing.Net 0.16.9 **não** tem `lib/unity` (achado na CI) — usa-se `netstandard2.1`.
- Testes C# **não rodam na máquina do desenvolvedor** (mesmo bloqueio de NuGet); só compilação local contra stub. Rodam na CI.
- **Decisões D-013…D-015 adotadas por default** (ZXing.Net, `adb reverse`, projeto no repositório) sem confirmação do usuário (D-016).
- **Dreaming:** ainda **não** instalado/usado (serviço de nuvem pago, acesso sob solicitação) — decisão pendente do usuário (opções A/B/C da Fase 1).
- Herdado: autenticação demo, Mosquitto anônimo, rate limit em memória, sem OIDC/RBAC, CI de segurança incompleta (Semgrep/Trivy/SBOM), Python 3.12 local não obtido.

## Defeitos encontrados na Fase 2 (corrigidos)
1. Driver usava `ConfigureAwait(false)`: a próxima requisição `UnityWebRequest` rodaria fora da thread principal — removido (visto na revisão, antes da CI).
2. Teste de relógio com `AddSeconds(4.6)` truncava um tick no .NET — instantes exatos em binário.
3. Suposição minha de `lib/unity` no ZXing.Net — refutada pela CI.
4. Teste que presumia rigor de tipo do Newtonsoft (número→string) — removido.

## Próximo passo (depende de você)
**Bloqueio novo:** o Android do usuário não tem a opção de ARCore (aparelho provavelmente não suportado ou sem Google Play Services for AR). A AR Foundation no Android **exige ARCore**. Caminhos propostos (decisão do usuário pendente): (1) usar outro aparelho que apareça na lista oficial de dispositivos ARCore; (2) modo sem AR no Unity (câmera comum + QR + HUD, sem âncora 3D); (3) leitor de QR no painel web (PWA) para validar o fluxo QR→API→exibição no celular real, sem Unity; (4) provedores alternativos (Huawei AR Engine, Vuforia) — maior risco/custo.
Em qualquer caminho: executar o checklist `docs/runbooks/ar-device-checklist.md` e anexar vídeo/medidas em `docs/evidence/phase-2/`; só então REQ-AR-001…005 podem virar `verified`. Instalar Unity Hub/6.3 LTS (licença Personal) e obter o ZXing numa rede **sem** bloqueio de `.nupkg`. Fase 3 (IA assistiva) **não** foi iniciada.
