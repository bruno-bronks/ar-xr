"""Valida a configuracao do Prometheus e roda os testes das regras de SLO com `promtool` (REQ-OPS-005).

  python scripts/check_prometheus.py          # exige Docker; usa a mesma imagem do perfil `observability`

Codigo de saida 0 = config valida e todos os testes de regra passaram. Nada e instalado no host.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "prom/prometheus:v3.15.0"  # manter igual ao compose.yaml
SCRIPT = (
    "echo placeholder > /tmp/metrics_token && "  # a config referencia credentials_file
    "promtool check config /etc/prometheus/prometheus.yml && "
    "promtool test rules /etc/prometheus/tests/slo.test.yml"
)


def main() -> int:
    source = ROOT / "platform" / "prometheus"
    command = [
        "docker", "run", "--rm",
        "--mount", f"type=bind,source={source},target=/etc/prometheus,readonly",
        "--entrypoint", "/bin/sh", IMAGE, "-c", SCRIPT,
    ]  # fmt: skip
    try:
        done = subprocess.run(command, check=False, timeout=300)  # noqa: S603
    except FileNotFoundError:
        print("docker nao encontrado")
        return 127
    return done.returncode


if __name__ == "__main__":
    sys.exit(main())
