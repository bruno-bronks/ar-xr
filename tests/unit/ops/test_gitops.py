"""SPEC-012 · REQ-OPS-003, REQ-OPS-007 (abuso): reconciliador GitOps (pull). Logica com Git e Deployer falsos; o `git` real e
exercitado em `test_git_cli_source_reads_the_desired_state_from_a_real_repository`."""

import json
import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from spatial_ops.deploy import DeployResult
from spatial_ops.gitops import (
    DesiredStateError,
    GitCliSource,
    GitError,
    LockHeldError,
    Reconciler,
    acquire_lock,
    parse_desired,
)
from spatial_ops.runner import Result, SubprocessRunner
from spatial_ops.state import Event, MemoryStore

# --- estado desejado (dado nao confiavel que vem do Git) ---------------------------------------------


def test_parse_desired_accepts_a_tag_and_optional_flags() -> None:
    desired = parse_desired('{"tag": "v1.2.3", "backup": true, "note": "release de outubro"}')

    assert (desired.tag, desired.backup) == ("v1.2.3", True)
    assert parse_desired('{"tag": "v2"}').backup is False


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json",
        "[]",
        '{"tag": ""}',
        '{"tag": 5}',
        '{"tag": "v1; rm -rf /"}',
        '{"tag": "../../etc"}',
        '{"tag": "v1", "backup": "yes"}',
        '{"tag": "v1", "command": "curl evil | sh"}',  # campo desconhecido e rejeitado, nunca ignorado
        '{"backup": true}',
    ],
)
def test_parse_desired_rejects_anything_else(text: str) -> None:
    with pytest.raises(DesiredStateError):
        parse_desired(text)


# --- reconciliacao -------------------------------------------------------------------------------------


class FakeGit:
    def __init__(self, desired: str = '{"tag": "v2"}') -> None:
        self.desired = desired
        self.fetches = 0
        self.fail_fetch = False
        self.fail_read = False
        self.read_paths: list[str] = []

    def fetch(self) -> None:
        self.fetches += 1
        if self.fail_fetch:
            raise GitError("fetch failed")

    def read(self, path: str) -> str:
        self.read_paths.append(path)
        if self.fail_read:
            raise GitError("no such file")
        return self.desired

    def revision(self) -> str:
        return "abc1234"


class FakeDeployer:
    """Mesma superficie que o Reconciler usa do `Deployer`; guarda o estado como o real."""

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.running: dict[str, str] = {}
        self.deploys: list[tuple[str, bool]] = []
        self.bad_tags: set[str] = set()

    def running_images(self, tag: str) -> dict[str, str]:
        return dict(self.running)

    def deploy(self, tag: str, *, backup: bool = False) -> DeployResult:
        self.deploys.append((tag, backup))
        state = self.store.load()
        if tag in self.bad_tags:
            state.history.append(Event(tag, "t", "failed", "smoke"))
            self.store.save(state)
            return DeployResult(False, tag, "smoke", rolled_back_to=state.current)
        if state.current != tag:
            state.previous, state.current = state.current, tag
        state.history.append(Event(tag, "t", "deployed"))
        self.store.save(state)
        self.running = {s: f"reg/spatial-ai-{s}:{tag}" for s in ("api", "worker", "simulator")}
        return DeployResult(True, tag, "deployed")


def _reconciler(
    git: FakeGit | None = None, store: MemoryStore | None = None
) -> tuple[Reconciler, FakeGit, FakeDeployer, MemoryStore]:
    store = store or MemoryStore()
    git = git or FakeGit()
    deployer = FakeDeployer(store)
    return Reconciler(deployer, git, store, env="homolog"), git, deployer, store


def test_first_reconcile_applies_the_desired_tag() -> None:
    reconciler, git, deployer, _ = _reconciler()

    result = reconciler.reconcile()

    assert result.ok
    assert (result.action, result.desired, result.revision) == ("applied", "v2", "abc1234")
    assert deployer.deploys == [("v2", False)]
    assert git.fetches == 1


def test_reconcile_is_idempotent_when_already_in_sync() -> None:
    reconciler, _, deployer, _ = _reconciler()
    reconciler.reconcile()

    again = reconciler.reconcile()

    assert (again.ok, again.action) == (True, "in-sync")
    assert deployer.deploys == [("v2", False)]  # nenhum deploy novo


def test_a_new_desired_tag_in_git_triggers_exactly_one_deploy() -> None:
    reconciler, git, deployer, store = _reconciler()
    reconciler.reconcile()
    git.desired = '{"tag": "v3"}'

    result = reconciler.reconcile()
    reconciler.reconcile()

    assert (result.ok, result.action) == (True, "applied")
    assert [t for t, _ in deployer.deploys] == ["v2", "v3"]
    assert (store.load().current, store.load().previous) == ("v3", "v2")


def test_drift_is_detected_and_corrected_when_running_images_differ_from_the_record() -> None:
    reconciler, _, deployer, _ = _reconciler()
    reconciler.reconcile()
    deployer.running["api"] = "reg/spatial-ai-api:hotfix-manual"  # alguem mexeu a mao

    result = reconciler.reconcile()

    assert (result.ok, result.action) == (True, "drift-corrected")
    assert [t for t, _ in deployer.deploys] == ["v2", "v2"]


def test_a_stack_that_is_down_counts_as_drift() -> None:
    reconciler, _, deployer, _ = _reconciler()
    reconciler.reconcile()
    deployer.running = {}

    assert reconciler.reconcile().action == "drift-corrected"


def test_a_failed_release_is_not_retried_in_a_loop() -> None:
    reconciler, _, deployer, _ = _reconciler()
    deployer.bad_tags.add("v2")

    first = reconciler.reconcile()
    second = reconciler.reconcile()

    assert (first.ok, first.action) == (False, "failed")
    assert (second.ok, second.action) == (False, "skipped-failed")
    assert len(deployer.deploys) == 1  # a segunda rodada nao tentou de novo


def test_retry_failed_forces_another_attempt() -> None:
    reconciler, _, deployer, _ = _reconciler()
    deployer.bad_tags.add("v2")
    reconciler.reconcile()
    deployer.bad_tags.clear()

    result = reconciler.reconcile(retry_failed=True)

    assert (result.ok, result.action) == (True, "applied")
    assert len(deployer.deploys) == 2


def test_fixing_git_to_a_different_tag_clears_the_failure_back_off() -> None:
    reconciler, git, deployer, _ = _reconciler()
    deployer.bad_tags.add("v2")
    reconciler.reconcile()
    git.desired = '{"tag": "v3"}'

    assert reconciler.reconcile().action == "applied"


def test_backup_flag_from_git_is_forwarded_to_the_deploy() -> None:
    reconciler, _, deployer, _ = _reconciler(FakeGit('{"tag": "v2", "backup": true}'))

    reconciler.reconcile()

    assert deployer.deploys == [("v2", True)]


def test_fetch_failure_changes_nothing() -> None:
    reconciler, git, deployer, _ = _reconciler()
    git.fail_fetch = True

    result = reconciler.reconcile()

    assert (result.ok, result.action) == (False, "error")
    assert result.detail == "fetch"
    assert deployer.deploys == []


def test_invalid_desired_state_changes_nothing_and_does_not_echo_the_content() -> None:
    reconciler, _, deployer, _ = _reconciler(FakeGit('{"tag": "v1", "command": "curl evil | sh"}'))

    result = reconciler.reconcile()

    assert (result.ok, result.action, result.detail) == (False, "error", "desired-state")
    assert deployer.deploys == []
    assert "curl" not in json.dumps(result.__dict__)


def test_only_the_environment_file_is_read_from_git() -> None:
    reconciler, git, _, _ = _reconciler()

    reconciler.reconcile()

    assert git.read_paths == ["deploy/desired/homolog.json"]


def test_environment_name_cannot_escape_the_desired_directory() -> None:
    with pytest.raises(ValueError, match="environment"):
        Reconciler(FakeDeployer(MemoryStore()), FakeGit(), MemoryStore(), env="../secrets")


# --- trava de execucao ---------------------------------------------------------------------------------------


def _take_and_release(path: Path, now: float) -> None:
    with acquire_lock(path, ttl_s=600, clock=lambda: now):
        pass


def test_lock_prevents_two_reconcilers_at_once(tmp_path: Path) -> None:
    path = tmp_path / "gitops.lock"

    with acquire_lock(path, ttl_s=600, clock=lambda: 1000.0), pytest.raises(LockHeldError):
        _take_and_release(path, now=1001.0)

    with acquire_lock(path, ttl_s=600, clock=lambda: 1002.0):  # liberada ao sair
        pass


def test_a_stale_lock_from_a_crashed_run_is_taken_over(tmp_path: Path) -> None:
    path = tmp_path / "gitops.lock"
    path.write_text("999999", "utf-8")
    os.utime(path, (1000.0, 1000.0))

    with acquire_lock(path, ttl_s=60, clock=lambda: 2000.0):
        assert path.exists()


def test_lock_is_released_even_if_the_work_raises(tmp_path: Path) -> None:
    path = tmp_path / "gitops.lock"

    with pytest.raises(RuntimeError), acquire_lock(path, ttl_s=60, clock=lambda: 1.0):
        raise RuntimeError("boom")

    assert not path.exists()


# --- fonte Git real ---------------------------------------------------------------------------------------------------


class RecordingRunner:
    def __init__(self, results: Sequence[Result]) -> None:
        self.results = list(results)
        self.calls: list[list[str]] = []

    def run(
        self,
        args: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        stdout_path: Path | None = None,
        stdin_path: Path | None = None,
    ) -> Result:
        self.calls.append(list(args))
        return self.results.pop(0)


def test_git_cli_source_never_uses_a_shell_and_pins_remote_and_ref(tmp_path: Path) -> None:
    runner = RecordingRunner([Result(0), Result(0, '{"tag": "v1"}'), Result(0, "abc1234\n")])
    source = GitCliSource(runner, tmp_path, remote="origin", ref="origin/main")

    source.fetch()
    content = source.read("deploy/desired/homolog.json")
    revision = source.revision()

    assert content == '{"tag": "v1"}'
    assert revision == "abc1234"
    assert runner.calls[0] == ["git", "-C", str(tmp_path), "fetch", "--quiet", "--prune", "origin"]
    assert runner.calls[1] == [
        "git", "-C", str(tmp_path), "show", "origin/main:deploy/desired/homolog.json",
    ]  # fmt: skip
    assert runner.calls[2] == ["git", "-C", str(tmp_path), "rev-parse", "--short=12", "origin/main"]


@pytest.mark.parametrize("ref", ["main; rm -rf /", "-evil", "a b", "../x", ""])
def test_git_cli_source_rejects_hostile_refs(tmp_path: Path, ref: str) -> None:
    with pytest.raises(ValueError, match="ref"):
        GitCliSource(RecordingRunner([]), tmp_path, remote="origin", ref=ref)


@pytest.mark.parametrize("path", ["../secrets", "/etc/passwd", "deploy/../../x", "a b", "-x"])
def test_git_cli_source_rejects_hostile_paths(tmp_path: Path, path: str) -> None:
    source = GitCliSource(
        RecordingRunner([Result(0, "x")]), tmp_path, remote="origin", ref="origin/main"
    )

    with pytest.raises(GitError):
        source.read(path)


def test_git_failures_raise_without_leaking_the_command_output(tmp_path: Path) -> None:
    runner = RecordingRunner(
        [Result(128, "", "fatal: could not read Username for 'https://token@host'")]
    )
    source = GitCliSource(runner, tmp_path, remote="origin", ref="origin/main")

    with pytest.raises(GitError) as raised:
        source.fetch()

    assert "token@host" not in str(raised.value)


@pytest.mark.skipif(shutil.which("git") is None, reason="git indisponivel")
def test_git_cli_source_reads_the_desired_state_from_a_real_repository(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    clone = tmp_path / "clone"

    def git(*args: str, cwd: Path) -> None:
        subprocess.run(  # noqa: S603
            ["git", "-c", "user.email=t@example.test", "-c", "user.name=t", *args],  # noqa: S607
            cwd=cwd, check=True, capture_output=True,
        )  # fmt: skip

    git("init", "--bare", "-b", "main", str(remote), cwd=tmp_path)
    git("clone", str(remote), str(work), cwd=tmp_path)
    (work / "deploy" / "desired").mkdir(parents=True)
    (work / "deploy" / "desired" / "homolog.json").write_text('{"tag": "v7"}', "utf-8")
    git("add", ".", cwd=work)
    git("commit", "-m", "desired v7", cwd=work)
    git("push", "origin", "HEAD:main", cwd=work)
    git("clone", str(remote), str(clone), cwd=tmp_path)

    source = GitCliSource(SubprocessRunner(), clone, remote="origin", ref="origin/main")
    source.fetch()

    assert parse_desired(source.read("deploy/desired/homolog.json")).tag == "v7"
    assert len(source.revision()) == 12

    # um novo commit no remoto so e visto depois do fetch (o que o reconciliador faz a cada rodada)
    (work / "deploy" / "desired" / "homolog.json").write_text('{"tag": "v8"}', "utf-8")
    git("commit", "-am", "desired v8", cwd=work)
    git("push", "origin", "HEAD:main", cwd=work)
    assert parse_desired(source.read("deploy/desired/homolog.json")).tag == "v7"
    source.fetch()
    assert parse_desired(source.read("deploy/desired/homolog.json")).tag == "v8"


# --- contrato JSON Schema == parser (REQ-OPS-003) ---------------------------------------------------------------------

SCHEMA = Path(__file__).resolve().parents[3] / "specs" / "contracts" / "desired-state.schema.json"

CASES = [
    '{"tag": "v1"}',
    '{"tag": "v1", "backup": true, "note": "x"}',
    '{"tag": "v1", "extra": 1}',
    '{"tag": ""}',
    '{"tag": "-v1"}',
    '{"tag": "v1", "backup": "yes"}',
    '{"tag": "v1", "note": 5}',
    '{"tag": "' + "a" * 65 + '"}',
    '{"backup": true}',
    "[]",
]


@pytest.mark.parametrize("text", CASES)
def test_the_published_json_schema_and_the_parser_agree(text: str) -> None:
    import jsonschema

    schema = json.loads(SCHEMA.read_text("utf-8"))
    schema_ok = jsonschema.Draft202012Validator(schema).is_valid(json.loads(text))
    try:
        parse_desired(text)
        parser_ok = True
    except DesiredStateError:
        parser_ok = False

    assert schema_ok == parser_ok, text
