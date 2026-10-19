# ADR-0003 — Arquitetura do cliente AR: núcleo C# puro testável + cola Unity fina

## Status
Proposto (aguarda aprovação). Data: 2026-10-19. Complementa os ADR-0001/0002.

## Contexto
A Fase 2 exige Unity + AR Foundation + ARCore, mas esta máquina **não tem Unity nem aparelho**, e o plano proíbe declarar AR validada só com testes de backend. Código que depende de `UnityEngine` não pode ser compilado ou testado aqui. Ao mesmo tempo, a maior parte do risco do cliente (regras de QR, tratamento de erros, estados offline, segurança) é lógica comum.

## Decisão
1. Toda a lógica de decisão vive em um **núcleo C# sem `UnityEngine`** (`Spatial.Ar.Core`): validação do QR, cliente da API, máquina de estados da sessão (reducer puro: `evento → comandos`), modelo de apresentação e verificação de configuração.
2. O núcleo é um *package* Unity (asmdef com `noEngineReferences`) **e** compila fora do Unity (`netstandard2.1`, `LangVersion 9`), de modo que `dotnet test` roda em CI e na máquina de desenvolvimento.
3. A **cola Unity** é fina: câmera/ARCore → luminância → ZXing → núcleo; `UnityWebRequest` implementa `IHttpTransport`; UI/âncora renderizam o `OverlayViewModel`. Nada de regra de negócio nela.
4. O cliente **não calcula status** (D-017): exibe o do servidor. Evita divergência com a SPEC-002.
5. JSON via `Newtonsoft.Json` (pacote oficial `com.unity.nuget.newtonsoft-json` no Unity; NuGet no `dotnet`).
6. Honestidade de verificação: a cola Unity é marcada **não compilada/não validada** até o checklist no aparelho; o núcleo é marcado **testado**.

## Consequências
- (+) A lógica de maior risco é testada de verdade, com fixtures geradas pela API real.
- (+) Trocar Unity por outro cliente (ex.: nativo) reaproveita as regras.
- (−) Duas camadas e um adaptador de transporte; mitigado por tamanho pequeno da cola.
- (−) A integração câmera→ZXing→âncora só é provada no aparelho.

## Alternativas rejeitadas
- Tudo em MonoBehaviours: não testável aqui; regras misturadas com ciclo de vida da engine.
- Augmented Images (ARCore) no lugar de QR: não lê QR (D-013).
- Cliente nativo Kotlin: foge do plano (Unity/AR Foundation).
