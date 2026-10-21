"""SPEC-012 · REQ-OPS-001, REQ-OPS-002, REQ-OPS-003, REQ-OPS-004: deploy por tag, release DEFEITUOSA, rollback e ensaio de
desastre com DOCKER REAL (registry local `registry:2`, projeto Compose proprio e portas proprias).

Demorado (varios minutos) e usa a rede/portas locais: so roda com `OPS_E2E=1`. Nao toca a pilha de
desenvolvimento nem o VPS (D-042). Os testes sao ORDENADOS e compartilham o ambiente do modulo.
"""

import json
import os
import shutil
import subprocess
import time
import urllib.request
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from spatial_ops.backup import BackupService
from spatial_ops.deploy import Deployer, EnvConfig, compose_base, load_env_config
from spatial_ops.gitops import GitCliSource, Reconciler
from spatial_ops.runner import SubprocessRunner
from spatial_ops.state import StateStore

ROOT = Path(__file__).resolve().parents[2]
PROJECT = "spatial-opse2e"
API_PORT, DB_PORT, MQTT_PORT, REGISTRY_PORT = 28088, 55434, 21883, 25000
IMAGES = ("spatial-ai-api", "spatial-ai-worker", "spatial-ai-simulator")
IMAGES_SERVICES = ("api", "worker", "simulator")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("OPS_E2E") != "1", reason="defina OPS_E2E=1 (teste demorado, usa Docker)"
    ),
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker indisponivel"),
]


@dataclass
class Ctx:
    registry: str
    config: EnvConfig
    runner: SubprocessRunner
    deployer: Deployer
    backups: BackupService
    timings: dict[str, float] = field(default_factory=dict)

    def api(self, path: str, bearer: str | None = "demo-operator-a") -> int:
        headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
        request = urllib.request.Request(f"http://127.0.0.1:{API_PORT}{path}", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
                return int(response.status)
        except Exception:
            return 0

    def sql(self, statement: str) -> str:
        command = [
            *compose_base(self.config),
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "spatial",
            "-d",
            "spatial",
            "-tAc",
            statement,
        ]
        return self.runner.run(command, env=dict(self.config.env), timeout=60).stdout.strip()

    def running_tag(self) -> str:
        images = self.deployer.running_images("x")
        tags = {
            image.rsplit(":", 1)[1]
            for service, image in images.items()
            if service in ("api", "worker", "simulator")
        }
        assert len(tags) == 1, images
        return tags.pop()


def _docker(
    *args: str, check: bool = True, timeout: int = 900, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["docker", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=check,
        timeout=timeout,
        env={**os.environ, **(env or {})},
    )


@pytest.fixture(scope="module")
def ctx(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Ctx]:
    work = tmp_path_factory.mktemp("ops-e2e")
    registry_name = f"it-registry-{uuid.uuid4().hex[:8]}"
    # porta FIXA: o daemon do Docker Desktop nao enxerga portas dinamicas publicadas no host
    _docker(
        "run",
        "-d",
        "--rm",
        "--name",
        registry_name,
        "-p",
        f"127.0.0.1:{REGISTRY_PORT}:5000",
        "registry:2",
    )
    registry = f"127.0.0.1:{REGISTRY_PORT}/"
    env_file = work / "e2e.env"
    env_file.write_text(
        f"OPS_COMPOSE_FILES=compose.yaml,deploy/vps/compose.override.yaml\nOPS_PROJECT={PROJECT}\n"
        f"OPS_REGISTRY={registry}\nOPS_API_URL=http://127.0.0.1:{API_PORT}\nOPS_SMOKE_TOKEN=demo-operator-a\n"
        f"OPS_WAIT_SECONDS=150\nOPS_SMOKE_SECONDS=90\nAPI_PORT={API_PORT}\nDB_PORT={DB_PORT}\nMQTT_PORT={MQTT_PORT}\n"
        "POSTGRES_PASSWORD=e2e-dev-only\n",
        "utf-8",
    )
    config = load_env_config(env_file, ROOT)
    runner = SubprocessRunner()
    deployer = Deployer(config, runner, StateStore(work / "state.json"))
    try:
        # v1: build real a partir do codigo atual; v2: mesma imagem, outra tag; bad: api que sai ao iniciar
        _docker(
            *("compose", "--project-directory", str(ROOT), "-f", str(ROOT / "compose.yaml")),
            *("build", *IMAGES_SERVICES),
            env={"IMAGE_TAG": "v1", "IMAGE_REGISTRY": registry},
            timeout=1800,
        )
        for name in IMAGES:
            _docker("tag", f"{registry}{name}:v1", f"{registry}{name}:v2")
            _docker("tag", f"{registry}{name}:v1", f"{registry}{name}:bad")
        dockerfile = work / "Dockerfile.bad"
        dockerfile.write_text(
            f'FROM {registry}spatial-ai-api:v1\nCMD ["python", "-c", "import sys; sys.exit(3)"]\n',
            "utf-8",
        )
        _docker("build", "-f", str(dockerfile), "-t", f"{registry}spatial-ai-api:bad", str(work))
        # "bad2": mesma release defeituosa sob outra tag (o GitOps nao repete uma tag que ja falhou)
        _docker("tag", f"{registry}spatial-ai-api:bad", f"{registry}spatial-ai-api:bad2")
        for name in IMAGES[1:]:
            _docker("tag", f"{registry}{name}:v1", f"{registry}{name}:bad2")
        for tag in ("v1", "v2", "bad", "bad2"):
            for name in IMAGES:
                _docker("push", f"{registry}{name}:{tag}")
        context = Ctx(
            registry, config, runner, deployer, BackupService(config, runner, work / "backups")
        )
        yield context
        # medicoes para a evidencia (pasta ignorada pelo Git)
        (ROOT / ".deploy").mkdir(exist_ok=True)
        (ROOT / ".deploy" / "ops-e2e-summary.json").write_text(
            json.dumps(context.timings, indent=2), "utf-8"
        )
    finally:
        env = {**config.env, "IMAGE_TAG": "v1", "IMAGE_REGISTRY": registry}
        runner.run([*compose_base(config), "down", "-v", "--remove-orphans"], env=env, timeout=300)
        _docker("rm", "-f", registry_name, check=False)


def _timed(ctx: Ctx, name: str, started: float) -> None:
    ctx.timings[name] = round(time.monotonic() - started, 1)


def test_1_first_release_is_deployed_by_tag_and_the_stack_serves(ctx: Ctx) -> None:
    started = time.monotonic()

    result = ctx.deployer.deploy("v1")

    _timed(ctx, "deploy_v1_s", started)
    assert result.ok, result
    assert ctx.running_tag() == "v1"
    assert ctx.api("/health/ready", None) == 200
    assert ctx.api("/api/v1/equipment") == 200


def test_2_second_release_replaces_it_and_keeps_v1_for_rollback(ctx: Ctx) -> None:
    started = time.monotonic()

    result = ctx.deployer.deploy("v2")

    _timed(ctx, "deploy_v2_s", started)
    assert result.ok, result
    assert ctx.running_tag() == "v2"
    state = ctx.deployer._store.load()
    assert (state.current, state.previous) == ("v2", "v1")


def test_3_a_defective_release_rolls_back_automatically_and_the_service_stays_up(ctx: Ctx) -> None:
    started = time.monotonic()

    result = ctx.deployer.deploy("bad")

    _timed(ctx, "bad_release_and_auto_rollback_s", started)
    assert not result.ok
    assert result.rolled_back_to == "v2"
    assert ctx.running_tag() == "v2"  # a tag defeituosa NAO ficou rodando
    assert ctx.api("/health/ready", None) == 200
    assert ctx.api("/api/v1/equipment") == 200
    results = [e.result for e in ctx.deployer._store.load().history]
    assert results[-3:] == ["deployed", "failed", "rolled_back"]


def test_4_manual_rollback_returns_to_the_previous_tag(ctx: Ctx) -> None:
    started = time.monotonic()

    result = ctx.deployer.rollback()

    _timed(ctx, "manual_rollback_s", started)
    assert result.ok, result
    assert ctx.running_tag() == "v1"
    assert ctx.api("/health/ready", None) == 200
    state = ctx.deployer._store.load()
    assert (state.current, state.previous) == ("v1", "v2")


def test_5_backup_is_verified_by_a_restore_drill_and_a_disaster_is_recovered(ctx: Ctx) -> None:
    deadline = time.monotonic() + 90
    while (
        time.monotonic() < deadline
        and int(ctx.sql("SELECT count(*) FROM telemetry_events") or 0) < 10
    ):
        time.sleep(3)
    before_disaster = int(ctx.sql("SELECT count(*) FROM telemetry_events") or 0)
    assert before_disaster >= 10, "o simulador deveria ter gerado telemetria"

    manifest = ctx.backups.create()
    drill = ctx.backups.verify(manifest)
    ctx.timings["backup_size_bytes"] = float(manifest.size)
    ctx.timings["drill_restore_s"] = round(drill.restore_seconds, 2)
    assert drill.ok, drill.mismatches
    assert manifest.tables_before["telemetry_events"] >= 10

    # DESASTRE: a tabela de eventos e apagada
    ctx.sql("TRUNCATE telemetry_events CASCADE")
    assert (
        int(ctx.sql("SELECT count(*) FROM telemetry_events") or 0)
        < manifest.tables_before["telemetry_events"]
    )

    # RECUPERACAO: para a aplicacao, recria o banco a partir do dump e reinicia
    started = time.monotonic()
    env = dict(ctx.config.env)
    ctx.runner.run(
        [*compose_base(ctx.config), "stop", "simulator", "worker", "api"], env=env, timeout=300
    )
    restore_seconds = ctx.backups.restore(manifest, "spatial")
    ctx.runner.run(
        [*compose_base(ctx.config), "start", "api", "worker", "simulator"], env=env, timeout=300
    )
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline and ctx.api("/health/ready", None) != 200:
        time.sleep(2)
    ctx.timings["rto_total_s"] = round(time.monotonic() - started, 1)
    ctx.timings["restore_only_s"] = round(restore_seconds, 2)

    assert ctx.api("/health/ready", None) == 200
    assert ctx.api("/api/v1/equipment") == 200
    recovered = int(ctx.sql("SELECT count(*) FROM telemetry_events") or 0)
    assert recovered >= manifest.tables_before["telemetry_events"]


def test_6_gitops_reconciler_converges_detects_drift_and_does_not_loop_on_a_bad_release(
    ctx: Ctx, tmp_path: Path
) -> None:
    """REQ-OPS-003 com Git REAL (repositorio remoto local) e a pilha REAL."""
    remote, work, clone = tmp_path / "remote.git", tmp_path / "work", tmp_path / "clone"

    def git(*args: str, cwd: Path) -> None:
        subprocess.run(  # noqa: S603
            ["git", "-c", "user.email=t@example.test", "-c", "user.name=t", *args],  # noqa: S607
            cwd=cwd,
            check=True,
            capture_output=True,
        )

    def declare(tag: str) -> None:
        (work / "deploy" / "desired").mkdir(parents=True, exist_ok=True)
        (work / "deploy" / "desired" / "e2e.json").write_text(json.dumps({"tag": tag}), "utf-8")
        git("add", ".", cwd=work)
        git("commit", "-m", f"desired {tag}", cwd=work)
        git("push", "origin", "HEAD:main", cwd=work)

    git("init", "--bare", "-b", "main", str(remote), cwd=tmp_path)
    git("clone", str(remote), str(work), cwd=tmp_path)
    declare("v2")
    git("clone", str(remote), str(clone), cwd=tmp_path)
    store = ctx.deployer._store
    reconciler = Reconciler(
        ctx.deployer,
        GitCliSource(ctx.runner, clone, remote="origin", ref="origin/main"),
        store,
        env="e2e",
    )

    started = time.monotonic()
    first = reconciler.reconcile()
    ctx.timings["gitops_apply_s"] = round(time.monotonic() - started, 1)
    assert (first.ok, first.action, first.desired) == (True, "applied", "v2"), first
    assert ctx.running_tag() == "v2"

    events_before = len(store.load().history)
    assert reconciler.reconcile().action == "in-sync"
    assert len(store.load().history) == events_before  # idempotente: nenhum deploy novo

    # DRIFT: alguem sobe outra tag a mao; o reconciliador percebe e corrige
    ctx.runner.run(
        [
            *compose_base(ctx.config),
            "up",
            "-d",
            "--no-build",
            "--wait",
            "api",
            "worker",
            "simulator",
        ],
        env={**ctx.config.env, "IMAGE_TAG": "v1", "IMAGE_REGISTRY": ctx.registry},
        timeout=300,
    )
    assert ctx.running_tag() == "v1"
    started = time.monotonic()
    drift = reconciler.reconcile()
    ctx.timings["gitops_drift_correction_s"] = round(time.monotonic() - started, 1)
    assert (drift.ok, drift.action) == (True, "drift-corrected"), drift
    assert ctx.running_tag() == "v2"

    # Estado desejado defeituoso: falha, volta para a tag boa e NAO repete em laco
    # "bad" ja falhou no teste 3: o reconciliador recusa repetir, sem tocar na pilha
    declare("bad")
    refused = reconciler.reconcile()
    assert (refused.ok, refused.action) == (False, "skipped-failed"), refused
    assert ctx.running_tag() == "v2"

    declare("bad2")
    failed = reconciler.reconcile()
    assert (failed.ok, failed.action, failed.rolled_back_to) == (False, "failed", "v2"), failed
    assert ctx.running_tag() == "v2"
    assert ctx.api("/health/ready", None) == 200
    skipped = reconciler.reconcile()
    assert (skipped.ok, skipped.action) == (False, "skipped-failed")

    # Correcao no Git (volta para v1) e aplicada
    declare("v1")
    fixed = reconciler.reconcile()
    assert (fixed.ok, fixed.action) == (True, "applied"), fixed
    assert ctx.running_tag() == "v1"


def test_7_summary_is_recorded_for_the_evidence(ctx: Ctx) -> None:
    assert {
        "deploy_v1_s",
        "bad_release_and_auto_rollback_s",
        "manual_rollback_s",
        "rto_total_s",
    } <= set(ctx.timings)
