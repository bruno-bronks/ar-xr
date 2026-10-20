"""Gera usuarios e senhas ALEATORIAS do broker endurecido (SPEC-011, REQ-IOT-003).

Grava em `platform/mosquitto/secure/` (ignorado pelo Git):
- `passwd`           arquivo de senhas do Mosquitto (somente hashes);
- `credentials.env`  senhas em claro para o Compose (`--env-file`) e para configurar dispositivos.
Nunca imprime as senhas. Uso: python scripts/gen_broker_users.py [--devices EQ-001,EQ-002,EQ-003]
"""

import argparse
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "common" / "src"))

from spatial_common.mosquitto_passwd import password_file_line  # noqa: E402

SERVICE_USERS = {
    "worker": "MQTT_WORKER_PASSWORD",
    "simulator": "MQTT_SIMULATOR_PASSWORD",
    "health": "MQTT_HEALTH_PASSWORD",
}


def generate(out: Path, devices: list[str]) -> tuple[Path, Path]:
    out.mkdir(parents=True, exist_ok=True)
    passwords = {user: secrets.token_urlsafe(24) for user in SERVICE_USERS}
    passwords.update({device: secrets.token_urlsafe(24) for device in devices})
    passwd = out / "passwd"
    passwd.write_text(
        "".join(password_file_line(u, p) + "\n" for u, p in passwords.items()), "utf-8"
    )
    env_lines = [f"{var}={passwords[user]}" for user, var in SERVICE_USERS.items()]
    env_lines += [f"MQTT_DEVICE_PASSWORD_{d.replace('-', '_')}={passwords[d]}" for d in devices]
    credentials = out / "credentials.env"
    credentials.write_text("\n".join(env_lines) + "\n", "utf-8")
    for path in (passwd, credentials):
        os.chmod(path, 0o600)  # no Windows e ignorado; em POSIX restringe ao dono
    return passwd, credentials


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "platform" / "mosquitto" / "secure"))
    parser.add_argument(
        "--devices", default="", help="ids de equipamento (um usuario por dispositivo)"
    )
    args = parser.parse_args()
    devices = [d.strip() for d in args.devices.split(",") if d.strip()]
    passwd, credentials = generate(Path(args.out), devices)
    print(
        f"usuarios gerados ({len(SERVICE_USERS) + len(devices)}): hashes em {passwd}; senhas em {credentials} (nao versionar)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
