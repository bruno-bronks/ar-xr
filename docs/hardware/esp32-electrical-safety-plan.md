# Plano elétrico e de segurança — sensores ESP32 (PORTÃO DE APROVAÇÃO)

**Estado: NÃO APROVADO. Nenhum hardware, firmware, fiação ou compra foi feito.** Requisito: REQ-IOT-001 · Spec: [SPEC-011](../../specs/functional/SPEC-011-vision-and-iot.md) · Decisões: D-038, D-039.

> **Aviso.** Este plano é um **roteiro de engenharia escrito por um agente de software**, não por profissional habilitado em eletricidade/instrumentação. Valores de componentes, normas e limites abaixo são **candidatos a confirmar**; nada foi verificado em bancada nem contra datasheets. **Nenhum item do portão pode ser dado como cumprido sem revisão de pessoa responsável.**

## 1. Objetivo e limite de atuação
Medir **temperatura** e **vibração** de um equipamento e publicar no broker (`spatial/v1/equipment/{id}/telemetry`, esquema `telemetry-event.v1`). O dispositivo é **somente sensor**: **nenhuma saída de atuação** (sem relé, contator, válvula, PWM de potência) e **nenhum tópico de comando**. Decisão e ação física continuam humanas (plano §6/§8). O estado do equipamento segue sendo decidido pelas regras da plataforma (SPEC-002).

## 2. Arquitetura proposta
`sensor(es) → ESP32 → Wi-Fi → broker MQTT (TLS + autenticação + ACL) → worker → PostgreSQL → API`
- Um usuário MQTT por dispositivo (usuário = id do equipamento); só publica no próprio tópico (implementado e testado — ver §8).
- Dispositivo mudo ⇒ a plataforma mostra `OFFLINE`; sensor com defeito ⇒ `quality=BAD` (a regra ignora a leitura). Nunca "normal por ausência".

## 3. Plano elétrico (a ser preenchido e revisado por responsável habilitado)
| Tema | Requisito de projeto | Candidato / a confirmar |
|---|---|---|
| Alimentação | Fonte certificada, isolada, com proteção contra sobrecorrente; sem bateria no MVP | 5 V DC regulados; fusível/PTC; **valores a dimensionar** |
| Níveis lógicos | GPIO do ESP32 é 3,3 V e **não tolera 5 V** | level shifter quando o sensor for 5 V |
| Temperatura | Faixa e exatidão compatíveis com os limiares do perfil do equipamento; sensor **fora** de circuitos de potência | 1-Wire (ex.: DS18B20) até a faixa suportada; termopar + conversor dedicado acima dela — **confirmar datasheets** |
| Vibração | Acelerômetro MEMS fixado na carcaça; cálculo de mm/s RMS exige filtragem/integração e **validação metrológica** | MEMS I²C/SPI (ex.: família ADXL/LIS3DH) — **não selecionado**; calibração com referência |
| Isolamento | Nenhuma ligação ao circuito de potência/rede do equipamento; sensores sem contato elétrico com a potência | isolação galvânica onde houver dúvida |
| Cabeamento | Blindado, aterrado em um ponto, longe de inversores/cabos de potência (EMI) | **a definir em campo** |
| Proteção | ESD/surto na entrada de alimentação e nas linhas de sensor; caixa com grau de proteção adequado ao ambiente | IP e material **a definir** |
| Térmica/ambiente | Faixa de temperatura de operação do módulo e da caixa; ventilação; sem exposição a líquidos | **a confirmar** |

## 4. Segurança funcional
- Sem atuação (§1). Falha segura = silêncio: watchdog reinicia o dispositivo; perda de energia/rede ⇒ `OFFLINE` na plataforma.
- Leitura inválida/fora de faixa/sensor desconectado ⇒ publicar `quality=BAD` (ou não publicar), **nunca** um valor plausível inventado.
- Taxa de publicação limitada (evita inundar o broker); `event_id` único por leitura (idempotência/replay).
- Relógio: sincronizar por NTP; o worker rejeita leituras com `observed_at` mais de 5 min no futuro.

## 5. Segurança de rede e informação
| Controle | Estado |
|---|---|
| Autenticação por dispositivo + ACL por tópico | **Implementado e testado** com Mosquitto real (opt-in): `compose.secure.yaml` |
| **TLS (8883) com CA própria e verificação do certificado no dispositivo** | **NÃO implementado — obrigatório antes de qualquer dispositivo real** (hoje a senha trafegaria em claro) |
| Segredos no dispositivo | Não versionar; usar armazenamento protegido do ESP32 (flash encryption / NVS criptografada) — **recursos a validar** |
| Secure boot e firmware assinado; OTA assinada | **A projetar/validar** |
| Depuração (JTAG/UART) | Desabilitar em produção — **a validar** |
| Rede | VLAN/segmento isolado para dispositivos; sem exposição à internet |
| Rotação/revogação | Procedimento para trocar a senha de um dispositivo e remover usuário do `passwd` — **a documentar** |
| Rate limit/cotas no broker | **Não implementado** |

## 6. Ameaças do dispositivo (resumo STRIDE)
| Ameaça | Mitigação atual / pendente |
|---|---|
| Spoofing: dispositivo falso publica em nome de outro | ACL `%u` (testado); credenciais únicas; **TLS pendente** |
| Tampering: leitura adulterada em trânsito | **TLS pendente**; esquema estrito no worker (testado) |
| Replay | `event_id` + idempotência `(source, event_id)` (testado); janela de tempo parcial |
| Information disclosure: senha do broker capturada | **TLS pendente**; segredo fora do código |
| DoS: dispositivo inunda o broker | **rate limit pendente** |
| Elevation: dispositivo comanda outro/atua | Sem tópicos de comando e sem saídas de atuação (testado: publicar em `/command` é negado) |

## 7. Portão de aprovação (todos obrigatórios antes de comprar/montar/energizar)
- [ ] **G1** Revisão elétrica e de instrumentação por profissional habilitado (preencher §3 com valores verificados).
- [ ] **G2** Análise de risco do local de instalação e normas aplicáveis (confirmar com o responsável da planta quais se aplicam).
- [ ] **G3** TLS no broker (`8883`), certificados e verificação no dispositivo, com teste automatizado.
- [ ] **G4** Firmware **escrito, revisado, compilado e testado em bancada** contra o broker de teste (usando o emulador como referência de comportamento).
- [ ] **G5** Ambiente de teste isolado (rede/segmento separado; sem equipamento em produção).
- [ ] **G6** Plano de desligamento/rollback e de rotação de credenciais.
- [ ] **G7** **Aprovação explícita do usuário**, registrada em ADR.

## 8. O que já existe em software (e o que isso NÃO prova)
- Emulador de dispositivo (`simulator.device_emulator`): publica eventos válidos no próprio tópico, validando com o parser do worker; testado contra a pilha real.
- Broker endurecido opt-in: `allow_anonymous false`, senha por usuário (hash PBKDF2-SHA512 compatível com o Mosquitto, verificado contra o broker real), ACL por dispositivo; testado com 14 casos contra Mosquitto real (anônimo/senha errada recusados; publicar em tópico alheio ou de comando negado; dispositivo nunca recebe telemetria).
- **Não prova:** nada sobre hardware, EMC, exatidão dos sensores, firmware, TLS, nem comportamento em campo.

## 9. Aprovação
| Item | Responsável | Data | Assinatura |
|---|---|---|---|
| Revisão elétrica (G1) | _pendente_ | | |
| Análise de risco (G2) | _pendente_ | | |
| Aprovação do usuário (G7) | _pendente_ | | |
