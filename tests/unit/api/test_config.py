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
        "HACC_SOURCE", "HACC_BASE_URL", "HACC_ALLOWED_HOSTS", "METRICS_TOKEN",
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


def test_hacc_defaults_to_the_simulated_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC-010 · REQ-HACC-001 (D-025): sem configuracao, nenhum HACC real e contatado."""
    _env(monkeypatch, DATABASE_URL=URL)

    settings = Settings()

    assert settings.hacc_source == "simulated"
    assert settings.hacc_base_url is None


@pytest.mark.parametrize(
    "extra",
    [{}, {"HACC_BASE_URL": "https://hacc.example.com"}, {"HACC_ALLOWED_HOSTS": "hacc.example.com"}],
)
def test_http_hacc_requires_base_url_and_allowed_hosts(
    monkeypatch: pytest.MonkeyPatch, extra: dict[str, str]
) -> None:
    _env(monkeypatch, DATABASE_URL=URL, HACC_SOURCE="http", **extra)

    with pytest.raises(ValidationError):
        Settings()


def test_http_hacc_with_url_and_hosts_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(
        monkeypatch,
        DATABASE_URL=URL,
        HACC_SOURCE="http",
        HACC_BASE_URL="https://hacc.example.com",
        HACC_ALLOWED_HOSTS="hacc.example.com, other.example.com",
    )

    assert Settings().hacc_source == "http"


# --- SPEC-012 · REQ-OPS-005: token de /metrics -------------------------------------------


def test_metrics_token_defaults_to_disabled_and_blank_means_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _env(monkeypatch, DATABASE_URL=URL)
    assert Settings().metrics_token is None

    _env(monkeypatch, DATABASE_URL=URL, METRICS_TOKEN="  ")
    assert Settings().metrics_token is None


def test_metrics_token_must_be_long_and_is_never_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, DATABASE_URL=URL, METRICS_TOKEN="short")
    with pytest.raises(ValidationError):
        Settings()

    _env(monkeypatch, DATABASE_URL=URL, METRICS_TOKEN="a-sufficiently-long-token-1")
    settings = Settings()
    assert settings.metrics_token is not None
    assert "a-sufficiently-long-token-1" not in repr(settings)
