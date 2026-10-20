"""SPEC-010 · REQ-HACC-003 (minimizacao), REQ-HACC-001 (somente dados simulados), REQ-HACC-005.

Modelos estritos (campo extra rejeita o payload inteiro) e fonte simulada deterministica.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError
from spatial_domain.beds import BedFlags, BedReading, BedStatus, evaluate_bed
from spatial_hacc.models import BedRecord, FlagsRecord, WardRecord
from spatial_hacc.simulated import SimulatedHaccSource

NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)

VALID_BED: dict[str, Any] = {
    "bed_id": "BED-1",
    "ward_id": "WARD-1",
    "tenant_id": "org-a",
    "label": "Leito 1",
    "x": 1,
    "y": 1,
    "occupied": True,
    "observed_at": "2026-10-20T12:00:00Z",
    "flags": {
        "bed_exit_alarm": False,
        "iv_pump_alarm": False,
        "call_button": False,
        "cleaning_due": False,
    },
}
VALID_WARD: dict[str, Any] = {
    "ward_id": "WARD-1",
    "tenant_id": "org-a",
    "name": "Ala 1",
    "width": 3,
    "height": 2,
}


def _bed_json(**overrides: Any) -> str:
    return json.dumps({**VALID_BED, **overrides})


def test_valid_payloads_parse() -> None:
    bed = BedRecord.model_validate_json(_bed_json())
    ward = WardRecord.model_validate_json(json.dumps(VALID_WARD))

    assert bed.observed_at == NOW
    assert bed.flags == FlagsRecord(
        bed_exit_alarm=False, iv_pump_alarm=False, call_button=False, cleaning_due=False
    )
    assert ward.width == 3


def test_models_have_exactly_the_allow_listed_fields() -> None:
    """Qualquer campo novo (potencialmente identificavel) exige mudar este teste de proposito."""
    assert set(BedRecord.model_fields) == {
        "bed_id", "ward_id", "tenant_id", "label", "x", "y", "occupied", "flags", "observed_at",
    }  # fmt: skip
    assert set(WardRecord.model_fields) == {"ward_id", "tenant_id", "name", "width", "height"}
    assert set(FlagsRecord.model_fields) == {
        "bed_exit_alarm", "iv_pump_alarm", "call_button", "cleaning_due",
    }  # fmt: skip


@pytest.mark.parametrize(
    "field",
    ["name", "patient_name", "cpf", "mrn", "diagnosis", "heart_rate", "birth_date", "notes", "id"],
)
def test_unknown_fields_reject_the_whole_bed_payload(field: str) -> None:
    with pytest.raises(ValidationError):
        BedRecord.model_validate_json(_bed_json(**{field: "valor"}))


def test_unknown_field_inside_flags_is_rejected_too() -> None:
    flags = {**VALID_BED["flags"], "temperature": 38.5}

    with pytest.raises(ValidationError):
        BedRecord.model_validate_json(_bed_json(flags=flags))


def test_one_bad_bed_rejects_the_entire_list() -> None:
    adapter = TypeAdapter(list[BedRecord])
    payload = json.dumps([VALID_BED, {**VALID_BED, "bed_id": "BED-2", "cpf": "000"}])

    with pytest.raises(ValidationError):
        adapter.validate_json(payload)


@pytest.mark.parametrize(
    "override",
    [
        {"bed_id": ""},
        {"bed_id": "a b"},
        {"bed_id": "x" * 65},
        {"ward_id": "../etc"},
        {"tenant_id": ""},
        {"label": ""},
        {"label": "l" * 41},
        {"x": 0},
        {"y": -1},
        {"x": 101},
        {"x": "1"},
        {"x": 1.5},
        {"occupied": "yes"},
        {"occupied": 1},
        {"observed_at": "2026-10-20T12:00:00"},  # sem fuso
        {"observed_at": "ontem"},
        {"flags": {"bed_exit_alarm": True}},  # faltando sinalizadores
    ],
)
def test_invalid_field_values_are_rejected(override: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        BedRecord.model_validate_json(_bed_json(**override))


def test_observed_at_may_be_null_meaning_no_reading() -> None:
    assert BedRecord.model_validate_json(_bed_json(observed_at=None)).observed_at is None


@pytest.mark.parametrize(
    "override", [{"width": 0}, {"height": 101}, {"name": ""}, {"name": "n" * 121}]
)
def test_invalid_ward_values_are_rejected(override: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        WardRecord.model_validate_json(json.dumps({**VALID_WARD, **override}))


# --- fonte simulada --------------------------------------------------------------------------


def _source(now: datetime = NOW) -> SimulatedHaccSource:
    return SimulatedHaccSource(lambda: now)


def test_simulated_data_is_deterministic_for_a_given_clock() -> None:
    assert _source().list_wards() == _source().list_wards()
    assert _source().list_beds("WARD-A1") == _source().list_beds("WARD-A1")


def test_simulated_wards_and_tenants() -> None:
    wards = {w.ward_id: w for w in _source().list_wards()}

    assert set(wards) == {"WARD-A1", "WARD-UTI", "WARD-B1"}
    assert {w.tenant_id for w in wards.values() if w.ward_id != "WARD-B1"} == {"org-a"}
    assert wards["WARD-B1"].tenant_id == "org-b"
    assert [len(_source().list_beds(w)) for w in ("WARD-A1", "WARD-UTI", "WARD-B1")] == [6, 4, 2]


def test_simulated_beds_fit_the_ward_grid_and_have_unique_positions_and_ids() -> None:
    source = _source()
    for ward in source.list_wards():
        beds = source.list_beds(ward.ward_id)
        assert all(1 <= b.x <= ward.width and 1 <= b.y <= ward.height for b in beds)
        assert len({(b.x, b.y) for b in beds}) == len(beds)
        assert all(b.ward_id == ward.ward_id and b.tenant_id == ward.tenant_id for b in beds)
    all_ids = [b.bed_id for w in source.list_wards() for b in source.list_beds(w.ward_id)]
    assert len(all_ids) == len(set(all_ids))


def test_unknown_ward_returns_no_beds() -> None:
    assert _source().list_beds("WARD-NOPE") == []


def test_simulated_cycle_exercises_every_status_over_a_minute() -> None:
    seen: set[BedStatus] = set()
    for step in range(0, 60, 5):
        now = NOW + timedelta(seconds=step)
        source = _source(now)
        for ward in source.list_wards():
            for bed in source.list_beds(ward.ward_id):
                f = bed.flags
                reading = BedReading(
                    bed.occupied,
                    BedFlags(f.bed_exit_alarm, f.iv_pump_alarm, f.call_button, f.cleaning_due),
                    bed.observed_at,
                )
                seen.add(evaluate_bed(reading, now))

    assert seen == set(BedStatus)


def test_simulated_dataset_has_no_personal_fields() -> None:
    dumped = json.dumps([b.model_dump(mode="json") for b in _source().list_beds("WARD-A1")])

    for forbidden in ("cpf", "nome", "patient", "paciente", "diagnos", "prontuario"):
        assert forbidden not in dumped.lower()
