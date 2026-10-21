"""Deploy por tag com verificacao e rollback automatico (SPEC-012, REQ-OPS-001/002). So stdlib.

Fluxo de `deploy(tag)`: valida a tag -> (backup opcional) -> `pull` -> `up -d --no-build --wait` ->
confere que os conteineres rodam MESMO a tag pedida -> smoke HTTP. Qualquer falha apos tocar a pilha
volta, automaticamente, para a ultima tag boa. A tag e o registry viajam no AMBIENTE do processo
(nunca na linha de comando) e segredos do ambiente nunca sao registrados.

LIMITE: o rollback troca imagens; NAO desfaz migracoes de banco (Alembic e so para frente). Migracoes
precisam ser retrocompativeis (expandir/contrair) e o `--backup` existe para os casos em que nao sao.
"""

import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from spatial_ops.runner import Result, Runner
from spatial_ops.state import Event, State, Store, validate_tag

APP_SERVICES = ("api", "worker", "simulator")
_REGISTRY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*(/[A-Za-z0-9._-]+)*/")
_PROJECT = re.compile(r"[a-z0-9][a-z0-9_-]{0,62}")
_COMPOSE_FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./-]{0,120}\.ya?ml")
_RESERVED = {
    "OPS_COMPOSE_FILES", "OPS_PROJECT", "OPS_REGISTRY", "OPS_API_URL", "OPS_SMOKE_TOKEN",
    "OPS_WAIT_SECONDS", "OPS_SMOKE_SECONDS",
}  # fmt: skip

Http = Callable[[str, Mapping[str, str], float], tuple[int, str]]


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not key.strip():
            raise ValueError(f"invalid env line {number}")
        values[key.strip()] = value.strip()
    return values


@dataclass(frozen=True)
class EnvConfig:
    name: str
    compose_files: tuple[str, ...]
    project: str
    registry: str
    api_url: str
    smoke_token: str | None
    wait_seconds: int
    smoke_seconds: int
    env: Mapping[str, str] = field(default_factory=dict)
    workdir: Path = Path(".")


def load_env_config(path: Path, workdir: Path) -> EnvConfig:
    values = parse_env_text(path.read_text("utf-8"))
    for key in ("OPS_COMPOSE_FILES", "OPS_PROJECT", "OPS_API_URL"):
        if not values.get(key):
            raise ValueError(f"missing {key}")
    registry = values.get("OPS_REGISTRY", "")
    if registry and not _REGISTRY.fullmatch(registry):
        raise ValueError("OPS_REGISTRY must be a host/path prefix ending with '/'")
    compose_files = tuple(f.strip() for f in values["OPS_COMPOSE_FILES"].split(",") if f.strip())
    if not compose_files or any(
        not _COMPOSE_FILE.fullmatch(f) or ".." in f.split("/") for f in compose_files
    ):
        raise ValueError(
            "OPS_COMPOSE_FILES must be relative .yaml/.yml paths inside the repository"
        )
    if not _PROJECT.fullmatch(values["OPS_PROJECT"]):
        raise ValueError("OPS_PROJECT must be a lowercase compose project name")
    if not re.fullmatch(r"https?://[A-Za-z0-9.\-:\[\]]+(/.*)?", values["OPS_API_URL"]):
        raise ValueError("OPS_API_URL must be an http(s) URL")
    return EnvConfig(
        name=path.stem,
        compose_files=compose_files,
        project=values["OPS_PROJECT"],
        registry=registry,
        api_url=values["OPS_API_URL"].rstrip("/"),
        smoke_token=values.get("OPS_SMOKE_TOKEN") or None,
        wait_seconds=int(values.get("OPS_WAIT_SECONDS", "120")),
        smoke_seconds=int(values.get("OPS_SMOKE_SECONDS", "60")),
        env={k: v for k, v in values.items() if k not in _RESERVED},
        workdir=workdir,
    )


@dataclass(frozen=True)
class DeployResult:
    ok: bool
    tag: str
    stage: str  # deployed | backup | pull | up | verify-images | smoke | rollback | no-previous
    rolled_back_to: str | None = None
    message: str = ""


def _urllib_get(url: str, headers: Mapping[str, str], timeout: float) -> tuple[int, str]:
    if not url.startswith(("http://", "https://")):  # urllib tambem abriria file://
        return 0, ""
    request = urllib.request.Request(url, headers=dict(headers), method="GET")  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return int(response.status), response.read(65536).decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, ""
    except (urllib.error.URLError, OSError):
        return 0, ""


def compose_base(config: EnvConfig) -> list[str]:
    """Prefixo `docker compose -p ... --project-directory ... -f ...` (sem shell, sem segredos).

    Os arquivos `-f` sao resolvidos contra `workdir`, para o resultado nao depender do cwd.
    """
    base = ["docker", "compose", "-p", config.project, "--project-directory", str(config.workdir)]
    for file in config.compose_files:
        base += ["-f", str(config.workdir / file)]
    return base


class Deployer:
    def __init__(
        self,
        config: EnvConfig,
        runner: Runner,
        store: Store,
        *,
        http: Http | None = None,
        clock: Callable[[], str] | None = None,
        sleep: Callable[[float], None] | None = None,
        backup: Callable[[], None] | None = None,
    ) -> None:
        import time

        self._config = config
        self._runner = runner
        self._store = store
        self._http: Http = http or _urllib_get
        self._clock = clock or (lambda: datetime.now(UTC).isoformat(timespec="seconds"))
        self._sleep = sleep or time.sleep
        self._backup = backup

    # --- comandos ---------------------------------------------------------------------------

    def _compose(self, *args: str) -> list[str]:
        return [*compose_base(self._config), *args]

    def _env(self, tag: str) -> dict[str, str]:
        return {**self._config.env, "IMAGE_TAG": tag, "IMAGE_REGISTRY": self._config.registry}

    def _run(self, tag: str, *args: str, timeout: float | None = None) -> Result:
        return self._runner.run(self._compose(*args), env=self._env(tag), timeout=timeout)

    def _up(self, tag: str) -> Result:
        wait = self._config.wait_seconds
        return self._run(
            tag, "up", "-d", "--no-build", "--wait", "--wait-timeout", str(wait), timeout=wait + 120
        )

    def running_images(self, tag: str) -> dict[str, str]:
        result = self._run(tag, "ps", "--format", "json")
        text = result.stdout.strip()
        if not result.ok or not text:
            return {}
        rows = (
            json.loads(text)
            if text.startswith("[")
            else [json.loads(line) for line in text.splitlines() if line.strip()]
        )
        return {str(r["Service"]): str(r["Image"]) for r in rows}

    def _images_match(self, tag: str) -> bool:
        images = self.running_images(tag)
        return all(images.get(s, "").endswith(f":{tag}") for s in APP_SERVICES)

    def _smoke(self) -> bool:
        attempts = max(1, self._config.smoke_seconds)
        for attempt in range(attempts):
            status, _ = self._http(f"{self._config.api_url}/health/ready", {}, 5.0)
            if status == 200:
                break
            if attempt + 1 < attempts:
                self._sleep(1.0)
        else:
            return False
        if self._config.smoke_token:
            headers = {"Authorization": f"Bearer {self._config.smoke_token}"}
            status, _ = self._http(f"{self._config.api_url}/api/v1/equipment", headers, 5.0)
            return status == 200
        return True

    def _converge(self, tag: str) -> tuple[bool, str]:
        """Sobe `tag` e verifica. Devolve (ok, estagio da falha)."""
        if not self._up(tag).ok:
            return False, "up"
        if not self._images_match(tag):
            return False, "verify-images"
        if not self._smoke():
            return False, "smoke"
        return True, "deployed"

    def _record(self, state: State, tag: str, result: str, detail: str = "") -> None:
        state.history.append(Event(tag, self._clock(), result, detail))

    # --- operacoes publicas -----------------------------------------------------------------

    def deploy(self, tag: str, *, backup: bool = False) -> DeployResult:
        validate_tag(tag)
        state = self._store.load()
        if backup and self._backup is not None:
            try:
                self._backup()
            except Exception as error:  # qualquer falha de backup aborta ANTES de tocar a pilha
                self._record(state, tag, "failed", f"backup: {type(error).__name__}")
                self._store.save(state)
                return DeployResult(
                    False, tag, "backup", message="backup failed; nothing was changed"
                )
        if self._config.registry and not self._run(tag, "pull", *APP_SERVICES).ok:
            self._record(state, tag, "failed", "pull")
            self._store.save(state)
            return DeployResult(False, tag, "pull", message="pull failed; running stack untouched")

        ok, stage = self._converge(tag)
        if ok:
            if state.current != tag:
                state.previous, state.current = state.current, tag
            self._record(state, tag, "deployed")
            self._store.save(state)
            return DeployResult(True, tag, "deployed")

        self._record(state, tag, "failed", stage)
        target = state.current if state.current != tag else state.previous
        if target is None:
            self._store.save(state)
            return DeployResult(False, tag, stage, message="no previous tag to roll back to")
        back_ok, _ = self._converge(target)
        if back_ok:
            self._record(state, target, "rolled_back", f"after failed {tag} ({stage})")
            self._store.save(state)
            return DeployResult(False, tag, stage, rolled_back_to=target)
        self._record(state, target, "rollback_failed", f"after failed {tag}")
        self._store.save(state)
        return DeployResult(
            False, tag, "rollback", message="rollback ALSO failed: manual intervention required"
        )

    def rollback(self) -> DeployResult:
        state = self._store.load()
        target = state.previous
        if target is None:
            return DeployResult(
                False, state.current or "", "no-previous", message="no previous tag recorded"
            )
        ok, _ = self._converge(target)
        if not ok:
            self._record(state, target, "rollback_failed", "manual rollback")
            self._store.save(state)
            return DeployResult(
                False, target, "rollback", message="rollback failed: manual intervention required"
            )
        state.previous, state.current = state.current, target
        self._record(state, target, "rollback", "manual")
        self._store.save(state)
        return DeployResult(True, target, "deployed", rolled_back_to=target)

    def status(self) -> dict[str, object]:
        state = self._store.load()
        tag = state.current or "latest"
        return {
            "environment": self._config.name,
            "current": state.current,
            "previous": state.previous,
            "running_images": self.running_images(tag) if state.current else {},
            "last_events": [vars(e) for e in state.history[-5:]],
        }
