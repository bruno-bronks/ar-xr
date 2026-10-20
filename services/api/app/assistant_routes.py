"""POST /api/v1/assistant/questions (SPEC-009). Assistivo: le o twin, nunca escreve nem aciona nada.

O texto da pergunta e da resposta NUNCA vai para log ou auditoria (D-022): so metadados.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from spatial_assistant.models import AssistantResult, LiveAlert, LiveState
from spatial_assistant.service import AssistantService
from spatial_assistant.text import normalize_text
from spatial_common.logging_json import correlation_id_var

from app.audit import audit, resource_id
from app.auth import Principal
from app.ratelimit import FixedWindowLimiter
from app.routes import PrincipalDep, _now, _owned, _repo, _twin
from app.schemas import AssistantAnswerOut, AssistantAskIn, ErrorOut
from app.twin import derive_alerts

_log = logging.getLogger("app.assistant")

router = APIRouter(prefix="/api/v1")


def _live_state(request: Request, principal: Principal, equipment_id: str) -> tuple[str, LiveState]:
    equipment = _owned(request, principal, equipment_id, "assistant.ask")
    twin = _twin(_repo(request), principal, equipment, _now(request))
    alerts = tuple(LiveAlert(a.severity, a.rule) for a in derive_alerts(twin))
    return equipment.type, LiveState(twin.status.value, alerts)


def _out(result: AssistantResult, live: LiveState) -> AssistantAnswerOut:
    return AssistantAnswerOut.model_validate(
        {
            "outcome": result.outcome.value,
            "answer": result.answer,
            "confidence": result.confidence.value,
            "sources": [s.__dict__ for s in result.sources],
            "human_review_required": result.human_review_required,
            "provider": result.provider.value,
            "fallback_used": result.fallback_used,
            "refusal_reason": result.refusal_reason.value if result.refusal_reason else None,
            "live_state": {
                "status": live.status,
                "alerts": [a.__dict__ for a in live.alerts],
            },
        }
    )


@router.post(
    "/assistant/questions",
    response_model=AssistantAnswerOut,
    tags=["assistant"],
    responses={
        401: {"model": ErrorOut},
        404: {"model": ErrorOut},
        429: {"model": ErrorOut},
    },
)
def ask_assistant(
    body: AssistantAskIn, request: Request, principal: PrincipalDep
) -> AssistantAnswerOut | JSONResponse:
    limiter: FixedWindowLimiter = request.app.state.assistant_limiter
    retry_after = limiter.hit(principal.user_id)
    if retry_after is not None:
        audit(principal, "assistant.ask", "assistant", "rate_limited")
        return JSONResponse(
            status_code=429,
            content={"detail": "rate limit exceeded"},
            headers={"Retry-After": str(retry_after)},
        )
    equipment_type, live = _live_state(request, principal, body.equipment_id)
    question = normalize_text(body.question)
    if not question:
        raise HTTPException(status_code=422, detail="question must not be empty")

    service: AssistantService = request.app.state.assistant
    result = service.ask(question, equipment_type, live)

    audit(
        principal,
        "assistant.ask",
        resource_id("equipment", body.equipment_id),
        result.outcome.value,
    )
    _log.info(
        "assistant",
        extra={
            "outcome": result.outcome.value,
            "provider": result.provider.value,
            "fallback_used": result.fallback_used,
            "refusal_reason": result.refusal_reason.value if result.refusal_reason else None,
            "source_ids": [s.chunk_id for s in result.sources],
            "question_chars": len(body.question),
            "answer_chars": len(result.answer),
            "human_review_required": result.human_review_required,
            "correlation_id": correlation_id_var.get(),
        },
    )
    return _out(result, live)
