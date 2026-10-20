"""SPEC-011 · REQ-CV-004 (D-034, D-037): a visao e assistiva e isolada do runtime.

Nenhum codigo de runtime (API, worker, simulador, pacotes) importa o modulo de visao nem as
dependencias de ML (AGPL/torch), e as imagens Docker/requirements dos servicos nao as incluem.
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FORBIDDEN = {"spatial_cv", "ultralytics", "torch", "torchvision", "cv2"}
RUNTIME_DIRS = ["services", "packages"]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text("utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_runtime_code_never_imports_vision_or_ml_dependencies() -> None:
    offenders = []
    for directory in RUNTIME_DIRS:
        for path in (ROOT / directory).rglob("*.py"):
            bad = _imports(path) & FORBIDDEN
            if bad:
                offenders.append((str(path.relative_to(ROOT)), sorted(bad)))

    assert offenders == []


def test_service_requirements_and_dockerfiles_do_not_include_ml() -> None:
    for requirements in (ROOT / "services").glob("*/requirements*"):
        text = requirements.read_text("utf-8").lower()
        for name in ("ultralytics", "torch", "opencv"):
            assert name not in text, (requirements.name, name)
    for dockerfile in (ROOT / "services").glob("*/Dockerfile"):
        text = dockerfile.read_text("utf-8")
        assert "ml/" not in text
        assert "spatial_cv" not in text


def test_vision_package_only_reads_status_it_never_writes_or_publishes() -> None:
    """A visao nao importa o repositorio, o broker nem a API: nao pode alterar status/alertas."""
    forbidden = {"paho", "sqlalchemy", "fastapi", "psycopg", "app", "worker", "simulator"}
    for path in (ROOT / "ml").rglob("*.py"):
        if ".venv-ml" in path.parts:
            continue
        assert _imports(path) & forbidden == set(), path.name
