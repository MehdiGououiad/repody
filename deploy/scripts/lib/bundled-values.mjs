/**
 * Generate bundled-profile Helm values fragments for lab scripts and docs.
 * Matches deploy/client/values-bundled.example.yaml contract.
 */

/**
 * @param {object} opts
 * @param {string} opts.imageRepo full registry path including project, e.g. ghcr.io/yourorg/repody
 * @param {string} opts.tag
 * @param {object} opts.hosts { web, api, auth, files }
 * @param {string} [opts.vlmUrl]
 * @param {string} [opts.jwksUrl]
 * @param {string} [opts.ingressClassName]
 * @param {string} [opts.vlmServedModel]
 */
export function bundledRepodyValuesYaml({
  imageRepo,
  tag,
  hosts,
  vlmUrl,
  jwksUrl,
  ingressClassName,
  vlmServedModel,
}) {
  const vlm = vlmUrl ?? "http://127.0.0.1:65535/v1";
  const jwks =
    jwksUrl ?? "http://keycloak.repody.svc.cluster.local:8080/realms/repody/protocol/openid-connect/certs";
  const classLine = ingressClassName ? `\n  className: ${ingressClassName}` : "";
  const modelLine = vlmServedModel ? `\n  vllmServedModel: ${vlmServedModel}` : "";

  return `# Generated bundled client values (lab)
global:
  deploymentProfile: bundled
  imagePullSecrets:
    - name: registry-pull-secret

ingress:
  enabled: true
  host: ${hosts.web}
  apiHost: ${hosts.api}
  filesHost: ${hosts.files}
  filesServiceName: repody-data-minio
  filesServicePort: 9000${classLine}
  tls:
    enabled: true
    secretName: repody-tls

images:
  backend:
    repository: ${imageRepo}/repody-backend
    tag: ${tag}
    pullPolicy: Always
  api:
    repository: ${imageRepo}/repody-backend
    tag: ${tag}
    pullPolicy: Always
  worker:
    repository: ${imageRepo}/repody-backend
    tag: ${tag}
    pullPolicy: Always
  web:
    repository: ${imageRepo}/repody-web
    tag: ${tag}
    pullPolicy: Always

secrets:
  existingSecret: repody-runtime-secrets

externalDatabase:
  existingSecret: repody-runtime-secrets
  urlKey: AUDIT_DATABASE_URL

externalRedis:
  existingSecret: repody-runtime-secrets
  urlKey: AUDIT_REDIS_URL

externalObjectStorage:
  endpoint: repody-data-minio:9000
  bucket: audit-documents
  existingSecret: repody-runtime-secrets
  accessKeyKey: AUDIT_MINIO_ACCESS_KEY
  secretKeyKey: AUDIT_MINIO_SECRET_KEY
  secure: false
  publicEndpoint: ${hosts.files}

config:
  authUrl: https://${hosts.web}
  oidcIssuer: https://${hosts.auth}/realms/repody
  oidcJwksUrl: ${jwks}
  keycloakAdminUrl: https://${hosts.auth}
  corsOrigins: '["https://${hosts.web}"]'
  vllmBaseUrl: ${vlm}${modelLine}
  operatorActionsEnabled: false

observability:
  otelEnabled: true
  otelEndpoint: http://otel-collector-opentelemetry-collector.observability.svc.cluster.local:4318/v1/traces

migrations:
  enabled: true
`;
}

/**
 * Keycloak auth chart overlay for lab ingress.
 * @param {object} opts
 * @param {string} opts.authHost
 * @param {string} [opts.className]
 */
export function bundledAuthValuesYaml({ authHost, className = "traefik" }) {
  return `# Generated bundled auth values (lab)
ingress:
  enabled: true
  host: ${authHost}
  className: ${className}
  tls:
    enabled: true
    secretName: repody-tls

keycloak:
  hostname: ${authHost}
  existingSecret: repody-runtime-secrets
  adminPassword: ""
`;
}

/**
 * External profile lab values — connection strings from Vault; data plane deployed separately.
 * @param {object} opts
 */
export function externalRepodyValuesYaml({
  imageRepo,
  tag,
  hosts,
  vlmUrl,
  jwksUrl,
  ingressClassName,
  vlmServedModel,
}) {
  const vlm = vlmUrl ?? "http://127.0.0.1:65535/v1";
  const jwks =
    jwksUrl ?? "http://keycloak.repody.svc.cluster.local:8080/realms/repody/protocol/openid-connect/certs";
  const classLine = ingressClassName ? `\n  className: ${ingressClassName}` : "";
  const modelLine = vlmServedModel ? `\n  vllmServedModel: ${vlmServedModel}` : "";

  return `# Generated external client values (lab)
global:
  deploymentProfile: external
  imagePullSecrets:
    - name: registry-pull-secret

ingress:
  enabled: true
  host: ${hosts.web}
  apiHost: ${hosts.api}
  filesHost: ${hosts.files}${classLine}
  tls:
    enabled: true
    secretName: repody-tls

images:
  backend:
    repository: ${imageRepo}/repody-backend
    tag: ${tag}
    pullPolicy: Always
  api:
    repository: ${imageRepo}/repody-backend
    tag: ${tag}
    pullPolicy: Always
  worker:
    repository: ${imageRepo}/repody-backend
    tag: ${tag}
    pullPolicy: Always
  web:
    repository: ${imageRepo}/repody-web
    tag: ${tag}
    pullPolicy: Always

secrets:
  existingSecret: repody-runtime-secrets

externalDatabase:
  existingSecret: repody-runtime-secrets
  urlKey: AUDIT_DATABASE_URL

externalRedis:
  existingSecret: repody-runtime-secrets
  urlKey: AUDIT_REDIS_URL

externalObjectStorage:
  endpoint: repody-data-minio:9000
  bucket: audit-documents
  existingSecret: repody-runtime-secrets
  accessKeyKey: AUDIT_MINIO_ACCESS_KEY
  secretKeyKey: AUDIT_MINIO_SECRET_KEY
  secure: false
  publicEndpoint: ${hosts.files}

config:
  authUrl: https://${hosts.web}
  oidcIssuer: https://${hosts.auth}/realms/repody
  oidcJwksUrl: ${jwks}
  keycloakAdminUrl: https://${hosts.auth}
  corsOrigins: '["https://${hosts.web}"]'
  vllmBaseUrl: ${vlm}${modelLine}

observability:
  otelEnabled: true
  otelEndpoint: http://otel-collector-opentelemetry-collector.observability.svc.cluster.local:4318/v1/traces

migrations:
  enabled: true
`;
}
