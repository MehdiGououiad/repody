#!/usr/bin/env bash
# Off-site backups of a stack (deploy/vps/README.md, "Backups"): every Postgres database
# (Repody, Keycloak, Hatchet) and the uploaded documents (SeaweedFS), encrypted by restic into
# object storage (Cloudflare R2). Run it from the stack's directory, as deploy:
#
#   bash tools/backup.sh             back up now, then keep 7 daily, 4 weekly, 12 monthly
#   bash tools/backup.sh check       verify the repository and 5% of its data
#   bash tools/backup.sh restore-test   restore the latest database dump into a throwaway
#                                    Postgres and the latest documents into a temporary folder
#
# Its settings live outside the stack, in ~/.config/repody-backup.env (mode 600):
#   RESTIC_REPOSITORY=s3:https://<account>.r2.cloudflarestorage.com/repody-backups
#   RESTIC_PASSWORD=...           the encryption key: keep a copy off the server, or the
#                                 backups cannot be read after the server is gone
#   AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...   an R2 token for that bucket only
#   HEALTHCHECK_URL=...           optional: pinged after a good backup, /fail after a bad one
# restic runs from its image (pinned below): nothing is installed on the server.
set -euo pipefail

IMAGE="restic/restic:0.19.1@sha256:136600b6ff6843d61d355f7f71f460a166429f35de6fd11b568fece3c9a4d510"
CONFIG="${HOME}/.config/repody-backup.env"
[ -s "${CONFIG}" ] || { echo "Create ${CONFIG} first (see the top of this script)." >&2; exit 1; }
# shellcheck disable=SC1090
HEALTHCHECK_URL="$(. "${CONFIG}" && echo "${HEALTHCHECK_URL:-}")"

project="$(grep '^COMPOSE_PROJECT_NAME=' .env | cut -d= -f2- || true)"
project="${project:-repody}"
compose=(docker compose --env-file .env --env-file release.env)
work="$(mktemp -d "${HOME}/.repody-backup.XXXXXX")"
trap 'rm -rf "${work}"' EXIT
mkdir -p "${HOME}/.cache/restic"

# restic, with the stack's documents mounted read-only and the dump folder beside them.
restic() {
  docker run --rm -i --env-file "${CONFIG}" --hostname "${project}" --user "$(id -u):$(id -g)" \
    -e RESTIC_CACHE_DIR=/cache -v "${HOME}/.cache/restic:/cache" \
    -v "${project}_seaweedfs-data:/data/documents:ro" -v "${work}:/data/dump" "${IMAGE}" "$@"
}

ping() { [ -z "${HEALTHCHECK_URL}" ] || curl -fsS -m 10 --retry 3 -o /dev/null "${HEALTHCHECK_URL}$1" || true; }

backup() {
  restic cat config > /dev/null 2>&1 || restic init
  # A dump that failed halfway must not become a snapshot: dump to a file first.
  "${compose[@]}" exec -T postgres pg_dumpall -U repody > "${work}/postgres.sql"
  test -s "${work}/postgres.sql"
  restic backup --tag postgres --host "${project}" /data/dump/postgres.sql
  restic backup --tag documents --host "${project}" /data/documents
  restic forget --host "${project}" --group-by host,tags \
    --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune
  echo "backed up ${project}: databases and documents"
}

check() {
  restic check --read-data-subset=5%
}

restore_test() {
  restic restore latest --host "${project}" --tag postgres --target /data/dump
  local dump="${work}/data/dump/postgres.sql"
  test -s "${dump}"
  db="repody-restore-test-$$"
  docker run -d --rm --name "${db}" -e POSTGRES_PASSWORD=restore-test postgres:18.6-alpine > /dev/null
  trap 'docker rm -f "${db}" > /dev/null 2>&1; rm -rf "${work}"' EXIT
  until docker exec "${db}" pg_isready -U postgres > /dev/null 2>&1; do sleep 1; done
  docker exec -i "${db}" psql -q -U postgres -v ON_ERROR_STOP=0 < "${dump}" > /dev/null 2>&1 || true
  local runs workflows
  runs="$(docker exec "${db}" psql -U postgres -d repody -Atc 'select count(*) from runs')"
  workflows="$(docker exec "${db}" psql -U postgres -d repody -Atc 'select count(*) from workflows')"
  echo "database restored: ${workflows} workflows, ${runs} runs"
  restic restore latest --host "${project}" --tag documents --target /data/dump
  echo "documents restored: $(find "${work}/data/documents" -type f | wc -l) files"
}

case "${1:-backup}" in
  backup) if backup; then ping ""; else ping "/fail"; exit 1; fi ;;
  check) check ;;
  restore-test) restore_test ;;
  *) echo "usage: bash tools/backup.sh [backup|check|restore-test]" >&2; exit 2 ;;
esac
