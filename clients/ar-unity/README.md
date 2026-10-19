# Cliente AR (Unity) — Fase 2

> **Honestidade de estado:** o **núcleo** (`Packages/com.spatial.ar.core`) é testado (ver abaixo). A **cola Unity**
> (`Assets/Scripts`, `Assets/Editor`) foi escrita **sem Unity instalado**: **nunca foi compilada nem executada**.
> A AR só será considerada validada após o [checklist em aparelho](../../docs/runbooks/ar-device-checklist.md).

Spec: [SPEC-008](../../specs/functional/SPEC-008-ar-client.md) · Decisão: [ADR-0003](../../docs/adr/0003-ar-client-architecture.md) · Requisitos REQ-AR-001…007.

## Versões (D-012, conferidas em `packages.unity.com`)
Unity **6.3 LTS (6000.3)** · AR Foundation **6.3.5** · ARCore XR Plugin **6.3.5** · Test Framework 1.4.6 · Newtonsoft 3.2.1 · ZXing.Net 0.16.9 (`zxing.unity.dll`).

## Estrutura
| Caminho | O que é | Estado |
|---|---|---|
| `Packages/com.spatial.ar.core/Runtime/` | Núcleo C# puro (sem `UnityEngine`): `QrPayload`, `SpatialApiClient`, `MarkerSession` (reducer), `OverlayViewModel`, `SessionDriver`, `ClientConfig` | **testado** em `tests/csharp` (xUnit) na CI; compila como `netstandard2.1`/C# 9 |
| `Assets/Scripts/` | `SpatialArApp` (composition root + HUD), `QrScanner` (ARCore → ZXing), `UnityWebRequestTransport` | **não compilado** |
| `Assets/Editor/ProjectSetup.cs` | menu *Spatial › Configure Android player settings* | **não compilado** |
| `Packages/manifest.json` | dependências oficiais Unity | versões conferidas no registro; não resolvidas por um editor |

## Montagem (primeira vez, ~30 min) — no PC com Unity Hub
1. **Instale** Unity Hub + **Unity 6.3 LTS** com *Android Build Support* (SDK, NDK, OpenJDK inclusos). (Licença Personal exige login — é com você.)
2. **ZXing:** em uma rede sem bloqueio de `.nupkg`, rode `scripts/fetch-zxing-unity.ps1 -ExpectedSha256 <hash da CI>`
   (copia `zxing.unity.dll` para `Assets/Plugins/ZXing/`, ignorado pelo Git). O hash é impresso pelo job `csharp` da CI.
3. Abra `clients/ar-unity/` no Unity Hub. **Corrija erros de compilação** da cola (esperados; registre quais no checklist).
4. *Spatial › Configure Android player settings*; em *Project Settings › XR Plug-in Management › Android* marque **ARCore**.
5. Crie a cena (*GameObject › XR › AR Session* e *XR Origin (Mobile AR)*). No XR Origin adicione **ARRaycastManager** e **ARAnchorManager**;
   na câmera, **ARCameraManager**. Adicione `QrScanner` (campo *Camera Manager*) e `SpatialArApp` num GameObject vazio e ligue os campos.
6. No PC: `docker compose up --build --wait` e `adb reverse tcp:8088 tcp:8088`. Build **Development** → *Build And Run* no aparelho.
7. Execute o checklist e anexe vídeo/medidas em `docs/evidence/phase-2/`.

## Regras que a cola NÃO pode quebrar
- Nunca logar token, URL, texto bruto do QR ou corpo de resposta (o núcleo só emite códigos fixos).
- Nunca recalcular status no cliente: exibir o `status` do servidor.
- Nenhuma chamada Unity fora da thread principal (por isso o driver não usa `ConfigureAwait(false)`).
- Release: `ClientConfig.Validate()` recusa `http://` e token `demo-`.

## Testes do núcleo
`dotnet test tests/csharp/Spatial.Ar.Core.Tests` (xUnit + Newtonsoft + ZXing.Net via NuGet). **Na máquina do desenvolvedor o proxy
corporativo bloqueia `.nupkg`**, então esses testes rodam na **CI** (job `csharp`). Localmente só é possível compilar o núcleo contra um stub.
