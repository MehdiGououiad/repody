# syntax=docker/dockerfile:1
# One backend image for api + workers (role chosen by the container command).
#   docker buildx bake backend --load      (see docker-bake.hcl)
# Role-specific targets (same layers): --target api | --target worker

FROM python:3.13.18-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

# Upgrade Debian security packages, then drop the base-image pip (vendored msgpack and setuptools).
# Every dependency ships a wheel (asyncpg, pypdfium2, Pillow, ...): no system libraries needed.
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/local/lib/python3.13/site-packages/pip \
      /usr/local/lib/python3.13/site-packages/pip-*.dist-info \
      /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.13 \
    && groupadd --system --gid 10001 repody \
    && useradd --system --uid 10001 --gid repody --home-dir /app --shell /usr/sbin/nologin repody \
    && mkdir -p /app \
    && chown repody:repody /app

FROM runtime-base AS build

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

WORKDIR /app

# Optional dependency groups from pyproject.toml (otel: the OpenTelemetry agent).
ARG BACKEND_EXTRAS=otel
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

FROM runtime-base AS app-runtime

WORKDIR /app

COPY --from=build --chown=repody:repody /opt/venv /opt/venv
COPY --chown=repody:repody alembic.ini ./
COPY --chown=repody:repody alembic/ ./alembic/
COPY --chown=repody:repody --chmod=755 scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh

USER repody

FROM app-runtime AS backend

ENV AUDIT_RUN_MIGRATIONS_ON_STARTUP=false \
    OTEL_SDK_DISABLED=true \
    OTEL_TRACES_EXPORTER=otlp \
    OTEL_METRICS_EXPORTER=none \
    OTEL_LOGS_EXPORTER=none \
    OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]

FROM backend AS worker

ENV OTEL_SERVICE_NAME=repody-worker
CMD ["sh", "-c", "exec taskiq worker repody.worker:broker --workers 1 --max-async-tasks ${AUDIT_WORKER_CONCURRENCY:-1}"]

FROM backend AS api

ENV OTEL_SERVICE_NAME=repody-api
EXPOSE 8000
CMD ["uvicorn", "repody.main:app", "--host", "0.0.0.0", "--port", "8000"]
