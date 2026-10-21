"""Reconciliador GitOps (pull): converge o ambiente para o estado desejado no Git (SPEC-012, REQ-OPS-003).

  python scripts/gitops_reconcile.py --env homolog [--remote origin] [--ref origin/main] [--retry-failed]

Le `deploy/desired/<env>.json` do objeto Git `<ref>` (nao do diretorio de trabalho), compara com o estado
registrado e com as imagens em execucao e, se divergirem, faz o deploy da tag desejada (com rollback
automatico). Uma tag que ja falhou nao e repetida em laco: use `--retry-failed` depois de corrigir.
Codigos de saida: 0 sincronizado/aplicado; 1 falhou ou pulado por falha anterior; 2 erro de leitura
do Git/estado desejado; 3 outra reconciliacao em andamento. Pensado para rodar por timer do systemd.
"""

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "ops" / "src"))

from spatial_ops.gitops import GitCliSource, LockHeldError, Reconciler, acquire_lock  # noqa: E402
from spatial_ops.runner import SubprocessRunner  # noqa: E402
from spatial_ops.state import StateStore  # noqa: E402
from spatial_ops.wiring import build_deployer, state_path  # noqa: E402

LOCK_TTL_S = 30 * 60  # um deploy nunca deve passar disso; trava mais velha = execucao que morreu


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--env", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()

    deployer = build_deployer(ROOT, args.env)
    git = GitCliSource(SubprocessRunner(), ROOT, remote=args.remote, ref=args.ref)
    reconciler = Reconciler(deployer, git, StateStore(state_path(ROOT, args.env)), env=args.env)
    (ROOT / ".deploy").mkdir(exist_ok=True)
    try:
        with acquire_lock(ROOT / ".deploy" / f"gitops-{args.env}.lock", ttl_s=LOCK_TTL_S):
            result = reconciler.reconcile(retry_failed=args.retry_failed)
    except LockHeldError:
        print(json.dumps({"ok": False, "action": "locked"}))
        return 3
    print(json.dumps({**asdict(result), "at": int(time.time())}))
    if result.ok:
        return 0
    return 2 if result.action == "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
