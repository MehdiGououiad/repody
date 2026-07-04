import { RESTRICTED_CONTAINER_SECURITY, RESTRICTED_POD_SECURITY } from "./lab-security.mjs";

/**
 * Run Alembic migrations via a one-off Job (lab scripts when Helm hook is skipped).
 * @param {object} opts
 * @param {(args: string[], options?: object) => object} opts.apply
 * @param {(args: string[]) => string} opts.getOut
 * @param {(message: string, code?: number) => never} opts.fail
 * @param {string} opts.namespace
 * @param {string} opts.backendImage
 * @param {string} [opts.jobName]
 */
export function ensureMigrationsJob({
  apply,
  getOut,
  fail,
  namespace,
  backendImage,
  jobName = "repody-migrations-manual",
}) {
  const done = getOut(["get", "job", jobName, "-n", namespace, "-o", "jsonpath={.status.succeeded}"]);
  if (done === "1") return;
  apply(["delete", "job", jobName, "-n", namespace, "--ignore-not-found"], { quiet: true });
  const manifest = `apiVersion: batch/v1
kind: Job
metadata:
  name: ${jobName}
  namespace: ${namespace}
spec:
  backoffLimit: 3
  template:
    metadata:
      labels:
        app.kubernetes.io/component: migrations
    spec:
      restartPolicy: OnFailure
      automountServiceAccountToken: false
${RESTRICTED_POD_SECURITY}
      imagePullSecrets:
        - name: registry-pull-secret
      containers:
        - name: migrations
          image: ${backendImage}
          imagePullPolicy: Always
          command: ["python", "/app/scripts/bootstrap_migrations.py"]
${RESTRICTED_CONTAINER_SECURITY}
          envFrom:
            - secretRef:
                name: repody-runtime-secrets
`;
  apply(["apply", "-f", "-"], { input: manifest, quiet: true });
  const wait = apply(["wait", "--for=condition=complete", `job/${jobName}`, "-n", namespace, "--timeout=300s"], {
    quiet: true,
  });
  if (wait.status !== 0) fail("database migrations job did not complete");
}
