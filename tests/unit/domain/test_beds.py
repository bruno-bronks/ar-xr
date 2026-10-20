"""SPEC-010 · REQ-HACC-005 · Z-006: estado operacional do leito (regra pura, sem interpretacao clinica).

Exemplos concretos + Hypothesis para B1-B3. A Z-006 passa no typecheck do CZT; nenhum teorema provado.
"""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st
from spatial_domain.beds import (
    BedFlags,
    BedReading,
    BedStatus,
    bed_alerts,
    evaluate_bed,
    worst_status,
)

NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)
AFTER = timedelta(seconds=30)


def _reading(
    *,
    occupied: bool = True,
    age_s: float | None = 1.0,
    bed_exit: bool = False,
    iv: bool = False,
    call: bool = False,
    cleaning: bool = False,
) -> BedReading:
    observed = None if age_s is None else NOW - timedelta(seconds=age_s)
    return BedReading(occupied, BedFlags(bed_exit, iv, call, cleaning), observed)


def _status(reading: BedReading) -> BedStatus:
    return evaluate_bed(reading, NOW, AFTER)


def test_quiet_fresh_bed_is_normal() -> None:
    assert _status(_reading()) is BedStatus.NORMAL
    assert _status(_reading(occupied=False)) is BedStatus.NORMAL


def test_missing_reading_is_unknown_never_normal() -> None:
    assert _status(_reading(age_s=None)) is BedStatus.UNKNOWN
    assert _status(_reading(age_s=None, iv=True, bed_exit=True)) is BedStatus.UNKNOWN


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"iv": True}, BedStatus.ALERT),
        ({"bed_exit": True}, BedStatus.ALERT),
        ({"bed_exit": True, "occupied": False}, BedStatus.NORMAL),  # saida de leito vazio: ignorada
        ({"call": True}, BedStatus.ATTENTION),
        ({"cleaning": True}, BedStatus.ATTENTION),
        ({"cleaning": True, "occupied": False}, BedStatus.ATTENTION),
        ({"call": True, "iv": True}, BedStatus.ALERT),  # ALERT prevalece sobre ATTENTION
        ({"iv": True, "occupied": False}, BedStatus.ALERT),
    ],
)
def test_flags_map_to_alert_or_attention(kwargs: dict[str, bool], expected: BedStatus) -> None:
    assert _status(_reading(**kwargs)) is expected


def test_stale_reading_is_offline_with_precedence_over_every_flag() -> None:
    stale = _reading(age_s=31.0, iv=True, bed_exit=True, call=True, cleaning=True)

    assert _status(stale) is BedStatus.OFFLINE
    assert [a.rule for a in bed_alerts(stale, NOW, AFTER)] == ["offline"]


def test_freshness_boundary_is_strict_like_d001() -> None:
    assert _status(_reading(age_s=30.0, iv=True)) is BedStatus.ALERT  # exatamente no limite: fresco
    assert _status(_reading(age_s=30.001, iv=True)) is BedStatus.OFFLINE


def test_future_timestamp_counts_as_fresh_not_offline() -> None:
    assert _status(_reading(age_s=-5.0)) is BedStatus.NORMAL


def test_alerts_list_one_entry_per_effective_flag() -> None:
    reading = _reading(bed_exit=True, iv=True, call=True, cleaning=True)

    assert [(a.severity, a.rule) for a in bed_alerts(reading, NOW, AFTER)] == [
        ("ALERT", "bed_exit_alarm"),
        ("ALERT", "iv_pump_alarm"),
        ("ATTENTION", "call_button"),
        ("ATTENTION", "cleaning_due"),
    ]
    assert [a.rule for a in bed_alerts(_reading(bed_exit=True, occupied=False), NOW, AFTER)] == []
    assert bed_alerts(_reading(age_s=None), NOW, AFTER) == []


def test_naive_datetimes_are_rejected() -> None:
    naive = datetime(2026, 10, 20, 12, 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        BedReading(True, BedFlags(), naive)
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate_bed(_reading(), naive, AFTER)


def test_non_positive_offline_after_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        evaluate_bed(_reading(), NOW, timedelta(0))


def test_worst_status_orders_alert_offline_unknown_attention_normal() -> None:
    S = BedStatus
    assert worst_status([]) is S.UNKNOWN  # ala sem leitos nunca e "normal"
    assert worst_status([S.NORMAL, S.NORMAL]) is S.NORMAL
    assert worst_status([S.NORMAL, S.ATTENTION]) is S.ATTENTION
    assert worst_status([S.ATTENTION, S.UNKNOWN]) is S.UNKNOWN
    assert worst_status([S.UNKNOWN, S.OFFLINE]) is S.OFFLINE
    assert worst_status([S.OFFLINE, S.ALERT, S.NORMAL]) is S.ALERT


# --- invariantes (Z-006 B1-B3) --------------------------------------------------------------

readings = st.builds(
    BedReading,
    st.booleans(),
    st.builds(BedFlags, st.booleans(), st.booleans(), st.booleans(), st.booleans()),
    st.one_of(
        st.none(),
        st.floats(min_value=-60, max_value=300, allow_nan=False).map(
            lambda s: NOW - timedelta(seconds=s)
        ),
    ),
)


@given(readings)
def test_b1_missing_reading_is_always_unknown(reading: BedReading) -> None:
    if reading.observed_at is None:
        assert evaluate_bed(reading, NOW, AFTER) is BedStatus.UNKNOWN
    else:
        assert evaluate_bed(reading, NOW, AFTER) is not BedStatus.UNKNOWN


@given(readings)
def test_b2_stale_is_always_offline(reading: BedReading) -> None:
    if reading.observed_at is not None and NOW - reading.observed_at > AFTER:
        assert evaluate_bed(reading, NOW, AFTER) is BedStatus.OFFLINE


@given(readings)
def test_b3_normal_implies_no_effective_flag(reading: BedReading) -> None:
    status = evaluate_bed(reading, NOW, AFTER)
    if status is BedStatus.NORMAL:
        flags = reading.flags
        assert not flags.iv_pump_alarm
        assert not flags.call_button
        assert not flags.cleaning_due
        assert not (flags.bed_exit_alarm and reading.occupied)
        assert reading.observed_at is not None


@given(readings)
def test_alerts_agree_with_status(reading: BedReading) -> None:
    status = evaluate_bed(reading, NOW, AFTER)
    alerts = bed_alerts(reading, NOW, AFTER)

    if status in {BedStatus.NORMAL, BedStatus.UNKNOWN}:
        assert alerts == []
    elif status is BedStatus.OFFLINE:
        assert [a.rule for a in alerts] == ["offline"]
    else:
        assert alerts
        severities = {a.severity for a in alerts}
        assert ("ALERT" in severities) == (status is BedStatus.ALERT)
