# Visão computacional (Fase 5) — PoC com dataset SINTÉTICO — gerado por `ml/evaluate.py`

> **Escopo e limites.** Dataset **sintético** (equipamentos estilizados + QR + lâmpada), gerado por script determinístico; **não há foto real**. Os números mostram o pipeline e a comparação metodológica, **não** o desempenho em campo. Detector: YOLOv8n treinado do zero em CPU (sem pesos pré-treinados). A visão é **assistiva**: não define status nem alertas, e não faz diagnóstico. O YOLO identifica o **tipo** do equipamento; isso equivale ao id só porque o seed tem um equipamento por tipo. Treino: 25 épocas, 480 imagens (metade do split de treino), imgsz 320, AdamW lr0=0,002, sem mosaic, CPU, 78 min.

Imagens de teste: **360** (60 por condição x 6 condições), limiar de decisão 0.25. Latência média por imagem em CPU: QR 129.7 ms · YOLO 71.3 ms · baseline HSV 27.7 ms.

## Detecção (mAP, split de teste; `model.val`, conf 0,001)

| Condição | imagens | precisão | revocação | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| TOTAL | 360 | 0.955 | 0.798 | 0.898 | 0.616 |
| clean | 60 | 0.977 | 0.991 | 0.993 | 0.832 |
| blur | 60 | 0.987 | 0.974 | 0.991 | 0.847 |
| lowlight | 60 | 0.980 | 0.997 | 0.993 | 0.855 |
| tilt | 60 | 0.935 | 0.892 | 0.937 | 0.436 |
| occlusion | 60 | 0.762 | 0.684 | 0.815 | 0.421 |
| small | 60 | 0.570 | 0.497 | 0.544 | 0.352 |

Por classe (TOTAL):

| Classe | precisão | revocação | AP50 | AP50-95 |
|---|---|---|---|---|
| compressor | 0.975 | 0.875 | 0.967 | 0.668 |
| pump | 0.988 | 0.697 | 0.949 | 0.677 |
| motor | 0.952 | 0.826 | 0.937 | 0.675 |
| lamp_normal | 0.941 | 0.812 | 0.844 | 0.539 |
| lamp_warning | 0.968 | 0.786 | 0.856 | 0.578 |
| lamp_critical | 0.904 | 0.792 | 0.834 | 0.560 |

## Comparação mensurável (mesmas imagens de teste)

### Identificação do equipamento: QR vs YOLO (verdade = marker/tipo do seed)

| Condição | n | QR leu o marker certo | YOLO acertou o tipo | QR **ou** YOLO | QR leu errado (silencioso) | Veredito pareado |
|---|---|---|---|---|---|---|
| clean | 60 | 93% (56/60; IC95 84% a 97%) | 100% (60/60; IC95 94% a 100%) | 100% (60/60; IC95 94% a 100%) | 0/60 | sem diferença detectável entre QR e YOLO (discordantes 0/4; p=0.125) |
| blur | 60 | 0% (0/60; IC95 0% a 6%) | 98% (59/60; IC95 91% a 100%) | 98% (59/60; IC95 91% a 100%) | 0/60 | YOLO é melhor (discordantes 0/59; McNemar exato p=3.47e-18) |
| lowlight | 60 | 63% (38/60; IC95 51% a 74%) | 100% (60/60; IC95 94% a 100%) | 100% (60/60; IC95 94% a 100%) | 0/60 | YOLO é melhor (discordantes 0/22; McNemar exato p=4.77e-07) |
| tilt | 60 | 87% (52/60; IC95 76% a 93%) | 87% (52/60; IC95 76% a 93%) | 97% (58/60; IC95 89% a 99%) | 0/60 | sem diferença detectável entre QR e YOLO (discordantes 6/6; p=1.000) |
| occlusion | 60 | 25% (15/60; IC95 16% a 37%) | 47% (28/60; IC95 35% a 59%) | 60% (36/60; IC95 47% a 71%) | 0/60 | YOLO é melhor (discordantes 8/21; McNemar exato p=0.0241) |
| small | 60 | 32% (19/60; IC95 21% a 44%) | 87% (52/60; IC95 76% a 93%) | 88% (53/60; IC95 78% a 94%) | 0/60 | YOLO é melhor (discordantes 1/34; McNemar exato p=2.1e-09) |
| TOTAL | 360 | 50% (180/360; IC95 45% a 55%) | 86% (311/360; IC95 82% a 90%) | 91% (326/360; IC95 87% a 93%) | 0/360 | YOLO é melhor (discordantes 15/146; McNemar exato p=3.76e-28) |

### Estado indicado pela lâmpada: YOLO vs baseline de cor vs simulador (verdade = regra real `evaluate_status`)

| Condição | n | lâmpada visível | YOLO acertou | baseline HSV acertou | YOLO **ou** HSV | Veredito pareado |
|---|---|---|---|---|---|---|
| clean | 60 | 60/60 | 100% (60/60; IC95 94% a 100%) | 85% (51/60; IC95 74% a 92%) | 100% (60/60; IC95 94% a 100%) | YOLO é melhor (discordantes 9/0; McNemar exato p=0.00391) |
| blur | 60 | 60/60 | 100% (60/60; IC95 94% a 100%) | 58% (35/60; IC95 46% a 70%) | 100% (60/60; IC95 94% a 100%) | YOLO é melhor (discordantes 25/0; McNemar exato p=5.96e-08) |
| lowlight | 60 | 60/60 | 98% (59/60; IC95 91% a 100%) | 78% (47/60; IC95 66% a 87%) | 98% (59/60; IC95 91% a 100%) | YOLO é melhor (discordantes 12/0; McNemar exato p=0.000488) |
| tilt | 60 | 60/60 | 98% (59/60; IC95 91% a 100%) | 85% (51/60; IC95 74% a 92%) | 100% (60/60; IC95 94% a 100%) | YOLO é melhor (discordantes 9/1; McNemar exato p=0.0215) |
| occlusion | 60 | 35/60 | 55% (33/60; IC95 42% a 67%) | 53% (32/60; IC95 41% a 65%) | 68% (41/60; IC95 56% a 79%) | sem diferença detectável entre YOLO e baseline HSV (discordantes 9/8; p=1.000) |
| small | 60 | 60/60 | 22% (13/60; IC95 13% a 34%) | 72% (43/60; IC95 59% a 81%) | 80% (48/60; IC95 68% a 88%) | baseline HSV é melhor (discordantes 5/35; McNemar exato p=1.38e-06) |
| TOTAL | 360 | 335/360 | 79% (284/360; IC95 74% a 83%) | 72% (259/360; IC95 67% a 76%) | 91% (328/360; IC95 88% a 94%) | YOLO é melhor (discordantes 69/44; McNemar exato p=0.0235) |

### Matriz de confusão do estado — YOLO (linhas = verdade da regra; colunas = previsto)

| verdade \ previsto | lamp_normal | lamp_warning | lamp_critical | (nada) |
|---|---|---|---|---|
| lamp_normal | 101 | 3 | 3 | 19 |
| lamp_warning | 4 | 98 | 6 | 18 |
| lamp_critical | 2 | 2 | 85 | 19 |

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
