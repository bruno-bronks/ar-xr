# Contexto de build = raiz do repositorio (ADR-0002): docker compose build api
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

COPY services/api/requirements.txt .
RUN pip install -r requirements.txt

COPY packages/domain/src/spatial_domain ./spatial_domain
COPY packages/storage/src/spatial_storage ./spatial_storage
COPY packages/common/src/spatial_common ./spatial_common
COPY packages/assistant/src/spatial_assistant ./spatial_assistant
COPY packages/hacc/src/spatial_hacc ./spatial_hacc
COPY services/api/app ./app
COPY clients/web-fallback /srv/panel
COPY knowledge /srv/knowledge

RUN useradd --system --uid 10001 --no-create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:get_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
