# SPEC-011 — Visão computacional (PoC) e caminho seguro até IoT real

Requisitos: REQ-CV-001 … REQ-CV-004, REQ-IOT-001 … REQ-IOT-003 · Decisões: D-033…D-039 · ADR: [ADR-0006](../../docs/adr/0006-vision-poc-and-iot-gate.md) · Plano de hardware: [esp32-electrical-safety-plan.md](../../docs/hardware/esp32-electrical-safety-plan.md).

## Limites (leia primeiro)
- **Sem fotos reais, sem hardware, sem firmware.** A visão roda sobre **dataset sintético** (D-033); o IoT entrega **plano + emulador + broker endurecido** (D-038). Nada disto prova desempenho em campo.
- A visão é **assistiva** (D-037): não define status/alertas, não faz diagnóstico, não atua.

## Parte A — Visão (PoC offline em `ml/`)
### Dataset (REQ-CV-001)
Gerador determinístico `spatial_cv.scene`: 640×480; equipamento estilizado (compressor, bomba, motor) + adesivo **QR** com o marker do seed + **lâmpada de estado** (verde/âmbar/vermelha) + **distratores** (lâmpada azul/branca, placa vermelha, folhagem verde). Seis condições: `clean`, `blur`, `lowlight`, `tilt`, `occlusion`, `small`. O **estado da lâmpada** vem da regra real `evaluate_status` sobre leituras sorteadas do perfil do seed (`spatial_cv.truth`); o gerador falha se a regra discordar da intenção.
Classes YOLO (D-035): `compressor`, `pump`, `motor`, `lamp_normal`, `lamp_warning`, `lamp_critical`. O QR **não** é classe: é o concorrente na identificação.
Splits com faixas de semente **disjuntas** (treino 0…, validação 1 000 000…, teste 2 000 000…) e estratificação 3 equipamentos × 3 estados em cada condição. Oclusão que cobre a lâmpada (> 50 %) remove o rótulo dela.
Arquivos: `manifest.csv` (verdade por imagem), `data.yaml`, `images/`, `labels/` (formato YOLO). Nada disso é versionado: reproduz-se por `ml/gen_dataset.py`.

### Treino e avaliação (REQ-CV-002, D-034)
`ml/train.py`: YOLOv8n em CPU, semente fixa, AdamW, sem mosaic. **Dois detectores comparados:** (A) **do zero** (linha de base, 25 épocas) e (B) **ajuste fino dos pesos oficiais** `yolov8n.pt` (12 épocas), autorizado pelo usuário em D-040; origem pinada em `ml/spatial_cv/weights.py` (URL do release `v8.3.0` + SHA-256 + tamanho), baixada e verificada por `ml/fetch_weights.py`. `ml/evaluate.py`: no split de **teste**, mAP/precisão/revocação (geral, por classe e por condição) e a comparação abaixo; relatórios em `docs/evidence/phase-5/cv-report-scratch.md` e `cv-report-pretrained.md`. O YOLO vive em ambiente isolado `ml/.venv-ml` (AGPL-3.0, pesos incluídos), fora das imagens Docker, da API e da CI (REQ-CV-004). O `.pt` é um *pickle* do PyTorch (executa código ao carregar): só se carrega o arquivo cujo SHA-256 confere com o pinado; o hash foi registrado do que foi baixado e **não** foi confirmado contra uma publicação oficial.

### Comparação mensurável (REQ-CV-003, D-036)
Mesmas imagens de teste, três pares:
1. **Identificação:** QR (`cv2.QRCodeDetector`, original + ampliada 2×) × YOLO (classe de equipamento de maior confiança). Verdade: marker/tipo do seed. O YOLO identifica o **tipo** (equivale ao id só porque o seed tem um equipamento por tipo). Conta-se separadamente o QR que lê **texto errado** (erro silencioso).
2. **Estado:** YOLO (lâmpada de maior confiança) × **baseline HSV** (maior bolha circular de cor de lâmpada) × estado da regra do simulador.
3. **Complementaridade:** "QR **ou** YOLO" e "YOLO **ou** HSV" (limite superior de uma fusão assistiva).
Estatística: taxas com **IC de Wilson 95 %**; pares com **McNemar exato** sobre os discordantes. O relatório só afirma superioridade com p < 0,05; senão diz *sem diferença detectável*. Matrizes de confusão do estado e latência média por método em CPU.

### Assistivo e isolado (REQ-CV-004, D-037)
Nenhum módulo de `services/` ou `packages/` importa `spatial_cv`, `ultralytics`, `torch` ou `cv2`; os `requirements`/Dockerfiles dos serviços não os incluem; `ml/` não importa broker, banco ou API (teste de isolamento por AST).

## Parte B — IoT (REQ-IOT-001…003, D-038/D-039)
- **Plano e portão** (`docs/hardware/esp32-electrical-safety-plan.md`): sem hardware/firmware até G1–G7 e aprovação explícita.
- **Emulador de dispositivo** (`simulator.device_emulator`): monta `telemetry-event.v1`, valida com o parser estrito do worker, publica QoS 1 no **próprio** tópico, credenciais opcionais. Testado contra a pilha real: valores válidos chegam à API; payload inválido ou tópico alheio é rejeitado e não aparece.
- **Broker endurecido opt-in** (`mosquitto.secure.conf`, `secure.acl`, `compose.secure.yaml`, `scripts/gen_broker_users.py`): `allow_anonymous false`; hash `$7$` PBKDF2-SHA512 gerado em Python e **verificado contra Mosquitto real**; ACL: `worker` só lê, `simulator` escreve, `health` só lê `$SYS`, dispositivos escrevem apenas em `.../{usuário}/telemetry`. Achado dos testes: o Mosquitto pode responder SUBACK "concedido" mesmo sem permissão de leitura; a ACL impede a **entrega** (o teste verifica que o dispositivo nunca recebe telemetria). Worker e simulador aceitam `MQTT_USERNAME`/`MQTT_PASSWORD` (anônimo por padrão).
- **Sem TLS** (pendência do portão G3).

## Segurança e limites
- Credenciais geradas aleatoriamente, em arquivos ignorados pelo Git; nunca impressas.
- O padrão de desenvolvimento continua anônimo (S-02); o endurecido é opt-in.
- Não verificado: hardware, firmware, TLS, exatidão de sensores, qualquer foto real, desempenho da visão em campo.
