"""SPEC-001 · REQ-ENG-002 (liveness) e REQ-ENG-003 (readiness)."""

import socket
import threading
from collections.abc import Callable, Mapping

import pytest
from app.health import check_broker, check_database
from app.main import create_app
from fastapi.testclient import TestClient

Check = Callable[[], bool]


def _client(checks: Mapping[str, Check]) -> TestClient:
    return TestClient(create_app(checks=checks), raise_server_exceptions=False)


def _ok() -> bool:
    return True


def _fail() -> bool:
    return False


def _boom() -> bool:
    raise RuntimeError("password=hunter2 host=db.internal")


# --- REQ-ENG-002: liveness -------------------------------------------------------------


def test_live_returns_200() -> None:
    response = _client({"database": _ok, "broker": _ok}).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_live_ignores_failing_dependencies() -> None:
    """Liveness nao consulta dependencias (SPEC-001 A1)."""
    response = _client({"database": _fail, "broker": _boom}).get("/health/live")

    assert response.status_code == 200


def test_live_does_not_execute_checks() -> None:
    calls: list[str] = []

    def spy() -> bool:
        calls.append("called")
        return True

    _client({"database": spy, "broker": spy}).get("/health/live")

    assert calls == []


# --- REQ-ENG-003: readiness ------------------------------------------------------------


def test_ready_returns_200_when_all_dependencies_ok() -> None:
    response = _client({"database": _ok, "broker": _ok}).get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok", "broker": "ok"}}


@pytest.mark.parametrize(
    ("database", "broker", "expected"),
    [
        (_fail, _ok, {"database": "fail", "broker": "ok"}),
        (_ok, _fail, {"database": "ok", "broker": "fail"}),
        (_fail, _fail, {"database": "fail", "broker": "fail"}),
    ],
)
def test_ready_returns_503_when_any_dependency_fails(
    database: Check, broker: Check, expected: dict[str, str]
) -> None:
    response = _client({"database": database, "broker": broker}).get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "checks": expected}


def test_ready_treats_exception_as_failure_not_500() -> None:
    response = _client({"database": _boom, "broker": _ok}).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "fail"


def test_ready_does_not_leak_exception_text() -> None:
    """SPEC-001 A3: nem credenciais nem texto de excecao no corpo."""
    response = _client({"database": _boom, "broker": _ok}).get("/health/ready")

    assert "hunter2" not in response.text
    assert "db.internal" not in response.text
    assert "RuntimeError" not in response.text


def test_ready_logs_failure_without_secrets(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING"):
        _client({"database": _boom, "broker": _ok}).get("/health/ready")

    assert "database" in caplog.text
    assert "hunter2" not in caplog.text


def test_ready_runs_all_checks_even_if_first_fails() -> None:
    calls: list[str] = []

    def first() -> bool:
        calls.append("database")
        return False

    def second() -> bool:
        calls.append("broker")
        return True

    _client({"database": first, "broker": second}).get("/health/ready")

    assert calls == ["database", "broker"]


# --- implementacoes reais das verificacoes ----------------------------------------------


def test_check_broker_true_when_port_open() -> None:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    thread = threading.Thread(target=server.accept, daemon=True)
    thread.start()
    try:
        assert check_broker("127.0.0.1", port, timeout=1.0) is True
    finally:
        server.close()


def test_check_broker_false_when_port_closed() -> None:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()  # porta livre => conexao recusada

    assert check_broker("127.0.0.1", port, timeout=1.0) is False


def test_check_database_false_and_silent_on_unreachable(caplog: pytest.LogCaptureFixture) -> None:
    url = "postgresql+psycopg://user:s3cr3t-pw@127.0.0.1:1/db"

    with caplog.at_level("WARNING"):
        result = check_database(url, timeout=1)

    assert result is False
    assert "s3cr3t-pw" not in caplog.text
