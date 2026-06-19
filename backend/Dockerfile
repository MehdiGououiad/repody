# syntax=docker/dockerfile:1.7
# Multi-target image: one hardened runtime target per backend role.
#   docker build --target api -t repody-api ./backend
#   docker build --target worker -t repody-worker ./backend

FROM python:3.13.14-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      curl libpq5 libgomp1 libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 repody \
    && useradd --system --uid 10001 --gid repody --home-dir /app --shell /usr/sbin/nologin repody \
    && mkdir -p /app /app/.data/storage /app/benchmark-reports /tmp/repody \
    && chown -R repody:repody /app /tmp/repody

FROM runtime-base AS build

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.11.21 \
    && python -m venv "$VIRTUAL_ENV"

WORKDIR /app

COPY pyproject.toml ./
COPY alembic.ini ./
COPY alembic/ ./alembic/
RUN mkdir -p src/audit_workbench && touch src/audit_workbench/__init__.py

ARG BACKEND_EXTRAS=otel
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python "$VIRTUAL_ENV/bin/python" --no-cache -e ".[${BACKEND_EXTRAS}]"

COPY src/ ./src/
COPY scripts/ ./scripts/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python "$VIRTUAL_ENV/bin/python" --no-cache -e ".[${BACKEND_EXTRAS}]"

FROM runtime-base AS app-runtime

WORKDIR /app

COPY --from=build --chown=repody:repody /opt/venv /opt/venv
COPY --chown=repody:repody alembic.ini ./
COPY --chown=repody:repody alembic/ ./alembic/
COPY --chown=repody:repody src/ ./src/
COPY --chown=repody:repody --chmod=755 scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh
COPY --chown=repody:repody scripts/ ./scripts/

RUN chmod +x /app/scripts/docker-entrypoint.sh \
    && chown -R repody:repody /app /opt/venv

USER repody

FROM app-runtime AS worker

ENV AUDIT_RUN_MIGRATIONS_ON_STARTUP=false \
    AUDIT_OTEL_SERVICE_NAME=repody-worker

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["python", "-m", "audit_workbench.hatchet.worker"]

FROM app-runtime AS api

ENV AUDIT_OTEL_SERVICE_NAME=repody-api

EXPOSE 8000
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "audit_workbench.main:app", "--host", "0.0.0.0", "--port", "8000"]
