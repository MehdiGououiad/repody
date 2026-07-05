/** OpenShift client test lab credentials — simulates Vault paths. Not for production. */
export const LAB = {
  pgUser: "audit",
  pgUserPassword: "bundled-e2e-pg-user",
  pgAdminPassword: "bundled-e2e-pg-admin",
  redisPassword: "bundled-e2e-redis",
  minioUser: "minioadmin",
  minioPassword: "bundled-e2e-minio",
  authSecret: "bundled-e2e-auth-secret-32chars!!",
  keycloakClientSecret: "repody-web-dev-secret",
  keycloakAdminPassword: "bundled-e2e-kc-admin",
  bugsinkDsn: "",
  vllmApiKey: "",
};

export function auditDatabaseUrl() {
  return `postgresql+asyncpg://${LAB.pgUser}:${LAB.pgUserPassword}@repody-data-postgresql:5432/audit_workbench`;
}

export function auditRedisUrl() {
  return `redis://:${LAB.redisPassword}@repody-data-redis-master:6379/0`;
}
