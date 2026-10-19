"""SPEC-006 · REQ-SEC-003: autenticacao demo explicita e fail-closed."""

import pytest
from app.auth import DemoAuthenticator, Principal
from app.config import Settings
from app.main import create_app
from pydantic import SecretStr, ValidationError
from spatial_storage.memory import InMemoryRepository

from tests.unit.api._app import Clock, ok

URL = "postgresql+psycopg://u:p@db:5432/x"


def test_demo_authenticator_knows_only_the_two_fictitious_tokens() -> None:
    auth = DemoAuthenticator()

    assert auth.authenticate("demo-operator-a") == Principal("user-a", "org-a")
    assert auth.authenticate("demo-operator-b") == Principal("user-b", "org-b")
    for token in ("", "demo-operator-c", "DEMO-OPERATOR-A", "demo-operator-a ", "x" * 10_000):
        assert auth.authenticate(token) is None


def test_settings_default_to_demo_outside_production() -> None:
    settings = Settings(database_url=URL, environment="development")

    assert settings.auth_mode == "demo"


@pytest.mark.parametrize("environment", ["development", "test", "staging"])
def test_demo_mode_is_allowed_outside_production(environment: str) -> None:
    Settings(database_url=URL, environment=environment, auth_mode="demo")


def test_production_with_demo_auth_is_refused_by_settings() -> None:
    with pytest.raises(ValidationError, match="demo"):
        Settings(database_url=URL, environment="production", auth_mode="demo")


def test_production_with_demo_auth_is_refused_even_if_settings_validation_is_bypassed() -> None:
    settings = Settings.model_construct(
        environment="production",
        auth_mode="demo",
        database_url=SecretStr(URL),
        log_level="INFO",
        mqtt_host="x",
        mqtt_port=1883,
    )

    with pytest.raises(RuntimeError, match="demo"):
        create_app(
            checks={"database": ok}, repo=InMemoryRepository(), settings=settings, clock=Clock()
        )


def test_oidc_mode_fails_closed_until_an_idp_is_approved() -> None:
    settings = Settings(database_url=URL, environment="production", auth_mode="oidc")

    with pytest.raises(RuntimeError, match="oidc"):
        create_app(
            checks={"database": ok}, repo=InMemoryRepository(), settings=settings, clock=Clock()
        )
