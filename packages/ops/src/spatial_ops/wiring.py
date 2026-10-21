"""Composicao dos objetos de operacao a partir de `deploy/envs/<ambiente>.env` (usada pelos CLIs)."""

import re
from pathlib import Path

from spatial_ops.backup import BackupService
from spatial_ops.deploy import Deployer, EnvConfig, load_env_config
from spatial_ops.runner import SubprocessRunner
from spatial_ops.state import StateStore

_ENV = re.compile(r"[a-z0-9][a-z0-9_-]{0,30}")


def env_config(root: Path, env: str) -> EnvConfig:
    if not _ENV.fullmatch(env):
        raise SystemExit(f"nome de ambiente invalido: {env!r}")
    path = root / "deploy" / "envs" / f"{env}.env"
    if not path.is_file():
        raise SystemExit(f"ambiente desconhecido: {env} (esperado {path})")
    return load_env_config(path, root)


def state_path(root: Path, env: str) -> Path:
    return root / ".deploy" / f"{env}.json"


def build_deployer(root: Path, env: str) -> Deployer:
    """Deployer com estado em `.deploy/<env>.json` e backup verificado (`--backup`) ligado."""
    config = env_config(root, env)
    runner = SubprocessRunner()
    backups = BackupService(config, runner, root / ".deploy" / "backups" / env)

    def backup() -> None:
        manifest = backups.create()
        result = backups.verify(manifest)
        if not result.ok:
            raise RuntimeError(f"ensaio de restauracao reprovou: {result.mismatches}")

    return Deployer(config, runner, StateStore(state_path(root, env)), backup=backup)
