#!/bin/sh
# Adds the admin area's Keycloak service account (repody-admin) to a realm imported before Repody
# 1.5. New installations get it from the realm file. Safe to run again. Run it on the server, from
# the stack's directory:
#
#   sh setup-admin-client.sh
#
# It reads KEYCLOAK_ADMIN_CLIENT_SECRET from .env, and signs in to Keycloak inside its container
# as the bootstrap admin (KC_BOOTSTRAP_ADMIN_*, the container's own environment).
set -eu

secret=$(grep '^KEYCLOAK_ADMIN_CLIENT_SECRET=' .env | cut -d= -f2-)
[ -n "${secret}" ] || { echo "Set KEYCLOAK_ADMIN_CLIENT_SECRET in .env first (openssl rand -hex 32)." >&2; exit 1; }

docker compose --env-file .env --env-file release.env exec -T -e SECRET="${secret}" keycloak \
  sh -eu -c "$(cat <<'KCADM'
kc=/opt/keycloak/bin/kcadm.sh
$kc config credentials --server http://localhost:8080 --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null
id=$($kc get clients -r repody -q clientId=repody-admin --fields id --format csv --noquotes)
if [ -z "$id" ]; then
  $kc create clients -r repody -s clientId=repody-admin -s "name=Repody admin area" \
    -s enabled=true -s publicClient=false -s standardFlowEnabled=false \
    -s implicitFlowEnabled=false -s directAccessGrantsEnabled=false \
    -s serviceAccountsEnabled=true -s fullScopeAllowed=false -s "secret=$SECRET"
  id=$($kc get clients -r repody -q clientId=repody-admin --fields id --format csv --noquotes)
  echo "Created the repody-admin client."
else
  $kc update "clients/$id" -r repody -s "secret=$SECRET" -s fullScopeAllowed=false
  echo "repody-admin exists: its secret is set again."
fi
# Keycloak 26.8.2+ accepts admin API tokens only with the kc-admin-api scope.
for scope in roles kc-admin-api; do
  sid=$($kc get client-scopes -r repody --fields id,name --format csv --noquotes | grep ",$scope\$" | cut -d, -f1)
  $kc update "clients/$id/default-client-scopes/$sid" -r repody
done
roles="manage-users view-users query-users query-groups"
rm_id=$($kc get clients -r repody -q clientId=realm-management --fields id --format csv --noquotes)
body="["
for role in $roles; do
  rid=$($kc get "clients/$rm_id/roles/$role" -r repody --fields id --format csv --noquotes)
  body="$body{\"id\":\"$rid\",\"name\":\"$role\"},"
done
body="${body%,}]"
echo "$body" | $kc create "clients/$id/scope-mappings/clients/$rm_id" -r repody -f -
set -- $roles
$kc add-roles -r repody --uusername service-account-repody-admin --cclientid realm-management \
  --rolename "$1" --rolename "$2" --rolename "$3" --rolename "$4"
echo "repody-admin: kc-admin-api scope, and manage-users, view-users, query-users, query-groups."
KCADM
)"
