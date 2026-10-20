"""Fonte HACC SIMULADA e deterministica por relogio (SPEC-010, D-025/D-028). Padrao do sistema.

Nenhum dado real: leitos com ids opacos e sinalizadores operacionais gerados de um ciclo de 60 s
(quatro fases de 15 s). Nao ha campo identificavel de pessoa.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from spatial_hacc.models import BedRecord, FlagsRecord, WardRecord

PHASE_SECONDS = 15
STALE_AGE = timedelta(seconds=120)  # leito "mudo": leitura velha => OFFLINE no dominio

_WARDS = (
    WardRecord(
        ward_id="WARD-A1", tenant_id="org-a", name="Ala A - Clínica (demo)", width=3, height=2
    ),
    WardRecord(ward_id="WARD-UTI", tenant_id="org-a", name="UTI (demo)", width=2, height=2),
    WardRecord(
        ward_id="WARD-B1", tenant_id="org-b", name="Ala B1 sentinela (demo)", width=2, height=1
    ),
)

# (ward, bed_id, label, x, y, occupied)
_LAYOUT = (
    ("WARD-A1", "A1-01", "Leito 01", 1, 1, True),
    ("WARD-A1", "A1-02", "Leito 02", 2, 1, True),
    ("WARD-A1", "A1-03", "Leito 03", 3, 1, True),
    ("WARD-A1", "A1-04", "Leito 04", 1, 2, False),
    ("WARD-A1", "A1-05", "Leito 05", 2, 2, True),
    ("WARD-A1", "A1-06", "Leito 06", 3, 2, True),  # sem leitura nenhuma => UNKNOWN
    ("WARD-UTI", "U-01", "UTI 01", 1, 1, True),
    ("WARD-UTI", "U-02", "UTI 02", 2, 1, True),
    ("WARD-UTI", "U-03", "UTI 03", 1, 2, True),  # mudo => OFFLINE
    ("WARD-UTI", "U-04", "UTI 04", 2, 2, True),
    ("WARD-B1", "B-01", "Leito B1", 1, 1, True),
    ("WARD-B1", "B-02", "Leito B2", 2, 1, False),
)
_TENANT = {w.ward_id: w.tenant_id for w in _WARDS}


def _flags(bed_id: str, phase: int) -> FlagsRecord:
    return FlagsRecord(
        bed_exit_alarm=bed_id == "A1-01" and phase == 1,
        iv_pump_alarm=(bed_id == "A1-03" and phase == 3) or (bed_id == "U-01" and phase in {0, 2}),
        call_button=(bed_id == "A1-02" and phase == 2) or (bed_id == "U-04" and phase == 1),
        cleaning_due=bed_id == "A1-04" and phase != 0,
    )


class SimulatedHaccSource:
    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    def list_wards(self) -> list[WardRecord]:
        return list(_WARDS)

    def list_beds(self, ward_id: str) -> list[BedRecord]:
        now = self._clock()
        phase = int(now.timestamp()) // PHASE_SECONDS % 4
        beds: list[BedRecord] = []
        for ward, bed_id, label, x, y, occupied in _LAYOUT:
            if ward != ward_id:
                continue
            observed: datetime | None = now
            if bed_id == "A1-06":
                observed = None
            elif bed_id == "U-03":
                observed = now - STALE_AGE
            beds.append(
                BedRecord(
                    bed_id=bed_id,
                    ward_id=ward,
                    tenant_id=_TENANT[ward],
                    label=label,
                    x=x,
                    y=y,
                    occupied=occupied,
                    flags=_flags(bed_id, phase),
                    observed_at=observed,
                )
            )
        return beds
