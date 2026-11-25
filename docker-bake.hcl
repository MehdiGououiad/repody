# Repody images - Docker Buildx Bake (https://docs.docker.com/build/bake/).
#
#   bun run images:build                      # docker buildx bake -f docker-bake.hcl --load
#   bun run images:release                    # docker buildx bake -f docker-bake.hcl --push
#   docker buildx bake -f docker-bake.hcl --print           # resolved config
#   docker buildx bake -f docker-bake.hcl backend --load    # one target
#
# Always pass -f docker-bake.hcl: without it bake also reads compose.yaml, whose variables
# (HATCHET_DB_PASSWORD) come from backend/.env.
#
# Every variable can be set from the environment of the same name:
#   REPODY_IMAGE_REGISTRY=ghcr.io/org REPODY_IMAGE_TAG=v1.2.3 \
#   REPODY_IMAGE_PLATFORMS=linux/amd64,linux/arm64 bun run images:release

variable "REPODY_IMAGE_REGISTRY" {
  default = ""
}

variable "REPODY_IMAGE_TAG" {
  default = "dev"
  validation {
    condition     = REPODY_IMAGE_TAG != "" && REPODY_IMAGE_TAG != "latest"
    error_message = "REPODY_IMAGE_TAG must be an immutable tag such as a semver or git SHA (not empty or \"latest\")."
  }
}

variable "REPODY_BACKEND_IMAGE_TAG" {
  default = REPODY_IMAGE_TAG
}

variable "REPODY_WEB_IMAGE_TAG" {
  default = REPODY_IMAGE_TAG
}

variable "REPODY_KEYCLOAK_IMAGE_TAG" {
  default = REPODY_IMAGE_TAG
}

# Comma-separated, e.g. linux/amd64,linux/arm64. Empty = builder's host platform.
variable "REPODY_IMAGE_PLATFORMS" {
  default = ""
}

# Python extras baked into the backend image (backend/pyproject.toml optional-dependencies).
variable "REPODY_BACKEND_EXTRAS" {
  default = "otel"
  validation {
    condition     = can(regex("^([A-Za-z0-9][A-Za-z0-9._-]*)?$", REPODY_BACKEND_EXTRAS))
    error_message = "REPODY_BACKEND_EXTRAS must be one optional-dependency name (\"otel\") or empty."
  }
}

variable "NEXT_PUBLIC_BUGSINK_DSN" {
  default = ""
}

function "image" {
  params = [name, tag]
  result = REPODY_IMAGE_REGISTRY != "" ? "${REPODY_IMAGE_REGISTRY}/${name}:${tag}" : "${name}:${tag}"
}

group "default" {
  targets = ["backend", "web", "keycloak"]
}

# Filled by docker/metadata-action in CI (OCI labels); empty locally.
target "docker-metadata-action" {}

target "_common" {
  inherits  = ["docker-metadata-action"]
  platforms = REPODY_IMAGE_PLATFORMS != "" ? split(",", REPODY_IMAGE_PLATFORMS) : []
}

# One image for api + workers; the role is chosen by the container command.
target "backend" {
  inherits = ["_common"]
  context  = "backend"
  target   = "backend"
  args = {
    BACKEND_EXTRAS = REPODY_BACKEND_EXTRAS
  }
  tags = [image("repody-backend", REPODY_BACKEND_IMAGE_TAG)]
}

target "web" {
  inherits   = ["_common"]
  context    = "."
  dockerfile = "Dockerfile.web"
  args = {
    NEXT_PUBLIC_BUGSINK_DSN = NEXT_PUBLIC_BUGSINK_DSN
  }
  tags = [image("repody-web", REPODY_WEB_IMAGE_TAG)]
}

# Production Keycloak: optimized build with the realm baked in (deploy/keycloak/Dockerfile).
target "keycloak" {
  inherits = ["_common"]
  context  = "deploy/keycloak"
  tags     = [image("repody-keycloak", REPODY_KEYCLOAK_IMAGE_TAG)]
}
