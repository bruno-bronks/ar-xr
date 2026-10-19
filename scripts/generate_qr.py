"""Gera os QR de teste do cliente AR (SPEC-008, REQ-AR-006): positivos e negativos.

O conteudo do QR e SOMENTE o marker opaco (nunca dados do equipamento). Saidas por caso:
  <nome>.png  imprimir (~8 cm de lado)
  <nome>.pgm  bitmap cinza P5 para testes automatizados (decodificados com ZXing.Net em tests/csharp)
  manifest.json  conteudo esperado e comportamento esperado do app

Uso:  python scripts/generate_qr.py [pasta-de-saida]     (padrao: docs/evidence/phase-2/qr)
Requer: pip install segno
"""

import json
import sys
from pathlib import Path
from typing import Any

import segno

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/evidence/phase-2/qr"
SCALE = 8  # pixels por modulo no PGM
BORDER = 4  # modulos de zona silenciosa (minimo da especificacao do QR)

CASES: list[dict[str, str]] = [
    {
        "name": "valid-QR-EQ-001",
        "content": "QR-EQ-001",
        "kind": "valid",
        "expected_app_behavior": "resolve para EQ-001 e exibe o overlay (org-a)",
    },
    {
        "name": "valid-QR-EQ-002",
        "content": "QR-EQ-002",
        "kind": "valid",
        "expected_app_behavior": "resolve para EQ-002 e exibe o overlay (org-a)",
    },
    {
        "name": "valid-QR-EQ-003",
        "content": "QR-EQ-003",
        "kind": "valid",
        "expected_app_behavior": "resolve para EQ-003 e exibe o overlay (org-a)",
    },
    {
        "name": "foreign-QR-EQ-B01",
        "content": "QR-EQ-B01",
        "kind": "foreign_org",
        "expected_app_behavior": "Marcador nao reconhecido (identico ao desconhecido; nenhum dado)",
    },
    {
        "name": "unknown-QR-NAO-EXISTE",
        "content": "QR-NAO-EXISTE",
        "kind": "unknown",
        "expected_app_behavior": "Marcador nao reconhecido (identico ao de outra organizacao)",
    },
    {
        "name": "invalid-url",
        "content": "https://example.com/QR-EQ-001",
        "kind": "invalid_content",
        "expected_app_behavior": "descartado localmente: NENHUMA requisicao ao servidor",
    },
    {
        "name": "invalid-json",
        "content": '{"id":"EQ-001"}',
        "kind": "invalid_content",
        "expected_app_behavior": "descartado localmente: NENHUMA requisicao ao servidor",
    },
    {
        "name": "invalid-space",
        "content": "QR EQ 001",
        "kind": "invalid_content",
        "expected_app_behavior": "descartado localmente: NENHUMA requisicao ao servidor",
    },
]


def _pgm(code: segno.QRCode) -> bytes:
    """Bitmap P5 (8 bits): modulo escuro = 0, claro = 255, com zona silenciosa."""
    side = len(code.matrix) + 2 * BORDER
    light_row = bytes([255]) * (side * SCALE)
    pixels = bytearray(light_row * (BORDER * SCALE))
    for row in code.matrix:
        line = bytearray(bytes([255]) * (BORDER * SCALE))
        for dark in row:
            line.extend(bytes([0 if dark else 255]) * SCALE)
        line.extend(bytes([255]) * (BORDER * SCALE))
        pixels.extend(bytes(line) * SCALE)
    pixels.extend(light_row * (BORDER * SCALE))
    size = side * SCALE
    header = f"P5\n{size} {size}\n255\n".encode("ascii")
    return header + bytes(pixels)


def generate(out_dir: Path) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    for case in CASES:
        code = segno.make(case["content"], error="q", micro=False)
        png, pgm = f"{case['name']}.png", f"{case['name']}.pgm"
        code.save(out_dir / png, kind="png", scale=10, border=BORDER)
        (out_dir / pgm).write_bytes(_pgm(code))
        manifest.append({**case, "png": png, "pgm": pgm})
    (out_dir / "manifest.json").write_text(
        json.dumps({"codes": manifest}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str]) -> int:
    out = Path(argv[0]) if argv else DEFAULT_OUT
    manifest = generate(out)
    print(f"{len(manifest)} QR gerados em {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
