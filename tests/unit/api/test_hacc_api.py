"""SPEC-010 · REQ-HACC-001, REQ-HACC-002, REQ-HACC-004, REQ-HACC-005: /api/v1/hacc/*.

Autenticacao, escopo hacc:read (403), segregacao por organizacao (404 uniforme, imposta no nosso lado),
estado por regra, 503 sem vazamento, somente GET e auditoria sem dados de leito.
"""

import json
import logging
from typing import Any

import pytest
from spatial_hacc.models import BedRecord, FlagsRecord, WardRecord
from spatial_hacc.simulated import SimulatedHaccSource
from spatial_hacc.source import HaccUnavailable

from tests.unit.api._app import NOW, auth, make_app, make_client

NURSE_A = "demo-nurse-a"
NURSE_B = "demo-nurse-b"
OPERATOR_A = "demo-operator-a"


def _client(**options: Any) -> Any:
    return make_client(hacc=SimulatedHaccSource(lambda: NOW), **options)


def _quiet(**kw: bool) -> FlagsRecord:
    base = {
        "bed_exit_alarm": False,
        "iv_pump_alarm": False,
        "call_button": False,
        "cleaning_due": False,
    }
    return FlagsRecord(**{**base, **kw})


def _bed(bed_id: str, ward: str, tenant: str, x: int, y: int, **kw: Any) -> BedRecord:
    return BedRecord(
        bed_id=bed_id,
        ward_id=ward,
        tenant_id=tenant,
        label=f"Leito {bed_id}",
        x=x,
        y=y,
        occupied=kw.pop("occupied", True),
        flags=_quiet(**kw.pop("flags", {})),
        observed_at=kw.pop("observed_at", NOW),
    )


class FakeSource:
    def __init__(
        self, wards: list[WardRecord], beds: list[BedRecord], error: Exception | None = None
    ):
        self.wards, self.beds, self.error = wards, beds, error

    def list_wards(self) -> list[WardRecord]:
        if self.error:
            raise self.error
        return self.wards

    def list_beds(self, ward_id: str) -> list[BedRecord]:
        if self.error:
            raise self.error
        return [b for b in self.beds if b.ward_id == ward_id]


ROUTES = ["/api/v1/hacc/wards", "/api/v1/hacc/wards/WARD-A1/beds"]


# --- autenticacao e escopo (REQ-HACC-004) --------------------------------------------------


@pytest.mark.parametrize("path", ROUTES)
def test_requires_authentication(path: str) -> None:
    response = _client().get(path)

    assert response.status_code == 401
    assert response.json() == {"detail": "not authenticated"}


@pytest.mark.parametrize("path", ROUTES)
@pytest.mark.parametrize("token", [OPERATOR_A, "demo-operator-b"])
def test_authenticated_user_without_scope_gets_403_and_no_data(path: str, token: str) -> None:
    response = _client().get(path, headers=auth(token))

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}


def test_403_is_audited_without_bed_data(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        _client().get("/api/v1/hacc/wards", headers=auth(OPERATOR_A))

    forbidden = [r for r in caplog.records if r.__dict__.get("outcome") == "forbidden"]
    assert forbidden
    assert forbidden[0].__dict__["user_id"] == "user-a"
    assert forbidden[0].__dict__["action"] == "hacc.access"


# --- segregacao por organizacao (REQ-HACC-001/004) ------------------------------------------


def test_each_org_sees_only_its_own_wards() -> None:
    client = _client()

    a = client.get("/api/v1/hacc/wards", headers=auth(NURSE_A)).json()
    b = client.get("/api/v1/hacc/wards", headers=auth(NURSE_B)).json()

    assert sorted(w["ward_id"] for w in a) == ["WARD-A1", "WARD-UTI"]
    assert [w["ward_id"] for w in b] == ["WARD-B1"]


def test_other_orgs_ward_is_indistinguishable_from_a_nonexistent_one() -> None:
    client = _client()

    foreign = client.get("/api/v1/hacc/wards/WARD-B1/beds", headers=auth(NURSE_A))
    reverse = client.get("/api/v1/hacc/wards/WARD-A1/beds", headers=auth(NURSE_B))
    missing = client.get("/api/v1/hacc/wards/WARD-NOPE/beds", headers=auth(NURSE_A))

    assert foreign.status_code == reverse.status_code == missing.status_code == 404
    assert foreign.json() == reverse.json() == missing.json() == {"detail": "not found"}


@pytest.mark.parametrize("ward_id", ["..%2Fetc", "a%20b", "x" * 65, "w;drop", "w%00"])
def test_malformed_ward_ids_are_404(ward_id: str) -> None:
    response = _client().get(f"/api/v1/hacc/wards/{ward_id}/beds", headers=auth(NURSE_A))

    assert response.status_code == 404
    assert response.json() == {"detail": "not found"}


def test_tenant_is_enforced_here_even_if_the_hacc_returns_foreign_records() -> None:
    own = WardRecord(ward_id="W-OWN", tenant_id="org-a", name="Propria", width=2, height=1)
    foreign = WardRecord(ward_id="W-FOR", tenant_id="org-b", name="Alheia", width=2, height=1)
    beds = [
        _bed("B-OWN", "W-OWN", "org-a", 1, 1),
        _bed("B-LEAK", "W-OWN", "org-b", 2, 1),  # leito de outro tenant dentro da ala propria
        _bed("B-FOR", "W-FOR", "org-b", 1, 1),
    ]
    client = make_client(hacc=FakeSource([own, foreign], beds))

    wards = client.get("/api/v1/hacc/wards", headers=auth(NURSE_A)).json()
    own_beds = client.get("/api/v1/hacc/wards/W-OWN/beds", headers=auth(NURSE_A)).json()
    foreign_beds = client.get("/api/v1/hacc/wards/W-FOR/beds", headers=auth(NURSE_A))

    assert [w["ward_id"] for w in wards] == ["W-OWN"]
    assert wards[0]["bed_count"] == 1
    assert [b["bed_id"] for b in own_beds["beds"]] == ["B-OWN"]
    assert foreign_beds.status_code == 404
    assert "B-LEAK" not in json.dumps(own_beds)


# --- estado por regra e formato (REQ-HACC-005) -----------------------------------------------


def test_beds_carry_server_computed_status_alerts_and_positions() -> None:
    body = _client().get("/api/v1/hacc/wards/WARD-UTI/beds", headers=auth(NURSE_A)).json()

    assert body["ward"] == {"ward_id": "WARD-UTI", "name": "UTI (demo)", "width": 2, "height": 2}
    assert body["evaluated_at"].endswith("Z")
    beds = {b["bed_id"]: b for b in body["beds"]}
    assert [(b["y"], b["x"]) for b in body["beds"]] == sorted(
        (b["y"], b["x"]) for b in body["beds"]
    )
    assert beds["U-03"]["status"] == "OFFLINE"  # leitura velha
    assert beds["U-03"]["alerts"] == [{"severity": "OFFLINE", "rule": "offline"}]
    assert body["status"] in {"ALERT", "OFFLINE"}
    for bed in beds.values():
        assert set(bed) == {
            "bed_id",
            "label",
            "x",
            "y",
            "occupied",
            "status",
            "observed_at",
            "alerts",
        }


def test_bed_without_reading_is_unknown_never_normal_and_ward_status_is_the_worst() -> None:
    ward = WardRecord(ward_id="W", tenant_id="org-a", name="W", width=2, height=1)
    beds = [
        _bed("B-OK", "W", "org-a", 1, 1),
        _bed("B-NONE", "W", "org-a", 2, 1, observed_at=None),
    ]
    client = make_client(hacc=FakeSource([ward], beds))

    body = client.get("/api/v1/hacc/wards/W/beds", headers=auth(NURSE_A)).json()
    summary = client.get("/api/v1/hacc/wards", headers=auth(NURSE_A)).json()

    statuses = {b["bed_id"]: b["status"] for b in body["beds"]}
    assert statuses == {"B-OK": "NORMAL", "B-NONE": "UNKNOWN"}
    assert body["status"] == "UNKNOWN"
    assert summary[0]["status"] == "UNKNOWN"
    assert summary[0]["alert_count"] == 0


def test_alarm_dominates_and_alert_count_sums_effective_alerts() -> None:
    ward = WardRecord(ward_id="W", tenant_id="org-a", name="W", width=3, height=1)
    beds = [
        _bed("B1", "W", "org-a", 1, 1, flags={"iv_pump_alarm": True, "call_button": True}),
        _bed("B2", "W", "org-a", 2, 1, flags={"bed_exit_alarm": True}, occupied=False),
        _bed("B3", "W", "org-a", 3, 1, flags={"cleaning_due": True}),
    ]
    client = make_client(hacc=FakeSource([ward], beds))

    summary = client.get("/api/v1/hacc/wards", headers=auth(NURSE_A)).json()[0]

    assert summary["status"] == "ALERT"
    assert summary["bed_count"] == 3
    assert (
        summary["alert_count"] == 3
    )  # iv + call (B1) + cleaning (B3); saida em leito vazio ignorada


def test_ward_without_beds_is_unknown_not_normal() -> None:
    ward = WardRecord(ward_id="W", tenant_id="org-a", name="W", width=1, height=1)
    client = make_client(hacc=FakeSource([ward], []))

    assert client.get("/api/v1/hacc/wards", headers=auth(NURSE_A)).json()[0]["status"] == "UNKNOWN"


def test_status_changes_with_the_clock() -> None:
    from tests.unit.api._app import Clock

    clock = Clock()
    client = make_client(hacc=SimulatedHaccSource(clock), clock=clock)

    seen: set[str] = set()
    for _ in range(8):
        seen.add(
            client.get("/api/v1/hacc/wards/WARD-A1/beds", headers=auth(NURSE_A)).json()["status"]
        )
        clock.advance(15)

    # a ala A1 tem um leito sem leitura (UNKNOWN) e alarmes nas fases 1 e 3 (ALERT)
    assert seen == {"ALERT", "UNKNOWN"}


# --- falha da fonte e somente leitura (REQ-HACC-002) -----------------------------------------


@pytest.mark.parametrize("path", ROUTES)
def test_source_failure_is_a_uniform_503_without_leaking(path: str) -> None:
    client = make_client(
        hacc=FakeSource([], [], error=HaccUnavailable("http://segredo:9/token=abc"))
    )

    response = client.get(path, headers=auth(NURSE_A))

    assert response.status_code == 503
    assert response.json() == {"detail": "hacc source unavailable"}
    assert "segredo" not in response.text


def test_only_get_routes_exist_under_hacc() -> None:
    paths = make_app(hacc=SimulatedHaccSource(lambda: NOW)).openapi()["paths"]
    hacc = {path: set(item) for path, item in paths.items() if path.startswith("/api/v1/hacc")}

    assert set(hacc) == {"/api/v1/hacc/wards", "/api/v1/hacc/wards/{ward_id}/beds"}
    assert all(methods == {"get"} for methods in hacc.values())


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_write_methods_are_not_allowed(method: str) -> None:
    client = _client()

    response = getattr(client, method)("/api/v1/hacc/wards", headers=auth(NURSE_A))

    assert response.status_code == 405


# --- auditoria e log seguros (REQ-HACC-004) ---------------------------------------------------


def test_audit_and_logs_never_contain_bed_state(caplog: pytest.LogCaptureFixture) -> None:
    client = _client()

    with caplog.at_level(logging.DEBUG):
        client.get("/api/v1/hacc/wards", headers=auth(NURSE_A))
        client.get("/api/v1/hacc/wards/WARD-A1/beds", headers=auth(NURSE_A))
        client.get("/api/v1/hacc/wards/WARD-B1/beds", headers=auth(NURSE_A))

    rendered = "\n".join(
        json.dumps(r.__dict__, default=str) + r.getMessage() for r in caplog.records
    )
    for secret in ("Leito 01", "A1-01", "iv_pump_alarm", "bed_exit_alarm", '"ALERT"', "UNKNOWN"):
        assert secret not in rendered, secret
    actions = [r.__dict__.get("action") for r in caplog.records if r.name == "app.audit"]
    assert actions.count("hacc.wards.list") == 1
    assert actions.count("hacc.beds.list") == 2
    outcomes = [
        r.__dict__["outcome"]
        for r in caplog.records
        if r.__dict__.get("action") == "hacc.beds.list"
    ]
    assert outcomes == ["allowed", "not_found"]
    meta = [r for r in caplog.records if r.name == "app.hacc"]
    assert meta
    assert all("beds" in r.__dict__ for r in meta)
