# Checklist de validação do cliente AR em aparelho físico

> **Estado: NÃO EXECUTADO.** Este checklist é o critério de pronto da Fase 2 (REQ-AR-007). Enquanto não houver
> linhas preenchidas com evidência (vídeo/captura/medida) em aparelho real, a AR **não** pode ser declarada validada.

## 0. Preparação (uma vez)
- [ ] Android com ARCore ([lista oficial](https://developers.google.com/ar/devices)), depuração USB ativa; modelo/Android/ARCore anotados abaixo.
- [ ] Unity 6.3 LTS com módulo *Android Build Support* (SDK/NDK/JDK incluídos). Abrir `clients/ar-unity/`.
- [ ] Resolver erros de compilação da cola Unity (esperados na 1ª abertura; registrar quais).
- [ ] `docker compose up --build --wait` no PC; `adb reverse tcp:8088 tcp:8088`; `adb devices` mostra o aparelho.
- [ ] Imprimir os QR de `docs/evidence/phase-2/qr/` (gerados por `scripts/generate_qr.py`) em ~8 cm de lado.
- [ ] Build **Development** instalada; URL `http://127.0.0.1:8088`, token `demo-operator-a`.

**Aparelho:** modelo ______ · Android ____ · versão do ARCore ____ · Unity ____ · data ____

## 1. Cenários funcionais
| # | Cenário | Esperado | Resultado | Evidência |
|---|---|---|---|---|
| F1 | Escanear `QR-EQ-001` | overlay do EQ-001 com status/leituras em ≤ 3 s | | |
| F2 | Escanear `QR-EQ-002` e `QR-EQ-003` | cada um mostra o seu equipamento | | |
| F3 | Escanear `QR-EQ-B01` (outra organização) | "Marcador não reconhecido"; **nenhum** dado | | |
| F4 | Escanear `QR-NAO-EXISTE` | mesma mensagem de F3 (indistinguível) | | |
| F5 | Escanear QR com conteúdo inválido (URL/JSON/espaço) | ignorado, **sem** requisição (ver log do servidor) | | |
| F6 | Trocar de QR com o overlay ativo | dados do anterior somem; novo equipamento aparece | | |
| F7 | EQ-002 durante a rampa do simulador | transição NORMAL → WARNING → CRITICAL em ≤ ~4 s do evento; alertas listados | | |
| F8 | EQ-003 durante o *dropout* | vira **OFFLINE** (nunca "normal"); alerta `offline` | | |

## 2. Degradação (REQ-AR-004)
| # | Cenário | Esperado | Resultado | Evidência |
|---|---|---|---|---|
| D1 | `docker compose stop api` com overlay ativo | última vista mantida, selo **DESATUALIZADO** com idade crescente; depois "Sem conexão" | | |
| D2 | `docker compose start api` | volta a atualizar sozinho | | |
| D3 | Modo avião / `adb reverse --remove-all` | idem D1, sem crash | | |
| D4 | Token inválido | "Sessão inválida"; dados removidos | | |
| D5 | Escanear >30 QR/min | 429 tratado, aguarda `Retry-After` | | |

## 3. Câmera e ancoragem
| # | Cenário | Esperado | Resultado | Evidência |
|---|---|---|---|---|
| A1 | Iluminação boa, 30–60 cm | leitura em ≤ 2 s | | |
| A2 | Pouca luz / reflexo / QR inclinado 45° | registrar taxa de sucesso (10 tentativas) | | |
| A3 | Mover o aparelho ao redor do QR | overlay permanece ancorado; registrar deriva visível | | |
| A4 | Perder e reencontrar o QR | overlay não pula para outro equipamento | | |

## 4. Medições (por aparelho — REQ-AR-007)
| Métrica | Método | Valor |
|---|---|---|
| Latência QR→overlay (p50/p95, n ≥ 20) | cronometrar do QR enquadrado até o overlay (vídeo quadro a quadro) | |
| FPS médio com overlay | Unity Profiler / `adb shell dumpsys gfxinfo` | |
| Estabilidade (sessão de 10 min, crashes/travadas) | contagem | |
| Aquecimento / bateria (10 min) | % de bateria | |

## 5. Segurança
- [ ] Build de **release** com token demo ou `http://` **recusa iniciar** (mensagem clara).
- [ ] `adb logcat` durante F1–F8 não contém token, URL com credenciais, corpo de resposta nem texto bruto do QR.

## Assinatura da execução
Responsável: ______ · Data: ______ · Veredito: ☐ aprovado ☐ aprovado com ressalvas ☐ reprovado
