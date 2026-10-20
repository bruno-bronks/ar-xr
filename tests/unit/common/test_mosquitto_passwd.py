"""SPEC-011 · REQ-IOT-003: hash de senha do Mosquitto (formato $7$) e geracao de usuarios.

A compatibilidade com o broker REAL e provada em tests/integration/test_broker_auth.py.
"""

import base64
import hashlib
import importlib.util
from pathlib import Path

import pytest
from spatial_common.mosquitto_passwd import ITERATIONS, hash_password, password_file_line

ROOT = Path(__file__).resolve().parents[3]


def test_hash_has_the_mosquitto_pbkdf2_sha512_layout() -> None:
    salt = bytes(range(12))

    hashed = hash_password("segredo", salt)

    prefix, iterations, salt_b64, digest_b64 = hashed[1:].split("$")
    assert (prefix, int(iterations)) == ("7", ITERATIONS)
    assert base64.b64decode(salt_b64) == salt
    expected = hashlib.pbkdf2_hmac("sha512", b"segredo", salt, ITERATIONS, dklen=64)
    assert base64.b64decode(digest_b64) == expected
    assert hashed.startswith("$7$101$")


def test_random_salt_makes_hashes_differ_and_deterministic_with_fixed_salt() -> None:
    assert hash_password("x") != hash_password("x")
    assert hash_password("x", b"0" * 12) == hash_password("x", b"0" * 12)


def test_password_file_line_never_contains_the_plaintext() -> None:
    line = password_file_line("EQ-001", "senha-super-secreta")

    assert line.startswith("EQ-001:$7$")
    assert "senha-super-secreta" not in line


@pytest.mark.parametrize("user", ["", "a:b", "a b", "a\nb", "x" * 65, "../x"])
def test_invalid_usernames_are_rejected(user: str) -> None:
    with pytest.raises(ValueError, match="invalid MQTT username"):
        password_file_line(user, "pw")


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty password"):
        password_file_line("EQ-001", "")


def test_generated_users_have_hashed_passwd_and_separate_plaintext_credentials(
    tmp_path: Path,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "gen_broker_users", ROOT / "scripts" / "gen_broker_users.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    passwd, credentials = module.generate(tmp_path, ["EQ-001", "EQ-002"])

    plain = dict(line.split("=", 1) for line in credentials.read_text("utf-8").split())
    passwd_text = passwd.read_text("utf-8")
    users = [line.split(":", 1)[0] for line in passwd_text.splitlines()]
    assert users == ["worker", "simulator", "health", "EQ-001", "EQ-002"]
    assert len(plain) == 5
    assert len(set(plain.values())) == 5  # senhas distintas
    assert all(len(v) >= 30 for v in plain.values())
    for secret in plain.values():
        assert secret not in passwd_text  # passwd so tem hashes


def test_credentials_directory_is_gitignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text("utf-8")

    assert "platform/mosquitto/secure/" in gitignore
