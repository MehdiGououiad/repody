# syntax=docker/dockerfile:1
# One backend image for api + workers (role chosen by the container command).
#   docker buildx bake -f docker-bake.hcl backend --load      (see docker-bake.hcl)

FROM python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/opt/venv/bin:$PATH"

# Upgrade Debian security packages, then drop the base-image pip (vendored msgpack and setuptools).
# Every dependency ships a wheel (asyncpg, pypdfium2, Pillow, ...): no system libraries needed.
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/local/lib/python3.14/site-packages/pip \
      /usr/local/lib/python3.14/site-packages/pip-*.dist-info \
      /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.14 \
    && groupadd --system --gid 10001 repody \
    && useradd --system --uid 10001 --gid repody --home-dir /app --shell /usr/sbin/nologin repody \
    && mkdir -p /app \
    && chown repody:repody /app

FROM runtime-base AS build

COPY --from=ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 /uv /uvx /bin/

WORKDIR /app

# The optional dependencies to install (otel: the OpenTelemetry agent; empty for none).
# As uv's Docker guide does: dependencies first (a cached layer), then the project; never the
# dev group.
ARG BACKEND_EXTRAS=otel
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project ${BACKEND_EXTRAS:+--extra $BACKEND_EXTRAS}

COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable ${BACKEND_EXTRAS:+--extra $BACKEND_EXTRAS}

FROM runtime-base AS app-runtime

WORKDIR /app

# Root owns the code (read-only to the app); the app user only runs it.
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY --chmod=755 scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh

# Numeric, so Kubernetes `runAsNonRoot` can verify the user is not root (a name cannot be).
USER 10001:10001

FROM app-runtime AS backend

# Traces go to OTLP; logs are structlog JSON on stdout (collected into Loki).
ENV AUDIT_RUN_MIGRATIONS_ON_STARTUP=false \
    OTEL_SDK_DISABLED=true \
    OTEL_TRACES_EXPORTER=otlp \
    OTEL_METRICS_EXPORTER=none \
    OTEL_LOGS_EXPORTER=none \
    OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
