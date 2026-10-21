"""Reconciliador GitOps de modelo PULL (SPEC-012, REQ-OPS-003; D-047). So stdlib.

O host busca o estado DESEJADO no Git (`deploy/desired/<ambiente>.json`, lido do objeto Git, nao do
diretorio de trabalho) e converge a pilha para ele: idempotente, detecta *drift* (imagens em execucao
diferentes do registrado) e nao fica tentando em laco uma release que ja falhou. O arquivo vindo do Git e
dado NAO confiavel: so `tag` (validada), `backup` (bool) e `note` sao aceitos; qualquer outro campo
reprova a leitura inteira, e o conteudo invalido nunca e repetido na saida.
"""

import contextlib
import json
import os
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from spatial_ops.deploy import APP_SERVICES, DeployResult
from spatial_ops.runner import Runner
from spatial_ops.state import Store, validate_tag

_ENV = re.compile(r"[a-z0-9][a-z0-9_-]{0,30}")
_REMOTE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,50}")
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,100}")
_PATH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,200}")
_ALLOWED_KEYS = {"tag", "backup", "note"}
GIT_TIMEOUT_S = 120.0


class DesiredStateError(Exception):
    """Estado desejado ausente, malformado ou com campos fora do contrato."""


class GitError(Exception):
    """Falha ao falar com o Git. A mensagem nunca carrega a saida do comando (pode ter credenciais)."""


class LockHeldError(Exception):
    """Outra reconciliacao esta em andamento."""


@dataclass(frozen=True)
class Desired:
    tag: str
    backup: bool = False


def parse_desired(text: str) -> Desired:
    try:
        data = json.loads(text)
    except ValueError as error:
        raise DesiredStateError("desired state is not valid JSON") from error
    if not isinstance(data, dict) or "tag" not in data:
        raise DesiredStateError("desired state must be an object with a 'tag'")
    if not set(data) <= _ALLOWED_KEYS:
        raise DesiredStateError("desired state has unknown fields")
    tag, backup, note = data["tag"], data.get("backup", False), data.get("note", "")
    if not isinstance(tag, str) or not isinstance(backup, bool):
        raise DesiredStateError("desired state has fields of the wrong type")
    if not isinstance(note, str) or len(note) > 200:
        raise DesiredStateError("desired state note is invalid")
    try:
        validate_tag(tag)
    except ValueError as error:
        raise DesiredStateError("desired state tag is invalid") from error
    return Desired(tag, backup)


# --- Git ----------------------------------------------------------------------------------------------------


class GitSource(Protocol):
    def fetch(self) -> None: ...

    def read(self, path: str) -> str: ...

    def revision(self) -> str: ...


class GitCliSource:
    """`git` por argv (sem shell), com remoto, ref e caminho validados e fixos por construcao."""

    def __init__(self, runner: Runner, repo: Path, *, remote: str, ref: str) -> None:
        if not _REMOTE.fullmatch(remote):
            raise ValueError("invalid git remote")
        if not _REF.fullmatch(ref) or ".." in ref:
            raise ValueError("invalid git ref")
        self._runner = runner
        self._repo = repo
        self._remote = remote
        self._ref = ref

    def _git(self, *args: str) -> str:
        result = self._runner.run(
            ["git", "-C", str(self._repo), *args],
            env={"GIT_TERMINAL_PROMPT": "0"},
            timeout=GIT_TIMEOUT_S,
        )
        if not result.ok:
            raise GitError(f"git {args[0]} failed")
        return result.stdout

    def fetch(self) -> None:
        self._git("fetch", "--quiet", "--prune", self._remote)

    def read(self, path: str) -> str:
        if not _PATH.fullmatch(path) or ".." in path.split("/"):
            raise GitError("refused to read an unsafe path")
        return self._git("show", f"{self._ref}:{path}")

    def revision(self) -> str:
        return self._git("rev-parse", "--short=12", self._ref).strip()


# --- trava ----------------------------------------------------------------------------------------------------


@contextlib.contextmanager
def acquire_lock(
    path: Path, *, ttl_s: float, clock: Callable[[], float] = time.time
) -> Iterator[None]:
    """Trava por arquivo (O_EXCL). Uma trava mais velha que `ttl_s` e de uma execucao que morreu."""
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    for attempt in range(2):
        try:
            descriptor = os.open(path, flags)
            break
        except FileExistsError:
            try:
                age = clock() - path.stat().st_mtime
            except FileNotFoundError:
                continue
            if attempt == 1 or age <= ttl_s:
                raise LockHeldError("another reconciliation is running") from None
            path.unlink(missing_ok=True)
    else:  # pragma: no cover - o laco sempre sai por break ou raise
        raise LockHeldError("could not take the lock")
    try:
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)
        yield
    finally:
        path.unlink(missing_ok=True)


# --- reconciliador ------------------------------------------------------------------------------------------------


class _Deployer(Protocol):
    def running_images(self, tag: str) -> dict[str, str]: ...

    def deploy(self, tag: str, *, backup: bool = False) -> DeployResult: ...


@dataclass(frozen=True)
class ReconcileResult:
    ok: bool
    action: str  # in-sync | applied | drift-corrected | failed | skipped-failed | error
    desired: str | None = None
    revision: str | None = None
    detail: str = ""
    rolled_back_to: str | None = None


class Reconciler:
    def __init__(self, deployer: _Deployer, git: GitSource, store: Store, *, env: str) -> None:
        if not _ENV.fullmatch(env):
            raise ValueError("invalid environment name")
        self._deployer = deployer
        self._git = git
        self._store = store
        self._path = f"deploy/desired/{env}.json"

    def _failed_before(self, tag: str) -> bool:
        for event in reversed(self._store.load().history):
            if event.tag == tag and event.result in ("failed", "deployed"):
                return event.result == "failed"
        return False

    def reconcile(self, *, retry_failed: bool = False) -> ReconcileResult:
        try:
            self._git.fetch()
        except GitError:
            return ReconcileResult(False, "error", detail="fetch")
        try:
            revision = self._git.revision()
            desired = parse_desired(self._git.read(self._path))
        except GitError:
            return ReconcileResult(False, "error", detail="read")
        except DesiredStateError:
            return ReconcileResult(False, "error", detail="desired-state")

        state = self._store.load()
        images = self._deployer.running_images(desired.tag)
        matches = all(images.get(s, "").endswith(f":{desired.tag}") for s in APP_SERVICES)
        if state.current == desired.tag and matches:
            return ReconcileResult(True, "in-sync", desired.tag, revision)
        if self._failed_before(desired.tag) and not retry_failed:
            return ReconcileResult(
                False, "skipped-failed", desired.tag, revision, "previous attempt failed"
            )

        action = "drift-corrected" if state.current == desired.tag else "applied"
        result = self._deployer.deploy(desired.tag, backup=desired.backup)
        if result.ok:
            return ReconcileResult(True, action, desired.tag, revision)
        return ReconcileResult(
            False, "failed", desired.tag, revision, result.stage, result.rolled_back_to
        )
