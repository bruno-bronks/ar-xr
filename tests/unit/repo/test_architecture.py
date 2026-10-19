"""ADR-0001/0002: fronteiras de modulo verificadas por analise estatica dos imports (AST)."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text("utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def _package_imports(root: Path) -> dict[Path, set[str]]:
    return {p: _imports(p) for p in root.rglob("*.py")}


FRAMEWORKS = {
    "fastapi",
    "starlette",
    "sqlalchemy",
    "alembic",
    "psycopg",
    "paho",
    "pydantic",
    "uvicorn",
}
SERVICES = {"app", "worker", "simulator"}


def test_domain_is_pure_no_frameworks_no_io_libraries_no_other_internal_package() -> None:
    allowed_internal = {"spatial_domain"}
    for path, imports in _package_imports(ROOT / "packages/domain/src").items():
        assert not imports & FRAMEWORKS, f"{path.name} importa framework: {imports & FRAMEWORKS}"
        assert not imports & SERVICES, path.name
        assert not {i for i in imports if i.startswith("spatial_")} - allowed_internal, path.name


def test_common_package_has_no_domain_or_framework_dependencies() -> None:
    for path, imports in _package_imports(ROOT / "packages/common/src").items():
        assert not imports & (FRAMEWORKS | SERVICES | {"spatial_domain", "spatial_storage"}), path


def test_storage_depends_only_on_domain_and_never_on_services() -> None:
    for path, imports in _package_imports(ROOT / "packages/storage/src").items():
        assert not imports & SERVICES, f"{path.name} importa servico"
        assert not imports & {"fastapi", "starlette", "paho", "uvicorn"}, path.name


@pytest.mark.parametrize(
    ("service", "forbidden"),
    [
        ("services/telemetry-worker", {"app", "simulator", "fastapi", "starlette"}),
        ("services/equipment-simulator", {"app", "worker", "sqlalchemy", "psycopg", "fastapi"}),
        ("services/api", {"worker", "simulator", "paho"}),
    ],
)
def test_services_do_not_depend_on_each_other_or_on_foreign_stacks(
    service: str, forbidden: set[str]
) -> None:
    for path, imports in _package_imports(ROOT / service).items():
        assert not imports & forbidden, f"{path.name}: {imports & forbidden}"


def test_api_never_touches_table_definitions_directly() -> None:
    """A API fala com o banco pela porta `Repository`; so o composition root conhece o Postgres."""
    for path in (ROOT / "services/api/app").rglob("*.py"):
        source = path.read_text("utf-8")
        assert "spatial_storage.models" not in source, path.name
        if path.name != "main.py":
            assert "spatial_storage.postgres" not in source, path.name
