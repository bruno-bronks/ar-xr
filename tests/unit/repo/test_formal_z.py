"""REQ-ENG-007: as specs Z passam por parse + typecheck REAIS (CZT) e um erro de tipo e rejeitado.

Requer JDK + czt.jar (ver docs/decisions/tool-evaluation.md). Sem eles os testes sao PULADOS
(nunca "passam"). O typecheck valida SINTAXE e TIPOS; nao prova teoremas.
"""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = Path.home() / ".tools"
Z_FILES = sorted((ROOT / "specs/formal-z").glob("*.tex"))


def _find_java() -> Path | None:
    configured = os.environ.get("JAVA_EXE")
    if configured and Path(configured).exists():
        return Path(configured)
    found = sorted(TOOLS.glob("jdk-*/bin/java.exe")) + sorted(TOOLS.glob("jdk-*/bin/java"))
    return found[0] if found else None


JAVA = _find_java()
CZT = Path(os.environ.get("CZT_JAR", TOOLS / "czt" / "czt.jar"))

pytestmark = pytest.mark.skipif(
    JAVA is None or not CZT.exists(), reason="JDK/CZT nao instalados (REQ-ENG-007 nao verificado)"
)


def _typecheck(path: Path) -> tuple[int, str]:
    assert JAVA is not None
    result = subprocess.run(  # noqa: S603
        [str(JAVA), "-jar", str(CZT), str(path)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def test_there_are_z_specs_to_check() -> None:
    assert len(Z_FILES) >= 3


@pytest.mark.parametrize("spec", Z_FILES, ids=lambda p: p.name)
def test_spec_parses_and_typechecks_with_zero_warnings_and_errors(spec: Path) -> None:
    code, output = _typecheck(spec)

    assert code == 0, output
    assert "Exception" not in output
    assert "0 warnings and errors" in output


def test_an_injected_type_error_is_rejected(tmp_path: Path) -> None:
    source = (ROOT / "specs/formal-z/z-002-status-evaluation.tex").read_text("utf-8")
    broken = tmp_path / "broken.tex"
    broken.write_text(source.replace(r"warn \leq crit", r"warn \leq GOOD"), encoding="utf-8")

    _, output = _typecheck(broken)

    assert "Type mismatch" in output
    assert "0 warnings and errors" not in output


def test_a_syntax_error_is_rejected(tmp_path: Path) -> None:
    source = (ROOT / "specs/formal-z/z-003-marker-resolution.tex").read_text("utf-8")
    broken = tmp_path / "broken.tex"
    broken.write_text(
        source.replace(r"\ran markerOf \subseteq", r"\ran markerOf \subseteq \subseteq"),
        encoding="utf-8",
    )

    code, output = _typecheck(broken)

    assert code != 0 or "0 warnings and errors" not in output
    assert "Syntax error" in output or "Exception" in output
