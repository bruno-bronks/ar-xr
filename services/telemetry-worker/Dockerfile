# Contexto de build = raiz do repositorio (ADR-0002): docker compose build worker
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

COPY services/telemetry-worker/requirements.txt .
RUN pip install -r requirements.txt

COPY packages/domain/src/spatial_domain ./spatial_domain
COPY packages/storage/src/spatial_storage ./spatial_storage
COPY packages/common/src/spatial_common ./spatial_common
COPY services/telemetry-worker/worker ./worker

RUN useradd --system --uid 10001 --no-create-home appuser
USER appuser

CMD ["python", "-m", "worker.main"]
