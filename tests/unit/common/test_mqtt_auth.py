"""SPEC-011 · REQ-IOT-003: credenciais MQTT opcionais (anonimo por padrao; senha nunca vaza)."""

import pytest
from simulator.main import SimulatorSettings
from spatial_common.mqtt_auth import apply_credentials, normalize_credentials
from worker.main import WorkerSettings


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def username_pw_set(self, username: str, password: str | None = None) -> None:
        self.calls.append((username, password))


def test_no_credentials_means_anonymous_and_does_not_touch_the_client() -> None:
    client = FakeClient()

    assert apply_credentials(client, None, None) is False
    assert apply_credentials(client, "", "") is False
    assert apply_credentials(client, "   ", None) is False
    assert client.calls == []


def test_both_credentials_are_applied() -> None:
    client = FakeClient()

    assert apply_credentials(client, " worker ", "s3gredo") is True
    assert client.calls == [("worker", "s3gredo")]


@pytest.mark.parametrize(("user", "password"), [("worker", None), ("worker", ""), (None, "x")])
def test_only_one_of_the_two_is_a_configuration_error(
    user: str | None, password: str | None
) -> None:
    with pytest.raises(ValueError, match="together"):
        normalize_credentials(user, password)


def test_password_never_appears_in_settings_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db/x")
    monkeypatch.setenv("MQTT_USERNAME", "worker")
    monkeypatch.setenv("MQTT_PASSWORD", "super-secreta-123")

    for settings in (WorkerSettings(), SimulatorSettings()):
        assert settings.mqtt_username == "worker"
        assert "super-secreta-123" not in repr(settings)
        assert "super-secreta-123" not in str(settings)
        assert settings.mqtt_password is not None
        assert settings.mqtt_password.get_secret_value() == "super-secreta-123"


def test_default_settings_are_anonymous(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("MQTT_USERNAME", "MQTT_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db/x")

    for settings in (WorkerSettings(), SimulatorSettings()):
        assert settings.mqtt_username is None
        assert settings.mqtt_password is None
