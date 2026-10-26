"""GET /api/v1/hacc/* (SPEC-010). SOMENTE LEITURA, escopo hacc:read, segregacao imposta aqui.

O `tenant_id` de cada registro e comparado com a organizacao do principal NESTE codigo (D-030): nada
e confiado ao HACC. Auditoria e logs nunca registram estado/rotulo de leito (REQ-HACC-004).
"""

import logging
import re
from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from spatial_common.logging_json import correlation_id_var
from spatial_domain.beds import (
    BedFlags,
    BedReading,
    BedStatus,
    bed_alerts,
    evaluate_bed,
    worst_status,
)
from spatial_hacc.models import BedRecord, WardRecord
from spatial_hacc.source import HaccSource, HaccUnavailable

from app.audit import audit, resource_id
from app.auth import Principal, require_scope
from app.schemas import (
    ErrorOut,
    HaccAlertOut,
    HaccBedOut,
    HaccWardBedsOut,
    HaccWardInfoOut,
    HaccWardSummaryOut,
)

_log = logging.getLogger("app.hacc")
_WARD_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")
SCOPE = "hacc:read"

HaccPrincipal = Annotated[Principal, Depends(require_scope(SCOPE))]
router = APIRouter(prefix="/api/v1/hacc", tags=["hacc"])


def _source(request: Request) -> HaccSource:
    source: HaccSource = request.app.state.hacc
    return source


def _now(request: Request) -> datetime:
    clock: Callable[[], datetime] = request.app.state.clock
    return clock()


def _unavailable(error: HaccUnavailable) -> HTTPException:
    _log.warning("hacc source unavailable", extra={"error_type": type(error).__name__})
    return HTTPException(status_code=503, detail="hacc source unavailable")


def _own_wards(source: HaccSource, org_id: str) -> list[WardRecord]:
    return [w for w in source.list_wards() if w.tenant_id == org_id]


def _own_beds(source: HaccSource, org_id: str, ward_id: str) -> list[BedRecord]:
    return [b for b in source.list_beds(ward_id) if b.tenant_id == org_id and b.ward_id == ward_id]


def _reading(bed: BedRecord) -> BedReading:
    f = bed.flags
    return BedReading(
        bed.occupied,
        BedFlags(f.bed_exit_alarm, f.iv_pump_alarm, f.call_button, f.cleaning_due),
        bed.observed_at,
        blocked=bed.blocked,
    )


def _bed_out(bed: BedRecord, now: datetime) -> tuple[HaccBedOut, BedStatus]:
    reading = _reading(bed)
    status = evaluate_bed(reading, now)
    out = HaccBedOut(
        bed_id=bed.bed_id,
        label=bed.label,
        x=bed.x,
        y=bed.y,
        occupied=bed.occupied,
        status=status.value,
        observed_at=bed.observed_at,
        alerts=[HaccAlertOut(severity=a.severity, rule=a.rule) for a in bed_alerts(reading, now)],
    )
    return out, status


@router.get(
    "/wards",
    response_model=list[HaccWardSummaryOut],
    responses={401: {"model": ErrorOut}, 403: {"model": ErrorOut}, 503: {"model": ErrorOut}},
)
def list_wards(request: Request, principal: HaccPrincipal) -> list[HaccWardSummaryOut]:
    source, now = _source(request), _now(request)
    summaries: list[HaccWardSummaryOut] = []
    total_beds = 0
    try:
        for ward in _own_wards(source, principal.org_id):
            beds = [_bed_out(b, now) for b in _own_beds(source, principal.org_id, ward.ward_id)]
            total_beds += len(beds)
            summaries.append(
                HaccWardSummaryOut(
                    ward_id=ward.ward_id,
                    name=ward.name,
                    bed_count=len(beds),
                    status=worst_status(s for _, s in beds).value,
                    alert_count=sum(len(b.alerts) for b, _ in beds),
                )
            )
    except HaccUnavailable as error:
        audit(principal, "hacc.wards.list", "hacc/wards", "unavailable")
        raise _unavailable(error) from None
    audit(principal, "hacc.wards.list", "hacc/wards", "allowed")
    _log.info(
        "hacc wards",
        extra={
            "wards": len(summaries),
            "beds": total_beds,
            "correlation_id": correlation_id_var.get(),
        },
    )
    return summaries


@router.get(
    "/wards/{ward_id}/beds",
    response_model=HaccWardBedsOut,
    responses={
        401: {"model": ErrorOut},
        403: {"model": ErrorOut},
        404: {"model": ErrorOut},
        503: {"model": ErrorOut},
    },
)
def list_beds(ward_id: str, request: Request, principal: HaccPrincipal) -> HaccWardBedsOut:
    source, now = _source(request), _now(request)
    resource = resource_id("ward", ward_id)
    ward: WardRecord | None = None
    try:
        if _WARD_ID.fullmatch(ward_id):
            ward = next(
                (w for w in _own_wards(source, principal.org_id) if w.ward_id == ward_id), None
            )
        if ward is None:
            audit(principal, "hacc.beds.list", resource, "not_found")
            raise HTTPException(status_code=404, detail="not found")
        beds = [_bed_out(b, now) for b in _own_beds(source, principal.org_id, ward.ward_id)]
    except HaccUnavailable as error:
        audit(principal, "hacc.beds.list", resource, "unavailable")
        raise _unavailable(error) from None
    beds.sort(key=lambda pair: (pair[0].y, pair[0].x, pair[0].bed_id))
    audit(principal, "hacc.beds.list", resource, "allowed")
    _log.info(
        "hacc beds",
        extra={"beds": len(beds), "correlation_id": correlation_id_var.get()},
    )
    return HaccWardBedsOut(
        ward=HaccWardInfoOut(
            ward_id=ward.ward_id, name=ward.name, width=ward.width, height=ward.height
        ),
        evaluated_at=now,
        status=worst_status(s for _, s in beds).value,
        beds=[b for b, _ in beds],
    )
