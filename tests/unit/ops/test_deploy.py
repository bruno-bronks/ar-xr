"""SPEC-012 · REQ-OPS-001, REQ-OPS-002, REQ-OPS-007 (abuso): deploy por tag, verificacao e rollback (logica, com Runner falso).

O comportamento REAL (Docker, registry, release defeituosa) e provado em tests/integration/test_ops_e2e.py.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from spatial_ops.deploy import Deployer, EnvConfig, load_env_config, parse_env_text
from spatial_ops.runner import Result
from spatial_ops.state import Event, MemoryStore, State, StateStore, validate_tag

SERVICES = ("api", "worker", "simulator", "migrate")


class FakeRunner:
    """Simula docker compose: `up` troca a tag em execucao; tags em `bad_tags` falham no `up`."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, str]]] = []
        self.running: str | None = None
        self.bad_tags: set[str] = set()
        self.pull_fails: set[str] = set()
        self.ps_stale: bool = False

    def run(
        self,
        args: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        stdout_path: Path | None = None,
        stdin_path: Path | None = None,
    ) -> Result:
        argv, environment = list(args), dict(env or {})
        self.calls.append((argv, environment))
        tag = environment.get("IMAGE_TAG", "")
        if "pull" in argv:
            return Result(1, "", "pull failed") if tag in self.pull_fails else Result(0)
        if "up" in argv:
            self.running = tag
            return Result(1, "", "unhealthy") if tag in self.bad_tags else Result(0)
        if "ps" in argv:
            shown = "old" if self.ps_stale else self.running
            rows = [{"Service": s, "Image": f"reg/spatial-ai-{s}:{shown}"} for s in SERVICES]
            return Result(0, "\n".join(json.dumps(r) for r in rows))
        return Result(0)

    def commands(self, word: str) -> list[list[str]]:
        return [argv for argv, _ in self.calls if word in argv]


class FakeHttp:
    """A API `nao fica pronta` apenas enquanto roda uma tag de `unready_tags` (como uma release ruim)."""

    def __init__(self, runner: FakeRunner | None = None) -> None:
        self.runner = runner
        self.unready_tags: set[str] = set()
        self.equipment_status = 200
        self.requests: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: Mapping[str, str], timeout: float) -> tuple[int, str]:
        self.requests.append((url, dict(headers)))
        if url.endswith("/health/ready"):
            bad = self.runner is not None and self.runner.running in self.unready_tags
            return (503 if bad else 200), "{}"
        return self.equipment_status, "[]"


def _config(tmp_path: Path, **overrides: object) -> EnvConfig:
    base: dict[str, object] = {
        "name": "homolog",
        "compose_files": ("compose.yaml", "deploy/vps/compose.override.yaml"),
        "project": "spatial-homolog",
        "registry": "reg/",
        "api_url": "http://127.0.0.1:18088",
        "smoke_token": "demo-operator-a",
        "wait_seconds": 30,
        "smoke_seconds": 5,
        "env": {"API_PORT": "18088", "POSTGRES_PASSWORD": "segredo-que-nao-pode-vazar"},
        "workdir": tmp_path,
    }
    base.update(overrides)
    return EnvConfig(**base)  # type: ignore[arg-type]


def _deployer(
    tmp_path: Path, runner: FakeRunner, http: FakeHttp | None = None, **cfg: object
) -> tuple[Deployer, MemoryStore, FakeHttp]:
    """Logica com armazenamento em memoria: o os.replace do Windows pode levar ~3 s por gravacao."""
    store = MemoryStore()
    fake_http = http or FakeHttp()
    deployer = Deployer(
        _config(tmp_path, **cfg),
        runner,
        store,
        http=fake_http,
        clock=lambda: "2026-10-20T12:00:00Z",
        sleep=lambda _s: None,
    )
    return deployer, store, fake_http


def test_first_deploy_records_state_and_never_builds(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, store, _ = _deployer(tmp_path, runner)

    result = deployer.deploy("v1")

    assert result.ok
    state = store.load()
    assert (state.current, state.previous) == ("v1", None)
    assert [e.result for e in state.history] == ["deployed"]
    up = runner.commands("up")[0]
    assert "--no-build" in up
    assert "--wait" in up
    assert "--build" not in up
    assert up[:6] == [
        "docker",
        "compose",
        "-p",
        "spatial-homolog",
        "--project-directory",
        str(tmp_path),
    ]
    assert up.count("-f") == 2


def test_tag_and_registry_travel_in_the_environment_never_in_the_command(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, _, _ = _deployer(tmp_path, runner)

    deployer.deploy("v1")

    for argv, env in runner.calls:
        assert env["IMAGE_TAG"] == "v1"
        assert env["IMAGE_REGISTRY"] == "reg/"
        assert "segredo-que-nao-pode-vazar" not in " ".join(argv)  # segredos so no env
    assert any(
        env.get("POSTGRES_PASSWORD") == "segredo-que-nao-pode-vazar" for _, env in runner.calls
    )


def test_registry_triggers_a_pull_of_the_app_images_before_touching_the_stack(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()
    deployer, _, _ = _deployer(tmp_path, runner)

    deployer.deploy("v1")

    order = [
        ("pull" if "pull" in a else "up" if "up" in a else "ps" if "ps" in a else "?")
        for a, _ in runner.calls
    ]
    assert order.index("pull") < order.index("up")
    pull = runner.commands("pull")[0]
    assert pull[-3:] == ["api", "worker", "simulator"]


def test_no_registry_means_no_pull(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, _, _ = _deployer(tmp_path, runner, registry="")

    assert deployer.deploy("v1").ok
    assert runner.commands("pull") == []


def test_second_deploy_keeps_the_previous_tag_for_rollback(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, store, _ = _deployer(tmp_path, runner)
    deployer.deploy("v1")

    result = deployer.deploy("v2")

    assert result.ok
    state = store.load()
    assert (state.current, state.previous) == ("v2", "v1")


def test_redeploying_the_same_tag_converges_without_losing_the_previous(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, store, _ = _deployer(tmp_path, runner)
    deployer.deploy("v1")
    deployer.deploy("v2")

    deployer.deploy("v2")

    state = store.load()
    assert (state.current, state.previous) == ("v2", "v1")
    assert len(runner.commands("up")) == 3


def test_failed_up_rolls_back_automatically_to_the_previous_tag(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, store, _ = _deployer(tmp_path, runner)
    deployer.deploy("v1")
    runner.bad_tags.add("v2")

    result = deployer.deploy("v2")

    assert not result.ok
    assert result.rolled_back_to == "v1"
    assert runner.running == "v1"  # o ambiente voltou a rodar a tag boa
    state = store.load()
    assert (state.current, state.previous) == ("v1", None)
    assert [e.result for e in state.history] == ["deployed", "failed", "rolled_back"]


def test_failed_smoke_after_a_clean_up_also_rolls_back(tmp_path: Path) -> None:
    runner = FakeRunner()
    http = FakeHttp(runner)
    deployer, store, _ = _deployer(tmp_path, runner, http)
    deployer.deploy("v1")
    http.unready_tags.add("v2")  # a v2 sobe, mas a API nao fica pronta

    result = deployer.deploy("v2")

    assert not result.ok
    assert result.stage == "smoke"
    assert result.rolled_back_to == "v1"
    assert runner.running == "v1"
    assert store.load().current == "v1"


def test_unauthorized_equipment_smoke_fails_the_release(tmp_path: Path) -> None:
    runner = FakeRunner()
    http = FakeHttp()
    http.equipment_status = 401
    deployer, store, _ = _deployer(tmp_path, runner, http)

    result = deployer.deploy("v1")

    assert not result.ok
    assert store.load().current is None


def test_smoke_sends_the_token_only_in_the_header(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, _, http = _deployer(tmp_path, runner)

    deployer.deploy("v1")

    equipment = [r for r in http.requests if r[0].endswith("/api/v1/equipment")]
    assert equipment
    assert equipment[0][1]["Authorization"] == "Bearer demo-operator-a"
    assert all("demo-operator-a" not in url for url, _ in http.requests)


def test_wrong_image_running_is_a_failed_release(tmp_path: Path) -> None:
    """`up` retornou 0, mas os contêineres rodam outra tag (ex.: cache): nao vale como deploy."""
    runner = FakeRunner()
    runner.ps_stale = True
    deployer, store, _ = _deployer(tmp_path, runner)

    result = deployer.deploy("v1")

    assert not result.ok
    assert result.stage == "verify-images"
    assert store.load().current is None


def test_failed_pull_leaves_the_running_stack_untouched(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, store, _ = _deployer(tmp_path, runner)
    deployer.deploy("v1")
    runner.pull_fails.add("v2")
    ups_before = len(runner.commands("up"))

    result = deployer.deploy("v2")

    assert not result.ok
    assert result.stage == "pull"
    assert result.rolled_back_to is None
    assert len(runner.commands("up")) == ups_before  # nem tentou subir
    assert runner.running == "v1"
    assert store.load().current == "v1"
    assert store.load().history[-1].result == "failed"


def test_first_deploy_failure_has_nothing_to_roll_back_to(tmp_path: Path) -> None:
    runner = FakeRunner()
    runner.bad_tags.add("v1")
    deployer, store, _ = _deployer(tmp_path, runner)

    result = deployer.deploy("v1")

    assert not result.ok
    assert result.rolled_back_to is None
    assert store.load().current is None
    assert len(runner.commands("up")) == 1


def test_rollback_that_also_fails_is_reported_and_recorded(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, store, _ = _deployer(tmp_path, runner)
    deployer.deploy("v1")
    runner.bad_tags.update({"v1", "v2"})  # a tag anterior tambem quebra

    result = deployer.deploy("v2")

    assert not result.ok
    assert result.rolled_back_to is None
    assert result.stage == "rollback"
    assert store.load().history[-1].result == "rollback_failed"


def test_manual_rollback_swaps_current_and_previous(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, store, _ = _deployer(tmp_path, runner)
    deployer.deploy("v1")
    deployer.deploy("v2")

    result = deployer.rollback()

    assert result.ok
    assert runner.running == "v1"
    state = store.load()
    assert (state.current, state.previous) == ("v1", "v2")  # permite "avancar" de volta
    assert state.history[-1].result == "rollback"


def test_manual_rollback_without_a_previous_tag_is_refused(tmp_path: Path) -> None:
    runner = FakeRunner()
    deployer, _, _ = _deployer(tmp_path, runner)
    deployer.deploy("v1")

    result = deployer.rollback()

    assert not result.ok
    assert result.stage == "no-previous"
    assert len(runner.commands("up")) == 1


@pytest.mark.parametrize(
    "tag", ["", " ", "v1;rm -rf /", "../x", "a b", "x" * 65, "-lead", "v1\nv2", "v1$(id)", "‮v1"]
)
def test_unsafe_tags_are_rejected_before_any_command_runs(tmp_path: Path, tag: str) -> None:
    runner = FakeRunner()
    deployer, _, _ = _deployer(tmp_path, runner)

    with pytest.raises(ValueError, match="invalid image tag"):
        deployer.deploy(tag)

    assert runner.calls == []


@pytest.mark.parametrize("tag", ["v1", "1.2.3", "sha-1a2b3c4", "main_2026-10-20", "A" * 64])
def test_normal_tags_are_accepted(tag: str) -> None:
    assert validate_tag(tag) == tag


def test_backup_hook_runs_first_and_a_failing_backup_aborts_the_deploy(tmp_path: Path) -> None:
    runner = FakeRunner()
    store = MemoryStore()
    order: list[str] = []

    def failing_backup() -> None:
        order.append("backup")
        raise RuntimeError("backup falhou")

    deployer = Deployer(
        _config(tmp_path),
        runner,
        store,
        http=FakeHttp(),
        clock=lambda: "t",
        sleep=lambda _s: None,
        backup=failing_backup,
    )

    result = deployer.deploy("v1", backup=True)

    assert not result.ok
    assert result.stage == "backup"
    assert order == ["backup"]
    assert runner.calls == []  # nada foi tocado


def test_backup_hook_is_skipped_unless_requested(tmp_path: Path) -> None:
    runner = FakeRunner()
    called: list[bool] = []
    deployer = Deployer(
        _config(tmp_path),
        runner,
        MemoryStore(),
        http=FakeHttp(),
        clock=lambda: "t",
        sleep=lambda _s: None,
        backup=lambda: called.append(True),
    )

    deployer.deploy("v1")
    assert called == []
    deployer.deploy("v2", backup=True)
    assert called == [True]


def test_history_is_bounded_in_both_stores(tmp_path: Path) -> None:
    events = [Event(f"v{i}", "t", "deployed") for i in range(130)]
    for store in (MemoryStore(), StateStore(tmp_path / "state.json")):
        store.save(State(current="v129", history=list(events)))

        loaded = store.load()

        assert len(loaded.history) == 100
        assert loaded.history[0].tag == "v30"  # mantem os mais recentes


def test_real_state_file_roundtrip_is_atomic_and_leaves_no_temp_file(tmp_path: Path) -> None:
    runner = FakeRunner()
    store = StateStore(tmp_path / "state.json")
    deployer = Deployer(
        _config(tmp_path), runner, store, http=FakeHttp(), clock=lambda: "t", sleep=lambda _s: None
    )

    deployer.deploy("v1")

    assert not (tmp_path / "state.json.tmp").exists()
    data = json.loads((tmp_path / "state.json").read_text("utf-8"))
    assert data["current"] == "v1"
    assert StateStore(tmp_path / "state.json").load().current == "v1"


# --- configuracao do ambiente -------------------------------------------------------------------


def test_env_text_parsing_handles_comments_blank_lines_and_values_with_equals() -> None:
    parsed = parse_env_text("# c\n\nA=1\nB = dois \nURL=postgres://u:p@h/db?x=1\nVAZIA=\n")

    assert parsed == {"A": "1", "B": "dois", "URL": "postgres://u:p@h/db?x=1", "VAZIA": ""}


def test_env_text_rejects_lines_without_equals() -> None:
    with pytest.raises(ValueError, match="line 2"):
        parse_env_text("A=1\nlinha-sem-igual\n")


def test_load_env_config_splits_reserved_keys_from_compose_env(tmp_path: Path) -> None:
    path = tmp_path / "homolog.env"
    path.write_text(
        "OPS_COMPOSE_FILES=compose.yaml, deploy/vps/compose.override.yaml\nOPS_PROJECT=spatial-homolog\n"
        "OPS_REGISTRY=localhost:5000/\nOPS_API_URL=http://127.0.0.1:18088\nOPS_SMOKE_TOKEN=demo-operator-a\n"
        "OPS_WAIT_SECONDS=90\nAPI_PORT=18088\n",
        "utf-8",
    )

    config = load_env_config(path, tmp_path)

    assert config.name == "homolog"
    assert config.compose_files == ("compose.yaml", "deploy/vps/compose.override.yaml")
    assert (config.project, config.registry, config.api_url) == (
        "spatial-homolog",
        "localhost:5000/",
        "http://127.0.0.1:18088",
    )
    assert config.smoke_token == "demo-operator-a"
    assert config.wait_seconds == 90
    assert config.env == {"API_PORT": "18088"}  # reservadas nao vao para o Compose


@pytest.mark.parametrize("missing", ["OPS_COMPOSE_FILES", "OPS_PROJECT", "OPS_API_URL"])
def test_load_env_config_requires_the_essential_keys(tmp_path: Path, missing: str) -> None:
    values = {
        "OPS_COMPOSE_FILES": "compose.yaml",
        "OPS_PROJECT": "p",
        "OPS_API_URL": "http://127.0.0.1:1",
    }
    del values[missing]
    path = tmp_path / "x.env"
    path.write_text("".join(f"{k}={v}\n" for k, v in values.items()), "utf-8")

    with pytest.raises(ValueError, match=missing):
        load_env_config(path, tmp_path)


@pytest.mark.parametrize("registry", ["localhost:5000", "reg/ x/", "reg;x/", "https://reg/"])
def test_registry_must_be_a_host_prefix_ending_with_a_slash_or_empty(
    tmp_path: Path, registry: str
) -> None:
    path = tmp_path / "x.env"
    path.write_text(
        f"OPS_COMPOSE_FILES=compose.yaml\nOPS_PROJECT=p\nOPS_API_URL=http://127.0.0.1:1\nOPS_REGISTRY={registry}\n",
        "utf-8",
    )

    with pytest.raises(ValueError, match="OPS_REGISTRY"):
        load_env_config(path, tmp_path)


@pytest.mark.parametrize("project", ["Spatial", "a b", "", "-x", "a;b", "a" * 64])
def test_project_name_must_be_a_safe_compose_project(tmp_path: Path, project: str) -> None:
    path = tmp_path / "x.env"
    path.write_text(
        f"OPS_COMPOSE_FILES=compose.yaml\nOPS_PROJECT={project}\nOPS_API_URL=http://127.0.0.1:1\n",
        "utf-8",
    )

    with pytest.raises(ValueError, match="OPS_PROJECT"):
        load_env_config(path, tmp_path)


@pytest.mark.parametrize(
    "files",
    [
        "../../etc/passwd",
        "/etc/passwd",
        "C:/Windows/x.yaml",
        "compose.yaml,../x.yaml",
        "compose.txt",
        "a b.yaml",
        "-f.yaml",
    ],
)
def test_compose_files_must_stay_inside_the_repository_and_be_yaml(
    tmp_path: Path, files: str
) -> None:
    """Abuso: arquivo .env adulterado nao pode apontar o Compose para fora do repositorio."""
    path = tmp_path / "x.env"
    path.write_text(
        f"OPS_COMPOSE_FILES={files}\nOPS_PROJECT=p\nOPS_API_URL=http://127.0.0.1:1\n", "utf-8"
    )

    with pytest.raises(ValueError, match="OPS_COMPOSE_FILES"):
        load_env_config(path, tmp_path)


def test_an_env_file_cannot_override_the_image_tag_or_registry_chosen_by_the_deploy(
    tmp_path: Path,
) -> None:
    """Abuso: IMAGE_TAG/IMAGE_REGISTRY no .env nao podem sobrepor a tag verificada pelo deploy."""
    runner = FakeRunner()
    deployer, _, _ = _deployer(
        tmp_path, runner, env={"IMAGE_TAG": "evil", "IMAGE_REGISTRY": "evil.example/"}
    )

    deployer.deploy("v1")

    up_env = next(env for argv, env in runner.calls if "up" in argv)
    assert (up_env["IMAGE_TAG"], up_env["IMAGE_REGISTRY"]) == ("v1", "reg/")


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://example.test/x", "gopher://x", "//x/y"]
)
def test_the_default_http_probe_refuses_non_http_schemes(url: str) -> None:
    """Abuso/SAST (Semgrep dynamic-urllib): o smoke nunca abre file:// nem outros esquemas."""
    from spatial_ops.deploy import _urllib_get

    assert _urllib_get(url, {}, 1.0) == (0, "")
