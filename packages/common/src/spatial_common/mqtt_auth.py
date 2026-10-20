"""Credenciais MQTT opcionais (SPEC-011, REQ-IOT-003). Padrao de desenvolvimento = anonimo.

Usuario e senha vem de variaveis de ambiente (`MQTT_USERNAME`/`MQTT_PASSWORD`) e so valem JUNTOS; um
sem o outro e erro de configuracao. Quem chama guarda a senha como segredo (ex.: `SecretStr`) e so a revela aqui, na hora de configurar o cliente.
"""

from typing import Protocol


class _PasswordClient(Protocol):
    def username_pw_set(self, username: str, password: str | None = None) -> object: ...


def normalize_credentials(username: str | None, password: str | None) -> tuple[str, str] | None:
    """(usuario, senha) ou None (anonimo). Vazio conta como ausente; so um dos dois => erro."""
    user = (username or "").strip() or None
    secret = password or ""
    if user is None and not secret:
        return None
    if user is None or not secret:
        raise ValueError("MQTT_USERNAME and MQTT_PASSWORD must be set together")
    return user, secret


def apply_credentials(client: _PasswordClient, username: str | None, password: str | None) -> bool:
    """Aplica as credenciais ao cliente paho, se houver. Devolve True se aplicou."""
    credentials = normalize_credentials(username, password)
    if credentials is None:
        return False
    client.username_pw_set(*credentials)
    return True
