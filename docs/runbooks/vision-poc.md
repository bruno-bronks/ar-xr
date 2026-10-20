# Runbook — Visão computacional (PoC offline, dataset SINTÉTICO)

Spec: [SPEC-011](../../specs/functional/SPEC-011-vision-and-iot.md) · Decisão: [ADR-0006](../adr/0006-vision-poc-and-iot-gate.md) · Resultados: [docs/evidence/phase-5](../evidence/phase-5/README.md).

> **Sem fotos reais.** Tudo roda sobre imagens geradas por script. Os números mostram o método, não o desempenho em campo. A visão é **assistiva**: não altera status/alertas e não faz diagnóstico.

## 1. Gerar o dataset (determinístico; roda no `.venv` principal)
```powershell
.\.venv\Scripts\python.exe ml\gen_dataset.py            # 160/30/60 cenas por condição (treino/val/teste)
```
Cria `ml/data/synth/` (ignorado pelo Git): `images/`, `labels/` (YOLO), `manifest.csv` (verdade por imagem), `data.yaml`. Mesma semente ⇒ mesmos bytes.

## 2. Ambiente de ML (isolado; AGPL-3.0)
```powershell
python -m venv ml\.venv-ml
.\ml\.venv-ml\Scripts\python.exe -m pip install ultralytics segno      # baixa torch (CPU) — cerca de 1 GB
```
O `ultralytics` fica **só** neste ambiente: não entra nas imagens Docker, na API nem na CI (teste `test_isolation.py`). Uso interno de avaliação; distribuir ou servir exigiria revisar a licença AGPL (alternativa Apache-2.0: YOLOX).

## 3. Treinar e avaliar (CPU)
```powershell
# (A) do zero (linha de base) — cerca de 78 min na máquina de desenvolvimento
.\ml\.venv-ml\Scripts\python.exe ml\train.py --epochs 25 --imgsz 320 --fraction 0.5 --name synth-yolov8n
# (B) ajuste fino de pesos oficiais (D-040): baixa e VERIFICA o SHA-256 antes de usar
.\.venv\Scripts\python.exe ml\fetch_weights.py
.\ml\.venv-ml\Scripts\python.exe ml\train.py --model ml\weights\yolov8n.pt --epochs 12 --imgsz 320 --fraction 0.5 --name synth-yolov8n-pretrained
.\ml\.venv-ml\Scripts\python.exe ml\evaluate.py --weights ml\runs\synth-yolov8n\weights\best.pt --imgsz 320 --tag scratch
.\ml\.venv-ml\Scripts\python.exe ml\evaluate.py --weights ml\runs\synth-yolov8n-pretrained\weights\best.pt --imgsz 320 --tag pretrained --origin "ajuste fino de yolov8n.pt oficial (D-040)"
```
O `.pt` é um *pickle* do PyTorch (executa código ao carregar) e AGPL-3.0: só use o arquivo verificado, só em `ml/.venv-ml`. A CPU é o gargalo: uma época a 480 px com 960 imagens levou ~14 min; por isso 320 px e metade do treino.
`evaluate.py` roda só no split de **teste** e grava `docs/evidence/phase-5/cv-report-<tag>.md` e `cv-summary-<tag>.json` (mAP por classe/condição, comparação QR × YOLO, estado YOLO × baseline HSV × regra do simulador, IC 95 % de Wilson, McNemar exato, matrizes de confusão, latência em CPU).

## 4. Testes automáticos (sem torch)
`pytest tests/unit/ml` cobre o gerador, os rótulos, a estatística, os baselines e o isolamento do runtime.

## 5. Como ler o relatório
- Só há "melhor" quando McNemar exato dá p < 0,05; senão: *sem diferença detectável*.
- O baseline de cor e os distratores são escolhas minhas e influenciam o resultado.
- Oclusão pode esconder a lâmpada: nesses casos o estado é impossível para qualquer método visual.
- O YOLO identifica o **tipo**; isso equivale ao id só porque o seed tem um equipamento por tipo.
