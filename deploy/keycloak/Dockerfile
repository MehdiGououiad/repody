# syntax=docker/dockerfile:1
# Production Keycloak for Repody: an optimized build with the realm baked in.
# Keycloak's container guide (https://www.keycloak.org/server/containers): build once with
# `kc.sh build`, then run `start --optimized`. The realm's URLs, client secret and first admin are
# `${VAR}` placeholders read from the environment at import (https://www.keycloak.org/server/importExport);
# the import is skipped once the realm exists.
#   docker buildx bake keycloak --load      (see docker-bake.hcl)

FROM quay.io/keycloak/keycloak:26.8.2@sha256:723b1d6e254c0fc96d5cffec860c7e0744d6a3277822b865bb538cf891575e41 AS builder

# Build-time options: the database vendor and the health endpoints (management port 9000).
ENV KC_DB=postgres \
    KC_HEALTH_ENABLED=true

RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:26.8.2@sha256:723b1d6e254c0fc96d5cffec860c7e0744d6a3277822b865bb538cf891575e41

COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY realm-repody.production.json /opt/keycloak/data/import/realm-repody.json

# The upstream image's unprivileged user, stated so the image never runs as root.
USER 1000

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
CMD ["start", "--optimized", "--import-realm"]
