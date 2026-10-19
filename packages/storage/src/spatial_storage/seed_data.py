"""Dados de seed de desenvolvimento (D-008): 3 maquinas ficticias em org-a + sentinela em org-b."""

from dataclasses import dataclass

from spatial_storage.repository import SensorProfile


@dataclass(frozen=True)
class EquipmentSeed:
    id: str
    org_id: str
    name: str
    type: str
    location: str
    marker_id: str
    profile: tuple[SensorProfile, ...]
    offline_after_seconds: int = 30


@dataclass(frozen=True)
class SeedData:
    organizations: tuple[tuple[str, str], ...]
    equipment: tuple[EquipmentSeed, ...]


def _profile(temp: tuple[float, float], vib: tuple[float, float]) -> tuple[SensorProfile, ...]:
    return (
        SensorProfile("temperature", "celsius", *temp),
        SensorProfile("vibration", "mm/s", *vib),
    )


SEED = SeedData(
    organizations=(("org-a", "Organizacao A (demo)"), ("org-b", "Organizacao B (demo)")),
    equipment=(
        EquipmentSeed(
            "EQ-001", "org-a", "Compressor de ar 01", "Compressor de ar", "Galpao A - Linha 1",
            "QR-EQ-001", _profile((85.0, 100.0), (5.0, 8.0)),
        ),
        EquipmentSeed(
            "EQ-002", "org-a", "Bomba centrifuga 02", "Bomba centrifuga", "Galpao A - Utilidades",
            "QR-EQ-002", _profile((70.0, 90.0), (4.0, 7.0)),
        ),
        EquipmentSeed(
            "EQ-003", "org-a", "Motor eletrico 03", "Motor eletrico", "Galpao B - Linha 2",
            "QR-EQ-003", _profile((80.0, 95.0), (6.0, 9.0)),
        ),
        EquipmentSeed(
            "EQ-B01", "org-b", "Equipamento sentinela B01", "Sentinela", "Galpao B (org-b)",
            "QR-EQ-B01", _profile((80.0, 95.0), (6.0, 9.0)),
        ),
    ),
)  # fmt: skip
