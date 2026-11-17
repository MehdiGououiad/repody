#!/bin/sh
# The smoke test's account (deploy/vps/smoke_test.py): a Keycloak service account, repody-tester,
# in its own client company (group client-repody-test) with the operator role. It signs in with
# client credentials (no password, no browser) and sees only its own company's work.
# Safe to run again. Run it on the server, from the stack's directory:
#
#   sh tools/setup-tester-client.sh
#
# It reads TESTER_CLIENT_SECRET from .env (created there when missing, never printed), and signs
# in to Keycloak inside its container as the bootstrap admin (KC_BOOTSTRAP_ADMIN_*).
#
# On staging only (DEPLOYMENT_ENVIRONMENT=staging in .env), it also creates a person to sign in
# with in the browser, for UI tests: tester@<APP_HOST>, operator in the same company, with the
# password UI_TESTER_PASSWORD (created in .env, never printed) and no required actions.
# Production never gets a password account that skips them.
set -eu

# The value of a secret in .env, created there first when missing or empty.
secret_in_env() {
  if ! grep -q "^$1=." .env; then
    sed -i "/^$1=/d" .env
    printf '%s=%s\n' "$1" "$(openssl rand -hex 32)" >> .env
    echo "$1 created in .env" >&2
  fi
  grep "^$1=" .env | cut -d= -f2-
}

secret=$(secret_in_env TESTER_CLIENT_SECRET)
ui_email=""
ui_password=""
if grep -qx 'DEPLOYMENT_ENVIRONMENT=staging' .env; then
  ui_email="tester@$(grep '^APP_HOST=' .env | cut -d= -f2-)"
  ui_password=$(secret_in_env UI_TESTER_PASSWORD)
fi

docker compose --env-file .env --env-file release.env exec -T -e SECRET="${secret}" \
  -e UI_EMAIL="${ui_email}" -e UI_PASSWORD="${ui_password}" keycloak \
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

if [ -n "$UI_EMAIL" ]; then
  uid=$($kc get users -r repody -q "email=$UI_EMAIL" -q exact=true --fields id --format csv --noquotes)
  if [ -z "$uid" ]; then
    $kc create users -r repody -s "username=$UI_EMAIL" -s "email=$UI_EMAIL" -s emailVerified=true \
      -s enabled=true -s firstName=UI -s lastName=Tester >/dev/null
    uid=$($kc get users -r repody -q "email=$UI_EMAIL" -q exact=true --fields id --format csv --noquotes)
  fi
  $kc update "users/$uid" -r repody -s 'requiredActions=[]'
  $kc set-password -r repody --userid "$uid" --new-password "$UI_PASSWORD"
  $kc add-roles -r repody --uid "$uid" --rolename operator
  $kc update "users/$uid/groups/$gid" -r repody -n
  echo "$UI_EMAIL: operator in client-repody-test (password: UI_TESTER_PASSWORD in .env)."
fi
KCADM
)"
