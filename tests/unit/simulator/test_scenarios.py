"""SPEC-007 · REQ-SIM-001: cenarios deterministicos do simulador, validados pelo dominio real."""

import itertools
import json
import math
from datetime import UTC, datetime, timedelta

import pytest
from simulator.scenarios import SimConfig, Simulation
from spatial_domain.status import Quality, Reading, Status, Threshold, evaluate_status
from spatial_domain.telemetry import equipment_id_from_topic, parse_payload
from spatial_storage.seed_data import SEED

T0 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)
CFG = SimConfig(
    interval_s=2.0, cycle_ticks=120, seed=42, duplicate_every=0, late_every=0, run_id="r1"
)
OFFLINE_AFTER = timedelta(seconds=30)
PROFILES = {
    e.id: {p.sensor_type: Threshold(p.warn, p.crit) for p in e.profile} for e in SEED.equipment
}


def _timeline(equipment_id: str, cfg: SimConfig = CFG, cycles: int = 2) -> list[Status]:
    """Estado do equipamento a cada tick, avaliado pelo modelo de dominio (SPEC-002)."""
    sim = Simulation(cfg)
    latest: dict[str, Reading] = {}
    statuses: list[Status] = []
    for tick in range(cfg.cycle_ticks * cycles):
        now = T0 + timedelta(seconds=tick * cfg.interval_s)
        for message in sim.step(now):
            event = parse_payload(message.payload)
            if event.equipment_id == equipment_id:
                latest[event.sensor_type] = Reading(event.value, event.observed_at, event.quality)
        statuses.append(evaluate_status(PROFILES[equipment_id], latest, now, OFFLINE_AFTER))
    return statuses


def _compress(statuses: list[Status]) -> list[Status]:
    out: list[Status] = []
    for status in statuses:
        if not out or out[-1] is not status:
            out.append(status)
    return out


def test_steady_equipment_is_never_alarming_or_offline() -> None:
    timeline = _timeline("EQ-001")

    assert set(timeline) <= {Status.NORMAL, Status.UNKNOWN}
    assert timeline[-1] is Status.NORMAL


def test_ramp_equipment_escalates_normal_warning_critical_and_recovers() -> None:
    timeline = _compress(_timeline("EQ-002"))

    assert [s for s in timeline if s is not Status.UNKNOWN][:5] == [
        Status.NORMAL,
        Status.WARNING,
        Status.CRITICAL,
        Status.WARNING,
        Status.NORMAL,
    ]


def test_dropout_equipment_goes_offline_and_comes_back() -> None:
    timeline = _compress(_timeline("EQ-003"))

    assert Status.OFFLINE in timeline
    first_offline = timeline.index(Status.OFFLINE)
    assert Status.NORMAL in timeline[:first_offline]
    assert Status.NORMAL in timeline[first_offline:]  # voltou a publicar
    assert Status.CRITICAL not in timeline


def test_simulation_is_deterministic() -> None:
    def run(cfg: SimConfig) -> list[bytes]:
        sim = Simulation(cfg)
        return [m.payload for t in range(30) for m in sim.step(T0 + timedelta(seconds=2 * t))]

    assert run(CFG) == run(CFG)
    assert run(CFG) != run(SimConfig(**{**CFG.__dict__, "seed": 7}))


def test_every_message_satisfies_the_contract_and_uses_the_right_topic() -> None:
    sim = Simulation(CFG)
    seen_equipment = set()

    for tick in range(CFG.cycle_ticks):
        for message in sim.step(T0 + timedelta(seconds=tick * 2)):
            event = parse_payload(message.payload)
            assert equipment_id_from_topic(message.topic) == event.equipment_id
            assert event.source == "equipment-simulator"
            assert event.quality is Quality.GOOD
            assert math.isfinite(event.value)
            seen_equipment.add(event.equipment_id)

    assert seen_equipment == {"EQ-001", "EQ-002", "EQ-003", "EQ-B01"}


def test_event_ids_are_unique_within_a_run_and_across_runs() -> None:
    def ids(run_id: str) -> list[str]:
        sim = Simulation(SimConfig(**{**CFG.__dict__, "run_id": run_id}))
        return [
            json.loads(m.payload)["event_id"]
            for t in range(10)
            for m in sim.step(T0 + timedelta(seconds=2 * t))
        ]

    first, second = ids("run-a"), ids("run-b")

    assert len(set(first)) == len(first)
    assert not set(first) & set(second)  # reiniciar o simulador nao gera colisao


def test_observed_at_follows_the_supplied_clock() -> None:
    sim = Simulation(CFG)
    now = T0 + timedelta(seconds=123)

    event = parse_payload(sim.step(now)[0].payload)

    assert event.observed_at == now


def test_duplicates_are_exact_replays_of_the_previous_message() -> None:
    sim = Simulation(SimConfig(**{**CFG.__dict__, "duplicate_every": 3}))

    payloads = [m.payload for t in range(5) for m in sim.step(T0 + timedelta(seconds=2 * t))]

    replays = [a for a, b in itertools.pairwise(payloads) if a == b]
    assert replays, "esperava ao menos um reenvio identico"
    assert len(payloads) - len(set(payloads)) == len(replays)


def test_late_messages_are_old_and_have_fresh_ids() -> None:
    sim = Simulation(SimConfig(**{**CFG.__dict__, "late_every": 5}))
    now = T0 + timedelta(seconds=600)

    events = [
        parse_payload(m.payload) for t in range(6) for m in sim.step(now + timedelta(seconds=2 * t))
    ]

    late = [e for e in events if e.observed_at < now]
    assert late, "esperava ao menos uma leitura atrasada"
    assert len({e.event_id for e in events}) == len(events)


@pytest.mark.parametrize("field", ["interval_s", "cycle_ticks"])
def test_config_rejects_non_positive_values(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        SimConfig(**{**CFG.__dict__, field: 0})
