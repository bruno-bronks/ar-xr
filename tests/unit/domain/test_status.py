"""SPEC-002 · REQ-MNT-002 · Z-002.

Exemplos concretos + property-based tests dos invariantes I1-I7 (a verificacao
formal da especificacao Z nao foi executada: ver docs/decisions/tool-evaluation.md).
"""

import math
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st
from spatial_domain.status import Quality, Reading, Status, Threshold, evaluate_status

NOW = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)
OFFLINE_AFTER = timedelta(seconds=30)
PROFILE = {"temperature": Threshold(warn=80.0, crit=100.0), "vibration": Threshold(5.0, 10.0)}

Snapshot = tuple[dict[str, Threshold], dict[str, Reading]]


def _reading(value: float, age_s: float = 1.0, quality: Quality = Quality.GOOD) -> Reading:
    return Reading(value=value, observed_at=NOW - timedelta(seconds=age_s), quality=quality)


def _eval(latest: Mapping[str, Reading], now: datetime = NOW) -> Status:
    return evaluate_status(PROFILE, latest, now, OFFLINE_AFTER)


def _full(temperature: float, vibration: float = 1.0, age_s: float = 1.0) -> dict[str, Reading]:
    """Leituras GOOD frescas para todos os sensores do perfil."""
    return {"temperature": _reading(temperature, age_s), "vibration": _reading(vibration, age_s)}


# --- exemplos ------------------------------------------------------------------------------


def test_no_readings_is_unknown_never_normal() -> None:
    assert _eval({}) is Status.UNKNOWN


def test_fresh_full_coverage_below_limits_is_normal() -> None:
    assert _eval(_full(50.0, 1.0)) is Status.NORMAL


def test_exact_warn_limit_does_not_alarm() -> None:  # D-001
    assert _eval(_full(80.0, 5.0)) is Status.NORMAL


def test_just_above_warn_is_warning() -> None:
    assert _eval(_full(80.0001)) is Status.WARNING


def test_exact_crit_limit_is_warning_not_critical() -> None:  # D-001
    assert _eval(_full(100.0)) is Status.WARNING


def test_just_above_crit_is_critical() -> None:
    assert _eval(_full(100.0001)) is Status.CRITICAL


def test_critical_on_one_sensor_dominates_normal_on_other() -> None:
    assert _eval(_full(20.0, vibration=11.0)) is Status.CRITICAL


def test_missing_sensor_prevents_normal() -> None:  # D-006
    assert _eval({"temperature": _reading(50.0)}) is Status.UNKNOWN


def test_alarm_evidence_dominates_incomplete_coverage() -> None:
    assert _eval({"temperature": _reading(500.0)}) is Status.CRITICAL


def test_stale_equipment_is_offline_even_with_critical_value() -> None:
    assert _eval(_full(500.0, age_s=31.0)) is Status.OFFLINE


def test_offline_boundary_is_inclusive_of_fresh() -> None:
    at_limit = _full(50.0, age_s=30.0)
    just_past = NOW - OFFLINE_AFTER - timedelta(microseconds=1)
    past_limit = {k: Reading(r.value, just_past, r.quality) for k, r in at_limit.items()}

    assert _eval(at_limit) is Status.NORMAL
    assert _eval(past_limit) is Status.OFFLINE


def test_bad_quality_sensor_prevents_normal() -> None:  # D-002
    latest = _full(50.0)
    latest["temperature"] = _reading(50.0, quality=Quality.BAD)

    assert _eval(latest) is Status.UNKNOWN


def test_bad_reading_cannot_raise_alarm() -> None:  # D-002
    latest = _full(50.0)
    latest["temperature"] = _reading(500.0, quality=Quality.BAD)

    assert _eval(latest) is Status.UNKNOWN


def test_bad_reading_cannot_mask_alarm() -> None:
    latest = _full(50.0, vibration=11.0)
    latest["temperature"] = _reading(1.0, quality=Quality.BAD)

    assert _eval(latest) is Status.CRITICAL


def test_stale_good_sensor_is_not_trusted_while_other_sensor_is_alive() -> None:  # D-003/D-006
    latest = {
        "temperature": _reading(50.0, age_s=300.0),  # GOOD, porem velha
        "vibration": _reading(1.0, age_s=2.0),  # viva
    }

    assert _eval(latest) is Status.UNKNOWN


def test_stale_good_sensor_cannot_raise_alarm() -> None:
    latest = {
        "temperature": _reading(500.0, age_s=300.0),
        "vibration": _reading(1.0, age_s=2.0),
    }

    assert _eval(latest) is Status.UNKNOWN


def test_future_observed_at_is_treated_as_age_zero() -> None:
    future = {
        k: Reading(r.value, NOW + timedelta(hours=1), r.quality) for k, r in _full(50.0).items()
    }

    assert _eval(future) is Status.NORMAL


def test_state_transitions_follow_values() -> None:
    values = [50.0, 90.0, 120.0, 90.0, 50.0]
    expected = [Status.NORMAL, Status.WARNING, Status.CRITICAL, Status.WARNING, Status.NORMAL]

    assert [_eval(_full(v)) for v in values] == expected


# --- validacao das precondicoes (Z: EquipmentSnapshot) ------------------------------------


def test_reading_for_sensor_without_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="profile"):
        _eval({"pressure": _reading(1.0)})


def test_naive_datetime_rejected() -> None:
    with pytest.raises(ValueError, match="timezone"):
        Reading(1.0, datetime(2026, 1, 1), Quality.GOOD)


def test_naive_now_rejected() -> None:
    with pytest.raises(ValueError, match="timezone"):
        _eval({"temperature": _reading(1.0)}, now=datetime(2026, 1, 1))


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_values_rejected(bad: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        Reading(bad, NOW, Quality.GOOD)
    with pytest.raises(ValueError, match="finite"):
        Threshold(warn=bad, crit=1.0)


def test_warn_greater_than_crit_rejected() -> None:
    with pytest.raises(ValueError, match="warn"):
        Threshold(warn=10.0, crit=5.0)


def test_non_positive_offline_after_rejected() -> None:
    with pytest.raises(ValueError, match="offline_after"):
        evaluate_status(PROFILE, {}, NOW, timedelta(0))


# --- propriedades (Hypothesis) ------------------------------------------------------------

finite = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
sensors = st.sampled_from(["temperature", "vibration"])


@st.composite
def thresholds(draw: st.DrawFn) -> Threshold:
    a, b = sorted((draw(finite), draw(finite)))
    return Threshold(warn=a, crit=b)


@st.composite
def readings(draw: st.DrawFn) -> Reading:
    age = draw(st.floats(min_value=-100.0, max_value=200.0))
    return Reading(draw(finite), NOW - timedelta(seconds=age), draw(st.sampled_from(Quality)))


@st.composite
def snapshots(draw: st.DrawFn) -> Snapshot:
    profile = {s: draw(thresholds()) for s in ("temperature", "vibration")}
    chosen = draw(st.lists(sensors, unique=True, max_size=2))
    return profile, {s: draw(readings()) for s in chosen}


def _fresh(latest: Mapping[str, Reading]) -> bool:
    last_seen = max(r.observed_at for r in latest.values())
    return NOW - last_seen <= OFFLINE_AFTER


def _usable(reading: Reading) -> bool:
    """Leitura valida = GOOD e fresca (Z-002: valid)."""
    return reading.quality is Quality.GOOD and NOW - reading.observed_at <= OFFLINE_AFTER


def _valid_over(profile: Mapping[str, Threshold], latest: Mapping[str, Reading], attr: str) -> bool:
    return any(_usable(r) and r.value > getattr(profile[s], attr) for s, r in latest.items())


@given(snapshots())
def test_i4_total_and_deterministic(snap: Snapshot) -> None:
    profile, latest = snap

    first = evaluate_status(profile, latest, NOW, OFFLINE_AFTER)
    second = evaluate_status(profile, latest, NOW, OFFLINE_AFTER)

    assert isinstance(first, Status)
    assert first is second


@given(snapshots())
def test_i1_normal_requires_full_fresh_valid_coverage_below_warn(snap: Snapshot) -> None:
    profile, latest = snap
    if evaluate_status(profile, latest, NOW, OFFLINE_AFTER) is Status.NORMAL:
        assert latest
        assert _fresh(latest)
        assert set(latest) == set(profile)
        assert all(_usable(r) for r in latest.values())
        assert not _valid_over(profile, latest, "warn")


@given(snapshots())
def test_i2_critical_requires_fresh_valid_reading_above_crit(snap: Snapshot) -> None:
    profile, latest = snap
    if evaluate_status(profile, latest, NOW, OFFLINE_AFTER) is Status.CRITICAL:
        assert _fresh(latest)
        assert _valid_over(profile, latest, "crit")


@given(snapshots())
def test_i2b_warning_requires_valid_reading_above_warn_and_none_above_crit(
    snap: Snapshot,
) -> None:
    profile, latest = snap
    if evaluate_status(profile, latest, NOW, OFFLINE_AFTER) is Status.WARNING:
        assert _valid_over(profile, latest, "warn")
        assert not _valid_over(profile, latest, "crit")


@given(snapshots())
def test_i3_stale_with_readings_is_offline(snap: Snapshot) -> None:
    profile, latest = snap
    if latest and not _fresh(latest):
        assert evaluate_status(profile, latest, NOW, OFFLINE_AFTER) is Status.OFFLINE


@given(snapshots())
def test_absence_of_readings_is_unknown(snap: Snapshot) -> None:
    profile, latest = snap
    if not latest:
        assert evaluate_status(profile, latest, NOW, OFFLINE_AFTER) is Status.UNKNOWN


_ALARM = {Status.WARNING: 1, Status.CRITICAL: 2}


@given(snapshots(), st.floats(min_value=0.0, max_value=1e6))
def test_i5_raising_a_usable_value_never_lowers_alarm_level(snap: Snapshot, delta: float) -> None:
    profile, latest = snap
    usable = [s for s, r in latest.items() if _usable(r)]
    if not usable:
        return
    sensor = usable[0]
    raised = dict(latest)
    base = latest[sensor]
    raised[sensor] = Reading(base.value + delta, base.observed_at, base.quality)

    before = evaluate_status(profile, latest, NOW, OFFLINE_AFTER)
    after = evaluate_status(profile, raised, NOW, OFFLINE_AFTER)

    assert (before is Status.OFFLINE) == (after is Status.OFFLINE)
    assert _ALARM.get(after, 0) >= _ALARM.get(before, 0)


@given(snapshots())
def test_i6_value_at_limit_is_not_exceeded(snap: Snapshot) -> None:
    profile, latest = snap
    at_limit = {s: Reading(profile[s].warn, r.observed_at, Quality.GOOD) for s, r in latest.items()}

    status = evaluate_status(profile, at_limit, NOW, OFFLINE_AFTER)

    assert status not in {Status.WARNING, Status.CRITICAL}


@given(snapshots(), finite)
def test_i7_bad_readings_do_not_change_result(snap: Snapshot, new_value: float) -> None:
    profile, latest = snap
    changed = {
        s: Reading(new_value, r.observed_at, r.quality) if r.quality is Quality.BAD else r
        for s, r in latest.items()
    }

    assert evaluate_status(profile, latest, NOW, OFFLINE_AFTER) is evaluate_status(
        profile, changed, NOW, OFFLINE_AFTER
    )


@given(snapshots(), finite)
def test_stale_good_readings_do_not_change_result(snap: Snapshot, new_value: float) -> None:
    """Leitura GOOD velha (nao fresca) e ignorada na avaliacao (D-003/D-006)."""
    profile, latest = snap
    changed = {
        s: Reading(new_value, r.observed_at, r.quality)
        if r.quality is Quality.GOOD and not _usable(r)
        else r
        for s, r in latest.items()
    }

    assert evaluate_status(profile, latest, NOW, OFFLINE_AFTER) is evaluate_status(
        profile, changed, NOW, OFFLINE_AFTER
    )
