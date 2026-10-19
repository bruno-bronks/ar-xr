"""SPEC-005 · REQ-MNT-003, REQ-MNT-001, REQ-MNT-007: suite de CONTRATO do repositorio.

Roda no dublê em memoria (sempre) e no PostgreSQL real (quando TEST_DATABASE_URL existe), garantindo
que as duas implementacoes tenham a mesma semantica (ADR-0002).
"""

import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from spatial_domain.markers import NOT_FOUND, Found, Registry
from spatial_domain.status import Quality
from spatial_domain.telemetry import TelemetryEvent
from spatial_storage.memory import InMemoryRepository
from spatial_storage.repository import RecordOutcome, Repository, UnknownEquipmentError
from spatial_storage.seed_data import SEED

T0 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)
RECEIVED = T0 + timedelta(seconds=1)


def _event(
    event_id: str = "e1",
    *,
    source: str = "sim",
    equipment_id: str = "EQ-001",
    sensor: str = "temperature",
    value: float = 50.0,
    observed_at: datetime = T0,
    quality: Quality = Quality.GOOD,
) -> TelemetryEvent:
    return TelemetryEvent(
        event_id=event_id,
        source=source,
        equipment_id=equipment_id,
        sensor_type=sensor,
        value=value,
        unit="celsius",
        observed_at=observed_at,
        quality=quality,
    )


@pytest.fixture(
    params=[
        "memory",
        pytest.param("postgres", marks=pytest.mark.integration),
    ]
)
def repo(request: pytest.FixtureRequest) -> Iterator[Repository]:
    if request.param == "memory":
        yield InMemoryRepository(SEED)
        return
    from spatial_storage.postgres import PostgresRepository

    engine = request.getfixturevalue("pg_engine")
    yield PostgresRepository(engine)


# --- leitura / seed (REQ-MNT-007) ----------------------------------------------------------


def test_seed_has_three_org_a_machines_plus_sentinel(repo: Repository) -> None:
    assert [e.id for e in repo.list_equipment("org-a")] == ["EQ-001", "EQ-002", "EQ-003"]
    assert [e.id for e in repo.list_equipment("org-b")] == ["EQ-B01"]
    assert repo.list_equipment("org-zzz") == []


def test_equipment_fields(repo: Repository) -> None:
    eq = repo.get_equipment("org-a", "EQ-001")

    assert eq is not None
    assert (eq.name, eq.type, eq.org_id) == ("Compressor de ar 01", "Compressor de ar", "org-a")
    assert eq.offline_after == timedelta(seconds=30)
    assert eq.last_seen_at is None


def test_get_equipment_is_isolated_by_org(repo: Repository) -> None:
    assert repo.get_equipment("org-b", "EQ-001") is None
    assert repo.get_equipment("org-a", "EQ-B01") is None
    assert repo.get_equipment("org-a", "EQ-NOPE") is None


def test_profile_per_equipment(repo: Repository) -> None:
    profile = repo.get_profile("EQ-002")

    assert profile is not None
    assert (profile["temperature"].warn, profile["temperature"].crit) == (70.0, 90.0)
    assert (profile["vibration"].warn, profile["vibration"].crit) == (4.0, 7.0)
    assert repo.get_profile("EQ-NOPE") is None


# --- markers (REQ-MNT-001, M1/M2/M4) --------------------------------------------------------


def test_each_test_qr_resolves_to_its_own_equipment_only(repo: Repository) -> None:
    for marker, equipment in (
        ("QR-EQ-001", "EQ-001"),
        ("QR-EQ-002", "EQ-002"),
        ("QR-EQ-003", "EQ-003"),
    ):
        found = repo.get_equipment_by_marker("org-a", marker)
        assert found is not None
        assert found.id == equipment


def test_marker_of_other_org_and_unknown_marker_are_indistinguishable(repo: Repository) -> None:
    assert repo.get_equipment_by_marker("org-a", "QR-EQ-B01") is None
    assert repo.get_equipment_by_marker("org-a", "QR-UNKNOWN") is None
    assert repo.get_equipment_by_marker("org-b", "QR-EQ-001") is None


@pytest.mark.parametrize("hostile", ["", "' OR 1=1 --", "%", "QR-EQ-001\x00", "😀", "A" * 5000])
def test_hostile_marker_is_just_not_found(repo: Repository, hostile: str) -> None:
    assert repo.get_equipment_by_marker("org-a", hostile) is None


def test_repository_agrees_with_domain_reference_model(repo: Repository) -> None:
    registry = Registry(
        marker_of={e.marker_id: e.id for e in SEED.equipment if e.marker_id},
        owner={e.id: e.org_id for e in SEED.equipment},
    )
    markers = [e.marker_id for e in SEED.equipment] + ["QR-UNKNOWN", "", "qr-eq-001"]
    for org in ("org-a", "org-b", "org-zzz"):
        for marker in markers:
            expected = registry.resolve(marker or "", org)
            got = repo.get_equipment_by_marker(org, marker or "")
            if isinstance(expected, Found):
                assert got is not None
                assert got.id == expected.equipment_id
            else:
                assert expected is NOT_FOUND
                assert got is None


# --- gravacao (REQ-MNT-003, Z-004) ----------------------------------------------------------


def test_record_accepts_and_exposes_latest(repo: Repository) -> None:
    outcome = repo.record(_event(value=51.5), RECEIVED)

    assert outcome is RecordOutcome.ACCEPTED
    [reading] = repo.latest_readings("org-a", "EQ-001")
    assert (reading.sensor_type, reading.value, reading.unit) == ("temperature", 51.5, "celsius")
    assert reading.observed_at == T0
    assert reading.received_at == RECEIVED
    assert reading.quality is Quality.GOOD
    assert (reading.source, reading.event_id) == ("sim", "e1")
    eq = repo.get_equipment("org-a", "EQ-001")
    assert eq is not None
    assert eq.last_seen_at == T0


def test_t1_duplicate_event_changes_nothing(repo: Repository) -> None:
    repo.record(_event("dup", value=50.0), RECEIVED)
    before = repo.latest_readings("org-a", "EQ-001")

    outcome = repo.record(_event("dup", value=999.0, observed_at=T0 + timedelta(hours=1)), RECEIVED)

    assert outcome is RecordOutcome.DUPLICATE
    assert repo.latest_readings("org-a", "EQ-001") == before
    assert repo.event_count("EQ-001") == 1


def test_same_event_id_from_different_source_is_a_distinct_event(repo: Repository) -> None:
    assert repo.record(_event("same", source="a"), RECEIVED) is RecordOutcome.ACCEPTED
    assert repo.record(_event("same", source="b"), RECEIVED) is RecordOutcome.ACCEPTED
    assert repo.event_count("EQ-001") == 2


def test_t2_out_of_order_event_goes_to_history_without_regressing_latest(repo: Repository) -> None:
    repo.record(_event("new", value=80.0, observed_at=T0 + timedelta(seconds=10)), RECEIVED)

    outcome = repo.record(_event("old", value=10.0, observed_at=T0), RECEIVED)

    assert outcome is RecordOutcome.ACCEPTED_HISTORY_ONLY
    [reading] = repo.latest_readings("org-a", "EQ-001")
    assert reading.value == 80.0
    assert reading.event_id == "new"
    assert repo.event_count("EQ-001") == 2
    eq = repo.get_equipment("org-a", "EQ-001")
    assert eq is not None
    assert eq.last_seen_at == T0 + timedelta(seconds=10)


def test_equal_observed_at_newer_arrival_wins(repo: Repository) -> None:
    repo.record(_event("first", value=1.0), RECEIVED)

    assert repo.record(_event("second", value=2.0), RECEIVED) is RecordOutcome.ACCEPTED

    [reading] = repo.latest_readings("org-a", "EQ-001")
    assert (reading.value, reading.event_id) == (2.0, "second")


def test_latest_is_tracked_per_sensor(repo: Repository) -> None:
    repo.record(_event("t", sensor="temperature", value=60.0), RECEIVED)
    repo.record(_event("v", sensor="vibration", value=3.0), RECEIVED)

    readings = {r.sensor_type: r.value for r in repo.latest_readings("org-a", "EQ-001")}

    assert readings == {"temperature": 60.0, "vibration": 3.0}


def test_bad_quality_reading_is_stored_with_its_quality(repo: Repository) -> None:
    repo.record(_event("bad", quality=Quality.BAD), RECEIVED)

    [reading] = repo.latest_readings("org-a", "EQ-001")
    assert reading.quality is Quality.BAD


def test_latest_readings_are_org_isolated(repo: Repository) -> None:
    repo.record(_event(), RECEIVED)

    assert repo.latest_readings("org-b", "EQ-001") == []
    assert repo.latest_readings("org-a", "EQ-002") == []


def test_record_for_unknown_equipment_raises_and_stores_nothing(repo: Repository) -> None:
    with pytest.raises(UnknownEquipmentError):
        repo.record(_event(equipment_id="EQ-NOPE"), RECEIVED)

    assert repo.event_count("EQ-NOPE") == 0


def test_record_for_sensor_without_profile_raises(repo: Repository) -> None:
    with pytest.raises(UnknownEquipmentError):
        repo.record(_event(sensor="pressure"), RECEIVED)


def test_concurrent_duplicates_produce_exactly_one_acceptance(repo: Repository) -> None:
    outcomes: list[RecordOutcome] = []
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()
        outcomes.append(repo.record(_event("race"), RECEIVED))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count(RecordOutcome.ACCEPTED) == 1
    assert outcomes.count(RecordOutcome.DUPLICATE) == 7
    assert repo.event_count("EQ-001") == 1
