"""SPEC-001 · REQ-SEC-001 (configuracao sem vazamento de segredos, 12-factor)."""

import pytest
from app.config import Settings
from pydantic import ValidationError

SECRET = "super-secret-pw-123"
URL = f"postgresql+psycopg://spatial:{SECRET}@db:5432/spatial"


def _env(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    for key in (
        "DATABASE_URL", "MQTT_HOST", "MQTT_PORT", "ENVIRONMENT", "LOG_LEVEL",
        "ASSISTANT_PROVIDER", "ANTHROPIC_API_KEY", "ASSISTANT_MODEL", "ASSISTANT_RATE_LIMIT",
    ):  # fmt: skip
        monkeypatch.delenv(key, raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, DATABASE_URL=URL)

    settings = Settings()

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.mqtt_host == "localhost"
    assert settings.mqtt_port == 1883
    assert settings.database_url.get_secret_value() == URL


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch)

    with pytest.raises(ValidationError):
        Settings()


def test_secret_never_appears_in_repr_or_str(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, DATABASE_URL=URL)

    settings = Settings()

    assert SECRET not in repr(settings)
    assert SECRET not in str(settings)
    assert SECRET not in settings.model_dump_json()


@pytest.mark.parametrize("port", ["0", "65536", "-1", "abc"])
def test_invalid_mqtt_port_rejected(monkeypatch: pytest.MonkeyPatch, port: str) -> None:
    _env(monkeypatch, DATABASE_URL=URL, MQTT_PORT=port)

    with pytest.raises(ValidationError):
        Settings()


def test_invalid_environment_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, DATABASE_URL=URL, ENVIRONMENT="prod-ish")

    with pytest.raises(ValidationError):
        Settings()


def test_reads_overrides_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, DATABASE_URL=URL, MQTT_HOST="broker", MQTT_PORT="1884", LOG_LEVEL="DEBUG")

    settings = Settings()

    assert (settings.mqtt_host, settings.mqtt_port, settings.log_level) == ("broker", 1884, "DEBUG")


def test_assistant_defaults_to_the_offline_extractive_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SPEC-009 · REQ-AI-005 (D-018): LLM desligado por padrao, sem chave."""
    _env(monkeypatch, DATABASE_URL=URL)

    settings = Settings()

    assert settings.assistant_provider == "extractive"
    assert settings.anthropic_api_key is None
    assert settings.assistant_rate_limit == 10


def test_llm_provider_requires_an_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, DATABASE_URL=URL, ASSISTANT_PROVIDER="llm")

    with pytest.raises(ValidationError):
        Settings()


def test_blank_api_key_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """O Compose repassa `ANTHROPIC_API_KEY=` vazio quando a variavel nao esta definida."""
    _env(monkeypatch, DATABASE_URL=URL, ANTHROPIC_API_KEY="  ")

    assert Settings().anthropic_api_key is None
    _env(monkeypatch, DATABASE_URL=URL, ANTHROPIC_API_KEY="", ASSISTANT_PROVIDER="llm")
    with pytest.raises(ValidationError):
        Settings()


def test_api_key_never_appears_in_repr_or_str(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(
        monkeypatch, DATABASE_URL=URL, ANTHROPIC_API_KEY="sk-ant-SEGREDO", ASSISTANT_PROVIDER="llm"
    )

    settings = Settings()

    assert "sk-ant-SEGREDO" not in repr(settings)
    assert "sk-ant-SEGREDO" not in str(settings)
    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-SEGREDO"
