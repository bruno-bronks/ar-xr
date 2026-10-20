"""SPEC-010: HACC Spatial contra a pilha REAL (API em container; fonte SIMULADA padrao).

Requisitos: REQ-HACC-001, REQ-HACC-002, REQ-HACC-003, REQ-HACC-004, REQ-HACC-005.
"""

import json

import pytest

from tests.integration._stack import (
    TOKEN_A,
    TOKEN_B,
    api,
    compose,
    requires_stack,
    wait_until,
)

pytestmark = [pytest.mark.integration, requires_stack]

NURSE_A = "demo-nurse-a"
NURSE_B = "demo-nurse-b"


def _ready() -> bool:
    return api("/api/v1/equipment")[0] == 200


def test_nurse_gets_simulated_wards_and_beds_over_real_http() -> None:
    wait_until(lambda: _ready() or None, 30, what="API pronta")

    status, wards = api("/api/v1/hacc/wards", NURSE_A)
    beds_status, beds = api("/api/v1/hacc/wards/WARD-UTI/beds", NURSE_A)

    assert status == beds_status == 200
    assert sorted(w["ward_id"] for w in wards) == ["WARD-A1", "WARD-UTI"]
    by_id = {b["bed_id"]: b for b in beds["beds"]}
    assert by_id["U-03"]["status"] == "OFFLINE"  # leito mudo da simulacao
    status_a1, a1 = api("/api/v1/hacc/wards/WARD-A1/beds", NURSE_A)
    assert {b["bed_id"]: b for b in a1["beds"]}["A1-06"]["status"] == "UNKNOWN"
    assert status_a1 == 200


def test_scope_and_org_segregation_over_real_http() -> None:
    assert api("/api/v1/hacc/wards", token=None)[0] == 401
    assert api("/api/v1/hacc/wards", TOKEN_A) == (
        403,
        {"detail": "forbidden"},
    )  # operador sem escopo
    assert api("/api/v1/hacc/wards", TOKEN_B)[0] == 403
    assert [w["ward_id"] for w in api("/api/v1/hacc/wards", NURSE_B)[1]] == ["WARD-B1"]
    foreign = api("/api/v1/hacc/wards/WARD-B1/beds", NURSE_A)
    missing = api("/api/v1/hacc/wards/WARD-NOPE/beds", NURSE_A)
    assert foreign == missing == (404, {"detail": "not found"})


def test_responses_carry_no_personal_or_clinical_fields() -> None:
    _, beds = api("/api/v1/hacc/wards/WARD-A1/beds", NURSE_A)
    rendered = json.dumps(beds).lower()

    for forbidden in ("cpf", "nome", "paciente", "patient", "diagnos", "prontuario", "heart"):
        assert forbidden not in rendered
    for bed in beds["beds"]:
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


def test_container_logs_have_hacc_metadata_but_no_bed_state() -> None:
    api("/api/v1/hacc/wards", NURSE_A)
    api("/api/v1/hacc/wards/WARD-A1/beds", NURSE_A)

    logs = compose("logs", "--no-color", "api").stdout
    hacc_lines = [line for line in logs.splitlines() if "app.hacc" in line or "hacc." in line]

    assert hacc_lines
    joined = "\n".join(hacc_lines)
    for secret in ("Leito 01", "iv_pump_alarm", "bed_exit_alarm", "A1-01"):
        assert secret not in joined
