"""Valida o provisionamento do host com as FERRAMENTAS OFICIAIS, num contentor descartavel (REQ-OPS-009).

  python scripts/verify_host.py

Roda `systemd-analyze verify` nas units de deploy/systemd e `cloud-init schema` em
deploy/cloud-init/user-data.yaml (imagem Debian + pacotes `systemd` e `cloud-init`, baixados do espelho
Debian por HTTP). Isto valida SINTAXE e ESQUEMA; nenhuma unit e executada e nada toca um servidor real.
Codigo de saida 0 = ambas as validacoes passaram.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "debian:12-slim"
SCRIPT = r"""
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends systemd cloud-init python3 >/dev/null
# o que as units referenciam precisa existir para a verificacao: usuario, docker.service e os scripts
useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin arxr
groupadd -f docker
printf '[Service]\nExecStart=/bin/true\n' > /etc/systemd/system/docker.service
ln -s /src /opt/ar-xr
cp /src/deploy/systemd/spatial-* /etc/systemd/system/
chmod 0644 /etc/systemd/system/spatial-*
echo '== systemd-analyze verify =='
systemd-analyze verify /etc/systemd/system/spatial-*.service /etc/systemd/system/spatial-*.timer
echo 'systemd-analyze: OK'
echo '== cloud-init schema =='
cloud-init schema --config-file /src/deploy/cloud-init/user-data.yaml
"""


def main() -> int:
    command = [
        "docker", "run", "--rm",
        "--mount", f"type=bind,source={ROOT},target=/src,readonly",
        IMAGE, "sh", "-c", SCRIPT,
    ]  # fmt: skip
    try:
        done = subprocess.run(command, check=False, timeout=900)  # noqa: S603
    except FileNotFoundError:
        print("docker nao encontrado")
        return 127
    return done.returncode


if __name__ == "__main__":
    sys.exit(main())
