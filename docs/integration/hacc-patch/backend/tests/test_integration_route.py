"""Testes da rota /integration/v1/beds (rodar: pip install pytest && pytest backend/tests)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.integration import router
from app.database import Base, get_db
from app.models.bed import Bed
from app.models.patient import Patient

TOKEN = "integration-test-token-123"  # valor ficticio de teste


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        db.add_all(
            [
                Bed(id="UTI-01", sector="ICU", status="occupied", patient_id="P-SECRET-1"),
                Bed(id="UTI-02", sector="ICU", status="available", patient_id=None),
                Bed(id="WARD-01", sector="Ward", status="unavailable", patient_id="P-SECRET-2"),
            ]
        )
        db.add(
            Patient(
                id="P-SECRET-1",
                name="Nome Ficticio Da Silva",
                age=61,
                gender="F",
                priority="critical",
                sector="ICU",
                bed_id="UTI-01",
            )
        )
        db.commit()

    app = FastAPI()
    app.include_router(router)

    def override():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override
    monkeypatch.setenv("HACC_INTEGRATION_TOKEN", TOKEN)
    return TestClient(app)


def _get(client, token=TOKEN):
    return client.get("/integration/v1/beds", headers={"Authorization": f"Bearer {token}"})


def test_returns_only_the_four_allowed_fields_per_bed(client):
    response = _get(client)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"generated_at", "beds"}
    assert [set(b) for b in body["beds"]] == [{"bed_id", "sector", "status", "occupied"}] * 3


def test_occupied_is_a_boolean_and_never_exposes_the_patient(client):
    text = _get(client).text

    beds = {b["bed_id"]: b for b in _get(client).json()["beds"]}
    assert beds["UTI-01"]["occupied"] is True
    assert beds["UTI-02"]["occupied"] is False
    assert beds["WARD-01"]["occupied"] is True  # indisponivel, mas com paciente associado
    assert beds["WARD-01"]["status"] == "unavailable"
    for forbidden in ("P-SECRET", "Nome Ficticio", "patient", "age", "gender", "priority", "61"):
        assert forbidden not in text


def test_requires_the_bearer_token(client):
    assert client.get("/integration/v1/beds").status_code == 401
    assert _get(client, "wrong-token-wrong-token").status_code == 401
    basic = client.get("/integration/v1/beds", headers={"Authorization": f"Basic {TOKEN}"})
    assert basic.status_code == 401
    assert basic.headers["www-authenticate"] == "Bearer"


def test_is_disabled_without_a_long_enough_token(client, monkeypatch):
    monkeypatch.delenv("HACC_INTEGRATION_TOKEN")
    assert _get(client).status_code == 404

    monkeypatch.setenv("HACC_INTEGRATION_TOKEN", "short")
    assert _get(client).status_code == 404


def test_is_not_cacheable(client):
    assert _get(client).headers["cache-control"] == "no-store"


def test_only_get_is_allowed(client):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    assert client.post("/integration/v1/beds", headers=headers, json={}).status_code == 405
    assert client.delete("/integration/v1/beds", headers=headers).status_code == 405
