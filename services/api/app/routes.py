"""Rotas /api/v1 (SPEC-006). Toda consulta e filtrada pela organizacao do principal."""

import re
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from spatial_storage.repository import EquipmentRecord, Repository

from app.audit import audit, resource_id
from app.auth import Principal, require_principal
from app.ratelimit import FixedWindowLimiter
from app.schemas import AlertOut, EquipmentOut, ErrorOut, TelemetryReadingOut, TwinOut
from app.twin import TwinView, build_twin, derive_alerts

_EQUIPMENT_ID = re.compile(r"[A-Za-z0-9._:-]{1,64}")
_MARKER_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")
type _Responses = dict[int | str, dict[str, Any]]
_NOT_FOUND: _Responses = {404: {"model": ErrorOut}}
_UNAUTHORIZED: _Responses = {401: {"model": ErrorOut}}

PrincipalDep = Annotated[Principal, Depends(require_principal)]


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="not found")


def _repo(request: Request) -> Repository:
    repo: Repository = request.app.state.repo
    return repo


def _now(request: Request) -> datetime:
    clock: Callable[[], datetime] = request.app.state.clock
    return clock()


def _twin(
    repo: Repository, principal: Principal, equipment: EquipmentRecord, now: datetime
) -> TwinView:
    profile = repo.get_profile(equipment.id) or {}
    readings = repo.latest_readings(principal.org_id, equipment.id)
    return build_twin(equipment, profile, readings, now)


def _equipment_out(equipment: EquipmentRecord, twin: TwinView) -> EquipmentOut:
    return EquipmentOut(
        id=equipment.id,
        name=equipment.name,
        type=equipment.type,
        location=equipment.location,
        last_seen_at=equipment.last_seen_at,
        status=twin.status.value,
    )


def _owned(
    request: Request, principal: Principal, equipment_id: str, action: str
) -> EquipmentRecord:
    """Resolve o equipamento DENTRO da organizacao; inexistente e de outra org => 404 identico."""
    equipment = None
    if _EQUIPMENT_ID.fullmatch(equipment_id):
        equipment = _repo(request).get_equipment(principal.org_id, equipment_id)
    audit(
        principal,
        action,
        resource_id("equipment", equipment_id),
        "allowed" if equipment is not None else "not_found",
    )
    if equipment is None:
        raise _not_found()
    return equipment


router = APIRouter(prefix="/api/v1")


@router.get(
    "/equipment",
    response_model=list[EquipmentOut],
    tags=["equipment"],
    responses=_UNAUTHORIZED,
)
def list_equipment(request: Request, principal: PrincipalDep) -> list[EquipmentOut]:
    repo, now = _repo(request), _now(request)
    audit(principal, "equipment.list", "equipment", "allowed")
    return [
        _equipment_out(e, _twin(repo, principal, e, now))
        for e in repo.list_equipment(principal.org_id)
    ]


@router.get(
    "/equipment/{equipment_id}",
    response_model=EquipmentOut,
    tags=["equipment"],
    responses={**_UNAUTHORIZED, **_NOT_FOUND},
)
def get_equipment(equipment_id: str, request: Request, principal: PrincipalDep) -> EquipmentOut:
    equipment = _owned(request, principal, equipment_id, "equipment.get")
    return _equipment_out(equipment, _twin(_repo(request), principal, equipment, _now(request)))


@router.get(
    "/equipment/{equipment_id}/telemetry/latest",
    response_model=list[TelemetryReadingOut],
    tags=["equipment"],
    responses={**_UNAUTHORIZED, **_NOT_FOUND},
)
def latest_telemetry(
    equipment_id: str, request: Request, principal: PrincipalDep
) -> list[TelemetryReadingOut]:
    equipment = _owned(request, principal, equipment_id, "telemetry.latest")
    return [
        TelemetryReadingOut(
            equipment_id=r.equipment_id,
            sensor_type=r.sensor_type,
            value=r.value,
            unit=r.unit,
            observed_at=r.observed_at,
            received_at=r.received_at,
            quality=r.quality.value,
            event_id=r.event_id,
        )
        for r in _repo(request).latest_readings(principal.org_id, equipment.id)
    ]


@router.get(
    "/equipment/{equipment_id}/twin",
    response_model=TwinOut,
    tags=["equipment"],
    responses={**_UNAUTHORIZED, **_NOT_FOUND},
)
def get_twin(equipment_id: str, request: Request, principal: PrincipalDep) -> TwinOut:
    equipment = _owned(request, principal, equipment_id, "twin.get")
    twin = _twin(_repo(request), principal, equipment, _now(request))
    return TwinOut.model_validate(
        {
            "equipment_id": twin.equipment_id,
            "status": twin.status.value,
            "evaluated_at": twin.evaluated_at,
            "offline_after_seconds": int(twin.offline_after.total_seconds()),
            "sensors": [
                {**s.__dict__, "quality": s.quality.value if s.quality else None}
                for s in twin.sensors
            ],
        }
    )


@router.get(
    "/equipment/{equipment_id}/alerts",
    response_model=list[AlertOut],
    response_model_exclude_none=True,
    tags=["equipment"],
    responses={**_UNAUTHORIZED, **_NOT_FOUND},
)
def get_alerts(equipment_id: str, request: Request, principal: PrincipalDep) -> list[AlertOut]:
    equipment = _owned(request, principal, equipment_id, "alerts.list")
    twin = _twin(_repo(request), principal, equipment, _now(request))
    return [AlertOut.model_validate(a.__dict__) for a in derive_alerts(twin)]


@router.get(
    "/spatial/markers/{marker_id}",
    response_model=EquipmentOut,
    tags=["spatial"],
    responses={**_UNAUTHORIZED, **_NOT_FOUND, 429: {"model": ErrorOut}},
)
def resolve_marker(
    marker_id: str, request: Request, principal: PrincipalDep
) -> EquipmentOut | JSONResponse:
    limiter: FixedWindowLimiter = request.app.state.marker_limiter
    retry_after = limiter.hit(principal.user_id)
    if retry_after is not None:
        audit(principal, "marker.resolve", "marker", "rate_limited")
        return JSONResponse(
            status_code=429,
            content={"detail": "rate limit exceeded"},
            headers={"Retry-After": str(retry_after)},
        )
    equipment = None
    if _MARKER_ID.fullmatch(marker_id):
        equipment = _repo(request).get_equipment_by_marker(principal.org_id, marker_id)
    # o marker consultado NUNCA e registrado quando nao resolve (evita log de tentativas de enumeracao)
    audit(
        principal,
        "marker.resolve",
        resource_id("equipment", equipment.id) if equipment else "marker",
        "allowed" if equipment is not None else "not_found",
    )
    if equipment is None:
        raise _not_found()
    return _equipment_out(equipment, _twin(_repo(request), principal, equipment, _now(request)))
