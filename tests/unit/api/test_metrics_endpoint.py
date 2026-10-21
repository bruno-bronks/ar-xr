"""SPEC-012 · REQ-OPS-005, REQ-OPS-007 (abuso): `/metrics` protegido por token proprio, rotulos de baixa cardinalidade, sem PII."""

import re
from collections.abc import Callable, Mapping

from fastapi.testclient import TestClient

from tests.unit.api._app import TOKEN_A, auth, make_app

METRICS_TOKEN = "metrics-test-token-0123456789"


def _client(checks: Mapping[str, Callable[[], bool]] | None = None) -> TestClient:
    return TestClient(
        make_app(metrics_token=METRICS_TOKEN, checks=checks), raise_server_exceptions=False
    )


def _scrape(client: TestClient, token: str = METRICS_TOKEN) -> str:
    response = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    return str(response.text)


def test_metrics_is_disabled_when_no_token_is_configured() -> None:
    client = TestClient(make_app(), raise_server_exceptions=False)

    response = client.get("/metrics", headers={"Authorization": f"Bearer {METRICS_TOKEN}"})

    assert response.status_code == 404
    assert response.json() == {"detail": "not found"}


def test_metrics_requires_the_metrics_token() -> None:
    client = _client()

    missing = client.get("/metrics")
    wrong = client.get("/metrics", headers={"Authorization": "Bearer nope"})
    basic = client.get("/metrics", headers={"Authorization": f"Basic {METRICS_TOKEN}"})

    assert (missing.status_code, wrong.status_code, basic.status_code) == (401, 401, 401)
    assert missing.headers["www-authenticate"] == "Bearer"
    assert METRICS_TOKEN not in missing.text + wrong.text


def test_a_demo_user_token_does_not_open_the_metrics_endpoint() -> None:
    response = _client().get("/metrics", headers=auth(TOKEN_A))

    assert response.status_code == 401


def test_the_metrics_token_does_not_open_the_business_api() -> None:
    response = _client().get(
        "/api/v1/equipment", headers={"Authorization": f"Bearer {METRICS_TOKEN}"}
    )

    assert response.status_code == 401


def test_scrape_returns_prometheus_text_without_caching() -> None:
    client = _client()
    client.get("/health/live")

    response = client.get("/metrics", headers={"Authorization": f"Bearer {METRICS_TOKEN}"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert response.headers["cache-control"] == "no-store"
    assert "# TYPE http_requests_total counter" in response.text
    assert "# TYPE http_request_duration_seconds histogram" in response.text


def test_requests_are_counted_by_route_template_method_and_status_class() -> None:
    client = _client()
    client.get("/api/v1/equipment", headers=auth())
    client.get("/api/v1/equipment/EQ-001", headers=auth())
    client.get("/api/v1/equipment/EQ-002", headers=auth())
    client.get("/api/v1/equipment/EQ-001")  # 401

    text = _scrape(client)

    assert 'route="/api/v1/equipment/{equipment_id}",method="GET",status_class="2xx"} 2' in text
    assert 'route="/api/v1/equipment/{equipment_id}",method="GET",status_class="4xx"} 1' in text
    assert 'route="/api/v1/equipment",method="GET",status_class="2xx"} 1' in text
    assert "EQ-001" not in text  # id nunca vira rotulo
    assert "EQ-002" not in text


def test_unknown_paths_collapse_into_one_series_so_scanners_cannot_blow_up_cardinality() -> None:
    client = _client()

    for i in range(50):
        client.get(f"/wp-admin/{i}.php")
    text = _scrape(client)

    series = [ln for ln in text.splitlines() if ln.startswith("http_requests_total{")]
    unmatched = [ln for ln in series if 'route="unmatched"' in ln]
    assert len(unmatched) == 1
    assert unmatched[0].endswith(" 50")
    assert "wp-admin" not in text


def test_no_secret_or_personal_value_appears_in_the_scrape() -> None:
    client = _client()
    client.get("/api/v1/equipment", headers={**auth(), "X-Correlation-ID": "corr-abc-123"})
    client.get("/api/v1/spatial/markers/MK-SECRET-9", headers=auth())

    text = _scrape(client)

    for forbidden in (TOKEN_A, "corr-abc-123", "MK-SECRET-9", "user-a", "org-a", METRICS_TOKEN):
        assert forbidden not in text


def test_dependency_gauge_reflects_the_readiness_checks_at_scrape_time() -> None:
    state = {"database": True}
    client = _client(checks={"database": lambda: state["database"], "broker": lambda: True})

    first = _scrape(client)
    state["database"] = False
    second = _scrape(client)

    assert 'dependency_up{dependency="database"} 1' in first
    assert 'dependency_up{dependency="database"} 0' in second
    assert 'dependency_up{dependency="broker"} 1' in second


def test_a_check_that_raises_is_reported_as_down_and_leaks_nothing() -> None:
    def boom() -> bool:
        raise RuntimeError("password=hunter2 host=db.internal")

    text = _scrape(_client(checks={"database": boom, "broker": lambda: True}))

    assert 'dependency_up{dependency="database"} 0' in text
    assert "hunter2" not in text
    assert "db.internal" not in text


def test_every_sample_line_is_well_formed() -> None:
    client = _client()
    client.get("/health/ready")
    client.get("/api/v1/equipment", headers=auth())
    sample = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^{}\n]*\})? \S+$")

    lines = [ln for ln in _scrape(client).splitlines() if ln and not ln.startswith("#")]

    assert lines
    assert all(sample.match(ln) for ln in lines), lines
