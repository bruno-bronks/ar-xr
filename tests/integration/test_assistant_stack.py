"""SPEC-009: assistente contra a pilha REAL (API em container, PostgreSQL real, base em /srv/knowledge).

Requisitos: REQ-AI-001, REQ-AI-002, REQ-AI-003, REQ-AI-004, REQ-AI-006.
"""

import pytest

from tests.integration._stack import (
    TOKEN_A,
    TOKEN_B,
    api,
    api_post,
    compose,
    requires_stack,
    wait_until,
)

pytestmark = [pytest.mark.integration, requires_stack]

ASK = "/api/v1/assistant/questions"
UNIQUE = "ZEBRAINTEGRACAO"


def _ready() -> bool:
    return api("/api/v1/equipment")[0] == 200


def test_answer_cites_the_approved_document_in_the_container() -> None:
    wait_until(lambda: _ready() or None, 30, what="API pronta")

    status, body = api_post(
        ASK,
        {"equipment_id": "EQ-001", "question": "Por que a temperatura do compressor está alta?"},
    )

    assert status == 200
    assert body["outcome"] == "answered"
    assert body["provider"] == "extractive"
    assert body["sources"][0]["document_id"] == "DOC-COMP-001"
    assert body["live_state"]["status"] in {"NORMAL", "WARNING", "CRITICAL", "OFFLINE", "UNKNOWN"}


def test_unsafe_and_unknown_questions_are_not_answered_over_real_http() -> None:
    refused = api_post(ASK, {"equipment_id": "EQ-001", "question": "Desligue o compressor"})[1]
    unknown = api_post(ASK, {"equipment_id": "EQ-001", "question": "Qual a capital da França?"})[1]

    assert refused["outcome"] == "refused"
    assert refused["refusal_reason"] == "physical_action"
    assert unknown["outcome"] == "insufficient_evidence"
    assert unknown["sources"] == []


def test_authorization_and_org_isolation_are_enforced() -> None:
    body = {"equipment_id": "EQ-001", "question": "Por que a temperatura está alta?"}

    assert api_post(ASK, body, token=None)[0] == 401
    foreign = api_post(ASK, body, token=TOKEN_B)
    missing = api_post(ASK, {**body, "equipment_id": "EQ-NOPE"}, token=TOKEN_A)
    assert foreign[0] == missing[0] == 404
    assert foreign[1] == missing[1] == {"detail": "not found"}


def test_container_logs_have_the_knowledge_base_summary_and_never_the_question() -> None:
    api_post(
        ASK, {"equipment_id": "EQ-001", "question": f"Por que a temperatura está alta? {UNIQUE}"}
    )

    logs = compose("logs", "--no-color", "api").stdout

    assert "knowledge base loaded" in logs
    assert '"rejected": []' in logs
    assert '"logger": "app.assistant"' in logs
    assert UNIQUE not in logs
