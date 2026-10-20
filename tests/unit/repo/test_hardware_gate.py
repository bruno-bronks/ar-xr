"""SPEC-011 · REQ-IOT-001: portao de aprovacao do hardware (plano eletrico e de seguranca).

Enquanto o plano nao estiver aprovado (todos os itens G1-G7 marcados + aprovacao registrada), o repositorio
NAO pode conter firmware, projeto de placa, nem tópico/rotina de atuacao.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs/hardware/esp32-electrical-safety-plan.md"
IGNORED_PARTS = {
    ".venv",
    ".venv-ml",
    "node_modules",
    "graphify-out",
    ".git",
    "Library",
    "__pycache__",
}
FIRMWARE_FILES = (
    "*.ino",
    "platformio.ini",
    "sdkconfig",
    "sdkconfig.defaults",
    "CMakeLists.txt",
    "*.kicad_pcb",
    "*.kicad_sch",
)


def _plan() -> str:
    return PLAN.read_text("utf-8")


def _gates() -> list[tuple[str, bool]]:
    return [
        (m.group(2), m.group(1) == "x")
        for m in re.finditer(r"^- \[( |x)\] \*\*(G\d)\*\*", _plan(), flags=re.MULTILINE)
    ]


def test_plan_declares_every_gate_and_its_state() -> None:
    gates = _gates()

    assert [g for g, _ in gates] == [f"G{i}" for i in range(1, 8)]
    assert "NÃO APROVADO" in _plan() or all(done for _, done in gates)


def test_plan_states_it_is_not_written_by_a_qualified_engineer() -> None:
    text = _plan()

    assert "não por profissional habilitado" in text
    assert "TLS" in text
    assert "nenhuma saída de atuação" in text.lower() or "nenhuma saída de atuação" in text


def test_no_firmware_or_board_files_exist_while_the_gate_is_open() -> None:
    gates_open = not all(done for _, done in _gates())
    found = []
    for pattern in FIRMWARE_FILES:
        for path in ROOT.rglob(pattern):
            if (
                not IGNORED_PARTS & set(path.parts)
                and "tests" not in path.parts
                and "clients" not in path.parts
            ):
                found.append(str(path.relative_to(ROOT)))
    firmware_dirs = [d for d in ("firmware", "hardware", "esp32") if (ROOT / d).is_dir()]

    if gates_open:
        assert found == []
        assert firmware_dirs == []


def test_no_actuation_topics_or_command_channels_exist_in_the_contracts() -> None:
    asyncapi = (ROOT / "specs/contracts/asyncapi.yaml").read_text("utf-8").lower()

    assert "command" not in asyncapi
    assert "actuat" not in asyncapi
    secure_acl = (ROOT / "platform/mosquitto/secure.acl").read_text("utf-8")
    assert not re.search(
        r"^\s*(topic|pattern)\s+(readwrite|write)\s+.*command", secure_acl, flags=re.MULTILINE
    )
