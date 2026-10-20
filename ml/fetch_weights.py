"""Baixa os pesos oficiais yolov8n.pt (URL pinada) e VERIFICA o SHA-256 antes de aceitar (SPEC-011, D-040).

Uso: python ml/fetch_weights.py  (grava ml/weights/yolov8n.pt; apaga o arquivo se o hash divergir)
"""

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

from spatial_cv import weights  # noqa: E402


def main() -> int:
    target = ROOT / "ml" / "weights" / "yolov8n.pt"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        try:
            weights.verify(target)
            print(f"ja presente e verificado: {target}")
            return 0
        except ValueError as error:
            print(f"arquivo existente reprovado ({error}); baixando de novo")
    with urllib.request.urlopen(weights.URL, timeout=120) as response:  # noqa: S310 - URL https pinada
        target.write_bytes(response.read(weights.SIZE_BYTES + 1))
    try:
        weights.verify(target)
    except ValueError as error:
        target.unlink(missing_ok=True)
        print(f"REPROVADO: {error}; arquivo removido")
        return 1
    print(f"baixado e verificado: {target} (sha256 {weights.SHA256})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
