"""SPEC-010 · REQ-HACC-007 (D-054): estado BLOQUEADO do leito (indisponivel no HACC).

Bloqueado e um estado OPERACIONAL, nao um alarme: perde para qualquer alarme, pendencia, leitura velha ou
ausente, e nao contamina o estado da ala.
"""

from datetime import UTC, datetime, timedelta

from spatial_domain.beds import (
    BedFlags,
    BedReading,
    BedStatus,
    bed_alerts,
    evaluate_bed,
    worst_status,
)

NOW = datetime(2026, 10, 26, 12, 0, 0, tzinfo=UTC)


def _reading(blocked: bool = True, age_s: float | None = 1.0, **flags: bool) -> BedReading:
    observed = None if age_s is None else NOW - timedelta(seconds=age_s)
    return BedReading(True, BedFlags(**flags), observed, blocked=blocked)


def test_a_fresh_blocked_bed_without_alarms_is_blocked() -> None:
    assert evaluate_bed(_reading(), NOW) is BedStatus.BLOCKED


def test_blocked_defaults_to_false_so_existing_readings_keep_their_meaning() -> None:
    assert BedReading(True, BedFlags(), NOW).blocked is False
    assert evaluate_bed(BedReading(True, BedFlags(), NOW), NOW) is BedStatus.NORMAL


def test_an_alarm_wins_over_blocked() -> None:
    assert evaluate_bed(_reading(iv_pump_alarm=True), NOW) is BedStatus.ALERT


def test_a_call_or_cleaning_wins_over_blocked() -> None:
    assert evaluate_bed(_reading(call_button=True), NOW) is BedStatus.ATTENTION
    assert evaluate_bed(_reading(cleaning_due=True), NOW) is BedStatus.ATTENTION


def test_a_stale_blocked_bed_is_offline_and_one_without_reading_is_unknown() -> None:
    assert evaluate_bed(_reading(age_s=300), NOW) is BedStatus.OFFLINE
    assert evaluate_bed(_reading(age_s=None), NOW) is BedStatus.UNKNOWN


def test_blocked_is_not_an_alert() -> None:
    assert bed_alerts(_reading(), NOW) == []


def test_a_blocked_bed_does_not_make_the_ward_blocked_or_worse() -> None:
    assert worst_status([BedStatus.NORMAL, BedStatus.BLOCKED]) is BedStatus.NORMAL
    assert worst_status([BedStatus.BLOCKED]) is BedStatus.NORMAL
    assert worst_status([BedStatus.BLOCKED, BedStatus.ATTENTION]) is BedStatus.ATTENTION
    assert worst_status([BedStatus.BLOCKED, BedStatus.UNKNOWN]) is BedStatus.UNKNOWN
    assert worst_status([]) is BedStatus.UNKNOWN  # ala vazia continua nunca "normal"
