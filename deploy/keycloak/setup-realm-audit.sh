#!/bin/sh
# Turns on the realm's audit trail and a tighter brute-force lockout on a realm imported before
# Repody 1.8 (new installations get both from the realm file). Safe to run again. Run it on the
# server, from the stack's directory (each deploy copies it to tools/):
#
#   sh tools/setup-realm-audit.sh
#
# - Sign-in events (sign-ins, failures, sign-outs, password and two-factor changes) and admin
#   events (who changed which user, group or client) are kept 90 days, in Keycloak's database.
#   Admin events are stored without the changed object's full representation.
# - An account is locked for a while after 10 failed sign-ins in a row (Keycloak's default: 30).
#
# It signs in to Keycloak inside its container as the bootstrap admin (KC_BOOTSTRAP_ADMIN_*, the
# container's own environment). Read the events in the admin console: Realm settings > Events.
set -eu

docker compose --env-file .env --env-file release.env exec -T keycloak sh -eu -c "$(cat <<'KCADM'
kc=/opt/keycloak/bin/kcadm.sh
$kc config credentials --server http://localhost:8080 --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null
$kc update realms/repody \
  -s eventsEnabled=true -s eventsExpiration=7776000 \
  -s 'enabledEventTypes=["LOGIN","LOGIN_ERROR","LOGOUT","LOGOUT_ERROR","CODE_TO_TOKEN_ERROR","REFRESH_TOKEN_ERROR","CLIENT_LOGIN_ERROR","UPDATE_PASSWORD","UPDATE_PASSWORD_ERROR","UPDATE_CREDENTIAL","UPDATE_CREDENTIAL_ERROR","REMOVE_CREDENTIAL","REMOVE_CREDENTIAL_ERROR","UPDATE_TOTP","REMOVE_TOTP","RESET_PASSWORD","RESET_PASSWORD_ERROR","EXECUTE_ACTIONS","EXECUTE_ACTION_TOKEN","EXECUTE_ACTION_TOKEN_ERROR","USER_DISABLED_BY_TEMPORARY_LOCKOUT","USER_DISABLED_BY_PERMANENT_LOCKOUT"]' \
  -s adminEventsEnabled=true -s adminEventsDetailsEnabled=false \
  -s bruteForceProtected=true -s failureFactor=10
$kc get realms/repody --fields eventsEnabled,eventsExpiration,adminEventsEnabled,failureFactor
KCADM
)"
