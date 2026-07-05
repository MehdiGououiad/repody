# syntax=docker/dockerfile:1.7
# One backend image for api + workers (role chosen by Kubernetes command).
#   pnpm images:build -- --only=backend
# Role-specific targets (same layers): --target api | --target worker

FROM python:3.13.14-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libpq5 libgomp1 libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 repody \
    && useradd --system --uid 10001 --gid repody --home-dir /app --shell /usr/sbin/nologin repody \
    && mkdir -p /app /app/.data/storage /app/benchmark-reports /tmp/repody \
    && chown -R repody:repody /app /tmp/repody

FROM runtime-base AS build

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG BACKEND_EXTRAS=otel
ARG INCLUDE_BENCHMARK_FIXTURES=false
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    set -eux; \
    extras=""; \
    for extra in $(echo "$BACKEND_EXTRAS" | tr "," " "); do extras="$extras --extra $extra"; done; \
    uv sync --locked --no-dev --no-install-project $extras

COPY src/ ./src/
COPY scripts/ ./scripts/
RUN --mount=type=cache,target=/root/.cache/uv \
    set -eux; \
    extras=""; \
    for extra in $(echo "$BACKEND_EXTRAS" | tr "," " "); do extras="$extras --extra $extra"; done; \
    uv sync --locked --no-dev --no-editable $extras

# Empty default; `pnpm images:build` may override via --build-context benchmark-fixtures=...
FROM scratch AS benchmark-fixtures

FROM runtime-base AS app-runtime

ARG INCLUDE_BENCHMARK_FIXTURES=false

WORKDIR /app

COPY --from=build --chown=repody:repody /opt/venv /opt/venv
COPY --chown=repody:repody alembic.ini ./
COPY --chown=repody:repody alembic/ ./alembic/
COPY --chown=repody:repody --chmod=755 scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh
COPY --chown=repody:repody scripts/bootstrap_migrations.py ./scripts/bootstrap_migrations.py
COPY --chown=repody:repody scripts/benchmark_suite.py ./scripts/benchmark_suite.py
COPY --from=benchmark-fixtures --chown=repody:repody / /tmp/benchmark-fixtures/

RUN set -eux; \
    mkdir -p /app/e2e/fixtures/documents; \
    if [ "$INCLUDE_BENCHMARK_FIXTURES" = "true" ]; then \
      cp -a /tmp/benchmark-fixtures/. /app/e2e/fixtures/documents/; \
    fi; \
    rm -rf /tmp/benchmark-fixtures; \
    chmod +x /app/scripts/docker-entrypoint.sh

USER repody

FROM app-runtime AS backend

ENV AUDIT_RUN_MIGRATIONS_ON_STARTUP=false

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]

FROM backend AS worker

ENV AUDIT_OTEL_SERVICE_NAME=repody-worker
CMD ["python", "-m", "audit_workbench.taskiq.worker"]

FROM backend AS api

ENV AUDIT_OTEL_SERVICE_NAME=repody-api
EXPOSE 8000
CMD ["uvicorn", "audit_workbench.main:app", "--host", "0.0.0.0", "--port", "8000"]
