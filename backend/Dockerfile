# syntax=docker/dockerfile:1.7
# Multi-target image — one target per microservice role.
#   docker build --target api -t repody-api ./backend
#   docker build --target worker -t repody-worker ./backend

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl libpq5 \
      libgomp1 libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.21

WORKDIR /app

COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/
RUN mkdir -p src/audit_workbench && touch src/audit_workbench/__init__.py

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache -e ".[otel]"

COPY src/ ./src/
COPY scripts/ ./scripts/
RUN uv pip install --system --no-cache -e ".[otel]"
RUN chmod +x /app/scripts/docker-entrypoint.sh

# ── Worker plane (Hatchet — ocr + fast pools share image, different env) ────────
FROM base AS worker

ENV AUDIT_RUN_MIGRATIONS_ON_STARTUP=false \
    AUDIT_OTEL_SERVICE_NAME=repody-worker

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["python", "-m", "audit_workbench.hatchet.worker"]

# ── Control plane (FastAPI) — last stage = default `docker build` target ──────
FROM base AS api

ENV AUDIT_OTEL_SERVICE_NAME=repody-api

EXPOSE 8000
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "audit_workbench.main:app", "--host", "0.0.0.0", "--port", "8000"]
