"""Treina o detector YOLO em CPU (SPEC-011, REQ-CV-002, D-034/D-040).

--model yolov8n.yaml  => do ZERO (linha de base);  --model ml/weights/yolov8n.pt => ajuste fino de pesos OFICIAIS.

Uso (no ambiente de ML): ml/.venv-ml/Scripts/python ml/train.py --epochs 40
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "ml"),
    str(ROOT / "packages" / "domain" / "src"),
    str(ROOT / "packages" / "storage" / "src"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(ROOT / "ml" / "data" / "synth" / "data.yaml"))
    parser.add_argument("--model", default="yolov8n.yaml", help="arquitetura (yaml = do zero)")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--imgsz", type=int, default=480)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--optimizer", default="AdamW")
    parser.add_argument("--lr0", type=float, default=0.002)
    parser.add_argument(
        "--mosaic",
        type=float,
        default=0.0,
        help="0 = sem mosaic (mais barato e converge mais rapido do zero)",
    )
    parser.add_argument(
        "--fraction", type=float, default=1.0, help="fracao do split de treino usada"
    )
    parser.add_argument("--name", default="synth-yolov8n")
    args = parser.parse_args()

    from ultralytics import YOLO

    started = time.time()
    model = YOLO(args.model)
    model.train(
        data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, device="cpu",
        seed=0, deterministic=True, pretrained=args.model.endswith(".pt"), project=str(ROOT / "ml" / "runs"),
        name=args.name, exist_ok=True, plots=False, amp=False, verbose=False, fraction=args.fraction, cache="ram", optimizer=args.optimizer, lr0=args.lr0, mosaic=args.mosaic, close_mosaic=0, workers=4,
    )  # fmt: skip
    print(
        f"treino concluido em {time.time() - started:.0f} s; pesos em ml/runs/{args.name}/weights/best.pt"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
