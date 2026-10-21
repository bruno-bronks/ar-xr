"""REQ-SEC-001, REQ-SEC-002 e REQ-ENG-005: segredos, portas em loopback e gates de CI."""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SENSITIVE = re.compile(r"(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE)", re.IGNORECASE)
PLACEHOLDER = re.compile(r"(change-?me|dev-only|example|placeholder|fake)", re.IGNORECASE)


def _compose() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "compose.yaml").read_text("utf-8"))  # type: ignore[no-any-return]


# --- REQ-SEC-001 ------------------------------------------------------------------------


def test_env_file_is_gitignored() -> None:
    lines = (ROOT / ".gitignore").read_text("utf-8").splitlines()

    assert ".env" in lines
    assert ".venv/" in lines or ".venv" in lines


def test_env_example_has_only_placeholder_secrets() -> None:
    content = (ROOT / ".env.example").read_text("utf-8")
    assignments = [
        line.split("=", 1)
        for line in content.splitlines()
        if "=" in line and not line.startswith("#")
    ]

    assert assignments
    for key, value in assignments:
        if SENSITIVE.search(key):
            assert PLACEHOLDER.search(value), f"{key} parece conter segredo real"


@pytest.mark.skipif(shutil.which("git") is None, reason="git indisponivel")
def test_no_env_file_is_tracked_by_git() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("nao e um repositorio git")
    tracked = subprocess.run(
        ["git", "ls-files"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    env_files = [f for f in tracked if re.fullmatch(r"(.*/)?\.env(\.[a-z]+)?", f)]
    assert set(env_files) <= {".env.example"}


# --- REQ-SEC-002 ------------------------------------------------------------------------


def test_compose_has_expected_services() -> None:
    services = _compose()["services"]
    assert set(services) == {"db", "broker", "migrate", "api", "worker", "simulator", "prometheus"}
    # observabilidade e opcional (REQ-OPS-005): so sobe com `--profile observability`
    assert services["prometheus"]["profiles"] == ["observability"]
    assert all("profiles" not in s for n, s in services.items() if n != "prometheus")


def test_compose_published_ports_bind_loopback_only() -> None:
    for name, service in _compose()["services"].items():
        for port in service.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), f"{name}: {port}"


def test_compose_images_are_pinned_and_not_privileged() -> None:
    for name, service in _compose()["services"].items():
        image = service.get("image")
        if image:
            assert ":" in image, f"{name}: imagem sem tag ({image})"
            assert not image.endswith(":latest"), f"{name}: tag latest ({image})"
        assert not service.get("privileged"), name


def test_compose_services_have_healthchecks_and_api_waits_for_dependencies() -> None:
    services = _compose()["services"]

    for name in ("db", "broker", "api", "worker"):
        assert "healthcheck" in services[name], name
    for name in ("api", "worker"):
        depends = services[name]["depends_on"]
        assert depends["db"]["condition"] == "service_healthy", name
        assert depends["broker"]["condition"] == "service_healthy", name
        assert depends["migrate"]["condition"] == "service_completed_successfully", name
    assert services["simulator"]["depends_on"]["worker"]["condition"] == "service_healthy"


@pytest.mark.parametrize("service", ["api", "telemetry-worker", "equipment-simulator"])
def test_service_dockerfiles_run_as_non_root(service: str) -> None:
    dockerfile = (ROOT / f"services/{service}/Dockerfile").read_text("utf-8")
    users = re.findall(r"^USER\s+(\S+)", dockerfile, flags=re.MULTILINE)

    assert users
    assert users[-1] not in {"root", "0"}


def test_mosquitto_dev_config_is_documented_as_dev_only() -> None:
    config = (ROOT / "platform/mosquitto/mosquitto.conf").read_text("utf-8")

    assert "DEV" in config.upper()


# --- REQ-ENG-005 ------------------------------------------------------------------------


def test_ci_workflow_runs_all_required_gates() -> None:
    text = (ROOT / ".github/workflows/ci.yml").read_text("utf-8")
    workflow = yaml.safe_load(text)

    for gate in ("ruff check", "ruff format --check", "mypy", "pytest", "gitleaks", "pip-audit"):
        assert gate in text, f"gate ausente na CI: {gate}"
    assert workflow["jobs"]
    # nenhum gate pode ser silenciado
    assert "continue-on-error: true" not in text
