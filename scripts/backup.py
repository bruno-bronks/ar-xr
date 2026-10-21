"""CLI de backup/restauracao do PostgreSQL (SPEC-012, REQ-OPS-004). So stdlib.

  python scripts/backup.py create  --env homolog [--keep 14]
  python scripts/backup.py verify  --env homolog [--file spatial-....dump]   # ensaio NAO destrutivo
  python scripts/backup.py restore --env homolog --yes [--file ...]          # DESTRUTIVO: recria o banco
  python scripts/backup.py list    --env homolog

`restore` para api/worker/simulador, recria o banco a partir do dump (hash conferido) e os reinicia.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "ops" / "src"))

from spatial_ops.backup import BackupService, BackupVerifyError  # noqa: E402
from spatial_ops.deploy import compose_base  # noqa: E402
from spatial_ops.runner import SubprocessRunner  # noqa: E402
from spatial_ops.wiring import env_config  # noqa: E402

SERVICES = ("simulator", "worker", "api")  # ordem de parada; a partida usa a ordem inversa


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=["create", "verify", "restore", "list"])
    parser.add_argument("--env", required=True)
    parser.add_argument("--file", help="nome do dump (padrao: o mais recente)")
    parser.add_argument("--keep", type=int, default=14, help="retencao apos `create`")
    parser.add_argument("--yes", action="store_true", help="confirma a restauracao destrutiva")
    args = parser.parse_args()

    config = env_config(ROOT, args.env)
    runner = SubprocessRunner()
    service = BackupService(config, runner, ROOT / ".deploy" / "backups" / args.env)

    try:
        if args.command == "create":
            manifest = service.create()
            removed = service.prune(args.keep)
            print(
                json.dumps(
                    {
                        "created": manifest.file,
                        "sha256": manifest.sha256,
                        "size": manifest.size,
                        "pruned": removed,
                    }
                )
            )
            return 0
        backups = service.backups()
        if args.command == "list":
            rows = [{"file": m.file, "created_at": m.created_at, "size": m.size} for m in backups]
            print(json.dumps(rows, indent=2))
            return 0
        chosen = next((m for m in backups if args.file in (None, m.file)), None)
        if chosen is None:
            print("nenhum backup encontrado")
            return 1
        if args.command == "verify":
            result = service.verify(chosen)
            print(
                json.dumps(
                    {
                        "ok": result.ok,
                        "file": chosen.file,
                        "restore_seconds": round(result.restore_seconds, 2),
                        "mismatches": result.mismatches,
                    }
                )
            )
            return 0 if result.ok else 1
        if not args.yes:
            print("restore e DESTRUTIVO: repita com --yes (o banco sera recriado a partir do dump)")
            return 1
        database = config.env.get("POSTGRES_DB", "spatial")
        runner.run([*compose_base(config), "stop", *SERVICES], env=dict(config.env), timeout=300)
        try:
            seconds = service.restore(chosen, database)
        finally:
            runner.run(
                [*compose_base(config), "start", *reversed(SERVICES)],
                env=dict(config.env),
                timeout=300,
            )
        print(
            json.dumps(
                {
                    "restored": chosen.file,
                    "database": database,
                    "restore_seconds": round(seconds, 2),
                }
            )
        )
        return 0
    except BackupVerifyError as error:
        print(f"FALHOU: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
