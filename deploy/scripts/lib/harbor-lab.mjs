import { createHarborCompose } from "./harbor-compose.mjs";

/**
 * Harbor lab — Docker Compose on the host (independent of OpenShift).
 * @see https://goharbor.io/docs/main/install-config/run-installer-script/
 */

export const HARBOR_NS = "harbor";
export const HARBOR_ADMIN = "admin";

export function createHarborLab(opts) {
  const compose = createHarborCompose(opts);

  function harborHost(_hosts) {
    return compose.pushHost();
  }

  function harborRegistry(_hosts) {
    return compose.registryBase();
  }

  function isInstalled() {
    return compose.isRunning();
  }

  function install(hosts) {
    return compose.install(hosts);
  }

  return {
    harborHost,
    harborRegistry,
    isInstalled,
    install,
    dockerLogin: compose.dockerLogin,
    writePullSecret: compose.writePullSecret,
    stop: compose.stop,
    HARBOR_NS,
    HARBOR_ADMIN,
  };
}
