"""Hash de senha no formato do `password_file` do Mosquitto 2.x (`$7$`: PBKDF2-HMAC-SHA512).

Formato: `usuario:$7$<iteracoes>$<sal em base64>$<hash em base64>`. Implementado aqui para nao passar
senhas por linha de comando; a compatibilidade e verificada contra um Mosquitto REAL
(tests/integration/test_broker_auth.py).
"""

import base64
import hashlib
import re
import secrets

ITERATIONS = 101
_USER = re.compile(r"[A-Za-z0-9._-]{1,64}")


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt if salt is not None else secrets.token_bytes(12)
    digest = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, ITERATIONS, dklen=64)
    return f"$7${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def password_file_line(username: str, password: str, salt: bytes | None = None) -> str:
    if not _USER.fullmatch(username):  # nada de ':' ou quebra de linha no nome
        raise ValueError("invalid MQTT username")
    if not password:
        raise ValueError("empty password")
    return f"{username}:{hash_password(password, salt)}"
