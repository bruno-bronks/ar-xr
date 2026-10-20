# Evidência da Fase 5 — Visão computacional (PoC sintético) e caminho seguro até IoT (2026-10-20)

Tudo abaixo foi **executado** nesta máquina (Windows 11, CPU de 8 threads, **sem GPU**, Python 3.13, torch 2.14.1 CPU, ultralytics 8.4.183, Docker 29.8.2). A CI do GitHub **não** foi executada para esta branch.

> **Sem fotos reais, sem hardware, sem firmware.** A visão roda sobre um dataset **sintético** gerado por script; o IoT entrega plano, emulador e broker endurecido. Nada disto prova desempenho em campo.

## 1. Verificações automáticas

| Verificação | Resultado |
|---|---|
| `scripts/check.ps1` (ruff, ruff format, mypy strict, pytest, pip-audit ×3) | passou: **855 testes passaram, 143 pulados** (pulam sem PostgreSQL/pilha); mypy strict em 137 arquivos; `pip-audit` sem achados (sem dependências novas nos serviços) |
| Gerador do dataset (`tests/unit/ml`) | determinístico (mesmos bytes), rótulos válidos nas 6 condições, splits disjuntos, estratificação, estado vindo da regra real |
| Estatística e baselines | IC de Wilson e McNemar exato (valores conhecidos), QR/cor testados; agregação da comparação testada |
| Isolamento (REQ-CV-004) | nenhum código de `services/` ou `packages/` importa `spatial_cv`/`ultralytics`/`torch`/`cv2`; `requirements` e Dockerfiles sem ML; `ml/` não importa broker/banco/API |
| Procedência dos pesos (D-040) | `ml/spatial_cv/weights.py`: URL pinada + SHA-256 + tamanho; o arquivo local confere com o pin |
| Portão de hardware (REQ-IOT-001) | `test_hardware_gate.py`: G1–G7 abertos ⇒ nenhum firmware/placa no repositório; sem tópico/canal de comando |
| Broker endurecido (REQ-IOT-003) | **14 casos contra Mosquitto REAL** em contêiner próprio: anônimo/senha errada/usuário desconhecido recusados; dispositivo só publica no próprio tópico (tópico alheio e `/command` ⇒ `0x87`); **dispositivo nunca recebe telemetria**; worker só lê; simulador escreve; `health` só lê `$SYS` |
| Pilha completa com o override endurecido | subiu saudável; simulador e worker autenticados; conexão anônima do host ⇒ CONNACK 135; emulador com a credencial do EQ-002 persistiu 63,21 °C; publicação forjada do EQ-002 no tópico do EQ-001 (99 999 °C) **não foi persistida** (0 linhas no banco) |
| Emulador contra a pilha real (REQ-IOT-002) | válido ⇒ persistido uma vez (`source = esp32-emulator`); duplicata ⇒ uma linha; payload inválido (sensor desconhecido, campo extra, equipamento ≠ tópico, não-JSON) ⇒ 4 rejeições no worker e nada persistido |
| Z (`verify-z.ps1`) | as 5 especificações existentes continuam passando no CZT (nenhuma spec Z nova nesta fase; nenhum teorema provado) |
| Mutação (manual) | **15 alterações deliberadas** (Wilson, McNemar, veredito, agregação, hash dos pesos, sementes dos splits, credenciais MQTT, hash `$7$`, validação do emulador, anônimo/ACL do broker): **15 detectadas** |

## 2. Dataset e treino (sintético, CPU)
- **1500 imagens** 640×480: treino 960 · validação 180 · teste 360 (60 por condição: `clean`, `blur`, `lowlight`, `tilt`, `occlusion`, `small`). Equipamento estilizado (compressor/bomba/motor) + adesivo QR + lâmpada de estado + distratores. **Estado verdadeiro = regra real `evaluate_status`.** Amostras: [samples/contact-sheet-conditions.jpg](samples/contact-sheet-conditions.jpg).
- **Detector A — do zero** (linha de base): YOLOv8n, 25 épocas, 480 imagens de treino (metade), 320 px, AdamW lr0 = 0,002, sem mosaic, 78 min. **Validação final: mAP50 0,893 · mAP50-95 0,622.**
- **Detector B — ajuste fino dos pesos oficiais** (autorizado, D-040): `yolov8n.pt` do release `ultralytics/assets v8.3.0` (6 549 796 bytes, **SHA-256 `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`**), mesmos hiperparâmetros, 12 épocas, 73 min. **Validação final: mAP50 0,991 · mAP50-95 0,790.** Convergiu em 2 épocas ao nível (mAP50 ≈ 0,90) que o detector A só alcançou na época ~24.
- Por que 320 px e metade do treino: uma época a 480 px com 960 imagens levou ~14 min nesta CPU (um treino de 40 épocas levaria > 9 h). O orçamento é pequeno; resultados de uma única semente (sem variância entre sementes).

## 3. Resultados no split de TESTE (360 imagens; relatórios completos: [A](cv-report-scratch.md) · [B](cv-report-pretrained.md))

| Medida (TOTAL) | A: do zero | B: pesos oficiais |
|---|---|---|
| mAP50 / mAP50-95 | 0,898 / 0,616 | **0,989 / 0,798** |
| Identificação do equipamento: **YOLO** acertou o tipo | 86 % (311/360) | **99 % (355/360)** |
| Identificação: **QR** leu o marker certo | 50 % (180/360; IC95 45–55 %) | 50 % (mesmas imagens) |
| QR **ou** YOLO | 91 % | 99 % (o QR **não acrescentou nada**: 0 casos só do QR) |
| QR que leu texto **errado** (erro silencioso) | 0/360 | 0/360 |
| Estado da lâmpada: **YOLO** × regra do simulador | 79 % (284/360) | **86 % (309/360)** |
| Estado da lâmpada: baseline de cor (HSV) | 72 % (259/360) | 72 % |
| YOLO **ou** baseline | 91 % | 93 % |

Identificação por condição, QR × YOLO-B (IC95 de Wilson; McNemar exato): `clean` 93 % × 100 % (**sem diferença detectável**, p = 0,125) · `blur` 0 % × 100 % · `lowlight` 63 % × 100 % · `tilt` 87 % × 97 % (p = 0,031) · `occlusion` 25 % × 98 % · `small` 32 % × 97 %.
Estado por condição, YOLO-B × baseline: `clean` 100 % × 85 % · `blur` 100 % × 58 % · `lowlight` 100 % × 78 % · `tilt` 100 % × 85 % · `occlusion` 63 % × 53 % (**sem diferença detectável**; lâmpada visível em só 35/60) · **`small` 52 % × 72 % — o baseline de cor é melhor** (p = 0,043; no detector A: 22 % × 72 %).

## 4. Como ler (limites que mudam a conclusão)
- **Dentro da distribuição.** Treino e teste vêm do mesmo gerador e do mesmo estilo visual; o YOLO aprendeu **esse** estilo. Em fotos reais o resultado pode ser muito pior. **Não** há afirmação de desempenho em campo.
- **Comparação injusta ao QR por construção do dataset.** O QR é pequeno e desenhado em baixa resolução; o decodificador é o do OpenCV (o app usa ZXing.Net). O YOLO identifica o **tipo**, não o id (só equivale ao id porque o seed tem um equipamento por tipo); o QR identifica o marker exato e nunca leu errado. Na prática o QR continua sendo a identificação confiável e o YOLO um complemento **assistivo**.
- **Baseline e distratores são escolhas minhas** e influenciam o resultado; o baseline de cor vence do YOLO na condição `small`.
- **Latência:** a máquina tem IDE e navegadores concorrendo; as medições variaram (YOLO de 71 a 257 ms para a mesma arquitetura). Só vale a ordem de grandeza (dezenas a centenas de ms em CPU); **nada** a concluir sobre velocidade.
- **Assistivo:** a visão não altera status/alertas (a regra de telemetria continua a autoridade) e não faz diagnóstico.
- **Licença/procedência:** `ultralytics` e os pesos são AGPL-3.0; o `.pt` é um *pickle* (executa código ao carregar) e o hash foi pinado do arquivo baixado, **sem confirmação contra publicação oficial**.

## 5. Gates finais desta execução
- `scripts/check.ps1`: passou (ver §1).
- Suíte completa com PostgreSQL real (sem integração/E2E): **923 passaram**.
- Pilha Docker reconstruída: **54 de integração e desempenho passaram** (inclui 14 do broker endurecido contra Mosquitto real e 4 do emulador) e **21 E2E** no navegador.
- Os testes de `tests/unit/ml` rodam em ~30 s com a CPU livre e não precisam de torch (só OpenCV, numpy e segno, já dependências de desenvolvimento).

## 6. Não verificado
- Qualquer foto real; generalização; desempenho em campo; variância entre sementes; ZXing.Net no lugar do OpenCV.
- Hardware, firmware, EMC, exatidão de sensores, **TLS** (senha em claro na rede), rate limit no broker.
- O plano elétrico/segurança do ESP32 **não está aprovado** (G1–G7 abertos) e foi escrito por um agente de software.
- CI do GitHub para esta branch; implantação da Fase 5 no VPS (nada de runtime mudou além das credenciais MQTT opcionais no worker/simulador).
