"""Configuracao 12-factor: somente variaveis de ambiente; segredos como SecretStr (REQ-SEC-001)."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: SecretStr
    mqtt_host: str = "localhost"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
