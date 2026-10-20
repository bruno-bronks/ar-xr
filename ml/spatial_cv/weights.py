"""Procedencia dos pesos pre-treinados oficiais (SPEC-011, D-040): URL pinada + SHA-256 + verificacao.

O `.pt` do PyTorch e um arquivo *pickle* (executa codigo ao carregar). Por isso so se carrega o arquivo
cujo SHA-256 confere com o pinado, vindo do release oficial, e apenas no ambiente isolado `ml/.venv-ml`.
O hash foi registrado do que foi baixado em 2026-10-20; NAO foi confirmado contra publicacao oficial.
"""

import hashlib
from pathlib import Path

URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt"
SHA256 = "f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36"
SIZE_BYTES = 6_549_796


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, expected: str = SHA256, size: int | None = SIZE_BYTES) -> None:
    """Levanta ValueError se o arquivo nao existe, tem tamanho diferente ou hash divergente."""
    if not path.is_file():
        raise ValueError(f"weights not found: {path.name}")
    if size is not None and path.stat().st_size != size:
        raise ValueError("weights size does not match the pinned size")
    if sha256_of(path) != expected.lower():
        raise ValueError("weights SHA-256 does not match the pinned hash")
