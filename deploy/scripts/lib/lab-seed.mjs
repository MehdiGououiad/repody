import { LAB, auditDatabaseUrl, auditRedisUrl } from "../../client/lab/lab.constants.mjs";

/**
 * Standard lab Vault KV payloads for bundled client labs.
 * @param {object} opts
 * @param {string} opts.dockerConfigJson REGISTRY_DOCKERCONFIGJSON value
 */
export function buildLabVaultKvs({ dockerConfigJson }) {
  const dataKv = {
    POSTGRES_ADMIN_PASSWORD: LAB.pgAdminPassword,
    POSTGRES_USER_PASSWORD: LAB.pgUserPassword,
    REDIS_PASSWORD: LAB.redisPassword,
    MINIO_ROOT_USER: LAB.minioUser,
    MINIO_ROOT_PASSWORD: LAB.minioPassword,
  };
  const runtimeKv = {
    AUTH_SECRET: LAB.authSecret,
    AUTH_KEYCLOAK_CLIENT_SECRET: LAB.keycloakClientSecret,
    KEYCLOAK_ADMIN_PASSWORD: LAB.keycloakAdminPassword,
    KEYCLOAK_DB_PASSWORD: LAB.keycloakDbPassword,
    AUDIT_DATABASE_URL: auditDatabaseUrl(),
    AUDIT_REDIS_URL: auditRedisUrl(),
    AUDIT_MINIO_ACCESS_KEY: LAB.minioUser,
    AUDIT_MINIO_SECRET_KEY: LAB.minioPassword,
    BUGSINK_DSN: LAB.bugsinkDsn,
    AUDIT_LLAMACPP_API_KEY: LAB.llamacppApiKey,
    REGISTRY_DOCKERCONFIGJSON: dockerConfigJson,
  };
  return { dataKv, runtimeKv };
}
