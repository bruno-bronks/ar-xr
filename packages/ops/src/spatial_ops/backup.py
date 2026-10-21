"""Backup e restauracao do PostgreSQL com manifesto e ensaio de restauracao (SPEC-012, REQ-OPS-004).

`create`: pg_dump (formato custom) + manifesto JSON {SHA-256, tamanho, versao, contagem de linhas por
tabela ANTES e DEPOIS do dump}. `verify` (ensaio de restauracao, nao destrutivo): confere o hash,
restaura num banco TEMPORARIO, compara contagens e remove o temporario. A comparacao aceita
`antes <= restaurado <= depois` porque as tabelas desta plataforma so crescem (eventos idempotentes,
sem DELETE) e o simulador pode publicar durante o dump.

LIMITES: backup logico de um unico banco; nao cobre o volume do broker (o worker e idempotente), nao e
backup fora do host (copiar para outro local e responsabilidade de quem opera) e nao e PITR.
"""

import hashlib
import json
import re
import secrets
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from spatial_ops.deploy import EnvConfig, compose_base
from spatial_ops.runner import Result, Runner

_DB = re.compile(r"[a-z_][a-z0-9_]{0,62}")
_COUNT_SQL = (
    "SELECT table_name || '|' || (xpath('/row/c/text()', query_to_xml("
    "format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text "
    "FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
    "ORDER BY table_name"
)


class BackupVerifyError(Exception):
    """Dump ausente/corrompido ou restauracao que falhou. Nunca carrega saida do banco com dados."""


@dataclass(frozen=True)
class BackupManifest:
    file: str
    sha256: str
    size: int
    created_at: str
    database: str
    server_version: str
    tables_before: dict[str, int]
    tables_after: dict[str, int]


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    mismatches: dict[str, str]
    restore_seconds: float
    tables: dict[str, int]


def load_manifest(path: Path) -> BackupManifest:
    return BackupManifest(**json.loads(path.read_text("utf-8")))


def _check_db(name: str) -> str:
    if not _DB.fullmatch(name):
        raise ValueError("invalid database name")
    return name


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class BackupService:
    def __init__(
        self,
        config: EnvConfig,
        runner: Runner,
        backup_dir: Path,
        *,
        clock: Callable[[], str] | None = None,
        timer: Callable[[], float] | None = None,
    ) -> None:
        import time

        self._config = config
        self._runner = runner
        self._dir = backup_dir
        self._clock = clock or (lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
        self._timer = timer or time.monotonic
        self._user = _check_db(config.env.get("POSTGRES_USER", "spatial"))
        self._database = _check_db(config.env.get("POSTGRES_DB", "spatial"))

    # --- primitivas --------------------------------------------------------------------------

    def _exec(
        self, *args: str, stdout_path: Path | None = None, stdin_path: Path | None = None
    ) -> Result:
        command = [*compose_base(self._config), "exec", "-T", "db", *args]
        return self._runner.run(
            command,
            env=dict(self._config.env),
            timeout=900,
            stdout_path=stdout_path,
            stdin_path=stdin_path,
        )

    def _psql(self, database: str, sql: str) -> Result:
        return self._exec("psql", "-U", self._user, "-d", database, "-tAc", sql)

    def table_counts(self, database: str) -> dict[str, int]:
        result = self._psql(_check_db(database), _COUNT_SQL)
        if not result.ok:
            raise BackupVerifyError("could not count table rows")
        counts: dict[str, int] = {}
        for line in result.stdout.splitlines():
            name, sep, value = line.strip().partition("|")
            if sep and value.isdigit():
                counts[name] = int(value)
        return counts

    # --- operacoes ---------------------------------------------------------------------------

    def create(self) -> BackupManifest:
        self._dir.mkdir(parents=True, exist_ok=True)
        stamp = self._clock()
        name = f"{self._database}-{re.sub(r'[-:]', '', stamp)}.dump"
        path = self._dir / name
        version = self._psql(self._database, "SHOW server_version").stdout.strip() or "unknown"
        before = self.table_counts(self._database)
        dump = self._exec(
            "pg_dump", "-U", self._user, "-d", self._database, "-Fc", "--no-owner", stdout_path=path
        )
        if not dump.ok:
            path.unlink(missing_ok=True)
            raise BackupVerifyError("pg_dump failed")
        after = self.table_counts(self._database)
        manifest = BackupManifest(
            name, _sha256(path), path.stat().st_size, stamp, self._database, version, before, after
        )
        (self._dir / f"{name}.manifest.json").write_text(
            json.dumps(asdict(manifest), indent=2) + "\n", "utf-8"
        )
        return manifest

    def _check_file(self, manifest: BackupManifest) -> Path:
        path = self._dir / manifest.file
        if not path.is_file():
            raise BackupVerifyError("dump file not found")
        if _sha256(path) != manifest.sha256:
            raise BackupVerifyError(
                "dump SHA-256 does not match the manifest (corrupted or tampered)"
            )
        return path

    def _restore_into(self, path: Path, database: str) -> float:
        started = self._timer()
        restore = self._exec(
            "pg_restore",
            "-U",
            self._user,
            "-d",
            database,
            "--no-owner",
            "--exit-on-error",
            stdin_path=path,
        )
        if not restore.ok:
            raise BackupVerifyError("pg_restore failed")
        return self._timer() - started

    def verify(self, manifest: BackupManifest) -> VerifyResult:
        """Ensaio de restauracao: NAO toca o banco real; o banco temporario e sempre removido."""
        path = self._check_file(manifest)
        temp = f"restore_verify_{secrets.token_hex(4)}"
        self._psql("postgres", f'CREATE DATABASE "{temp}"')
        try:
            seconds = self._restore_into(path, temp)
            restored = self.table_counts(temp)
        finally:
            self._psql("postgres", f'DROP DATABASE IF EXISTS "{temp}" WITH (FORCE)')
        mismatches: dict[str, str] = {}
        for table in sorted(
            set(restored) | set(manifest.tables_before) | set(manifest.tables_after)
        ):
            low, high = manifest.tables_before.get(table), manifest.tables_after.get(table)
            got = restored.get(table)
            if low is None or high is None:
                mismatches[table] = "unexpected table in the restored database"
            elif got is None:
                mismatches[table] = "table missing after restore"
            elif not low <= got <= high:
                mismatches[table] = f"restored {got} rows, expected between {low} and {high}"
        return VerifyResult(not mismatches, mismatches, seconds, restored)

    def restore(self, manifest: BackupManifest, target: str) -> float:
        """DESTRUTIVO: recria `target` a partir do dump. Pare api/worker/simulador antes (ver CLI)."""
        _check_db(target)
        path = self._check_file(manifest)
        self._psql("postgres", f'DROP DATABASE IF EXISTS "{target}" WITH (FORCE)')
        self._psql("postgres", f'CREATE DATABASE "{target}"')
        return self._restore_into(path, target)

    def backups(self) -> list[BackupManifest]:
        if not self._dir.is_dir():
            return []
        manifests = [load_manifest(p) for p in self._dir.glob("*.manifest.json")]
        return sorted(manifests, key=lambda m: (m.created_at, m.file), reverse=True)

    def prune(self, keep: int) -> list[str]:
        """Mantem os `keep` mais recentes (minimo 1: nunca apaga o ultimo backup). Devolve os removidos."""
        ordered = self.backups()
        removed: list[str] = []
        for manifest in ordered[max(keep, 1) :]:
            (self._dir / manifest.file).unlink(missing_ok=True)
            (self._dir / f"{manifest.file}.manifest.json").unlink(missing_ok=True)
            removed.append(manifest.file)
        return removed
