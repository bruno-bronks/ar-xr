"""Carga controlada contra a HOMOLOGACAO e medicao dos SLIs (SPEC-012, REQ-OPS-006). So stdlib.

  python scripts/load_test.py --base-url http://127.0.0.1:18088 --metrics-token $METRICS_TOKEN \\
      --duration 60 --rps 40 --workers 4 --out docs/evidence/phase-6/slo-load-test.json

NUNCA aponte para o VPS compartilhado nem para HACC/dados reais. Os tokens `demo-*` sao ficticios.
Saida 0 = SLOs atendidos E contagens do cliente batem com as do servidor (`/metrics`); 1 caso contrario.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "ops" / "src"))

from spatial_ops.loadtest import (  # noqa: E402
    Request,
    SloTarget,
    compare_with_server,
    evaluate,
    parse_prometheus,
    run_load,
)

OPERATOR = "demo-operator-a"
MIX = [
    Request("/api/v1/equipment", "/api/v1/equipment", OPERATOR, 3.0),
    Request(
        "/api/v1/equipment/{equipment_id}/twin", "/api/v1/equipment/EQ-001/twin", OPERATOR, 3.0
    ),
    Request(
        "/api/v1/equipment/{equipment_id}/telemetry/latest",
        "/api/v1/equipment/EQ-001/telemetry/latest",
        OPERATOR,
        2.0,
    ),
    Request("/health/ready", "/health/ready", None, 1.0),
    # credencial invalida: 401 e erro do CLIENTE, nao conta como indisponibilidade
    Request("/api/v1/equipment", "/api/v1/equipment", "invalid-token", 0.5),
]


def _fetch(url: str, token: str | None, timeout: float = 5.0) -> tuple[int, str]:
    if not url.startswith(("http://", "https://")):  # urllib tambem abriria file://
        raise ValueError("only http(s) URLs are allowed")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - URL informada pelo operador
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return int(response.status), response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--metrics-token", required=True)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--rps", type=float, default=40.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    status, text = _fetch(f"{base}/metrics", args.metrics_token)
    if status != 200:
        print(f"nao foi possivel ler /metrics (HTTP {status}); a conferencia exige METRICS_TOKEN")
        return 1
    before = parse_prometheus(text)

    def send(path: str, token: str | None) -> int:
        return _fetch(f"{base}{path}", token)[0]

    samples = run_load(
        send, MIX, duration_s=args.duration, rps=args.rps, workers=args.workers, seed=args.seed
    )

    status, text = _fetch(f"{base}/metrics", args.metrics_token)
    after = parse_prometheus(text)
    report = evaluate(samples, SloTarget(), args.duration)
    mismatches = compare_with_server(samples, before, after)
    report["profile"] = {
        "rps": args.rps,
        "workers": args.workers,
        "duration_s": args.duration,
        "seed": args.seed,
        "mix": [{"route": r.route, "weight": r.weight} for r in MIX],
    }
    report["server_crosscheck"] = {"consistent": not mismatches, "mismatches": mismatches}
    output = json.dumps(report, indent=2)
    print(output)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output + "\n", "utf-8")
    return 0 if report["slo"]["all_met"] and not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
