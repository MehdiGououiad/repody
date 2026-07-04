import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

/**
 * Promote images from k3d registry to in-cluster Harbor via skopeo Job.
 * @see https://goharbor.io/docs/main/working-with-projects/working-with-images/pulling-pushing-images/
 */
export function promoteK3dImagesToHarbor({
  kubectl,
  kubectlOut,
  fail,
  sleep,
  runtimeDir,
  harborNamespace,
  tag,
  sourceRegistryHost,
  destRegistryHost,
  harborUser,
  harborPass,
}) {
  const src = `docker://${sourceRegistryHost}/repody`;
  const dst = `docker://${destRegistryHost}/repody`;
  const creds = `${harborUser}:${harborPass}`;
  const script = [
    "set -e",
    `skopeo copy --src-tls-verify=false --dest-tls-verify=false ${src}/repody-backend:${tag} ${dst}/repody-backend:${tag} --dest-creds ${creds}`,
    `skopeo copy --src-tls-verify=false --dest-tls-verify=false ${src}/repody-web:${tag} ${dst}/repody-web:${tag} --dest-creds ${creds}`,
  ]
    .map((line) => `              ${line}`)
    .join("\n");

  kubectl(["delete", "job", "harbor-image-promote", "-n", harborNamespace, "--ignore-not-found"], {
    quiet: true,
  });
  const manifest = `apiVersion: batch/v1
kind: Job
metadata:
  name: harbor-image-promote
  namespace: ${harborNamespace}
spec:
  backoffLimit: 3
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: skopeo
          image: quay.io/skopeo/stable:latest
          command: ["/bin/sh", "-c"]
          args:
            - |
${script}
`;
  mkdirSync(runtimeDir, { recursive: true });
  const jobPath = path.join(runtimeDir, "harbor-image-promote.job.yaml");
  writeFileSync(jobPath, manifest, "utf8");
  const applied = kubectl(["apply", "-f", jobPath], { quiet: true });
  if (applied.status !== 0) fail("kubectl apply harbor-image-promote job failed");
  sleep(5000);
  const wait = kubectl(
    ["wait", "--for=condition=complete", "job/harbor-image-promote", "-n", harborNamespace, "--timeout=600s"],
    { quiet: true },
  );
  if (wait.status !== 0) {
    const pod = kubectlOut([
      "get",
      "pods",
      "-n",
      harborNamespace,
      "-l",
      "job-name=harbor-image-promote",
      "-o",
      "jsonpath={.items[0].metadata.name}",
    ]);
    if (pod) kubectl(["logs", pod, "-n", harborNamespace, "--tail=100"], { quiet: false });
    fail("in-cluster promote k3d registry → Harbor failed");
  }
}
