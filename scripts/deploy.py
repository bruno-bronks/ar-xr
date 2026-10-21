"""CLI de release/deploy/rollback por tag (SPEC-012, REQ-OPS-001/002). So stdlib.

  python scripts/deploy.py build    --tag v1 [--registry localhost:5000/] [--push]
  python scripts/deploy.py deploy   --env homolog --tag v1 [--backup]
  python scripts/deploy.py rollback --env homolog
  python scripts/deploy.py status   --env homolog

Estado em `.deploy/<env>.json` (ignorado pelo Git). Codigos de saida: 0 ok; 1 deploy falhou e a pilha
VOLTOU para a tag anterior; 2 falhou e o rollback tambem falhou (intervencao manual).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "ops" / "src"))

from spatial_ops.deploy import APP_SERVICES, Deployer  # noqa: E402
from spatial_ops.runner import SubprocessRunner  # noqa: E402
from spatial_ops.state import validate_tag  # noqa: E402
from spatial_ops.wiring import build_deployer  # noqa: E402


def _deployer(env: str) -> Deployer:
    return build_deployer(ROOT, env)


def _build(tag: str, registry: str, push: bool) -> int:
    validate_tag(tag)
    runner = SubprocessRunner()
    env = {"IMAGE_TAG": tag, "IMAGE_REGISTRY": registry}
    base = ["docker", "compose", "--project-directory", str(ROOT), "-f", "compose.yaml"]
    build = runner.run([*base, "build", *APP_SERVICES], env=env, timeout=1800)
    print(build.stderr[-800:] if not build.ok else f"build ok: {tag}")
    if not build.ok:
        return 1
    if push:
        pushed = runner.run([*base, "push", *APP_SERVICES], env=env, timeout=900)
        print(pushed.stderr[-800:] if not pushed.ok else f"push ok: {registry}*:{tag}")
        return 0 if pushed.ok else 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--tag", required=True)
    b.add_argument("--registry", default="")
    b.add_argument("--push", action="store_true")
    d = sub.add_parser("deploy")
    d.add_argument("--env", required=True)
    d.add_argument("--tag", required=True)
    d.add_argument(
        "--backup", action="store_true", help="backup + ensaio de restauracao ANTES de subir"
    )
    for name in ("rollback", "status"):
        sub.add_parser(name).add_argument("--env", required=True)
    args = parser.parse_args()

    if args.command == "build":
        return _build(args.tag, args.registry, args.push)
    deployer = _deployer(args.env)
    if args.command == "status":
        print(json.dumps(deployer.status(), indent=2))
        return 0
    result = (
        deployer.deploy(args.tag, backup=args.backup)
        if args.command == "deploy"
        else deployer.rollback()
    )
    print(
        json.dumps(
            {
                "ok": result.ok,
                "tag": result.tag,
                "stage": result.stage,
                "rolled_back_to": result.rolled_back_to,
                "message": result.message,
            }
        )
    )
    if result.ok:
        return 0
    return 2 if result.stage == "rollback" else 1


if __name__ == "__main__":
    raise SystemExit(main())
