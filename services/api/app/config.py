"""Configuracao 12-factor: somente variaveis de ambiente; segredos como SecretStr (REQ-SEC-001)."""

from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: SecretStr
    mqtt_host: str = "localhost"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    auth_mode: Literal["demo", "oidc"] = "demo"
    marker_rate_limit: int = Field(default=30, ge=1)  # resolucoes de marker por minuto/principal
    panel_dir: str | None = None
    knowledge_dir: str | None = None
    assistant_provider: Literal["extractive", "llm"] = (
        "extractive"  # D-018: LLM desligado por padrao
    )
    anthropic_api_key: SecretStr | None = None
    assistant_model: str = "claude-sonnet-5-5"
    assistant_rate_limit: int = Field(default=10, ge=1)  # perguntas por minuto/usuario (D-023)
    hacc_source: Literal["simulated", "http", "hacc"] = (
        "simulated"  # D-025/D-026/D-054: simulada por padrao
    )
    hacc_base_url: str | None = None
    hacc_allowed_hosts: str = ""  # lista separada por virgula
    hacc_api_token: SecretStr | None = None  # Bearer da rota de integracao do HACC (D-054)
    hacc_allow_plain_http: bool = False  # D-055: http fora do loopback (so rede privada); desligado
    hacc_tenant_id: str = "org-a"  # organizacao dona dos leitos do HACC (imposta aqui, D-030)
    metrics_token: SecretStr | None = None  # /metrics so existe com token proprio (REQ-OPS-005)

    @field_validator("anthropic_api_key", "metrics_token", "hacc_api_token", mode="before")
    @classmethod
    def _blank_key_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _http_hacc_requires_url_and_hosts(self) -> Self:
        if self.hacc_source == "http" and not (
            self.hacc_base_url and self.hacc_allowed_hosts.strip()
        ):
            raise ValueError("HACC_SOURCE=http requires HACC_BASE_URL and HACC_ALLOWED_HOSTS")
        return self

    @model_validator(mode="after")
    def _hacc_integration_requires_url_hosts_and_token(self) -> Self:
        if self.hacc_source == "hacc":
            token = self.hacc_api_token.get_secret_value() if self.hacc_api_token else ""
            if not (self.hacc_base_url and self.hacc_allowed_hosts.strip() and len(token) >= 16):
                raise ValueError(
                    "HACC_SOURCE=hacc requires HACC_BASE_URL, HACC_ALLOWED_HOSTS and a "
                    "HACC_API_TOKEN with at least 16 characters"
                )
        return self

    @model_validator(mode="after")
    def _metrics_token_is_long_enough(self) -> Self:
        if self.metrics_token is not None and len(self.metrics_token.get_secret_value()) < 16:
            raise ValueError("METRICS_TOKEN must have at least 16 characters")
        return self

    @model_validator(mode="after")
    def _llm_requires_a_key(self) -> Self:
        if self.assistant_provider == "llm" and self.anthropic_api_key is None:
            raise ValueError("ASSISTANT_PROVIDER=llm requires ANTHROPIC_API_KEY")
        return self

    @model_validator(mode="after")
    def _demo_auth_never_in_production(self) -> Self:
        if self.environment == "production" and self.auth_mode == "demo":
            raise ValueError("demo authentication is not allowed in production")
        return self
