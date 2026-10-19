"""SPEC-008 A8 · REQ-AR-006: geracao reprodutivel dos QR de teste (positivos e negativos).

A decodificacao com a MESMA biblioteca do app (ZXing.Net) roda em tests/csharp (QrRoundTripTests);
aqui, alem da estrutura, o OpenCV decodifica de forma independente.
"""

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest
from spatial_storage.seed_data import SEED

ROOT = Path(__file__).resolve().parents[3]
MARKER_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}")
CRLF, LF = bytes([13, 10]), bytes([10])  # git pode normalizar o fim de linha do manifest.json


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_qr", ROOT / "scripts/generate_qr.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load()


@pytest.fixture(scope="module")
def out(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("qr")
    gen.generate(directory)
    return directory


def _manifest(out: Path) -> list[dict[str, str]]:
    return json.loads((out / "manifest.json").read_text("utf-8"))["codes"]  # type: ignore[no-any-return]


def test_positive_cases_are_exactly_the_org_a_seed_markers() -> None:
    seeded = {e.marker_id for e in SEED.equipment if e.org_id == "org-a"}
    positive = {c["content"] for c in gen.CASES if c["kind"] == "valid"}

    assert positive == seeded == {"QR-EQ-001", "QR-EQ-002", "QR-EQ-003"}


def test_foreign_case_is_the_other_orgs_seed_marker_and_unknown_is_not_in_the_seed() -> None:
    seeded = {e.marker_id for e in SEED.equipment}
    by_kind = {
        c["kind"]: c["content"] for c in gen.CASES if c["kind"] in {"foreign_org", "unknown"}
    }

    assert by_kind["foreign_org"] == next(
        e.marker_id for e in SEED.equipment if e.org_id == "org-b"
    )
    assert by_kind["unknown"] not in seeded


def test_marker_shaped_cases_obey_the_client_alphabet_and_invalid_ones_do_not() -> None:
    for case in gen.CASES:
        shaped = MARKER_RE.fullmatch(case["content"]) is not None
        assert shaped == (case["kind"] in {"valid", "foreign_org", "unknown"}), case["name"]


def test_every_case_has_png_pgm_and_manifest_entry(out: Path) -> None:
    manifest = _manifest(out)

    assert {m["name"] for m in manifest} == {c["name"] for c in gen.CASES}
    for entry in manifest:
        assert (out / entry["png"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert (out / entry["pgm"]).exists()
        assert entry["expected_app_behavior"]


def test_pgm_is_a_square_binary_bitmap_with_only_black_and_white(out: Path) -> None:
    for entry in _manifest(out):
        raw = (out / entry["pgm"]).read_bytes()
        header = re.match(rb"P5\n(\d+) (\d+)\n255\n", raw)
        assert header is not None
        width, height = int(header.group(1)), int(header.group(2))
        pixels = raw[header.end() :]
        assert width == height
        assert len(pixels) == width * height
        assert set(pixels) <= {0, 255}
        assert set(pixels) == {0, 255}


def test_generation_is_deterministic(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"

    gen.generate(first)
    gen.generate(second)

    for file in first.iterdir():
        assert file.read_bytes() == (second / file.name).read_bytes(), file.name


def test_opencv_independently_decodes_every_pgm_to_its_exact_content(out: Path) -> None:
    cv2 = pytest.importorskip("cv2")
    numpy = pytest.importorskip("numpy")
    detector = cv2.QRCodeDetector()

    for entry in _manifest(out):
        raw = (out / entry["pgm"]).read_bytes()
        header = re.match(rb"P5\n(\d+) (\d+)\n255\n", raw)
        assert header is not None
        size = int(header.group(1))
        image = numpy.frombuffer(raw[header.end() :], dtype=numpy.uint8).reshape(size, size)
        decoded, _, _ = detector.detectAndDecode(image)
        assert decoded == entry["content"], entry["name"]


def test_output_never_contains_secrets(out: Path) -> None:
    text = (out / "manifest.json").read_text("utf-8")

    assert "demo-operator" not in text
    assert "password" not in text.lower()


def test_committed_qr_assets_are_up_to_date(tmp_path: Path) -> None:
    """Os arquivos versionados (usados pelos testes C#) devem ser exatamente o que o script gera."""
    gen.generate(tmp_path)
    committed = ROOT / "docs/evidence/phase-2/qr"

    for file in [*sorted(tmp_path.glob("*.pgm")), tmp_path / "manifest.json"]:
        stored = (committed / file.name).read_bytes().replace(CRLF, LF)
        assert stored == file.read_bytes().replace(CRLF, LF), file.name
    assert {p.name for p in committed.glob("*.pgm")} == {p.name for p in tmp_path.glob("*.pgm")}
