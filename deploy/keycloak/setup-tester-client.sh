#!/bin/sh
# The production smoke test's account (deploy/vps/smoke_test.py): a Keycloak service account,
# repody-tester, in its own client company (group client-repody-test) with the operator role. It
# signs in with client credentials (no password, no browser) and sees only its own company's work.
# Safe to run again. Run it on the server, from the stack's directory:
#
#   sh tools/setup-tester-client.sh
#
# It reads TESTER_CLIENT_SECRET from .env (created there when missing, never printed), and signs
# in to Keycloak inside its container as the bootstrap admin (KC_BOOTSTRAP_ADMIN_*).
set -eu

if ! grep -q '^TESTER_CLIENT_SECRET=.' .env; then
  sed -i '/^TESTER_CLIENT_SECRET=/d' .env
  printf 'TESTER_CLIENT_SECRET=%s\n' "$(openssl rand -hex 32)" >> .env
  echo "TESTER_CLIENT_SECRET created in .env"
fi
secret=$(grep '^TESTER_CLIENT_SECRET=' .env | cut -d= -f2-)

docker compose --env-file .env --env-file release.env exec -T -e SECRET="${secret}" keycloak \
  sh -eu -c "$(cat <<'KCADM'
kc=/opt/keycloak/bin/kcadm.sh
$kc config credentials --server http://localhost:8080 --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null
id=$($kc get clients -r repody -q clientId=repody-tester --fields id --format csv --noquotes)
if [ -z "$id" ]; then
  $kc create clients -r repody -s clientId=repody-tester -s "name=Repody smoke test" \
    -s enabled=true -s publicClient=false -s standardFlowEnabled=false \
    -s implicitFlowEnabled=false -s directAccessGrantsEnabled=false \
    -s serviceAccountsEnabled=true -s fullScopeAllowed=false -s "secret=$SECRET" \
    -s 'protocolMappers=[{"name":"repody-api-audience","protocol":"openid-connect","protocolMapper":"oidc-audience-mapper","config":{"included.client.audience":"repody-api","access.token.claim":"true","id.token.claim":"false"}},{"name":"groups","protocol":"openid-connect","protocolMapper":"oidc-group-membership-mapper","config":{"full.path":"false","access.token.claim":"true","id.token.claim":"false","claim.name":"groups"}}]'
  id=$($kc get clients -r repody -q clientId=repody-tester --fields id --format csv --noquotes)
  echo "Created the repody-tester client."
else
  $kc update "clients/$id" -r repody -s "secret=$SECRET"
  echo "repody-tester exists: its secret is set again."
fi
# The operator role in its tokens (full scope off: only this role is mapped).
role=$($kc get roles/operator -r repody --fields id,name --format csv --noquotes)
echo "[{\"id\":\"${role%%,*}\",\"name\":\"operator\"}]" | $kc create "clients/$id/scope-mappings/realm" -r repody -f -
$kc add-roles -r repody --uusername service-account-repody-tester --rolename operator
gid=$($kc get groups -r repody -q search=client-repody-test --fields id,name --format csv --noquotes | grep ',client-repody-test$' | cut -d, -f1 || true)
if [ -z "$gid" ]; then
  $kc create groups -r repody -s name=client-repody-test >/dev/null
  gid=$($kc get groups -r repody -q search=client-repody-test --fields id,name --format csv --noquotes | grep ',client-repody-test$' | cut -d, -f1)
fi
uid=$($kc get users -r repody -q username=service-account-repody-tester --fields id --format csv --noquotes)
$kc update "users/$uid/groups/$gid" -r repody -n
echo "repody-tester: operator in client-repody-test."
KCADM
)"
