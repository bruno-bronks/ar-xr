"""Configuracao 12-factor: somente variaveis de ambiente; segredos como SecretStr (REQ-SEC-001)."""

from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
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

    @model_validator(mode="after")
    def _demo_auth_never_in_production(self) -> Self:
        if self.environment == "production" and self.auth_mode == "demo":
            raise ValueError("demo authentication is not allowed in production")
        return self
