import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Harbor on Docker Compose — official online installer workflow.
 * @see https://goharbor.io/docs/main/install-config/download-installer/
 * @see https://goharbor.io/docs/main/install-config/run-installer-script/
 * @see https://goharbor.io/docs/main/working-with-projects/working-with-images/pulling-pushing-images/
 */

export const HARBOR_ADMIN = "admin";
export const HARBOR_VERSION = process.env.REPODY_HARBOR_VERSION?.trim() || "2.14.0";
export const HARBOR_PROJECT = "repody";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const labHarborDir = path.join(root, "deploy/client/lab/harbor");
const templateYml = path.join(labHarborDir, "harbor.yml");

function findBash() {
  if (process.platform !== "win32") return "bash";
  for (const candidate of [
    process.env.REPODY_BASH_PATH,
    "C:\\Program Files\\Git\\bin\\bash.exe",
    "C:\\Program Files (x86)\\Git\\bin\\bash.exe",
  ]) {
    if (candidate && existsSync(candidate)) return candidate;
  }
  return "bash";
}

export function createHarborCompose({ fail, log, sleep, state, runtimeDir, dryRun = false }) {
  // Avoid OneDrive paths — Harbor prepare uses docker bind mounts (official installer on Windows).
  const harborHome =
    process.env.REPODY_HARBOR_RUNTIME_DIR?.trim() ||
    path.join(os.homedir(), ".cache", "repody", "harbor");
  const installerDir = path.join(harborHome, `harbor-installer-v${HARBOR_VERSION}`);

  function pushHost() {
    return process.env.REPODY_HARBOR_HOST?.trim() || "localhost:5080";
  }

  function clusterHost() {
    if (process.env.REPODY_HARBOR_CLUSTER_HOST?.trim()) {
      return process.env.REPODY_HARBOR_CLUSTER_HOST.trim();
    }
    // CRC VM resolves the host via host.crc.testing (not host.crc.internal).
    if (pushHost().startsWith("localhost")) return "host.crc.testing:5080";
    return pushHost();
  }

  function registryBase(host = pushHost()) {
    return `${host.replace(/^https?:\/\//, "")}/${HARBOR_PROJECT}`;
  }

  function isRunning() {
    if (state.isFresh("harbor")) return true;
    if (!existsSync(path.join(installerDir, "docker-compose.yml"))) return false;
    const probe = spawnQuiet("docker", [
      "compose",
      "-f",
      path.join(installerDir, "docker-compose.yml"),
      "ps",
      "--status=running",
      "-q",
    ], { cwd: installerDir });
    return probe.status === 0 && (probe.stdout ?? "").trim().length > 0;
  }

  function ensureInstaller() {
    const composeYml = path.join(installerDir, "docker-compose.yml");
    const prepareScript = path.join(installerDir, "prepare");
    if (existsSync(composeYml)) {
      return installerDir;
    }
    if (existsSync(prepareScript) && !process.env.REPODY_FORCE_INFRA) {
      return installerDir;
    }

    mkdirSync(harborHome, { recursive: true });
    const tgz = path.join(harborHome, `harbor-online-installer-v${HARBOR_VERSION}.tgz`);
    const url = `https://github.com/goharbor/harbor/releases/download/v${HARBOR_VERSION}/harbor-online-installer-v${HARBOR_VERSION}.tgz`;

    log("harbor", `downloading official installer v${HARBOR_VERSION}`);
    const curl = process.platform === "win32" ? "curl.exe" : "curl";
    const dl = spawnSync(curl, ["-fsSL", "-o", tgz, url], { encoding: "utf8", stdio: "inherit", shell: false });
    if (dl.status !== 0) fail(`Harbor installer download failed: ${url}`);

    mkdirSync(installerDir, { recursive: true });
    const tar = spawnSync("tar", ["-xzf", tgz, "-C", installerDir, "--strip-components=1"], {
      encoding: "utf8",
      stdio: "inherit",
      shell: false,
    });
    if (tar.status !== 0) fail("Harbor installer extract failed (need tar in PATH)");

    return installerDir;
  }

  function stripHttpsBlock(yml) {
    const lines = yml.split("\n");
    const out = [];
    let skip = false;
    for (const line of lines) {
      if (/^https:\s*$/.test(line)) {
        skip = true;
        out.push("# https disabled for lab (HTTP only)");
        continue;
      }
      if (skip) {
        if (/^[a-z_][\w-]*:/.test(line) && !line.startsWith("  ")) {
          skip = false;
          out.push(line);
        }
        continue;
      }
      out.push(line);
    }
    return out.join("\n");
  }

  function writeHarborYml(dir) {
    const password = process.env.REPODY_HARBOR_PASSWORD?.trim() || "Harbor12345";
    const tmplPath = path.join(dir, "harbor.yml.tmpl");
    const basePath = existsSync(tmplPath) ? tmplPath : templateYml;
    let yml = readFileSync(basePath, "utf8");
    yml = stripHttpsBlock(yml);
    yml = yml.replace(/^hostname:.*/m, "hostname: localhost");
    yml = yml.replace(/(\nhttp:\n(?:  .*\n)*?  port: )\d+/m, "$15080");
    yml = yml.replace(/harbor_admin_password:.*/, `harbor_admin_password: ${password}`);
    const dataDir = path.join(dir, "harbor-data");
    mkdirSync(dataDir, { recursive: true });
    const dataVolume = process.platform === "win32" ? dataDir.replace(/\\/g, "/") : dataDir;
    yml = yml.replace(/^data_volume:.*/m, `data_volume: ${dataVolume}`);
    if (process.env.REPODY_HARBOR_HOST?.trim()) {
      const hostOnly = process.env.REPODY_HARBOR_HOST.trim().split(":")[0];
      yml = yml.replace(/^hostname:.*/m, `hostname: ${hostOnly}`);
    }
    writeFileSync(path.join(dir, "harbor.yml"), yml, "utf8");
  }

  function parseDataVolume(dir) {
    const yml = readFileSync(path.join(dir, "harbor.yml"), "utf8");
    const match = yml.match(/^[^#]*data_volume:\s*(\S+)/m);
    const volume = match?.[1] ?? "harbor-data";
    return path.isAbsolute(volume) ? volume : path.join(dir, volume);
  }

  /** Official prepare via docker run — avoids Git Bash MSYS path conversion on Windows. */
  function runPrepareNative(dir) {
    const inputDir = path.join(dir, "input");
    rmSync(inputDir, { recursive: true, force: true });
    mkdirSync(inputDir, { recursive: true });
    cpSync(path.join(dir, "harbor.yml"), path.join(inputDir, "harbor.yml"));

    const dataPath = parseDataVolume(dir);
    mkdirSync(dataPath, { recursive: true });
    const configDir = path.join(dir, "common", "config");
    mkdirSync(configDir, { recursive: true });

    const dockerArgs = [
      "run",
      "--rm",
      "-v",
      `${inputDir}:/input`,
      "-v",
      `${dataPath}:/data`,
      "-v",
      `${dir}:/compose_location`,
      "-v",
      `${configDir}:/config`,
      "--privileged",
      `goharbor/prepare:v${HARBOR_VERSION}`,
      "prepare",
    ];

    // Linux prepare script mounts host root; skip on Windows (Git Bash breaks `-v /:/hostfs/`).
    if (process.platform === "linux") {
      dockerArgs.splice(
        dockerArgs.length - 2,
        0,
        "-v",
        "/:/hostfs/",
      );
    } else if (process.platform === "darwin") {
      const home = os.homedir();
      dockerArgs.splice(dockerArgs.length - 2, 0, "-v", `${home}:/hostfs${home}`);
    }

    log("harbor", "running official prepare (generates docker-compose.yml)");
    const result = spawnSync("docker", dockerArgs, {
      cwd: dir,
      encoding: "utf8",
      stdio: "inherit",
      shell: false,
    });
    rmSync(inputDir, { recursive: true, force: true });
    if (result.status !== 0) fail("Harbor prepare failed");
  }

  function runPrepare(dir) {
    const script = path.join(dir, "prepare");
    if (!existsSync(script)) fail(`Harbor prepare script missing in ${dir}`);
    if (process.platform === "win32") {
      runPrepareNative(dir);
      return;
    }
    log("harbor", "running official prepare (generates docker-compose.yml)");
    const result = spawnSync(findBash(), [script], {
      cwd: dir,
      encoding: "utf8",
      stdio: "inherit",
      shell: false,
      env: { ...process.env, MSYS_NO_PATHCONV: "1", MSYS2_ARG_CONV_EXCL: "*" },
    });
    if (result.status !== 0) fail("Harbor prepare failed");
  }

  function composeUp(dir) {
    log("harbor", "docker compose up -d (official Harbor stack)");
    const result = spawnSync("docker", ["compose", "up", "-d"], {
      cwd: dir,
      encoding: "utf8",
      stdio: "inherit",
      shell: false,
    });
    if (result.status !== 0) fail("docker compose up failed for Harbor");
  }

  function waitReady(host, password, timeoutSec = 300) {
    const curl = process.platform === "win32" ? "curl.exe" : "curl";
    const auth = Buffer.from(`${HARBOR_ADMIN}:${password}`).toString("base64");
    const deadline = Date.now() + timeoutSec * 1000;
    while (Date.now() < deadline) {
      const probe = spawnQuiet(curl, [
        "-fsS",
        "-H",
        `Authorization: Basic ${auth}`,
        `http://${host}/api/v2.0/systeminfo`,
      ]);
      if (probe.status === 0) return true;
      sleep(5000);
    }
    return false;
  }

  function ensureProject(host, password) {
    const auth = Buffer.from(`${HARBOR_ADMIN}:${password}`).toString("base64");
    const curl = process.platform === "win32" ? "curl.exe" : "curl";
    const base = `http://${host}/api/v2.0`;
    const probe = spawnQuiet(curl, ["-fsS", "-H", `Authorization: Basic ${auth}`, `${base}/projects?name=${HARBOR_PROJECT}`]);
    if (probe.status !== 0) return;
    if ((probe.stdout ?? "").includes(`"name":"${HARBOR_PROJECT}"`)) return;
    const create = spawnQuiet(curl, [
      "-fsS",
      "-X",
      "POST",
      "-H",
      `Authorization: Basic ${auth}`,
      "-H",
      "Content-Type: application/json",
      "-d",
      JSON.stringify({ project_name: HARBOR_PROJECT, public: false }),
      `${base}/projects`,
    ]);
    if (create.status !== 0) {
      fail(`Harbor project ${HARBOR_PROJECT} creation failed: ${(create.stderr ?? create.stdout ?? "").trim()}`);
    }
  }

  /** Start Harbor via official Docker Compose installer — host-only, not in-cluster. */
  function install() {
    if (dryRun) {
      log("harbor", `[dry-run] compose install at http://${pushHost()}`);
      return { host: pushHost(), clusterHost: clusterHost(), password: "Harbor12345", registry: registryBase() };
    }

    const password = process.env.REPODY_HARBOR_PASSWORD?.trim() || "Harbor12345";
    const host = pushHost();

    if (isRunning() && !process.env.REPODY_FORCE_INFRA) {
      log("harbor", `already running at http://${host} (skip compose up)`);
    } else {
      const dir = ensureInstaller();
      writeHarborYml(dir);
      runPrepare(dir);
      composeUp(dir);
      if (!waitReady(host, password)) fail("Harbor API did not become ready");
    }

    ensureProject(host, password);

    const info = {
      host,
      clusterHost: clusterHost(),
      password,
      registry: registryBase(),
      clusterRegistry: registryBase(clusterHost()),
      installedAt: new Date().toISOString(),
    };
    state.write({ harbor: info });
    log(
      "harbor",
      [
        `ready http://${host} (Docker Compose — official installer)`,
        `  push:  ${info.registry}`,
        `  pull:  ${info.clusterRegistry} (set REPODY_HARBOR_CLUSTER_HOST for CRC)`,
      ].join("\n"),
    );
    return info;
  }

  function dockerLogin(host, user, password) {
    const login = spawnSync("docker", ["login", "-u", user, "--password-stdin", host], {
      encoding: "utf8",
      input: password,
      stdio: "pipe",
      shell: false,
    });
    if (login.status !== 0) {
      fail(`docker login to ${host} failed: ${(login.stderr ?? login.stdout ?? "").trim()}`);
    }
  }

  function writePullSecret(host, user, password) {
    const auth = Buffer.from(`${user}:${password}`, "utf8").toString("base64");
    const registryHost = host.replace(/^https?:\/\//, "").split("/")[0];
    const dockerConfig = JSON.stringify({
      auths: {
        [registryHost]: { username: user, password, auth, email: "repody-lab@local" },
      },
    });
    return dockerConfig;
  }

  function stop() {
    if (!existsSync(path.join(installerDir, "docker-compose.yml"))) return;
    spawnSync("docker", ["compose", "down"], { cwd: installerDir, encoding: "utf8", stdio: "inherit", shell: false });
    log("harbor", "Docker Compose stack stopped");
  }

  return {
    install,
    stop,
    dockerLogin,
    writePullSecret,
    pushHost,
    clusterHost,
    registryBase,
    isRunning,
    HARBOR_ADMIN,
    HARBOR_PROJECT,
  };
}

function spawnQuiet(cmd, args) {
  return spawnSync(cmd, args, { encoding: "utf8", stdio: "pipe", shell: false });
}
