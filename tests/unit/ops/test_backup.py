"""SPEC-012 · REQ-OPS-004: backup com manifesto, retencao e ensaio de restauracao (logica, Runner falso).

O ensaio contra o PostgreSQL REAL (dados destruidos e recuperados) esta em tests/integration/test_ops_e2e.py.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from spatial_ops.backup import BackupService, BackupVerifyError, load_manifest
from spatial_ops.deploy import EnvConfig
from spatial_ops.runner import Result


class FakePg:
    """Simula `docker compose exec db {psql,pg_dump,pg_restore}`."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.source_counts = {"equipment": 3, "telemetry_events": 100}
        self.counts_after_dump = {
            "equipment": 3,
            "telemetry_events": 104,
        }  # o simulador publicou durante o dump
        self.restored_counts = {
            "equipment": 3,
            "telemetry_events": 102,
        }  # dentro de [antes, depois]
        self.dump_bytes = b"PGDMP-conteudo-do-dump"
        self.restore_fails = False
        self.dumps_done = 0
        self.dbs: set[str] = {"spatial"}

    def run(
        self,
        args: Sequence[str],
        *,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        stdout_path: Path | None = None,
        stdin_path: Path | None = None,
    ) -> Result:
        argv = list(args)
        self.calls.append(argv)
        if "pg_dump" in argv:
            assert stdout_path is not None
            stdout_path.write_bytes(self.dump_bytes)
            self.dumps_done += 1
            return Result(0)
        if "pg_restore" in argv:
            if self.restore_fails:
                return Result(1, "", "restore error")
            self.dbs.add(argv[argv.index("-d") + 1])
            return Result(0)
        if "psql" in argv:
            sql = argv[-1]
            if "query_to_xml" in sql:
                database = argv[argv.index("-d") + 1]
                if database == "spatial":
                    counts = self.source_counts if self.dumps_done == 0 else self.counts_after_dump
                else:
                    counts = self.restored_counts
                return Result(0, "\n".join(f"{t}|{n}" for t, n in counts.items()) + "\n")
            if "server_version" in sql:
                return Result(0, "16.4\n")
            if sql.startswith("CREATE DATABASE"):
                self.dbs.add(sql.split()[2].strip('"'))
            if sql.startswith("DROP DATABASE"):
                self.dbs.discard(sql.split()[4].strip('"'))
            return Result(0)
        return Result(0)

    def commands(self, word: str) -> list[list[str]]:
        return [c for c in self.calls if word in c]


def _config(tmp_path: Path) -> EnvConfig:
    return EnvConfig(
        name="homolog",
        compose_files=("compose.yaml",),
        project="spatial-homolog",
        registry="",
        api_url="http://127.0.0.1:18088",
        smoke_token=None,
        wait_seconds=30,
        smoke_seconds=5,
        env={
            "POSTGRES_USER": "spatial",
            "POSTGRES_DB": "spatial",
            "POSTGRES_PASSWORD": "segredo-nao-vaza",
        },
        workdir=tmp_path,
    )


def _service(tmp_path: Path, pg: FakePg, moments: list[str] | None = None) -> BackupService:
    stamps = iter(moments or [f"2026-10-20T12:00:{i:02d}Z" for i in range(60)])
    ticks = iter(float(i) for i in range(1000))
    return BackupService(
        _config(tmp_path),
        pg,
        tmp_path / "backups",
        clock=lambda: next(stamps),
        timer=lambda: next(ticks),
    )


def test_create_writes_dump_and_manifest_with_hash_size_counts_and_version(tmp_path: Path) -> None:
    pg = FakePg()

    manifest = _service(tmp_path, pg).create()

    dump = tmp_path / "backups" / manifest.file
    assert dump.read_bytes() == pg.dump_bytes
    assert manifest.sha256 == hashlib.sha256(pg.dump_bytes).hexdigest()
    assert manifest.size == len(pg.dump_bytes)
    assert manifest.server_version == "16.4"
    assert manifest.tables_before == {"equipment": 3, "telemetry_events": 100}
    assert manifest.tables_after == {"equipment": 3, "telemetry_events": 104}
    on_disk = json.loads(
        (tmp_path / "backups" / f"{manifest.file}.manifest.json").read_text("utf-8")
    )
    assert on_disk["sha256"] == manifest.sha256
    assert load_manifest(tmp_path / "backups" / f"{manifest.file}.manifest.json") == manifest


def test_dump_uses_custom_format_without_putting_secrets_in_the_command(tmp_path: Path) -> None:
    pg = FakePg()

    _service(tmp_path, pg).create()

    dump_cmd = pg.commands("pg_dump")[0]
    assert "-Fc" in dump_cmd
    assert "--no-owner" in dump_cmd
    for argv in pg.calls:
        assert "segredo-nao-vaza" not in " ".join(argv)


def test_file_name_is_utc_timestamped_and_safe(tmp_path: Path) -> None:
    pg = FakePg()

    manifest = _service(tmp_path, pg, ["2026-10-20T12:34:56Z"] * 5).create()

    assert manifest.file == "spatial-20261020T123456Z.dump"


def test_verify_restores_into_a_temporary_database_compares_counts_and_drops_it(
    tmp_path: Path,
) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg)
    manifest = service.create()

    result = service.verify(manifest)

    assert result.ok
    assert result.mismatches == {}
    assert result.restore_seconds >= 0
    assert pg.dbs == {"spatial"}  # o banco temporario foi removido; o real nao foi tocado
    restore = pg.commands("pg_restore")[0]
    assert restore[restore.index("-d") + 1].startswith("restore_verify_")
    assert restore[restore.index("-d") + 1] != "spatial"


def test_verify_accepts_counts_between_before_and_after_because_tables_only_grow(
    tmp_path: Path,
) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg)
    manifest = service.create()
    for restored in (100, 102, 104):
        pg.restored_counts = {"equipment": 3, "telemetry_events": restored}

        assert service.verify(manifest).ok


@pytest.mark.parametrize(
    "restored",
    [
        {"equipment": 3, "telemetry_events": 99},  # perdeu dados
        {"equipment": 3, "telemetry_events": 105},  # mais do que existia
        {"equipment": 2, "telemetry_events": 102},  # tabela estatica divergiu
        {"equipment": 3},  # tabela sumiu
        {"equipment": 3, "telemetry_events": 102, "intrusa": 1},  # tabela inesperada
    ],
)
def test_verify_fails_with_a_precise_report_when_counts_do_not_match(
    tmp_path: Path, restored: dict[str, int]
) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg)
    manifest = service.create()
    pg.restored_counts = restored

    result = service.verify(manifest)

    assert not result.ok
    assert result.mismatches
    assert pg.dbs == {"spatial"}  # mesmo falhando, limpa o temporario


def test_corrupted_dump_is_detected_before_any_restore_is_attempted(tmp_path: Path) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg)
    manifest = service.create()
    (tmp_path / "backups" / manifest.file).write_bytes(b"corrompido")

    with pytest.raises(BackupVerifyError, match="SHA-256"):
        service.verify(manifest)

    assert pg.commands("pg_restore") == []


def test_missing_dump_is_reported(tmp_path: Path) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg)
    manifest = service.create()
    (tmp_path / "backups" / manifest.file).unlink()

    with pytest.raises(BackupVerifyError, match="not found"):
        service.verify(manifest)


def test_failed_pg_restore_is_reported_and_the_temp_database_is_dropped(tmp_path: Path) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg)
    manifest = service.create()
    pg.restore_fails = True

    with pytest.raises(BackupVerifyError, match="pg_restore"):
        service.verify(manifest)

    assert pg.dbs == {"spatial"}


def test_restore_into_a_target_recreates_the_database_and_checks_the_hash_first(
    tmp_path: Path,
) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg)
    manifest = service.create()

    service.restore(manifest, "spatial")

    sqls = [c[-1] for c in pg.commands("psql") if c[-1].startswith(("DROP", "CREATE"))]
    assert sqls[-2].startswith("DROP DATABASE IF EXISTS")
    assert "FORCE" in sqls[-2]
    assert sqls[-1].startswith("CREATE DATABASE")
    assert pg.commands("pg_restore")[-1][pg.commands("pg_restore")[-1].index("-d") + 1] == "spatial"


@pytest.mark.parametrize(
    "name",
    ["", "a b", "x;drop database spatial", '"quoted"', "a" * 64, "9starts", "UPPER-case", "a'b"],
)
def test_unsafe_database_names_are_refused(tmp_path: Path, name: str) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg)
    manifest = service.create()
    before = len(pg.calls)

    with pytest.raises(ValueError, match="invalid database name"):
        service.restore(manifest, name)

    assert len(pg.calls) == before


def test_prune_keeps_only_the_newest_n_backups_and_their_manifests(tmp_path: Path) -> None:
    pg = FakePg()
    stamps = [f"2026-10-20T12:00:{i:02d}Z" for i in range(10)]
    service = _service(tmp_path, pg, stamps)
    names = []
    for _ in range(5):
        names.append(service.create().file)

    removed = service.prune(keep=2)

    assert sorted(removed) == sorted(names[:3])
    left = sorted(p.name for p in (tmp_path / "backups").iterdir())
    assert left == sorted(list(names[3:]) + [f"{n}.manifest.json" for n in names[3:]])


def test_prune_never_removes_the_last_backup_even_with_keep_zero(tmp_path: Path) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg)
    manifest = service.create()

    assert service.prune(keep=0) == []
    assert (tmp_path / "backups" / manifest.file).exists()


def test_backups_returns_manifests_newest_first(tmp_path: Path) -> None:
    pg = FakePg()
    service = _service(tmp_path, pg, [f"2026-10-20T12:0{i}:00Z" for i in range(5)])
    first, second = service.create(), service.create()

    assert [m.file for m in service.backups()] == [second.file, first.file]
