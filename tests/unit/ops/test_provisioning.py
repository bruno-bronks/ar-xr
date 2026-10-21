"""SPEC-012 · REQ-OPS-009, REQ-OPS-003 e REQ-OPS-001: provisionamento declarativo (cloud-init + systemd) e estado desejado.

Estas checagens sao ESTATICAS (rodam em qualquer maquina). A validacao com as ferramentas oficiais
(`cloud-init schema`, `systemd-analyze verify`) roda em `scripts/verify_host.py` (Docker).
"""

import configparser
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from spatial_ops.gitops import parse_desired

ROOT = Path(__file__).resolve().parents[3]
SYSTEMD = ROOT / "deploy" / "systemd"
USER_DATA = ROOT / "deploy" / "cloud-init" / "user-data.yaml"
SERVICES = sorted(SYSTEMD.glob("*.service"))
TIMERS = sorted(SYSTEMD.glob("*.timer"))


def _unit(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str  # type: ignore[assignment,method-assign]
    parser.read(path, encoding="utf-8")
    return parser


def test_the_expected_units_exist() -> None:
    names = {p.name for p in SERVICES} | {p.name for p in TIMERS}

    assert names == {
        "spatial-gitops.service",
        "spatial-gitops.timer",
        "spatial-backup.service",
        "spatial-backup.timer",
        "spatial-backup-verify.service",
        "spatial-backup-verify.timer",
    }


@pytest.mark.parametrize("path", SERVICES, ids=lambda p: p.name)
def test_services_run_as_the_unprivileged_user_with_hardening(path: Path) -> None:
    service = _unit(path)["Service"]

    assert service["Type"] == "oneshot"
    assert service["User"] == "arxr"
    assert service["NoNewPrivileges"] == "yes"
    assert service["ProtectSystem"] == "strict"
    assert service["PrivateTmp"] == "yes"
    assert service["ReadWritePaths"] == "/opt/ar-xr/.deploy"  # unico lugar com escrita


@pytest.mark.parametrize("path", SERVICES, ids=lambda p: p.name)
def test_service_commands_point_to_scripts_that_exist_in_the_repository(path: Path) -> None:
    command = _unit(path)["Service"]["ExecStart"].split()

    assert command[0] == "/usr/bin/python3"  # caminho absoluto, sem shell
    relative = command[1].removeprefix("/opt/ar-xr/")
    assert (ROOT / relative).is_file(), relative
    assert "sh" not in command[:1]
    assert ";" not in " ".join(command)


@pytest.mark.parametrize("path", TIMERS, ids=lambda p: p.name)
def test_every_timer_points_to_an_existing_service_and_is_installable(path: Path) -> None:
    unit = _unit(path)

    assert (SYSTEMD / unit["Timer"]["Unit"]).is_file()
    assert unit["Install"]["WantedBy"] == "timers.target"


def test_the_reconciler_timer_does_not_pile_up_runs() -> None:
    timer = _unit(SYSTEMD / "spatial-gitops.timer")["Timer"]

    assert "OnUnitInactiveSec" in timer  # conta a partir do FIM da execucao anterior
    assert "RandomizedDelaySec" in timer


def test_backup_runs_daily_and_the_restore_drill_weekly() -> None:
    assert _unit(SYSTEMD / "spatial-backup.timer")["Timer"]["Persistent"] == "true"
    assert _unit(SYSTEMD / "spatial-backup-verify.timer")["Timer"]["OnCalendar"].startswith("Sun")


# --- cloud-init --------------------------------------------------------------------------------------------------


def _cloud_config() -> dict[str, Any]:
    text = USER_DATA.read_text("utf-8")
    assert text.startswith("#cloud-config\n")
    loaded = yaml.safe_load(text)
    assert isinstance(loaded, dict)
    return loaded


def test_cloud_init_disables_password_and_root_login() -> None:
    config = _cloud_config()

    assert config["ssh_pwauth"] is False
    assert config["disable_root"] is True
    assert config["users"][0]["lock_passwd"] is True


def test_cloud_init_firewall_denies_incoming_by_default() -> None:
    commands = [" ".join(c) for c in _cloud_config()["runcmd"] if isinstance(c, list)]

    assert "ufw default deny incoming" in commands
    assert "ufw allow OpenSSH" in commands
    assert not any(re.search(r"\b(80|443|8088|5432|55432|1883)\b", c) for c in commands)


def test_cloud_init_carries_no_secret_only_clearly_marked_placeholders() -> None:
    text = USER_DATA.read_text("utf-8")

    assert not re.search(r"(?i)(password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9+/]{12,}", text)
    assert "BEGIN" not in text
    assert "PRIVATE KEY" not in text
    assert text.count("PREENCHER") >= 2  # chave SSH e URL do repositorio


def test_the_bootstrap_installs_only_unit_files_that_exist_and_generates_the_secret_on_the_host() -> (
    None
):
    files = _cloud_config()["write_files"]
    bootstrap = next(f["content"] for f in files if f["path"].endswith("spatial-bootstrap.sh"))

    assert "deploy/systemd/*.service" in bootstrap
    assert "/dev/urandom" in bootstrap  # POSTGRES_PASSWORD nasce no host
    assert "umask 077" in bootstrap
    for timer in TIMERS:
        assert timer.name in bootstrap


# --- estado desejado ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path", sorted((ROOT / "deploy" / "desired").glob("*.json")), ids=lambda p: p.name
)
def test_every_committed_desired_state_is_valid_under_the_strict_contract(path: Path) -> None:
    desired = parse_desired(path.read_text("utf-8"))

    assert desired.tag


def test_the_vps_is_not_enrolled_in_gitops_without_an_explicit_request() -> None:
    assert not (ROOT / "deploy" / "desired" / "vps.json").exists()


# --- workflow de release (escrito, nao executado) -----------------------------------------------------------


def test_release_workflow_runs_only_on_version_tags_with_minimal_permissions() -> None:
    """REQ-OPS-001/D-044: publicar so por tag `v*`; permissoes minimas; so o GITHUB_TOKEN como segredo."""
    path = ROOT / ".github" / "workflows" / "release.yml"
    text = path.read_text("utf-8")
    workflow = yaml.safe_load(text)
    triggers = workflow.get("on", workflow.get(True))

    assert triggers == {"push": {"tags": ["v*"]}}
    assert workflow["permissions"] == {"contents": "read", "packages": "write"}
    assert set(re.findall(r"secrets\.(\w+)", text)) == {"GITHUB_TOKEN"}
    assert "tag invalida" in text  # a tag e validada antes de virar nome de imagem
    assert text.index("trivy") < text.index("docker compose push")  # varre antes de publicar
