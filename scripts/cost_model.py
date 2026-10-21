"""Imprime (ou grava com --write) a estimativa de custos reproduzivel (SPEC-012, REQ-OPS-008).

python scripts/cost_model.py            # imprime
python scripts/cost_model.py --write    # atualiza docs/cloud/cost-estimate.md
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "ops" / "src"))

from spatial_ops.cost import render_markdown  # noqa: E402


def main() -> int:
    text = render_markdown()
    if "--write" in sys.argv[1:]:
        target = ROOT / "docs" / "cloud" / "cost-estimate.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, "utf-8")
        print(f"escrito: {target}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
