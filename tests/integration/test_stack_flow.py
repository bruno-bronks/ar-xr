"""SPEC-005/006/007: fluxo REAL simulador -> broker -> worker -> PostgreSQL -> API (Compose no ar).

Requisitos: REQ-MNT-001, REQ-MNT-003, REQ-MNT-006, REQ-MNT-007, REQ-SIM-001, REQ-SEC-003.
"""

from datetime import UTC, datetime, timedelta

import pytest

from tests.integration._stack import TOKEN_A, TOKEN_B, api, requires_stack, wait_until

pytestmark = [pytest.mark.integration, requires_stack]


def test_simulator_data_reaches_the_api_fresh_and_complete() -> None:
    def fresh() -> list[dict[str, object]] | None:
        status, body = api("/api/v1/equipment")
        if status != 200 or len(body) != 3:
            return None
        return body if all(e["last_seen_at"] for e in body) else None

    equipment = wait_until(fresh, 60, what="3 equipamentos com last_seen_at")

    assert [e["id"] for e in equipment] == ["EQ-001", "EQ-002", "EQ-003"]
    for item in equipment:
        status, readings = api(f"/api/v1/equipment/{item['id']}/telemetry/latest")
        assert status == 200
        assert {r["sensor_type"] for r in readings} == {"temperature", "vibration"}
        newest = max(datetime.fromisoformat(r["observed_at"]) for r in readings)
        # a leitura vigente nunca regride, mas pode estar velha no dropout do EQ-003
        assert newest <= datetime.now(UTC) + timedelta(minutes=5)


def test_steady_equipment_is_normal_and_states_are_all_valid() -> None:
    def settled() -> dict[str, str] | None:
        status, body = api("/api/v1/equipment")
        return {e["id"]: e["status"] for e in body} if status == 200 else None

    states = wait_until(settled, 30, what="estados disponiveis")

    assert states["EQ-001"] == "NORMAL"  # cenario "steady"
    assert set(states.values()) <= {"NORMAL", "WARNING", "CRITICAL", "OFFLINE", "UNKNOWN"}


def test_authorization_is_enforced_over_real_http() -> None:
    assert api("/api/v1/equipment", token=None)[0] == 401
    assert api("/api/v1/equipment", token="invalid")[0] == 401
    assert [e["id"] for e in api("/api/v1/equipment", TOKEN_B)[1]] == ["EQ-B01"]

    foreign = api("/api/v1/equipment/EQ-001", TOKEN_B)
    missing = api("/api/v1/equipment/EQ-NOPE", TOKEN_B)
    assert foreign == missing == (404, {"detail": "not found"})
    assert api("/api/v1/equipment/EQ-001/twin", TOKEN_B)[0] == 404


def test_the_three_test_qr_codes_resolve_over_real_http() -> None:
    for marker, equipment in (
        ("QR-EQ-001", "EQ-001"),
        ("QR-EQ-002", "EQ-002"),
        ("QR-EQ-003", "EQ-003"),
    ):
        status, body = api(f"/api/v1/spatial/markers/{marker}")
        assert status == 200
        assert body["id"] == equipment
    assert api("/api/v1/spatial/markers/QR-EQ-B01", TOKEN_A)[0] == 404
    assert api("/api/v1/spatial/markers/QR-EQ-001", TOKEN_B)[0] == 404


def test_panel_is_served_by_the_api_container() -> None:
    import urllib.request

    from tests.integration._stack import BASE_URL

    assert BASE_URL is not None
    with urllib.request.urlopen(BASE_URL + "/panel/", timeout=5) as response:  # noqa: S310
        body = response.read().decode()
        assert response.status == 200
        assert "content-security-policy" in {k.lower() for k in response.headers}
    assert "Painel de equipamentos" in body
