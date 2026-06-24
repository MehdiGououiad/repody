#!/usr/bin/env node
/**
 * Local Harbor (real registry) for prod-path testing — replaces docker registry:2 on :5001.
 *
 *   pnpm harbor:prepare    Download Harbor installer + harbor.yml
 *   pnpm harbor:up         Start Harbor (docker compose)
 *   pnpm harbor:bootstrap  prepare + up + login + project
 *   pnpm dev:harbor        Bootstrap Repody stack using Harbor
 *
 * Requires: Docker Desktop, bash (Git Bash or WSL on Windows), curl
 * Docs: https://goharbor.io/docs/latest/install-config/
 */
import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { resolveLocalRegistryConfig } from "./k8s-local-registry-config.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const config = resolveLocalRegistryConfig(root);
const HARBOR_VERSION = process.env.REPODY_HARBOR_VERSION ?? "2.11.2";
const INSTALLER_NAME = `harbor-online-installer-v${HARBOR_VERSION}.tgz`;
const INSTALLER_URL = `https://github.com/goharbor/harbor/releases/download/v${HARBOR_VERSION}/${INSTALLER_NAME}`;

function bashExecutable() {
  if (process.platform !== "win32") return "bash";
  const fromEnv = process.env.REPODY_BASH?.trim();
  if (fromEnv && existsSync(fromEnv)) return fromEnv;
  const candidates = [
    "C:\\Program Files\\Git\\bin\\bash.exe",
    "C:\\Program Files\\Git\\usr\\bin\\bash.exe",
  ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  return "bash";
}

function runBash(script, { cwd }) {
  const bash = bashExecutable();
  const env =
    process.platform === "win32"
      ? {
          ...process.env,
          MSYS_NO_PATHCONV: "1",
          MSYS2_ARG_CONV_EXCL: "*",
        }
      : process.env;
  run(bash, [script], { cwd, env });
}

/** @param {string} cmd @param {string[]} args */
function run(cmd, args, { cwd = root, inherit = true, env = process.env } = {}) {
  const result = spawnSync(cmd, args, {
    cwd,
    env,
    stdio: inherit ? "inherit" : "pipe",
    encoding: "utf8",
    shell: false,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
  return result;
}

function sleepSync(ms) {
  spawnSync(
    "node",
    ["-e", `const d=Date.now();while(Date.now()-d<${ms});`],
    { stdio: "ignore" },
  );
}

function harborDir() {
  return config.harborInstallDir;
}

function harborUrl(pathname = "") {
  return `http://${config.registryHost}:${config.harborHttpPort}${pathname}`;
}

function writeHarborYml(dir) {
  const tmplPath = path.join(dir, "harbor.yml.tmpl");
  const harborYml = path.join(dir, "harbor.yml");
  if (!existsSync(tmplPath)) {
    const example = path.join(root, "deploy/harbor/harbor.yml.example");
    copyFileSync(example, harborYml);
    console.error(`ok: wrote ${harborYml} from example`);
    return;
  }
  let text = readFileSync(tmplPath, "utf8");
  text = text.replace(
    /^hostname: reg\.mydomain\.com/m,
    `hostname: ${config.registryHost}`,
  );
  text = text.replace(
    /^# http related config\nhttp:\n  # port for http.*\n  port: 80/m,
    `# http related config\nhttp:\n  port: ${config.harborHttpPort}`,
  );
  text = text.replace(
    /^# https related config\nhttps:[\s\S]*?(?=\n# # Harbor will set ipv4)/m,
    "# https disabled for local HTTP-only dev\n",
  );
  text = text.replace(/^data_volume: \/data/m, "data_volume: ./data");
  if (!/^external_url:/m.test(text)) {
    text = text.replace(
      /^# external_url: https:\/\/reg\.mydomain\.com:8433/m,
      `external_url: ${harborUrl()}`,
    );
  }
  writeFileSync(harborYml, text);
  console.error(`ok: wrote ${harborYml} from harbor.yml.tmpl`);
}

function dockerLoginRegistry() {
  const registry = `${config.registryHost}:${config.harborHttpPort}`;
  console.error(`→ docker login ${registry}`);
  const login = spawnSync(
    "docker",
    ["login", registry, "-u", "admin", "--password-stdin"],
    {
      input: config.harborAdminPassword,
      encoding: "utf8",
      shell: process.platform === "win32",
      stdio: ["pipe", "inherit", "inherit"],
    },
  );
  if (login.status !== 0) {
    process.exit(login.status ?? 1);
  }
  console.error("ok: docker logged in to Harbor");
}

function cmdPrepare() {
  const dir = harborDir();
  const runtimeRoot = path.dirname(dir);
  mkdirSync(dir, { recursive: true });
  const tgzPath = path.join(runtimeRoot, INSTALLER_NAME);

  if (!existsSync(path.join(dir, "install.sh"))) {
    console.error(`→ Downloading Harbor ${HARBOR_VERSION} installer…`);
    const curl = process.platform === "win32" ? "curl.exe" : "curl";
    run(curl, ["-fL", "-o", tgzPath, INSTALLER_URL]);
    const size = spawnSync("node", ["-e", `console.log(require('fs').statSync(${JSON.stringify(tgzPath)}).size)`], {
      encoding: "utf8",
    });
    const bytes = Number(size.stdout?.trim() ?? 0);
    if (bytes < 10_000) {
      console.error(`✗ Download looks too small (${bytes} bytes): ${tgzPath}`);
      process.exit(1);
    }
    console.error(`→ Extracting ${INSTALLER_NAME} (${bytes} bytes)`);
    run("tar", ["-xzf", tgzPath, "-C", runtimeRoot]);
    if (!existsSync(path.join(dir, "install.sh"))) {
      console.error(`✗ Expected ${path.join(dir, "install.sh")} after extract`);
      process.exit(1);
    }
  } else {
    console.error(`ok: Harbor installer already at ${dir}`);
  }

  const harborYml = path.join(dir, "harbor.yml");
  if (!existsSync(harborYml)) {
    writeHarborYml(dir);
  } else {
    console.error(`ok: ${harborYml} already exists`);
  }

  const envExample = path.join(root, "deploy/harbor/paths.harbor.local.env.example");
  const envLocal = path.join(root, "deploy/harbor/paths.harbor.local.env");
  if (!existsSync(envLocal)) {
    copyFileSync(envExample, envLocal);
    console.error(`ok: wrote ${envLocal}`);
  }

  console.error(`
Next:
  1. pnpm k8s:local:hosts   (adds harbor.repody.local)
  2. pnpm harbor:up
  3. pnpm harbor:bootstrap  (or harbor:login + harbor:project)
  4. pnpm dev:harbor
`);
}

function cmdUp() {
  const dir = harborDir();
  if (!existsSync(path.join(dir, "install.sh"))) {
    console.error("Harbor not prepared. Run: pnpm harbor:prepare");
    process.exit(1);
  }
  const compose = path.join(dir, "docker-compose.yml");
  if (existsSync(compose)) {
    console.error("→ Starting Harbor (docker compose up -d)…");
    run("docker", ["compose", "-f", compose, "up", "-d"], { cwd: dir });
  } else {
    console.error("→ First-time Harbor install (install.sh)…");
    const script =
      process.platform === "win32" ? "install.sh" : "./install.sh";
    runBash(script, { cwd: dir });
  }
  console.error(`\n✓ Harbor UI: ${harborUrl()}  (admin / ${config.harborAdminPassword})\n`);
}

function cmdDown() {
  const dir = harborDir();
  const compose = path.join(dir, "docker-compose.yml");
  if (!existsSync(compose)) {
    console.error("ok: Harbor compose file missing — nothing to stop");
    return;
  }
  console.error("→ Stopping Harbor…");
  run("docker", ["compose", "-f", compose, "down"], { cwd: dir });
  console.error("✓ Harbor stopped");
}

function cmdLogin() {
  dockerLoginRegistry();
}

function cmdProject() {
  const api = harborUrl("/api/v2.0/projects");
  const body = JSON.stringify({
    project_name: config.harborProject,
    public: true,
  });
  const curl = process.platform === "win32" ? "curl.exe" : "curl";
  const result = spawnSync(
    curl,
    [
      "-fsS",
      "-u",
      `admin:${config.harborAdminPassword}`,
      "-H",
      "Content-Type: application/json",
      "-X",
      "POST",
      api,
      "-d",
      body,
    ],
    { encoding: "utf8", shell: false },
  );
  if (result.status === 0) {
    console.error(`ok: Harbor project '${config.harborProject}' ready (public)`);
    return;
  }
  const text = `${result.stdout ?? ""}${result.stderr ?? ""}`;
  if (/already exists|conflict|409/i.test(text)) {
    console.error(`ok: Harbor project '${config.harborProject}' already exists`);
    return;
  }
  console.error(text || "Failed to create Harbor project");
  process.exit(result.status ?? 1);
}

function findHarborProxyContainer() {
  const byLabel = spawnSync(
    "docker",
    [
      "ps",
      "--format",
      "{{.Names}}",
      "--filter",
      "label=com.docker.compose.service=proxy",
    ],
    { encoding: "utf8", shell: process.platform === "win32" },
  );
  const labeled = (byLabel.stdout ?? "")
    .split("\n")
    .map((name) => name.trim())
    .filter(Boolean);
  if (labeled[0]) return labeled[0];

  const all = spawnSync("docker", ["ps", "--format", "{{.Names}}"], {
    encoding: "utf8",
    shell: process.platform === "win32",
  });
  return (
    (all.stdout ?? "")
      .split("\n")
      .map((name) => name.trim())
      .find((name) => /^(nginx|harbor-proxy|harbor-nginx)$/i.test(name)) ?? ""
  );
}

function cmdConnectKind() {
  const proxy = findHarborProxyContainer();
  if (!proxy) {
    console.error("✗ Harbor proxy container not found. Is Harbor running? (pnpm harbor:up)");
    process.exit(1);
  }
  const networks = spawnSync("docker", ["network", "ls", "--format", "{{.Name}}"], {
    encoding: "utf8",
    shell: process.platform === "win32",
  });
  if (!networks.stdout?.includes("kind")) {
    console.error("✗ kind network missing — create cluster first: pnpm dev:harbor");
    process.exit(1);
  }
  const result = spawnSync(
    "docker",
    ["network", "connect", "--alias", config.registryHost, "kind", proxy],
    { encoding: "utf8", shell: process.platform === "win32" },
  );
  if (result.status === 0) {
    console.error(`ok: ${proxy} on kind network as ${config.registryHost}`);
    return;
  }
  const stderr = result.stderr ?? "";
  if (stderr.includes("already exists")) {
    console.error(`ok: ${proxy} already on kind network`);
    return;
  }
  console.error(stderr || "docker network connect failed");
  process.exit(result.status ?? 1);
}

function cmdBootstrap() {
  cmdPrepare();
  cmdUp();
  console.error("→ Waiting for Harbor API…");
  const curl = process.platform === "win32" ? "curl.exe" : "curl";
  let ready = false;
  for (let i = 0; i < 60; i++) {
    const probe = spawnSync(
      curl,
      ["-fsS", "--max-time", "3", harborUrl("/api/v2.0/health")],
      { encoding: "utf8", shell: false },
    );
    if (probe.status === 0) {
      ready = true;
      break;
    }
    sleepSync(5000);
  }
  if (!ready) {
    console.error("✗ Harbor API did not become ready in time");
    process.exit(1);
  }
  dockerLoginRegistry();
  cmdProject();
  console.error(`
✓ Harbor bootstrap complete.

  pnpm k8s:local:hosts
  pnpm dev:harbor

After kind cluster exists, connect Harbor to kind (safe to repeat):
  pnpm harbor:connect-kind
`);
}

const sub = process.argv[2] ?? "bootstrap";
if (sub === "prepare") cmdPrepare();
else if (sub === "up") cmdUp();
else if (sub === "down") cmdDown();
else if (sub === "login") cmdLogin();
else if (sub === "project") cmdProject();
else if (sub === "connect-kind") cmdConnectKind();
else if (sub === "bootstrap") cmdBootstrap();
else {
  console.error(
    "Usage: pnpm harbor:[prepare|up|down|login|project|connect-kind|bootstrap]",
  );
  process.exit(1);
}
