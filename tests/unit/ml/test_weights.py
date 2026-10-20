"""SPEC-011 · REQ-CV-002 (D-040): procedencia dos pesos pre-treinados (hash pinado e verificacao)."""

import hashlib
from pathlib import Path

import pytest
from spatial_cv import weights


def _file(tmp_path: Path, content: bytes) -> Path:
    path = tmp_path / "w.pt"
    path.write_bytes(content)
    return path


def test_pinned_values_have_the_expected_shape() -> None:
    assert weights.URL.startswith("https://github.com/ultralytics/assets/releases/download/v")
    assert len(weights.SHA256) == 64
    assert int(weights.SHA256, 16) >= 0
    assert weights.SIZE_BYTES > 1_000_000


def test_matching_file_passes(tmp_path: Path) -> None:
    content = b"pesos de teste"
    path = _file(tmp_path, content)

    weights.verify(path, hashlib.sha256(content).hexdigest(), size=len(content))


def test_wrong_hash_is_rejected(tmp_path: Path) -> None:
    path = _file(tmp_path, b"adulterado")

    with pytest.raises(ValueError, match="SHA-256"):
        weights.verify(path, hashlib.sha256(b"original").hexdigest(), size=None)


def test_wrong_size_is_rejected_before_hashing(tmp_path: Path) -> None:
    path = _file(tmp_path, b"abc")

    with pytest.raises(ValueError, match="size"):
        weights.verify(path, hashlib.sha256(b"abc").hexdigest(), size=999)


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not found"):
        weights.verify(tmp_path / "nao-existe.pt")


def test_hash_comparison_is_case_insensitive(tmp_path: Path) -> None:
    content = b"x"
    path = _file(tmp_path, content)

    weights.verify(path, hashlib.sha256(content).hexdigest().upper(), size=None)


def test_actual_downloaded_weights_if_present_match_the_pin() -> None:
    """Se os pesos baixados existirem localmente, precisam conferir com o hash pinado."""
    path = Path(__file__).resolve().parents[3] / "ml" / "weights" / "yolov8n.pt"
    if not path.is_file():
        pytest.skip("pesos nao baixados (ml/fetch_weights.py)")

    weights.verify(path)
