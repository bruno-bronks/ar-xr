"""Estado verdadeiro do "simulador" para o dataset de visao (SPEC-011, D-036).

O rotulo de estado de cada cena NAO e inventado aqui: sorteamos leituras de telemetria compativeis
com o perfil de limiares do equipamento semeado (seed_data) e deixamos a regra REAL
`spatial_domain.status.evaluate_status` decidir NORMAL/WARNING/CRITICAL.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np
from spatial_domain.status import Quality, Reading, Status, Threshold, evaluate_status
from spatial_storage.seed_data import SEED, EquipmentSeed

NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)
OFFLINE_AFTER = timedelta(seconds=30)

# Equipamentos da organizacao A do seed (um por tipo): o tipo e o que o detector enxerga.
TYPE_BY_EQUIPMENT = {"EQ-001": "compressor", "EQ-002": "pump", "EQ-003": "motor"}
EQUIPMENT_IDS = tuple(TYPE_BY_EQUIPMENT)
LAMP_STATUSES = (Status.NORMAL, Status.WARNING, Status.CRITICAL)
LAMP_CLASS = {
    Status.NORMAL: "lamp_normal",
    Status.WARNING: "lamp_warning",
    Status.CRITICAL: "lamp_critical",
}


@dataclass(frozen=True)
class Truth:
    equipment_id: str
    equipment_type: str
    qr_text: str
    status: Status
    temperature: float
    vibration: float


def equipment_seed(equipment_id: str) -> EquipmentSeed:
    return next(e for e in SEED.equipment if e.id == equipment_id)


def sample_truth(rng: np.random.Generator, equipment_id: str, target: Status) -> Truth:
    """Sorteia leituras para o estado alvo e CONFIRMA com a regra real (falha se divergir)."""
    seed = equipment_seed(equipment_id)
    profile = {p.sensor_type: Threshold(p.warn, p.crit) for p in seed.profile}
    temp_p, vib_p = profile["temperature"], profile["vibration"]

    if target is Status.NORMAL:
        temp = float(rng.uniform(0.3 * temp_p.warn, 0.95 * temp_p.warn))
        vib = float(rng.uniform(0.2 * vib_p.warn, 0.9 * vib_p.warn))
    elif target is Status.WARNING:
        temp = float(rng.uniform(temp_p.warn * 1.01, temp_p.crit))
        vib = float(rng.uniform(0.2 * vib_p.warn, 0.9 * vib_p.warn))
    elif target is Status.CRITICAL:
        temp = float(rng.uniform(temp_p.crit * 1.01, temp_p.crit * 1.25))
        vib = float(rng.uniform(0.2 * vib_p.warn, 1.3 * vib_p.crit))
    else:
        raise ValueError(f"unsupported lamp status: {target}")

    observed = NOW - timedelta(seconds=1)
    readings = {
        "temperature": Reading(temp, observed, Quality.GOOD),
        "vibration": Reading(vib, observed, Quality.GOOD),
    }
    status = evaluate_status(profile, readings, NOW, OFFLINE_AFTER)
    if status is not target:  # defesa: o rotulo vem da regra, nao da intencao
        raise AssertionError(f"rule says {status}, wanted {target}")
    return Truth(equipment_id, TYPE_BY_EQUIPMENT[equipment_id], seed.marker_id, status, temp, vib)
