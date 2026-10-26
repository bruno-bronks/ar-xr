"""Rota de INTEGRACAO somente leitura para sistemas externos (ex.: AR_XR).

Contrato minimo e estavel, separado das rotas internas:
- devolve APENAS `bed_id`, `sector`, `status` e `occupied` (booleano) por leito;
- NUNCA devolve `patient_id`, nome, idade, sexo, prioridade, payload de evento nem recomendacao;
- exige `Authorization: Bearer <HACC_INTEGRATION_TOKEN>`; sem o token configurado (>= 16 caracteres)
  a rota NAO existe (404), entao subir o HACC sem configurar nada nao abre a integracao;
- nao escreve nada e nao depende de MQTT.
"""

import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bed import Bed

router = APIRouter(
    prefix="/integration/v1",
    tags=["Integration"],
)

MIN_TOKEN_LENGTH = 16


def require_integration_token(
    authorization: str | None = Header(default=None),
) -> None:
    expected = os.getenv("HACC_INTEGRATION_TOKEN", "")

    if len(expected) < MIN_TOKEN_LENGTH:
        # Integracao desligada: a rota se comporta como inexistente.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    scheme, _, presented = (authorization or "").partition(" ")

    if scheme.lower() != "bearer" or not hmac.compare_digest(
        presented.encode(),
        expected.encode(),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/beds")
def integration_beds(
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(require_integration_token),
):
    response.headers["Cache-Control"] = "no-store"

    beds = (
        db.query(Bed)
        .order_by(Bed.sector, Bed.id)
        .all()
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "beds": [
            {
                "bed_id": bed.id,
                "sector": bed.sector,
                "status": bed.status,
                "occupied": bed.patient_id is not None,
            }
            for bed in beds
        ],
    }
