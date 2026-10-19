# SPEC-008 — Cliente AR Android (Unity)

Requisitos: REQ-AR-001 … REQ-AR-007 · Contrato consumido: [`openapi.yaml`](../contracts/openapi.yaml) (`/spatial/markers/{id}`, `/equipment/{id}/twin`, `/equipment/{id}/alerts`) · Decisões: D-012…D-017 · ADR: [ADR-0003](../../docs/adr/0003-ar-client-architecture.md).

## Problema e atores
O operador aponta o celular para o QR de um equipamento e vê, sobreposto, estado e leituras atualizados; a IA ainda **não** participa (Fase 3). Atores: operador (celular Android), API (Fase 1).

## Arquitetura do cliente (duas camadas)

| Camada | Conteúdo | Verificação |
|---|---|---|
| **Núcleo** `Spatial.Ar.Core` (C# puro, sem `UnityEngine`) | validação do QR, cliente da API, máquina de estados da sessão, modelo de apresentação (textos/cores) | **testado com `dotnet test`** (xUnit), compilado também como `netstandard2.1`/C# 9 (compatível com o Unity) |
| **Cola Unity** (`Spatial.Ar.Unity`) | câmera/ARCore, decodificação ZXing, `UnityWebRequest`, UI/âncora | **NÃO compilada nem executada nesta máquina** (sem Unity). Verificada só por revisão; vira "validada" apenas após o checklist no aparelho |

## Fluxo
1. **Scanning:** a cada ~5 quadros, a imagem de luminância é decodificada (ZXing). Texto fora de `^[A-Za-z0-9._:-]{1,128}$` é **descartado sem requisição** (REQ-AR-001).
2. **Resolving:** `GET /api/v1/spatial/markers/{id}` (no máx. 1/s). Respostas:
   - 200 → equipamento → **Live**;
   - 404 → "Marcador não reconhecido" (idêntico para desconhecido/alheio — REQ-AR-002) → volta a **Scanning** após 2 s;
   - 401 → "Sessão inválida" (descarta dados);
   - 429 → aguarda `Retry-After` e volta a Scanning;
   - rede/timeout/5xx/JSON inválido → "Sem conexão com o servidor" e tenta de novo.
3. **Live:** a cada 2 s busca `twin` + `alerts` do equipamento. Sucesso → vista **atual**. Falha → mantém a última vista **marcada desatualizada** com a idade (REQ-AR-004); após 3 falhas seguidas exibe "Sem conexão" mantendo a vista antiga.
4. **Troca de QR:** novo marker diferente (debounce 1 s) → descarta a vista anterior e resolve o novo (sem vazamento entre equipamentos — REQ-AR-005). O mesmo marker reescaneado é ignorado.

### Estado de apresentação (REQ-AR-003, D-017)
| Servidor (`twin.status`) | Texto | Cor | Observação |
|---|---|---|---|
| NORMAL | Normal | verde | — |
| WARNING | Atenção | âmbar | lista os alertas |
| CRITICAL | Crítico | vermelho | lista os alertas |
| OFFLINE | Offline — sem dados recentes | cinza | alerta `offline` |
| UNKNOWN | Desconhecido — dados insuficientes | roxo | **nunca** mostrado como normal |
| (cliente sem resposta recente) | + selo "DESATUALIZADO há N s" | atenuado | só o selo; o status exibido é o último do servidor |

O cliente **não** classifica valores contra limites: exibe `valid`, `warn`, `crit` e o `status` recebidos.

## Segurança (REQ-AR-005)
- Token demo e `http://` só em build de **Development** (`DEVELOPMENT_BUILD`/`UNITY_EDITOR`); build de release com token demo ou URL não-`https` falha na inicialização (`ClientConfig.Validate`, testado no núcleo).
- Logs nunca incluem token, URL completa com query, corpo de resposta ou o texto bruto do QR.
- Tamanho máximo de resposta aceito: 64 KiB; JSON inválido ⇒ falha tratada, não exceção.
- O token no aparelho é público (demo): o app só funciona contra o ambiente de desenvolvimento.

## Rede em desenvolvimento
`adb reverse tcp:8088 tcp:8088` e URL base `http://127.0.0.1:8088` no app (D-014). Nada é exposto na LAN.

## Geração dos QR de teste (REQ-AR-006)
`scripts/generate_qr.py` gera PNG (impressão) e PGM (teste) de: `QR-EQ-001/002/003` (positivos), `QR-EQ-B01` (de **outra** organização), `QR-NAO-EXISTE` (desconhecido) e conteúdos inválidos (ex.: JSON, URL, espaço) para os cenários negativos. O conteúdo do QR é só o marker.

## Critérios de aceitação
| # | Critério | Onde |
|---|---|---|
| A1 | Validação do QR: aceita o padrão; rejeita vazio, >128, espaços, controle, unicode, URL/JSON/SQL | `QrPayloadTests` |
| A2 | Cliente da API mapeia 200/401/404/429/5xx/timeout/rede/JSON inválido/corpo grande | `SpatialApiClientTests` |
| A3 | Máquina de estados: fluxo feliz, 404 genérico, 401, 429, rede, troca de QR, debounce, desatualizado | `MarkerSessionTests` |
| A4 | Modelo de apresentação: textos/cores/selo; UNKNOWN/OFFLINE nunca normais | `OverlayViewModelTests` |
| A5 | Driver completo com transporte falso e relógio falso | `SessionDriverTests` |
| A6 | Configuração: release recusa demo e http | `ClientConfigTests` |
| A7 | DTOs leem **JSON real gerado pela API** (fixtures regeneradas por teste Python) | `ApiFixtureTests` + `tests/contract/test_ar_fixtures.py` |
| A8 | QR gerados decodificam com ZXing.Net exatamente o marker | `QrRoundTripTests` |
| A9 | **Checklist no aparelho físico** | [`ar-device-checklist.md`](../../docs/runbooks/ar-device-checklist.md) — **PENDENTE (hardware)** |

## Riscos
- Âncora AR instável (iluminação, superfície sem textura): só mensurável no aparelho.
- O caminho `XRCpuImage → ZXing` é o mais sujeito a erro de integração; por isso é a primeira coisa do checklist.
- Cola Unity sem compilação nesta máquina: pode haver erros de compilação na primeira abertura (listados no README do projeto).
