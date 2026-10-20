# Visão computacional (Fase 5) — PoC com dataset SINTÉTICO — gerado por `ml/evaluate.py`

> **Escopo e limites.** Dataset **sintético** (equipamentos estilizados + QR + lâmpada), gerado por script determinístico; **não há foto real**. Os números mostram o pipeline e a comparação metodológica, **não** o desempenho em campo. Detector: YOLOv8n com ajuste fino a partir dos pesos oficiais yolov8n.pt (release ultralytics/assets v8.3.0; SHA-256 f59b3d83…3b36; autorizado em D-040). A visão é **assistiva**: não define status nem alertas, e não faz diagnóstico. O YOLO identifica o **tipo** do equipamento; isso equivale ao id só porque o seed tem um equipamento por tipo. Ajuste fino: 12 épocas, 480 imagens (metade do split de treino), imgsz 320, AdamW lr0=0,002, sem mosaic, CPU, 73 min.

Imagens de teste: **360** (60 por condição x 6 condições), limiar de decisão 0.25. Latência média por imagem em CPU: QR 191.2 ms · YOLO 184.8 ms · baseline HSV 43.0 ms.

## Detecção (mAP, split de teste; `model.val`, conf 0,001)

| Condição | imagens | precisão | revocação | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| TOTAL | 360 | 0.966 | 0.963 | 0.989 | 0.798 |
| clean | 60 | 0.996 | 1.000 | 0.995 | 0.978 |
| blur | 60 | 0.995 | 1.000 | 0.995 | 0.965 |
| lowlight | 60 | 0.995 | 1.000 | 0.995 | 0.967 |
| tilt | 60 | 0.981 | 0.945 | 0.983 | 0.461 |
| occlusion | 60 | 0.973 | 1.000 | 0.995 | 0.879 |
| small | 60 | 0.916 | 0.845 | 0.927 | 0.629 |

Por classe (TOTAL):

| Classe | precisão | revocação | AP50 | AP50-95 |
|---|---|---|---|---|
| compressor | 0.957 | 1.000 | 0.994 | 0.835 |
| pump | 0.968 | 0.996 | 0.995 | 0.856 |
| motor | 0.959 | 0.975 | 0.990 | 0.858 |
| lamp_normal | 0.940 | 0.940 | 0.975 | 0.743 |
| lamp_warning | 0.991 | 0.908 | 0.990 | 0.774 |
| lamp_critical | 0.980 | 0.960 | 0.993 | 0.721 |

## Comparação mensurável (mesmas imagens de teste)

### Identificação do equipamento: QR vs YOLO (verdade = marker/tipo do seed)

| Condição | n | QR leu o marker certo | YOLO acertou o tipo | QR **ou** YOLO | QR leu errado (silencioso) | Veredito pareado |
|---|---|---|---|---|---|---|
| clean | 60 | 93% (56/60; IC95 84% a 97%) | 100% (60/60; IC95 94% a 100%) | 100% (60/60; IC95 94% a 100%) | 0/60 | sem diferença detectável entre QR e YOLO (discordantes 0/4; p=0.125) |
| blur | 60 | 0% (0/60; IC95 0% a 6%) | 100% (60/60; IC95 94% a 100%) | 100% (60/60; IC95 94% a 100%) | 0/60 | YOLO é melhor (discordantes 0/60; McNemar exato p=1.73e-18) |
| lowlight | 60 | 63% (38/60; IC95 51% a 74%) | 100% (60/60; IC95 94% a 100%) | 100% (60/60; IC95 94% a 100%) | 0/60 | YOLO é melhor (discordantes 0/22; McNemar exato p=4.77e-07) |
| tilt | 60 | 87% (52/60; IC95 76% a 93%) | 97% (58/60; IC95 89% a 99%) | 97% (58/60; IC95 89% a 99%) | 0/60 | YOLO é melhor (discordantes 0/6; McNemar exato p=0.0312) |
| occlusion | 60 | 25% (15/60; IC95 16% a 37%) | 98% (59/60; IC95 91% a 100%) | 98% (59/60; IC95 91% a 100%) | 0/60 | YOLO é melhor (discordantes 0/44; McNemar exato p=1.14e-13) |
| small | 60 | 32% (19/60; IC95 21% a 44%) | 97% (58/60; IC95 89% a 99%) | 97% (58/60; IC95 89% a 99%) | 0/60 | YOLO é melhor (discordantes 0/39; McNemar exato p=3.64e-12) |
| TOTAL | 360 | 50% (180/360; IC95 45% a 55%) | 99% (355/360; IC95 97% a 99%) | 99% (355/360; IC95 97% a 99%) | 0/360 | YOLO é melhor (discordantes 0/175; McNemar exato p=4.18e-53) |

### Estado indicado pela lâmpada: YOLO vs baseline de cor vs simulador (verdade = regra real `evaluate_status`)

| Condição | n | lâmpada visível | YOLO acertou | baseline HSV acertou | YOLO **ou** HSV | Veredito pareado |
|---|---|---|---|---|---|---|
| clean | 60 | 60/60 | 100% (60/60; IC95 94% a 100%) | 85% (51/60; IC95 74% a 92%) | 100% (60/60; IC95 94% a 100%) | YOLO é melhor (discordantes 9/0; McNemar exato p=0.00391) |
| blur | 60 | 60/60 | 100% (60/60; IC95 94% a 100%) | 58% (35/60; IC95 46% a 70%) | 100% (60/60; IC95 94% a 100%) | YOLO é melhor (discordantes 25/0; McNemar exato p=5.96e-08) |
| lowlight | 60 | 60/60 | 100% (60/60; IC95 94% a 100%) | 78% (47/60; IC95 66% a 87%) | 100% (60/60; IC95 94% a 100%) | YOLO é melhor (discordantes 13/0; McNemar exato p=0.000244) |
| tilt | 60 | 60/60 | 100% (60/60; IC95 94% a 100%) | 85% (51/60; IC95 74% a 92%) | 100% (60/60; IC95 94% a 100%) | YOLO é melhor (discordantes 9/0; McNemar exato p=0.00391) |
| occlusion | 60 | 35/60 | 63% (38/60; IC95 51% a 74%) | 53% (32/60; IC95 41% a 65%) | 70% (42/60; IC95 57% a 80%) | sem diferença detectável entre YOLO e baseline HSV (discordantes 10/4; p=0.180) |
| small | 60 | 60/60 | 52% (31/60; IC95 39% a 64%) | 72% (43/60; IC95 59% a 81%) | 87% (52/60; IC95 76% a 93%) | baseline HSV é melhor (discordantes 9/21; McNemar exato p=0.0428) |
| TOTAL | 360 | 335/360 | 86% (309/360; IC95 82% a 89%) | 72% (259/360; IC95 67% a 76%) | 93% (334/360; IC95 90% a 95%) | YOLO é melhor (discordantes 75/25; McNemar exato p=5.64e-07) |

### Matriz de confusão do estado — YOLO (linhas = verdade da regra; colunas = previsto)

| verdade \ previsto | lamp_normal | lamp_warning | lamp_critical | (nada) |
|---|---|---|---|---|
| lamp_normal | 109 | 0 | 0 | 17 |
| lamp_warning | 2 | 102 | 0 | 22 |
| lamp_critical | 0 | 0 | 98 | 10 |

### Matriz de confusão do estado — baseline HSV (linhas = verdade da regra; colunas = previsto)

| verdade \ previsto | lamp_normal | lamp_warning | lamp_critical | (nada) |
|---|---|---|---|---|
| lamp_normal | 96 | 2 | 15 | 13 |
| lamp_warning | 17 | 91 | 8 | 10 |
| lamp_critical | 14 | 10 | 72 | 12 |

## Leitura honesta

- Só há afirmação de superioridade quando o teste de McNemar exato dá p < 0,05; caso contrário o relatório diz *sem diferença detectável*.
- O baseline de cor é de propósito simples; os distratores (lâmpada azul/branca, placa vermelha, folhagem verde) foram escolhidos por mim e influenciam o resultado.
- Oclusão pode esconder a lâmpada: nesses casos o estado é impossível para qualquer método visual (a verdade continua sendo a da regra).
- Condições avaliadas: clean, blur, lowlight, tilt, occlusion, small.
