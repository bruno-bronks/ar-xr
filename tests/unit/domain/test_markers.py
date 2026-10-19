"""SPEC-003 · REQ-MNT-001 · Z-003: resolucao de marker/QR sem vazamento entre organizacoes."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from spatial_domain.markers import NOT_FOUND, Found, NotFound, Registry

# Seed ilustrativo dos 3 QR de teste (o seed real pertence a Fase 1; M4 sera repetido la).
MARKER_OF = {"QR-EQ-001": "EQ-001", "QR-EQ-002": "EQ-002", "QR-EQ-003": "EQ-003"}
OWNER = {"EQ-001": "org-a", "EQ-002": "org-a", "EQ-003": "org-b"}


@pytest.fixture
def registry() -> Registry:
    return Registry(marker_of=MARKER_OF, owner=OWNER)


def test_m4_each_known_marker_resolves_only_to_its_equipment(registry: Registry) -> None:
    assert registry.resolve("QR-EQ-001", "org-a") == Found("EQ-001")
    assert registry.resolve("QR-EQ-002", "org-a") == Found("EQ-002")
    assert registry.resolve("QR-EQ-003", "org-b") == Found("EQ-003")


def test_m1_marker_of_other_org_is_not_found(registry: Registry) -> None:
    assert registry.resolve("QR-EQ-003", "org-a") is NOT_FOUND
    assert registry.resolve("QR-EQ-001", "org-b") is NOT_FOUND


def test_unknown_marker_is_not_found(registry: Registry) -> None:
    assert registry.resolve("QR-DOES-NOT-EXIST", "org-a") is NOT_FOUND


def test_m2_unknown_and_foreign_markers_are_indistinguishable(registry: Registry) -> None:
    foreign = registry.resolve("QR-EQ-003", "org-a")
    unknown = registry.resolve("QR-UNKNOWN", "org-a")

    assert foreign == unknown
    assert repr(foreign) == repr(unknown)
    assert isinstance(foreign, NotFound)


def test_unknown_caller_org_sees_nothing(registry: Registry) -> None:
    assert registry.resolve("QR-EQ-001", "org-zzz") is NOT_FOUND


@pytest.mark.parametrize(
    "hostile",
    ["", " ", "' OR 1=1 --", "../../etc/passwd", "QR-EQ-001\x00", "😀", "A" * 10_000, "qr-eq-001"],
)
def test_hostile_marker_content_is_just_an_opaque_key(registry: Registry, hostile: str) -> None:
    assert registry.resolve(hostile, "org-a") is NOT_FOUND


def test_m3_resolve_does_not_mutate_registry(registry: Registry) -> None:
    before = (dict(registry.marker_of), dict(registry.owner))

    registry.resolve("QR-EQ-001", "org-a")
    registry.resolve("nope", "org-a")

    assert (dict(registry.marker_of), dict(registry.owner)) == before


def test_registry_is_isolated_from_caller_mutation() -> None:
    marker_of = dict(MARKER_OF)
    registry = Registry(marker_of=marker_of, owner=OWNER)

    marker_of["QR-EQ-001"] = "EQ-003"

    assert registry.resolve("QR-EQ-001", "org-a") == Found("EQ-001")


def test_marker_map_must_be_injective() -> None:
    with pytest.raises(ValueError, match="injective"):
        Registry(marker_of={"QR-1": "EQ-001", "QR-2": "EQ-001"}, owner=OWNER)


def test_every_marked_equipment_must_have_an_owner() -> None:
    with pytest.raises(ValueError, match="owner"):
        Registry(marker_of={"QR-9": "EQ-999"}, owner=OWNER)


org_ids = st.sampled_from(["org-a", "org-b", "org-c"])


@given(st.text(max_size=50), org_ids)
def test_m1_found_implies_ownership(marker: str, caller: str) -> None:
    registry = Registry(marker_of=MARKER_OF, owner=OWNER)

    result = registry.resolve(marker, caller)

    if isinstance(result, Found):
        assert OWNER[result.equipment_id] == caller
        assert MARKER_OF[marker] == result.equipment_id


@given(st.text(max_size=50), org_ids)
def test_m2_everything_not_owned_gives_the_same_answer(marker: str, caller: str) -> None:
    registry = Registry(marker_of=MARKER_OF, owner=OWNER)

    result = registry.resolve(marker, caller)

    owned = marker in MARKER_OF and OWNER[MARKER_OF[marker]] == caller
    assert owned or result is NOT_FOUND
