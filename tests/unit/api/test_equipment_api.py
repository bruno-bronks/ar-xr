"""SPEC-006 · REQ-MNT-006, REQ-MNT-001, REQ-MNT-002, REQ-SEC-003, REQ-SEC-004.

Autenticacao, isolamento por organizacao, twin, alertas, markers, rate limit e auditoria — contra o
repositorio em memoria (a mesma bateria roda contra PostgreSQL em tests/integration/test_api_postgres.py).
"""

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from spatial_domain.status import Quality
from spatial_storage.memory import InMemoryRepository
from spatial_storage.postgres import PostgresRepository
from spatial_storage.repository import Repository
from spatial_storage.seed_data import SEED

from tests.unit.api._app import (
    TOKEN_A,
    TOKEN_B,
    Clock,
    auth,
    feed,
    make_app,
    make_client,
    new_repo,
    reading,
    set_backend,
)


@pytest.fixture(
    autouse=True,
    params=["memory", pytest.param("postgres", marks=pytest.mark.integration)],
)
def _backend(request: pytest.FixtureRequest) -> Iterator[None]:
    """A MESMA bateria roda contra o dublê em memoria e contra o PostgreSQL real (ADR-0002)."""
    if request.param == "memory":
        set_backend(lambda: InMemoryRepository(SEED))
    else:
        engine = request.getfixturevalue("pg_engine")
        set_backend(lambda: PostgresRepository(engine))
    yield
    set_backend(lambda: InMemoryRepository(SEED))


READ_ROUTES = [
    "/api/v1/equipment",
    "/api/v1/equipment/EQ-001",
    "/api/v1/equipment/EQ-001/telemetry/latest",
    "/api/v1/equipment/EQ-001/twin",
    "/api/v1/equipment/EQ-001/alerts",
    "/api/v1/spatial/markers/QR-EQ-001",
    "/api/v1/equipment/EQ-NOPE/twin",  # inexistente tambem exige autenticacao
]


def _full(repo: Repository, eq: str = "EQ-001", temp: float = 50.0, vib: float = 1.0) -> None:
    feed(repo, reading(eq, "temperature", temp), reading(eq, "vibration", vib))


def _strip(response: Any) -> tuple[int, Any, dict[str, str]]:
    headers = {k: v for k, v in response.headers.items() if k.lower() != "x-correlation-id"}
    return response.status_code, response.json(), headers


# --- REQ-SEC-003: autenticacao -----------------------------------------------------------


@pytest.mark.parametrize("path", READ_ROUTES)
def test_every_api_route_requires_authentication(path: str) -> None:
    response = make_client().get(path)

    assert response.status_code == 401
    assert response.json() == {"detail": "not authenticated"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header",
    [
        "Bearer wrong-token",
        "Bearer ",
        "Bearer",
        "Basic demo-operator-a",
        "demo-operator-a",
        "bearer  x",
    ],
)
def test_invalid_credentials_get_the_same_401(header: str) -> None:
    response = make_client().get("/api/v1/equipment", headers={"Authorization": header})

    assert response.status_code == 401
    assert response.json() == {"detail": "not authenticated"}


def test_scheme_is_case_insensitive_but_token_is_exact() -> None:
    client = make_client()

    assert (
        client.get(
            "/api/v1/equipment", headers={"Authorization": "bearer demo-operator-a"}
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/v1/equipment", headers={"Authorization": "Bearer DEMO-OPERATOR-A"}
        ).status_code
        == 401
    )


def test_health_endpoints_remain_public() -> None:
    client = make_client()

    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_assistant_endpoint_is_not_routed_until_phase_3() -> None:
    response = make_client().post("/api/v1/assistant/questions", json={}, headers=auth())

    assert response.status_code in {404, 405}


# --- REQ-MNT-006: leitura e isolamento ----------------------------------------------------


def test_list_shows_only_own_org_and_unknown_status_without_data() -> None:
    client = make_client()

    own = client.get("/api/v1/equipment", headers=auth(TOKEN_A)).json()
    other = client.get("/api/v1/equipment", headers=auth(TOKEN_B)).json()

    assert [e["id"] for e in own] == ["EQ-001", "EQ-002", "EQ-003"]
    assert {e["status"] for e in own} == {"UNKNOWN"}  # ausencia de dado nunca vira NORMAL
    assert [e["id"] for e in other] == ["EQ-B01"]
    assert own[0] == {
        "id": "EQ-001",
        "name": "Compressor de ar 01",
        "type": "Compressor de ar",
        "location": "Galpao A - Linha 1",
        "last_seen_at": None,
        "status": "UNKNOWN",
    }


def test_detail_of_other_org_is_identical_to_nonexistent() -> None:
    client = make_client()

    foreign = client.get("/api/v1/equipment/EQ-001", headers=auth(TOKEN_B))
    missing = client.get("/api/v1/equipment/EQ-DOES-NOT-EXIST", headers=auth(TOKEN_B))

    assert foreign.status_code == 404
    assert _strip(foreign) == _strip(missing)
    assert foreign.json() == {"detail": "not found"}


@pytest.mark.parametrize("suffix", ["", "/telemetry/latest", "/twin", "/alerts"])
def test_all_equipment_subresources_hide_other_orgs_equipment(suffix: str) -> None:
    repo = new_repo()
    _full(repo)
    client = make_client(repo=repo)

    foreign = client.get(f"/api/v1/equipment/EQ-001{suffix}", headers=auth(TOKEN_B))
    missing = client.get(f"/api/v1/equipment/EQ-ZZZ{suffix}", headers=auth(TOKEN_B))

    assert foreign.status_code == 404
    assert _strip(foreign) == _strip(missing)
    assert "temperature" not in foreign.text


@pytest.mark.parametrize(
    "bad_id", ["x" * 65, "a b", "..", "%3Cscript%3E", "a%00b", "é", "EQ-001%2F..%2FEQ-002"]
)
def test_malformed_ids_are_uniform_404_and_never_reflected(bad_id: str) -> None:
    response = make_client().get(f"/api/v1/equipment/{bad_id}", headers=auth())

    assert response.status_code == 404
    assert response.json() == {"detail": "not found"}
    assert bad_id not in response.text


def test_latest_telemetry_is_empty_list_without_data_and_complete_with_data() -> None:
    repo = new_repo()
    client = make_client(repo=repo)
    assert client.get("/api/v1/equipment/EQ-001/telemetry/latest", headers=auth()).json() == []

    feed(repo, reading("EQ-001", "temperature", 61.5, event_id="t1"))
    [item] = client.get("/api/v1/equipment/EQ-001/telemetry/latest", headers=auth()).json()

    assert item == {
        "equipment_id": "EQ-001",
        "sensor_type": "temperature",
        "value": 61.5,
        "unit": "celsius",
        "observed_at": "2026-10-19T12:00:29Z",
        "received_at": "2026-10-19T12:00:30Z",
        "quality": "GOOD",
        "event_id": "t1",
    }


# --- REQ-MNT-002: twin (SPEC-002 com o relogio do servidor) -------------------------------


def test_twin_normal_with_full_fresh_coverage_and_sensor_details() -> None:
    repo = new_repo()
    _full(repo, temp=50.0, vib=1.0)

    twin = make_client(repo=repo).get("/api/v1/equipment/EQ-001/twin", headers=auth()).json()

    assert twin["status"] == "NORMAL"
    assert twin["equipment_id"] == "EQ-001"
    assert twin["evaluated_at"] == "2026-10-19T12:00:30Z"
    assert twin["offline_after_seconds"] == 30
    temperature = next(s for s in twin["sensors"] if s["sensor_type"] == "temperature")
    assert temperature == {
        "sensor_type": "temperature",
        "unit": "celsius",
        "value": 50.0,
        "observed_at": "2026-10-19T12:00:29Z",
        "quality": "GOOD",
        "warn": 85.0,
        "crit": 100.0,
        "valid": True,
    }


def test_twin_without_data_is_unknown_never_normal() -> None:
    twin = make_client().get("/api/v1/equipment/EQ-001/twin", headers=auth()).json()

    assert twin["status"] == "UNKNOWN"
    assert [s["value"] for s in twin["sensors"]] == [None, None]
    assert [s["valid"] for s in twin["sensors"]] == [False, False]


@pytest.mark.parametrize(
    ("temp", "expected"),
    [(85.0, "NORMAL"), (85.1, "WARNING"), (100.0, "WARNING"), (100.1, "CRITICAL")],
)
def test_twin_status_boundaries_follow_strict_greater_than(temp: float, expected: str) -> None:
    repo = new_repo()
    _full(repo, temp=temp)

    twin = make_client(repo=repo).get("/api/v1/equipment/EQ-001/twin", headers=auth()).json()

    assert twin["status"] == expected


def test_twin_becomes_offline_when_time_passes_without_data() -> None:
    repo, clock = new_repo(), Clock()
    _full(repo, temp=500.0)  # valor critico, mas...
    client = make_client(repo=repo, clock=clock)
    assert (
        client.get("/api/v1/equipment/EQ-001/twin", headers=auth()).json()["status"] == "CRITICAL"
    )

    clock.advance(30)  # 31 s desde a ultima leitura (observada 1 s antes de NOW)
    twin = client.get("/api/v1/equipment/EQ-001/twin", headers=auth()).json()

    assert twin["status"] == "OFFLINE"  # offline tem precedencia sobre o limiar


def test_twin_marks_stale_or_bad_sensor_invalid_and_status_unknown() -> None:
    repo = new_repo()
    feed(
        repo,
        reading("EQ-001", "temperature", 50.0, age_s=1),
        reading("EQ-001", "vibration", 1.0, age_s=1, quality=Quality.BAD),
    )

    twin = make_client(repo=repo).get("/api/v1/equipment/EQ-001/twin", headers=auth()).json()

    vib = next(s for s in twin["sensors"] if s["sensor_type"] == "vibration")
    assert vib["valid"] is False
    assert vib["quality"] == "BAD"
    assert twin["status"] == "UNKNOWN"


def test_equipment_status_in_list_matches_twin_and_last_seen_is_exposed() -> None:
    repo = new_repo()
    _full(repo, "EQ-002", temp=95.0)
    client = make_client(repo=repo)

    listed = {e["id"]: e for e in client.get("/api/v1/equipment", headers=auth()).json()}

    assert listed["EQ-002"]["status"] == "CRITICAL"
    assert listed["EQ-002"]["last_seen_at"] == "2026-10-19T12:00:29Z"
    assert listed["EQ-001"]["status"] == "UNKNOWN"


# --- alertas deterministicos (D-010) -------------------------------------------------------


def test_alerts_critical_warning_and_none() -> None:
    repo = new_repo()
    _full(repo, "EQ-001", temp=101.0, vib=6.0)  # temp critica, vibracao em warning
    _full(repo, "EQ-002", temp=10.0, vib=1.0)  # normal
    client = make_client(repo=repo)

    alerts = client.get("/api/v1/equipment/EQ-001/alerts", headers=auth()).json()

    by_rule = {a["rule"]: a for a in alerts}
    assert set(by_rule) == {"temperature>crit", "vibration>warn"}
    assert by_rule["temperature>crit"]["severity"] == "CRITICAL"
    assert by_rule["temperature>crit"]["value"] == 101.0
    assert by_rule["temperature>crit"]["limit"] == 100.0
    assert by_rule["vibration>warn"]["severity"] == "WARNING"
    assert by_rule["temperature>crit"]["raised_at"] == "2026-10-19T12:00:29Z"
    assert client.get("/api/v1/equipment/EQ-002/alerts", headers=auth()).json() == []


def test_exact_limit_and_bad_quality_do_not_alert() -> None:
    repo = new_repo()
    feed(
        repo,
        reading("EQ-001", "temperature", 85.0),  # exatamente no warn
        reading("EQ-001", "vibration", 99.0, quality=Quality.BAD),  # defeituoso
    )

    assert (
        make_client(repo=repo).get("/api/v1/equipment/EQ-001/alerts", headers=auth()).json() == []
    )


def test_offline_equipment_raises_a_single_offline_alert() -> None:
    repo, clock = new_repo(), Clock()
    _full(repo, temp=500.0)
    client = make_client(repo=repo, clock=clock)
    clock.advance(120)

    alerts = client.get("/api/v1/equipment/EQ-001/alerts", headers=auth()).json()

    assert [(a["severity"], a["rule"]) for a in alerts] == [("OFFLINE", "offline")]
    assert alerts[0]["raised_at"] == "2026-10-19T12:00:59Z"  # ultima leitura (12:00:29) + 30 s


# --- REQ-MNT-001: marker/QR ---------------------------------------------------------------


def test_each_test_qr_resolves_to_its_equipment() -> None:
    client = make_client()

    for marker, equipment in (
        ("QR-EQ-001", "EQ-001"),
        ("QR-EQ-002", "EQ-002"),
        ("QR-EQ-003", "EQ-003"),
    ):
        response = client.get(f"/api/v1/spatial/markers/{marker}", headers=auth())
        assert response.status_code == 200
        assert response.json()["id"] == equipment


def test_foreign_marker_and_unknown_marker_are_indistinguishable() -> None:
    client = make_client()

    foreign = client.get("/api/v1/spatial/markers/QR-EQ-B01", headers=auth(TOKEN_A))
    unknown = client.get("/api/v1/spatial/markers/QR-NOT-A-THING", headers=auth(TOKEN_A))
    reverse = client.get("/api/v1/spatial/markers/QR-EQ-001", headers=auth(TOKEN_B))

    assert foreign.status_code == unknown.status_code == reverse.status_code == 404
    assert _strip(foreign) == _strip(unknown) == _strip(reverse)


@pytest.mark.parametrize(
    "hostile", ["x" * 129, "' OR 1=1 --", "QR-EQ-001%00", "%F0%9F%98%80", "a b"]
)
def test_hostile_markers_never_error_or_leak(hostile: str) -> None:
    response = make_client().get(f"/api/v1/spatial/markers/{hostile}", headers=auth())

    assert response.status_code == 404
    assert response.json() == {"detail": "not found"}


def test_marker_resolution_is_rate_limited_per_principal() -> None:
    clock = Clock()
    client = make_client(clock=clock, marker_rate_limit=3)

    codes = [
        client.get("/api/v1/spatial/markers/QR-GUESS", headers=auth(TOKEN_A)).status_code
        for _ in range(5)
    ]
    blocked = client.get("/api/v1/spatial/markers/QR-EQ-001", headers=auth(TOKEN_A))

    assert codes == [404, 404, 404, 429, 429]  # tentativas de enumeracao esbarram no limite
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "rate limit exceeded"}
    assert int(blocked.headers["retry-after"]) >= 1
    assert client.get("/api/v1/spatial/markers/QR-EQ-B01", headers=auth(TOKEN_B)).status_code == 200

    clock.advance(61)
    assert client.get("/api/v1/spatial/markers/QR-EQ-001", headers=auth(TOKEN_A)).status_code == 200


def test_rate_limit_does_not_apply_to_equipment_reads() -> None:
    client = make_client(marker_rate_limit=1)

    codes = {client.get("/api/v1/equipment", headers=auth()).status_code for _ in range(5)}

    assert codes == {200}


# --- REQ-SEC-004: auditoria ----------------------------------------------------------------


def test_audit_log_records_who_what_outcome_without_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = make_client()

    with caplog.at_level(logging.INFO, logger="app.audit"):
        client.get(
            "/api/v1/equipment/EQ-001", headers={**auth(TOKEN_A), "X-Correlation-ID": "audit-1"}
        )
        client.get("/api/v1/equipment/EQ-001", headers=auth(TOKEN_B))

    records = [r.__dict__ for r in caplog.records if r.name == "app.audit"]
    assert len(records) == 2
    allowed, denied = records
    assert (allowed["user_id"], allowed["org_id"]) == ("user-a", "org-a")
    assert (allowed["action"], allowed["resource"], allowed["outcome"]) == (
        "equipment.get",
        "equipment/EQ-001",
        "allowed",
    )
    assert allowed["correlation_id"] == "audit-1"
    assert (denied["user_id"], denied["outcome"]) == ("user-b", "not_found")
    assert TOKEN_A not in caplog.text
    assert TOKEN_B not in caplog.text


def test_audit_log_of_rate_limited_marker_lookup(caplog: pytest.LogCaptureFixture) -> None:
    client = make_client(marker_rate_limit=1)

    with caplog.at_level(logging.INFO, logger="app.audit"):
        client.get("/api/v1/spatial/markers/QR-EQ-001", headers=auth())
        client.get("/api/v1/spatial/markers/QR-EQ-001", headers=auth())

    outcomes = [r.__dict__["outcome"] for r in caplog.records if r.name == "app.audit"]
    assert outcomes == ["allowed", "rate_limited"]


def test_audit_never_logs_the_requested_marker_value_for_misses(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="app.audit"):
        make_client().get("/api/v1/spatial/markers/QR-SECRET-GUESS", headers=auth())

    [record] = [r for r in caplog.records if r.name == "app.audit"]
    assert record.__dict__["outcome"] == "not_found"
    assert "QR-SECRET-GUESS" not in caplog.text


# --- cabecalhos de seguranca e painel ------------------------------------------------------


def test_api_responses_are_not_cacheable_and_nosniff() -> None:
    response = make_client().get("/api/v1/equipment", headers=auth())

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_panel_is_served_with_a_strict_content_security_policy() -> None:
    response = make_client().get("/panel/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "'unsafe-inline'" not in csp.split("style-src")[0]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_panel_does_not_load_external_resources() -> None:
    html = make_client().get("/panel/").text

    assert "http://" not in html
    assert "https://" not in html


def test_apps_are_independent() -> None:
    first, second = make_app(), make_app()

    assert first.state.repo is not second.state.repo


def test_panel_dir_lookup_survives_shallow_container_paths(tmp_path: Any) -> None:
    """Regressao: na imagem Docker o modulo fica em /srv/app (poucos niveis acima)."""
    from pathlib import Path

    from app.main import _find_panel_dir

    _find_panel_dir(None, module_file=Path("/srv/app/main.py"))  # nao pode levantar IndexError
    panel = tmp_path / "custom"
    panel.mkdir()
    (panel / "index.html").write_text("<html></html>")
    assert _find_panel_dir(str(panel), module_file=Path("/srv/app/main.py")) == panel
