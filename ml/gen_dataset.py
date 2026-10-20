"""Gera o dataset YOLO sintetico (SPEC-011, REQ-CV-001). Deterministico: mesma saida a cada execucao.

Uso: python ml/gen_dataset.py [--out ml/data/synth] [--train 160 --val 30 --test 60]  (cenas POR condicao)
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "ml"),
    str(ROOT / "packages" / "domain" / "src"),
    str(ROOT / "packages" / "storage" / "src"),
]

from spatial_cv.dataset import DEFAULT_PER_CONDITION, build_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "ml" / "data" / "synth"))
    for split, default in DEFAULT_PER_CONDITION.items():
        parser.add_argument(f"--{split}", type=int, default=default, help="cenas por condicao")
    args = parser.parse_args()
    counts = {split: getattr(args, split) for split in DEFAULT_PER_CONDITION}
    data_yaml = build_dataset(Path(args.out), counts)
    print(f"dataset em {args.out} ({counts} por condicao); data.yaml: {data_yaml}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
